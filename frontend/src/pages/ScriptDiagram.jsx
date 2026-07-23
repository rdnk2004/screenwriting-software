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

  const [script, setScript] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    } catch (err) {
      setError("Failed to load diagram data: " + err.message);
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
      // Default grid placement if pos_x/pos_y are at defaults
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

  // Save updated node position on drag stop
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

  if (loading) {
    return <p style={{ padding: "2rem", color: "#888" }}>Loading relationship diagram…</p>;
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
          🕸️ Character Map &mdash; {script?.title}
        </h2>

        {/* Legend */}
        <div style={{ display: "flex", gap: "0.8rem", marginLeft: "1.5rem", fontSize: "0.75rem" }}>
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <span key={type} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
              <span
                style={{
                  width: "10px",
                  height: "10px",
                  borderRadius: "50%",
                  backgroundColor: color,
                }}
              />
              <span style={{ textTransform: "capitalize", color: "#aaa" }}>{type}</span>
            </span>
          ))}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + Add Relationship
          </button>
        </div>
      </div>

      {/* Diagram Canvas Container */}
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
            <p>No characters found in this script.</p>
            <button
              className="btn btn-primary"
              style={{ marginTop: "1rem" }}
              onClick={() => navigate(`/scripts/${id}/characters`)}
            >
              Go to Characters Page
            </button>
          </div>
        )}
      </div>

      {/* Add / Edit Relationship Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div
            style={{
              background: "#1e293b",
              padding: "2rem",
              borderRadius: "8px",
              width: "480px",
              maxWidth: "90%",
              boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
              border: "1px solid #334155",
            }}
          >
            <h3 style={{ marginBottom: "1.5rem", color: "#fff" }}>Add Relationship Connection</h3>

            <form onSubmit={handleCreateRelationship} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.3rem" }}>
                  Character A (From)
                </label>
                <select
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
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
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
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
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
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
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
                  value={relForm.label}
                  onChange={(e) => setRelForm({ ...relForm, label: e.target.value })}
                  placeholder="Relationship Label"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.3rem" }}>
                  Notes
                </label>
                <textarea
                  rows={2}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
                  value={relForm.notes}
                  onChange={(e) => setRelForm({ ...relForm, notes: e.target.value })}
                  placeholder="Details about their dynamic..."
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

            {/* List of Existing Relationships */}
            {relationships.length > 0 && (
              <div style={{ marginTop: "2rem", borderTop: "1px solid #334155", paddingTop: "1rem" }}>
                <h4 style={{ fontSize: "0.85rem", color: "#aaa", marginBottom: "0.75rem" }}>
                  Existing Connections
                </h4>
                <div style={{ maxHeight: "150px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {relationships.map((r) => (
                    <div
                      key={r.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        background: "#0f172a",
                        padding: "0.4rem 0.8rem",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                      }}
                    >
                      <span style={{ color: "#fff" }}>
                        <strong>{r.character_a_name}</strong> &rarr; <strong>{r.character_b_name}</strong> ({r.label || r.type})
                      </span>
                      <button
                        className="btn"
                        style={{ padding: "0.1rem 0.4rem", fontSize: "0.7rem", borderColor: "#e55", color: "#e55" }}
                        onClick={() => handleDeleteRel(r.id)}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
