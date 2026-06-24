#!/usr/bin/env python3
"""
Batch ClueChain JSON Generator

This script processes multi-paragraph text files and generates ClueChain JSON files
for each paragraph using the existing generate_cluechain_json.py script.

Usage:
    python batch_generate_cluechain_json.py --file paragraphs_food.txt --category FOOD --day 13

Features:
    - Parses multi-paragraph files with configurable delimiters (===, #, ---)
    - Generates 12 monthly JSON files with a single command
    - Automatic rate limiting to respect API quotas
    - Progress reporting and error handling
    - Dry-run mode for testing without API calls
    - Continue-on-error for graceful failure recovery

Requirements:
    - Existing generate_cluechain_json.py script
    - GROQ_API_KEY in environment variables
"""

import argparse
import csv
import datetime
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
import tempfile
import glob as glob_module


@dataclass
class ParagraphData:
    """Parsed paragraph from input file."""
    title: str
    attribution: str
    text: str  # Full text with title + attribution + paragraph
    month: int  # 1-12


@dataclass
class BatchResults:
    """Results from batch processing."""
    successful: List[str]  # Filenames
    failed: List[Tuple[int, str]]  # (month, error_message)
    total_time: float


class ProgressReporter:
    """Handles progress reporting and user feedback."""

    def __init__(self, total: int, category: str, day: int, delay: float):
        self.total = total
        self.category = category
        self.day = day
        self.delay = delay
        self.successful = []
        self.failed = []
        self.start_time = None

    def print_header(self):
        """Print the batch generation header."""
        print("\n🚀 Starting Batch Generation")
        print(f"   Category: {self.category}")
        print(f"   Day: {self.day}")
        print(f"   Paragraphs: {self.total}")
        print(f"   Delay: {self.delay}s between calls")
        print("═" * 60 + "\n")
        self.start_time = time.time()

    def print_progress(self, index: int, title: str, month: int):
        """Print progress for current paragraph."""
        print(f"[{index}/{self.total}] Processing: {title}")
        print(f"       Date: {month:02d}-{self.day:02d}")
        print(f"       Calling Groq API...")

    def print_success(self, filename: str, duration: float):
        """Print success message."""
        print(f"✅     Generated: {filename} ({duration:.1f}s)\n")
        self.successful.append(filename)

    def print_error(self, month: int, title: str, error: str):
        """Print error message."""
        print(f"❌ [month {month:02d}] FAILED (all retries exhausted): {title}")
        print(f"   Error: {error}")
        print(f"   Completed: {len(self.successful)}/{self.total}")
        print(f"   Failed: {len(self.failed) + 1}/{self.total}\n")
        self.failed.append((month, error))

    def print_summary(self):
        """Print final summary."""
        total_time = time.time() - self.start_time

        print("\n" + "═" * 60)
        print("📊 BATCH GENERATION SUMMARY")
        print("═" * 60)
        print(f"Total Paragraphs: {self.total}")
        print(f"Successful: {len(self.successful)}")
        print(f"Failed: {len(self.failed)}")

        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        print(f"Total Time: {minutes}m {seconds}s")

        if self.successful:
            avg_time = total_time / len(self.successful)
            print(f"Average Time per Paragraph: {avg_time:.1f}s")

        print()

        if len(self.failed) == 0:
            print("✅ All files generated successfully!")
        else:
            print(f"⚠️  {len(self.failed)} file(s) failed to generate")
            for month, error in self.failed:
                print(f"   - Month {month:02d}: {error}")


def slugify_title(title: str) -> str:
    """
    Convert title to URL-safe slug.

    Args:
        title: Original title string

    Returns:
        Slugified version (lowercase, hyphens, no punctuation)

    Examples:
        "Fancy a Kulfi? From Granita to Queso Helado"
        -> "fancy-a-kulfi-from-granita-to-queso-helado"
    """
    # Convert to lowercase
    slug = title.lower()

    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')

    # Remove all punctuation except hyphens
    slug = re.sub(r'[^\w\-]', '', slug)

    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens
    slug = slug.strip('-')

    return slug


def parse_paragraphs(file_path: str, delimiter: str = "===",
                     start_month: int = 1, end_month: int = 12) -> List[ParagraphData]:
    """
    Parse multi-paragraph file into individual ParagraphData objects.

    Args:
        file_path: Path to the text file
        delimiter: Paragraph separator pattern (default: "===")
        start_month: First month number to assign (default: 1)
        end_month: Last month number to assign (default: 12)

    Returns:
        List of ParagraphData objects (up to end_month - start_month + 1)

    Raises:
        ValueError: If file is empty or has invalid format
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {e}")

    if not content.strip():
        raise ValueError("File is empty")

    # Build delimiter regex pattern
    # Supports: ===, ====, #, ##, ###, ---, or numbered (1., 2., ... 12.)
    delimiter_pattern = r'^\s*(={3,}|#{1,3}|-{3,}|\d{1,2}\.)\s*$'

    # Split by delimiter
    sections = re.split(delimiter_pattern, content, flags=re.MULTILINE)

    # Filter out empty sections and delimiter matches
    paragraphs = []
    current_text = []

    for section in sections:
        section = section.strip()
        if not section or re.match(delimiter_pattern, section):
            # This is a delimiter or empty - if we have accumulated text, save it
            if current_text:
                paragraphs.append('\n'.join(current_text))
                current_text = []
        else:
            current_text.append(section)

    # Don't forget the last paragraph
    if current_text:
        paragraphs.append('\n'.join(current_text))

    if not paragraphs:
        raise ValueError("No paragraphs found in file")

    # Parse each paragraph
    count = end_month - start_month + 1
    parsed = []
    for idx, para_text in enumerate(paragraphs[:count], 0):  # Slice to requested range
        lines = para_text.strip().split('\n')

        # Find first non-empty line (title)
        title_idx = 0
        while title_idx < len(lines) and not lines[title_idx].strip():
            title_idx += 1

        if title_idx >= len(lines):
            print(f"⚠️  Warning: Skipping paragraph {idx + 1} - no title found")
            continue

        title = re.sub(r'^[Tt]itle:\s*', '', lines[title_idx].strip())

        # Next non-empty line is attribution
        attribution_idx = title_idx + 1
        while attribution_idx < len(lines) and not lines[attribution_idx].strip():
            attribution_idx += 1

        attribution = ""
        if attribution_idx < len(lines):
            attribution = lines[attribution_idx].strip()

        # Full text is everything from title onward
        full_text = '\n'.join(lines[title_idx:]).strip()

        parsed.append(ParagraphData(
            title=title,
            attribution=attribution,
            text=full_text,
            month=start_month + idx
        ))

    # Warnings
    if len(paragraphs) < count:
        print(f"⚠️  Warning: Found only {len(paragraphs)} paragraphs (expected {count} for months {start_month:02d}-{end_month:02d})")
    elif len(paragraphs) > count:
        print(f"⚠️  Warning: Found {len(paragraphs)} paragraphs, processing first {count} only (months {start_month:02d}-{end_month:02d})")

    return parsed


def rename_output_file(output_dir: str, month: int, day: int,
                      title: str, category: str) -> Path:
    """
    Rename generated JSON file to MMDD.json in the new directory structure.

    Args:
        output_dir: Directory containing the generated file
        month: Month number (1-12)
        day: Day number (1-31)
        title: Original paragraph title (unused, kept for API compatibility)
        category: Category name (unused, kept for API compatibility)

    Returns:
        Path to renamed file

    Raises:
        FileNotFoundError: If generated file not found
    """
    # Find file matching pattern (generator writes MM-DD_Title.json or MM-DD.json)
    pattern = f"{month:02d}-{day:02d}*.json"
    old_files = list(Path(output_dir).glob(pattern))

    if len(old_files) == 0:
        raise FileNotFoundError(f"Generated file not found matching: {pattern}")

    old_file = old_files[0]  # Should only be one

    # New filename: MMDD.json (e.g. "0113.json")
    new_filename = f"{month:02d}{day:02d}.json"
    new_path = Path(output_dir) / new_filename

    # Rename (overwrite if exists)
    old_file.rename(new_path)

    return new_path


def regenerate_daily_index(output_dir: str) -> None:
    """
    Regenerate assets/data/indexes/daily.json from the files present in output_dir.

    Args:
        output_dir: Path to assets/data/puzzles/daily/mmdd/
    """
    import json as _json
    mmdd_dir = Path(output_dir)
    indexes_dir = mmdd_dir.parent.parent.parent / "indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)
    index_path = indexes_dir / "daily.json"

    generic_days = sorted(f.stem for f in mmdd_dir.glob("*.json"))

    # Preserve existing overrides if the file already exists
    existing_overrides = {}
    if index_path.exists():
        try:
            existing = _json.loads(index_path.read_text(encoding="utf-8"))
            existing_overrides = existing.get("overrides", {})
        except Exception:
            pass

    data = {
        "collection": "daily",
        "description": "One puzzle per calendar day.",
        "fallback": "mmdd",
        "generic_days": generic_days,
        "overrides": existing_overrides,
    }
    index_path.write_text(_json.dumps(data, indent=2), encoding="utf-8")
    print(f"   ↻ Regenerated indexes/daily.json ({len(generic_days)} days)")


LOG_FILE = Path(__file__).parent.parent / "logs" / "batch_failures.csv"
LOG_COLUMNS = ["timestamp", "mmdd", "title", "category", "reason_code", "attempts", "duration_s", "error_detail"]

# Ordered patterns: first match wins. Checked against the final error string (lowercased).
_REASON_PATTERNS = [
    ("TITLE_WORD_VIOLATION",  r"title word|contain title word|hidden words contain title"),
    ("CLUE_CONTAINS_WORD",    r"clue text contains the hidden word"),
    ("CLUE_TYPE_MISMATCH",    r"missing required clue types|clue types"),
    ("CLUE_POINTS_INVALID",   r"points, got|must have \d"),
    ("WRONG_CLUE_COUNT",      r"must have exactly 3 clues"),
    ("RATE_LIMIT",            r"429|rate.?limit"),
    ("JSON_PARSE_ERROR",      r"json|parse|decode"),
    ("TIMEOUT",               r"timeout"),
    ("FILE_NOT_FOUND",        r"no generated file found|filenotfound"),
]


def _classify_error(error: str) -> str:
    """Map a raw error string to a short reason code."""
    low = error.lower()
    for code, pattern in _REASON_PATTERNS:
        if re.search(pattern, low):
            return code
    return "SUBPROCESS_ERROR"


def log_failure(mmdd: str, title: str, category: str, reason_code: str,
                attempts: int, duration: float, error_detail: str) -> None:
    """Append one failure row to the persistent batch failures log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_header = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mmdd": mmdd,
            "title": title,
            "category": category,
            "reason_code": reason_code,
            "attempts": attempts,
            "duration_s": f"{duration:.1f}",
            "error_detail": error_detail[:300].replace("\n", " "),  # cap length, flatten newlines
        })


def generate_single_paragraph(paragraph: ParagraphData, day: int,
                              category: str, output_dir: str,
                              script_path: str,
                              groq_keys: List[str],
                              key_index: int = 0,
                              max_retries: int = 3) -> Tuple[bool, str, float]:
    """
    Generate JSON for a single paragraph using the existing script.
    Retries up to max_retries times on validation failure.

    Args:
        paragraph: ParagraphData object
        day: Day of month (1-31)
        category: Category name
        output_dir: Output directory
        script_path: Path to generate_cluechain_json.py
        groq_keys: List of available GROQ API keys (1–3)
        key_index: Which key to use (0-based, wraps around)
        max_retries: Maximum number of attempts (default: 3)

    Returns:
        Tuple of (success, filename_or_error, duration, reason_code, attempts_made)
    """
    start_time = time.time()
    last_error = "Unknown error"
    attempts_made = 0

    # Pick the key for this paragraph (round-robin)
    active_key = groq_keys[key_index % len(groq_keys)] if groq_keys else ""
    key_num = key_index % len(groq_keys) + 1 if groq_keys else 1
    print(f"       🔑 Using GROQ_API_KEY{key_num}")

    # Build subprocess environment: inherit current env, override GROQ_API_KEY
    sub_env = os.environ.copy()
    sub_env["GROQ_API_KEY"] = active_key

    for attempt in range(1, max_retries + 1):
        attempts_made = attempt
        if attempt > 1:
            print(f"       ↻ Retry {attempt}/{max_retries}...")

        # Create temporary file with paragraph text
        temp_file = None
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                             delete=False, encoding='utf-8') as f:
                f.write(paragraph.text)
                temp_file = f.name

            # Build subprocess command
            date_str = f"{paragraph.month:02d}-{day:02d}"
            cmd = [
                sys.executable,  # Use same Python interpreter
                script_path,
                "--file", temp_file,
                "--title", paragraph.title,
                "--date", date_str,
                "--output", output_dir
            ]

            # Execute subprocess — stream stdout live AND collect it for error extraction
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # merge stderr into stdout
                text=True,
                env=sub_env,
            )
            collected_lines = []
            for line in proc.stdout:
                print(line, end="", flush=True)   # live display
                collected_lines.append(line)
            proc.wait(timeout=300)
            collected_output = "".join(collected_lines)

            if proc.returncode != 0:
                # Extract the most informative error line from output
                error_line = next(
                    (l.strip() for l in reversed(collected_lines)
                     if l.strip() and not l.startswith("   ↻")),
                    f"exit code {proc.returncode}"
                )
                last_error = error_line

                # Non-retryable errors: the inner script already gave up — don't waste API calls
                non_retryable = [
                    "title word", "contain title word", "hidden words contain title",
                    "clue text contains the hidden word",
                ]
                if any(phrase in last_error.lower() for phrase in non_retryable):
                    break  # Inner script already flagged this as unretryable

                continue  # Retry for transient failures (JSON parse, validation, etc.)

            # Rename to MMDD.json only when targeting the mmdd directory;
            # staging and other dirs keep the descriptive MM-DD_Title.json name.
            try:
                is_mmdd_dir = Path(output_dir).resolve().name == "mmdd"
                if is_mmdd_dir:
                    new_path = rename_output_file(
                        output_dir, paragraph.month, day, paragraph.title, category
                    )
                    regenerate_daily_index(output_dir)
                else:
                    # Find the generated file by its original name
                    pattern = f"{paragraph.month:02d}-{day:02d}*.json"
                    matches = list(Path(output_dir).glob(pattern))
                    if not matches:
                        raise FileNotFoundError(
                            f"Generated file not found matching: {pattern}"
                        )
                    new_path = matches[0]
                duration = time.time() - start_time
                return True, new_path.name, duration, "", attempts_made
            except FileNotFoundError as e:
                last_error = str(e)
                continue  # Retry

        except subprocess.TimeoutExpired:
            last_error = "API call timeout (>5 minutes)"
            break  # Don't retry timeouts
        except Exception as e:
            last_error = str(e)
            break  # Don't retry unexpected errors
        finally:
            # Clean up temp file
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()

    # Use "EXHAUSTED" to mark this as the batch-level summary row,
    # distinct from the per-attempt rows written by generate_cluechain_json.py
    reason_code = "EXHAUSTED:" + _classify_error(last_error)
    return False, last_error, time.time() - start_time, reason_code, attempts_made


def process_batch(paragraphs: List[ParagraphData], day: int, category: str,
                 output_dir: str, script_path: str, delay: float = 3.0,
                 continue_on_error: bool = False) -> BatchResults:
    """
    Process batch of paragraphs and generate JSON files.

    Args:
        paragraphs: List of ParagraphData objects
        day: Day of month
        category: Category name
        output_dir: Output directory
        script_path: Path to generation script
        delay: Seconds to wait between API calls
        continue_on_error: Continue processing if one fails

    Returns:
        BatchResults with success/failure tracking
    """
    # Collect available Groq keys from environment (loaded by caller via dotenv)
    groq_keys = [k for k in [
        os.environ.get("GROQ_API_KEY"),
        os.environ.get("GROQ_API_KEY2"),
        os.environ.get("GROQ_API_KEY3"),
    ] if k]
    if len(groq_keys) > 1:
        print(f"ℹ️  Key rotation enabled: {len(groq_keys)} GROQ keys found (rotating per paragraph)")
    else:
        print(f"ℹ️  Single GROQ key in use (add GROQ_API_KEY2/3 to .env for rotation)")

    reporter = ProgressReporter(len(paragraphs), category, day, delay)
    reporter.print_header()

    for idx, para in enumerate(paragraphs, 1):
        reporter.print_progress(idx, para.title, para.month)

        # Generate JSON — rotate key by paragraph index (0-based)
        success, result, duration, reason_code, attempts_made = generate_single_paragraph(
            para, day, category, output_dir, script_path,
            groq_keys=groq_keys, key_index=idx - 1,
        )

        if success:
            reporter.print_success(result, duration)

            # Rate limiting delay (except for last item)
            if idx < len(paragraphs):
                time.sleep(delay)
        else:
            reporter.print_error(para.month, para.title, result)
            mmdd = f"{para.month:02d}{day:02d}"
            log_failure(mmdd, para.title, category, reason_code,
                        attempts_made, duration, result)
            print(f"   📝 Logged to {LOG_FILE}")

            if not continue_on_error:
                print("\n❌ Stopping due to error (use --continue-on-error to continue)\n")
                break
            else:
                # Still delay on error to avoid rapid-fire failures
                if idx < len(paragraphs):
                    time.sleep(delay)

    reporter.print_summary()

    return BatchResults(
        successful=reporter.successful,
        failed=reporter.failed,
        total_time=time.time() - reporter.start_time
    )


def dry_run(paragraphs: List[ParagraphData], day: int, category: str,
            output_dir: str = "./assets/data/puzzles/daily/mmdd"):
    """
    Preview what would be generated without making API calls.

    Args:
        paragraphs: Parsed paragraphs
        day: Day of month
        category: Category name
        output_dir: Output directory
    """
    is_mmdd_dir = Path(output_dir).resolve().name == "mmdd"
    print("\n🔍 DRY RUN MODE - No API calls will be made\n")
    print(f"Output dir: {output_dir}")
    print(f"Rename to MMDD.json: {'yes' if is_mmdd_dir else 'no (keeping title-based names)'}\n")
    print(f"Parsed {len(paragraphs)} paragraphs:\n")

    for para in paragraphs:
        if is_mmdd_dir:
            filename = f"{para.month:02d}{day:02d}.json"
        else:
            slug = slugify_title(para.title)
            filename = f"{para.month:02d}-{day:02d}_{slug}.json"

        print(f"[{para.month}] Month: {para.month:02d}, Day: {day:02d}")
        print(f"    Title: {para.title}")
        print(f"    Attribution: {para.attribution}")
        print(f"    Text length: {len(para.text)} characters")
        print(f"    Output: {filename}\n")

    print("✅ All paragraphs parsed successfully")
    print(f"   Ready to generate {len(paragraphs)} JSON files\n")


def validate_arguments(args):
    """
    Validate command-line arguments.

    Args:
        args: Parsed arguments

    Raises:
        ValueError: If validation fails
    """
    # Validate file exists
    if not Path(args.file).exists():
        raise ValueError(f"Input file not found: {args.file}")

    # Validate day
    if not 1 <= args.day <= 31:
        raise ValueError(f"Invalid day: {args.day} (must be 1-31)")

    # Validate category (basic check)
    if not args.category.replace('_', '').replace('-', '').isalnum():
        raise ValueError(f"Invalid category name: {args.category}")

    # Validate month range
    if not 1 <= args.start_month <= 12:
        raise ValueError(f"Invalid start-month: {args.start_month} (must be 1-12)")
    if not 1 <= args.end_month <= 12:
        raise ValueError(f"Invalid end-month: {args.end_month} (must be 1-12)")
    if args.start_month > args.end_month:
        raise ValueError(f"start-month ({args.start_month}) must be <= end-month ({args.end_month})")

    # Validate delay
    if args.delay < 0:
        raise ValueError(f"Invalid delay: {args.delay} (must be >= 0)")

    # Find generate_cluechain_json.py
    script_path = Path(__file__).parent / "generate_cluechain_json.py"
    if not script_path.exists():
        raise ValueError(f"Generator script not found: {script_path}")

    return script_path


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Batch generate ClueChain JSON files from multi-paragraph text files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python batch_generate_cluechain_json.py --file paragraphs_food.txt --category FOOD --day 13

  # Custom delay for rate limiting
  python batch_generate_cluechain_json.py --file paragraphs_food.txt --category FOOD --day 13 --delay 5

  # Continue on error
  python batch_generate_cluechain_json.py --file paragraphs_food.txt --category FOOD --day 13 --continue-on-error

  # Dry run to preview
  python batch_generate_cluechain_json.py --file paragraphs_food.txt --category FOOD --day 13 --dry-run

Input File Format:
  Paragraphs separated by delimiters (===, #, or ---)
  Each paragraph:
    Line 1: Title
    Line 2: Attribution (author/source)
    Blank line
    Remaining: Paragraph text

Output Format:
  12 JSON files named: MMDD.json
  Example: 0113.json  (saved to assets/data/puzzles/daily/mmdd/)
        """
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to multi-paragraph text file"
    )
    parser.add_argument(
        "--category",
        required=True,
        help="Category name (e.g., FOOD, GEOGRAPHY)"
    )
    parser.add_argument(
        "--day",
        type=int,
        required=True,
        help="Day of month (1-31)"
    )
    parser.add_argument(
        "--delimiter",
        default="===",
        help="Paragraph separator (default: ===)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=30.0,
        help="Seconds between API calls (default: 30.0)"
    )
    parser.add_argument(
        "--output-dir",
        default="./assets/data/puzzles/daily/mmdd",
        dest="output",
        help="Output directory (default: ./assets/data/puzzles/daily/mmdd)"
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing if one paragraph fails"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview parsing without making API calls"
    )
    parser.add_argument(
        "--start-month",
        type=int,
        default=1,
        help="First month to generate (1-12, default: 1)"
    )
    parser.add_argument(
        "--end-month",
        type=int,
        default=12,
        help="Last month to generate (1-12, default: 12)"
    )

    args = parser.parse_args()

    # Load .env so GROQ_API_KEY* are available in os.environ
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed; rely on environment variables being set directly

    # Validate arguments
    try:
        script_path = validate_arguments(args)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # Parse input file
    try:
        paragraphs = parse_paragraphs(args.file, args.delimiter,
                                      args.start_month, args.end_month)

        if not paragraphs:
            print("❌ Error: No valid paragraphs found in file")
            sys.exit(1)

    except ValueError as e:
        print(f"❌ Error parsing file: {e}")
        sys.exit(1)

    # Dry run mode
    if args.dry_run:
        dry_run(paragraphs, args.day, args.category, args.output)
        sys.exit(0)

    # Process batch
    try:
        results = process_batch(
            paragraphs,
            args.day,
            args.category,
            args.output,
            str(script_path),
            args.delay,
            args.continue_on_error
        )

        # Exit with error code if any failed and not continuing on error
        if results.failed and not args.continue_on_error:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
