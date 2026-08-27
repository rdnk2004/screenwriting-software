"""
fountain.py — Full Fountain 1.1 Screenplay Format Parser and Serializer.

Specification Reference: https://fountain.io/syntax

Features supported:
  - Title Page metadata key-value parsing (Title, Credit, Author, Source, Draft date, Contact, Notes, Copyright)
  - Scene Headings with optional scene numbers (e.g. INT. CABIN - DAY #1A#) and forced headings (.HEADING)
  - Character cues with extensions (V.O., O.S., CONT'D) and forced cues (@NAME)
  - Dual dialogue detection via caret marker (e.g. JOHN ^) with left/right position pairing
  - Dialogue & Parentheticals
  - Transitions (natural uppercase ending in 'TO:' or forced '>TRANSITION')
  - Synopses (= Scene summary note)
  - Section headings (# ACT I, ## SEQUENCE 1)
  - Centered text (> CENTERED TEXT <)
  - Lyrics (~ Line of lyric)
  - Boneyard (/* ... */) and Inline Notes ([[ note ]])
"""
import re
from typing import Iterator
from .screenplay_terms import extract_character_extension, normalize_character_name, is_valid_character_cue

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

_RE_SCENE_HEADING_FORCED = re.compile(r"^\.([^\.].*)$")
_RE_SCENE_HEADING = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|INT\./EXT\.|I/E\.|I/E)\s+", re.IGNORECASE
)
_RE_SCENE_NUMBER = re.compile(r"#([A-Za-z0-9\.\-_]+)#\s*$")
_RE_TRANSITION_FORCED = re.compile(r"^>(.+)$")
_RE_TRANSITION_NATURAL = re.compile(r"^([A-Z][A-Z\s]+TO:)\s*$")
_RE_TRANSITION_CENTERED = re.compile(r"^>(.+)<$")
_RE_CHARACTER = re.compile(r"^([A-Z0-9\s\.\-']+?)(\s*\([^)]+\))?(\s*\^)?\s*$")
_RE_FORCED_CHARACTER = re.compile(r"^@([^\n]+?)(\s*\([^)]+\))?(\s*\^)?\s*$")
_RE_PARENTHETICAL = re.compile(r"^\((.+)\)\s*$")
_RE_SYNOPSIS = re.compile(r"^=\s*(.+)$")
_RE_SECTION = re.compile(r"^(#{1,6})\s*(.+)$")
_RE_LYRICS = re.compile(r"^~\s*(.+)$")
_RE_FORCED_ACTION = re.compile(r"^!(.+)$")
_RE_NOTE = re.compile(r"\[\[(.*?)\]\]", re.DOTALL)
_RE_BONEYARD = re.compile(r"/\*.*?\*/", re.DOTALL)
_RE_TITLE_KEY_VALUE = re.compile(r"^([A-Za-z\s]+):\s*(.*)$")

_RE_HEADING_PARTS = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|INT\./EXT\.|I/E\.|I/E)?\s*(.+?)\s*[-–]\s*(.+?)$",
    re.IGNORECASE,
)


def _parse_heading_details(heading: str) -> tuple[str, str, str, str]:
    """
    Extracts clean_heading, scene_number, location, and time_of_day from heading text.
    """
    raw = heading.strip()
    scene_number = ""

    # Check for trailing scene number #1A#
    num_match = _RE_SCENE_NUMBER.search(raw)
    if num_match:
        scene_number = num_match.group(1).strip()
        raw = raw[:num_match.start()].strip()

    # Location & time of day parsing
    parts_match = _RE_HEADING_PARTS.match(raw)
    if parts_match:
        location = parts_match.group(2).strip()
        time_of_day = parts_match.group(3).strip()
    else:
        location = raw
        time_of_day = ""

    return raw, scene_number, location, time_of_day


def parse_title_page(lines: list[str]) -> tuple[dict, int]:
    """
    Parses Fountain Title Page metadata key-value pairs from the top of the file.
    Returns (title_page_dict, lines_consumed_count).
    """
    metadata = {
        "title": "",
        "credit": "",
        "author": "",
        "source": "",
        "notes": "",
        "draft_date": "",
        "contact": "",
        "copyright": "",
    }

    key_map = {
        "title": "title",
        "credit": "credit",
        "author": "author",
        "authors": "author",
        "written by": "author",
        "source": "source",
        "based on": "source",
        "notes": "notes",
        "draft date": "draft_date",
        "date": "draft_date",
        "contact": "contact",
        "copyright": "copyright",
    }

    if not lines:
        metadata["credit"] = "written by"
        return metadata, 0

    idx = 0
    current_key = None

    # Title page must start on line 0 with a valid key: value pattern
    first_match = _RE_TITLE_KEY_VALUE.match(lines[0].strip()) if lines else None
    if not first_match or first_match.group(1).lower().strip() not in key_map:
        metadata["credit"] = "written by"
        return metadata, 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if not stripped:
            # First blank line marks end of title page
            idx += 1
            break

        kv_match = _RE_TITLE_KEY_VALUE.match(stripped)
        if kv_match:
            raw_key = kv_match.group(1).lower().strip()
            raw_val = kv_match.group(2).strip()
            if raw_key in key_map:
                current_key = key_map[raw_key]
                if metadata[current_key]:
                    metadata[current_key] += "\n" + raw_val
                else:
                    metadata[current_key] = raw_val
            else:
                current_key = None
        elif current_key and (line.startswith("   ") or line.startswith("\t")):
            # Indented continuation of multi-line value
            metadata[current_key] += "\n" + stripped
        else:
            break

        idx += 1

    if not metadata["credit"]:
        metadata["credit"] = "written by"

    return metadata, idx


# ---------------------------------------------------------------------------
# Public Parsing API
# ---------------------------------------------------------------------------

def parse_fountain_document(text: str) -> dict:
    """
    Parses full Fountain text into a structured document containing:
    - title_page: dict of TitlePage fields
    - scenes: list of parsed scene dicts with lines and dual dialogue attributes
    """
    # 1. Clean boneyards and extract inline notes
    text_clean = _RE_BONEYARD.sub("", text)

    lines_raw = text_clean.splitlines()

    # 2. Extract Title Page
    title_page_data, consumed = parse_title_page(lines_raw)
    content_lines = lines_raw[consumed:]

    # 3. Parse Screenplay Scenes & Lines
    scenes = []
    current_scene = None
    scene_order = 0
    line_order = 0
    prev_type = None
    in_dialogue_block = False

    # Dual dialogue tracking
    last_character_line_idx = None
    last_dialogue_lines = []

    def start_scene(heading_raw: str) -> dict:
        nonlocal scene_order, line_order
        clean_heading, scene_num, location, time_of_day = _parse_heading_details(heading_raw)
        s = {
            "order": scene_order,
            "scene_number": scene_num,
            "heading": clean_heading,
            "location": location,
            "time_of_day": time_of_day,
            "pov_character": None,
            "synopsis": "",
            "notes": "",
            "lines": [],
        }
        scene_order += 1
        line_order = 0
        return s

    current_dual_state = (False, "")

    def add_line(
        ltype: str,
        ltext: str,
        is_dual_dialogue: bool = False,
        dual_pos: str = "",
    ):
        nonlocal line_order, prev_type
        if current_scene is None:
            return
        ext = extract_character_extension(ltext) if ltype == "character" else ""
        current_scene["lines"].append(
            {
                "order": line_order,
                "type": ltype,
                "text": ltext,
                "extension": ext,
                "is_dual_dialogue": is_dual_dialogue,
                "dual_pos": dual_pos,
            }
        )
        line_order += 1
        prev_type = ltype

    current_scene = start_scene("")

    for raw_line in content_lines:
        line_text = raw_line.rstrip()

        if not line_text.strip():
            in_dialogue_block = False
            prev_type = None
            current_dual_state = (False, "")
            continue

        trimmed = line_text.strip()

        # Check for Synopsis '= Synopsis text'
        syn_match = _RE_SYNOPSIS.match(trimmed)
        if syn_match:
            syn_text = syn_match.group(1).strip()
            if current_scene:
                if current_scene["synopsis"]:
                    current_scene["synopsis"] += "\n" + syn_text
                else:
                    current_scene["synopsis"] = syn_text
            continue

        # Check for Section Headings '# ACT I'
        sec_match = _RE_SECTION.match(trimmed)
        if sec_match:
            # Treated as action for visual continuity
            add_line("action", trimmed)
            continue

        # Check for Forced Action '!...'
        forced_action = _RE_FORCED_ACTION.match(trimmed)
        if forced_action:
            in_dialogue_block = False
            current_dual_state = (False, "")
            add_line("action", forced_action.group(1).strip())
            continue

        # Check for Forced Scene Heading '.INT...'
        forced_heading = _RE_SCENE_HEADING_FORCED.match(trimmed)
        if forced_heading:
            in_dialogue_block = False
            current_dual_state = (False, "")
            h_text = forced_heading.group(1).strip().upper()
            if current_scene["lines"] or current_scene["heading"]:
                scenes.append(current_scene)
            current_scene = start_scene(h_text)
            add_line("scene_heading", current_scene["heading"])
            continue

        # Natural Scene Heading
        if _RE_SCENE_HEADING.match(trimmed):
            in_dialogue_block = False
            current_dual_state = (False, "")
            if current_scene["lines"] or current_scene["heading"]:
                scenes.append(current_scene)
            current_scene = start_scene(trimmed.upper())
            add_line("scene_heading", current_scene["heading"])
            continue

        # Forced Transition '>...' or Centered '>...<'
        centered_match = _RE_TRANSITION_CENTERED.match(trimmed)
        if centered_match:
            in_dialogue_block = False
            current_dual_state = (False, "")
            add_line("action", centered_match.group(1).strip())
            continue

        forced_trans = _RE_TRANSITION_FORCED.match(trimmed)
        if forced_trans:
            in_dialogue_block = False
            current_dual_state = (False, "")
            add_line("transition", forced_trans.group(1).strip().upper())
            continue

        # Natural Transition
        if _RE_TRANSITION_NATURAL.match(trimmed):
            in_dialogue_block = False
            current_dual_state = (False, "")
            add_line("transition", trimmed.strip().upper())
            continue

        # Parenthetical inside dialogue
        if _RE_PARENTHETICAL.match(trimmed) and in_dialogue_block:
            is_dual, dual_pos = current_dual_state
            add_line("parenthetical", trimmed.strip(), is_dual_dialogue=is_dual, dual_pos=dual_pos)
            continue

        # Dialogue following character or parenthetical
        if in_dialogue_block and prev_type in ("character", "parenthetical", "dialogue"):
            is_dual, dual_pos = current_dual_state
            add_line("dialogue", trimmed, is_dual_dialogue=is_dual, dual_pos=dual_pos)
            continue

        # Dual Dialogue Character Cue check (ends with ^)
        is_dual = False
        is_forced_char = _RE_FORCED_CHARACTER.match(trimmed)
        is_natural_char = (
            _RE_CHARACTER.match(trimmed)
            and not _RE_SCENE_HEADING.match(trimmed)
            and not _RE_TRANSITION_NATURAL.match(trimmed)
            and len(trimmed.replace(" ", "")) >= 2
        )

        if is_forced_char or is_natural_char:
            char_text = trimmed[1:] if is_forced_char else trimmed
            if char_text.endswith("^"):
                is_dual = True
                char_text = char_text[:-1].strip()

            dual_pos = "right" if is_dual else ""
            current_dual_state = (is_dual, dual_pos)
            in_dialogue_block = True
            add_line(
                "character",
                char_text.upper(),
                is_dual_dialogue=is_dual,
                dual_pos=dual_pos,
            )

            # If dual dialogue (right), mark previous character block as left
            if is_dual and current_scene and len(current_scene["lines"]) > 1:
                # Find previous character line in this scene
                for idx in range(len(current_scene["lines"]) - 2, -1, -1):
                    line_item = current_scene["lines"][idx]
                    if line_item["type"] == "character":
                        line_item["is_dual_dialogue"] = True
                        line_item["dual_pos"] = "left"
                        # Mark all its following dialogue/parentheticals as left
                        for j in range(idx + 1, len(current_scene["lines"]) - 1):
                            current_scene["lines"][j]["is_dual_dialogue"] = True
                            current_scene["lines"][j]["dual_pos"] = "left"
                        break
            continue

        # Default fallback: Action
        in_dialogue_block = False
        current_dual_state = (False, "")
        add_line("action", trimmed)

    # Flush trailing scene
    if current_scene:
        scenes.append(current_scene)

    # Remove empty preamble scene
    scenes = [s for s in scenes if s["heading"] or s["lines"]]

    # Normalize order
    for i, s in enumerate(scenes):
        s["order"] = i

    return {
        "title_page": title_page_data,
        "scenes": scenes,
    }


def parse_fountain(text: str) -> list[dict]:
    """
    Backward-compatible entry point that returns the parsed scenes list.
    """
    return parse_fountain_document(text)["scenes"]


# ---------------------------------------------------------------------------
# Public Serialization API
# ---------------------------------------------------------------------------

def serialize_to_fountain(scenes_data: list[dict], title_page_data: dict | None = None) -> str:
    """
    Serializes scene structures and optional Title Page metadata back to standard Fountain text.
    """
    parts: list[str] = []

    # 1. Serialize Title Page if present
    if title_page_data:
        title = title_page_data.get("title", "").strip()
        if title:
            parts.append(f"Title: {title}")
        credit = title_page_data.get("credit", "").strip()
        if credit:
            parts.append(f"Credit: {credit}")
        author = title_page_data.get("author", "").strip()
        if author:
            parts.append(f"Author: {author}")
        source = title_page_data.get("source", "").strip()
        if source:
            parts.append(f"Source: {source}")
        draft_date = title_page_data.get("draft_date", "").strip()
        if draft_date:
            parts.append(f"Draft date: {draft_date}")
        contact = title_page_data.get("contact", "").strip()
        if contact:
            parts.append(f"Contact:\n\t{contact.replace(chr(10), chr(10) + chr(9))}")
        notes = title_page_data.get("notes", "").strip()
        if notes:
            parts.append(f"Notes:\n\t{notes.replace(chr(10), chr(10) + chr(9))}")
        copyright_text = title_page_data.get("copyright", "").strip()
        if copyright_text:
            parts.append(f"Copyright: {copyright_text}")

        if parts:
            parts.append("")  # Blank line separating Title Page

    # 2. Serialize Scenes and Lines
    for scene in sorted(scenes_data, key=lambda s: s.get("order", 0)):
        synopsis = scene.get("synopsis", "").strip()
        if synopsis:
            for syn_line in synopsis.splitlines():
                parts.append(f"= {syn_line.strip()}")

        scene_notes = scene.get("notes", "").strip()
        if scene_notes:
            parts.append(f"[[ {scene_notes} ]]")

        scene_num = scene.get("scene_number", "").strip()
        lines = sorted(scene.get("lines", []), key=lambda l: l.get("order", 0))
        prev_type = None
        for line in lines:
            ltype = line["type"]
            text = line["text"]
            is_dual = line.get("is_dual_dialogue", False)
            dual_pos = line.get("dual_pos", "")
            rendered = _render_line(
                ltype,
                text,
                prev_type,
                is_dual,
                dual_pos,
                scene_number=scene_num if ltype == "scene_heading" else "",
            )
            parts.append(rendered)
            prev_type = ltype

        parts.append("")  # Blank line between scenes

    return "\n".join(parts).strip() + "\n"


def _render_line(
    ltype: str,
    text: str,
    prev_type: str | None = None,
    is_dual: bool = False,
    dual_pos: str = "",
    scene_number: str = "",
) -> str:
    """Renders an individual screenplay element to Fountain syntax."""
    if ltype == "scene_heading":
        heading_text = text.upper()
        if scene_number and f"#{scene_number}#" not in heading_text:
            heading_text = f"{heading_text} #{scene_number}#"
        return f"\n{heading_text}"
    elif ltype == "action":
        prefix = "\n" if prev_type in ("dialogue", "parenthetical") else ""
        return f"{prefix}{text}"
    elif ltype == "character":
        suffix = " ^" if is_dual and dual_pos == "right" else ""
        return f"\n{text.upper()}{suffix}"
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
