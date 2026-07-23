"""
Fountain screenplay format parser and serializer.

Reference: https://fountain.io/syntax

Supported elements:
  - Scene Heading   INT./EXT. prefix or forced with '.'
  - Action          Any other paragraph
  - Character       ALL CAPS line (optionally followed by extension like (V.O.))
  - Dialogue        Line following a character
  - Parenthetical   Line starting with '(' inside dialogue block
  - Transition      ALL CAPS line ending with 'TO:' or forced with '>'
  - Lyrics          Line starting with '~' (treated as action for storage)
  - Notes/Boneyard  [[note]] and /* boneyard */ — skipped during import
"""
import re
from typing import Iterator

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_RE_SCENE_HEADING_FORCED = re.compile(r"^\.")   # .INT. or .EXT. forced
_RE_SCENE_HEADING = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|I/E\.)\s", re.IGNORECASE
)
_RE_TRANSITION_FORCED = re.compile(r"^>(.+)$")
_RE_TRANSITION_NATURAL = re.compile(
    r"^([A-Z][A-Z\s]+TO:)\s*$"
)
_RE_CHARACTER = re.compile(
    r"^([A-Z][A-Z0-9\s\.\-']+?)(\s*\([^)]+\))?\s*$"
)
_RE_PARENTHETICAL = re.compile(r"^\((.+)\)\s*$")
_RE_NOTE = re.compile(r"\[\[.*?\]\]", re.DOTALL)
_RE_BONEYARD = re.compile(r"/\*.*?\*/", re.DOTALL)
_RE_TITLE_PAGE = re.compile(r"^[A-Za-z ]+:.*$")

# Scene heading location/time parser
_RE_HEADING_PARTS = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|I/E\.)?\s*(.+?)\s*[-–]\s*(.+?)$",
    re.IGNORECASE,
)


def _strip_markup(text: str) -> str:
    """Remove Fountain inline markup (*bold*, _underline_, etc.)."""
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text


def _parse_heading_location(heading: str):
    """Extract location and time_of_day from a scene heading string."""
    m = _RE_HEADING_PARTS.match(heading)
    if m:
        location = m.group(2).strip()
        time_of_day = m.group(3).strip()
    else:
        location = heading
        time_of_day = ""
    return location, time_of_day


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_fountain(text: str) -> list[dict]:
    """
    Parse a Fountain-formatted string into a list of scene dicts.

    Returns:
        [
            {
                "heading": str,
                "location": str,
                "time_of_day": str,
                "pov_character": None,
                "order": int,
                "lines": [
                    {"order": int, "type": str, "text": str},
                    ...
                ],
            },
            ...
        ]

    Key Fountain parsing rule:
      - Blank lines separate blocks/paragraphs and reset dialogue context.
      - Within a single block (no blank lines), lines continue from each other:
            CHARACTER NAME
            (parenthetical)
            Dialogue text here.
        All three are classified line-by-line based on context.
    """
    # Strip boneyard / notes
    text = _RE_BONEYARD.sub("", text)
    text = _RE_NOTE.sub("", text)

    # Strip optional title page
    lines_raw = text.splitlines()
    start_idx = _skip_title_page(lines_raw)
    lines_raw = lines_raw[start_idx:]

    scenes: list[dict] = []
    current_scene: dict | None = None
    scene_order = 0
    line_order = 0
    prev_type: str | None = None
    in_dialogue_block = False  # True from character cue until blank line

    def new_scene(heading: str) -> dict:
        nonlocal scene_order, line_order
        location, time_of_day = _parse_heading_location(heading)
        s = {
            "heading": heading,
            "location": location,
            "time_of_day": time_of_day,
            "pov_character": None,
            "order": scene_order,
            "lines": [],
        }
        scene_order += 1
        line_order = 0
        return s

    def add_line(ltype: str, ltext: str):
        nonlocal line_order, prev_type
        if current_scene is None:
            return
        current_scene["lines"].append(
            {"order": line_order, "type": ltype, "text": ltext}
        )
        line_order += 1
        prev_type = ltype

    # Create a catch-all scene for preamble content
    current_scene = new_scene("")

    for raw_line in lines_raw:
        line_text = raw_line.rstrip()

        if not line_text.strip():
            # Blank line -> end of any dialogue block; reset context
            in_dialogue_block = False
            prev_type = None
            continue

        elem_type, elem_text = _classify_line(line_text, prev_type, in_dialogue_block)

        if elem_type == "scene_heading":
            in_dialogue_block = False
            if current_scene["lines"] or current_scene["heading"]:
                scenes.append(current_scene)
            current_scene = new_scene(elem_text)
            add_line("scene_heading", elem_text)
        else:
            if elem_type == "character":
                in_dialogue_block = True
            elif elem_type not in ("dialogue", "parenthetical"):
                in_dialogue_block = False
            add_line(elem_type, elem_text)

    # Flush last scene
    if current_scene:
        scenes.append(current_scene)

    # Remove empty leading preamble scene
    scenes = [s for s in scenes if s["heading"] or s["lines"]]

    # Re-number scenes
    for i, s in enumerate(scenes):
        s["order"] = i

    return scenes


def serialize_to_fountain(scenes_data: list[dict]) -> str:
    """
    Serialize a list of scene dicts (as returned by parse_fountain, or
    assembled from Scene/Line model instances) back into Fountain text.
    """
    parts: list[str] = []

    for scene in sorted(scenes_data, key=lambda s: s.get("order", 0)):
        lines = sorted(scene.get("lines", []), key=lambda l: l.get("order", 0))
        prev_type = None
        for line in lines:
            ltype = line["type"]
            text = line["text"]
            parts.append(_render_line(ltype, text, prev_type))
            prev_type = ltype
        parts.append("")  # blank line between scenes

    return "\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _skip_title_page(lines: list[str]) -> int:
    """Return index of first non-title-page line."""
    if not lines:
        return 0
    # Title pages have key:value pairs and end with a blank line
    i = 0
    while i < len(lines) and _RE_TITLE_PAGE.match(lines[i].strip()):
        i += 1
    if i > 0 and i < len(lines) and lines[i].strip() == "":
        return i + 1
    return 0


def _split_paragraphs(lines: list[str]) -> Iterator[str]:
    """Yield non-empty paragraphs separated by blank lines."""
    buf: list[str] = []
    for line in lines:
        if line.strip() == "":
            if buf:
                yield "\n".join(buf).strip()
                buf = []
        else:
            buf.append(line)
    if buf:
        yield "\n".join(buf).strip()


def _classify_line(
    text: str, prev_type: str | None, in_dialogue_block: bool = False
) -> tuple[str, str]:
    """
    Classify a single line of text into (element_type, cleaned_text).

    Args:
        text:             The raw line text (trailing whitespace stripped).
        prev_type:        The type of the immediately preceding line (None if
                          we're at the start or after a blank line).
        in_dialogue_block: True if we're inside a character/dialogue block
                          (character cue has been seen, no blank line yet).
    """
    trimmed = text.strip()

    if not trimmed:
        return "action", ""

    # Forced scene heading
    if trimmed.startswith(".") and not trimmed.startswith(".."):
        return "scene_heading", trimmed[1:].strip().upper()

    # Natural scene heading
    if _RE_SCENE_HEADING.match(trimmed):
        return "scene_heading", trimmed.upper()

    # Forced transition
    m = _RE_TRANSITION_FORCED.match(trimmed)
    if m:
        return "transition", m.group(1).strip()

    # Natural transition
    if _RE_TRANSITION_NATURAL.match(trimmed):
        return "transition", trimmed.strip()

    # Parenthetical — only valid inside a dialogue context
    if _RE_PARENTHETICAL.match(trimmed) and in_dialogue_block:
        return "parenthetical", trimmed.strip()

    # Dialogue — only if we're inside a character/dialogue block
    if in_dialogue_block and prev_type in ("character", "parenthetical", "dialogue"):
        return "dialogue", trimmed

    # Character cue — ALL CAPS single line
    # Must not be a scene heading or transition
    if (
        _RE_CHARACTER.match(trimmed)
        and not _RE_SCENE_HEADING.match(trimmed)
        and not _RE_TRANSITION_NATURAL.match(trimmed)
        and len(trimmed.replace(" ", "")) >= 2
    ):
        return "character", trimmed

    # Default: action
    return "action", trimmed


def _render_line(ltype: str, text: str, prev_type: str | None = None) -> str:
    """Render a single line/element to Fountain syntax."""
    if ltype == "scene_heading":
        return f"\n{text.upper()}"
    elif ltype == "action":
        # Add blank line before action if previous was dialogue/parenthetical
        prefix = "\n" if prev_type in ("dialogue", "parenthetical") else ""
        return f"{prefix}{text}"
    elif ltype == "character":
        return f"\n{text.upper()}"
    elif ltype == "dialogue":
        return text
    elif ltype == "parenthetical":
        t = text.strip()
        if not t.startswith("("):
            t = f"({t}"
        if not t.endswith(")"):
            t = f"{t})"
        return t
    elif ltype == "transition":
        return f"\n{text.upper()}\n"
    else:
        return text
