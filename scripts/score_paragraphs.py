#!/usr/bin/env python3
"""
ClueChain Paragraph Quality Scorer

Scores paragraphs on multiple quality dimensions using a hybrid approach:
- Rule-based scores (spaCy POS tagging, variety metrics) — fast, no API calls
- LLM scores (Groq) for subjective dimensions — one call per paragraph

Usage:
    python scripts/score_paragraphs.py                     # Score all unscored (resumes)
    python scripts/score_paragraphs.py --batch-size 20     # Score only 20 unscored then stop
    python scripts/score_paragraphs.py --force              # Re-score everything
    python scripts/score_paragraphs.py --file <path>        # Score single file
    python scripts/score_paragraphs.py --dry-run            # Show what would be scored
    python scripts/score_paragraphs.py --delay 2.0          # Custom API delay

Requirements:
    - GROQ_API_KEY in .env file (for LLM scoring)
    - python -m spacy download en_core_web_sm
"""

import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: Missing python-dotenv. Run: uv pip install python-dotenv")
    sys.exit(1)

try:
    import spacy
except ImportError:
    print("Error: Missing spacy. Run: uv pip install spacy")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROQ_MODEL = "llama-3.3-70b-versatile"
_SCRIPT_DIR = Path(__file__).parent
_PROMPTS_DIR = _SCRIPT_DIR / "prompts"
_OUTPUT_DIR = _SCRIPT_DIR / "output"
_DATA_DIR = _SCRIPT_DIR.parent / "assets" / "data"
_SCORES_FILE = _OUTPUT_DIR / "paragraph_scores.json"
_RANKINGS_CSV = _OUTPUT_DIR / "paragraph_rankings.csv"
_RANKINGS_MD = _OUTPUT_DIR / "paragraph_rankings.md"

# Weights for final score calculation
WEIGHTS = {
    "word_quality": 0.30,
    "variety": 0.15,
    "connectivity": 0.20,
    "clueability": 0.15,
    "discovery_curve": 0.10,
    "narrative_interest": 0.10,
}

# POS scoring for word quality
POS_SCORES = {
    "NOUN": 2, "PROPN": 2,
    "VERB": 1,
    "ADJ": 1,
    "ADV": 0,
    "DET": -5, "ADP": -5, "CONJ": -5, "CCONJ": -5, "SCONJ": -5,
    "PRON": -5, "AUX": -5, "PART": -5,
}

# Concrete word categories for bonus scoring
CONCRETE_CATEGORIES = {
    "animals": {"dog", "cat", "bird", "fish", "horse", "bear", "wolf", "lion",
                "tiger", "eagle", "whale", "shark", "deer", "fox", "rabbit",
                "snake", "elephant", "monkey", "cow", "pig", "chicken", "duck",
                "goat", "sheep", "turtle", "frog", "owl", "hawk", "dolphin",
                "bat", "mouse", "rat", "ant", "bee", "butterfly", "spider"},
    "tools": {"hammer", "saw", "drill", "wrench", "knife", "scissors", "needle",
              "axe", "shovel", "rake", "brush", "pen", "pencil", "compass",
              "ruler", "pliers", "screwdriver", "chisel"},
    "buildings": {"house", "castle", "temple", "church", "tower", "bridge",
                  "barn", "cabin", "palace", "fortress", "cottage", "mansion",
                  "shed", "warehouse", "factory", "stadium", "theater", "museum",
                  "library", "school", "hospital", "prison", "lighthouse"},
    "food": {"bread", "rice", "meat", "fish", "fruit", "apple", "orange",
             "banana", "grape", "cheese", "butter", "milk", "egg", "salt",
             "sugar", "pepper", "cake", "pie", "soup", "stew", "corn",
             "wheat", "potato", "tomato", "onion", "garlic", "honey"},
    "body": {"hand", "foot", "head", "eye", "ear", "nose", "mouth", "arm",
             "leg", "finger", "heart", "bone", "brain", "blood", "skin",
             "hair", "teeth", "tongue", "shoulder", "knee", "chest", "spine"},
    "weather": {"rain", "snow", "storm", "wind", "thunder", "lightning",
                "cloud", "fog", "frost", "hail", "drought", "flood",
                "hurricane", "tornado", "blizzard", "sunshine"},
    "vehicles": {"car", "truck", "bus", "train", "ship", "boat", "plane",
                 "bicycle", "motorcycle", "wagon", "cart", "sled", "canoe",
                 "rocket", "helicopter", "submarine"},
    "instruments": {"guitar", "piano", "drum", "violin", "flute", "trumpet",
                    "harp", "bell", "horn", "whistle", "organ", "banjo"},
}
ALL_CONCRETE_WORDS = set()
for cat_words in CONCRETE_CATEGORIES.values():
    ALL_CONCRETE_WORDS.update(cat_words)


# ---------------------------------------------------------------------------
# LLM provider helpers (NIM primary, Groq fallback)
# ---------------------------------------------------------------------------

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL = "meta/llama-3.3-70b-instruct"


def _make_nim_client(api_key: str):
    """Create an OpenAI-compatible client pointing at NVIDIA NIM."""
    try:
        from openai import OpenAI
        return OpenAI(base_url=NIM_BASE_URL, api_key=api_key)
    except ImportError:
        raise ImportError("openai package not installed. Run: uv pip install openai")


def _make_groq_client(api_key: str):
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        raise ImportError("groq package not installed. Run: uv pip install groq")


def _call_llm(client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Call an OpenAI-compatible LLM and return raw content."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Rule-based scoring
# ---------------------------------------------------------------------------

def _load_spacy_model():
    """Load spaCy English model."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        print("Error: spaCy model not found. Run: python -m spacy download en_core_web_sm")
        sys.exit(1)


def score_word_quality(nlp, paragraph_data: Dict) -> Tuple[float, str]:
    """
    Score hidden words based on POS tags, word length, and concreteness.
    Returns (score 0-10, reason string).
    """
    text = paragraph_data["text"]
    hidden_words = [hw["word"].lower() for hw in paragraph_data["hiddenWords"]]

    doc = nlp(text)

    # Map hidden words to their in-context POS tags
    word_pos = {}
    for token in doc:
        if token.text.lower() in hidden_words and token.text.lower() not in word_pos:
            word_pos[token.text.lower()] = token.pos_

    total_raw = 0
    details = []

    for word in hidden_words:
        raw = 0

        # POS score
        pos = word_pos.get(word, "NOUN")  # default to NOUN if not found
        pos_val = POS_SCORES.get(pos, 0)
        raw += pos_val

        # Word length penalty
        if len(word) < 4:
            raw -= 1

        # Concreteness bonus
        if word in ALL_CONCRETE_WORDS:
            raw += 1

        total_raw += raw
        details.append(f"{word}({pos}:{raw:+d})")

    # Normalize: raw range is roughly -6 to +3 per word, so -60 to +30 total
    # Map to 0-10 scale
    # Midpoint around 10 (average +1 per word) -> score 5
    normalized = max(0, min(10, (total_raw + 20) / 4.0))

    # Count function words (POS score < 0)
    func_count = sum(1 for w in hidden_words if POS_SCORES.get(word_pos.get(w, "NOUN"), 0) < 0)
    noun_count = sum(1 for w in hidden_words if word_pos.get(w, "NOUN") in ("NOUN", "PROPN"))

    reason = f"{noun_count} nouns, {func_count} function words"
    return round(normalized, 1), reason


def score_variety(nlp, paragraph_data: Dict) -> Tuple[float, str]:
    """
    Score variety based on POS diversity, word length spread, and related_words groupings.
    Returns (score 0-10, reason string).
    """
    text = paragraph_data["text"]
    hidden_words_data = paragraph_data["hiddenWords"]
    hidden_words = [hw["word"].lower() for hw in hidden_words_data]

    doc = nlp(text)

    # POS diversity: count unique POS tags among hidden words
    word_pos = {}
    for token in doc:
        if token.text.lower() in hidden_words and token.text.lower() not in word_pos:
            word_pos[token.text.lower()] = token.pos_

    pos_tags = [word_pos.get(w, "NOUN") for w in hidden_words]
    unique_pos = len(set(pos_tags))
    # 1 unique = 0, 5+ unique = 10
    pos_diversity = min(10, (unique_pos - 1) * 2.5)

    # Word length spread
    lengths = [len(w) for w in hidden_words]
    if len(lengths) > 1:
        length_std = statistics.stdev(lengths)
        # std of 0 = 0, std of 3+ = 10
        length_diversity = min(10, length_std * 3.33)
    else:
        length_diversity = 0

    # Related words groupings: count independent groups
    # Words with no related_words are independent; words sharing related_words form groups
    groups = []
    assigned = set()
    for hw in hidden_words_data:
        word = hw["word"].lower()
        if word in assigned:
            continue
        related = [r.lower() for r in hw.get("related_words", [])]
        if related:
            group = {word} | set(related)
            assigned.update(group)
            groups.append(group)
        else:
            assigned.add(word)
            groups.append({word})

    # More independent groups = higher variety
    # 10 independent = 10, 1 big group = 2
    group_diversity = min(10, groups.__len__() * 1.25) if groups else 5

    # Combine: 40% POS, 30% length, 30% groups
    score = pos_diversity * 0.4 + length_diversity * 0.3 + group_diversity * 0.3

    reason = f"{unique_pos} POS types, {len(groups)} word groups, length std={round(statistics.stdev(lengths), 1) if len(lengths) > 1 else 0}"
    return round(max(0, min(10, score)), 1), reason


# ---------------------------------------------------------------------------
# LLM scoring
# ---------------------------------------------------------------------------

def format_hidden_words_section(hidden_words: List[Dict]) -> str:
    """Format hidden words and clues for the LLM prompt."""
    lines = []
    for i, hw in enumerate(hidden_words, 1):
        lines.append(f"### Word {i}: **{hw['word']}** (Difficulty: {hw['difficulty']})")
        related = hw.get("related_words", [])
        if related:
            lines.append(f"Related to: {', '.join(related)}")
        for clue in hw.get("clues", []):
            lines.append(f"- [{clue['type']}, {clue['points']}pts] {clue['clue']}")
        lines.append("")
    return "\n".join(lines)


def score_with_llm(client, model: str, paragraph_data: Dict) -> Optional[Dict]:
    """
    Get LLM scores for subjective dimensions.
    Returns dict with connectivity, clueability, discovery_curve, narrative_interest, catalog_penalty.
    Returns None on failure.
    """
    system_prompt = (_PROMPTS_DIR / "scoring_system_prompt.txt").read_text(encoding="utf-8")
    template = (_PROMPTS_DIR / "scoring_user_prompt_template.txt").read_text(encoding="utf-8")

    hidden_section = format_hidden_words_section(paragraph_data["hiddenWords"])

    user_prompt = (template
        .replace("{title}", paragraph_data.get("title", "Untitled"))
        .replace("{date}", paragraph_data.get("date", "unknown"))
        .replace("{text}", paragraph_data["text"])
        .replace("{hidden_words_section}", hidden_section)
    )

    raw = _call_llm(client, model, system_prompt, user_prompt)
    result = json.loads(raw)

    # Validate expected keys
    expected = ["connectivity", "clueability", "discovery_curve", "narrative_interest", "catalog_penalty"]
    for key in expected:
        if key not in result:
            raise ValueError(f"LLM response missing key: {key}")
        if "score" not in result[key]:
            raise ValueError(f"LLM response missing 'score' in {key}")

    return result


# ---------------------------------------------------------------------------
# Score computation and aggregation
# ---------------------------------------------------------------------------

def compute_final_score(scores: Dict) -> float:
    """Compute weighted final score from individual dimension scores."""
    total = 0.0
    for dim, weight in WEIGHTS.items():
        if dim in scores and scores[dim] is not None:
            total += scores[dim] * weight

    # Add catalog penalty (raw deduction)
    catalog = scores.get("catalog_penalty", 0)
    if catalog is not None:
        total += catalog

    return round(total, 2)


def compute_partial_score(scores: Dict) -> Tuple[float, float]:
    """
    Compute score using only available dimensions.
    Returns (score, weight_covered) where weight_covered is the fraction of total weight used.
    """
    total = 0.0
    weight_used = 0.0

    for dim, weight in WEIGHTS.items():
        if dim in scores and scores[dim] is not None:
            total += scores[dim] * weight
            weight_used += weight

    catalog = scores.get("catalog_penalty", 0) or 0
    total += catalog

    if weight_used > 0:
        # Scale up to what a full score would be (proportional estimate)
        estimated_full = (total - catalog) / weight_used + catalog
        return round(estimated_full, 2), round(weight_used, 2)

    return 0.0, 0.0


def classify_tier(score: float) -> str:
    """Classify a score into a tier."""
    if score >= 7.5:
        return "Top"
    elif score >= 5.0:
        return "Middle"
    else:
        return "Bottom"


def classify_overall_rating(total_score: float) -> str:
    """Classify a 0-100 total score into an overall rating."""
    if total_score >= 75:
        return "good"
    elif total_score >= 50:
        return "okay"
    else:
        return "poor"


def compute_total_score(scores: Dict, has_llm: bool) -> float:
    """Compute a 0-100 total score from dimension scores."""
    if has_llm:
        final = compute_final_score(scores)
    else:
        final, _ = compute_partial_score(scores)
    return round(max(0, min(100, final * 10)), 1)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def stamp_summary_fields(all_scores: Dict):
    """Add total_score and overall_rating to every entry."""
    for filename, entry in all_scores.items():
        scores = entry.get("scores", {})
        has_llm = entry.get("has_llm_scores", False)
        total = compute_total_score(scores, has_llm)
        entry["total_score"] = total
        entry["overall_rating"] = classify_overall_rating(total)


def load_paragraph_files(data_dir: Path, single_file: Optional[str] = None) -> List[Tuple[str, Dict]]:
    """Load paragraph JSON files. Returns list of (filename, data) tuples."""
    results = []
    if single_file:
        path = Path(single_file)
        if not path.is_absolute():
            # Resolve relative to cwd, not data_dir
            path = Path.cwd() / path
        if path.exists():
            with open(path, encoding="utf-8") as f:
                results.append((path.name, json.load(f)))
        else:
            print(f"Error: File not found: {path}")
            sys.exit(1)
    else:
        for path in sorted(data_dir.glob("*.json")):
            if path.name == "index.json":
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if "hiddenWords" in data and "text" in data:
                    results.append((path.name, data))
            except (json.JSONDecodeError, KeyError):
                pass
    return results


def load_scores(scores_file: Path) -> Dict:
    """Load existing scores from checkpoint file."""
    if scores_file.exists():
        with open(scores_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_scores(scores: Dict, scores_file: Path):
    """Save scores to checkpoint file."""
    scores_file.parent.mkdir(parents=True, exist_ok=True)
    with open(scores_file, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_rankings(all_scores: Dict) -> List[Dict]:
    """Generate ranked list from scores. Returns list of row dicts sorted by score desc."""
    rows = []
    for filename, entry in all_scores.items():
        scores = entry.get("scores", {})
        has_llm = entry.get("has_llm_scores", False)

        if has_llm:
            final = compute_final_score(scores)
            score_type = "full"
        else:
            final, weight_covered = compute_partial_score(scores)
            score_type = f"partial ({int(weight_covered * 100)}%)"

        total = round(max(0, min(100, final * 10)), 1)

        rows.append({
            "filename": filename,
            "title": entry.get("title", ""),
            "final_score": final,
            "total_score": total,
            "overall_rating": classify_overall_rating(total),
            "score_type": score_type,
            "tier": classify_tier(final),
            "word_quality": scores.get("word_quality"),
            "variety": scores.get("variety"),
            "connectivity": scores.get("connectivity"),
            "clueability": scores.get("clueability"),
            "discovery_curve": scores.get("discovery_curve"),
            "narrative_interest": scores.get("narrative_interest"),
            "catalog_penalty": scores.get("catalog_penalty"),
        })

    rows.sort(key=lambda r: r["final_score"], reverse=True)
    return rows


def write_rankings_csv(rows: List[Dict], output_path: Path):
    """Write rankings to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["rank", "filename", "title", "total_score", "overall_rating",
                  "final_score", "tier", "score_type",
                  "word_quality", "variety", "connectivity", "clueability",
                  "discovery_curve", "narrative_interest", "catalog_penalty"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            row_copy = dict(row)
            row_copy["rank"] = i
            writer.writerow(row_copy)


def write_rankings_md(rows: List[Dict], output_path: Path):
    """Write human-readable tier report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top = [r for r in rows if r["tier"] == "Top"]
    middle = [r for r in rows if r["tier"] == "Middle"]
    bottom = [r for r in rows if r["tier"] == "Bottom"]

    full_count = sum(1 for r in rows if r["score_type"] == "full")
    partial_count = len(rows) - full_count

    good = sum(1 for r in rows if r["overall_rating"] == "good")
    okay = sum(1 for r in rows if r["overall_rating"] == "okay")
    poor = sum(1 for r in rows if r["overall_rating"] == "poor")

    lines = [
        "# ClueChain Paragraph Quality Rankings",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        f"Total paragraphs: {len(rows)}",
        f"Fully scored (rule + LLM): {full_count}",
        f"Partially scored (rule only): {partial_count}",
        "",
        "## Summary",
        "",
        f"| Rating | Count | Score Range (0-100) |",
        f"|--------|-------|---------------------|",
        f"| Good | {good} | >= 75 |",
        f"| Okay | {okay} | 50 - 74 |",
        f"| Poor | {poor} | < 50 |",
        "",
    ]

    def _format_tier(tier_name: str, tier_rows: List[Dict]) -> List[str]:
        section = [f"## {tier_name} Tier ({len(tier_rows)} paragraphs)", ""]
        if not tier_rows:
            section.append("_No paragraphs in this tier._")
            section.append("")
            return section

        section.append("| # | Total | Rating | Type | Title | File |")
        section.append("|---|-------|--------|------|-------|------|")
        for i, r in enumerate(tier_rows, 1):
            total_str = f"{r['total_score']:.0f}"
            section.append(f"| {i} | {total_str}/100 | {r['overall_rating']} | {r['score_type']} | {r['title'][:40]} | {r['filename']} |")
        section.append("")
        return section

    lines.extend(_format_tier("Top", top))
    lines.extend(_format_tier("Middle", middle))
    lines.extend(_format_tier("Bottom", bottom))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score ClueChain paragraphs on quality dimensions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/score_paragraphs.py                        # LLM-score all unscored (resumes)
  python scripts/score_paragraphs.py --batch-size 20        # LLM-score only 20 unscored then stop
  python scripts/score_paragraphs.py --rules                # Also run rule-based scoring (spaCy)
  python scripts/score_paragraphs.py --rules --batch-size 0 # Rule-based only, no LLM
  python scripts/score_paragraphs.py --force                # Re-score everything
  python scripts/score_paragraphs.py --file path/to/file    # Score single file
  python scripts/score_paragraphs.py --dry-run              # Show what would be scored
  python scripts/score_paragraphs.py --delay 2.0            # Custom API delay
  python scripts/score_paragraphs.py --groq                 # Use Groq instead of NIM
        """
    )
    parser.add_argument("--batch-size", type=int, default=20,
                        help="Max paragraphs to LLM-score per run (default: 20)")
    parser.add_argument("--force", action="store_true",
                        help="Re-score all paragraphs (ignore checkpoint)")
    parser.add_argument("--file", type=str, default=None,
                        help="Score a single file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be scored without scoring")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between API calls in seconds (default: 2.0)")
    parser.add_argument("--rules", action="store_true",
                        help="Run rule-based scoring (spaCy POS/variety). Off by default.")
    parser.add_argument("--groq", action="store_true",
                        help="Use Groq instead of NIM for LLM scoring")
    args = parser.parse_args()

    # Load env and optionally spaCy
    load_dotenv()
    nlp = _load_spacy_model() if args.rules else None

    # Load existing scores (checkpoint)
    if args.force:
        all_scores = {}
    else:
        all_scores = load_scores(_SCORES_FILE)

    # Load paragraph files
    paragraphs = load_paragraph_files(_DATA_DIR, args.file)
    print(f"Found {len(paragraphs)} paragraph files")

    if not paragraphs:
        print("No paragraph files found.")
        return

    # Phase 1: Rule-based scoring (only when --rules is passed)
    if args.rules:
        print("\n--- Phase 1: Rule-based scoring ---")
        rule_scored = 0
        for filename, data in paragraphs:
            wq_score, wq_reason = score_word_quality(nlp, data)
            var_score, var_reason = score_variety(nlp, data)

            if filename not in all_scores:
                all_scores[filename] = {
                    "title": data.get("title", ""),
                    "date": data.get("date", ""),
                    "scores": {},
                    "reasons": {},
                    "has_llm_scores": False,
                }

            all_scores[filename]["scores"]["word_quality"] = wq_score
            all_scores[filename]["scores"]["variety"] = var_score
            all_scores[filename]["reasons"]["word_quality"] = wq_reason
            all_scores[filename]["reasons"]["variety"] = var_reason
            rule_scored += 1

        print(f"Rule-based scores computed for {rule_scored} paragraphs")

        # Save after rule-based phase
        stamp_summary_fields(all_scores)
        save_scores(all_scores, _SCORES_FILE)
    else:
        # Ensure entries exist for paragraphs not yet in all_scores
        for filename, data in paragraphs:
            if filename not in all_scores:
                all_scores[filename] = {
                    "title": data.get("title", ""),
                    "date": data.get("date", ""),
                    "scores": {},
                    "reasons": {},
                    "has_llm_scores": False,
                }

    # Phase 2: LLM scoring for unscored paragraphs
    # Determine which need LLM scoring
    needs_llm = []
    for filename, data in paragraphs:
        if not all_scores.get(filename, {}).get("has_llm_scores", False):
            needs_llm.append((filename, data))

    print(f"\n--- Phase 2: LLM scoring ---")
    print(f"Paragraphs needing LLM scores: {len(needs_llm)}")
    print(f"Batch size: {args.batch_size}")

    if args.dry_run:
        print("\nDry run — would score these files:")
        for fn, _ in needs_llm[:args.batch_size]:
            print(f"  {fn}")
        if len(needs_llm) > args.batch_size:
            print(f"  ... and {len(needs_llm) - args.batch_size} more in future batches")
    else:
        # Set up LLM client: NIM default, --groq to override
        nim_key = os.getenv("NIM_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        client = None
        provider = None

        if args.groq:
            if groq_key:
                client = _make_groq_client(groq_key)
                model = GROQ_MODEL
                provider = "Groq"
            else:
                print("Error: --groq specified but GROQ_API_KEY not set.")
                sys.exit(1)
        elif nim_key:
            client = _make_nim_client(nim_key)
            model = NIM_MODEL
            provider = "NIM"
        elif groq_key:
            client = _make_groq_client(groq_key)
            model = GROQ_MODEL
            provider = "Groq"

        if not client:
            print("Warning: Neither NIM_API_KEY nor GROQ_API_KEY set. Skipping LLM scoring.")
            print("Rankings will use rule-based scores only (45% weight).")
        else:
            print(f"Using {provider} ({model})")
            batch = needs_llm[:args.batch_size]
            llm_scored = 0
            llm_failed = 0

            for i, (filename, data) in enumerate(batch, 1):
                print(f"  [{i}/{len(batch)}] Scoring {filename}...", end=" ", flush=True)
                start = time.time()
                try:
                    llm_result = score_with_llm(client, model, data)
                    elapsed = time.time() - start

                    # Store LLM scores
                    for dim in ["connectivity", "clueability", "discovery_curve", "narrative_interest"]:
                        all_scores[filename]["scores"][dim] = llm_result[dim]["score"]
                        all_scores[filename]["reasons"][dim] = llm_result[dim]["reason"]

                    all_scores[filename]["scores"]["catalog_penalty"] = llm_result["catalog_penalty"]["score"]
                    all_scores[filename]["reasons"]["catalog_penalty"] = llm_result["catalog_penalty"]["reason"]
                    all_scores[filename]["has_llm_scores"] = True
                    all_scores[filename]["llm_provider"] = provider
                    llm_scored += 1

                    print(f"done ({elapsed:.1f}s)")

                    # Save checkpoint after each successful scoring
                    stamp_summary_fields(all_scores)
                    save_scores(all_scores, _SCORES_FILE)

                    # Rate limiting
                    if i < len(batch):
                        time.sleep(args.delay)

                except Exception as e:
                    elapsed = time.time() - start
                    llm_failed += 1
                    print(f"FAILED ({elapsed:.1f}s): {e}")

                    # On rate limit, stop the batch
                    if "429" in str(e) or "rate" in str(e).lower():
                        print("Rate limited — stopping batch early.")
                        break

            print(f"\nLLM scoring complete: {llm_scored} scored, {llm_failed} failed")
            remaining = len(needs_llm) - llm_scored
            if remaining > 0:
                print(f"Remaining unscored: {remaining} (run again to continue)")

    # Phase 3: Generate rankings from all available scores
    print("\n--- Phase 3: Generating rankings ---")
    rows = generate_rankings(all_scores)

    write_rankings_csv(rows, _RANKINGS_CSV)
    write_rankings_md(rows, _RANKINGS_MD)

    print(f"Rankings written to:")
    print(f"  {_RANKINGS_CSV}")
    print(f"  {_RANKINGS_MD}")

    # Summary
    good = sum(1 for r in rows if r["overall_rating"] == "good")
    okay = sum(1 for r in rows if r["overall_rating"] == "okay")
    poor = sum(1 for r in rows if r["overall_rating"] == "poor")
    full = sum(1 for r in rows if r["score_type"] == "full")
    print(f"\nRating distribution: Good={good}, Okay={okay}, Poor={poor}")
    print(f"Fully scored: {full}/{len(rows)}")


if __name__ == "__main__":
    main()
