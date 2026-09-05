import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import FountainEditor from "../editor/FountainEditor.jsx";
import WordRuler from "../components/WordRuler.jsx";
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
  { id: "parenthetical", label: "Parenthetical", shortcut: "Ctrl+Alt+5", prefix: "(" },
  { id: "dialogue", label: "Dialogue", shortcut: "Ctrl+Alt+4", prefix: "" },
  { id: "transition", label: "Transition", shortcut: "Ctrl+Alt+6", prefix: "CUT TO:" },
  { id: "centered", label: "Centered", shortcut: "Ctrl+Alt+7", prefix: "> ", suffix: " <" },
];

export default function ScriptEditor() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [fountainText, setFountainText] = useState("");
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [error, setError] = useState(null);
  const [isDirty, setIsDirty] = useState(false);

  // Glossary Drawer & Ribbon State
  const [showGlossary, setShowGlossary] = useState(false);
  const [activeTab, setActiveTab] = useState("elements"); // "home" | "elements" | "view"
  const [showRuler, setShowRuler] = useState(true);
  const [showLineNumbers, setShowLineNumbers] = useState(false);

  // Zoom & Stats state
  const [zoom, setZoom] = useState(1);
  const [stats, setStats] = useState({ lineNo: 1, lineType: "action", words: 0, lines: 1 });
  const [editorView, setEditorView] = useState(null);

  const textRef = useRef("");
  const autoSaveTimerRef = useRef(null);

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
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [id]);

  const performSave = async (silent = false) => {
    if (!silent) setStatus("Saving…");
    try {
      await importFountain(id, textRef.current);
      setIsDirty(false);
      setStatus(silent ? "Autosaved ✓" : "Saved ✓");
      setTimeout(() => setStatus(""), 2000);
      return true;
    } catch (e) {
      setStatus("Error: " + (e.response?.data?.detail || e.message));
      return false;
    }
  };

  const handleEditorChange = useCallback(
    (text) => {
      textRef.current = text;
      setIsDirty(true);

      // Debounced 1.5s autosave
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      autoSaveTimerRef.current = setTimeout(() => {
        performSave(true);
      }, 1500);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [id]
  );

  const handleCursorChange = useCallback((cursorStats) => {
    setStats(cursorStats);
  }, []);

  const handleManualSave = async () => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    await performSave(false);
  };

  const handleSafeNavigate = async (path) => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    if (isDirty) {
      setStatus("Saving before leaving…");
      await performSave(true);
    }
    navigate(path);
  };

  const handleExportPdf = async () => {
    setStatus("Exporting PDF…");
    try {
      await performSave(true);
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
      await performSave(true);
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

  const handleInsertMarkup = (symbolLeft, symbolRight = symbolLeft) => {
    if (!editorView) return;
    const { state } = editorView;
    const sel = state.selection.main;
    const selectedText = state.sliceDoc(sel.from, sel.to);
    const wrapped = `${symbolLeft}${selectedText || "text"}${symbolRight}`;
    editorView.dispatch({
      changes: { from: sel.from, to: sel.to, insert: wrapped },
      selection: {
        anchor: sel.from + symbolLeft.length,
        head: sel.from + symbolLeft.length + (selectedText.length || 4),
      },
    });
    editorView.focus();
  };

  const handleInsertPrefix = (prefix) => {
    if (!editorView) return;
    const { state } = editorView;
    const sel = state.selection.main;
    const lineObj = state.doc.lineAt(sel.head);
    editorView.dispatch({
      changes: { from: lineObj.from, to: lineObj.from, insert: prefix },
    });
    editorView.focus();
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      handleManualSave();
    }
  };

  const totalPages = Math.max(1, Math.ceil((stats.lines || 1) / 54));

  if (error) {
    return (
      <div className="dashboard-container">
        <p style={{ color: "#f87171", padding: "2rem 0" }}>{error}</p>
        <button className="btn" onClick={() => handleSafeNavigate("/")}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="editor-layout" onKeyDown={handleKeyDown}>
      {/* Top Header Bar */}
      <div className="editor-toolbar">
        <button
          className="btn"
          onClick={() => handleSafeNavigate("/")}
          style={{ padding: "0.35rem 0.75rem", fontSize: "0.85rem" }}
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

        <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
          <button
            className={`btn ${isDirty ? "btn-primary" : ""}`}
            onClick={handleManualSave}
            title="Save Script (Ctrl+S)"
          >
            💾 Save {isDirty ? "●" : ""}
          </button>
          <button className="btn" onClick={handleExportPdf} title="Export PDF Document">
            📄 Export PDF
          </button>
          <button className="btn" onClick={handleExportWord} title="Export Microsoft Word (.docx)">
            📝 Export Word
          </button>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          <button
            className="btn"
            style={{ background: "#1e293b", borderColor: "#38bdf8", color: "#38bdf8" }}
            onClick={() => setShowGlossary(true)}
            title="Screenwriting Glossary & Guidelines"
          >
            📖 Guide
          </button>
          <button className="btn" onClick={() => handleSafeNavigate(`/scripts/${id}/characters`)}>
            🎭 Characters
          </button>
          <button className="btn" onClick={() => handleSafeNavigate(`/scripts/${id}/diagram`)}>
            🕸️ Map
          </button>
          <button className="btn" onClick={() => handleSafeNavigate(`/scripts/${id}/outline`)}>
            📋 Outline
          </button>
          <button className="btn" onClick={() => handleSafeNavigate(`/scripts/${id}/analysis`)}>
            📊 Analysis
          </button>
        </div>

        {status && (
          <span style={{ fontSize: "0.8rem", color: "#38bdf8", fontWeight: 600, marginLeft: "0.5rem" }}>
            {status}
          </span>
        )}
      </div>

      {/* Screenplay Ribbon Bar */}
      <div className="word-ribbon-container">
        {/* Ribbon Tab Selectors */}
        <div className="ribbon-tabs">
          <button
            className={`ribbon-tab ${activeTab === "elements" ? "active" : ""}`}
            onClick={() => setActiveTab("elements")}
          >
            🎭 Screenplay Elements
          </button>
          <button
            className={`ribbon-tab ${activeTab === "home" ? "active" : ""}`}
            onClick={() => setActiveTab("home")}
          >
            ✏️ Text Formatting & Editing
          </button>
          <button
            className={`ribbon-tab ${activeTab === "view" ? "active" : ""}`}
            onClick={() => setActiveTab("view")}
          >
            👁️ View & Ruler Options
          </button>
        </div>

        {/* Ribbon Tab Content Panes */}
        <div className="ribbon-content">
          {activeTab === "elements" && (
            <div className="ribbon-group">
              <span className="ribbon-label">Screenplay Format (Tab to Cycle):</span>
              <div className="ribbon-buttons">
                {ELEMENT_TYPES.map((elem) => {
                  const isActive = stats.lineType === elem.id;
                  return (
                    <button
                      key={elem.id}
                      className={`ribbon-btn ${isActive ? "active" : ""}`}
                      onClick={() => handleSetElementType(elem.id)}
                      title={`${elem.label} (${elem.shortcut})`}
                    >
                      {elem.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === "home" && (
            <div className="ribbon-group" style={{ gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span className="ribbon-label">Font:</span>
                <span className="ribbon-font-badge">Courier Prime 12pt</span>
              </div>

              <div className="ribbon-divider" />

              <div style={{ display: "flex", gap: "0.3rem" }}>
                <button
                  className="ribbon-btn"
                  style={{ fontWeight: "bold" }}
                  onClick={() => handleInsertMarkup("**")}
                  title="Bold (**text**)"
                >
                  B
                </button>
                <button
                  className="ribbon-btn"
                  style={{ fontStyle: "italic" }}
                  onClick={() => handleInsertMarkup("*")}
                  title="Italic (*text*)"
                >
                  I
                </button>
                <button
                  className="ribbon-btn"
                  style={{ textDecoration: "underline" }}
                  onClick={() => handleInsertMarkup("_")}
                  title="Underline (_text_)"
                >
                  U
                </button>
                <button
                  className="ribbon-btn"
                  onClick={() => handleInsertMarkup("> ", " <")}
                  title="Centered Text (> text <)"
                >
                  Centered
                </button>
                <button
                  className="ribbon-btn"
                  onClick={handleToggleUppercase}
                  title="Uppercase Current Line (Ctrl+Shift+U)"
                >
                  AA
                </button>
              </div>

              <div className="ribbon-divider" />

              <div style={{ display: "flex", gap: "0.3rem" }}>
                <button
                  className="ribbon-btn"
                  onClick={() => handleInsertPrefix("INT. ")}
                  title="Insert INT. prefix"
                >
                  + INT.
                </button>
                <button
                  className="ribbon-btn"
                  onClick={() => handleInsertPrefix("EXT. ")}
                  title="Insert EXT. prefix"
                >
                  + EXT.
                </button>
                <button
                  className="ribbon-btn"
                  onClick={() => handleInsertPrefix("CUT TO: ")}
                  title="Insert CUT TO: prefix"
                >
                  + CUT TO:
                </button>
                <button
                  className="ribbon-btn"
                  onClick={() => handleInsertPrefix("(")}
                  title="Insert Parenthetical"
                >
                  + (
                </button>
              </div>
            </div>
          )}

          {activeTab === "view" && (
            <div className="ribbon-group" style={{ gap: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <button
                  className={`ribbon-btn ${showRuler ? "active" : ""}`}
                  onClick={() => setShowRuler(!showRuler)}
                >
                  📏 {showRuler ? "Hide Ruler" : "Show Ruler"}
                </button>
                <button
                  className={`ribbon-btn ${showLineNumbers ? "active" : ""}`}
                  onClick={() => setShowLineNumbers(!showLineNumbers)}
                >
                  🔢 {showLineNumbers ? "Hide Line Numbers" : "Show Line Numbers"}
                </button>
              </div>

              <div className="ribbon-divider" />

              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span className="ribbon-label">Zoom Level:</span>
                {[0.75, 0.9, 1, 1.25, 1.5].map((z) => (
                  <button
                    key={z}
                    className={`ribbon-btn ${zoom === z ? "active" : ""}`}
                    onClick={() => setZoom(z)}
                  >
                    {Math.round(z * 100)}%
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Screenplay Paper Workspace */}
      <div className="editor-desk">
        {loading ? (
          <p style={{ color: "#94a3b8", padding: "4rem", textAlign: "center" }}>
            Loading screenplay document…
          </p>
        ) : (
          <div
            className="paper-wrapper"
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: "top center",
              transition: "transform 0.15s ease-out",
            }}
          >
            {/* Horizontal Screenplay Ruler */}
            {showRuler && <WordRuler activeType={stats.lineType} />}

            {/* Pristine 8.5" x 11" Screenplay Paper Document */}
            <FountainEditor
              initialDoc={fountainText}
              onChange={handleEditorChange}
              onCursorChange={handleCursorChange}
              onInitView={setEditorView}
              zoom={1}
              showLineNumbers={showLineNumbers}
            />
          </div>
        )}
      </div>

      {/* Screenplay Professional Status Bar */}
      <div className="word-status-bar">
        <div className="status-left">
          <span>
            PAGE <strong style={{ color: "#38bdf8" }}>{Math.ceil(stats.lineNo / 54) || 1}</strong> OF {totalPages}
          </span>
          <span className="status-divider">|</span>
          <span>{stats.words} WORDS</span>
          <span className="status-divider">|</span>
          <span>{stats.lines} LINES</span>
          <span className="status-divider">|</span>
          <span>
            ELEMENT: <strong style={{ color: "#38bdf8", textTransform: "uppercase" }}>{stats.lineType.replace("_", " ")}</strong>
          </span>
        </div>

        <div className="status-center">
          <span>
            <strong>Tab</strong>: Cycle &nbsp;•&nbsp; <strong>Enter</strong>: Smart Flow &nbsp;•&nbsp; <strong>Ctrl+Alt+1..7</strong>: Elements
          </span>
        </div>

        <div className="status-right">
          <span>ZOOM: {Math.round(zoom * 100)}%</span>
          <button
            className="status-zoom-btn"
            onClick={() => setZoom((z) => Math.max(0.6, Math.round((z - 0.1) * 10) / 10))}
            title="Zoom Out"
          >
            -
          </button>
          <button
            className="status-zoom-btn"
            onClick={() => setZoom((z) => Math.min(2.0, Math.round((z + 0.1) * 10) / 10))}
            title="Zoom In"
          >
            +
          </button>
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
