#!/usr/bin/env python3
"""
ClueChain Leak Fixer

Fixes clue leaks and title spoilers in puzzle JSONs using Groq LLM,
with automatic fallback to NVIDIA NIM when Groq rate-limits.

Two fix strategies:
1. Clue leaks: Re-generate the leaking clue via LLM with banned-word constraints
2. Title spoilers: Swap the hidden word with another word from the paragraph

Requires leak_audit.csv from audit_leaks.py (run that first).

Usage:
    python scripts/audit_leaks.py                              # Step 1: scan
    python scripts/fix_leaks.py --dry-run                      # Preview changes
    python scripts/fix_leaks.py --fix-type clue                # Fix clue leaks only
    python scripts/fix_leaks.py --fix-type title               # Fix title leaks only
    python scripts/fix_leaks.py --fix-type both                # Fix both
    python scripts/fix_leaks.py --batch-size 10 --delay 5      # Throttled batch
    python scripts/fix_leaks.py --start-from 0315              # Resume from MMDD
    python scripts/fix_leaks.py --provider nim                 # Force NIM provider
    python scripts/fix_leaks.py --file some.json --dry-run     # Direct scan (one-off)

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
from collections import defaultdict
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

_PROGRESS_FILE = _OUTPUT_DIR / "fix_progress.json"
_FIX_LOG_CSV = _OUTPUT_DIR / "fix_log.csv"
_FIX_CLUE_PROMPT = _PROMPTS_DIR / "fix_clue_prompt.txt"
_AUDIT_CSV = _OUTPUT_DIR / "leak_audit.csv"


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
        start = self._current
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
                    max_tokens=500,
                    timeout=30,
                )
                # NIM doesn't support response_format json_object
                if name != "nim":
                    kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
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
        # Still add Groq as fallback
        for k in groq_keys:
            provider.add_groq(k)
    elif force == "groq":
        for k in groq_keys:
            provider.add_groq(k)
        if nim_key:
            provider.add_nim(nim_key)
    else:
        # Default: Groq first (all keys), then NIM as fallback
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
# Banned word list builder
# ---------------------------------------------------------------------------

def _build_banned_words(nlp, hidden_word: str, leaked_word: str) -> List[str]:
    """Build a comprehensive banned-word list for clue regeneration."""
    hw_lower = hidden_word.lower()
    hw_lemma = _get_lemma(nlp, hw_lower)
    lw_lower = leaked_word.lower()
    lw_lemma = _get_lemma(nlp, lw_lower)

    banned = {hw_lower, hw_lemma, lw_lower, lw_lemma}

    # Add common inflections
    for base in [hw_lower, hw_lemma]:
        banned.add(base + "s")
        banned.add(base + "es")
        banned.add(base + "ed")
        banned.add(base + "ing")
        banned.add(base + "er")
        banned.add(base + "ly")
        banned.add(base + "tion")
        banned.add(base + "ment")
        if base.endswith("e"):
            banned.add(base[:-1] + "ing")
            banned.add(base[:-1] + "ed")
        if base.endswith("y"):
            banned.add(base[:-1] + "ies")
            banned.add(base[:-1] + "ied")

    return sorted(banned)


# ---------------------------------------------------------------------------
# Clue leak fixing
# ---------------------------------------------------------------------------

def fix_clue_leak(nlp, provider: LLMProvider, puzzle_data: Dict,
                  hw_obj: Dict, clue_idx: int, leaked_word: str,
                  max_retries: int = 3) -> Optional[Dict]:
    """
    Generate a replacement clue for a leaking clue.

    Returns the new clue dict on success, None on failure.
    """
    clue_obj = hw_obj["clues"][clue_idx]
    hidden_word = hw_obj["word"]
    banned = _build_banned_words(nlp, hidden_word, leaked_word)

    template = _FIX_CLUE_PROMPT.read_text(encoding="utf-8")

    user_prompt = (template
        .replace("{paragraph_text}", puzzle_data.get("text", ""))
        .replace("{hidden_word}", hidden_word)
        .replace("{clue_type}", clue_obj["type"])
        .replace("{clue_points}", str(clue_obj["points"]))
        .replace("{original_clue}", clue_obj["clue"])
        .replace("{banned_words_list}", ", ".join(banned))
    )

    system_prompt = (
        "You are a clue writer for a word-guessing game. "
        "Write a single replacement clue. Respond with ONLY valid JSON."
    )

    for attempt in range(1, max_retries + 1):
        try:
            raw = provider.call(system_prompt, user_prompt)
            result = json.loads(raw)

            new_clue_text = result.get("clue", "")
            if not new_clue_text:
                continue

            # Validate the new clue is leak-free
            new_leak = _clue_word_leaks(nlp, hidden_word, new_clue_text)
            if new_leak:
                print(f"         Attempt {attempt}: replacement still leaks '{new_leak}', retrying...")
                continue

            return {
                "clue": new_clue_text,
                "type": clue_obj["type"],
                "points": clue_obj["points"],
            }

        except Exception as e:
            print(f"         Attempt {attempt} error: {e}")
            if "429" in str(e) or "rate" in str(e).lower():
                raise  # Propagate rate limits

    return None


# ---------------------------------------------------------------------------
# Title spoiler fixing (word swap)
# ---------------------------------------------------------------------------

def find_replacement_words(nlp, puzzle_data: Dict, title: str) -> List[str]:
    """Find candidate replacement words from the paragraph text."""
    text = puzzle_data.get("text", "")
    title_words_lower = {w.lower() for w in re.findall(r"[a-zA-Z]+", title)}
    hidden_words_lower = {hw["word"].lower() for hw in puzzle_data.get("hiddenWords", [])}

    doc = nlp(text)
    candidates = []
    seen = set()

    for token in doc:
        w = token.text.lower()
        if (token.is_alpha
            and len(w) >= 4
            and not token.is_stop
            and token.pos_ in ("NOUN", "VERB", "ADJ")
            and not token.ent_type_  # skip named entities
            and w not in title_words_lower
            and w not in hidden_words_lower
            and w not in seen):
            # Check that the word's lemma doesn't match any title word lemma
            w_lemma = token.lemma_.lower()
            title_lemma_match = False
            for tw in title_words_lower:
                if len(tw) >= 4 and _get_lemma(nlp, tw) == w_lemma:
                    title_lemma_match = True
                    break
            if not title_lemma_match:
                candidates.append(w)
                seen.add(w)

    return candidates


def generate_clues_for_word(provider: LLMProvider, paragraph_text: str,
                            word: str, max_retries: int = 3) -> Optional[List[Dict]]:
    """Generate 3 clues for a replacement word."""
    system_prompt = (
        "You are a clue writer for a word-guessing game called ClueChain. "
        "Generate exactly 3 clues for the given word. Respond with ONLY valid JSON."
    )

    user_prompt = f"""Generate 3 clues for the hidden word "{word}" in this paragraph:

{paragraph_text}

Rules:
- Do NOT use the word "{word}" or any of its variants in any clue
- One Indirect clue (5-7 points): lateral thinking, wordplay
- One Suggestive clue (3-4 points): characteristic or association
- One Straight clue (1-2 points): direct definition

Respond with JSON:
{{
  "clues": [
    {{"clue": "...", "type": "Indirect", "points": 6}},
    {{"clue": "...", "type": "Suggestive", "points": 3}},
    {{"clue": "...", "type": "Straight", "points": 1}}
  ]
}}"""

    for attempt in range(1, max_retries + 1):
        try:
            raw = provider.call(system_prompt, user_prompt)
            result = json.loads(raw)
            clues = result.get("clues", [])
            if len(clues) == 3:
                return clues
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                raise
    return None


def fix_title_spoiler(nlp, provider: LLMProvider, puzzle_data: Dict,
                      spoiled_word: str) -> Optional[Dict]:
    """
    Fix a title spoiler by swapping the hidden word with a replacement from the paragraph.

    Returns dict with 'old_word', 'new_word', 'new_hw_obj' on success, None on failure.
    """
    title = puzzle_data.get("title", "")
    candidates = find_replacement_words(nlp, puzzle_data, title)

    if not candidates:
        print(f"         No replacement candidates found for '{spoiled_word}'")
        return None

    # Try first 3 candidates
    for candidate in candidates[:3]:
        clues = generate_clues_for_word(
            provider, puzzle_data.get("text", ""), candidate
        )
        if not clues:
            continue

        # Validate all clues are leak-free
        all_clean = True
        for clue_obj in clues:
            leak = _clue_word_leaks(nlp, candidate, clue_obj.get("clue", ""))
            if leak:
                all_clean = False
                break

        if all_clean:
            # Find the original hw object to determine difficulty
            old_hw = next(
                (hw for hw in puzzle_data["hiddenWords"]
                 if hw["word"].lower() == spoiled_word.lower()),
                None
            )
            difficulty = old_hw["difficulty"] if old_hw else "Intermediate"

            # Build replacement hidden word object
            new_hw_obj = {
                "word": candidate,
                "difficulty": difficulty,
                "related_words": [],
                "clues": clues,
            }

            return {
                "old_word": spoiled_word,
                "new_word": candidate,
                "new_hw_obj": new_hw_obj,
            }

    return None


# ---------------------------------------------------------------------------
# Fix log
# ---------------------------------------------------------------------------

_LOG_FIELDS = ["timestamp", "mmdd", "title", "fix_type", "hidden_word",
               "action", "detail", "status"]


def _log_fix(mmdd: str, title: str, fix_type: str, hidden_word: str,
             action: str, detail: str, status: str):
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
            "fix_type": fix_type,
            "hidden_word": hidden_word,
            "action": action,
            "detail": detail[:300],
            "status": status,
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
# CSV-based leak loading
# ---------------------------------------------------------------------------

def _load_leaks_from_csv(fix_type: str, start_from: Optional[str] = None
                         ) -> Dict[str, Dict]:
    """
    Read leak_audit.csv and group rows by mmdd.

    Returns dict keyed by mmdd, each value a dict with:
        clue_leaks: list of CSV rows with leak_type == "clue_leak"
        title_spoilers: list of CSV rows with leak_type in ("title_spoiler", "title_spoiler_stem")
    """
    grouped: Dict[str, Dict] = {}
    with open(_AUDIT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mmdd = row["mmdd"]
            if start_from and mmdd < start_from:
                continue

            leak_type = row["leak_type"]

            # Filter by requested fix type
            is_clue = leak_type == "clue_leak"
            is_title = leak_type in ("title_spoiler", "title_spoiler_stem")
            if fix_type == "clue" and not is_clue:
                continue
            if fix_type == "title" and not is_title:
                continue
            if not is_clue and not is_title:
                continue

            if mmdd not in grouped:
                grouped[mmdd] = {"clue_leaks": [], "title_spoilers": []}

            if is_clue:
                grouped[mmdd]["clue_leaks"].append(row)
            else:
                grouped[mmdd]["title_spoilers"].append(row)

    return grouped


def _resolve_clue_indices(data: Dict, csv_row: Dict) -> Optional[Dict]:
    """
    Map a CSV clue_leak row to hw_idx/clue_idx by matching hidden_word and clue_text.

    Returns a dict compatible with the old detect_leaks format, or None if not found.
    """
    hidden_word = csv_row["hidden_word"]
    clue_text = csv_row["clue_text"]

    for hw_idx, hw in enumerate(data.get("hiddenWords", [])):
        if hw["word"].lower() != hidden_word.lower():
            continue
        for clue_idx, clue_obj in enumerate(hw.get("clues", [])):
            if clue_obj.get("clue", "") == clue_text:
                return {
                    "hw_idx": hw_idx,
                    "clue_idx": clue_idx,
                    "hidden_word": hidden_word,
                    "leaked_word": csv_row["leaked_word"],
                    "clue_type": csv_row["clue_type"],
                }
    return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_puzzle(nlp, provider: LLMProvider, filepath: Path, data: Dict,
                   fix_type: str, dry_run: bool,
                   clue_leaks: List[Dict] = None,
                   title_spoiled: List[str] = None) -> Tuple[int, int]:
    """
    Process a single puzzle file.

    clue_leaks: pre-resolved leak dicts (hw_idx, clue_idx, hidden_word, leaked_word, clue_type)
    title_spoiled: list of hidden words that appear in the title

    Returns (clue_fixes, title_fixes) counts.
    """
    mmdd = filepath.stem
    title = data.get("title", "")

    if clue_leaks is None:
        clue_leaks = []
    if title_spoiled is None:
        title_spoiled = []

    if not clue_leaks and not title_spoiled:
        return 0, 0

    clue_fixes = 0
    title_fixes = 0
    modified = False

    # Fix clue leaks
    if fix_type in ("clue", "both") and clue_leaks:
        for leak in clue_leaks:
            hw_idx = leak["hw_idx"]
            clue_idx = leak["clue_idx"]
            hw_obj = data["hiddenWords"][hw_idx]
            old_clue = hw_obj["clues"][clue_idx]["clue"]

            if dry_run:
                print(f"    [DRY-RUN] Would fix clue leak: '{leak['hidden_word']}' "
                      f"({leak['clue_type']}) leaks '{leak['leaked_word']}'")
                clue_fixes += 1
                continue

            print(f"    Fixing clue leak: '{leak['hidden_word']}' "
                  f"({leak['clue_type']}) leaks '{leak['leaked_word']}'")

            try:
                new_clue = fix_clue_leak(
                    nlp, provider, data, hw_obj, clue_idx, leak["leaked_word"]
                )
                if new_clue:
                    hw_obj["clues"][clue_idx] = new_clue
                    modified = True
                    clue_fixes += 1
                    _log_fix(mmdd, title, "clue_leak", leak["hidden_word"],
                             "re-clue", f"'{old_clue}' -> '{new_clue['clue']}'", "success")
                    print(f"      Fixed: '{new_clue['clue'][:60]}...'")
                else:
                    _log_fix(mmdd, title, "clue_leak", leak["hidden_word"],
                             "re-clue", f"Failed to generate replacement", "failed")
                    print(f"      FAILED to generate replacement")
            except Exception as e:
                _log_fix(mmdd, title, "clue_leak", leak["hidden_word"],
                         "re-clue", str(e), "error")
                raise

    # Fix title spoilers
    if fix_type in ("title", "both") and title_spoiled:
        for spoiled_word in title_spoiled:
            if dry_run:
                print(f"    [DRY-RUN] Would fix title spoiler: '{spoiled_word}'")
                title_fixes += 1
                continue

            print(f"    Fixing title spoiler: '{spoiled_word}'")

            try:
                result = fix_title_spoiler(nlp, provider, data, spoiled_word)
                if result:
                    # Replace the hidden word object in the puzzle
                    for i, hw in enumerate(data["hiddenWords"]):
                        if hw["word"].lower() == spoiled_word.lower():
                            data["hiddenWords"][i] = result["new_hw_obj"]

                            # Update related_words in other hidden words
                            for other_hw in data["hiddenWords"]:
                                if spoiled_word.lower() in [r.lower() for r in other_hw.get("related_words", [])]:
                                    other_hw["related_words"] = [
                                        r for r in other_hw["related_words"]
                                        if r.lower() != spoiled_word.lower()
                                    ]
                            break

                    modified = True
                    title_fixes += 1
                    _log_fix(mmdd, title, "title_spoiler", spoiled_word,
                             "word_swap", f"'{spoiled_word}' -> '{result['new_word']}'",
                             "success")
                    print(f"      Swapped: '{spoiled_word}' -> '{result['new_word']}'")
                else:
                    _log_fix(mmdd, title, "title_spoiler", spoiled_word,
                             "word_swap", "No valid replacement found", "failed")
                    print(f"      FAILED to find replacement")
            except Exception as e:
                _log_fix(mmdd, title, "title_spoiler", spoiled_word,
                         "word_swap", str(e), "error")
                raise

    # Write modified file
    if modified and not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"    Saved: {filepath.name}")

    return clue_fixes, title_fixes


def _direct_scan_and_fix(args, nlp, provider):
    """--file mode: scan specified files directly and fix (no CSV needed)."""
    from score_paragraphs import _FALSE_PREFIX_ROOTS, _shared_prefix_len

    puzzles = []
    for fp in args.file:
        path = Path(fp)
        if not path.is_absolute():
            path = Path.cwd() / path
        with open(path, encoding="utf-8") as f:
            puzzles.append((path, json.load(f)))

    print(f"Loaded {len(puzzles)} file(s) (direct scan mode)")

    progress = _load_progress()
    total_clue_fixes = 0
    total_title_fixes = 0

    for i, (filepath, data) in enumerate(puzzles, 1):
        mmdd = filepath.stem
        title = data.get("title", "")

        # Scan this file for leaks inline
        clue_leaks, title_spoiled = _scan_puzzle(nlp, data)

        has_clue = len(clue_leaks) > 0 and args.fix_type in ("clue", "both")
        has_title = len(title_spoiled) > 0 and args.fix_type in ("title", "both")
        if not has_clue and not has_title:
            print(f"[{i}/{len(puzzles)}] {mmdd} — no leaks")
            continue

        cl_count = len(clue_leaks) if has_clue else 0
        tl_count = len(title_spoiled) if has_title else 0
        print(f"\n[{i}/{len(puzzles)}] {mmdd} ({title}) "
              f"— {cl_count} clue leaks, {tl_count} title spoilers")

        try:
            cf, tf = process_puzzle(nlp, provider, filepath, data,
                                    args.fix_type, args.dry_run,
                                    clue_leaks if has_clue else [],
                                    title_spoiled if has_title else [])
            total_clue_fixes += cf
            total_title_fixes += tf
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\n--- Fix Summary ---")
    print(f"Clue leaks fixed:    {total_clue_fixes}")
    print(f"Title spoilers fixed: {total_title_fixes}")


def _scan_puzzle(nlp, data: Dict) -> Tuple[List[Dict], List[str]]:
    """
    Scan a single puzzle for leaks (used by --file direct mode only).

    Returns (clue_leaks, title_spoiled_words) in the format process_puzzle expects.
    """
    clue_leaks = []
    title_spoiled = []

    title = data.get("title", "")
    title_words = set(title.lower().split())

    for hw_idx, hw in enumerate(data.get("hiddenWords", [])):
        word = hw["word"]
        word_lower = word.lower()

        # Title spoiler check (exact match)
        if word_lower in title_words:
            title_spoiled.append(word)
            continue

        # Title spoiler check (stemming)
        hw_lemma = _get_lemma(nlp, word_lower)
        for tw in title_words:
            if len(tw) >= 4 and _get_lemma(nlp, tw) == hw_lemma:
                title_spoiled.append(word)
                break

        # Clue leak check
        for clue_idx, clue_obj in enumerate(hw.get("clues", [])):
            clue_text = clue_obj.get("clue", "")
            leaked_word = _clue_word_leaks(nlp, word, clue_text)
            if leaked_word:
                clue_leaks.append({
                    "hw_idx": hw_idx,
                    "clue_idx": clue_idx,
                    "hidden_word": word,
                    "leaked_word": leaked_word,
                    "clue_type": clue_obj.get("type", ""),
                })

    return clue_leaks, title_spoiled


def main():
    parser = argparse.ArgumentParser(
        description="Fix clue leaks and title spoilers in ClueChain puzzles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--fix-type", choices=["clue", "title", "both"], default="both",
                        help="What to fix (default: both)")
    parser.add_argument("--batch-size", type=int, default=0,
                        help="Max puzzles to fix (0 = all)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between API calls in seconds (default: 5.0)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying files or calling API")
    parser.add_argument("--start-from", type=str, default=None,
                        help="Start from this MMDD (skip earlier puzzles)")
    parser.add_argument("--file", nargs="+", default=None,
                        help="Fix specific files (scans directly, no CSV needed)")
    parser.add_argument("--provider", choices=["groq", "nim"], default=None,
                        help="Force a specific LLM provider (default: groq first, nim fallback)")
    parser.add_argument("--force", action="store_true",
                        help="Skip staleness check on leak_audit.csv")
    args = parser.parse_args()

    load_dotenv()
    nlp = _load_spacy_model()

    # Set up LLM provider (skip in dry-run)
    provider = None
    if not args.dry_run:
        provider = _build_provider(force=args.provider)

    # --file mode: direct scan, no CSV dependency
    if args.file:
        _direct_scan_and_fix(args, nlp, provider)
        return

    # CSV mode: require leak_audit.csv
    if not _AUDIT_CSV.exists():
        print(f"Error: {_AUDIT_CSV} not found.")
        print("Run audit_leaks.py first to generate leak_audit.csv")
        sys.exit(1)

    # Staleness check: warn if CSV is older than any puzzle file
    if not args.force:
        csv_mtime = _AUDIT_CSV.stat().st_mtime
        newest_puzzle = max(
            (p.stat().st_mtime for p in _MMDD_DIR.glob("*.json")),
            default=0,
        )
        if newest_puzzle > csv_mtime:
            print(f"Warning: leak_audit.csv is older than some puzzle files.")
            print("Run audit_leaks.py to refresh, or use --force to proceed anyway.")
            sys.exit(1)

    # Load leaks from CSV grouped by mmdd
    leak_groups = _load_leaks_from_csv(args.fix_type, start_from=args.start_from)

    # Load progress to skip already-completed puzzles
    progress = _load_progress()
    completed = set(progress.get("completed", []))

    # Remove already-completed mmdds
    for mmdd in list(leak_groups.keys()):
        if mmdd in completed:
            del leak_groups[mmdd]

    if not leak_groups:
        print("Nothing to fix! (all leaky puzzles already completed or none found in CSV)")
        return

    # Sort by mmdd, then load puzzle files
    sorted_mmdds = sorted(leak_groups.keys())

    # Build work list: load puzzle data and resolve CSV rows to indices
    work_list = []
    for mmdd in sorted_mmdds:
        filepath = _MMDD_DIR / f"{mmdd}.json"
        if not filepath.exists():
            print(f"Warning: {filepath} not found, skipping")
            continue

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        group = leak_groups[mmdd]

        # Resolve clue leak CSV rows to hw_idx/clue_idx
        clue_leaks = []
        for row in group["clue_leaks"]:
            resolved = _resolve_clue_indices(data, row)
            if resolved:
                clue_leaks.append(resolved)
            else:
                print(f"Warning: could not resolve clue leak in {mmdd} "
                      f"for '{row['hidden_word']}' — clue may have changed")

        # Collect title spoiler words
        title_spoiled = [row["hidden_word"] for row in group["title_spoilers"]]

        cl_count = len(clue_leaks)
        tl_count = len(title_spoiled)
        work_list.append((filepath, data, clue_leaks, title_spoiled, cl_count, tl_count))

    # Sort by total leaks (worst first)
    work_list.sort(key=lambda x: -(x[4] + x[5]))

    if args.batch_size > 0:
        work_list = work_list[:args.batch_size]

    print(f"Puzzles to fix: {len(work_list)} (from leak_audit.csv)")
    if not work_list:
        print("Nothing to fix!")
        return

    total_clue_fixes = 0
    total_title_fixes = 0

    for i, (filepath, data, clue_leaks, title_spoiled, cl_count, tl_count) in enumerate(work_list, 1):
        mmdd = filepath.stem

        print(f"\n[{i}/{len(work_list)}] {mmdd} ({data.get('title', '')}) "
              f"— {cl_count} clue leaks, {tl_count} title spoilers")

        try:
            cf, tf = process_puzzle(nlp, provider, filepath, data,
                                    args.fix_type, args.dry_run,
                                    clue_leaks, title_spoiled)
            total_clue_fixes += cf
            total_title_fixes += tf

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

    print(f"\n--- Fix Summary ---")
    print(f"Clue leaks fixed:    {total_clue_fixes}")
    print(f"Title spoilers fixed: {total_title_fixes}")
    if not args.dry_run:
        print(f"Fix log: {_FIX_LOG_CSV}")
        print(f"Progress: {_PROGRESS_FILE}")


if __name__ == "__main__":
    main()
