import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getScript,
  listBeats,
  createBeat,
  updateBeat,
  deleteBeat,
} from "../api.js";

const PRESET_BEATS_SAVE_THE_CAT = [
  "Opening Image",
  "Theme Stated",
  "Set-up",
  "Catalyst",
  "Debate",
  "Break into Two",
  "B Story",
  "Fun and Games",
  "Midpoint",
  "Bad Guys Close In",
  "All Hope Is Lost",
  "Dark Night of the Soul",
  "Break into Three",
  "Finale",
  "Final Image",
];

const PRESET_BEATS_THREE_ACT = [
  "Act I: Inciting Incident",
  "Act I: Plot Point 1",
  "Act II-A: Rising Action",
  "Act II-A: Midpoint Climax",
  "Act II-B: Complications",
  "Act II-B: Plot Point 2",
  "Act III: Climax",
  "Act III: Resolution",
];

export default function ScriptOutline() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [script, setScript] = useState(null);
  const [beats, setBeats] = useState([]);
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newBeatName, setNewBeatName] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const scriptData = await getScript(id);
      setScript(scriptData);
      setScenes(scriptData.scenes || []);
      const beatList = await listBeats(id);
      setBeats(beatList);
    } catch (err) {
      setError("Failed to load outline data: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleAddBeat = async (e) => {
    e.preventDefault();
    if (!newBeatName.trim()) return;
    try {
      const nextOrder = beats.length > 0 ? Math.max(...beats.map((b) => b.order)) + 1 : 1;
      await createBeat({
        script: id,
        name: newBeatName.trim(),
        order: nextOrder,
        linked_scene: null,
      });
      setNewBeatName("");
      const updated = await listBeats(id);
      setBeats(updated);
    } catch (err) {
      alert("Failed to add beat: " + err.message);
    }
  };

  const handleLoadPreset = async (presetList) => {
    if (beats.length > 0 && !confirm("Loading preset beats will append to your current beats. Proceed?")) {
      return;
    }
    try {
      let currentMaxOrder = beats.length > 0 ? Math.max(...beats.map((b) => b.order)) : 0;
      for (const name of presetList) {
        currentMaxOrder += 1;
        await createBeat({
          script: id,
          name: name,
          order: currentMaxOrder,
          linked_scene: null,
        });
      }
      const updated = await listBeats(id);
      setBeats(updated);
    } catch (err) {
      alert("Failed to load preset beats: " + err.message);
    }
  };

  const handleLinkScene = async (beatId, sceneId) => {
    try {
      await updateBeat(beatId, { linked_scene: sceneId ? parseInt(sceneId) : null });
      const updated = await listBeats(id);
      setBeats(updated);
    } catch (err) {
      alert("Failed to link scene: " + err.message);
    }
  };

  const handleMoveBeat = async (index, direction) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= beats.length) return;

    const newBeats = [...beats];
    const temp = newBeats[index];
    newBeats[index] = newBeats[targetIndex];
    newBeats[targetIndex] = temp;

    // Re-index order
    try {
      for (let i = 0; i < newBeats.length; i++) {
        const item = newBeats[i];
        if (item.order !== i + 1) {
          await updateBeat(item.id, { order: i + 1 });
        }
      }
      const updated = await listBeats(id);
      setBeats(updated);
    } catch (err) {
      alert("Failed to reorder beat: " + err.message);
    }
  };

  const handleDeleteBeat = async (beatId) => {
    if (!confirm("Delete this beat from outline?")) return;
    try {
      await deleteBeat(beatId);
      const updated = await listBeats(id);
      setBeats(updated);
    } catch (err) {
      alert("Failed to delete beat: " + err.message);
    }
  };

  if (loading) {
    return <p style={{ padding: "2rem", color: "#888" }}>Loading script outline…</p>;
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
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0f172a" }}>
      {/* Header Toolbar */}
      <div className="editor-toolbar">
        <button className="btn" onClick={() => navigate(`/scripts/${id}`)} style={{ padding: "0.3rem 0.8rem" }}>
          ← Back to Editor
        </button>
        <h2 style={{ fontSize: "1.1rem", color: "#e8e8e8" }}>
          📋 Beat Sheet & Outline &mdash; {script?.title}
        </h2>

        <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem" }}>
          <button className="btn" onClick={() => handleLoadPreset(PRESET_BEATS_SAVE_THE_CAT)}>
            + Save the Cat Preset
          </button>
          <button className="btn" onClick={() => handleLoadPreset(PRESET_BEATS_THREE_ACT)}>
            + 3-Act Preset
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: "2rem", overflowY: "auto" }}>
        <div style={{ maxWidth: "900px", margin: "0 auto" }}>
          {/* Add New Beat Form */}
          <form
            onSubmit={handleAddBeat}
            style={{
              display: "flex",
              gap: "0.8rem",
              marginBottom: "2rem",
              background: "#1e293b",
              padding: "1rem",
              borderRadius: "8px",
              border: "1px solid #334155",
            }}
          >
            <input
              style={{
                flex: 1,
                padding: "0.6rem 0.8rem",
                background: "#0f172a",
                border: "1px solid #334155",
                color: "#fff",
                borderRadius: "4px",
              }}
              placeholder="Enter new beat name (e.g. Inciting Incident)..."
              value={newBeatName}
              onChange={(e) => setNewBeatName(e.target.value)}
            />
            <button className="btn btn-primary" type="submit">
              + Add Beat
            </button>
          </form>

          {/* Beats List */}
          {beats.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "3rem",
                background: "#1e293b",
                borderRadius: "8px",
                border: "1px dashed #334155",
                color: "#94a3b8",
              }}
            >
              <p>No story beats added yet.</p>
              <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
                Add beats manually above or load a structure template (Save the Cat / 3-Act Structure).
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {beats.map((beat, idx) => (
                <div
                  key={beat.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "1rem",
                    background: "#1e293b",
                    padding: "0.9rem 1.2rem",
                    borderRadius: "6px",
                    border: "1px solid #334155",
                  }}
                >
                  <span
                    style={{
                      fontWeight: "bold",
                      color: "#38bdf8",
                      minWidth: "28px",
                      fontSize: "0.9rem",
                    }}
                  >
                    #{idx + 1}
                  </span>

                  <div style={{ flex: 1 }}>
                    <div style={{ color: "#fff", fontWeight: "600", fontSize: "1rem" }}>{beat.name}</div>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "2px" }}>
                      Linked Scene: {beat.linked_scene_heading || "Not linked"}
                    </div>
                  </div>

                  {/* Scene Link Selector */}
                  <select
                    style={{
                      padding: "0.4rem 0.6rem",
                      background: "#0f172a",
                      border: "1px solid #334155",
                      color: "#fff",
                      borderRadius: "4px",
                      fontSize: "0.85rem",
                      maxWidth: "220px",
                    }}
                    value={beat.linked_scene || ""}
                    onChange={(e) => handleLinkScene(beat.id, e.target.value)}
                  >
                    <option value="">-- Link to Scene --</option>
                    {scenes.map((sc) => (
                      <option key={sc.id} value={sc.id}>
                        Scene {sc.order + 1}: {sc.heading}
                      </option>
                    ))}
                  </select>

                  {/* Reorder & Action Buttons */}
                  <div style={{ display: "flex", gap: "0.3rem" }}>
                    <button
                      className="btn"
                      style={{ padding: "0.2rem 0.5rem" }}
                      disabled={idx === 0}
                      onClick={() => handleMoveBeat(idx, -1)}
                    >
                      ▲
                    </button>
                    <button
                      className="btn"
                      style={{ padding: "0.2rem 0.5rem" }}
                      disabled={idx === beats.length - 1}
                      onClick={() => handleMoveBeat(idx, 1)}
                    >
                      ▼
                    </button>
                    <button
                      className="btn"
                      style={{ padding: "0.2rem 0.5rem", borderColor: "#e55", color: "#e55", marginLeft: "0.4rem" }}
                      onClick={() => handleDeleteBeat(beat.id)}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
