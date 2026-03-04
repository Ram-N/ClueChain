#!/usr/bin/env python3
"""
Unified Pack Unit JSON Generator

Reads a plain-text file of paragraphs (one per blank-line-separated block),
calls Groq to select words and write three-tier clues, and saves a unit JSON.

Output paths:
  --date given  → assets/data/units/{pack_type}/YYYY/MM/DD.json
  --date absent → assets/data/units/{pack_type}/{pack_slug}.json

Usage:
    # Literature pack
    uv run python scripts/generate_pack_unit.py \\
        --file assets/data/library/dickens.txt \\
        --pack-type literature \\
        --pack-slug tale-of-two-cities \\
        --title "A Tale of Two Cities" \\
        --source "Charles Dickens, 1859" \\
        --license public-domain

    # News pack (date-nested output)
    uv run python scripts/generate_pack_unit.py \\
        --file assets/data/library/news_032026.txt \\
        --pack-type news \\
        --date 2026-03-04 \\
        --title "March 4, 2026 News"

Requirements:
    - GROQ_API_KEY in .env file
"""

import argparse
import csv
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Please install dependencies: uv pip install -r requirements.txt")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROQ_MODEL   = "llama-3.3-70b-versatile"
_PROMPTS_DIR = Path(__file__).parent / "prompts"

VALID_CLUE_TYPES = {"Indirect", "Suggestive", "Straight"}
VALID_POINTS = {
    "Indirect":   {5, 6, 7},
    "Suggestive": {3, 4},
    "Straight":   {1, 2},
}

# ---------------------------------------------------------------------------
# Groq helpers
# ---------------------------------------------------------------------------


def _make_groq_client(api_key: str):
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        raise ImportError("groq package not installed. Run: uv pip install groq")


def _call_llm(client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Call Groq and return raw content string."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------


def parse_paragraphs(text: str) -> List[str]:
    """Split source text on blank lines; return non-empty paragraph strings."""
    blocks = text.split("\n\n")
    paragraphs = []
    for block in blocks:
        stripped = block.strip()
        if stripped:
            # Normalise internal line breaks to spaces
            paragraph = " ".join(stripped.splitlines())
            paragraphs.append(paragraph)
    return paragraphs


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_item_response(data: Dict, paragraph_text: str) -> None:
    """Raise ValueError if the LLM response doesn't meet requirements."""
    if "title" not in data or not data["title"].strip():
        raise ValueError("Missing or empty 'title'")

    blanks = data.get("blanks")
    if not isinstance(blanks, list) or not (4 <= len(blanks) <= 10):
        raise ValueError(
            f"Expected 4–10 blanks, got "
            f"{len(blanks) if isinstance(blanks, list) else type(blanks)}"
        )

    paragraph_lower = paragraph_text.lower()

    for i, blank in enumerate(blanks, 1):
        word = blank.get("word", "")
        if not word:
            raise ValueError(f"Blank {i}: missing 'word'")

        if word.lower() not in paragraph_lower:
            raise ValueError(f"Blank {i}: word '{word}' not found in paragraph text")

        clues = blank.get("clues")
        if not isinstance(clues, list) or len(clues) != 3:
            raise ValueError(
                f"Blank {i} ('{word}'): must have exactly 3 clues, "
                f"got {len(clues) if isinstance(clues, list) else type(clues)}"
            )

        seen_types = set()
        for j, clue_obj in enumerate(clues, 1):
            clue_type = clue_obj.get("type", "")
            clue_text = clue_obj.get("clue", "")
            points    = clue_obj.get("points")

            if clue_type not in VALID_CLUE_TYPES:
                raise ValueError(
                    f"Blank {i} ('{word}'), clue {j}: invalid type '{clue_type}'. "
                    f"Must be one of {VALID_CLUE_TYPES}"
                )
            if clue_type in seen_types:
                raise ValueError(f"Blank {i} ('{word}'): duplicate clue type '{clue_type}'")
            seen_types.add(clue_type)

            if not clue_text.strip():
                raise ValueError(f"Blank {i} ('{word}'), clue '{clue_type}': empty clue text")

            if word.lower() in clue_text.lower():
                raise ValueError(
                    f"Blank {i} ('{word}'), clue '{clue_type}': clue text contains the answer word"
                )

            if points not in VALID_POINTS[clue_type]:
                raise ValueError(
                    f"Blank {i} ('{word}'), clue '{clue_type}': "
                    f"invalid points {points}, must be one of {VALID_POINTS[clue_type]}"
                )

        missing_types = VALID_CLUE_TYPES - seen_types
        if missing_types:
            raise ValueError(f"Blank {i} ('{word}'): missing required clue types {missing_types}")


# ---------------------------------------------------------------------------
# LLM call per paragraph
# ---------------------------------------------------------------------------


def process_paragraph(client, paragraph_text: str, system_prompt: str,
                       user_prompt_template: str, max_retries: int = 3) -> Dict:
    """
    Call the LLM for one paragraph and return the validated response dict.
    Raises ValueError after max_retries exhausted.
    """
    user_prompt = user_prompt_template.replace("{paragraph_text}", paragraph_text)
    last_error  = "Unknown error"

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"       ↻ Retry {attempt}/{max_retries}...")

        try:
            raw = _call_llm(client, GROQ_MODEL, system_prompt, user_prompt)
        except Exception as api_err:
            last_error = str(api_err)
            print(f"       ⚠️  API error: {last_error}")
            if attempt == max_retries:
                raise
            continue

        try:
            data = json.loads(raw)
        except Exception as parse_err:
            last_error = f"JSON parse error: {parse_err}"
            print(f"       ⚠️  {last_error}")
            continue

        try:
            validate_item_response(data, paragraph_text)
        except ValueError as val_err:
            last_error = str(val_err)
            print(f"       ⚠️  Validation failed: {last_error}")
            continue

        return data

    raise ValueError(f"Failed after {max_retries} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Unit JSON assembly
# ---------------------------------------------------------------------------

PRACTICE_BLOCK = {
    "enabled": True,
    "blanking": {
        "mode": "auto",
        "targets": {
            "easy":     {"min_blanks": 3, "max_blanks": 5},
            "standard": {"min_blanks": 5, "max_blanks": 7},
            "advanced": {"min_blanks": 7, "max_blanks": 10},
        },
        "avoid": {"stopwords": True, "numbers": True, "very_short_words_max_len": 3},
    },
    "scoring": {
        "max_points": 100,
        "per_blank": "proportional",
        "penalties": {"wrong_guess": 1, "reveal_word": 10},
    },
}


def build_unit_json(items_data: List[Dict], paragraph_texts: List[str],
                    unit_title: str, pack_type: str, pack_slug: Optional[str],
                    date_str: Optional[str], source_name: str, source_license: str) -> Dict:
    """Assemble the full unit JSON from per-paragraph LLM results."""

    if date_str:
        unit_id = f"{pack_type}-{date_str}"
    else:
        unit_id = f"{pack_type}-{pack_slug}"

    items = []
    for idx, (llm_data, text) in enumerate(zip(items_data, paragraph_texts), 1):
        item_id = f"{unit_id}-{idx:02d}"

        authored_variant = {
            "variant_id": "llm-v1",
            "blanks": llm_data["blanks"],
        }

        item = {
            "item_id":  item_id,
            "title":    llm_data["title"],
            "text":     text,
            "practice": PRACTICE_BLOCK,
            "authored_variants": [authored_variant],
        }
        items.append(item)

    unit: Dict = {
        "schema_version": 1,
        "unit_id":         unit_id,
        "unit_type":       pack_type,
        "title":           unit_title,
        "source":          {"name": source_name, "license": source_license},
        "navigation":      {"collection": pack_type},
        "tags":            ["vocabulary", pack_type],
        "reading_level":   "adult",
        "estimated_minutes": max(5, len(items) * 2),
        "items":           items,
    }

    if date_str:
        unit["date"] = date_str

    return unit


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_unit_json(unit: Dict, pack_type: str, pack_slug: Optional[str],
                    date_str: Optional[str], output_root: Optional[str]) -> Path:
    """Write the unit JSON to the appropriate path."""
    base = Path(output_root) if output_root else Path("assets/data/units")

    if date_str:
        date_obj = datetime.date.fromisoformat(date_str)
        out_dir  = base / pack_type / str(date_obj.year) / f"{date_obj.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{date_obj.day:02d}.json"
    else:
        out_dir = base / pack_type
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{pack_slug}.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(unit, f, indent=2, ensure_ascii=False)

    return out_path


# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------

_LOG_FILE    = Path(__file__).parent.parent / "logs" / "pack_words.csv"
_LOG_COLUMNS = ["generated_at", "pack_type", "unit_id", "item_id", "item_title",
                "word", "indirect_clue", "suggestive_clue", "straight_clue"]


def _clue_text_by_type(clues: List[Dict], clue_type: str) -> str:
    for c in clues:
        if c.get("type") == clue_type:
            return c.get("clue", "")
    return ""


def append_to_log(unit: Dict) -> None:
    """Append one row per blank to logs/pack_words.csv."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_header = not _LOG_FILE.exists()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with _LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        for item in unit["items"]:
            blanks = item.get("authored_variants", [{}])[0].get("blanks", [])
            for blank in blanks:
                clues = blank.get("clues", [])
                writer.writerow({
                    "generated_at":   now,
                    "pack_type":      unit["unit_type"],
                    "unit_id":        unit["unit_id"],
                    "item_id":        item["item_id"],
                    "item_title":     item["title"],
                    "word":           blank["word"],
                    "indirect_clue":  _clue_text_by_type(clues, "Indirect"),
                    "suggestive_clue": _clue_text_by_type(clues, "Suggestive"),
                    "straight_clue":  _clue_text_by_type(clues, "Straight"),
                })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate a pack unit JSON with LLM-authored clues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Literature pack
  uv run python scripts/generate_pack_unit.py \\
      --file assets/data/library/dickens.txt \\
      --pack-type literature \\
      --pack-slug tale-of-two-cities \\
      --title "A Tale of Two Cities" \\
      --source "Charles Dickens, 1859" \\
      --license public-domain

  # News pack (date-nested output)
  uv run python scripts/generate_pack_unit.py \\
      --file assets/data/library/news_032026.txt \\
      --pack-type news \\
      --date 2026-03-04 \\
      --title "March 4, 2026 News"

  # Dry run (no API calls)
  uv run python scripts/generate_pack_unit.py \\
      --file assets/data/library/dickens.txt --dry-run
        """,
    )
    parser.add_argument("--file",       required=True,
                        help="Path to source text file (paragraphs separated by blank lines)")
    parser.add_argument("--pack-type",  required=True,
                        help="Pack type: literature, news, history, ai, etc.")
    parser.add_argument("--pack-slug",  default=None,
                        help="Slug for output filename (required when --date is not given)")
    parser.add_argument("--date",       default=None,
                        help="Output date YYYY-MM-DD (enables date-nested output path)")
    parser.add_argument("--title",      default=None,
                        help="Unit title")
    parser.add_argument("--source",     default="Unknown",
                        help="Source attribution string (default: 'Unknown')")
    parser.add_argument("--license",    default="unknown",
                        help="License string (default: 'unknown')")
    parser.add_argument("--delay",      type=float, default=5.0,
                        help="Seconds between Groq calls (default: 5)")
    parser.add_argument("--output",     default=None,
                        help="Override output root directory (default: assets/data/units)")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Parse and preview without calling the API")
    args = parser.parse_args()

    # ---- Validate mutually required args ----
    if not args.date and not args.pack_slug:
        print("❌ Either --date YYYY-MM-DD or --pack-slug SLUG is required.")
        sys.exit(1)

    if args.date:
        try:
            datetime.date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)

    # ---- Default title ----
    unit_title = args.title or (
        args.pack_slug.replace("-", " ").title() if args.pack_slug
        else f"{args.pack_type.title()} Unit"
    )

    # ---- Read source file ----
    src_path = Path(args.file)
    if not src_path.exists():
        print(f"❌ File not found: {src_path}")
        sys.exit(1)

    raw_text   = src_path.read_text(encoding="utf-8")
    paragraphs = parse_paragraphs(raw_text)

    if not paragraphs:
        print("❌ No paragraphs found in source file.")
        sys.exit(1)

    print(f"📄 Source:    {src_path}")
    print(f"   Pack type: {args.pack_type}  |  Title: {unit_title}")
    if args.date:
        print(f"   Date:      {args.date}")
    else:
        print(f"   Slug:      {args.pack_slug}")
    print(f"   Found {len(paragraphs)} paragraph(s)")
    print()

    for i, para in enumerate(paragraphs, 1):
        words = len(para.split())
        print(f"   [{i}] {words} words — {para[:70]}{'…' if len(para) > 70 else ''}")

    if args.dry_run:
        print("\n✅ Dry run complete — no API calls made.")
        return

    # ---- Load env + Groq clients (round-robin across available keys) ----
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    keys    = [k for k in [api_key, os.getenv("GROQ_API_KEY2"), os.getenv("GROQ_API_KEY3")] if k]
    clients = [_make_groq_client(k) for k in keys]
    print(f"\n   Keys available: {len(clients)} (rotating per paragraph)")

    # ---- Load prompts ----
    system_prompt        = (_PROMPTS_DIR / "pack_system_prompt.txt").read_text(encoding="utf-8")
    user_prompt_template = (_PROMPTS_DIR / "pack_user_prompt_template.txt").read_text(encoding="utf-8")

    # ---- Process each paragraph ----
    print()
    items_data: List[Dict]    = []
    failed_indices: List[int] = []

    for i, paragraph in enumerate(paragraphs, 1):
        client  = clients[(i - 1) % len(clients)]
        key_num = (i - 1) % len(clients) + 1
        print(f"🔄 Paragraph {i}/{len(paragraphs)}  [key {key_num}]…")
        try:
            result = process_paragraph(client, paragraph, system_prompt, user_prompt_template)
            items_data.append(result)
            word_list = [b["word"] for b in result["blanks"]]
            print(f"   ✅ '{result['title']}' — {len(result['blanks'])} blanks: {', '.join(word_list)}")
        except Exception as err:
            print(f"   ❌ Failed: {err}")
            failed_indices.append(i)
            items_data.append(None)

        if i < len(paragraphs):
            time.sleep(args.delay)

    # ---- Filter out failed items ----
    paired = [(d, t) for d, t in zip(items_data, paragraphs) if d is not None]
    if not paired:
        print("\n❌ All paragraphs failed. No output written.")
        sys.exit(1)

    good_data, good_texts = zip(*paired)

    # ---- Assemble + write ----
    unit = build_unit_json(
        list(good_data), list(good_texts),
        unit_title, args.pack_type, args.pack_slug,
        args.date, args.source, args.license,
    )
    out_path = write_unit_json(unit, args.pack_type, args.pack_slug, args.date, args.output)
    append_to_log(unit)

    # ---- Summary ----
    total_blanks = sum(
        len(it["authored_variants"][0]["blanks"]) for it in unit["items"]
    )
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"   Unit ID:  {unit['unit_id']}")
    print(f"   Items:    {len(unit['items'])} (of {len(paragraphs)} paragraphs)")
    if failed_indices:
        print(f"   Failed:   paragraphs {failed_indices}")
    print(f"   Blanks:   {total_blanks} total")
    print(f"   Output:   {out_path}")
    print(f"   Log:      {_LOG_FILE}")
    print("=" * 60)

    if args.date:
        date_obj  = datetime.date.fromisoformat(args.date)
        unit_path = f"{args.pack_type}/{date_obj.year}/{date_obj.month:02d}/{date_obj.day:02d}"
        print(f"\n✅ Done. Open learning/news.html?unit={unit_path} to preview.")
    else:
        print(f"\n✅ Done. Output: {out_path}")


if __name__ == "__main__":
    main()
