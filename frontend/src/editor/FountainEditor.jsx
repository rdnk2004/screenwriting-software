/**
 * FountainEditor.jsx
 *
 * A controlled CodeMirror 6 editor pre-configured with the Fountain extension.
 * Props:
 *   initialDoc  — initial Fountain text string
 *   onChange    — called with the full text whenever the document changes
 */
import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { history, historyKeymap } from "@codemirror/commands";
import { keymap as keymapFacet } from "@codemirror/view";
import { fountainExtension } from "./fountainMode.js";

export default function FountainEditor({ initialDoc = "", onChange }) {
  const containerRef = useRef(null);
  const viewRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const state = EditorState.create({
      doc: initialDoc,
      extensions: [
        history(),
        keymapFacet.of(historyKeymap),
        lineNumbers(),
        highlightActiveLine(),
        ...fountainExtension,
        EditorView.updateListener.of((update) => {
          if (update.docChanged && onChange) {
            onChange(update.state.doc.toString());
          }
        }),
        EditorView.theme({
          "&": { height: "100%" },
          ".cm-scroller": { overflow: "auto" },
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: containerRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // only mount once

  const loadedDocRef = useRef(initialDoc);

  // If initialDoc changes externally (e.g. after load), replace document
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (initialDoc !== loadedDocRef.current && current !== initialDoc) {
      loadedDocRef.current = initialDoc;
      view.dispatch({
        changes: { from: 0, to: current.length, insert: initialDoc },
      });
    }
  }, [initialDoc]);

  return (
    <div
      ref={containerRef}
      style={{ height: "100%", overflow: "auto" }}
    />
  );
}
