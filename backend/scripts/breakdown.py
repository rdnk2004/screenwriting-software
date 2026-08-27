"""
breakdown.py — Hollywood Production Breakdown & 1/8th Page Calculation Service.

Implements the standard industry production scheduling system (Movie Magic Scheduling / AD Breakdown specs):
  - 1 Page = 8 Eighths (1/8th page ≈ 6.8 vertical line units)
  - Minimum scene measurement: 1/8th page
  - Scene-by-scene production sheets with INT/EXT classification, page length, and speaking cast
  - Location breakdown with set counts and day/night schedule requirements
  - Cast breakdown with total scene appearances, dialogue line counts, word counts, and screen eighths
  - Day/Night and INT/EXT aggregate shooting matrices
"""
import re
from typing import Any
from collections import defaultdict
from .screenplay_terms import normalize_character_name, extract_character_extension

# Standard vertical line height weight in Courier 12pt formatting (accounting for spacing)
# Scene heading: ~2 lines (with top margin)
# Character: ~2 lines (with top margin)
# Parenthetical: ~1 line
# Dialogue: ~1 line
# Action: ~1.5 lines (with paragraph margins)
# Transition: ~2 lines
LINE_WEIGHTS = {
    "scene_heading": 2.0,
    "action": 1.5,
    "character": 1.8,
    "dialogue": 1.0,
    "parenthetical": 1.0,
    "transition": 2.0,
}

LINES_PER_PAGE = 54.0
LINES_PER_EIGHTH = LINES_PER_PAGE / 8.0  # 6.75 vertical lines per 1/8th page


def format_eighths(eighths: int) -> str:
    """
    Formats an integer number of eighths into standard Hollywood notation.
    Examples:
        0 -> "0"
        1 -> "1/8"
        4 -> "4/8"
        8 -> "1"
        11 -> "1 3/8"
        16 -> "2"
        19 -> "2 3/8"
    """
    if eighths <= 0:
        return "0"
    pages = eighths // 8
    rem = eighths % 8
    if pages == 0:
        return f"{rem}/8"
    elif rem == 0:
        return f"{pages}"
    else:
        return f"{pages} {rem}/8"


def calculate_scene_eighths(lines: list[Any]) -> int:
    """
    Calculates the 1/8th page count for a list of scene lines based on standard physical line heights.
    Minimum length for any non-empty scene is 1 eighth (1/8).
    """
    if not lines:
        return 1

    total_weight = 0.0
    for line in lines:
        if isinstance(line, dict):
            ltype = line.get("type", "action")
            text = line.get("text", "")
        else:
            ltype = getattr(line, "type", "action")
            text = getattr(line, "text", "")

        weight = LINE_WEIGHTS.get(ltype, 1.0)
        # Estimate additional line wrapping for long action or dialogue lines (> 60 chars)
        text_len = len(text)
        wrap_lines = max(1, (text_len // 55) + 1) if text_len > 55 else 1
        total_weight += weight * wrap_lines

    eighths = int(round(total_weight / LINES_PER_EIGHTH))
    return max(1, eighths)


def classify_int_ext(heading: str) -> str:
    """Classifies a scene slugline into INT, EXT, INT/EXT, or OTHER."""
    h = heading.upper().strip()
    if h.startswith("INT/EXT") or h.startswith("INT./EXT") or h.startswith("I/E"):
        return "INT/EXT"
    elif h.startswith("INT.") or h.startswith("INT"):
        return "INT"
    elif h.startswith("EXT.") or h.startswith("EXT"):
        return "EXT"
    return "OTHER"


def normalize_time_of_day(tod: str) -> str:
    """Normalizes time of day to standard production categories (DAY, NIGHT, DUSK, DAWN, CONTINUOUS)."""
    t = tod.upper().strip()
    if not t:
        return "DAY"
    if "NIGHT" in t or "LATE" in t or "MIDNIGHT" in t:
        return "NIGHT"
    if "DUSK" in t or "SUNSET" in t or "EVENING" in t:
        return "DUSK"
    if "DAWN" in t or "SUNRISE" in t or "MORNING" in t:
        return "DAWN"
    if "CONTINUOUS" in t or "SAME" in t:
        return "CONTINUOUS"
    return "DAY"


def generate_production_breakdown(script) -> dict:
    """
    Generates a full Hollywood Production Breakdown report from a Script database instance.

    Returns:
        {
            "summary": {
                "total_scenes": int,
                "total_eighths": int,
                "total_pages_str": str,
                "estimated_running_time_seconds": float,
                "unique_locations_count": int,
                "speaking_characters_count": int,
            },
            "shooting_matrix": {
                "INT_DAY": {"scenes": int, "eighths": int, "pages_str": str},
                "INT_NIGHT": {"scenes": int, "eighths": int, "pages_str": str},
                "EXT_DAY": {"scenes": int, "eighths": int, "pages_str": str},
                "EXT_NIGHT": {"scenes": int, "eighths": int, "pages_str": str},
                "OTHER": {"scenes": int, "eighths": int, "pages_str": str},
            },
            "scenes": [
                {
                    "id": int,
                    "scene_number": str,
                    "order": int,
                    "heading": str,
                    "int_ext": str,
                    "location": str,
                    "time_of_day": str,
                    "eighths": int,
                    "page_length_str": str,
                    "estimated_seconds": float,
                    "cast": list[str],
                    "synopsis": str,
                },
                ...
            ],
            "locations": [
                {
                    "name": str,
                    "scene_count": int,
                    "eighths": int,
                    "page_length_str": str,
                    "day_scenes": int,
                    "night_scenes": int,
                },
                ...
            ],
            "cast": [
                {
                    "name": str,
                    "scene_count": int,
                    "dialogue_line_count": int,
                    "dialogue_word_count": int,
                    "total_eighths": int,
                    "first_appearance_scene": str,
                    "last_appearance_scene": str,
                },
                ...
            ]
        }
    """
    scenes_qs = script.scenes.prefetch_related("lines").all().order_by("order")

    scene_breakdowns = []
    location_map = defaultdict(lambda: {"scene_count": 0, "eighths": 0, "day_scenes": 0, "night_scenes": 0})
    cast_map = defaultdict(lambda: {
        "name": "",
        "scene_count": 0,
        "dialogue_line_count": 0,
        "dialogue_word_count": 0,
        "total_eighths": 0,
        "first_scene": "",
        "last_scene": "",
        "_scenes_seen": set(),
    })

    shooting_matrix = {
        "INT_DAY": {"scenes": 0, "eighths": 0},
        "INT_NIGHT": {"scenes": 0, "eighths": 0},
        "EXT_DAY": {"scenes": 0, "eighths": 0},
        "EXT_NIGHT": {"scenes": 0, "eighths": 0},
        "OTHER": {"scenes": 0, "eighths": 0},
    }

    total_eighths = 0

    for s in scenes_qs:
        lines = list(s.lines.all().order_by("order"))
        eighths = calculate_scene_eighths(lines)
        total_eighths += eighths

        int_ext = classify_int_ext(s.heading)
        tod_category = normalize_time_of_day(s.time_of_day)

        # Update shooting matrix
        if int_ext in ("INT", "EXT") and tod_category in ("DAY", "NIGHT"):
            matrix_key = f"{int_ext}_{tod_category}"
        else:
            matrix_key = "OTHER"
        shooting_matrix[matrix_key]["scenes"] += 1
        shooting_matrix[matrix_key]["eighths"] += eighths

        # Identify speaking cast and word counts in this scene
        scene_cast_names = set()
        for line in lines:
            if line.type == "character":
                char_name = normalize_character_name(line.text)
                if char_name:
                    scene_cast_names.add(char_name)
                    c_data = cast_map[char_name]
                    c_data["name"] = char_name
                    if s.id not in c_data["_scenes_seen"]:
                        c_data["_scenes_seen"].add(s.id)
                        c_data["scene_count"] += 1
                        c_data["total_eighths"] += eighths
                        s_label = s.scene_number or f"Scene {s.order + 1}"
                        if not c_data["first_scene"]:
                            c_data["first_scene"] = s_label
                        c_data["last_scene"] = s_label

            elif line.type == "dialogue":
                # Find previous character
                pass

        # Count dialogue lines and words per character
        curr_char = ""
        for line in lines:
            if line.type == "character":
                curr_char = normalize_character_name(line.text)
            elif line.type == "dialogue" and curr_char:
                c_data = cast_map[curr_char]
                c_data["dialogue_line_count"] += 1
                c_data["dialogue_word_count"] += len(line.text.split())

        # Update Location map
        clean_loc = (s.location or s.heading).upper().strip()
        loc_data = location_map[clean_loc]
        loc_data["scene_count"] += 1
        loc_data["eighths"] += eighths
        if tod_category == "NIGHT":
            loc_data["night_scenes"] += 1
        else:
            loc_data["day_scenes"] += 1

        scene_breakdowns.append({
            "id": s.id,
            "scene_number": s.scene_number or f"{s.order + 1}",
            "order": s.order,
            "heading": s.heading,
            "int_ext": int_ext,
            "location": s.location or clean_loc,
            "time_of_day": s.time_of_day,
            "eighths": eighths,
            "page_length_str": format_eighths(eighths),
            "estimated_seconds": round(eighths * 7.5, 1),
            "cast": sorted(list(scene_cast_names)),
            "synopsis": s.synopsis,
        })

    # Prepare shooting matrix output
    matrix_output = {}
    for k, v in shooting_matrix.items():
        matrix_output[k] = {
            "scenes": v["scenes"],
            "eighths": v["eighths"],
            "pages_str": format_eighths(v["eighths"]),
        }

    # Prepare locations output
    locations_output = []
    for loc_name, loc_info in sorted(location_map.items(), key=lambda x: x[1]["eighths"], reverse=True):
        locations_output.append({
            "name": loc_name,
            "scene_count": loc_info["scene_count"],
            "eighths": loc_info["eighths"],
            "page_length_str": format_eighths(loc_info["eighths"]),
            "day_scenes": loc_info["day_scenes"],
            "night_scenes": loc_info["night_scenes"],
        })

    # Prepare cast output
    cast_output = []
    for char_name, c_info in sorted(cast_map.items(), key=lambda x: x[1]["dialogue_word_count"], reverse=True):
        cast_output.append({
            "name": char_name,
            "scene_count": c_info["scene_count"],
            "dialogue_line_count": c_info["dialogue_line_count"],
            "dialogue_word_count": c_info["dialogue_word_count"],
            "total_eighths": c_info["total_eighths"],
            "first_appearance_scene": c_info["first_scene"],
            "last_appearance_scene": c_info["last_scene"],
        })

    total_scenes_count = len(scenes_qs)
    summary = {
        "total_scenes": total_scenes_count,
        "total_eighths": total_eighths,
        "total_pages_str": format_eighths(total_eighths),
        "estimated_running_time_seconds": round(total_eighths * 7.5, 1),
        "unique_locations_count": len(locations_output),
        "speaking_characters_count": len(cast_output),
    }

    return {
        "summary": summary,
        "shooting_matrix": matrix_output,
        "scenes": scene_breakdowns,
        "locations": locations_output,
        "cast": cast_output,
    }
