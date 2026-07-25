import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { history, historyKeymap } from "@codemirror/commands";
import { keymap as keymapFacet } from "@codemirror/view";
import { fountainExtension, getLineType } from "./fountainMode.js";

export default function FountainEditor({
  initialDoc = "",
  onChange,
  onCursorChange,
  onInitView,
  zoom = 1,
}) {
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
          if (onCursorChange) {
            const { state } = update.view;
            const sel = state.selection.main;
            const lineNo = state.doc.lineAt(sel.head).number;
            const lineType = getLineType(state, lineNo);
            const text = state.doc.toString();
            const words = text.trim() ? text.trim().split(/\s+/).length : 0;
            const lines = state.doc.lines;
            onCursorChange({ lineNo, lineType, words, lines });
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
    if (onInitView) onInitView(view);

    return () => {
      view.destroy();
      viewRef.current = null;
      if (onInitView) onInitView(null);
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
      style={{
        height: "100%",
        overflow: "auto",
        transform: `scale(${zoom})`,
        transformOrigin: "top center",
        transition: "transform 0.15s ease-out",
      }}
    />
  );
}
