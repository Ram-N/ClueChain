#!/usr/bin/env python3
"""
fetch_paragraphs.py — Multi-source paragraph fetcher for ClueChain

Fetches N copyright-free paragraphs on a given topic from Wikipedia,
Project Gutenberg, or The Guardian, scores them for interestingness,
and writes a numbered-delimiter library file ready for
batch_generate_cluechain_json.py.

Usage:
    # Wikipedia (default — unchanged behaviour)
    python scripts/fetch_paragraphs.py --topic "philosophy" --count 12

    # Project Gutenberg (no API key needed)
    python scripts/fetch_paragraphs.py --topic "adventure" --source gutenberg --count 10

    # The Guardian (free API key from open-platform.theguardian.com)
    python scripts/fetch_paragraphs.py --topic "science" --source guardian --guardian-key YOUR_KEY --count 10

    # Dry-run (print to stdout, no file written)
    python scripts/fetch_paragraphs.py --topic "civics" --count 6 --dry-run

Dependencies (pip install):
    wikipediaapi wikipedia textstat spacy vaderSentiment requests
    python -m spacy download en_core_web_sm
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


def _load_dotenv(env_path: Path = Path(".env")) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (if not already set)."""
    if not env_path.exists():
        return
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv()


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

def _import_deps(source: str = "wikipedia"):
    """Import dependencies appropriate for the chosen source."""
    missing = []
    mods = {}

    # Always needed for scoring
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

    # Wikipedia-specific deps
    if source == "wikipedia":
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

    # Gutenberg and Guardian both just need requests
    if source in ("gutenberg", "guardian"):
        try:
            import requests
            mods["requests"] = requests
        except ImportError:
            missing.append("requests")

    if missing:
        print("Missing dependencies. Install with:")
        print(f"  pip install {' '.join(missing)}")
        if "spacy" not in missing:
            print("  python -m spacy download en_core_web_sm")
        sys.exit(1)

    return mods


# ---------------------------------------------------------------------------
# Shared paragraph utilities
# ---------------------------------------------------------------------------

_CITATION_RE = re.compile(r'\[\d+\]')
_CITATION_PATTERNS = re.compile(
    r'ISBN\s[\d\-X]+|doi:\S+|S2CID\s\d+|\(\d{4}\)\.'
)


def _clean_text(text: str) -> str:
    text = _CITATION_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _passes_para_filters(para: str, min_chars: int, max_chars: int, max_words: Optional[int]) -> bool:
    """Return True if paragraph passes length and quality filters."""
    if len(para) < 80:
        return False
    if not any(c in para for c in '.!?'):
        return False
    if bool(_CITATION_PATTERNS.search(para)):
        return False
    if not (min_chars <= len(para) <= max_chars):
        return False
    if max_words is not None and len(para.split()) > max_words:
        return False
    return True


def _split_into_paras(text: str) -> List[str]:
    """Split a block of text into paragraph candidates."""
    # Normalize Windows line endings before splitting
    text = text.replace('\r\n', '\n')
    return [_clean_text(p) for p in text.split('\n\n') if p.strip()]


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
    """
    results = []

    _SKIP_SECTIONS = {
        "references", "external links", "bibliography", "further reading",
        "see also", "notes", "citations", "sources", "footnotes",
    }

    def _walk(section, depth=0):
        raw = section.text.strip() if depth > 0 else ""
        title_part = section.title if depth > 0 else page.title

        if depth > 0 and title_part.strip().lower() in _SKIP_SECTIONS:
            return

        if raw:
            for para in _split_into_paras(raw):
                if _passes_para_filters(para, min_chars, max_chars, max_words):
                    results.append((page.title, title_part, para))

        for subsection in section.sections:
            _walk(subsection, depth + 1)

    summary = _clean_text(page.summary)
    if _passes_para_filters(summary, min_chars, max_chars, max_words):
        results.append((page.title, "Overview", summary))

    for section in page.sections:
        _walk(section, depth=1)

    return results


def fetch_from_wikipedia(topic: str, count: int, min_chars: int, max_chars: int, max_words: Optional[int], mods) -> List[Tuple[str, str, str]]:
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
        if len(page.summary) < 200:
            return
        extracted = _extract_paragraphs_from_sections(page, min_chars, max_chars, max_words)
        candidates.extend(extracted)

    _add_from_page(topic)

    if len(candidates) < target:
        try:
            search_results = mods["wikipedia"].search(topic, results=10)
            for title in search_results:
                if len(candidates) >= target:
                    break
                _add_from_page(title)
        except Exception:
            pass

    return candidates


# ---------------------------------------------------------------------------
# Gutenberg fetching
# ---------------------------------------------------------------------------

def _gutendex_search(topic: str, requests) -> list:
    """
    Search Gutendex with progressively looser queries until we find results.

    Strategy:
    1. Try the full topic string as-is.
    2. Try each individual word in the topic (picking the most specific).
    3. Try the first word alone.

    Returns the raw results list (may be empty).
    """
    queries_to_try = _build_search_variants(topic)

    for query in queries_to_try:
        print(f"  Searching Gutendex for '{query}'...")
        try:
            resp = requests.get(
                "https://gutendex.com/books",
                params={"search": query, "languages": "en"},
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as e:
            print(f"  Gutendex search failed: {e}")
            return []

        if results:
            print(f"  Found {len(results)} book(s) with query '{query}'")
            return results

    return []


def _build_search_variants(topic: str) -> List[str]:
    """
    Return a list of search strings to try, from most specific to broadest.

    Examples:
      "astronomy finding"  → ["astronomy finding", "astronomy", "finding"]
      "dickens"            → ["dickens"]
      "french revolution"  → ["french revolution", "french", "revolution"]
    """
    topic = topic.strip()
    words = topic.split()
    variants = [topic]  # always try the full string first

    if len(words) > 1:
        # Try each word, longest first (more specific words tend to be longer)
        for word in sorted(set(words), key=len, reverse=True):
            candidate = word.strip()
            if candidate and candidate not in variants:
                variants.append(candidate)

    return variants


def fetch_from_gutenberg(topic: str, count: int, min_chars: int, max_chars: int, max_words: Optional[int], mods) -> List[Tuple[str, str, str]]:
    """
    Fetch paragraph candidates from Project Gutenberg via the Gutendex API.

    1. Searches Gutendex for books matching the topic (with fallback queries).
    2. Picks the top books by download count.
    3. Downloads the plain-text file for each book.
    4. Splits into paragraphs, applies standard filters, and caps per-book
       output so results come from diverse sources.

    Returns list of (book_title, author, paragraph_text) tuples.
    """
    requests = mods["requests"]
    target = count * 4
    candidates = []

    results = _gutendex_search(topic, requests)

    if not results:
        print(f"  No Gutenberg books found for topic '{topic}'.")
        return []

    # Sort by download count descending, take top 8
    results.sort(key=lambda b: b.get("download_count", 0), reverse=True)
    books_to_try = results[:8]

    # Cap how many paragraphs we take from any single book so we get variety.
    # Aim for at least 2–3 paragraphs per book across ~8 books.
    per_book_cap = max(3, (target // max(1, len(books_to_try))) + 2)

    for book in books_to_try:
        if len(candidates) >= target:
            break

        book_title = book.get("title", "Unknown Title")
        authors = book.get("authors", [])
        author_name = authors[0].get("name", "Unknown Author") if authors else "Unknown Author"
        formats = book.get("formats", {})

        # Find a plain-text URL — prefer UTF-8
        txt_url = (
            formats.get("text/plain; charset=utf-8")
            or formats.get("text/plain; charset=us-ascii")
            or formats.get("text/plain")
        )

        if not txt_url:
            continue

        print(f"  Fetching: {book_title} ({author_name}) ...")
        try:
            txt_resp = requests.get(txt_url, timeout=30)
            txt_resp.raise_for_status()
            raw_text = txt_resp.text
        except Exception as e:
            print(f"    Failed to fetch text: {e}")
            continue

        # Strip Project Gutenberg header/footer boilerplate
        raw_text = _strip_gutenberg_boilerplate(raw_text)

        # Split into paragraphs, filter, and cap per book for diversity
        book_paras = []
        for para in _split_into_paras(raw_text):
            if _passes_para_filters(para, min_chars, max_chars, max_words):
                book_paras.append((book_title, author_name, para))
                if len(book_paras) >= per_book_cap:
                    break

        candidates.extend(book_paras)
        print(f"    Got {len(book_paras)} paragraphs from this book ({len(candidates)} total)")

    return candidates


def _strip_gutenberg_boilerplate(text: str) -> str:
    """
    Remove the standard Project Gutenberg header and footer from plain-text files.
    The content between these markers is the actual book text.
    """
    # Header ends at first occurrence of "*** START OF"
    start_marker = re.search(r'\*{3}\s*START OF [^\n]+\n', text, re.IGNORECASE)
    if start_marker:
        text = text[start_marker.end():]

    # Footer starts at "*** END OF"
    end_marker = re.search(r'\*{3}\s*END OF [^\n]+', text, re.IGNORECASE)
    if end_marker:
        text = text[:end_marker.start()]

    return text


# ---------------------------------------------------------------------------
# Guardian fetching
# ---------------------------------------------------------------------------

def _guardian_body_to_paras(body: str, min_chars: int, max_chars: int) -> List[str]:
    """
    Guardian's bodyText arrives as one flat string with no newlines.
    Split it into sentence-window chunks that fit within [min_chars, max_chars].

    Strategy: tokenise into sentences, then greedily accumulate sentences
    into a chunk until adding the next sentence would exceed max_chars.
    """
    # Sentence splitter — handles Mr./Mrs./Dr. abbreviations crudely but well enough
    sentence_re = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'(])')
    sentences = [s.strip() for s in sentence_re.split(body) if s.strip()]

    chunks = []
    current: List[str] = []
    current_len = 0

    for sent in sentences:
        added_len = len(sent) + (1 if current else 0)  # +1 for the joining space
        if current and current_len + added_len > max_chars:
            chunk = ' '.join(current)
            if len(chunk) >= min_chars:
                chunks.append(chunk)
            current = [sent]
            current_len = len(sent)
        else:
            current.append(sent)
            current_len += added_len

    if current:
        chunk = ' '.join(current)
        if len(chunk) >= min_chars:
            chunks.append(chunk)

    return chunks


def fetch_from_guardian(topic: str, api_key: str, count: int, min_chars: int, max_chars: int, max_words: Optional[int], mods) -> List[Tuple[str, str, str]]:
    """
    Fetch paragraph candidates from The Guardian API.

    1. Searches for articles matching the topic.
    2. Extracts bodyText from each article (arrives as one flat string).
    3. Splits into sentence-window chunks and applies standard filters.

    Returns list of (headline, "The Guardian", paragraph_text) tuples.
    Requires a free API key from open-platform.theguardian.com.
    """
    requests = mods["requests"]
    target = count * 4
    candidates = []

    print(f"  Searching The Guardian for '{topic}'...")
    page_num = 1

    while len(candidates) < target:
        try:
            resp = requests.get(
                "https://content.guardianapis.com/search",
                params={
                    "q": topic,
                    "show-fields": "bodyText,headline",
                    "page-size": 10,
                    "page": page_num,
                    "lang": "en",
                    "api-key": api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  Guardian API request failed: {e}")
            break

        results = data.get("response", {}).get("results", [])
        if not results:
            break

        for article in results:
            fields = article.get("fields", {})
            headline = fields.get("headline") or article.get("webTitle", "The Guardian")
            body = fields.get("bodyText", "")

            if not body:
                continue

            # Guardian bodyText is a flat string — split into sentence windows
            for para in _guardian_body_to_paras(body, min_chars, max_chars):
                if _passes_para_filters(para, min_chars, max_chars, max_words):
                    candidates.append((headline, "The Guardian", para))

        total_pages = data.get("response", {}).get("pages", 1)
        if page_num >= total_pages or page_num >= 5:
            break
        page_num += 1

    print(f"  Collected {len(candidates)} Guardian candidates")
    return candidates


# ---------------------------------------------------------------------------
# Source dispatcher
# ---------------------------------------------------------------------------

def fetch_candidates(
    source: str,
    topic: str,
    count: int,
    min_chars: int,
    max_chars: int,
    max_words: Optional[int],
    mods,
    guardian_key: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """Dispatch to the appropriate source fetcher."""
    if source == "wikipedia":
        fetch_count = count * 3
        return fetch_from_wikipedia(topic, fetch_count, min_chars, max_chars, max_words, mods)
    elif source == "gutenberg":
        return fetch_from_gutenberg(topic, count, min_chars, max_chars, max_words, mods)
    elif source == "guardian":
        key = guardian_key or os.environ.get("GUARDIAN_API_KEY")
        if not key:
            print("ERROR: Guardian API key not found.")
            print("  Set GUARDIAN_API_KEY in .env, or pass --guardian-key YOUR_KEY")
            print("  Get a free key at: https://open-platform.theguardian.com/access/")
            sys.exit(1)
        return fetch_from_guardian(topic, key, count, min_chars, max_chars, max_words, mods)
    else:
        print(f"ERROR: Unknown source '{source}'. Choose from: wikipedia, gutenberg, guardian")
        sys.exit(1)


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
    if 50 <= fk_ease <= 70:
        fk_norm = 1.0
    elif fk_ease < 50:
        fk_norm = max(0.0, (fk_ease - 20) / 30.0)
    else:
        fk_norm = max(0.0, (100 - fk_ease) / 30.0)

    # --- Named entity density ---
    doc = nlp(text[:1000])
    ne_density = len(doc.ents) / max(1, word_count)
    ne_norm = min(1.0, ne_density / 0.10)

    # --- Lexical diversity ---
    lower_words = [w.lower() for w in words]
    lex_diversity = len(set(lower_words)) / max(1, len(lower_words))
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
    sent_norm = min(1.0, std_dev / 15.0)

    # --- Topic relevance ---
    text_lower = text.lower()
    topic_hits = sum(text_lower.count(w.lower()) for w in topic_words)
    relevance = topic_hits / max(1, word_count / 100)
    rel_norm = min(1.0, relevance / 3.0)

    # --- Sentiment strength ---
    vader_scores = vader.polarity_scores(text)
    sentiment_norm = abs(vader_scores["compound"])

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


def diversify_candidates(candidates: List[Candidate], count: int) -> List[Candidate]:
    """
    Return up to `count` candidates chosen to maximise source diversity.

    Works by round-robining through article titles in score order:
    pick the best-scoring unused candidate from each title in turn until
    we have enough. This prevents any one article/book from dominating.
    """
    if not candidates:
        return []

    # Group by article title (preserving score order within each group)
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for c in candidates:
        groups[c.article_title].append(c)

    # Order the groups by the best score in each group
    ordered_titles = sorted(groups.keys(), key=lambda t: groups[t][0].score, reverse=True)
    group_iters = {t: iter(groups[t]) for t in ordered_titles}

    selected = []
    while len(selected) < count:
        made_progress = False
        for title in ordered_titles:
            if len(selected) >= count:
                break
            it = group_iters.get(title)
            if it is None:
                continue
            try:
                selected.append(next(it))
                made_progress = True
            except StopIteration:
                group_iters[title] = None
        if not made_progress:
            break  # all groups exhausted

    return selected


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
        description="Fetch paragraphs for a ClueChain library file (Wikipedia, Gutenberg, or Guardian)."
    )
    p.add_argument("--topic", required=True, help='Search topic, e.g. "philosophy"')
    p.add_argument("--count", type=int, default=12, help="Number of paragraphs to fetch (default: 12)")
    p.add_argument("--source", default="wikipedia", choices=["wikipedia", "gutenberg", "guardian"],
                   help="Paragraph source (default: wikipedia)")
    p.add_argument("--guardian-key", dest="guardian_key", default=None,
                   help="The Guardian API key (falls back to GUARDIAN_API_KEY env var / .env)")
    p.add_argument("--output", help="Output file path (default: assets/data/library/{slug}.txt)")
    p.add_argument("--min-chars", type=int, default=450, dest="min_chars",
                   help="Min paragraph length in characters (default: 450)")
    p.add_argument("--max-chars", type=int, default=900, dest="max_chars",
                   help="Max paragraph length in characters (default: 900)")
    p.add_argument("--max-words", type=int, default=120, dest="max_words",
                   help="Max paragraph length in words (default: 120)")
    p.add_argument("--min-score", type=float, default=40.0, dest="min_score",
                   help="Discard paragraphs below this score (default: 40)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="Print output to stdout, do not write file")
    p.add_argument("--append", action="store_true",
                   help="Append new paragraphs to existing file instead of overwriting")
    return p.parse_args()


def main():
    args = parse_args()
    mods = _import_deps(args.source)

    topic = args.topic
    count = args.count

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        slug = _topic_slug(topic)
        out_path = Path("assets/data/library") / f"{slug}.txt"

    print(f"Topic     : {topic}")
    print(f"Source    : {args.source}")
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
        for block in existing_text.split('\n\n'):
            block = block.strip()
            if block and not block.startswith(('Title:', '\n')) and not re.match(r'^\d+\.$', block):
                existing_prefixes.add(block[:80])
                existing_count += 1
        print(f"Existing file has ~{existing_count} paragraphs — will deduplicate against them.")

    # Fetch
    source_label = {
        "wikipedia": "Wikipedia",
        "gutenberg": "Project Gutenberg",
        "guardian": "The Guardian",
    }[args.source]
    print(f"Fetching paragraphs from {source_label}...")

    raw = fetch_candidates(
        source=args.source,
        topic=topic,
        count=count * 4 if args.append else count,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        max_words=args.max_words,
        mods=mods,
        guardian_key=args.guardian_key,
    )
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

    selected = diversify_candidates(scored, count)
    print(f"  Selected {len(selected)} (diversity-balanced across sources)")

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
