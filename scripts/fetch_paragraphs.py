#!/usr/bin/env python3
"""
fetch_paragraphs.py — Wikipedia-based paragraph fetcher for ClueChain

Fetches N copyright-free paragraphs on a given topic from Wikipedia,
scores them for interestingness, and writes a numbered-delimiter library
file ready for batch_generate_cluechain_json.py.

Usage:
    python scripts/fetch_paragraphs.py --topic "philosophy" --count 12
    python scripts/fetch_paragraphs.py --topic "maps" --count 12 --output assets/data/library/maps.txt
    python scripts/fetch_paragraphs.py --topic "civics" --count 6 --dry-run

Dependencies (pip install):
    wikipediaapi wikipedia textstat spacy vaderSentiment
    python -m spacy download en_core_web_sm
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    article_title: str
    section: str
    text: str
    score: float = 0.0
    word_count: int = 0
    fk_score: float = 0.0
    ne_density: float = 0.0
    lex_diversity: float = 0.0


# ---------------------------------------------------------------------------
# Lazy imports (give helpful errors if deps missing)
# ---------------------------------------------------------------------------

def _import_deps():
    missing = []
    mods = {}

    try:
        import wikipediaapi
        mods["wikipediaapi"] = wikipediaapi
    except ImportError:
        missing.append("wikipediaapi")

    try:
        import wikipedia
        mods["wikipedia"] = wikipedia
    except ImportError:
        missing.append("wikipedia")

    try:
        import textstat
        mods["textstat"] = textstat
    except ImportError:
        missing.append("textstat")

    try:
        import spacy
        mods["spacy"] = spacy
    except ImportError:
        missing.append("spacy")

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        mods["vader"] = SentimentIntensityAnalyzer
    except ImportError:
        missing.append("vaderSentiment")

    if missing:
        print("Missing dependencies. Install with:")
        print(f"  pip install {' '.join(missing)}")
        if "spacy" not in missing:
            print("  python -m spacy download en_core_web_sm")
        sys.exit(1)

    return mods


# ---------------------------------------------------------------------------
# Wikipedia fetching
# ---------------------------------------------------------------------------

def _make_wiki(mods):
    """Create a wikipediaapi Wiki object with a descriptive user-agent."""
    wiki = mods["wikipediaapi"].Wikipedia(
        language="en",
        user_agent="ClueChain-ParagraphFetcher/1.0 (contact: cluechain-dev)"
    )
    return wiki


def _extract_paragraphs_from_sections(page, min_chars: int, max_chars: int, max_words: Optional[int]) -> List[Tuple[str, str, str]]:
    """
    Recursively walk page sections and extract (article_title, section_title, text) tuples.
    Filters by char length, optional word count, and skips section-header-like lines.
    """
    results = []
    citation_re = re.compile(r'\[\d+\]')

    # Section titles that are purely navigational / reference noise
    _SKIP_SECTIONS = {
        "references", "external links", "bibliography", "further reading",
        "see also", "notes", "citations", "sources", "footnotes",
    }

    # Patterns that indicate citation/reference dumps
    _CITATION_PATTERNS = re.compile(
        r'ISBN\s[\d\-X]+|doi:\S+|S2CID\s\d+|\(\d{4}\)\.'
    )

    def _clean(text: str) -> str:
        text = citation_re.sub('', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _looks_like_header(para: str) -> bool:
        """Skip short lines without sentence-ending punctuation."""
        if len(para) < 80:
            return True
        if not any(c in para for c in '.!?'):
            return True
        return False

    def _looks_like_citation_dump(para: str) -> bool:
        """Reject paragraphs that are reference lists or citation noise."""
        return bool(_CITATION_PATTERNS.search(para))

    def _passes_filters(para: str) -> bool:
        if _looks_like_header(para):
            return False
        if _looks_like_citation_dump(para):
            return False
        if not (min_chars <= len(para) <= max_chars):
            return False
        if max_words is not None and len(para.split()) > max_words:
            return False
        return True

    def _walk(section, depth=0):
        raw = section.text.strip() if depth > 0 else ""
        title_part = section.title if depth > 0 else page.title

        # Skip navigational / reference sections by title
        if depth > 0 and title_part.strip().lower() in _SKIP_SECTIONS:
            return

        if raw:
            for para in raw.split('\n\n'):
                para = _clean(para)
                if _passes_filters(para):
                    results.append((page.title, title_part, para))

        for subsection in section.sections:
            _walk(subsection, depth + 1)

    # Walk top-level text (summary)
    summary = _clean(page.summary)
    if _passes_filters(summary):
        results.append((page.title, "Overview", summary))

    for section in page.sections:
        _walk(section, depth=1)

    return results


def _fetch_candidates(topic: str, count: int, min_chars: int, max_chars: int, max_words: Optional[int], mods) -> List[Tuple[str, str, str]]:
    """
    Fetch (article_title, section, paragraph_text) tuples from Wikipedia.
    Pulls from primary article first; searches related articles if needed.
    Returns up to 3× count candidates.
    """
    wiki = _make_wiki(mods)
    target = count * 3
    candidates = []
    visited_titles = set()

    def _add_from_page(title: str):
        if title in visited_titles:
            return
        visited_titles.add(title)
        page = wiki.page(title)
        if not page.exists():
            return
        # Skip disambiguation pages (they have very short text)
        if len(page.summary) < 200:
            return
        extracted = _extract_paragraphs_from_sections(page, min_chars, max_chars, max_words)
        candidates.extend(extracted)

    # 1) Try exact match
    _add_from_page(topic)

    # 2) If still short, search for related articles
    if len(candidates) < target:
        try:
            search_results = mods["wikipedia"].search(topic, results=10)
            for title in search_results:
                if len(candidates) >= target:
                    break
                _add_from_page(title)
        except Exception:
            pass  # network hiccup — use what we have

    return candidates


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _load_nlp(mods):
    """Load spaCy model; give a helpful error if the model isn't downloaded."""
    try:
        return mods["spacy"].load("en_core_web_sm")
    except OSError:
        print("spaCy model not found. Run:")
        print("  python -m spacy download en_core_web_sm")
        sys.exit(1)


def _score_candidate(text: str, topic_words: List[str], nlp, vader, mods) -> Tuple[float, int, float, float, float]:
    """
    Return (score_0_100, word_count, fk_ease, ne_density, lex_diversity).
    """
    words = text.split()
    word_count = len(words)

    # --- Word count score (peaks at 125 words) ---
    wc_score = max(0.0, 1.0 - abs(word_count - 125) / 75.0)
    wc_score = min(1.0, wc_score)

    # --- Flesch reading ease (target 50-70) ---
    fk_ease = mods["textstat"].flesch_reading_ease(text)
    # Normalise: 50-70 → 1.0, drops off outside that band
    if 50 <= fk_ease <= 70:
        fk_norm = 1.0
    elif fk_ease < 50:
        fk_norm = max(0.0, (fk_ease - 20) / 30.0)
    else:
        fk_norm = max(0.0, (100 - fk_ease) / 30.0)

    # --- Named entity density ---
    doc = nlp(text[:1000])  # limit for speed
    ne_density = len(doc.ents) / max(1, word_count)
    # Target density 0.04-0.12; normalise to 0-1
    ne_norm = min(1.0, ne_density / 0.10)

    # --- Lexical diversity ---
    lower_words = [w.lower() for w in words]
    lex_diversity = len(set(lower_words)) / max(1, len(lower_words))
    # Higher is better; normalise (floor at 0.5, ceiling at 0.9)
    lex_norm = min(1.0, max(0.0, (lex_diversity - 0.4) / 0.4))

    # --- Sentence variety (std dev of sentence lengths) ---
    sentences = re.split(r'[.!?]+', text)
    sent_lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(sent_lengths) > 1:
        mean_len = sum(sent_lengths) / len(sent_lengths)
        variance = sum((x - mean_len) ** 2 for x in sent_lengths) / len(sent_lengths)
        std_dev = variance ** 0.5
    else:
        std_dev = 0.0
    # Target std_dev ≥ 5; cap at 15
    sent_norm = min(1.0, std_dev / 15.0)

    # --- Topic relevance ---
    text_lower = text.lower()
    topic_hits = sum(text_lower.count(w.lower()) for w in topic_words)
    relevance = topic_hits / max(1, word_count / 100)
    rel_norm = min(1.0, relevance / 3.0)

    # --- Sentiment strength ---
    vader_scores = vader.polarity_scores(text)
    sentiment_norm = abs(vader_scores["compound"])

    # Weighted sum
    score = (
        0.20 * wc_score
        + 0.20 * fk_norm
        + 0.20 * ne_norm
        + 0.15 * lex_norm
        + 0.10 * sent_norm
        + 0.10 * rel_norm
        + 0.05 * sentiment_norm
    ) * 100

    return score, word_count, fk_ease, ne_density, lex_diversity


def score_candidates(
    raw: List[Tuple[str, str, str]],
    topic: str,
    min_score: float,
    mods,
) -> List[Candidate]:
    """Score all candidates, filter by min_score, return sorted list."""
    nlp = _load_nlp(mods)
    vader = mods["vader"]()
    topic_words = re.split(r'[\s,]+', topic)

    scored = []
    for art_title, section, text in raw:
        s, wc, fk, ne, lex = _score_candidate(text, topic_words, nlp, vader, mods)
        if s >= min_score:
            scored.append(Candidate(
                article_title=art_title,
                section=section,
                text=text,
                score=s,
                word_count=wc,
                fk_score=fk,
                ne_density=ne,
                lex_diversity=lex,
            ))

    # Deduplicate by text prefix (first 80 chars)
    seen = set()
    deduped = []
    for c in scored:
        key = c.text[:80]
        if key not in seen:
            seen.add(key)
            deduped.append(c)

    deduped.sort(key=lambda c: c.score, reverse=True)
    return deduped


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _topic_slug(topic: str) -> str:
    slug = topic.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug.strip('-')


def format_library_file(candidates: List[Candidate]) -> str:
    """Format candidates as a numbered-delimiter library file."""
    lines = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}.")
        lines.append(f"Title: {c.article_title} — {c.section}")
        lines.append("")
        lines.append(c.text)
        lines.append("")
    return '\n'.join(lines)


def print_preview_table(candidates: List[Candidate]):
    """Print a ranked preview table to stdout."""
    print(f"\n{'#':>3}  {'Score':>5}  {'Words':>5}  {'FK':>5}  {'NE':>5}  Title")
    print("─" * 80)
    for i, c in enumerate(candidates, 1):
        title = f"{c.article_title} — {c.section}"
        if len(title) > 40:
            title = title[:37] + "..."
        print(
            f"{i:>3}  {c.score:>5.1f}  {c.word_count:>5}  "
            f"{c.fk_score:>5.1f}  {c.ne_density:>5.3f}  {title}"
        )
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Fetch Wikipedia paragraphs for a ClueChain library file."
    )
    p.add_argument("--topic", required=True, help='Search topic, e.g. "philosophy"')
    p.add_argument("--count", type=int, default=12, help="Number of paragraphs to fetch (default: 12)")
    p.add_argument("--output", help="Output file path (default: assets/data/library/{slug}.txt)")
    p.add_argument("--min-chars", type=int, default=500, dest="min_chars", help="Min paragraph length in characters (default: 500)")
    p.add_argument("--max-chars", type=int, default=1300, dest="max_chars", help="Max paragraph length in characters (default: 1300)")
    p.add_argument("--max-words", type=int, default=150, dest="max_words", help="Max paragraph length in words (default: 150)")
    p.add_argument("--min-score", type=float, default=40.0, dest="min_score", help="Discard paragraphs below this score (default: 40)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="Print output to stdout, do not write file")
    p.add_argument("--append", action="store_true", help="Append new paragraphs to existing file instead of overwriting")
    return p.parse_args()


def main():
    args = parse_args()
    mods = _import_deps()

    topic = args.topic
    count = args.count

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        slug = _topic_slug(topic)
        out_path = Path("assets/data/library") / f"{slug}.txt"

    print(f"Topic     : {topic}")
    print(f"Count     : {count}")
    print(f"Char range: {args.min_chars}–{args.max_chars}")
    print(f"Max words : {args.max_words}")
    print(f"Min score : {args.min_score}")
    if args.append:
        print(f"Mode      : append")
    if not args.dry_run:
        print(f"Output    : {out_path}")
    print()

    # Load existing paragraphs for deduplication (append mode)
    existing_prefixes: set = set()
    existing_count = 0
    if args.append and out_path.exists():
        existing_text = out_path.read_text(encoding="utf-8")
        # Each paragraph block starts after a blank line following the Title: line
        for block in existing_text.split('\n\n'):
            block = block.strip()
            if block and not block.startswith(('Title:', '\n')) and not re.match(r'^\d+\.$', block):
                existing_prefixes.add(block[:80])
                existing_count += 1
        print(f"Existing file has ~{existing_count} paragraphs — will deduplicate against them.")

    # Fetch (fetch extra to account for dedup losses in append mode)
    fetch_count = count * 4 if args.append else count * 3
    print("Fetching paragraphs from Wikipedia...")
    raw = _fetch_candidates(topic, fetch_count, args.min_chars, args.max_chars, args.max_words, mods)
    print(f"  Found {len(raw)} raw candidates")

    if not raw:
        print("ERROR: No paragraphs found. Try a different topic or broaden --min-chars/--max-chars.")
        sys.exit(1)

    # Score
    print("Scoring candidates...")
    scored = score_candidates(raw, topic, args.min_score, mods)
    print(f"  {len(scored)} candidates passed min-score filter")

    # In append mode, remove any candidate already in the existing file
    if args.append and existing_prefixes:
        scored = [c for c in scored if c.text[:80] not in existing_prefixes]
        print(f"  {len(scored)} candidates after deduplication against existing file")

    if len(scored) < count:
        print(f"WARNING: Only {len(scored)} paragraphs available (requested {count}).")
        print("  Try lowering --min-score or broadening char range.")

    selected = scored[:count]
    print(f"  Selected top {len(selected)}")

    # Preview
    print_preview_table(selected)

    if not selected:
        print("No paragraphs to write.")
        sys.exit(1)

    # Output
    content = format_library_file(selected)

    if args.dry_run:
        print("─" * 80)
        print(content)
    elif args.append:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as f:
            f.write("\n" + content)
        print(f"Appended {len(selected)} paragraph(s) to {out_path}")
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"Written: {out_path}  ({len(selected)} paragraphs)")


if __name__ == "__main__":
    main()
