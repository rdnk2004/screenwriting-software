import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getScript, getScriptAnalysis } from "../api.js";

export default function ScriptAnalysis() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [script, setScript] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const s = await getScript(id);
      setScript(s);
      const analysis = await getScriptAnalysis(id);
      setData(analysis);
    } catch (err) {
      setError("Failed to load script analysis: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) {
    return <p style={{ padding: "2rem", color: "#888" }}>Calculating script analysis metrics…</p>;
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
          📊 Script Analysis & Dashboard &mdash; {script?.title}
        </h2>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: "2rem", overflowY: "auto" }}>
        <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
          {/* Key Metrics Overview Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "1rem",
              marginBottom: "2rem",
            }}
          >
            <div style={{ background: "#1e293b", padding: "1.2rem", borderRadius: "8px", border: "1px solid #334155" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Total Scenes</div>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "#38bdf8", marginTop: "0.3rem" }}>
                {data.total_scenes}
              </div>
            </div>

            <div style={{ background: "#1e293b", padding: "1.2rem", borderRadius: "8px", border: "1px solid #334155" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Dialogue Lines</div>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "#4ecdc4", marginTop: "0.3rem" }}>
                {data.total_dialogue_lines}
              </div>
            </div>

            <div style={{ background: "#1e293b", padding: "1.2rem", borderRadius: "8px", border: "1px solid #334155" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Estimated Pages</div>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "#ff85a1", marginTop: "0.3rem" }}>
                ~{data.estimated_total_pages}
              </div>
            </div>

            <div style={{ background: "#1e293b", padding: "1.2rem", borderRadius: "8px", border: "1px solid #334155" }}>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Unique Locations</div>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "#a78bfa", marginTop: "0.3rem" }}>
                {data.locations.length}
              </div>
            </div>
          </div>

          {/* Section 1: Dialogue Balance per Character */}
          <div style={{ background: "#1e293b", padding: "1.5rem", borderRadius: "8px", border: "1px solid #334155", marginBottom: "2rem" }}>
            <h3 style={{ fontSize: "1.1rem", color: "#38bdf8", marginBottom: "1.2rem" }}>
              🗣️ Dialogue Balance (% Spoken Lines)
            </h3>

            {data.dialogue_balance.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>No dialogue lines found in screenplay.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
                {data.dialogue_balance.map((item) => (
                  <div key={item.character}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "#fff", marginBottom: "0.3rem" }}>
                      <span>
                        <strong>{item.character}</strong>
                      </span>
                      <span>
                        {item.dialogue_lines} lines ({item.percentage}%)
                      </span>
                    </div>

                    <div style={{ width: "100%", background: "#0f172a", height: "10px", borderRadius: "5px", overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${Math.min(item.percentage, 100)}%`,
                          height: "100%",
                          background: "linear-gradient(90deg, #38bdf8, #818cf8)",
                          borderRadius: "5px",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: Beat & Act Breakdown */}
          <div style={{ background: "#1e293b", padding: "1.5rem", borderRadius: "8px", border: "1px solid #334155", marginBottom: "2rem" }}>
            <h3 style={{ fontSize: "1.1rem", color: "#4ecdc4", marginBottom: "1.2rem" }}>
              📑 Act & Beat Breakdown
            </h3>

            {data.beat_breakdown.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                No story beats defined yet. Go to the <strong>Outline</strong> screen to add beats.
              </p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", color: "#fff", fontSize: "0.85rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #334155", textAlign: "left" }}>
                    <th style={{ padding: "0.6rem" }}>Beat Name</th>
                    <th style={{ padding: "0.6rem" }}>Linked Scene</th>
                    <th style={{ padding: "0.6rem", textAlign: "right" }}>Scene Count</th>
                    <th style={{ padding: "0.6rem", textAlign: "right" }}>Est. Pages</th>
                  </tr>
                </thead>
                <tbody>
                  {data.beat_breakdown.map((b) => (
                    <tr key={b.id} style={{ borderBottom: "1px solid #0f172a" }}>
                      <td style={{ padding: "0.6rem", fontWeight: "600" }}>{b.name}</td>
                      <td style={{ padding: "0.6rem", color: "#94a3b8" }}>{b.linked_scene_heading || "Unlinked"}</td>
                      <td style={{ padding: "0.6rem", textAlign: "right", color: "#38bdf8" }}>{b.scene_count}</td>
                      <td style={{ padding: "0.6rem", textAlign: "right", color: "#ff85a1" }}>~{b.estimated_pages}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Section 3: Grid of Locations and Active Characters */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "1.5rem" }}>
            {/* Location List */}
            <div style={{ background: "#1e293b", padding: "1.5rem", borderRadius: "8px", border: "1px solid #334155" }}>
              <h3 style={{ fontSize: "1rem", color: "#a78bfa", marginBottom: "1rem" }}>
                📍 Locations & Scene Counts
              </h3>
              {data.locations.length === 0 ? (
                <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>No locations found.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  {data.locations.map((loc) => (
                    <div
                      key={loc.location}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "0.5rem 0.8rem",
                        background: "#0f172a",
                        borderRadius: "4px",
                        fontSize: "0.85rem",
                      }}
                    >
                      <span style={{ color: "#fff", fontWeight: "bold" }}>{loc.location}</span>
                      <span style={{ color: "#a78bfa" }}>
                        {loc.scene_count} scene{loc.scene_count === 1 ? "" : "s"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Active Characters */}
            <div style={{ background: "#1e293b", padding: "1.5rem", borderRadius: "8px", border: "1px solid #334155" }}>
              <h3 style={{ fontSize: "1rem", color: "#ff85a1", marginBottom: "1rem" }}>
                🎭 Character Activity Summary
              </h3>

              <div style={{ marginBottom: "1rem" }}>
                <h4 style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                  Most Active
                </h4>
                {data.most_active_characters.length === 0 ? (
                  <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>None</p>
                ) : (
                  data.most_active_characters.map((c) => (
                    <div
                      key={c.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "0.4rem 0.6rem",
                        background: "#0f172a",
                        borderRadius: "4px",
                        marginBottom: "0.3rem",
                        fontSize: "0.85rem",
                      }}
                    >
                      <span style={{ color: "#fff" }}>{c.name}</span>
                      <span style={{ color: "#38bdf8" }}>
                        {c.scene_count} scenes &bull; {c.dialogue_line_count} lines
                      </span>
                    </div>
                  ))
                )}
              </div>

              {data.least_active_characters.length > 0 && (
                <div>
                  <h4 style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                    Least Active
                  </h4>
                  {data.least_active_characters.map((c) => (
                    <div
                      key={c.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "0.4rem 0.6rem",
                        background: "#0f172a",
                        borderRadius: "4px",
                        marginBottom: "0.3rem",
                        fontSize: "0.85rem",
                      }}
                    >
                      <span style={{ color: "#fff" }}>{c.name}</span>
                      <span style={{ color: "#94a3b8" }}>
                        {c.scene_count} scenes &bull; {c.dialogue_line_count} lines
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
