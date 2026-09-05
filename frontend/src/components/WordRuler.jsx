import React from "react";

const ELEMENT_INDENTS = {
  scene_heading: { left: 1.5, right: 7.5, label: "Scene Heading (Full Width)" },
  action: { left: 1.5, right: 7.5, label: "Action (Full Width)" },
  character: { left: 3.7, right: 7.5, label: "Character Cue (Centered)" },
  dialogue: { left: 2.5, right: 6.5, label: "Dialogue Block" },
  parenthetical: { left: 3.0, right: 6.0, label: "Parenthetical Delivery" },
  transition: { left: 5.5, right: 7.5, label: "Transition (Right Aligned)" },
  centered: { left: 2.5, right: 6.5, label: "Centered Text" },
};

export default function WordRuler({ activeType = "action" }) {
  const indents = ELEMENT_INDENTS[activeType] || ELEMENT_INDENTS.action;

  // Total ruler width is 8.5 inches (0 to 8.5 in)
  const leftPct = (indents.left / 8.5) * 100;
  const rightPct = (indents.right / 8.5) * 100;
  const leftMarginPct = (1.5 / 8.5) * 100;
  const rightMarginPct = (7.5 / 8.5) * 100;

  return (
    <div className="word-ruler-container" title={`Active Indents: ${indents.label}`}>
      {/* Shaded Left Margin (0 to 1.5 in) */}
      <div
        className="ruler-shaded-margin left"
        style={{ width: `${leftMarginPct}%` }}
      />

      {/* Printable Ruler Scale */}
      <div className="ruler-scale">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((num) => (
          <div key={num} className="ruler-inch" style={{ left: `${(num / 8.5) * 100}%` }}>
            <span className="ruler-num">{num}</span>
            <div className="ruler-tick major" />
            <div className="ruler-tick half" style={{ left: "-50%" }} />
            <div className="ruler-tick quarter" style={{ left: "-75%" }} />
            <div className="ruler-tick quarter" style={{ left: "-25%" }} />
          </div>
        ))}
      </div>

      {/* Shaded Right Margin (7.5 to 8.5 in) */}
      <div
        className="ruler-shaded-margin right"
        style={{ width: `${100 - rightMarginPct}%` }}
      />

      {/* Active Left Indent Marker */}
      <div
        className="ruler-indent-marker left"
        style={{ left: `${leftPct}%` }}
        title={`Left Indent: ${indents.left}"`}
      >
        <div className="indent-triangle-down" />
        <div className="indent-box" />
      </div>

      {/* Active Right Indent Marker */}
      <div
        className="ruler-indent-marker right"
        style={{ left: `${rightPct}%` }}
        title={`Right Indent: ${indents.right}"`}
      >
        <div className="indent-triangle-down" />
      </div>
    </div>
  );
}
