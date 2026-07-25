import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  getScript,
  listCharacters,
  listRelationships,
  createRelationship,
  deleteRelationship,
  updateCharacterPosition,
  extractCharacters,
  getScriptExtraction,
} from "../api.js";

const TYPE_COLORS = {
  ally: "#4ecdc4",
  rival: "#ff6b6b",
  romantic: "#ff85a1",
  family: "#4d96ff",
  other: "#a0a0a0",
};

export default function ScriptDiagram() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("map"); // "map" | "extraction"

  const [script, setScript] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [extractionData, setExtractionData] = useState(null);

  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCharacterFilter, setSelectedCharacterFilter] = useState("All");

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Relationship Form Modal State
  const [showModal, setShowModal] = useState(false);
  const [relForm, setRelForm] = useState({
    character_a: "",
    character_b: "",
    label: "",
    type: "ally",
    notes: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const s = await getScript(id);
      setScript(s);
      const chars = await listCharacters(id);
      setCharacters(chars);
      const rels = await listRelationships(id);
      setRelationships(rels);
      const ext = await getScriptExtraction(id);
      setExtractionData(ext);
    } catch (err) {
      setError("Failed to load diagram & extraction data: " + err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Convert characters -> React Flow Nodes
  useEffect(() => {
    const flowNodes = characters.map((c, index) => {
      const x = c.pos_x !== 100.0 ? c.pos_x : 150 + (index % 4) * 220;
      const y = c.pos_y !== 100.0 ? c.pos_y : 120 + Math.floor(index / 4) * 160;

      return {
        id: String(c.id),
        position: { x, y },
        data: {
          label: (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "1rem", fontWeight: "bold", color: "#fff" }}>
                {c.name}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#aaa", marginTop: "4px" }}>
                {c.scene_count} scenes &bull; {c.dialogue_line_count} lines
              </div>
            </div>
          ),
        },
        style: {
          background: "#1e293b",
          color: "#fff",
          border: "2px solid #38bdf8",
          borderRadius: "8px",
          padding: "10px 16px",
          minWidth: "150px",
          boxShadow: "0 4px 14px rgba(0, 0, 0, 0.4)",
        },
      };
    });
    setNodes(flowNodes);
  }, [characters, setNodes]);

  // Convert relationships -> React Flow Edges
  useEffect(() => {
    const flowEdges = relationships.map((r) => {
      const color = TYPE_COLORS[r.type] || TYPE_COLORS.other;
      const displayLabel = r.label ? `${r.label}` : r.type.toUpperCase();

      return {
        id: `rel-${r.id}`,
        source: String(r.character_a),
        target: String(r.character_b),
        label: displayLabel,
        type: "smoothstep",
        animated: r.type === "romantic" || r.type === "ally",
        style: { stroke: color, strokeWidth: 2.5 },
        labelStyle: { fill: "#ffffff", fontWeight: 700, fontSize: 11 },
        labelBgStyle: { fill: "#0f172a", fillOpacity: 0.85, rx: 4, ry: 4 },
        labelBgPadding: [6, 4],
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: color,
          width: 16,
          height: 16,
        },
      };
    });
    setEdges(flowEdges);
  }, [relationships, setEdges]);

  // Trigger script re-extraction & auto-character discovery
  const handleRunAutoExtraction = async () => {
    setExtracting(true);
    try {
      await extractCharacters(id);
      await loadData();
    } catch (err) {
      alert("Extraction failed: " + err.message);
    } finally {
      setExtracting(false);
    }
  };

  const handleNodeDragStop = useCallback(async (event, node) => {
    try {
      await updateCharacterPosition(node.id, node.position.x, node.position.y);
    } catch {
      /* silent */
    }
  }, []);

  const handleCreateRelationship = async (e) => {
    e.preventDefault();
    if (!relForm.character_a || !relForm.character_b) {
      alert("Please select two characters.");
      return;
    }
    if (relForm.character_a === relForm.character_b) {
      alert("Character A and Character B must be different.");
      return;
    }

    try {
      await createRelationship({
        script: id,
        character_a: relForm.character_a,
        character_b: relForm.character_b,
        label: relForm.label,
        type: relForm.type,
        notes: relForm.notes,
      });
      const updatedRels = await listRelationships(id);
      setRelationships(updatedRels);
      setShowModal(false);
      setRelForm({
        character_a: "",
        character_b: "",
        label: "",
        type: "ally",
        notes: "",
      });
    } catch (err) {
      alert("Failed to create relationship: " + err.message);
    }
  };

  const handleDeleteRel = async (relId) => {
    if (!confirm("Remove this relationship connection?")) return;
    try {
      await deleteRelationship(relId);
      const updatedRels = await listRelationships(id);
      setRelationships(updatedRels);
    } catch (err) {
      alert("Failed to delete: " + err.message);
    }
  };

  const filteredExtractedLines = useMemo(() => {
    if (!extractionData || !extractionData.extracted_lines) return [];
    if (selectedCharacterFilter === "All") return extractionData.extracted_lines;
    return extractionData.extracted_lines.filter(
      (l) => l.character.toLowerCase() === selectedCharacterFilter.toLowerCase()
    );
  }, [extractionData, selectedCharacterFilter]);

  if (loading) {
    return <p style={{ padding: "2rem", color: "#888" }}>Loading extraction device & map…</p>;
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <p style={{ color: "#f87171", padding: "2rem 0" }}>{error}</p>
        <button className="btn" onClick={() => navigate(`/scripts/${id}`)}>
          ← Back to Editor
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#090d16" }}>
      {/* Header Toolbar */}
      <div className="editor-toolbar">
        <button
          className="btn"
          onClick={() => navigate(`/scripts/${id}`)}
          style={{ padding: "0.3rem 0.8rem" }}
        >
          ← Back to Editor
        </button>
        <h2 style={{ fontSize: "1.1rem", color: "#e8e8e8" }}>
          ⚡ Script Extracting Device &mdash; {script?.title}
        </h2>

        {/* Tab View Switcher */}
        <div style={{ marginLeft: "1.5rem", display: "flex", gap: "0.4rem" }}>
          <button
            className={`btn ${activeTab === "map" ? "btn-primary" : ""}`}
            onClick={() => setActiveTab("map")}
          >
            🕸️ Connection Map
          </button>

          <button
            className={`btn ${activeTab === "extraction" ? "btn-primary" : ""}`}
            onClick={() => setActiveTab("extraction")}
          >
            📋 Extracted Dialogue Matrix
          </button>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem" }}>
          <button
            className="btn"
            style={{ background: "#1e293b", borderColor: "#4ecdc4", color: "#4ecdc4" }}
            onClick={handleRunAutoExtraction}
            disabled={extracting}
          >
            {extracting ? "Extracting Script…" : "⚡ Run Script Extraction Engine"}
          </button>

          {activeTab === "map" && (
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              + Add Connection
            </button>
          )}
        </div>
      </div>

      {/* VIEW 1: MAP VIEW */}
      {activeTab === "map" && (
        <div style={{ flex: 1, position: "relative", background: "#090d16" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDragStop={handleNodeDragStop}
            fitView
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls style={{ background: "#1e293b", color: "#fff", border: "1px solid #334155" }} />
          </ReactFlow>

          {nodes.length === 0 && (
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                color: "#64748b",
                textAlign: "center",
              }}
            >
              <p style={{ marginBottom: "1rem" }}>No extracted character nodes found in this script.</p>
              <button
                className="btn btn-primary"
                onClick={handleRunAutoExtraction}
                disabled={extracting}
              >
                ⚡ Run Script Extraction Engine
              </button>
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: DIALOGUE & LINE CONNECTIONS EXTRACTION MATRIX */}
      {activeTab === "extraction" && (
        <div style={{ flex: 1, padding: "2rem", overflowY: "auto", background: "#0f172a" }}>
          <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
            {/* Top Extraction Overview Cards */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "1.25rem",
                marginBottom: "2rem",
              }}
            >
              <div style={{ background: "#1e293b", padding: "1.25rem", borderRadius: "12px", border: "1px solid #334155" }}>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Total Extracted Lines</div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#38bdf8", marginTop: "0.3rem" }}>
                  {extractionData?.total_extracted_lines || 0}
                </div>
              </div>

              <div style={{ background: "#1e293b", padding: "1.25rem", borderRadius: "12px", border: "1px solid #334155" }}>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Extracted Characters</div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#4ecdc4", marginTop: "0.3rem" }}>
                  {extractionData?.total_characters || 0}
                </div>
              </div>

              <div style={{ background: "#1e293b", padding: "1.25rem", borderRadius: "12px", border: "1px solid #334155" }}>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Character Connections</div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "#ff85a1", marginTop: "0.3rem" }}>
                  {extractionData?.connections?.length || 0}
                </div>
              </div>
            </div>

            {/* Character Co-occurrence & Dialogue Exchanges Section */}
            <div style={{ background: "#1e293b", padding: "1.5rem", borderRadius: "12px", border: "1px solid #334155", marginBottom: "2rem" }}>
              <h3 style={{ fontSize: "1.1rem", color: "#38bdf8", marginBottom: "1rem" }}>
                🔗 Extracted Character Connections & Scene Exchanges
              </h3>

              {(!extractionData?.connections || extractionData.connections.length === 0) ? (
                <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                  No character connections extracted yet. Click "⚡ Run Script Extraction Engine" above.
                </p>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
                  {extractionData.connections.map((conn, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: "#0f172a",
                        padding: "1rem",
                        borderRadius: "8px",
                        border: "1px solid #334155",
                      }}
                    >
                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#f8fafc", marginBottom: "0.4rem" }}>
                        {conn.character_a} &amp; {conn.character_b}
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8", display: "flex", gap: "1rem" }}>
                        <span>🎬 {conn.shared_scenes} Shared Scene{conn.shared_scenes === 1 ? "" : "s"}</span>
                        <span>💬 {conn.dialogue_exchanges} Dialogue Exchange{conn.dialogue_exchanges === 1 ? "" : "s"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Extracted Dialogue Lines Log */}
            <div style={{ background: "#1e293b", padding: "1.5rem", borderRadius: "12px", border: "1px solid #334155" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", flexWrap: "wrap", gap: "1rem" }}>
                <h3 style={{ fontSize: "1.1rem", color: "#4ecdc4" }}>
                  💬 Extracted Line-by-Line Dialogue Stream
                </h3>

                {/* Character Filter */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Filter Character:</span>
                  <select
                    className="search-input"
                    style={{ flex: "none", width: "180px", padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}
                    value={selectedCharacterFilter}
                    onChange={(e) => setSelectedCharacterFilter(e.target.value)}
                  >
                    <option value="All">All Characters</option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.name}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {filteredExtractedLines.length === 0 ? (
                <p style={{ color: "#94a3b8", fontSize: "0.85rem", padding: "2rem 0", textAlign: "center" }}>
                  No extracted dialogue lines match the current filter.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "600px", overflowY: "auto" }}>
                  {filteredExtractedLines.map((line, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: "#0f172a",
                        padding: "1rem",
                        borderRadius: "8px",
                        border: "1px solid #1e293b",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.78rem" }}>
                        <span style={{ color: "#38bdf8", fontWeight: 700 }}>
                          SCENE {line.scene_order}: {line.scene_heading}
                        </span>
                        <span style={{ color: "#64748b" }}>Line #{line.line_order}</span>
                      </div>

                      <div style={{ fontWeight: 700, color: "#f8fafc", fontSize: "0.9rem", marginBottom: "0.25rem" }}>
                        {line.character}
                      </div>

                      <p
                        style={{
                          fontFamily: "Courier Prime, Courier New, monospace",
                          fontSize: "0.95rem",
                          color: "#e2e8f0",
                          lineHeight: "1.4",
                          background: "#090d16",
                          padding: "0.6rem 0.8rem",
                          borderRadius: "4px",
                          border: "1px solid #1e293b",
                        }}
                      >
                        {line.dialogue || "(Silent reaction / Action transition)"}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Relationship Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: "1.25rem", color: "#fff" }}>Add Relationship Connection</h3>

            <form onSubmit={handleCreateRelationship} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.3rem" }}>
                  Character A (From)
                </label>
                <select
                  className="search-input"
                  style={{ width: "100%" }}
                  value={relForm.character_a}
                  onChange={(e) => setRelForm({ ...relForm, character_a: e.target.value })}
                  required
                >
                  <option value="">Select Character</option>
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.3rem" }}>
                  Character B (To)
                </label>
                <select
                  className="search-input"
                  style={{ width: "100%" }}
                  value={relForm.character_b}
                  onChange={(e) => setRelForm({ ...relForm, character_b: e.target.value })}
                  required
                >
                  <option value="">Select Character</option>
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.3rem" }}>
                  Relationship Type
                </label>
                <select
                  className="search-input"
                  style={{ width: "100%" }}
                  value={relForm.type}
                  onChange={(e) => setRelForm({ ...relForm, type: e.target.value })}
                >
                  <option value="ally">Ally</option>
                  <option value="rival">Rival</option>
                  <option value="romantic">Romantic</option>
                  <option value="family">Family</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.3rem" }}>
                  Label (e.g. "Best Friend", "Arch Nemesis", "Siblings")
                </label>
                <input
                  className="search-input"
                  style={{ width: "100%" }}
                  value={relForm.label}
                  onChange={(e) => setRelForm({ ...relForm, label: e.target.value })}
                  placeholder="Relationship Label"
                />
              </div>

              <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
                <button className="btn btn-primary" type="submit">
                  Save Connection
                </button>
                <button className="btn" type="button" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
