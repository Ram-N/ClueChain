#!/usr/bin/env python3
"""
Show scores for a puzzle file.

Usage:
    python scripts/show_score.py 07-04.json
    python scripts/show_score.py tale          # partial match
    python scripts/show_score.py 0527          # mmdd match
"""

import json
import sys
from pathlib import Path

SCORES_FILE = Path(__file__).parent / "output" / "paragraph_scores.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/show_score.py <filename or search term>")
        sys.exit(1)

    query = sys.argv[1]
    scores = json.load(open(SCORES_FILE))

    # Exact match first
    if query in scores:
        matches = {query: scores[query]}
    else:
        # Partial match (case-insensitive)
        q = query.lower()
        matches = {k: v for k, v in scores.items() if q in k.lower() or q in v.get("title", "").lower()}

    if not matches:
        print(f"No match for '{query}'")
        sys.exit(1)

    for filename, entry in matches.items():
        print(f"\n  {filename}")
        print(f"  {entry.get('title', '')}")
        print(f"  Date: {entry.get('date', '?')}    Score: {entry.get('total_score', '?')}/100    Rating: {entry.get('overall_rating', '?')}")
        print()
        s = entry.get("scores", {})
        for dim in ("word_quality", "variety", "connectivity", "clueability", "discovery_curve", "narrative_interest", "catalog_penalty"):
            val = s.get(dim)
            if val is not None:
                label = dim.replace("_", " ").title()
                print(f"    {label:<22} {val}")
        reasons = entry.get("reasons", {})
        if reasons:
            print()
            for dim, reason in reasons.items():
                label = dim.replace("_", " ").title()
                print(f"    {label}: {reason}")
        print()


if __name__ == "__main__":
    main()
