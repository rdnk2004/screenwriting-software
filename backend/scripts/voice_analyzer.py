"""
voice_analyzer.py — Character Voice Distinctiveness & Dialogue Homogenization Analyzer.

Evaluates screenplay dialogue to determine each character's unique linguistic fingerprint:
  - Lexical Diversity (Type-Token Ratio / vocabulary richness)
  - Cadence & Utterance Rhythm (Words per dialogue line, standard deviation)
  - Punctuation & Rhetorical Distribution (?, !, ..., --, .)
  - Unique Keyword Fingerprints (TF-IDF / relative distinctiveness)
  - Distinctiveness Score (0-100) comparing character against script average
  - Pairwise Voice Overlap Matrix to detect dialogue homogenization between cast members
"""
import re
import math
from collections import Counter, defaultdict
from .screenplay_terms import normalize_character_name

# Common English dialogue stop words to filter out when discovering distinctive vocabulary
COMMON_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "just", "like", "yeah", "okay",
    "well", "oh", "gonna", "gotta", "wanna", "um", "uh"
}

_RE_WORDS = re.compile(r"\b[a-zA-Z']+\b")


def _tokenize_text(text: str) -> list[str]:
    """Extracts lowercase alphabetic words from text."""
    return [w.lower() for w in _RE_WORDS.findall(text)]


def _calculate_punctuation_profile(lines: list[str]) -> dict:
    """Calculates distribution of rhetorical punctuation marks."""
    total_lines = len(lines)
    if total_lines == 0:
        return {"questions": 0, "exclamations": 0, "hesitations": 0, "declaratives": 0}

    q_count = sum(1 for line in lines if "?" in line)
    e_count = sum(1 for line in lines if "!" in line)
    h_count = sum(1 for line in lines if ("..." in line or "--" in line or "—" in line))
    d_count = sum(1 for line in lines if ("." in line and "?" not in line and "!" not in line and "..." not in line))

    return {
        "questions_pct": round((q_count / total_lines) * 100.0, 1),
        "exclamations_pct": round((e_count / total_lines) * 100.0, 1),
        "hesitations_pct": round((h_count / total_lines) * 100.0, 1),
        "declaratives_pct": round((d_count / total_lines) * 100.0, 1),
    }


def analyze_character_voices(script) -> dict:
    """
    Performs comprehensive voice distinctiveness analysis for all speaking characters in a script.

    Returns:
        {
            "characters": [
                {
                    "name": str,
                    "total_dialogue_lines": int,
                    "total_words": int,
                    "words_per_line": float,
                    "lexical_diversity_ttr": float,
                    "avg_word_length": float,
                    "distinctiveness_score": float,
                    "cadence_label": str ("Snappy / Rapid", "Balanced", "Monologue / Verbose"),
                    "punctuation_profile": dict,
                    "top_keywords": list[str],
                },
                ...
            ],
            "similarity_matrix": [
                {
                    "character_a": str,
                    "character_b": str,
                    "similarity_score": float,
                    "homogenization_risk": str ("High", "Moderate", "Distinct"),
                },
                ...
            ]
        }
    """
    scenes = script.scenes.prefetch_related("lines").all().order_by("order")

    # Collect dialogue lines per character
    character_lines = defaultdict(list)
    script_all_words = []

    for s in scenes:
        curr_char = ""
        for line in s.lines.all().order_by("order"):
            if line.type == "character":
                curr_char = normalize_character_name(line.text)
            elif line.type == "dialogue" and curr_char:
                character_lines[curr_char].append(line.text)
                words = _tokenize_text(line.text)
                script_all_words.extend(words)

    # Filter characters with at least 2 dialogue lines for statistical significance
    significant_chars = {
        name: lines for name, lines in character_lines.items() if len(lines) >= 2
    }

    if not significant_chars:
        return {"characters": [], "similarity_matrix": []}

    # Baseline script statistics
    total_script_words_count = len(script_all_words)
    global_word_counts = Counter(script_all_words)

    char_profiles = []
    char_word_vectors = {}

    for name, lines in sorted(significant_chars.items(), key=lambda x: len(x[1]), reverse=True):
        words = []
        for line in lines:
            words.extend(_tokenize_text(line))

        total_words = len(words)
        unique_words = len(set(words))
        total_lines = len(lines)

        w_per_line = round(total_words / total_lines, 1) if total_lines > 0 else 0.0
        ttr = round(unique_words / total_words, 2) if total_words > 0 else 0.0
        avg_word_len = round(sum(len(w) for w in words) / total_words, 1) if total_words > 0 else 0.0

        # Cadence category
        if w_per_line < 6.0:
            cadence = "Snappy / Rapid"
        elif w_per_line >= 10.0:
            cadence = "Monologue / Verbose"
        else:
            cadence = "Balanced"

        # Punctuation
        p_profile = _calculate_punctuation_profile(lines)

        # Top distinctive keywords using TF-IDF style weighting against script baseline
        char_word_counts = Counter(words)
        char_word_vectors[name] = char_word_counts

        distinctive_scores = {}
        for w, c_count in char_word_counts.items():
            if w in COMMON_STOP_WORDS or len(w) <= 2:
                continue
            tf = c_count / total_words
            # Inverse document / global frequency
            gf = global_word_counts.get(w, 1) / total_script_words_count
            distinctive_scores[w] = tf / (gf + 0.001)

        top_keywords = [
            w for w, _ in sorted(distinctive_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Distinctiveness Score (0-100) based on TTR, cadence variation, and unique vocabulary
        # Normal baseline ~50
        base_distinctiveness = min(100.0, max(10.0, round((ttr * 50.0) + (abs(w_per_line - 9.0) * 3.5) + (len(top_keywords) * 4.0), 1)))

        char_profiles.append({
            "name": name,
            "total_dialogue_lines": total_lines,
            "total_words": total_words,
            "words_per_line": w_per_line,
            "lexical_diversity_ttr": ttr,
            "avg_word_length": avg_word_len,
            "distinctiveness_score": base_distinctiveness,
            "cadence_label": cadence,
            "punctuation_profile": p_profile,
            "top_keywords": top_keywords,
        })

    # Pairwise Cosine Similarity Matrix between character vocabularies
    similarity_matrix = []
    char_names = list(char_word_vectors.keys())
    for i in range(len(char_names)):
        for j in range(i + 1, len(char_names)):
            name_a = char_names[i]
            name_b = char_names[j]
            vec_a = char_word_vectors[name_a]
            vec_b = char_word_vectors[name_b]

            # Cosine similarity
            all_keys = set(vec_a.keys()) | set(vec_b.keys())
            dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in all_keys)
            norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
            norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

            if norm_a > 0 and norm_b > 0:
                sim = round(dot / (norm_a * norm_b), 2)
            else:
                sim = 0.0

            if sim >= 0.75:
                risk = "High (Dialogue Homogenization Risk)"
            elif sim >= 0.50:
                risk = "Moderate"
            else:
                risk = "Distinct"

            similarity_matrix.append({
                "character_a": name_a,
                "character_b": name_b,
                "similarity_score": sim,
                "homogenization_risk": risk,
            })

    return {
        "characters": char_profiles,
        "similarity_matrix": similarity_matrix,
    }
