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
        print(f"❌ [{month}/12] FAILED: {title}")
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


def parse_paragraphs(file_path: str, delimiter: str = "===") -> List[ParagraphData]:
    """
    Parse multi-paragraph file into individual ParagraphData objects.

    Args:
        file_path: Path to the text file
        delimiter: Paragraph separator pattern (default: "===")

    Returns:
        List of ParagraphData objects (up to 12)

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
    parsed = []
    for idx, para_text in enumerate(paragraphs[:12], 1):  # Only first 12
        lines = para_text.strip().split('\n')

        # Find first non-empty line (title)
        title_idx = 0
        while title_idx < len(lines) and not lines[title_idx].strip():
            title_idx += 1

        if title_idx >= len(lines):
            print(f"⚠️  Warning: Skipping paragraph {idx} - no title found")
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
            month=idx
        ))

    # Warnings
    if len(paragraphs) < 12:
        print(f"⚠️  Warning: Found only {len(paragraphs)} paragraphs (expected 12)")
    elif len(paragraphs) > 12:
        print(f"⚠️  Warning: Found {len(paragraphs)} paragraphs, processing first 12 only")

    return parsed


def rename_output_file(output_dir: str, month: int, day: int,
                      title: str, category: str) -> Path:
    """
    Rename generated JSON file to new naming convention.

    Args:
        output_dir: Directory containing the generated file
        month: Month number (1-12)
        day: Day number (1-31)
        title: Original paragraph title
        category: Category name (e.g., "FOOD")

    Returns:
        Path to renamed file

    Raises:
        FileNotFoundError: If generated file not found
    """
    # Find file matching pattern (old format: MM-DD_Title.json)
    pattern = f"{month:02d}-{day:02d}_*.json"
    old_files = list(Path(output_dir).glob(pattern))

    if len(old_files) == 0:
        raise FileNotFoundError(f"Generated file not found matching: {pattern}")

    old_file = old_files[0]  # Should only be one

    # Build new filename
    slug = slugify_title(title)
    new_filename = f"{month:02d}-{day:02d}-{category}-{slug}.json"
    new_path = Path(output_dir) / new_filename

    # Rename
    old_file.rename(new_path)

    return new_path


def generate_single_paragraph(paragraph: ParagraphData, day: int,
                              category: str, output_dir: str,
                              script_path: str) -> Tuple[bool, str, float]:
    """
    Generate JSON for a single paragraph using the existing script.

    Args:
        paragraph: ParagraphData object
        day: Day of month (1-31)
        category: Category name
        output_dir: Output directory
        script_path: Path to generate_cluechain_json.py

    Returns:
        Tuple of (success, filename_or_error, duration)
    """
    start_time = time.time()

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

        # Execute subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            # Try to extract meaningful error from stderr
            error_msg = "Unknown error"
            if result.stderr:
                error_msg = result.stderr.strip()
            # Also include stdout if stderr is empty (some errors go to stdout)
            elif result.stdout:
                error_msg = result.stdout.strip()
            return False, error_msg, time.time() - start_time

        # Rename the generated file
        try:
            new_path = rename_output_file(
                output_dir, paragraph.month, day, paragraph.title, category
            )
            duration = time.time() - start_time
            return True, new_path.name, duration
        except FileNotFoundError as e:
            return False, str(e), time.time() - start_time

    except subprocess.TimeoutExpired:
        return False, "API call timeout (>5 minutes)", time.time() - start_time
    except Exception as e:
        return False, str(e), time.time() - start_time
    finally:
        # Clean up temp file
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()


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
    reporter = ProgressReporter(len(paragraphs), category, day, delay)
    reporter.print_header()

    for idx, para in enumerate(paragraphs, 1):
        reporter.print_progress(idx, para.title, para.month)

        # Generate JSON
        success, result, duration = generate_single_paragraph(
            para, day, category, output_dir, script_path
        )

        if success:
            reporter.print_success(result, duration)

            # Rate limiting delay (except for last item)
            if idx < len(paragraphs):
                time.sleep(delay)
        else:
            reporter.print_error(para.month, para.title, result)

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


def dry_run(paragraphs: List[ParagraphData], day: int, category: str):
    """
    Preview what would be generated without making API calls.

    Args:
        paragraphs: Parsed paragraphs
        day: Day of month
        category: Category name
    """
    print("\n🔍 DRY RUN MODE - No API calls will be made\n")
    print(f"Parsed {len(paragraphs)} paragraphs:\n")

    for para in paragraphs:
        slug = slugify_title(para.title)
        filename = f"{para.month:02d}-{day:02d}-{category}-{slug}.json"

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
  12 JSON files named: MM-DD-CATEGORY-title-slug.json
  Example: 01-13-FOOD-fancy-a-kulfi-from-granita-to-queso-helado.json
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
        default=3.0,
        help="Seconds between API calls (default: 3.0)"
    )
    parser.add_argument(
        "--output",
        default="./assets/data",
        help="Output directory (default: ./assets/data)"
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

    args = parser.parse_args()

    # Validate arguments
    try:
        script_path = validate_arguments(args)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # Parse input file
    try:
        paragraphs = parse_paragraphs(args.file, args.delimiter)

        if not paragraphs:
            print("❌ Error: No valid paragraphs found in file")
            sys.exit(1)

    except ValueError as e:
        print(f"❌ Error parsing file: {e}")
        sys.exit(1)

    # Dry run mode
    if args.dry_run:
        dry_run(paragraphs, args.day, args.category)
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
