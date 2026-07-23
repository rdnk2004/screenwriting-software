/**
 * fountainMode.js
 *
 * CodeMirror 6 extension that implements:
 *  1. Line-level classification of Fountain element types
 *  2. CSS class decorations per element type
 *  3. Tab key → cycle element type
 *  4. Enter key → smart next-element logic
 *  5. Auto-uppercase for scene headings and character cues
 */

import {
  EditorView,
  Decoration,
  ViewPlugin,
  keymap,
} from "@codemirror/view";
import { StateEffect, StateField, Transaction } from "@codemirror/state";

// ---------------------------------------------------------------------------
// Element type definitions & cycling order
// ---------------------------------------------------------------------------

export const LINE_TYPES = [
  "scene_heading",
  "action",
  "character",
  "dialogue",
  "parenthetical",
  "transition",
];

const CYCLE_ORDER = [
  "scene_heading",
  "action",
  "character",
  "dialogue",
  "parenthetical",
  "transition",
];

/** What element type should follow the current one when Enter is pressed. */
const NEXT_AFTER = {
  scene_heading: "action",
  action: "action",
  character: "dialogue",
  dialogue: "action",
  parenthetical: "dialogue",
  transition: "scene_heading",
};

// ---------------------------------------------------------------------------
// CSS class map
// ---------------------------------------------------------------------------

const TYPE_CLASS = {
  scene_heading: "fountain-scene-heading",
  action: "fountain-action",
  character: "fountain-character",
  dialogue: "fountain-dialogue",
  parenthetical: "fountain-parenthetical",
  transition: "fountain-transition",
};

// ---------------------------------------------------------------------------
// Fountain heuristic classifier (mirrors backend logic, simplified)
// ---------------------------------------------------------------------------

const RE_SCENE_HEADING = /^(INT\.|EXT\.|INT\/EXT\.|I\/E\.)\s/i;
const RE_TRANSITION = /^[A-Z][A-Z\s]+TO:\s*$/;
const RE_PARENTHETICAL = /^\(.*\)\s*$/;
const RE_CHARACTER = /^[A-Z][A-Z0-9\s\.\-']+(\s*\([^)]+\))?\s*$/;

/**
 * Classify a single line of text given the previous line's type.
 * Returns an element type string.
 */
export function classifyLine(text, prevType) {
  const trimmed = text.trim();

  if (!trimmed) return "action";

  // Forced scene heading
  if (trimmed.startsWith(".") && !trimmed.startsWith("..")) return "scene_heading";
  // Natural scene heading
  if (RE_SCENE_HEADING.test(trimmed)) return "scene_heading";

  // Forced transition
  if (trimmed.startsWith(">")) return "transition";
  // Natural transition
  if (RE_TRANSITION.test(trimmed)) return "transition";

  // Parenthetical (only valid inside dialogue context)
  if (RE_PARENTHETICAL.test(trimmed) && ["character", "dialogue", "parenthetical"].includes(prevType))
    return "parenthetical";

  // Dialogue (after character or parenthetical)
  if (["character", "parenthetical"].includes(prevType) && trimmed.length > 0)
    return "dialogue";

  // Character cue
  if (RE_CHARACTER.test(trimmed) && trimmed.replace(/\s/g, "").length >= 2 && !RE_SCENE_HEADING.test(trimmed))
    return "character";

  return "action";
}

// ---------------------------------------------------------------------------
// StateField: stores per-line type overrides (user used Tab to override)
// ---------------------------------------------------------------------------

/** Effect to set the type for a specific line number. */
export const setLineTypeEffect = StateEffect.define();

/**
 * Map from line number → forced type string.
 * If a line is not in this map, the heuristic classifier is used.
 */
export const lineTypeField = StateField.define({
  create: () => new Map(),
  update(map, tr) {
    let newMap = map;
    for (const effect of tr.effects) {
      if (effect.is(setLineTypeEffect)) {
        newMap = new Map(newMap);
        newMap.set(effect.value.line, effect.value.type);
      }
    }
    // When lines are inserted/deleted, remap forced types
    if (tr.docChanged && newMap.size > 0) {
      const remapped = new Map();
      newMap.forEach((type, lineNo) => {
        try {
          const oldPos = tr.startState.doc.line(lineNo).from;
          const newLineNo = tr.newDoc.lineAt(tr.changes.mapPos(oldPos)).number;
          remapped.set(newLineNo, type);
        } catch {
          // line was deleted, skip
        }
      });
      newMap = remapped;
    }
    return newMap;
  },
});

// ---------------------------------------------------------------------------
// Get the type for a given line (forced override OR heuristic)
// ---------------------------------------------------------------------------

export function getLineType(state, lineNo) {
  const forced = state.field(lineTypeField).get(lineNo);
  if (forced) return forced;

  const lineObj = state.doc.line(lineNo);
  const prevType = lineNo > 1 ? getLineType(state, lineNo - 1) : "action";
  return classifyLine(lineObj.text, prevType);
}

// ---------------------------------------------------------------------------
// Decoration ViewPlugin — adds CSS class decorations to each line
// ---------------------------------------------------------------------------

function buildDecorations(view) {
  const decorations = [];
  for (const { from, to } of view.visibleRanges) {
    let lineNo = view.state.doc.lineAt(from).number;
    const lastLine = view.state.doc.lineAt(to).number;
    while (lineNo <= lastLine) {
      const lineObj = view.state.doc.line(lineNo);
      const type = getLineType(view.state, lineNo);
      const cls = TYPE_CLASS[type] || "fountain-action";
      decorations.push(
        Decoration.line({ class: cls }).range(lineObj.from)
      );
      lineNo++;
    }
  }
  return Decoration.set(decorations, true);
}

export const fountainDecorations = ViewPlugin.fromClass(
  class {
    constructor(view) {
      this.decorations = buildDecorations(view);
    }
    update(update) {
      if (update.docChanged || update.viewportChanged || update.startState.field(lineTypeField) !== update.state.field(lineTypeField)) {
        this.decorations = buildDecorations(update.view);
      }
    }
  },
  { decorations: (v) => v.decorations }
);

// ---------------------------------------------------------------------------
// Auto-uppercase transformation
// ---------------------------------------------------------------------------

/**
 * After every document change, uppercase lines that are scene_heading or
 * character type.
 */
export const autoUppercase = EditorView.updateListener.of((update) => {
  if (!update.docChanged) return;

  // Gather changes: find lines that need uppercasing
  const changes = [];
  update.changes.iterChangedRanges((_fromA, _toA, fromB, toB) => {
    const startLine = update.state.doc.lineAt(fromB).number;
    const endLine = update.state.doc.lineAt(toB).number;
    for (let ln = startLine; ln <= endLine; ln++) {
      const type = getLineType(update.state, ln);
      if (type === "scene_heading" || type === "character") {
        const lineObj = update.state.doc.line(ln);
        const upper = lineObj.text.toUpperCase();
        if (upper !== lineObj.text) {
          changes.push({ from: lineObj.from, to: lineObj.to, insert: upper });
        }
      }
    }
  });

  if (changes.length === 0) return;

  // Dispatch the uppercasing as a separate transaction annotated so it
  // doesn't re-trigger this listener infinitely.
  update.view.dispatch({
    changes,
    annotations: Transaction.addToHistory.of(false),
  });
});

// ---------------------------------------------------------------------------
// Keymap: Tab cycles type, Enter inserts next element
// ---------------------------------------------------------------------------

function cycleType(view) {
  const { state } = view;
  const sel = state.selection.main;
  const lineNo = state.doc.lineAt(sel.head).number;
  const current = getLineType(state, lineNo);
  const idx = CYCLE_ORDER.indexOf(current);
  const next = CYCLE_ORDER[(idx + 1) % CYCLE_ORDER.length];

  view.dispatch({
    effects: setLineTypeEffect.of({ line: lineNo, type: next }),
  });
  return true;
}

function smartEnter(view) {
  const { state } = view;
  const sel = state.selection.main;
  const lineNo = state.doc.lineAt(sel.head).number;
  const currentType = getLineType(state, lineNo);
  const nextType = NEXT_AFTER[currentType] || "action";

  // Insert a newline (standard behaviour) — then force the next line's type
  const insertPos = sel.head;
  view.dispatch(
    state.replaceSelection("\n"),
    // After the transaction, the cursor is on the new line
  );

  // Now force the new line's type
  const newLineNo = view.state.doc.lineAt(view.state.selection.main.head).number;
  view.dispatch({
    effects: setLineTypeEffect.of({ line: newLineNo, type: nextType }),
  });

  return true;
}

// ---------------------------------------------------------------------------
// Combined extension export
// ---------------------------------------------------------------------------

export const fountainExtension = [
  lineTypeField,
  fountainDecorations,
  autoUppercase,
  keymap.of([
    { key: "Tab", run: cycleType },
    { key: "Enter", run: smartEnter },
  ]),
];
