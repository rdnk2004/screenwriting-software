import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listScripts, createScript, deleteScript } from "../api.js";

export default function ScriptList() {
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    listScripts()
      .then(setScripts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleNew = async () => {
    try {
      const script = await createScript("Untitled Script");
      navigate(`/scripts/${script.id}`);
    } catch (e) {
      alert("Failed to create script: " + e.message);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Delete this script?")) return;
    try {
      await deleteScript(id);
      load();
    } catch (e) {
      alert("Failed to delete: " + e.message);
    }
  };

  return (
    <div className="list-container">
      <h1>📄 My Scripts</h1>
      <div style={{ marginBottom: "1.5rem" }}>
        <button className="btn btn-primary" onClick={handleNew}>
          + New Script
        </button>
      </div>

      {loading && <p style={{ color: "#888" }}>Loading…</p>}
      {error && <p style={{ color: "#e55" }}>Error: {error}</p>}

      {!loading && scripts.length === 0 && (
        <p style={{ color: "#888" }}>No scripts yet. Create one above!</p>
      )}

      {scripts.map((s) => (
        <div
          key={s.id}
          className="script-item"
          onClick={() => navigate(`/scripts/${s.id}`)}
        >
          <span className="title">{s.title}</span>
          <span style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            <span className="date">
              {new Date(s.updated_at).toLocaleDateString()}
            </span>
            <button
              className="btn"
              style={{ padding: "0.2rem 0.6rem", fontSize: "0.75rem" }}
              onClick={(e) => handleDelete(e, s.id)}
            >
              Delete
            </button>
          </span>
        </div>
      ))}
    </div>
  );
}
