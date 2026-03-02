#!/usr/bin/env python3
"""
News Unit JSON Generator

Reads a plain-text file of news paragraphs (one per blank-line-separated block),
calls Groq to select words and write three-tier hints, and saves a unit JSON to:
  assets/data/units/news/{YYYY}/{MM}/{DD}.json

Usage:
    uv run python scripts/generate_news_unit.py \\
        --file assets/data/library/news_022026.txt \\
        --date 2026-02-01 \\
        --title "February 2026 News" \\
        --delay 5

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
from typing import Dict, List, Optional

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

# ---------------------------------------------------------------------------
# Groq helpers (copied from generate_cluechain_json.py)
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
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------


def parse_articles(text: str) -> List[str]:
    """Split source text on blank lines; return non-empty article strings."""
    blocks = text.split("\n\n")
    articles = []
    for block in blocks:
        stripped = block.strip()
        if stripped:
            # Normalise internal line breaks to spaces
            article = " ".join(stripped.splitlines())
            articles.append(article)
    return articles


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

REQUIRED_HINT_KEYS = {"direct", "intermediate", "indirect"}


def validate_item_response(data: Dict, article_text: str) -> None:
    """Raise ValueError if the LLM response doesn't meet requirements."""
    if "title" not in data or not data["title"].strip():
        raise ValueError("Missing or empty 'title'")

    blanks = data.get("blanks")
    if not isinstance(blanks, list) or not (2 <= len(blanks) <= 10):
        raise ValueError(f"Expected 2–10 blanks, got {len(blanks) if isinstance(blanks, list) else type(blanks)}")

    article_lower = article_text.lower()

    for i, blank in enumerate(blanks, 1):
        word = blank.get("word", "")
        if not word:
            raise ValueError(f"Blank {i}: missing 'word'")

        if word.lower() not in article_lower:
            raise ValueError(f"Blank {i}: word '{word}' not found in article text")

        hints = blank.get("hints", {})
        missing = REQUIRED_HINT_KEYS - set(hints.keys())
        if missing:
            raise ValueError(f"Blank {i} ('{word}'): missing hint keys {missing}")

        for key in REQUIRED_HINT_KEYS:
            hint_text = hints.get(key, "")
            if not hint_text.strip():
                raise ValueError(f"Blank {i} ('{word}'): empty hint '{key}'")
            if word.lower() in hint_text.lower():
                raise ValueError(f"Blank {i} ('{word}'): hint '{key}' contains the answer word")


# ---------------------------------------------------------------------------
# LLM call per article
# ---------------------------------------------------------------------------


def process_article(client, article_text: str, system_prompt: str,
                    user_prompt_template: str, max_retries: int = 3) -> Dict:
    """
    Call the LLM for one article and return the validated response dict.
    Raises ValueError after max_retries exhausted.
    """
    user_prompt = user_prompt_template.replace("{article_text}", article_text)
    last_error = "Unknown error"

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
            validate_item_response(data, article_text)
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


def build_unit_json(items_data: List[Dict], article_texts: List[str],
                    unit_title: str, date_str: str) -> Dict:
    """
    Assemble the full unit JSON from per-article LLM results.

    items_data: list of validated LLM dicts (one per article)
    article_texts: corresponding original article strings
    """
    date_obj = datetime.date.fromisoformat(date_str)
    unit_id  = f"news-{date_str}"

    items = []
    for idx, (llm_data, text) in enumerate(zip(items_data, article_texts), 1):
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

    return {
        "schema_version": 1,
        "unit_id":         unit_id,
        "unit_type":       "news",
        "title":           unit_title,
        "date":            date_str,
        "topic":           "current-events",
        "source":          {"name": "Editorial", "license": "editorial"},
        "navigation":      {"collection": "news"},
        "tags":            ["vocabulary", "current-events"],
        "reading_level":   "adult",
        "estimated_minutes": max(5, len(items) * 2),
        "items":           items,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_unit_json(unit: Dict, output_root: str, date_str: str) -> Path:
    """Write the unit JSON to assets/data/units/news/YYYY/MM/DD.json."""
    date_obj = datetime.date.fromisoformat(date_str)
    out_dir  = Path(output_root) / str(date_obj.year) / f"{date_obj.month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_obj.day:02d}.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(unit, f, indent=2, ensure_ascii=False)

    return out_path


# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------

_LOG_FILE = Path(__file__).parent.parent / "logs" / "news_words.csv"
_LOG_COLUMNS = ["generated_at", "date", "unit_id", "item_id", "item_title",
                "word", "direct", "intermediate", "indirect"]


def append_to_log(unit: Dict) -> None:
    """Append one row per blank to logs/news_words.csv."""
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
                hints = blank.get("hints", {})
                writer.writerow({
                    "generated_at":  now,
                    "date":          unit["date"],
                    "unit_id":       unit["unit_id"],
                    "item_id":       item["item_id"],
                    "item_title":    item["title"],
                    "word":          blank["word"],
                    "direct":        hints.get("direct", ""),
                    "intermediate":  hints.get("intermediate", ""),
                    "indirect":      hints.get("indirect", ""),
                })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate a news unit JSON with LLM-authored hints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/generate_news_unit.py \\
      --file assets/data/library/news_022026.txt \\
      --date 2026-02-01 \\
      --title "February 2026 News" \\
      --delay 5

  # Preview without calling the API:
  uv run python scripts/generate_news_unit.py \\
      --file assets/data/library/news_022026.txt --dry-run
        """,
    )
    parser.add_argument("--file",    required=True,
                        help="Path to source text file (paragraphs separated by blank lines)")
    parser.add_argument("--date",    default=None,
                        help="Output date YYYY-MM-DD (default: today)")
    parser.add_argument("--title",   default="Today's News",
                        help="Unit title (default: 'Today's News')")
    parser.add_argument("--delay",   type=float, default=5.0,
                        help="Seconds between Groq calls (default: 5)")
    parser.add_argument("--output",  default="assets/data/units/news",
                        help="Output root directory (default: assets/data/units/news)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and preview without calling the API")
    args = parser.parse_args()

    # ---- Date ----
    if args.date:
        try:
            datetime.date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)
        date_str = args.date
    else:
        date_str = datetime.date.today().isoformat()

    # ---- Read source file ----
    src_path = Path(args.file)
    if not src_path.exists():
        print(f"❌ File not found: {src_path}")
        sys.exit(1)

    raw_text = src_path.read_text(encoding="utf-8")
    articles = parse_articles(raw_text)

    if not articles:
        print("❌ No articles found in source file.")
        sys.exit(1)

    print(f"📰 Source: {src_path}")
    print(f"   Found {len(articles)} article(s)")
    print(f"   Date:  {date_str}  |  Title: {args.title}")
    print()

    for i, art in enumerate(articles, 1):
        words = len(art.split())
        print(f"   [{i}] {words} words — {art[:70]}{'…' if len(art) > 70 else ''}")

    if args.dry_run:
        print("\n✅ Dry run complete — no API calls made.")
        return

    # ---- Load env + Groq clients (round-robin across available keys) ----
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    keys = [k for k in [api_key, os.getenv("GROQ_API_KEY2"), os.getenv("GROQ_API_KEY3")] if k]
    clients = [_make_groq_client(k) for k in keys]
    print(f"   Keys available: {len(clients)} (rotating per article)")

    # ---- Load prompts ----
    system_prompt        = (_PROMPTS_DIR / "news_system_prompt.txt").read_text(encoding="utf-8")
    user_prompt_template = (_PROMPTS_DIR / "news_user_prompt_template.txt").read_text(encoding="utf-8")

    # ---- Process each article ----
    print()
    items_data: List[Dict] = []
    failed_indices: List[int] = []

    for i, article in enumerate(articles, 1):
        client = clients[(i - 1) % len(clients)]
        key_num = (i - 1) % len(clients) + 1
        print(f"🔄 Article {i}/{len(articles)}  [key {key_num}]…")
        try:
            result = process_article(client, article, system_prompt, user_prompt_template)
            items_data.append(result)
            word_list = [b["word"] for b in result["blanks"]]
            print(f"   ✅ '{result['title']}' — {len(result['blanks'])} blanks: {', '.join(word_list)}")
        except Exception as err:
            print(f"   ❌ Failed: {err}")
            failed_indices.append(i)
            # Insert a placeholder so indices stay aligned
            items_data.append(None)

        if i < len(articles):
            time.sleep(args.delay)

    # ---- Filter out failed items ----
    paired = [(d, t) for d, t in zip(items_data, articles) if d is not None]
    if not paired:
        print("\n❌ All articles failed. No output written.")
        sys.exit(1)

    good_data, good_texts = zip(*paired)

    # ---- Assemble + write ----
    unit = build_unit_json(list(good_data), list(good_texts), args.title, date_str)
    out_path = write_unit_json(unit, args.output, date_str)
    append_to_log(unit)

    # ---- Summary ----
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"   Unit ID:  {unit['unit_id']}")
    print(f"   Items:    {len(unit['items'])} (of {len(articles)} articles)")
    if failed_indices:
        print(f"   Failed:   articles {failed_indices}")
    total_blanks = sum(len(it["authored_variants"][0]["blanks"]) for it in unit["items"])
    print(f"   Blanks:   {total_blanks} total")
    print(f"   Output:   {out_path}")
    print(f"   Log:      {_LOG_FILE}")
    print("=" * 60)

    date_obj2 = datetime.date.fromisoformat(date_str)
    unit_path = f"news/{date_obj2.year}/{date_obj2.month:02d}/{date_obj2.day:02d}"
    print(f"\n✅ Done. Open learning/news.html?unit={unit_path} to preview.")


if __name__ == "__main__":
    main()
