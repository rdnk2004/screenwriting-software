import { useState, useMemo } from "react";

export const GLOSSARY_TERMS = [
  {
    id: "int_ext",
    term: "INT. / EXT. (Scene Headings)",
    category: "Headings & Sluglines",
    snippet: "INT. COFFEE SHOP - DAY\n",
    format: "INT. (Interior) or EXT. (Exterior) - LOCATION - TIME OF DAY",
    description:
      "Establishes where and when a scene takes place. Always written in ALL CAPS. 'INT.' means indoors, 'EXT.' means outdoors, and 'INT./EXT.' is used for moving vehicles or doorways.",
    example: "INT. DETECTIVE OFFICE - NIGHT\nRain beats against the window glass.",
  },
  {
    id: "vo",
    term: "V.O. (Voiceover)",
    category: "Audio & Voice",
    snippet: "NARRATOR (V.O.)\n",
    format: "CHARACTER NAME (V.O.)",
    description:
      "Indicates speech heard by the audience from a narrator or character who is NOT physically present in the scene (e.g. inner thoughts, phone recordings, documentary narration).",
    example: "ROSE (V.O.)\nIt has been eighty-four years...",
  },
  {
    id: "os",
    term: "O.S. / O.C. (Off-Screen / Off-Camera)",
    category: "Audio & Voice",
    snippet: "POLICE OFFICER (O.S.)\n",
    format: "CHARACTER NAME (O.S.)",
    description:
      "Used when a character is physically present inside the location of the scene, but is hidden from the camera's view (e.g. calling out from another room, behind a closed door).",
    example: "MOM (O.S.)\nDinner is ready!",
  },
  {
    id: "contd",
    term: "CONT'D (Continued Dialogue)",
    category: "Audio & Voice",
    snippet: "JOHN (CONT'D)\n",
    format: "CHARACTER NAME (CONT'D)",
    description:
      "Used when a character speaks, pauses for an action beat, and then continues speaking. Indicates to actors that the thought continues unbroken.",
    example: "JOHN\nI knew it.\n\nJohn slams his fist on the desk.\n\nJOHN (CONT'D)\nYou lied to me.",
  },
  {
    id: "montage",
    term: "MONTAGE",
    category: "Pacing & Special Formatting",
    snippet: "MONTAGE - TRAINING SEQUENCE\n\nA) Rocky runs up the museum steps.\nB) Rocky punches the frozen meat.\nC) Rocky drinks raw eggs.\n\nEND MONTAGE.",
    format: "MONTAGE - DESCRIPTION ... END MONTAGE.",
    description:
      "A series of brief, rapid shots showing a progression of events, time passing, or thematic transformation set to music or quick cuts.",
    example: "MONTAGE - BANK HEIST PREPARATION\n- Alex blueprints the vault.\n- Sarah tests the laser cutter.",
  },
  {
    id: "intercut",
    term: "INTERCUT",
    category: "Pacing & Special Formatting",
    snippet: "INTERCUT PHONE CONVERSATION - SARAH / MARK\n",
    format: "INTERCUT [LOCATION A] / [LOCATION B]",
    description:
      "Used to alternate rapidly back and forth between two simultaneous locations without writing separate INT./EXT. scene headings for every single line (e.g. phone calls).",
    example: "INTERCUT PHONE CONVERSATION - POLICE HQ / GETAWAY CAR\n\nOFFICER MILLS\nWe have you surrounded.\n\nJACK\nThen it's a fair fight.",
  },
  {
    id: "flashback",
    term: "FLASHBACK",
    category: "Pacing & Special Formatting",
    snippet: "FLASHBACK:\n\nINT. CHILDHOOD BEDROOM - 1995 - NIGHT\n\nBACK TO PRESENT:\n",
    format: "FLASHBACK: ... BACK TO PRESENT:",
    description:
      "Temporarily shifts the story to a past event. Always clearly mark the start with FLASHBACK: and close with BACK TO PRESENT: to maintain clarity.",
    example: "FLASHBACK:\n\nEXT. SUMMER CAMP - 2005 - DAY\nYoung David drops his compass in the mud.\n\nBACK TO PRESENT:",
  },
  {
    id: "chyron",
    term: "CHYRON / SUPER (On-Screen Text)",
    category: "Headings & Sluglines",
    snippet: "SUPER: \"PARIS, FRANCE - 1942\"\n",
    format: "SUPER: \"TEXT TO DISPLAY\"",
    description:
      "Superimposed text or caption displayed on screen for the audience (e.g. date, location, title, translated subtitle).",
    example: "SUPER: \"THREE YEARS LATER\"\n\nEXT. CITY STREETS - DAY",
  },
  {
    id: "beat",
    term: "PAUSE / (BEAT)",
    category: "Pacing & Special Formatting",
    snippet: "(beat)\n",
    format: "(beat) inside parenthetical or action line",
    description:
      "Indicates a silent pause in speech or action, signifying emotional hesitation, realization, or tension.",
    example: "DR. ARIS\nI found the cure.\n\n(beat)\n\nDR. ARIS (CONT'D)\n...But it's too late.",
  },
  {
    id: "parenthetical",
    term: "PARENTHETICAL",
    category: "Audio & Voice",
    snippet: "(whispering)\n",
    format: "(emotional tone or physical micro-action)",
    description:
      "Brief directional cues placed directly under a character name to instruct delivery (e.g. (whispering), (sarcastic), (pointing gun)). Keep them short and sparse.",
    example: "AGENT SMITH\n(smirking)\nMr. Anderson...",
  },
  {
    id: "smash_cut",
    term: "SMASH CUT TO:",
    category: "Transitions & Cuts",
    snippet: "SMASH CUT TO:\n",
    format: "SMASH CUT TO:",
    description:
      "A dramatic, sudden, and jarring transition from one scene to a contrasting scene (e.g. cutting from a quiet sleeping baby to a screaming rock concert).",
    example: "EXT. QUIET MEADOW - DAY\nAn peaceful robin chirps on a branch.\n\nSMASH CUT TO:\n\nINT. WARZONE - CONTINUOUS",
  },
  {
    id: "insert",
    term: "INSERT (Close-Up Detail)",
    category: "Headings & Sluglines",
    snippet: "INSERT - THE POCKET WATCH\n\nThe second hand ticks backwards.\n\nBACK TO SCENE\n",
    format: "INSERT - OBJECT ... BACK TO SCENE",
    description:
      "Directs camera focus to a specific object or text detail that is critical for the story (e.g. a letter, clock, text message on a phone).",
    example: "INSERT - CELL PHONE SCREEN\nAn unread text reads: 'RUN NOW'.\n\nBACK TO SCENE",
  },
];

export default function GlossaryDrawer({ isOpen, onClose, onInsertTerm }) {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const categories = useMemo(() => {
    const set = new Set(GLOSSARY_TERMS.map((t) => t.category));
    return ["All", ...Array.from(set)];
  }, []);

  const filteredTerms = useMemo(() => {
    return GLOSSARY_TERMS.filter((term) => {
      const matchesCategory = selectedCategory === "All" || term.category === selectedCategory;
      const matchesSearch =
        term.term.toLowerCase().includes(search.toLowerCase()) ||
        term.description.toLowerCase().includes(search.toLowerCase()) ||
        term.format.toLowerCase().includes(search.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [search, selectedCategory]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "440px",
        height: "100vh",
        background: "#0f172a",
        borderLeft: "1px solid #334155",
        boxShadow: "-10px 0 30px rgba(0,0,0,0.5)",
        zIndex: 200,
        display: "flex",
        flexDirection: "column",
        animation: "slideInRight 0.2s ease-out",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "1.25rem 1.5rem",
          background: "#1e293b",
          borderBottom: "1px solid #334155",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f8fafc" }}>
            📖 Screenwriting Terms & Guide
          </h2>
          <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "2px" }}>
            Learn industry standard screenplay rules & 1-click insert
          </p>
        </div>
        <button
          className="btn"
          style={{ padding: "0.2rem 0.5rem", fontSize: "0.9rem" }}
          onClick={onClose}
        >
          ✕
        </button>
      </div>

      {/* Search & Categories */}
      <div style={{ padding: "1rem 1.5rem", background: "#0f172a", borderBottom: "1px solid #1e293b" }}>
        <input
          className="search-input"
          style={{ width: "100%", marginBottom: "0.75rem", fontSize: "0.85rem" }}
          placeholder="🔍 Search terms (e.g. V.O., INT, Montage)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          {categories.map((cat) => (
            <button
              key={cat}
              className={`btn ${selectedCategory === cat ? "btn-primary" : ""}`}
              style={{ padding: "0.2rem 0.5rem", fontSize: "0.72rem", borderRadius: "12px" }}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Glossary Terms List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "1.25rem 1.5rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {filteredTerms.length === 0 ? (
          <p style={{ color: "#64748b", textAlign: "center", marginTop: "2rem", fontSize: "0.85rem" }}>
            No screenwriting terms match your filter.
          </p>
        ) : (
          filteredTerms.map((t) => (
            <div
              key={t.id}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "10px",
                padding: "1rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#38bdf8" }}>{t.term}</h3>
                <span
                  style={{
                    fontSize: "0.68rem",
                    padding: "0.15rem 0.4rem",
                    borderRadius: "4px",
                    background: "rgba(56, 189, 248, 0.1)",
                    color: "#38bdf8",
                    border: "1px solid rgba(56, 189, 248, 0.2)",
                  }}
                >
                  {t.category}
                </span>
              </div>

              <p style={{ fontSize: "0.82rem", color: "#e2e8f0", lineHeight: "1.45", marginBottom: "0.75rem" }}>
                {t.description}
              </p>

              <div style={{ background: "#090d16", padding: "0.6rem", borderRadius: "6px", fontSize: "0.75rem", marginBottom: "0.75rem", border: "1px solid #1e293b" }}>
                <div style={{ color: "#64748b", fontSize: "0.68rem", textTransform: "uppercase", marginBottom: "0.2rem" }}>
                  Standard Format:
                </div>
                <code style={{ color: "#4ecdc4", fontFamily: "Courier Prime, Courier New, monospace" }}>
                  {t.format}
                </code>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                  Example snippet available
                </span>

                <button
                  className="btn btn-primary"
                  style={{ padding: "0.3rem 0.75rem", fontSize: "0.78rem" }}
                  onClick={() => {
                    if (onInsertTerm) onInsertTerm(t.snippet);
                  }}
                >
                  ⚡ Insert into Script
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
