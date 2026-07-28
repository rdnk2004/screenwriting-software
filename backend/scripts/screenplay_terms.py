"""
screenplay_terms.py — Reserved screenwriting terms, transition tokens, scene heading elements,
and character cue validation/normalization utilities.
"""
import re

TRANSITIONS = {
    "CUT TO:",
    "SMASH CUT TO:",
    "MATCH CUT TO:",
    "DISSOLVE TO:",
    "FADE IN:",
    "FADE OUT.",
    "FADE TO BLACK.",
    "JUMP CUT TO:",
    "TIME CUT:",
    "INTERCUT WITH:",
}

SCENE_HEADING_TOKENS = {
    "INT.",
    "EXT.",
    "INT./EXT.",
    "I/E",
    "DAY",
    "NIGHT",
    "CONTINUOUS",
    "LATER",
    "MOMENTS LATER",
    "DAWN",
    "DUSK",
    "SAME TIME",
}

NON_CHARACTER_CAPS = {
    "ANGLE ON",
    "CLOSE ON",
    "CLOSE-UP",
    "EXTREME CLOSE-UP",
    "WIDE SHOT",
    "POV",
    "INSERT",
    "ESTABLISHING SHOT",
    "BACK TO SCENE",
    "MONTAGE",
    "SERIES OF SHOTS",
    "END MONTAGE",
    "TITLE CARD",
    "SUPER:",
    "TEXT ON SCREEN",
    "END OF ACT",
}

CHARACTER_EXTENSIONS = re.compile(
    r"\s*\((?:V\.O\.|O\.S\.|O\.C\.|CONT'D|CONT|PRE-LAP|FILTERED|ON PHONE)\)",
    re.IGNORECASE,
)

_RE_PURE_SCENE_HEADING = re.compile(
    r"^\s*(INT\.|EXT\.|INT/\s*EXT\.|INT\./\s*EXT\.|I/E\.|I/E\b)",
    re.IGNORECASE,
)

ALL_RESERVED_TERMS = TRANSITIONS | SCENE_HEADING_TOKENS | NON_CHARACTER_CAPS


def extract_character_extension(text: str) -> str:
    """
    Extract character extension (e.g. 'V.O.') from line text if present using CHARACTER_EXTENSIONS.
    """
    if not text:
        return ""
    match = CHARACTER_EXTENSIONS.search(text)
    if match:
        raw_ext = match.group(0).strip()
        if raw_ext.startswith("(") and raw_ext.endswith(")"):
            return raw_ext[1:-1].strip()
        return raw_ext
    return ""


def is_valid_character_cue(text: str) -> bool:
    """
    Validates whether a line text is a valid character cue or should be rejected as a structural term.
    """
    if not text or not text.strip():
        return False

    raw = text.strip()

    # Reject pure scene headings (e.g. INT., EXT., INT./EXT., I/E regardless of what follows)
    if _RE_PURE_SCENE_HEADING.match(raw):
        return False

    # Strip character extension before checking
    base = CHARACTER_EXTENSIONS.sub("", raw).strip()
    if not base:
        return False

    def _trim(s: str) -> str:
        return re.sub(r"[\s\.,:;\!\?\-_]+$", "", s).strip().upper()

    base_trimmed = _trim(base)
    raw_trimmed = _trim(raw)

    for term in ALL_RESERVED_TERMS:
        term_trimmed = _trim(term)
        if not term_trimmed:
            continue

        # 1. Exact match (case-insensitive, trimming trailing punctuation)
        if base_trimmed == term_trimmed or raw_trimmed == term_trimmed:
            return False

        # 2. Starts with term
        pattern_start = r"^" + re.escape(term_trimmed) + r"(\b|[^A-Z0-9]|$)"
        if re.search(pattern_start, base_trimmed) or re.search(pattern_start, raw_trimmed):
            return False

        # 3. Ends with term
        pattern_end = r"(^|[^A-Z0-9]|\b)" + re.escape(term_trimmed) + r"$"
        if re.search(pattern_end, base_trimmed) or re.search(pattern_end, raw_trimmed):
            return False

    return True


def normalize_character_name(text: str) -> str:
    """
    Normalizes character line cue text by stripping extensions (e.g. (V.O.)) and extra whitespace,
    returning uppercase string. Returns empty string if invalid character cue.
    """
    if not text or not is_valid_character_cue(text):
        return ""
    cleaned = CHARACTER_EXTENSIONS.sub("", text)
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)
    return cleaned.strip().upper()
