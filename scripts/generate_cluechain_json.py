#!/usr/bin/env python3
"""
ClueChain JSON and Hints Generator

Generates ClueChain puzzle JSON from paragraph text.
Backend: Groq (fast, free tier).

Usage:
    python generate_cluechain_json.py --file paragraph.txt --title "Title" --date 07-15

Requirements:
    - GROQ_API_KEY in .env file
"""

import argparse
import csv
import datetime as dt
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

try:
    import spacy as _spacy
except ImportError:
    _spacy = None  # spaCy is optional but enables leak validation

# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

GROQ_MODEL   = "llama-3.3-70b-versatile"
_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _make_groq_client(api_key: str):
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        raise ImportError("groq package not installed. Run: uv pip install groq")


def _call_llm(client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Call Groq and return raw content."""
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
# ---------------------------------------------------------------------------
# Failure logging
# ---------------------------------------------------------------------------

_LOG_FILE = Path(__file__).parent.parent / "logs" / "batch_failures.csv"
_LOG_COLUMNS = ["timestamp", "mmdd", "title", "category", "reason_code",
                "attempts", "duration_s", "error_detail"]


def _classify_gen_error(error: str) -> str:
    patterns = [
        ("TITLE_WORD_VIOLATION", r"title word|contain title word|hidden words contain title"),
        ("CLUE_CONTAINS_WORD",   r"clue text contains the hidden word"),
        ("CLUE_TYPE_MISMATCH",   r"missing required clue types|clue types"),
        ("CLUE_POINTS_INVALID",  r"points, got|must have \d"),
        ("WRONG_CLUE_COUNT",     r"must have exactly 3 clues"),
        ("RATE_LIMIT",           r"429|rate.?limit"),
        ("JSON_PARSE_ERROR",     r"json|parse|decode"),
        ("TIMEOUT",              r"timeout"),
    ]
    low = error.lower()
    for code, pat in patterns:
        if re.search(pat, low):
            return code
    return "GENERATION_ERROR"


def log_generation_failure(date: str, title: str, reason_code: str,
                           attempt: int, duration: float, error_detail: str) -> None:
    """Append one per-attempt failure row to the persistent log."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_header = not _LOG_FILE.exists()
    mmdd = date.replace("-", "")  # "02-10" → "0210"
    with _LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp":    dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mmdd":         mmdd,
            "title":        title,
            "category":     "?",   # not known inside generator
            "reason_code":  reason_code,
            "attempts":     attempt,
            "duration_s":   f"{duration:.1f}",
            "error_detail": error_detail[:300].replace("\n", " "),
        })


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class ClueChainGenerator:
    """Generates ClueChain JSON files using Groq backend."""

    _nlp = None  # lazy-loaded spaCy model (class-level, shared across instances)

    def __init__(self, groq_key: Optional[str] = None,
                 groq_key2: Optional[str] = None,
                 groq_key3: Optional[str] = None):
        self.groq_key         = groq_key
        self.groq_key2        = groq_key2
        self.groq_key3        = groq_key3
        # Ordered list of available keys for rotation
        self._groq_keys       = [k for k in [groq_key, groq_key2, groq_key3] if k]
        self._active_groq_key = groq_key  # tracks which key is currently in use

        if not groq_key:
            raise ValueError("GROQ_API_KEY required")

    @classmethod
    def _get_nlp(cls):
        """Lazy-load spaCy model for leak validation."""
        if cls._nlp is None:
            if _spacy is None:
                return None
            try:
                cls._nlp = _spacy.load("en_core_web_sm")
            except OSError:
                print("Warning: spaCy model not found. Skipping leak validation.")
                print("  Install with: python -m spacy download en_core_web_sm")
                return None
        return cls._nlp

    def _client_and_model(self):
        return _make_groq_client(self._active_groq_key), GROQ_MODEL

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return (_PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")

    def _build_user_prompt(self, paragraph: str, title: Optional[str], date: str) -> str:
        title_text = title if title else "ClueChain Challenge"
        # Build an explicit banned-word list from the title for the prompt
        title_words = sorted({w for w in re.findall(r"[a-zA-Z]+", title_text) if len(w) > 3},
                             key=str.lower)
        title_words_list = ", ".join(title_words) if title_words else "(none)"
        template = (_PROMPTS_DIR / "user_prompt_template.txt").read_text(encoding="utf-8")
        return (template
            .replace("{paragraph}", paragraph)
            .replace("{title}", title_text)
            .replace("{date}", date)
            .replace("{title_words_list}", title_words_list))

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _title_word_violations(self, data: Dict, title: str) -> List[str]:
        """Return hidden words that appear in the title (exact or stemming match)."""
        title_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", title)}
        violations = []

        nlp = self._get_nlp()

        for w in data.get("hiddenWords", []):
            hw = w.get("word", "").lower()
            # Exact match
            if hw in title_words:
                violations.append(w["word"])
                continue

            # Stemming-aware match (requires spaCy)
            if nlp and len(hw) >= 4:
                try:
                    from score_paragraphs import _get_lemma, _shared_prefix_len, _FALSE_PREFIX_ROOTS
                    hw_lemma = _get_lemma(nlp, hw)
                    for tw in title_words:
                        if len(tw) < 4:
                            continue
                        tw_lemma = _get_lemma(nlp, tw)
                        # Lemma match
                        if hw_lemma == tw_lemma:
                            violations.append(w["word"])
                            break
                        # Shared prefix of 5+ chars
                        if len(hw) >= 5 and len(tw) >= 5:
                            plen = _shared_prefix_len(hw, tw)
                            if plen >= 5 and hw[:plen] not in _FALSE_PREFIX_ROOTS:
                                violations.append(w["word"])
                                break
                except ImportError:
                    pass  # score_paragraphs not available, skip stemming check

        return violations

    def _check_clue_leaks(self, data: Dict) -> List[str]:
        """Check all clues for hidden word leaks. Returns list of leak descriptions."""
        nlp = self._get_nlp()
        if nlp is None:
            return []  # Can't check without spaCy

        try:
            from score_paragraphs import _clue_word_leaks
        except ImportError:
            return []  # score_paragraphs not available

        leaks = []
        for hw in data.get("hiddenWords", []):
            word = hw["word"]
            for clue_obj in hw.get("clues", []):
                clue_text = clue_obj.get("clue", "")
                leaked = _clue_word_leaks(nlp, word, clue_text)
                if leaked:
                    leaks.append(f'"{word}" {clue_obj["type"]} clue has "{leaked}"')
        return leaks

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
                                date: str, max_retries: int) -> Dict:
        """Try to generate using Groq, with retries for validation failures."""
        client, model = self._client_and_model()
        title_text    = title or "ClueChain Challenge"
        system_prompt = self._build_system_prompt()
        user_prompt   = self._build_user_prompt(paragraph, title, date)
        last_error    = "Unknown error"
        import time as _time

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"       ↻ Retry {attempt}/{max_retries}...")

            attempt_start = _time.time()
            attempt_error = None

            try:
                content = _call_llm(client, model, system_prompt, user_prompt)
            except Exception as api_err:
                err_str = str(api_err).lower()
                # 429 / rate-limit: rotate to the next available key before giving up
                if "429" in err_str or "rate_limit" in err_str or "rate limit" in err_str:
                    current_idx = self._groq_keys.index(self._active_groq_key) if self._active_groq_key in self._groq_keys else -1
                    next_idx = current_idx + 1
                    if next_idx < len(self._groq_keys):
                        next_key = self._groq_keys[next_idx]
                        key_num = next_idx + 1
                        print(f"       ⚠️  Groq key rate-limited — switching to GROQ_API_KEY{key_num}...")
                        self._active_groq_key = next_key
                        client, model = self._client_and_model()
                        content = _call_llm(client, model, system_prompt, user_prompt)
                    else:
                        attempt_error = str(api_err)
                        last_error = attempt_error
                        log_generation_failure(date, title_text,
                                               _classify_gen_error(attempt_error),
                                               attempt, _time.time() - attempt_start,
                                               attempt_error)
                        raise
                else:
                    attempt_error = str(api_err)
                    last_error = attempt_error
                    log_generation_failure(date, title_text,
                                           _classify_gen_error(attempt_error),
                                           attempt, _time.time() - attempt_start,
                                           attempt_error)
                    raise

            try:
                result = json.loads(content)
            except Exception as parse_err:
                attempt_error = f"JSON parse error: {parse_err}"
                last_error = attempt_error
                log_generation_failure(date, title_text, "JSON_PARSE_ERROR",
                                       attempt, _time.time() - attempt_start,
                                       attempt_error)
                continue

            if "text" not in result:
                result["text"] = paragraph
            if "id" not in result:
                result["id"] = f"ClueChain-{datetime.now().year}-{date}"

            violations = self._title_word_violations(result, title_text)
            if violations:
                attempt_error = f"Hidden words contain title words: {violations}"
                last_error = attempt_error
                print(f"       ⚠️  Title-word violation: {violations} — skipping (no retry)")
                log_generation_failure(date, title_text, "TITLE_WORD_VIOLATION",
                                       attempt, _time.time() - attempt_start,
                                       attempt_error)
                break

            try:
                self._validate_json(result)
            except ValueError as val_err:
                attempt_error = str(val_err)
                last_error = attempt_error
                log_generation_failure(date, title_text,
                                       _classify_gen_error(attempt_error),
                                       attempt, _time.time() - attempt_start,
                                       attempt_error)
                continue

            # Post-validation: check for clue leaks (spaCy-based)
            clue_leak_issues = self._check_clue_leaks(result)
            if clue_leak_issues:
                attempt_error = f"Clue leaks detected: {clue_leak_issues}"
                last_error = attempt_error
                print(f"       ⚠️  {attempt_error} — retrying")
                log_generation_failure(date, title_text, "CLUE_LEAK",
                                       attempt, _time.time() - attempt_start,
                                       attempt_error)
                continue

            return result

        raise ValueError(f"[groq] Failed after {max_retries} attempts: {last_error}")

    # ------------------------------------------------------------------
    # Public generate
    # ------------------------------------------------------------------

    def generate_json(self, paragraph: str, title: Optional[str] = None,
                      date: Optional[str] = None, max_retries: int = 3) -> Dict:
        """Generate ClueChain JSON using Groq."""
        if not date:
            date = datetime.now().strftime("%m-%d")

        title_text = title or "ClueChain Challenge"
        print(f"🚀 Generating ClueChain JSON...")
        print(f"   Title: {title_text}  |  Date: {date}  |  Backend: groq")
        print(f"   Paragraph length: {len(paragraph)} characters")

        return self._generate_with_backend(paragraph, title, date, max_retries)

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
  python generate_cluechain_json.py --file paragraph.txt --title "Food Science"
  python generate_cluechain_json.py --file paragraph.txt --date 11-20 --output ./data
        """
    )
    parser.add_argument("--file",   required=True,        help="Path to paragraph text file")
    parser.add_argument("--title",                        help="Title (defaults to 'ClueChain Challenge')")
    parser.add_argument("--date",                         help="Date in MM-DD format (defaults to today)")
    parser.add_argument("--output", default="./assets/data/puzzles/daily/mmdd", help="Output directory")
    args = parser.parse_args()

    load_dotenv()
    groq_key  = os.getenv("GROQ_API_KEY")
    groq_key2 = os.getenv("GROQ_API_KEY2")
    groq_key3 = os.getenv("GROQ_API_KEY3")

    if not groq_key:
        print("❌ Error: GROQ_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    if groq_key2:
        print("ℹ️  GROQ_API_KEY2 found — will auto-rotate if primary key is rate-limited.")
    if groq_key3:
        print("ℹ️  GROQ_API_KEY3 found — will auto-rotate if secondary key is rate-limited.")

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
            groq_key3=groq_key3,
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
