import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getScript,
  listCharacters,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  extractCharacters,
} from "../api.js";

export default function ScriptCharacters() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [script, setScript] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState(null);

  // Form state
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    bio: "",
    motivation: "",
    arc_notes: "",
    voice_notes: "",
    image_url: "",
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const scriptData = await getScript(id);
      setScript(scriptData);
      const charList = await listCharacters(id);
      setCharacters(charList);
      if (charList.length > 0 && !selectedId) {
        setSelectedId(charList[0].id);
      }
    } catch (err) {
      setError("Failed to load script or characters: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const selectedChar = characters.find((c) => c.id === selectedId);

  useEffect(() => {
    if (selectedChar) {
      setFormData({
        name: selectedChar.name,
        bio: selectedChar.bio || "",
        motivation: selectedChar.motivation || "",
        arc_notes: selectedChar.arc_notes || "",
        voice_notes: selectedChar.voice_notes || "",
        image_url: selectedChar.image_url || "",
      });
      setIsEditing(false);
    }
  }, [selectedId, selectedChar]);

  const handleCreate = async () => {
    const name = prompt("Enter character name:");
    if (!name || !name.trim()) return;
    try {
      const created = await createCharacter({
        script: id,
        name: name.trim(),
      });
      const updatedList = await listCharacters(id);
      setCharacters(updatedList);
      setSelectedId(created.id);
    } catch (err) {
      alert("Failed to create character: " + err.message);
    }
  };

  const handleExtract = async () => {
    setExtracting(true);
    try {
      const extracted = await extractCharacters(id);
      setCharacters(extracted);
      if (extracted.length > 0) {
        setSelectedId(extracted[0].id);
      }
    } catch (err) {
      alert("Failed to extract characters: " + err.message);
    } finally {
      setExtracting(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!selectedId) return;
    try {
      const updated = await updateCharacter(selectedId, formData);
      const updatedList = await listCharacters(id);
      setCharacters(updatedList);
      setIsEditing(false);
    } catch (err) {
      alert("Failed to save character: " + err.message);
    }
  };

  const handleDelete = async () => {
    if (!selectedChar) return;
    if (!confirm(`Delete character ${selectedChar.name}?`)) return;
    try {
      await deleteCharacter(selectedId);
      const updatedList = await listCharacters(id);
      setCharacters(updatedList);
      setSelectedId(updatedList.length > 0 ? updatedList[0].id : null);
    } catch (err) {
      alert("Failed to delete character: " + err.message);
    }
  };

  if (loading) {
    return <p style={{ padding: "2rem", color: "#888" }}>Loading characters…</p>;
  }

  if (error) {
    return (
      <div className="list-container">
        <p style={{ color: "#e55" }}>{error}</p>
        <button className="btn" onClick={() => navigate(`/scripts/${id}`)}>
          ← Back to Editor
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Header toolbar */}
      <div className="editor-toolbar">
        <button
          className="btn"
          onClick={() => navigate(`/scripts/${id}`)}
          style={{ padding: "0.3rem 0.8rem" }}
        >
          ← Back to Editor
        </button>
        <h2 style={{ fontSize: "1.1rem", color: "#e8e8e8" }}>
          🎭 Characters &mdash; {script?.title}
        </h2>
        <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-primary" onClick={handleCreate}>
            + New Character
          </button>

          <button
            className="btn"
            onClick={handleExtract}
            disabled={extracting}
          >
            {extracting ? "Scanning Script…" : "⚡ Auto-Discover from Text"}
          </button>
        </div>
      </div>

      {/* Main split content area */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar list */}
        <div
          style={{
            width: "280px",
            background: "#111",
            borderRight: "1px solid #333",
            overflowY: "auto",
            padding: "1rem",
          }}
        >
          {characters.length === 0 ? (
            <p style={{ color: "#888", fontSize: "0.85rem" }}>
              No characters created yet. Click "+ New Character" or "Auto-Discover from Text" above.
            </p>
          ) : (
            characters.map((c) => (
              <div
                key={c.id}
                onClick={() => setSelectedId(c.id)}
                style={{
                  padding: "0.75rem",
                  borderRadius: "4px",
                  marginBottom: "0.5rem",
                  background: c.id === selectedId ? "#2a3a4a" : "#222",
                  border: c.id === selectedId ? "1px solid #4a7fa5" : "1px solid #333",
                  cursor: "pointer",
                  color: "#fff",
                }}
              >
                <div style={{ fontWeight: "bold" }}>{c.name}</div>
                <div style={{ fontSize: "0.75rem", color: "#aaa", marginTop: "0.2rem" }}>
                  {c.scene_count} scene{c.scene_count === 1 ? "" : "s"} &bull; {c.dialogue_line_count} dialogue line{c.dialogue_line_count === 1 ? "" : "s"}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detail & Edit Panel */}
        <div style={{ flex: 1, padding: "2rem", overflowY: "auto", background: "#1a1a1a" }}>
          {selectedChar ? (
            <div style={{ maxWidth: "800px", margin: "0 auto" }}>
              {/* Character Banner */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  borderBottom: "1px solid #333",
                  paddingBottom: "1rem",
                  marginBottom: "1.5rem",
                }}
              >
                <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                  {selectedChar.image_url && (
                    <img
                      src={selectedChar.image_url}
                      alt={selectedChar.name}
                      style={{
                        width: "64px",
                        height: "64px",
                        borderRadius: "50%",
                        objectFit: "cover",
                        border: "2px solid #4a7fa5",
                      }}
                    />
                  )}
                  <div>
                    <h1 style={{ fontSize: "1.8rem", color: "#fff", fontFamily: "Georgia, serif" }}>
                      {selectedChar.name}
                    </h1>
                    <span style={{ fontSize: "0.85rem", color: "#888" }}>
                      Script Character Profile
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "0.5rem" }}>
                  {!isEditing ? (
                    <button className="btn btn-primary" onClick={() => setIsEditing(true)}>
                      Edit Profile
                    </button>
                  ) : (
                    <button className="btn" onClick={() => setIsEditing(false)}>
                      Cancel
                    </button>
                  )}
                  <button className="btn" style={{ borderColor: "#e55", color: "#e55" }} onClick={handleDelete}>
                    Delete
                  </button>
                </div>
              </div>

              {/* Auto-Computed Statistics Panel */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                  gap: "1rem",
                  marginBottom: "2rem",
                }}
              >
                <div
                  style={{
                    background: "#222",
                    padding: "1rem",
                    borderRadius: "6px",
                    border: "1px solid #333",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: "#888", textTransform: "uppercase" }}>
                    Scenes Appeared
                  </div>
                  <div style={{ fontSize: "1.8rem", fontWeight: "bold", color: "#4a7fa5", marginTop: "0.2rem" }}>
                    {selectedChar.scene_count}
                  </div>
                </div>

                <div
                  style={{
                    background: "#222",
                    padding: "1rem",
                    borderRadius: "6px",
                    border: "1px solid #333",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: "#888", textTransform: "uppercase" }}>
                    Dialogue Lines
                  </div>
                  <div style={{ fontSize: "1.8rem", fontWeight: "bold", color: "#4a7fa5", marginTop: "0.2rem" }}>
                    {selectedChar.dialogue_line_count}
                  </div>
                </div>

                <div
                  style={{
                    background: "#222",
                    padding: "1rem",
                    borderRadius: "6px",
                    border: "1px solid #333",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: "#888", textTransform: "uppercase" }}>
                    First Appearance
                  </div>
                  <div style={{ fontSize: "0.9rem", color: "#fff", marginTop: "0.4rem" }}>
                    {selectedChar.first_appearance_scene
                      ? selectedChar.first_appearance_scene.heading
                      : "None"}
                  </div>
                </div>

                <div
                  style={{
                    background: "#222",
                    padding: "1rem",
                    borderRadius: "6px",
                    border: "1px solid #333",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", color: "#888", textTransform: "uppercase" }}>
                    Last Appearance
                  </div>
                  <div style={{ fontSize: "0.9rem", color: "#fff", marginTop: "0.4rem" }}>
                    {selectedChar.last_appearance_scene
                      ? selectedChar.last_appearance_scene.heading
                      : "None"}
                  </div>
                </div>
              </div>

              {/* View / Edit Form */}
              {isEditing ? (
                <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", color: "#aaa", marginBottom: "0.3rem" }}>
                      Character Name
                    </label>
                    <input
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "#222",
                        border: "1px solid #444",
                        color: "#fff",
                        borderRadius: "4px",
                      }}
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", color: "#aaa", marginBottom: "0.3rem" }}>
                      Image URL (Optional)
                    </label>
                    <input
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "#222",
                        border: "1px solid #444",
                        color: "#fff",
                        borderRadius: "4px",
                      }}
                      value={formData.image_url}
                      onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                      placeholder="https://example.com/character.jpg"
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", color: "#aaa", marginBottom: "0.3rem" }}>
                      Biography & Background
                    </label>
                    <textarea
                      rows={4}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "#222",
                        border: "1px solid #444",
                        color: "#fff",
                        borderRadius: "4px",
                        fontFamily: "inherit",
                      }}
                      value={formData.bio}
                      onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                      placeholder="Origin story, history, role in screenplay..."
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", color: "#aaa", marginBottom: "0.3rem" }}>
                      Core Motivation / Goal
                    </label>
                    <textarea
                      rows={3}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "#222",
                        border: "1px solid #444",
                        color: "#fff",
                        borderRadius: "4px",
                        fontFamily: "inherit",
                      }}
                      value={formData.motivation}
                      onChange={(e) => setFormData({ ...formData, motivation: e.target.value })}
                      placeholder="What does this character want more than anything?"
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", color: "#aaa", marginBottom: "0.3rem" }}>
                      Character Arc Notes
                    </label>
                    <textarea
                      rows={3}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "#222",
                        border: "1px solid #444",
                        color: "#fff",
                        borderRadius: "4px",
                        fontFamily: "inherit",
                      }}
                      value={formData.arc_notes}
                      onChange={(e) => setFormData({ ...formData, arc_notes: e.target.value })}
                      placeholder="How do they change from Act I to Act III?"
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", color: "#aaa", marginBottom: "0.3rem" }}>
                      Voice & Dialogue Notes
                    </label>
                    <textarea
                      rows={3}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "#222",
                        border: "1px solid #444",
                        color: "#fff",
                        borderRadius: "4px",
                        fontFamily: "inherit",
                      }}
                      value={formData.voice_notes}
                      onChange={(e) => setFormData({ ...formData, voice_notes: e.target.value })}
                      placeholder="Speech pattern, vocabulary, rhythm, catchphrases..."
                    />
                  </div>

                  <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
                    <button className="btn btn-primary" type="submit">
                      Save Changes
                    </button>
                    <button className="btn" type="button" onClick={() => setIsEditing(false)}>
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                  <section>
                    <h3 style={{ fontSize: "0.95rem", color: "#4a7fa5", marginBottom: "0.5rem" }}>
                      BIOGRAPHY & BACKGROUND
                    </h3>
                    <p style={{ color: "#ddd", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                      {selectedChar.bio || "No biography added yet. Click 'Edit Profile' to add notes."}
                    </p>
                  </section>

                  <section>
                    <h3 style={{ fontSize: "0.95rem", color: "#4a7fa5", marginBottom: "0.5rem" }}>
                      MOTIVATION & GOAL
                    </h3>
                    <p style={{ color: "#ddd", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                      {selectedChar.motivation || "No motivation notes added."}
                    </p>
                  </section>

                  <section>
                    <h3 style={{ fontSize: "0.95rem", color: "#4a7fa5", marginBottom: "0.5rem" }}>
                      CHARACTER ARC
                    </h3>
                    <p style={{ color: "#ddd", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                      {selectedChar.arc_notes || "No arc notes added."}
                    </p>
                  </section>

                  <section>
                    <h3 style={{ fontSize: "0.95rem", color: "#4a7fa5", marginBottom: "0.5rem" }}>
                      VOICE & DIALOGUE STYLE
                    </h3>
                    <p style={{ color: "#ddd", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                      {selectedChar.voice_notes || "No voice notes added."}
                    </p>
                  </section>
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: "#888", textAlign: "center", marginTop: "4rem" }}>
              Select a character on the left or create a new one.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
