#!/usr/bin/env python3
"""
ClueChain Title Leak Fixer

Fixes title leaks — hidden words that appear in the puzzle title — by asking
an LLM to pick the best replacement word from the paragraph and generate
3 clues for it.

Usage:
    python scripts/fix_title_leaks.py --dry-run                # Scan only, show leaks
    python scripts/fix_title_leaks.py                          # Fix all, preview
    python scripts/fix_title_leaks.py --batch-size 10          # Fix first 10
    python scripts/fix_title_leaks.py --file 0119.json         # Fix specific file(s)
    python scripts/fix_title_leaks.py --start-from 0500        # Resume from MMDD
    python scripts/fix_title_leaks.py --provider nim            # Force NIM
    python scripts/fix_title_leaks.py --delay 3                # Throttle (default 5s)

Requirements:
    - GROQ_API_KEY (+ optional GROQ_API_KEY2, GROQ_API_KEY3) in .env
    - NIM_API_KEY in .env (optional, used as fallback)
    - python -m spacy download en_core_web_sm
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

from score_paragraphs import (
    _clue_word_leaks,
    _get_lemma,
    _load_spacy_model,
    _shared_prefix_len,
    _FALSE_PREFIX_ROOTS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROQ_MODEL = "llama-3.3-70b-versatile"
NIM_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
_SCRIPT_DIR = Path(__file__).parent
_PROMPTS_DIR = _SCRIPT_DIR / "prompts"
_OUTPUT_DIR = _SCRIPT_DIR / "output"
_MMDD_DIR = _SCRIPT_DIR.parent / "assets" / "data" / "puzzles" / "daily" / "mmdd"

_PROGRESS_FILE = _OUTPUT_DIR / "title_fix_progress.json"
_FIX_LOG_CSV = _OUTPUT_DIR / "title_fix_log.csv"
_FIX_PROMPT = _PROMPTS_DIR / "fix_title_word_prompt.txt"

# Valid clue point ranges by type
_VALID_POINTS = {
    "Indirect": {5, 6, 7},
    "Suggestive": {3, 4},
    "Straight": {1, 2},
}
_VALID_DIFFICULTIES = {"Easy", "Intermediate", "Hard"}


# ---------------------------------------------------------------------------
# LLM helpers — multi-provider with automatic fallback
# ---------------------------------------------------------------------------

class LLMProvider:
    """Wraps one or more API backends with automatic key rotation and fallback."""

    def __init__(self):
        self._backends: List[Tuple[str, object, str]] = []  # (name, client, model)
        self._current = 0

    def add_groq(self, api_key: str):
        try:
            from groq import Groq
            self._backends.append(("groq", Groq(api_key=api_key), GROQ_MODEL))
        except ImportError:
            raise ImportError("groq package not installed. Run: uv pip install groq")

    def add_nim(self, api_key: str):
        try:
            from openai import OpenAI
            client = OpenAI(base_url=NIM_BASE_URL, api_key=api_key)
            self._backends.append(("nim", client, NIM_MODEL))
        except ImportError:
            raise ImportError("openai package not installed. Run: uv pip install openai")

    @property
    def name(self) -> str:
        if not self._backends:
            return "none"
        return self._backends[self._current][0]

    def _rotate(self) -> bool:
        """Move to next backend. Returns False if exhausted."""
        next_idx = self._current + 1
        if next_idx >= len(self._backends):
            return False
        self._current = next_idx
        name = self._backends[self._current][0]
        print(f"    >> Rotated to {name} (backend {self._current + 1}/{len(self._backends)})")
        return True

    def call(self, system_prompt: str, user_prompt: str) -> str:
        """Call the current backend, rotating on rate-limit errors."""
        last_err = None
        while True:
            name, client, model = self._backends[self._current]
            try:
                kwargs = dict(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4096 if name == "nim" else 800,
                    timeout=60 if name == "nim" else 30,
                )
                # NIM doesn't support response_format json_object
                if name != "nim":
                    kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if not content:
                    raise ValueError(f"{name} returned empty response")
                return content
            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "rate" in err_str.lower()
                if is_rate_limit and self._rotate():
                    last_err = e
                    continue
                raise
        raise last_err  # should not reach here


def _build_provider(force: Optional[str] = None) -> LLMProvider:
    """Build an LLMProvider from environment variables."""
    provider = LLMProvider()

    groq_keys = [k for k in [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY2"),
        os.getenv("GROQ_API_KEY3"),
    ] if k]

    nim_key = os.getenv("NIM_API_KEY")

    if force == "nim":
        if not nim_key:
            print("Error: --provider nim requires NIM_API_KEY in .env")
            sys.exit(1)
        provider.add_nim(nim_key)
        for k in groq_keys:
            provider.add_groq(k)
    elif force == "groq":
        for k in groq_keys:
            provider.add_groq(k)
        if nim_key:
            provider.add_nim(nim_key)
    else:
        for k in groq_keys:
            provider.add_groq(k)
        if nim_key:
            provider.add_nim(nim_key)

    if not provider._backends:
        print("Error: No API keys found. Set GROQ_API_KEY or NIM_API_KEY in .env")
        sys.exit(1)

    names = [b[0] for b in provider._backends]
    print(f"LLM backends: {', '.join(names)} ({len(names)} total)")
    return provider


# ---------------------------------------------------------------------------
# Title leak scanning
# ---------------------------------------------------------------------------

def scan_title_leaks(nlp, data: Dict) -> List[str]:
    """
    Detect hidden words that leak into the title.

    Checks:
    1. Exact match (case-insensitive)
    2. Lemma match (e.g. "eroding" in title matches hidden word "erosion")
    3. Shared prefix of 5+ chars (e.g. title "Nature" blocks hidden "natural")

    Returns list of leaked hidden word strings.
    """
    title = data.get("title", "")
    title_words_raw = re.findall(r"[a-zA-Z]+", title)
    title_words_lower = {w.lower() for w in title_words_raw}
    title_lemmas = {_get_lemma(nlp, w.lower()) for w in title_words_raw if len(w) >= 4}

    leaked = []

    for hw in data.get("hiddenWords", []):
        word = hw["word"]
        word_lower = word.lower()
        hw_lemma = _get_lemma(nlp, word_lower)

        # Check 1: exact match
        if word_lower in title_words_lower:
            leaked.append(word)
            continue

        # Check 2: lemma match
        if hw_lemma in title_lemmas:
            leaked.append(word)
            continue

        # Check 3: shared prefix of 5+ chars with any title word
        found = False
        for tw in title_words_lower:
            if len(tw) >= 5 and len(word_lower) >= 5:
                plen = _shared_prefix_len(word_lower, tw)
                if plen >= 5:
                    shared = word_lower[:plen]
                    if shared not in _FALSE_PREFIX_ROOTS:
                        leaked.append(word)
                        found = True
                        break
        if found:
            continue

    return leaked


# ---------------------------------------------------------------------------
# LLM-based title leak fixing
# ---------------------------------------------------------------------------

def fix_title_leak(nlp, provider: LLMProvider, data: Dict, leaked_word: str,
                   max_retries: int = 5) -> Optional[Dict]:
    """
    Ask the LLM to pick a replacement word and generate clues.

    Returns dict with 'old_word', 'new_word', 'new_hw_obj' on success, None on failure.
    """
    title = data.get("title", "")
    text = data.get("text", "")
    hidden_words = [hw["word"] for hw in data.get("hiddenWords", [])]
    hidden_words_str = ", ".join(hidden_words)

    # Build explicit banned title words list
    title_words_raw = re.findall(r"[a-zA-Z]+", title)
    title_words_lower = sorted({w.lower() for w in title_words_raw if len(w) >= 3})
    title_words_banned = ", ".join(title_words_lower)

    template = _FIX_PROMPT.read_text(encoding="utf-8")
    user_prompt = (template
        .replace("{title}", title)
        .replace("{paragraph_text}", text)
        .replace("{current_hidden_words}", hidden_words_str)
        .replace("{leaked_word}", leaked_word)
        .replace("{title_words_banned}", title_words_banned)
    )

    system_prompt = (
        "You are a word selector and clue writer for a word-guessing game. "
        "Pick a replacement word and write 3 clues. Respond with ONLY valid JSON."
    )

    attempt_errors = []

    for attempt in range(1, max_retries + 1):
        try:
            raw = provider.call(system_prompt, user_prompt)
            result = json.loads(raw)

            word = result.get("word", "").strip().lower()
            difficulty = result.get("difficulty", "Intermediate")
            clues = result.get("clues", [])

            # Validate the replacement
            error = _validate_replacement(nlp, data, leaked_word, word, difficulty, clues)
            if error:
                msg = f"word='{word}': {error}"
                attempt_errors.append(msg)
                print(f"         Attempt {attempt}: {msg}, retrying...")
                continue

            new_hw_obj = {
                "word": word,
                "difficulty": difficulty,
                "related_words": [],
                "clues": clues,
            }

            return {
                "old_word": leaked_word,
                "new_word": word,
                "new_hw_obj": new_hw_obj,
                "attempt_errors": attempt_errors,
            }

        except json.JSONDecodeError as e:
            msg = f"JSON parse error: {e}"
            attempt_errors.append(msg)
            print(f"         Attempt {attempt}: {msg}")
        except Exception as e:
            err_str = str(e)
            msg = f"error: {err_str}"
            attempt_errors.append(msg)
            print(f"         Attempt {attempt}: {msg}")
            if "429" in err_str or "rate" in err_str.lower():
                raise  # Propagate rate limits

    return {"attempt_errors": attempt_errors}


def _validate_replacement(nlp, data: Dict, leaked_word: str, word: str,
                          difficulty: str, clues: List[Dict]) -> Optional[str]:
    """
    Validate LLM output. Returns error string if invalid, None if valid.
    """
    title = data.get("title", "")
    text = data.get("text", "")
    hidden_words_lower = {hw["word"].lower() for hw in data.get("hiddenWords", [])}

    # 1. Word must be non-empty
    if not word:
        return "empty word"

    # 2. Word must be >= 4 letters
    if len(word) < 4:
        return f"word '{word}' too short ({len(word)} chars)"

    # 3. Word must exist in paragraph text (case-insensitive)
    # Use [^a-zA-Z] boundaries instead of \b to handle quotes/punctuation
    pattern = r'(?<![a-zA-Z])' + re.escape(word) + r'(?![a-zA-Z])'
    if not re.search(pattern, text, re.IGNORECASE):
        return f"word '{word}' not found in paragraph text"

    # 4. Word must not be in the title
    title_words_raw = re.findall(r"[a-zA-Z]+", title)
    title_words_lower = {w.lower() for w in title_words_raw}
    title_lemmas = {_get_lemma(nlp, w.lower()) for w in title_words_raw if len(w) >= 4}

    if word in title_words_lower:
        return f"word '{word}' appears in title (exact)"

    word_lemma = _get_lemma(nlp, word)
    if word_lemma in title_lemmas:
        return f"word '{word}' matches title word (lemma)"

    for tw in title_words_lower:
        if len(tw) >= 5 and len(word) >= 5:
            plen = _shared_prefix_len(word, tw)
            if plen >= 5:
                shared = word[:plen]
                if shared not in _FALSE_PREFIX_ROOTS:
                    return f"word '{word}' shares prefix '{shared}' with title word '{tw}'"

    # 5. Word must not already be a hidden word
    if word in hidden_words_lower:
        return f"word '{word}' is already a hidden word"

    # 6. Valid difficulty
    if difficulty not in _VALID_DIFFICULTIES:
        return f"invalid difficulty '{difficulty}'"

    # 7. Must have exactly 3 clues
    if len(clues) != 3:
        return f"expected 3 clues, got {len(clues)}"

    # 8. Validate clue structure and types
    seen_types = set()
    for clue_obj in clues:
        clue_text = clue_obj.get("clue", "")
        clue_type = clue_obj.get("type", "")
        points = clue_obj.get("points")

        if not clue_text:
            return "empty clue text"

        if clue_type not in _VALID_POINTS:
            return f"invalid clue type '{clue_type}'"

        if clue_type in seen_types:
            return f"duplicate clue type '{clue_type}'"
        seen_types.add(clue_type)

        if points not in _VALID_POINTS[clue_type]:
            return f"{clue_type} clue has invalid points {points} (valid: {_VALID_POINTS[clue_type]})"

        # 9. Clues must be leak-free
        leaked = _clue_word_leaks(nlp, word, clue_text)
        if leaked:
            return f"{clue_type} clue leaks '{leaked}'"

    # Ensure all 3 types present
    if seen_types != {"Indirect", "Suggestive", "Straight"}:
        missing = {"Indirect", "Suggestive", "Straight"} - seen_types
        return f"missing clue type(s): {missing}"

    return None


# ---------------------------------------------------------------------------
# Fix log
# ---------------------------------------------------------------------------

_LOG_FIELDS = ["timestamp", "mmdd", "title", "leaked_word", "new_word",
               "difficulty", "status", "detail"]


def _log_fix(mmdd: str, title: str, leaked_word: str, new_word: str,
             difficulty: str, status: str, detail: str):
    """Append a row to the fix log CSV."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not _FIX_LOG_CSV.exists()
    with _FIX_LOG_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mmdd": mmdd,
            "title": title,
            "leaked_word": leaked_word,
            "new_word": new_word,
            "difficulty": difficulty,
            "status": status,
            "detail": detail[:300],
        })


# ---------------------------------------------------------------------------
# Progress checkpoint
# ---------------------------------------------------------------------------

def _load_progress() -> Dict:
    if _PROGRESS_FILE.exists():
        with open(_PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def _save_progress(progress: Dict):
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


# ---------------------------------------------------------------------------
# Per-puzzle processing
# ---------------------------------------------------------------------------

def process_puzzle(nlp, provider: Optional[LLMProvider], filepath: Path,
                   data: Dict, leaked_words: List[str],
                   dry_run: bool) -> int:
    """
    Process a single puzzle file, replacing leaked hidden words.

    Returns count of fixes applied.
    """
    mmdd = filepath.stem
    title = data.get("title", "")
    fixes = 0
    modified = False

    for leaked_word in leaked_words:
        if dry_run:
            print(f"    [DRY-RUN] Title leak: '{leaked_word}' appears in title '{title}'")
            fixes += 1
            continue

        print(f"    Fixing title leak: '{leaked_word}'")

        try:
            result = fix_title_leak(nlp, provider, data, leaked_word)

            if "new_hw_obj" in result:
                # Success — replace the hidden word object in the puzzle
                for i, hw in enumerate(data["hiddenWords"]):
                    if hw["word"].lower() == leaked_word.lower():
                        data["hiddenWords"][i] = result["new_hw_obj"]

                        # Clean up related_words references in other hidden words
                        for other_hw in data["hiddenWords"]:
                            if leaked_word.lower() in [r.lower() for r in other_hw.get("related_words", [])]:
                                other_hw["related_words"] = [
                                    r for r in other_hw["related_words"]
                                    if r.lower() != leaked_word.lower()
                                ]
                        break

                modified = True
                fixes += 1
                _log_fix(mmdd, title, leaked_word, result["new_word"],
                         result["new_hw_obj"]["difficulty"], "success",
                         f"'{leaked_word}' -> '{result['new_word']}'")
                print(f"      Swapped: '{leaked_word}' -> '{result['new_word']}'")
            else:
                # All attempts failed — log the reasons
                errors = result.get("attempt_errors", [])
                detail = " | ".join(errors) if errors else "unknown"
                _log_fix(mmdd, title, leaked_word, "", "", "failed", detail)
                print(f"      FAILED: {detail}")
        except Exception as e:
            _log_fix(mmdd, title, leaked_word, "", "", "error", str(e))
            raise

    # Write modified file
    if modified and not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"    Saved: {filepath.name}")

    return fixes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fix title leaks in ClueChain puzzles using LLM-powered word replacement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--batch-size", type=int, default=0,
                        help="Max puzzles to fix (0 = all)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between API calls in seconds (default: 5.0)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan only — show leaks without fixing")
    parser.add_argument("--start-from", type=str, default=None,
                        help="Start from this MMDD (skip earlier puzzles)")
    parser.add_argument("--file", nargs="+", default=None,
                        help="Fix specific files (paths or filenames in mmdd dir)")
    parser.add_argument("--provider", choices=["groq", "nim"], default=None,
                        help="Force a specific LLM provider (default: groq first, nim fallback)")
    args = parser.parse_args()

    load_dotenv()
    nlp = _load_spacy_model()

    # Set up LLM provider (skip in dry-run)
    provider = None
    if not args.dry_run:
        provider = _build_provider(force=args.provider)

    # Load puzzle files
    if args.file:
        puzzles = []
        for fp in args.file:
            path = Path(fp)
            if not path.is_absolute():
                # Try as filename in mmdd dir first
                mmdd_path = _MMDD_DIR / fp
                if mmdd_path.exists():
                    path = mmdd_path
                else:
                    path = Path.cwd() / fp
            with open(path, encoding="utf-8") as f:
                puzzles.append((path, json.load(f)))
    else:
        puzzles = []
        for path in sorted(_MMDD_DIR.glob("*.json")):
            mmdd = path.stem
            if args.start_from and mmdd < args.start_from:
                continue
            with open(path, encoding="utf-8") as f:
                puzzles.append((path, json.load(f)))

    print(f"Loaded {len(puzzles)} puzzle file(s)")

    # Phase 1: Scan for title leaks
    print("\n--- Scanning for title leaks ---")
    work_list = []  # (filepath, data, leaked_words)
    total_leaks = 0

    for filepath, data in puzzles:
        leaked = scan_title_leaks(nlp, data)
        if leaked:
            work_list.append((filepath, data, leaked))
            total_leaks += len(leaked)

    print(f"Found {total_leaks} title leak(s) across {len(work_list)} puzzle(s)")

    if not work_list:
        print("Nothing to fix!")
        return

    # Filter out already-completed puzzles (unless --file mode)
    if not args.file:
        progress = _load_progress()
        completed = set(progress.get("completed", []))
        before = len(work_list)
        work_list = [(fp, d, lw) for fp, d, lw in work_list if fp.stem not in completed]
        skipped = before - len(work_list)
        if skipped:
            print(f"Skipping {skipped} already-completed puzzle(s)")
    else:
        progress = _load_progress()

    if not work_list:
        print("All leaky puzzles already completed!")
        return

    # Apply batch size
    if args.batch_size > 0:
        work_list = work_list[:args.batch_size]

    print(f"\nPuzzles to process: {len(work_list)}")

    if args.dry_run:
        print("\n--- Dry Run Results ---")

    # Phase 2: Fix leaks
    total_fixes = 0
    total_failures = 0

    for i, (filepath, data, leaked_words) in enumerate(work_list, 1):
        mmdd = filepath.stem
        title = data.get("title", "")
        print(f"\n[{i}/{len(work_list)}] {mmdd} ({title}) — {len(leaked_words)} leak(s)")

        try:
            fixes = process_puzzle(nlp, provider, filepath, data, leaked_words, args.dry_run)
            total_fixes += fixes
            total_failures += len(leaked_words) - fixes

            if not args.dry_run:
                progress["completed"].append(mmdd)
                _save_progress(progress)

            # Delay between puzzles
            if not args.dry_run and i < len(work_list):
                time.sleep(args.delay)

        except Exception as e:
            err_str = str(e)
            print(f"    ERROR: {err_str}")
            if not args.dry_run:
                progress["failed"].append(mmdd)
                _save_progress(progress)
            if "429" in err_str or "rate" in err_str.lower():
                print("Rate limited — stopping.")
                break

    # Summary
    print(f"\n--- Summary ---")
    print(f"Title leaks fixed: {total_fixes}")
    if total_failures > 0:
        print(f"Failed:            {total_failures}")
    if not args.dry_run and total_fixes > 0:
        print(f"Fix log: {_FIX_LOG_CSV}")
        print(f"Progress: {_PROGRESS_FILE}")


if __name__ == "__main__":
    main()
