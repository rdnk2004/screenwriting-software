import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import FountainEditor from "../editor/FountainEditor.jsx";
import { setSpecificLineType, toggleUppercaseCurrentLine } from "../editor/fountainMode.js";
import {
  getScript,
  updateScriptTitle,
  importFountain,
  exportFountain,
  exportPdf,
  exportWord,
} from "../api.js";

import GlossaryDrawer from "../components/GlossaryDrawer.jsx";

const ELEMENT_TYPES = [
  { id: "scene_heading", label: "Scene Heading", shortcut: "Ctrl+Alt+1", prefix: "INT. " },
  { id: "action", label: "Action", shortcut: "Ctrl+Alt+2", prefix: "" },
  { id: "character", label: "Character", shortcut: "Ctrl+Alt+3", prefix: "" },
  { id: "dialogue", label: "Dialogue", shortcut: "Ctrl+Alt+4", prefix: "" },
  { id: "parenthetical", label: "Parenthetical", shortcut: "Ctrl+Alt+5", prefix: "(" },
  { id: "transition", label: "Transition", shortcut: "Ctrl+Alt+6", prefix: "CUT TO:" },
];

export default function ScriptEditor() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [fountainText, setFountainText] = useState("");
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [error, setError] = useState(null);

  // Glossary Drawer State
  const [showGlossary, setShowGlossary] = useState(false);

  // Zoom & Stats state
  const [zoom, setZoom] = useState(1);
  const [stats, setStats] = useState({ lineNo: 1, lineType: "action", words: 0, lines: 1 });
  const [editorView, setEditorView] = useState(null);

  const textRef = useRef("");

  // Load script
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      getScript(id),
      exportFountain(id).catch(() => ""),
    ])
      .then(([script, text]) => {
        if (!active) return;
        setTitle(script.title);
        setFountainText(text || "");
        textRef.current = text || "";
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError("Script not found or failed to load.");
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [id]);

  const handleEditorChange = useCallback((text) => {
    textRef.current = text;
  }, []);

  const handleCursorChange = useCallback((cursorStats) => {
    setStats(cursorStats);
  }, []);

  const handleSave = async () => {
    setStatus("Saving…");
    try {
      await importFountain(id, textRef.current);
      setStatus("Saved ✓");
      setTimeout(() => setStatus(""), 2000);
    } catch (e) {
      setStatus("Error: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleExportPdf = async () => {
    setStatus("Exporting PDF…");
    try {
      await importFountain(id, textRef.current);
      await exportPdf(id, `${title || "script"}.pdf`);
      setStatus("Exported PDF ✓");
      setTimeout(() => setStatus(""), 2000);
    } catch (e) {
      setStatus("Export PDF failed: " + e.message);
    }
  };

  const handleExportWord = async () => {
    setStatus("Exporting Word…");
    try {
      await importFountain(id, textRef.current);
      await exportWord(id, `${title || "script"}.docx`);
      setStatus("Exported Word ✓");
      setTimeout(() => setStatus(""), 2000);
    } catch (e) {
      setStatus("Export Word failed: " + e.message);
    }
  };

  const handleTitleBlur = async () => {
    try {
      await updateScriptTitle(id, title);
    } catch {
      /* silent */
    }
  };

  // Switch element type via toolbar button
  const handleSetElementType = (typeId) => {
    if (editorView) {
      setSpecificLineType(editorView, typeId);
      editorView.focus();
    }
  };

  const handleToggleUppercase = () => {
    if (editorView) {
      toggleUppercaseCurrentLine(editorView);
      editorView.focus();
    }
  };

  const handleInsertMarkup = (symbol) => {
    if (!editorView) return;
    const { state } = editorView;
    const sel = state.selection.main;
    const selectedText = state.sliceDoc(sel.from, sel.to);
    const wrapped = `${symbol}${selectedText || "text"}${symbol}`;
    editorView.dispatch({
      changes: { from: sel.from, to: sel.to, insert: wrapped },
    });
    editorView.focus();
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      handleSave();
    }
  };

  if (error) {
    return (
      <div className="dashboard-container">
        <p style={{ color: "#f87171", padding: "2rem 0" }}>{error}</p>
        <button className="btn" onClick={() => navigate("/")}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="editor-layout" onKeyDown={handleKeyDown}>
      {/* Top Application Toolbar */}
      <div className="editor-toolbar">
        <button
          className="btn"
          onClick={() => navigate("/")}
          style={{ padding: "0.4rem 0.8rem" }}
        >
          ← Dashboard
        </button>

        <input
          className="script-title-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleTitleBlur}
          placeholder="Script title"
          aria-label="Script title"
        />

        <button className="btn btn-primary" onClick={handleSave}>
          💾 Save
        </button>

        <button className="btn" onClick={handleExportPdf}>
          📄 Export PDF
        </button>

        <button className="btn" onClick={handleExportWord}>
          📝 Export Word
        </button>

        <button
          className="btn"
          style={{ background: "#1e293b", borderColor: "#38bdf8", color: "#38bdf8" }}
          onClick={() => setShowGlossary(true)}
        >
          📖 Screenwriting Guide
        </button>

        <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem" }}>
          <button className="btn" onClick={() => navigate(`/scripts/${id}/characters`)}>
            🎭 Characters
          </button>
          <button className="btn" onClick={() => navigate(`/scripts/${id}/diagram`)}>
            🕸️ Map
          </button>
          <button className="btn" onClick={() => navigate(`/scripts/${id}/outline`)}>
            📋 Outline
          </button>
          <button className="btn" onClick={() => navigate(`/scripts/${id}/analysis`)}>
            📊 Analysis
          </button>
        </div>

        {status && <span style={{ fontSize: "0.8rem", color: "#38bdf8", fontWeight: 600 }}>{status}</span>}
      </div>

      {/* Quick Element & Formatting Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          padding: "0.5rem 1.25rem",
          background: "#1e293b",
          borderBottom: "1px solid #334155",
          flexWrap: "wrap",
          fontSize: "0.8rem",
        }}
      >
        <span style={{ color: "#94a3b8", fontWeight: 600, marginRight: "0.4rem" }}>
          Format Element:
        </span>

        {ELEMENT_TYPES.map((elem) => {
          const isActive = stats.lineType === elem.id;
          return (
            <button
              key={elem.id}
              className={`btn ${isActive ? "btn-primary" : ""}`}
              style={{
                padding: "0.25rem 0.6rem",
                fontSize: "0.78rem",
                borderRadius: "6px",
              }}
              onClick={() => handleSetElementType(elem.id)}
              title={elem.shortcut}
            >
              {elem.label}
            </button>
          );
        })}

        <div style={{ width: "1px", height: "20px", background: "#334155", margin: "0 0.5rem" }} />

        {/* Text Formatting Helpers */}
        <button
          className="btn"
          style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem", fontWeight: "bold" }}
          onClick={() => handleInsertMarkup("**")}
          title="Bold (**text**)"
        >
          B
        </button>

        <button
          className="btn"
          style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem", fontStyle: "italic" }}
          onClick={() => handleInsertMarkup("*")}
          title="Italic (*text*)"
        >
          I
        </button>

        <button
          className="btn"
          style={{ padding: "0.25rem 0.5rem", fontSize: "0.78rem" }}
          onClick={handleToggleUppercase}
          title="Uppercase (Ctrl+Shift+U)"
        >
          AA
        </button>

        {/* Zoom Controls */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span style={{ color: "#94a3b8", fontSize: "0.75rem" }}>Zoom:</span>
          {[0.8, 1, 1.2, 1.5].map((z) => (
            <button
              key={z}
              className={`btn ${zoom === z ? "btn-primary" : ""}`}
              style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
              onClick={() => setZoom(z)}
            >
              {Math.round(z * 100)}%
            </button>
          ))}
        </div>
      </div>

      {/* Screenplay Paper Area (Word-like Page Environment) */}
      <div className="editor-scroll">
        {loading ? (
          <p style={{ color: "#94a3b8", padding: "3rem", textAlign: "center" }}>
            Loading screenplay document…
          </p>
        ) : (
          <FountainEditor
            initialDoc={fountainText}
            onChange={handleEditorChange}
            onCursorChange={handleCursorChange}
            onInitView={setEditorView}
            zoom={zoom}
          />
        )}
      </div>

      {/* Bottom Status Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.4rem 1.25rem",
          background: "#0f172a",
          borderTop: "1px solid #1e293b",
          fontSize: "0.78rem",
          color: "#94a3b8",
        }}
      >
        <div style={{ display: "flex", gap: "1.25rem", alignItems: "center" }}>
          <span>
            Current Element: <strong style={{ color: "#38bdf8", textTransform: "capitalize" }}>{stats.lineType.replace("_", " ")}</strong>
          </span>
          <span>Line {stats.lineNo} of {stats.lines}</span>
          <span>{stats.words} Words</span>
          <span>~{Math.max(1, Math.ceil(stats.lines / 54))} Pages</span>
        </div>

        <div>
          <span style={{ color: "#64748b" }}>
            Shortcuts: <strong>Tab</strong> = Cycle &nbsp;|&nbsp; <strong>Enter</strong> = Smart Flow &nbsp;|&nbsp; <strong>Ctrl+Alt+1..6</strong> = Format Element &nbsp;|&nbsp; <strong>Ctrl+S</strong> = Save
          </span>
        </div>
      </div>

      {/* Screenwriting Guide & Glossary Drawer */}
      <GlossaryDrawer
        isOpen={showGlossary}
        onClose={() => setShowGlossary(false)}
        onInsertTerm={(snippet) => {
          if (editorView) {
            const { state } = editorView;
            const sel = state.selection.main;
            editorView.dispatch({
              changes: { from: sel.from, to: sel.to, insert: snippet },
            });
            editorView.focus();
            setStatus("Term inserted ✓");
            setTimeout(() => setStatus(""), 2000);
          }
        }}
      />
    </div>
  );
}
