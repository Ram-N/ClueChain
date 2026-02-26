#!/usr/bin/env python3
"""
ClueChain JSON and Hints Generator

Generates ClueChain puzzle JSON from paragraph text.
Primary backend: Groq (fast, free tier).
Fallback backend: OpenRouter / Gemini Flash Lite (cheap, high quality).

Usage:
    python generate_cluechain_json.py --file paragraph.txt --title "Title" --date 07-15
    python generate_cluechain_json.py --file paragraph.txt --model openrouter

Requirements:
    - GROQ_API_KEY and/or OPENROUTER_API_KEY in .env file
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Please install dependencies: uv pip install -r requirements.txt")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

GROQ_MODEL       = "llama-3.3-70b-versatile"
_PROMPTS_DIR     = Path(__file__).parent / "prompts"
OPENROUTER_BASE  = "https://openrouter.ai/api/v1"

_model_config_path = Path(__file__).parent / "model-config.json"
if _model_config_path.exists():
    with open(_model_config_path) as _f:
        OPENROUTER_MODEL = json.load(_f).get("openrouter_model", "google/gemini-2.0-flash-lite-001")
else:
    OPENROUTER_MODEL = "google/gemini-2.0-flash-lite-001"


def _make_groq_client(api_key: str):
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        raise ImportError("groq package not installed. Run: uv pip install groq")


def _make_openrouter_client(api_key: str):
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE)
    except ImportError:
        raise ImportError("openai package not installed. Run: uv pip install openai")


def _call_llm(client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Call either Groq or OpenRouter (both are OpenAI-compatible) and return raw content."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class ClueChainGenerator:
    """Generates ClueChain JSON files.

    backend: 'groq' (default) | 'openrouter'
    Falls back to openrouter automatically when groq exhausts all retries.
    """

    def __init__(self, groq_key: Optional[str] = None,
                 groq_key2: Optional[str] = None,
                 openrouter_key: Optional[str] = None,
                 backend: str = "groq"):
        self.groq_key         = groq_key
        self.groq_key2        = groq_key2
        self.openrouter_key   = openrouter_key
        self.backend          = backend  # 'groq' | 'openrouter'
        self._active_groq_key = groq_key  # tracks which key is currently in use

        # Eagerly validate requested backend
        if backend == "groq" and not groq_key:
            raise ValueError("GROQ_API_KEY required for groq backend")
        if backend == "openrouter" and not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY required for openrouter backend")

    def _client_and_model(self, backend: str):
        if backend == "groq":
            return _make_groq_client(self._active_groq_key), GROQ_MODEL
        else:
            return _make_openrouter_client(self.openrouter_key), OPENROUTER_MODEL

    # ------------------------------------------------------------------
    # Prompt builders (shared by both backends)
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return (_PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")

    def _build_user_prompt(self, paragraph: str, title: Optional[str], date: str) -> str:
        title_text = title if title else "ClueChain Challenge"
        template = (_PROMPTS_DIR / "user_prompt_template.txt").read_text(encoding="utf-8")
        return (template
            .replace("{paragraph}", paragraph)
            .replace("{title}", title_text)
            .replace("{date}", date))

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _title_word_violations(self, data: Dict, title: str) -> List[str]:
        """Return hidden words that appear in the title."""
        title_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", title)}
        return [
            w["word"] for w in data.get("hiddenWords", [])
            if w.get("word", "").lower() in title_words
        ]

    def _validate_json(self, data: Dict) -> None:
        required_keys = {"title", "date", "text", "hiddenWords"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"Missing required keys. Expected: {required_keys}")

        hidden_words = data.get("hiddenWords", [])
        if len(hidden_words) != 10:
            raise ValueError(f"Expected exactly 10 hidden words, got {len(hidden_words)}")

        for idx, word_obj in enumerate(hidden_words, 1):
            if "word" not in word_obj or "difficulty" not in word_obj or "clues" not in word_obj:
                raise ValueError(f"Word {idx} missing required fields")

            if word_obj["difficulty"] not in ["Easy", "Intermediate", "Hard"]:
                raise ValueError(f"Word {idx} has invalid difficulty: {word_obj['difficulty']}")

            clues = word_obj.get("clues", [])
            if len(clues) != 3:
                raise ValueError(f"Word {idx} must have exactly 3 clues, got {len(clues)}")

            clue_types = [c.get("type") for c in clues]
            if set(clue_types) != {"Indirect", "Suggestive", "Straight"}:
                raise ValueError(f"Word {idx} missing required clue types. Got: {clue_types}")

            for clue in clues:
                clue_type = clue.get("type")
                points    = clue.get("points")
                if clue_type == "Indirect"   and points not in [5, 6, 7]:
                    raise ValueError(f"Indirect clue must have 5-7 points, got {points}")
                elif clue_type == "Suggestive" and points not in [3, 4]:
                    raise ValueError(f"Suggestive clue must have 3-4 points, got {points}")
                elif clue_type == "Straight"   and points not in [1, 2]:
                    raise ValueError(f"Straight clue must have 1-2 points, got {points}")

        print("✅ JSON validation passed!")
        print("\n📝 Hidden Words (10):")
        by_difficulty: Dict[str, List[str]] = {"Easy": [], "Intermediate": [], "Hard": []}
        for word_obj in hidden_words:
            by_difficulty[word_obj["difficulty"]].append(word_obj["word"])
        for difficulty in ["Easy", "Intermediate", "Hard"]:
            words = by_difficulty[difficulty]
            if words:
                print(f"   {difficulty}: {', '.join(words)}")

    # ------------------------------------------------------------------
    # Core generation (single backend attempt)
    # ------------------------------------------------------------------

    def _generate_with_backend(self, paragraph: str, title: Optional[str],
                                date: str, backend: str, max_retries: int) -> Dict:
        """Try to generate using a specific backend, with retries for title violations."""
        client, model = self._client_and_model(backend)
        title_text    = title or "ClueChain Challenge"
        system_prompt = self._build_system_prompt()
        user_prompt   = self._build_user_prompt(paragraph, title, date)
        last_error    = "Unknown error"

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"       ↻ Retry {attempt}/{max_retries}...")

            try:
                content = _call_llm(client, model, system_prompt, user_prompt)
            except Exception as api_err:
                err_str = str(api_err).lower()
                # 429 / rate-limit: try rotating to GROQ_API_KEY2 before giving up
                if backend == "groq" and ("429" in err_str or "rate_limit" in err_str or "rate limit" in err_str):
                    if self.groq_key2 and self._active_groq_key != self.groq_key2:
                        print(f"       ⚠️  GROQ_API_KEY rate-limited — switching to GROQ_API_KEY2...")
                        self._active_groq_key = self.groq_key2
                        client, model = self._client_and_model(backend)
                        content = _call_llm(client, model, system_prompt, user_prompt)
                    else:
                        raise
                else:
                    raise
            result  = json.loads(content)

            if "text" not in result:
                result["text"] = paragraph
            if "id" not in result:
                result["id"] = f"ClueChain-{datetime.now().year}-{date}"

            violations = self._title_word_violations(result, title_text)
            if violations:
                print(f"       ⚠️  Title-word violation: {violations} — skipping (no retry)")
                last_error = f"Hidden words contain title words: {violations}"
                break

            self._validate_json(result)
            return result

        raise ValueError(f"[{backend}] Failed after {max_retries} attempts: {last_error}")

    # ------------------------------------------------------------------
    # Public generate (with automatic fallback)
    # ------------------------------------------------------------------

    def generate_json(self, paragraph: str, title: Optional[str] = None,
                      date: Optional[str] = None, max_retries: int = 3) -> Dict:
        """
        Generate ClueChain JSON. Uses the configured primary backend.
        If the primary fails all retries, automatically falls back to OpenRouter
        (if the key is available), rather than raising immediately.
        """
        if not date:
            date = datetime.now().strftime("%m-%d")

        title_text = title or "ClueChain Challenge"
        print(f"🚀 Generating ClueChain JSON...")
        print(f"   Title: {title_text}  |  Date: {date}  |  Backend: {self.backend}")
        print(f"   Paragraph length: {len(paragraph)} characters")

        try:
            return self._generate_with_backend(paragraph, title, date,
                                               self.backend, max_retries)
        except (ValueError, Exception) as primary_err:
            # Determine fallback backend
            fallback = "openrouter" if self.backend == "groq" else "groq"
            fallback_key = (self.openrouter_key if fallback == "openrouter"
                            else self.groq_key)

            if not fallback_key:
                raise ValueError(
                    f"Primary backend ({self.backend}) failed and no fallback key available.\n"
                    f"Error: {primary_err}"
                )

            print(f"\n   ⚠️  Primary backend ({self.backend}) failed: {primary_err}")
            print(f"   🔄 Falling back to {fallback} ({OPENROUTER_MODEL if fallback == 'openrouter' else GROQ_MODEL})...")

            return self._generate_with_backend(paragraph, title, date,
                                               fallback, max_retries)

    # ------------------------------------------------------------------
    # Save / summary
    # ------------------------------------------------------------------

    def save_json(self, data: Dict, output_dir: str, date: str,
                  title: Optional[str] = None) -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if title:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')
            filename = f"{date}_{safe_title}.json"
        else:
            filename = f"{date}.json"

        file_path = output_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return file_path

    def print_summary(self, data: Dict) -> None:
        print("\n" + "="*60)
        print("📊 GENERATION SUMMARY")
        print("="*60)
        print(f"Title: {data['title']}")
        print(f"Date:  {data['date']}")
        print(f"\n📝 Hidden Words ({len(data['hiddenWords'])}):")

        by_difficulty: Dict[str, List[str]] = {"Easy": [], "Intermediate": [], "Hard": []}
        for word_obj in data["hiddenWords"]:
            by_difficulty[word_obj["difficulty"]].append(word_obj["word"])
        for difficulty, words in by_difficulty.items():
            if words:
                print(f"  {difficulty}: {', '.join(words)}")

        related_groups, processed = [], set()
        for word_obj in data["hiddenWords"]:
            word    = word_obj["word"]
            related = word_obj.get("related_words", [])
            if related and word not in processed:
                group = sorted([word] + related)
                related_groups.append(group)
                processed.update(group)

        if related_groups:
            print(f"\n🔗 Thematically Related Word Groups:")
            for group in related_groups:
                print(f"  - {', '.join(group)}")
        else:
            print(f"\n🔗 Thematically Related Word Groups: None")
        print("="*60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate ClueChain JSON files from paragraph text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: Groq primary, OpenRouter fallback
  python generate_cluechain_json.py --file paragraph.txt --title "Food Science"

  # Force OpenRouter (Gemini Flash Lite)
  python generate_cluechain_json.py --file paragraph.txt --model openrouter

  # Specify date and output directory
  python generate_cluechain_json.py --file paragraph.txt --date 11-20 --output ./data
        """
    )
    parser.add_argument("--file",   required=True,        help="Path to paragraph text file")
    parser.add_argument("--title",                        help="Title (defaults to 'ClueChain Challenge')")
    parser.add_argument("--date",                         help="Date in MM-DD format (defaults to today)")
    parser.add_argument("--output", default="./assets/data/puzzles/daily/mmdd", help="Output directory")
    parser.add_argument("--model",  default="groq",
                        choices=["groq", "openrouter"],
                        help="Primary backend: groq (default) or openrouter")
    args = parser.parse_args()

    load_dotenv()
    groq_key       = os.getenv("GROQ_API_KEY")
    groq_key2      = os.getenv("GROQ_API_KEY2")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # Validate that the requested primary backend has a key
    if args.model == "groq" and not groq_key:
        print("❌ Error: GROQ_API_KEY not set. Add it to your .env file.")
        sys.exit(1)
    if args.model == "openrouter" and not openrouter_key:
        print("❌ Error: OPENROUTER_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    # Warn if fallback key is missing (non-fatal)
    if args.model == "groq" and groq_key2:
        print("ℹ️  GROQ_API_KEY2 found — will auto-rotate if primary key is rate-limited.")
    if args.model == "groq" and not openrouter_key:
        print("⚠️  OPENROUTER_API_KEY not set — no fallback available if Groq fails.")
    if args.model == "openrouter" and not groq_key:
        print("⚠️  GROQ_API_KEY not set — no fallback available if OpenRouter fails.")

    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            paragraph = f.read().strip()
        if not paragraph:
            print(f"❌ Error: File {args.file} is empty")
            sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.file}")
        sys.exit(1)

    try:
        import time
        start_time = time.time()

        generator = ClueChainGenerator(
            groq_key=groq_key,
            groq_key2=groq_key2,
            openrouter_key=openrouter_key,
            backend=args.model,
        )
        result = generator.generate_json(paragraph, args.title, args.date)

        date        = args.date or datetime.now().strftime("%m-%d")
        output_file = generator.save_json(result, args.output, date, args.title)

        duration = time.time() - start_time
        print(f"✅     Generated: {output_file.name} ({duration:.1f}s)\n")

        generator.print_summary(result)

        print(f"\n✅ JSON file saved to: {output_file}")
        print(f"\n💡 Tip: Validate with:")
        print(f"   python assets/data/json_validator.py {output_file}")

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
