#!/usr/bin/env python3
"""
Model Test — ClueChain LLM Benchmark

Tests one or more OpenRouter models against a single paragraph and scores
the output using the existing json_validator + quality heuristics.

Usage:
    # Test the model currently set in model-config.json
    uv run python scripts/model_test.py --file /tmp/my_para.txt

    # Test specific models (comma-separated OpenRouter IDs)
    uv run python scripts/model_test.py --file /tmp/my_para.txt \\
        --models "google/gemini-2.0-flash-lite-001,meta-llama/llama-3.3-70b-instruct:free"

    # Also test Groq as baseline
    uv run python scripts/model_test.py --file /tmp/my_para.txt --include-groq

    # Change delay between calls (default: 6s)
    uv run python scripts/model_test.py --file /tmp/my_para.txt --delay 10

Paragraph file format (same as generate_cluechain_json.py):
    Title: Some Title Here

    Paragraph text goes here...

Output:
    A scored comparison table. Results saved to /tmp/model_test_results/.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPTS_DIR   = Path(__file__).parent
PROJECT_ROOT  = SCRIPTS_DIR.parent
GENERATOR     = SCRIPTS_DIR / "generate_cluechain_json.py"
VALIDATOR     = PROJECT_ROOT / "assets" / "data" / "json_validator.py"
MODEL_CONFIG  = SCRIPTS_DIR / "model-config.json"

DIFFICULTY_LEVELS = ["Easy", "Intermediate", "Medium", "Hard"]
IDEAL_DIST = {"Easy": 3, "Intermediate": 4, "Hard": 3}  # target spread


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def score_output(data: dict) -> dict:
    """
    Score a generated JSON on quality heuristics (0–100).

    Breakdown:
      30 pts  Difficulty spread  — how close to 3/4/3 Easy/Int/Hard
      25 pts  Clue length        — avg chars per clue (target ≥ 60)
      20 pts  Related words      — fraction of words that have ≥ 2 related_words
      15 pts  No giveaway clues  — penalise very short clues (< 20 chars)
      10 pts  Word variety       — no duplicate words (validator catches this,
                                   but we reward uniqueness positively)
    """
    hw = data.get("hiddenWords", [])
    if not hw:
        return {"total": 0, "breakdown": {}, "notes": ["No hiddenWords found"]}

    notes = []

    # 1. Difficulty spread (30 pts)
    counts = {}
    for w in hw:
        d = w.get("difficulty", "")
        counts[d] = counts.get(d, 0) + 1

    spread_score = 30
    for level, target in IDEAL_DIST.items():
        actual = counts.get(level, 0)
        # Deduct 3 pts per word off-target, max 10 pts per level
        spread_score -= min(10, abs(actual - target) * 3)
    spread_score = max(0, spread_score)
    notes.append(f"Difficulty dist: {counts}")

    # 2. Clue length (25 pts)
    all_clues = [c["clue"] for w in hw for c in w.get("clues", []) if "clue" in c]
    if all_clues:
        avg_len = sum(len(c) for c in all_clues) / len(all_clues)
        # 25 pts at avg ≥ 80 chars, scales down linearly to 0 at avg = 20
        clue_len_score = min(25, max(0, int((avg_len - 20) / 60 * 25)))
        notes.append(f"Avg clue length: {avg_len:.0f} chars")
    else:
        clue_len_score = 0

    # 3. Related words coverage (20 pts)
    well_related = sum(1 for w in hw if len(w.get("related_words", [])) >= 2)
    related_score = int(well_related / len(hw) * 20)
    notes.append(f"Words with ≥2 related: {well_related}/{len(hw)}")

    # 4. No giveaway clues — short clues < 20 chars (15 pts)
    short_clues = [c for c in all_clues if len(c) < 20]
    giveaway_score = max(0, 15 - len(short_clues) * 3)
    if short_clues:
        notes.append(f"Short clues (< 20 chars): {len(short_clues)}")

    # 5. Word uniqueness (10 pts)
    words = [w.get("word", "").lower() for w in hw]
    unique_score = 10 if len(words) == len(set(words)) else 5
    if len(words) != len(set(words)):
        notes.append("Duplicate words detected")

    total = spread_score + clue_len_score + related_score + giveaway_score + unique_score
    return {
        "total": total,
        "breakdown": {
            "difficulty_spread": spread_score,
            "clue_length":       clue_len_score,
            "related_words":     related_score,
            "no_giveaways":      giveaway_score,
            "word_uniqueness":   unique_score,
        },
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Run generator for one model
# ---------------------------------------------------------------------------

def run_model(para_file: str, model_id: str, backend: str,
              out_dir: Path, delay: float) -> dict:
    """
    Call generate_cluechain_json.py for one model.
    Returns a result dict with keys: model, backend, output_file, elapsed,
    validator_errors, quality, error.
    """
    result = {"model": model_id, "backend": backend, "output_file": None,
              "elapsed": None, "validator_errors": [], "quality": None, "error": None}

    # Temporarily patch model-config.json if testing a specific openrouter model
    original_config = None
    if backend == "openrouter":
        with open(MODEL_CONFIG) as f:
            original_config = f.read()
        cfg = json.loads(original_config)
        cfg["openrouter_model"] = model_id
        with open(MODEL_CONFIG, "w") as f:
            json.dump(cfg, f, indent=2)

    try:
        t0 = time.time()
        proc = subprocess.run(
            ["uv", "run", "python", str(GENERATOR),
             "--file",   para_file,
             "--date",   "99-99",       # sentinel date — won't affect content
             "--model",  backend,
             "--output", str(out_dir)],
            capture_output=True, text=True, timeout=120
        )
        result["elapsed"] = round(time.time() - t0, 1)

        if proc.returncode != 0:
            result["error"] = (proc.stderr or proc.stdout).strip()[-300:]
            return result

        # Find the output file
        candidates = list(out_dir.glob("99-99_*.json"))
        if not candidates:
            result["error"] = "No output file found"
            return result

        out_file = candidates[-1]  # most recent
        result["output_file"] = out_file.name

        # Rename to avoid collision on next run
        safe_name = re.sub(r'[^a-z0-9]', '_', model_id.lower())[:30]
        dest = out_dir / f"99-99_{safe_name}.json"
        out_file.rename(dest)
        result["output_file"] = dest.name

        # Validate
        val = subprocess.run(
            ["uv", "run", "python", str(VALIDATOR), str(dest)],
            capture_output=True, text=True
        )
        val_output = val.stdout + val.stderr
        errors = [ln for ln in val_output.splitlines() if ln.startswith("- ")]
        result["validator_errors"] = errors

        # Quality score
        with open(dest) as f:
            data = json.load(f)
        result["quality"] = score_output(data)

    except subprocess.TimeoutExpired:
        result["error"] = "Timed out after 120s"
    except Exception as e:
        result["error"] = str(e)
    finally:
        # Restore model-config.json
        if original_config is not None:
            with open(MODEL_CONFIG, "w") as f:
                f.write(original_config)

    return result


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_results(results: list):
    sep = "═" * 70
    print(f"\n{sep}")
    print("  MODEL TEST RESULTS")
    print(sep)

    for r in results:
        label = r["model"] if r["backend"] == "openrouter" else f"groq ({r['model']})"
        print(f"\n▶ {label}")
        print(f"  Backend : {r['backend']}")

        if r["error"]:
            print(f"  ❌ FAILED: {r['error']}")
            continue

        elapsed = r["elapsed"]
        val_errors = r["validator_errors"]
        q = r["quality"]

        val_status = "✅ PASS" if not val_errors else f"❌ FAIL ({len(val_errors)} errors)"
        print(f"  Validation : {val_status}")
        if val_errors:
            for e in val_errors[:5]:
                print(f"    {e}")
            if len(val_errors) > 5:
                print(f"    ... and {len(val_errors) - 5} more")

        if q:
            print(f"  Quality    : {q['total']}/100")
            bd = q["breakdown"]
            print(f"    Difficulty spread : {bd['difficulty_spread']}/30")
            print(f"    Clue length       : {bd['clue_length']}/25")
            print(f"    Related words     : {bd['related_words']}/20")
            print(f"    No giveaways      : {bd['no_giveaways']}/15")
            print(f"    Word uniqueness   : {bd['word_uniqueness']}/10")
            for note in q["notes"]:
                print(f"    → {note}")

        print(f"  Time       : {elapsed}s")

    # Summary table
    print(f"\n{sep}")
    print("  SUMMARY")
    print(sep)
    print(f"  {'Model':<42} {'Valid':>6}  {'Quality':>8}  {'Time':>6}")
    print(f"  {'-'*42} {'-'*6}  {'-'*8}  {'-'*6}")
    for r in sorted(results, key=lambda x: (x["quality"] or {}).get("total", -1), reverse=True):
        label = (r["model"] if r["backend"] == "openrouter" else f"groq")[:42]
        if r["error"]:
            print(f"  {label:<42} {'ERROR':>6}  {'—':>8}  {'—':>6}")
        else:
            valid = "PASS" if not r["validator_errors"] else "FAIL"
            score = str(r["quality"]["total"]) if r["quality"] else "—"
            print(f"  {label:<42} {valid:>6}  {score:>8}  {r['elapsed']:>5}s")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Test ClueChain LLM models on a single paragraph"
    )
    parser.add_argument("--file", required=True,
                        help="Path to paragraph text file (Title: ... + body)")
    parser.add_argument("--models",
                        help="Comma-separated OpenRouter model IDs to test. "
                             "Defaults to the model in model-config.json.")
    parser.add_argument("--include-groq", action="store_true",
                        help="Also test Groq (llama-3.3-70b-versatile) as baseline")
    parser.add_argument("--delay", type=float, default=6.0,
                        help="Seconds between API calls (default: 6)")
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    # Determine models to test
    openrouter_models = []
    if args.models:
        openrouter_models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        # Default: use whatever is in model-config.json
        with open(MODEL_CONFIG) as f:
            cfg = json.load(f)
        openrouter_models = [cfg["openrouter_model"]]

    jobs = [{"model": m, "backend": "openrouter"} for m in openrouter_models]
    if args.include_groq:
        jobs.append({"model": "llama-3.3-70b-versatile", "backend": "groq"})

    out_dir = Path(tempfile.mkdtemp(prefix="model_test_"))
    print(f"\nOutput dir: {out_dir}")
    print(f"Testing {len(jobs)} model(s) on: {args.file}\n")

    results = []
    for i, job in enumerate(jobs):
        if i > 0:
            print(f"  Waiting {args.delay}s before next call...")
            time.sleep(args.delay)
        label = job["model"] if job["backend"] == "openrouter" else f"groq/{job['model']}"
        print(f"[{i+1}/{len(jobs)}] Running {label}...")
        r = run_model(args.file, job["model"], job["backend"], out_dir, args.delay)
        results.append(r)

    print_results(results)
    print(f"Raw output files in: {out_dir}\n")


if __name__ == "__main__":
    main()
