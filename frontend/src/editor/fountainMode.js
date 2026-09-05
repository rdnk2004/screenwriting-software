/**
 * fountainMode.js
 *
 * CodeMirror 6 extension for Fountain screenplay format:
 *  1. Full Fountain 1.1 line-level classification (Scene Heading, Action, Character,
 *     Parenthetical, Dialogue, Transition, Centered)
 *  2. PageBreakWidget implementation for standard ~54-line screenplay pages
 *  3. Memoized parsed line types for 60fps typing without recursive lag
 *  4. Hollywood standard auto-formatting (Tab element cycle, smart Enter, auto-caps)
 */

import {
  EditorView,
  Decoration,
  ViewPlugin,
  keymap,
  WidgetType,
} from "@codemirror/view";
import { StateEffect, StateField, Transaction } from "@codemirror/state";

// ---------------------------------------------------------------------------
// PageBreakWidget: Renders visual screenplay page dividers every 54 lines
// ---------------------------------------------------------------------------

export class PageBreakWidget extends WidgetType {
  constructor(pageNum) {
    super();
    this.pageNum = pageNum;
  }

  toDOM() {
    const wrap = document.createElement("div");
    wrap.className = "screenplay-page-break-widget";
    const badge = document.createElement("span");
    badge.className = "page-break-badge";
    badge.textContent = `PAGE ${this.pageNum}`;
    wrap.appendChild(badge);
    return wrap;
  }

  eq(other) {
    return other.pageNum === this.pageNum;
  }
}

// ---------------------------------------------------------------------------
// Element type definitions & cycling order
// ---------------------------------------------------------------------------

export const LINE_TYPES = [
  "scene_heading",
  "action",
  "character",
  "parenthetical",
  "dialogue",
  "transition",
  "centered",
];

export const CYCLE_ORDER = [
  "scene_heading",
  "action",
  "character",
  "parenthetical",
  "dialogue",
  "transition",
  "centered",
];

/** What element type naturally follows when Enter is pressed */
export const NEXT_AFTER = {
  scene_heading: "action",
  action: "action",
  character: "dialogue",
  dialogue: "dialogue",
  parenthetical: "dialogue",
  transition: "scene_heading",
  centered: "action",
};

// ---------------------------------------------------------------------------
// CSS class map
// ---------------------------------------------------------------------------

export const TYPE_CLASS = {
  scene_heading: "fountain-scene-heading",
  action: "fountain-action",
  character: "fountain-character",
  dialogue: "fountain-dialogue",
  parenthetical: "fountain-parenthetical",
  transition: "fountain-transition",
  centered: "fountain-centered",
};

// ---------------------------------------------------------------------------
// Fountain syntax patterns
// ---------------------------------------------------------------------------

const RE_SCENE_HEADING = /^(INT\.|EXT\.|INT\/EXT\.|INT\.\/EXT\.|I\/E\.|I\/E)\s+/i;
const RE_TRANSITION_NATURAL = /^[A-Z][A-Z\s]+TO:\s*$/;
const RE_PARENTHETICAL = /^\(.*\)\s*$/;
const RE_CHARACTER = /^([A-Z0-9\s\.\-']+?)(\s*\([^)]+\))?(\s*\^)?\s*$/;

// ---------------------------------------------------------------------------
// StateField: stores per-line type overrides (user forced via Tab or Toolbar)
// ---------------------------------------------------------------------------

export const setLineTypeEffect = StateEffect.define();

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
// Fast Linear Document Classifier (Fountain 1.1 Specification Compliant)
// ---------------------------------------------------------------------------

export function parseDocumentLineTypes(doc, forcedMap = new Map()) {
  const types = [];
  let inDialogueBlock = false;
  let prevNonEmptyType = null;
  const lineCount = doc.lines;

  for (let i = 1; i <= lineCount; i++) {
    // Check manual override first
    if (forcedMap && forcedMap.has(i)) {
      const forced = forcedMap.get(i);
      types[i] = forced;
      if (forced === "character" || forced === "parenthetical" || forced === "dialogue") {
        inDialogueBlock = true;
      } else {
        inDialogueBlock = false;
      }
      prevNonEmptyType = forced;
      continue;
    }

    const lineText = doc.line(i).text;
    const trimmed = lineText.trim();

    if (!trimmed) {
      types[i] = "action"; // Blank line behaves as action spacing
      inDialogueBlock = false;
      prevNonEmptyType = null;
      continue;
    }

    // 1. Centered text: > CENTERED TEXT <
    if (trimmed.startsWith(">") && trimmed.endsWith("<") && trimmed.length > 2) {
      types[i] = "centered";
      inDialogueBlock = false;
      prevNonEmptyType = "centered";
      continue;
    }

    // 2. Forced scene heading: .HEADING
    if (trimmed.startsWith(".") && !trimmed.startsWith("..")) {
      types[i] = "scene_heading";
      inDialogueBlock = false;
      prevNonEmptyType = "scene_heading";
      continue;
    }

    // 3. Natural scene heading: INT., EXT., etc.
    if (RE_SCENE_HEADING.test(trimmed)) {
      types[i] = "scene_heading";
      inDialogueBlock = false;
      prevNonEmptyType = "scene_heading";
      continue;
    }

    // 4. Forced transition: >TRANSITION
    if (trimmed.startsWith(">") && !trimmed.endsWith("<")) {
      types[i] = "transition";
      inDialogueBlock = false;
      prevNonEmptyType = "transition";
      continue;
    }

    // 5. Natural transition: CUT TO:, FADE OUT., etc.
    if (RE_TRANSITION_NATURAL.test(trimmed)) {
      types[i] = "transition";
      inDialogueBlock = false;
      prevNonEmptyType = "transition";
      continue;
    }

    // 6. Parenthetical: (delivery)
    if (RE_PARENTHETICAL.test(trimmed) && (inDialogueBlock || ["character", "dialogue", "parenthetical"].includes(prevNonEmptyType))) {
      types[i] = "parenthetical";
      inDialogueBlock = true;
      prevNonEmptyType = "parenthetical";
      continue;
    }

    // 7. Dialogue: continues across multiple lines after character or parenthetical
    if (inDialogueBlock && ["character", "parenthetical", "dialogue"].includes(prevNonEmptyType)) {
      types[i] = "dialogue";
      prevNonEmptyType = "dialogue";
      continue;
    }

    // 8. Character cue: ALL CAPS name preceded by blank line or scene heading
    const cleanLetters = trimmed.replace(/[^A-Za-z]/g, "");
    const isAllCaps = trimmed === trimmed.toUpperCase();
    if (
      isAllCaps &&
      cleanLetters.length >= 2 &&
      !RE_SCENE_HEADING.test(trimmed) &&
      !RE_TRANSITION_NATURAL.test(trimmed) &&
      RE_CHARACTER.test(trimmed)
    ) {
      types[i] = "character";
      inDialogueBlock = true;
      prevNonEmptyType = "character";
      continue;
    }

    // 9. Default fallback: Action description
    types[i] = "action";
    inDialogueBlock = false;
    prevNonEmptyType = "action";
  }

  return types;
}

// ---------------------------------------------------------------------------
// StateField for Memoized Line Types (Instant O(1) Lookups)
// ---------------------------------------------------------------------------

export const parsedLineTypesField = StateField.define({
  create(state) {
    const forced = state.field(lineTypeField, false) || new Map();
    return parseDocumentLineTypes(state.doc, forced);
  },
  update(types, tr) {
    if (tr.docChanged || tr.effects.some((e) => e.is(setLineTypeEffect))) {
      const forced = tr.state.field(lineTypeField, false) || new Map();
      return parseDocumentLineTypes(tr.state.doc, forced);
    }
    return types;
  },
});

/**
 * Get element type for a specific line number (1-indexed).
 */
export function getLineType(state, lineNo) {
  try {
    const types = state.field(parsedLineTypesField, false);
    if (types && types[lineNo]) {
      return types[lineNo];
    }
  } catch {
    // fallback if field not initialized
  }

  const forced = state.field(lineTypeField, false)?.get(lineNo);
  if (forced) return forced;

  const doc = state.doc;
  if (lineNo >= 1 && lineNo <= doc.lines) {
    const text = doc.line(lineNo).text;
    return classifyLine(text, lineNo > 1 ? "action" : "scene_heading");
  }
  return "action";
}

/** Legacy single-line classifier kept for backward compatibility */
export function classifyLine(text, prevType) {
  const trimmed = text.trim();
  if (!trimmed) return "action";
  if (trimmed.startsWith(">") && trimmed.endsWith("<") && trimmed.length > 2) return "centered";
  if (trimmed.startsWith(".") && !trimmed.startsWith("..")) return "scene_heading";
  if (RE_SCENE_HEADING.test(trimmed)) return "scene_heading";
  if (trimmed.startsWith(">")) return "transition";
  if (RE_TRANSITION_NATURAL.test(trimmed)) return "transition";
  if (RE_PARENTHETICAL.test(trimmed) && ["character", "dialogue", "parenthetical"].includes(prevType)) return "parenthetical";
  if (["character", "parenthetical", "dialogue"].includes(prevType) && trimmed.length > 0) return "dialogue";
  const isAllCaps = trimmed === trimmed.toUpperCase();
  if (isAllCaps && trimmed.replace(/[^A-Za-z]/g, "").length >= 2 && !RE_SCENE_HEADING.test(trimmed) && RE_CHARACTER.test(trimmed)) {
    return "character";
  }
  return "action";
}

// ---------------------------------------------------------------------------
// Decoration ViewPlugin — adds CSS class decorations to each line
// ---------------------------------------------------------------------------

function buildDecorations(view) {
  const decorations = [];
  const state = view.state;
  const types = state.field(parsedLineTypesField, false) || [];

  for (const { from, to } of view.visibleRanges) {
    let lineNo = state.doc.lineAt(from).number;
    const lastLine = state.doc.lineAt(to).number;

    while (lineNo <= lastLine) {
      const lineObj = state.doc.line(lineNo);
      const type = types[lineNo] || getLineType(state, lineNo);
      const cls = TYPE_CLASS[type] || "fountain-action";

      // Add visual page break divider every 54 screenplay lines
      if (lineNo > 1 && lineNo % 54 === 1) {
        const pageNum = Math.floor(lineNo / 54) + 1;
        decorations.push(
          Decoration.widget({
            widget: new PageBreakWidget(pageNum),
            side: -1,
          }).range(lineObj.from)
        );
      }

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
      if (
        update.docChanged ||
        update.viewportChanged ||
        update.startState.field(lineTypeField) !== update.state.field(lineTypeField) ||
        update.startState.field(parsedLineTypesField, false) !== update.state.field(parsedLineTypesField, false)
      ) {
        this.decorations = buildDecorations(update.view);
      }
    }
  },
  { decorations: (v) => v.decorations }
);

// ---------------------------------------------------------------------------
// Auto-uppercase transformation for Scene Headings and Character cues
// ---------------------------------------------------------------------------

export const autoUppercase = EditorView.updateListener.of((update) => {
  if (!update.docChanged) return;

  const changes = [];
  update.changes.iterChangedRanges((_fromA, _toA, fromB, toB) => {
    const startLine = update.state.doc.lineAt(fromB).number;
    const endLine = update.state.doc.lineAt(toB).number;
    for (let ln = startLine; ln <= endLine; ln++) {
      const type = getLineType(update.state, ln);
      if (type === "scene_heading" || type === "character" || type === "transition") {
        const lineObj = update.state.doc.line(ln);
        const upper = lineObj.text.toUpperCase();
        if (upper !== lineObj.text) {
          changes.push({ from: lineObj.from, to: lineObj.to, insert: upper });
        }
      }
    }
  });

  if (changes.length === 0) return;

  update.view.dispatch({
    changes,
    annotations: Transaction.addToHistory.of(false),
  });
});

// ---------------------------------------------------------------------------
// Keyboard Handlers: Tab (Cycle), Enter (Smart Flow)
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
  const lineObj = state.doc.lineAt(sel.head);
  const currentType = getLineType(state, lineObj.number);
  const trimmed = lineObj.text.trim();

  // If hitting Enter on an empty line while inside dialogue, break cleanly to Action
  if (currentType === "dialogue" && !trimmed) {
    view.dispatch({
      effects: setLineTypeEffect.of({ line: lineObj.number, type: "action" }),
    });
  }

  // Insert standard newline
  view.dispatch(state.replaceSelection("\n"));
  return true;
}

export function setSpecificLineType(view, targetType) {
  const { state } = view;
  const sel = state.selection.main;
  const lineNo = state.doc.lineAt(sel.head).number;
  view.dispatch({
    effects: setLineTypeEffect.of({ line: lineNo, type: targetType }),
  });
  return true;
}

export function toggleUppercaseCurrentLine(view) {
  const { state } = view;
  const sel = state.selection.main;
  const lineObj = state.doc.lineAt(sel.head);
  const upper = lineObj.text.toUpperCase();
  if (upper !== lineObj.text) {
    view.dispatch({
      changes: { from: lineObj.from, to: lineObj.to, insert: upper },
    });
  }
  return true;
}

// ---------------------------------------------------------------------------
// Combined extension export
// ---------------------------------------------------------------------------

export const fountainExtension = [
  lineTypeField,
  parsedLineTypesField,
  fountainDecorations,
  autoUppercase,
  keymap.of([
    { key: "Tab", run: cycleType },
    { key: "Enter", run: smartEnter },
    { key: "Ctrl-Alt-1", run: (v) => setSpecificLineType(v, "scene_heading") },
    { key: "Ctrl-Alt-2", run: (v) => setSpecificLineType(v, "action") },
    { key: "Ctrl-Alt-3", run: (v) => setSpecificLineType(v, "character") },
    { key: "Ctrl-Alt-4", run: (v) => setSpecificLineType(v, "dialogue") },
    { key: "Ctrl-Alt-5", run: (v) => setSpecificLineType(v, "parenthetical") },
    { key: "Ctrl-Alt-6", run: (v) => setSpecificLineType(v, "transition") },
    { key: "Ctrl-Alt-7", run: (v) => setSpecificLineType(v, "centered") },
    { key: "Ctrl-Shift-u", run: toggleUppercaseCurrentLine },
  ]),
];
