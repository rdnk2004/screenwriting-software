import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import FountainEditor from "../editor/FountainEditor.jsx";
import {
  getScript,
  updateScriptTitle,
  importFountain,
  exportFountain,
  exportPdf,
  exportWord,
} from "../api.js";

export default function ScriptEditor() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [fountainText, setFountainText] = useState("");
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(""); // "Saving…" | "Saved" | error
  const [error, setError] = useState(null);

  // Ref to hold the latest editor text without causing re-renders
  const textRef = useRef("");

  // Load script: get detail (with title) and export to Fountain text
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      getScript(id),
      exportFountain(id).catch(() => "") // Fallback to empty text if no scenes exist yet
    ])
      .then(([script, text]) => {
        if (!active) return;
        setTitle(script.title);
        setFountainText(text || "");
        textRef.current = text || "";
        setLoading(false);
      })
      .catch((err) => {
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

  const handleKeyDown = (e) => {
    // Ctrl+S / Cmd+S to save
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      handleSave();
    }
  };

  if (error) {
    return (
      <div className="list-container">
        <p style={{ color: "#e55" }}>{error}</p>
        <button className="btn" onClick={() => navigate("/")}>
          ← Back
        </button>
      </div>
    );
  }

  return (
    <div className="editor-layout" onKeyDown={handleKeyDown}>
      <div className="editor-toolbar">
        <button
          className="btn"
          onClick={() => navigate("/")}
          style={{ padding: "0.3rem 0.8rem" }}
        >
          ← Scripts
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
          Save
        </button>

        <button className="btn" onClick={handleExportPdf}>
          Export PDF
        </button>

        <button className="btn" onClick={handleExportWord}>
          Export Word
        </button>

        <button
          className="btn"
          onClick={() => navigate(`/scripts/${id}/characters`)}
          style={{ marginLeft: "0.5rem" }}
        >
          🎭 Characters
        </button>

        <button
          className="btn"
          onClick={() => navigate(`/scripts/${id}/diagram`)}
        >
          🕸️ Map
        </button>

        <button
          className="btn"
          onClick={() => navigate(`/scripts/${id}/outline`)}
        >
          📋 Outline
        </button>

        <button
          className="btn"
          onClick={() => navigate(`/scripts/${id}/analysis`)}
        >
          📊 Analysis
        </button>

        {status && <span className="status">{status}</span>}

        <span className="status" style={{ marginLeft: 0 }}>
          Tab = cycle type &nbsp;|&nbsp; Ctrl+S = save
        </span>
      </div>

      <div className="editor-scroll">
        {loading ? (
          <p style={{ color: "#888", padding: "2rem" }}>Loading script…</p>
        ) : (
          <FountainEditor
            initialDoc={fountainText}
            onChange={handleEditorChange}
          />
        )}
      </div>
    </div>
  );
}
