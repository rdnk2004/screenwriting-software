"""
table_read.py — Multi-Voice Table Read Manifest Generation Service.

Converts a screenplay into a synchronized, multi-speaker Table Read audio manifest:
  - Role assignment: Maps screenplay lines to NARRATOR (sluglines, action) or distinct Character actors.
  - Vocal direction parsing: Extracts vocal delivery hints from parentheticals (e.g. whisper, shouting, laughing, sarcastic).
  - Audio staging flags: Identifies V.O. (Voice-Over), O.S. (Off-Screen), and Dual Dialogue positioning.
  - Timing estimation: Calculates speech durations per block (150 words/min speech rate baseline).
  - Voice cast roster: Summarizes all cast voices, lines, words, and default synthesized persona profiles.
"""
import re
from collections import defaultdict
from .screenplay_terms import normalize_character_name, extract_character_extension

# Speech rate: ~150 words per minute -> 2.5 words per second
WORDS_PER_SECOND = 2.5
PAUSE_AFTER_SCENE_HEADING_SECONDS = 0.8
PAUSE_AFTER_ACTION_BLOCK_SECONDS = 0.4
PAUSE_AFTER_SPEECH_SECONDS = 0.3

# Vocal delivery direction keywords from parentheticals
EMOTION_KEYWORDS = {
    "whisper": "whispering",
    "whispers": "whispering",
    "whispering": "whispering",
    "shout": "shouting",
    "shouts": "shouting",
    "shouting": "shouting",
    "yell": "shouting",
    "yells": "shouting",
    "yelling": "shouting",
    "scream": "screaming",
    "screams": "screaming",
    "screaming": "screaming",
    "laugh": "laughing",
    "laughs": "laughing",
    "laughing": "laughing",
    "chuckle": "laughing",
    "chuckles": "laughing",
    "crying": "crying",
    "cries": "crying",
    "sobbing": "crying",
    "sarcastic": "sarcastic",
    "sarcastically": "sarcastic",
    "angry": "angry",
    "angrily": "angry",
    "coldly": "cold",
    "nervous": "nervous",
    "nervously": "nervous",
    "quietly": "quiet",
    "softly": "soft",
    "singing": "singing",
}


def _detect_emotion_hint(parenthetical_text: str) -> str:
    """Extracts emotional/vocal delivery modifier from parenthetical text."""
    if not parenthetical_text:
        return "neutral"
    clean = re.sub(r"[^\w\s]", "", parenthetical_text.lower()).strip()
    words = clean.split()
    for w in words:
        if w in EMOTION_KEYWORDS:
            return EMOTION_KEYWORDS[w]
    return "neutral"


def _estimate_duration(text: str, base_pause: float = 0.3) -> float:
    """Estimates duration in seconds based on word count and base pause."""
    word_count = len(text.split())
    if word_count == 0:
        return base_pause
    duration = (word_count / WORDS_PER_SECOND) + base_pause
    return round(duration, 2)


def generate_table_read_manifest(
    script,
    narrator_voice_name: str = "Narrator",
    voice_mapping: dict | None = None,
    include_action_in_read: bool = True,
) -> dict:
    """
    Builds a complete, sequential Table Read audio cues manifest for a screenplay.

    Returns:
        {
            "summary": {
                "total_blocks": int,
                "total_spoken_words": int,
                "estimated_runtime_seconds": float,
                "estimated_runtime_formatted": str ("MM:SS" or "HH:MM:SS"),
                "total_cast_roles": int,
            },
            "roles": [
                {
                    "name": str,
                    "voice_persona_id": str,
                    "is_narrator": bool,
                    "total_lines": int,
                    "total_words": int,
                },
                ...
            ],
            "timeline": [
                {
                    "block_index": int,
                    "scene_id": int,
                    "scene_number": str,
                    "scene_heading": str,
                    "speaker": str,
                    "is_narrator": bool,
                    "text": str,
                    "direction": str,
                    "emotion_hint": str,
                    "audio_effect": str ("none", "spatial_offscreen", "intimate_voiceover"),
                    "is_dual_dialogue": bool,
                    "dual_pos": str,
                    "word_count": int,
                    "estimated_duration_seconds": float,
                },
                ...
            ]
        }
    """
    scenes = script.scenes.prefetch_related("lines").all().order_by("order")
    voice_map = voice_mapping or {}

    timeline = []
    block_index = 0
    total_spoken_words = 0
    total_duration_sec = 0.0

    roles_stats = defaultdict(lambda: {"total_lines": 0, "total_words": 0, "is_narrator": False})

    # Narrator baseline
    roles_stats[narrator_voice_name]["is_narrator"] = True

    for scene in scenes:
        scene_heading = scene.heading or f"SCENE {scene.order + 1}"
        scene_num_label = scene.scene_number or f"{scene.order + 1}"

        # 1. Narrator Scene Slugline Block
        if scene.heading:
            words_cnt = len(scene.heading.split())
            dur = _estimate_duration(scene.heading, base_pause=PAUSE_AFTER_SCENE_HEADING_SECONDS)
            timeline.append({
                "block_index": block_index,
                "scene_id": scene.id,
                "scene_number": scene_num_label,
                "scene_heading": scene_heading,
                "speaker": narrator_voice_name,
                "is_narrator": True,
                "text": scene.heading,
                "direction": "",
                "emotion_hint": "declarative",
                "audio_effect": "none",
                "is_dual_dialogue": False,
                "dual_pos": "",
                "word_count": words_cnt,
                "estimated_duration_seconds": dur,
            })
            block_index += 1
            total_spoken_words += words_cnt
            total_duration_sec += dur
            roles_stats[narrator_voice_name]["total_lines"] += 1
            roles_stats[narrator_voice_name]["total_words"] += words_cnt

        # 2. Iterate through scene lines
        lines = list(scene.lines.all().order_by("order"))
        idx = 0

        while idx < len(lines):
            line = lines[idx]
            ltype = line.type
            text = line.text.strip()

            if not text:
                idx += 1
                continue

            # Action Line (Narrator)
            if ltype == "action" and include_action_in_read:
                words_cnt = len(text.split())
                dur = _estimate_duration(text, base_pause=PAUSE_AFTER_ACTION_BLOCK_SECONDS)
                timeline.append({
                    "block_index": block_index,
                    "scene_id": scene.id,
                    "scene_number": scene_num_label,
                    "scene_heading": scene_heading,
                    "speaker": narrator_voice_name,
                    "is_narrator": True,
                    "text": text,
                    "direction": "",
                    "emotion_hint": "neutral",
                    "audio_effect": "none",
                    "is_dual_dialogue": False,
                    "dual_pos": "",
                    "word_count": words_cnt,
                    "estimated_duration_seconds": dur,
                })
                block_index += 1
                total_spoken_words += words_cnt
                total_duration_sec += dur
                roles_stats[narrator_voice_name]["total_lines"] += 1
                roles_stats[narrator_voice_name]["total_words"] += words_cnt
                idx += 1
                continue

            # Character Speech Block (Character + optional Parenthetical + Dialogue)
            elif ltype == "character":
                char_name = normalize_character_name(text)
                ext = extract_character_extension(text) or line.extension
                is_dual = line.is_dual_dialogue
                dual_pos = line.dual_pos

                # Audio spatial effect
                if "V.O." in ext:
                    audio_effect = "intimate_voiceover"
                elif "O.S." in ext or "O.C." in ext:
                    audio_effect = "spatial_offscreen"
                else:
                    audio_effect = "none"

                parenthetical_text = ""
                dialogue_texts = []
                idx += 1

                # Gather following parentheticals and dialogue in this cue block
                while idx < len(lines) and lines[idx].type in ("parenthetical", "dialogue"):
                    sub_line = lines[idx]
                    if sub_line.type == "parenthetical":
                        parenthetical_text = sub_line.text.strip("()")
                    elif sub_line.type == "dialogue":
                        dialogue_texts.append(sub_line.text.strip())
                    idx += 1

                if dialogue_texts:
                    full_dialogue = " ".join(dialogue_texts)
                    emotion = _detect_emotion_hint(parenthetical_text)
                    words_cnt = len(full_dialogue.split())
                    dur = _estimate_duration(full_dialogue, base_pause=PAUSE_AFTER_SPEECH_SECONDS)

                    timeline.append({
                        "block_index": block_index,
                        "scene_id": scene.id,
                        "scene_number": scene_num_label,
                        "scene_heading": scene_heading,
                        "speaker": char_name,
                        "is_narrator": False,
                        "text": full_dialogue,
                        "direction": parenthetical_text,
                        "emotion_hint": emotion,
                        "audio_effect": audio_effect,
                        "is_dual_dialogue": is_dual,
                        "dual_pos": dual_pos,
                        "word_count": words_cnt,
                        "estimated_duration_seconds": dur,
                    })
                    block_index += 1
                    total_spoken_words += words_cnt
                    total_duration_sec += dur
                    roles_stats[char_name]["total_lines"] += len(dialogue_texts)
                    roles_stats[char_name]["total_words"] += words_cnt
                continue

            idx += 1

    # Build roles manifest
    roles_output = []
    for role_name, r_data in sorted(roles_stats.items(), key=lambda x: (not x[1]["is_narrator"], -x[1]["total_words"])):
        # Default synthetic voice persona assignment heuristic
        persona = voice_map.get(role_name, f"voice-{role_name.lower().replace(' ', '-')}")
        roles_output.append({
            "name": role_name,
            "voice_persona_id": persona,
            "is_narrator": r_data["is_narrator"],
            "total_lines": r_data["total_lines"],
            "total_words": r_data["total_words"],
        })

    # Format runtime
    total_seconds_int = int(round(total_duration_sec))
    hours = total_seconds_int // 3600
    minutes = (total_seconds_int % 3600) // 60
    seconds = total_seconds_int % 60
    if hours > 0:
        runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        runtime_str = f"{minutes:02d}:{seconds:02d}"

    return {
        "summary": {
            "total_blocks": len(timeline),
            "total_spoken_words": total_spoken_words,
            "estimated_runtime_seconds": round(total_duration_sec, 1),
            "estimated_runtime_formatted": runtime_str,
            "total_cast_roles": len(roles_output),
        },
        "roles": roles_output,
        "timeline": timeline,
    }
