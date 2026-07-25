import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { listScripts, createScript, deleteScript, uploadScriptFile } from "../api.js";

export default function ScriptList() {
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("updated");

  // Modal State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    setError(null);
    listScripts()
      .then(setScripts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  // New blank script
  const handleNew = async () => {
    try {
      const script = await createScript("Untitled Script");
      navigate(`/scripts/${script.id}`);
    } catch (e) {
      alert("Failed to create script: " + e.message);
    }
  };

  // Delete script
  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this screenplay?")) return;
    try {
      await deleteScript(id);
      load();
    } catch (e) {
      alert("Failed to delete: " + e.message);
    }
  };

  // Upload handler
  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select or drop a script file.");
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      const created = await uploadScriptFile(uploadFile, uploadTitle);
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadTitle("");
      navigate(`/scripts/${created.id}`);
    } catch (err) {
      setUploadError("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setUploadFile(file);
      if (!uploadTitle) {
        setUploadTitle(file.name.rsplit ? file.name.rsplit(".", 1)[0] : file.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  // Filtered & Sorted scripts
  const filteredScripts = useMemo(() => {
    let result = scripts.filter((s) =>
      s.title.toLowerCase().includes(search.toLowerCase())
    );

    if (sortBy === "updated") {
      result.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    } else if (sortBy === "title") {
      result.sort((a, b) => a.title.localeCompare(b.title));
    } else if (sortBy === "scenes") {
      result.sort((a, b) => (b.scene_count || 0) - (a.scene_count || 0));
    }

    return result;
  }, [scripts, search, sortBy]);

  // Overall Statistics
  const totalScenes = useMemo(
    () => scripts.reduce((acc, s) => acc + (s.scene_count || 0), 0),
    [scripts]
  );
  const totalPages = useMemo(
    () => scripts.reduce((acc, s) => acc + (s.estimated_pages || 0), 0),
    [scripts]
  );
  const totalCharacters = useMemo(
    () => scripts.reduce((acc, s) => acc + (s.character_count || 0), 0),
    [scripts]
  );

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">📄 Screenplay Dashboard</h1>
          <p className="dashboard-subtitle">
            Manage, upload, edit, and analyze your screenwriting projects.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button className="btn btn-primary" onClick={handleNew}>
            + New Blank Script
          </button>
          <button className="btn" onClick={() => setShowUploadModal(true)}>
            ⚡ Upload Script File
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Scripts</div>
          <div className="value">{scripts.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Scenes</div>
          <div className="value" style={{ color: "#4ecdc4" }}>{totalScenes}</div>
        </div>
        <div className="stat-card">
          <div className="label">Estimated Pages</div>
          <div className="value" style={{ color: "#ff85a1" }}>~{Math.round(totalPages)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Characters Discovered</div>
          <div className="value" style={{ color: "#a78bfa" }}>{totalCharacters}</div>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="controls-bar">
        <input
          className="search-input"
          placeholder="🔍 Search scripts by title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="search-input"
          style={{ flex: "none", width: "180px" }}
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="updated">Sort by Last Updated</option>
          <option value="title">Sort by Title</option>
          <option value="scenes">Sort by Scene Count</option>
        </select>
      </div>

      {/* State Messages */}
      {loading && <p style={{ color: "#94a3b8", padding: "2rem 0" }}>Loading dashboard scripts…</p>}
      {error && <p style={{ color: "#f87171", padding: "1rem 0" }}>Error: {error}</p>}

      {!loading && filteredScripts.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "4rem 2rem",
            background: "#0f172a",
            borderRadius: "12px",
            border: "1px dashed #334155",
            marginTop: "1rem",
          }}
        >
          <h3 style={{ fontSize: "1.2rem", color: "#f8fafc", marginBottom: "0.5rem" }}>
            No Screenplays Found
          </h3>
          <p style={{ color: "#94a3b8", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
            {search ? "No scripts match your search criteria." : "Get started by creating a new script or uploading an existing Fountain/TXT/Word file."}
          </p>
          <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
            <button className="btn btn-primary" onClick={handleNew}>
              + Create Script
            </button>
            <button className="btn" onClick={() => setShowUploadModal(true)}>
              ⚡ Upload File
            </button>
          </div>
        </div>
      )}

      {/* Script Cards Grid */}
      <div className="scripts-grid">
        {filteredScripts.map((s) => (
          <div
            key={s.id}
            className="script-card"
            onClick={() => navigate(`/scripts/${s.id}`)}
          >
            <div>
              <div className="script-card-header">
                <h2 className="script-card-title">{s.title}</h2>
                <span className="badge">
                  {s.scene_count || 0} scene{(s.scene_count || 0) === 1 ? "" : "s"}
                </span>
              </div>

              <div className="script-card-meta">
                <span>📄 ~{s.estimated_pages || 0} pages</span>
                <span>🎭 {s.character_count || 0} characters</span>
              </div>
            </div>

            <div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "#64748b",
                  marginBottom: "1rem",
                }}
              >
                Updated {new Date(s.updated_at).toLocaleDateString()} at {new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>

              <div className="script-card-actions" onClick={(e) => e.stopPropagation()}>
                <button
                  className="btn btn-primary"
                  style={{ padding: "0.3rem 0.7rem", fontSize: "0.8rem" }}
                  onClick={() => navigate(`/scripts/${s.id}`)}
                >
                  ✏️ Edit
                </button>
                <button
                  className="btn"
                  style={{ padding: "0.3rem 0.7rem", fontSize: "0.8rem" }}
                  onClick={() => navigate(`/scripts/${s.id}/diagram`)}
                >
                  🕸️ Map
                </button>
                <button
                  className="btn"
                  style={{ padding: "0.3rem 0.7rem", fontSize: "0.8rem" }}
                  onClick={() => navigate(`/scripts/${s.id}/outline`)}
                >
                  📋 Outline
                </button>
                <button
                  className="btn"
                  style={{ padding: "0.3rem 0.7rem", fontSize: "0.8rem" }}
                  onClick={() => navigate(`/scripts/${s.id}/analysis`)}
                >
                  📊 Analysis
                </button>
                <button
                  className="btn btn-danger"
                  style={{ padding: "0.3rem 0.7rem", fontSize: "0.8rem", marginLeft: "auto" }}
                  onClick={(e) => handleDelete(e, s.id)}
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Script Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: "#f8fafc" }}>
              ⚡ Upload Screenplay File
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "0.25rem" }}>
              Upload your script in <strong>.fountain</strong>, <strong>.txt</strong>, or <strong>.docx</strong> format.
            </p>

            <form onSubmit={handleUploadSubmit}>
              {/* Dropzone */}
              <div
                className={`dropzone ${isDragOver ? "active" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => document.getElementById("script-file-input").click()}
              >
                <input
                  id="script-file-input"
                  type="file"
                  accept=".fountain,.txt,.docx"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      const file = e.target.files[0];
                      setUploadFile(file);
                      if (!uploadTitle) {
                        setUploadTitle(file.name.replace(/\.[^/.]+$/, ""));
                      }
                    }
                  }}
                />
                <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📁</div>
                {uploadFile ? (
                  <div>
                    <span style={{ color: "#38bdf8", fontWeight: 600 }}>{uploadFile.name}</span>
                    <span style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block" }}>
                      ({Math.round(uploadFile.size / 1024)} KB) — Click or drop to change
                    </span>
                  </div>
                ) : (
                  <div>
                    <span style={{ color: "#f8fafc", fontWeight: 500 }}>
                      Drag and drop your script file here, or click to browse
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "#64748b", display: "block", marginTop: "0.3rem" }}>
                      Supports Fountain (.fountain), Plain Text (.txt), Word (.docx)
                    </span>
                  </div>
                )}
              </div>

              {/* Title Input */}
              <div style={{ marginBottom: "1.25rem" }}>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.4rem" }}>
                  Script Title (Optional)
                </label>
                <input
                  className="search-input"
                  style={{ width: "100%" }}
                  placeholder="e.g. Inception (Final Draft)"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                />
              </div>

              {uploadError && (
                <p style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: "1rem" }}>
                  {uploadError}
                </p>
              )}

              <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
                <button
                  className="btn"
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit" disabled={uploading}>
                  {uploading ? "Parsing & Uploading…" : "Upload Script"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
