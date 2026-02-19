#!/usr/bin/env python3
"""
ClueChain JSON and Hints Generator

This script uses the Groq API to generate ClueChain game JSON files from paragraph text.
It follows the specifications in docs/JSON_Creation_PRD.md to select 10 hidden words
and generate three types of clues for each word.

Usage:
    python generate_cluechain_json.py --file path/to/paragraph.txt --title "Title" --date 07-15

Requirements:
    - GROQ_API_KEY environment variable set in .env file
    - See requirements.txt for Python dependencies
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from groq import Groq
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)


class ClueChainGenerator:
    """Generates ClueChain JSON files using Groq API."""

    def __init__(self, api_key: str):
        """Initialize the generator with Groq API credentials."""
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # Groq's most capable model

    def _build_system_prompt(self) -> str:
        """Build the comprehensive system prompt from the PRD specifications."""
        return """You are a ClueChain JSON and hints generator. Your task is to analyze an English paragraph and generate a structured JSON output with exactly 10 hidden words and their clues.

CRITICAL RULES FOR WORD SELECTION:
1. Select EXACTLY 10 single words (no more, no less)
2. EXCLUDE:
   - Short words: any word with 3 or fewer letters (e.g., 'the', 'run', 'big') — minimum 4 letters
   - Proper nouns, names, places, brands: even if lowercase in the text (e.g., 'google', 'london')
   - Made-up or invented words that don't appear in a standard English dictionary
   - Compound words (e.g., 'spaceship')
   - Words with spaces, hyphens, apostrophes, or punctuation
3. Difficulty Balance: Mix of Easy (3-4), Intermediate (3-4), and Hard (2-3) words
4. All words MUST exist in the provided paragraph text

CLUE GENERATION RULES (3 clues per word):
Each word MUST have exactly one clue of each type: Indirect, Suggestive, Straight. Never repeat a type.

1. INDIRECT (Hard, 5-7 points):
   - Lateral thinking, wordplay, riddles, puns
   - Poetic, humorous, or multi-layered
   - Max 2 sentences
   - Valid points: 5, 6, or 7 ONLY

2. SUGGESTIVE (Intermediate, 3-4 points):
   - Describes characteristic, association, or function
   - Requires simple deduction
   - Max 2 sentences
   - Valid points: 3 or 4 ONLY — never 2, never 5

3. STRAIGHT (Easy, 1-2 points):
   - Direct definition or synonym
   - Dictionary-style, unambiguous
   - Max 1 sentence
   - Valid points: 1 or 2 ONLY — never 3

COMMON MISTAKES TO AVOID:
- Do NOT assign points: 2 to a Suggestive clue (valid: 3 or 4)
- Do NOT assign points: 5 to a Straight clue (valid: 1 or 2)
- Do NOT generate two Suggestive clues and omit the Straight clue
- Do NOT generate two Indirect clues and omit the Suggestive clue
- Every word must have all three types: one Indirect, one Suggestive, one Straight

THEMATIC LINKING:
- If exactly 2-3 words are thematically related, populate their related_words arrays
- Each word in the group must list the OTHER words in the group
- If no group of 2-3 exists, all related_words arrays must be empty []

OUTPUT FORMAT:
Respond with ONLY valid JSON matching this exact structure. Do not include any additional text, explanations, or markdown formatting."""

    def _build_user_prompt(self, paragraph: str, title: Optional[str], date: str) -> str:
        """Build the user prompt with paragraph text and metadata."""
        title_text = title if title else "ClueChain Challenge"

        return f"""Generate a ClueChain JSON file for the following paragraph.

PARAGRAPH_TEXT:
{paragraph}

TITLE: {title_text}
DATE: {date}

Return ONLY the JSON object with this structure:
{{
  "title": "{title_text}",
  "date": "{date}",
  "text": "{paragraph}",
  "hiddenWords": [
    {{
      "word": "word_text",
      "difficulty": "Easy | Intermediate | Hard",
      "related_words": [],
      "clues": [
        {{"clue": "indirect clue", "type": "Indirect", "points": 5}},
        {{"clue": "suggestive clue", "type": "Suggestive", "points": 3}},
        {{"clue": "straight clue", "type": "Straight", "points": 1}}
      ]
    }}
  ]
}}

Remember:
- Exactly 10 hidden words
- 3 clues per word (Indirect, Suggestive, Straight)
- Points must be within valid ranges for each type
- Check for 2-3 word thematic groups and link them properly"""

    def generate_json(self, paragraph: str, title: Optional[str] = None,
                     date: Optional[str] = None) -> Dict:
        """
        Generate ClueChain JSON from a paragraph using Groq API.

        Args:
            paragraph: The text paragraph to process
            title: Optional title for the JSON (defaults to "ClueChain Challenge")
            date: Optional date in MM-DD format (defaults to today's MM-DD)

        Returns:
            Dictionary containing the generated JSON structure

        Raises:
            ValueError: If API response is invalid or doesn't meet requirements
        """
        if not date:
            date = datetime.now().strftime("%m-%d")

        print(f"🚀 Generating ClueChain JSON...")
        print(f"   Title: {title or 'ClueChain Challenge'}")
        print(f"   Date: {date}")
        print(f"   Paragraph length: {len(paragraph)} characters\n")

        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": self._build_user_prompt(paragraph, title, date)}
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Ensure the paragraph text is included (AI might not include it)
            if "text" not in result:
                result["text"] = paragraph

            # Add id field for backward compatibility (format: ClueChain-YYYY-MM-DD)
            if "id" not in result and date:
                current_year = datetime.now().year
                result["id"] = f"ClueChain-{current_year}-{date}"

            # Validate the response
            self._validate_json(result)

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise ValueError(f"API call failed: {e}")

    def _validate_json(self, data: Dict) -> None:
        """
        Validate that the generated JSON meets all requirements.

        Raises:
            ValueError: If validation fails
        """
        # Check top-level keys
        required_keys = {"title", "date", "text", "hiddenWords"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"Missing required keys. Expected: {required_keys}")

        # Check exactly 10 words
        hidden_words = data.get("hiddenWords", [])
        if len(hidden_words) != 10:
            raise ValueError(f"Expected exactly 10 hidden words, got {len(hidden_words)}")

        # Validate each word
        for idx, word_obj in enumerate(hidden_words, 1):
            # Check word structure
            if "word" not in word_obj or "difficulty" not in word_obj or "clues" not in word_obj:
                raise ValueError(f"Word {idx} missing required fields")

            # Check difficulty
            if word_obj["difficulty"] not in ["Easy", "Intermediate", "Hard"]:
                raise ValueError(f"Word {idx} has invalid difficulty: {word_obj['difficulty']}")

            # Check clues
            clues = word_obj.get("clues", [])
            if len(clues) != 3:
                raise ValueError(f"Word {idx} must have exactly 3 clues, got {len(clues)}")

            # Validate clue types and points
            clue_types = [c.get("type") for c in clues]
            expected_types = {"Indirect", "Suggestive", "Straight"}
            if set(clue_types) != expected_types:
                raise ValueError(f"Word {idx} missing required clue types. Got: {clue_types}")

            # Validate point ranges
            for clue in clues:
                clue_type = clue.get("type")
                points = clue.get("points")

                if clue_type == "Indirect" and points not in [5, 6, 7]:
                    raise ValueError(f"Indirect clue must have 5-7 points, got {points}")
                elif clue_type == "Suggestive" and points not in [3, 4]:
                    raise ValueError(f"Suggestive clue must have 3-4 points, got {points}")
                elif clue_type == "Straight" and points not in [1, 2]:
                    raise ValueError(f"Straight clue must have 1-2 points, got {points}")

        print("✅ JSON validation passed!")

        # Show hidden words by difficulty
        print("\n📝 Hidden Words (10):")
        by_difficulty = {"Easy": [], "Intermediate": [], "Hard": []}
        for word_obj in hidden_words:
            by_difficulty[word_obj["difficulty"]].append(word_obj["word"])

        for difficulty in ["Easy", "Intermediate", "Hard"]:
            words = by_difficulty[difficulty]
            if words:
                print(f"   {difficulty}: {', '.join(words)}")

    def save_json(self, data: Dict, output_dir: str, date: str, title: Optional[str] = None) -> Path:
        """
        Save the generated JSON to a file.

        Args:
            data: The JSON data to save
            output_dir: Directory to save the file
            date: Date string for filename
            title: Optional title for filename

        Returns:
            Path to the saved file
        """
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if title:
            # Sanitize title for filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')
            filename = f"{date}_{safe_title}.json"
        else:
            filename = f"{date}.json"

        file_path = output_path / filename

        # Save with pretty formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path

    def print_summary(self, data: Dict) -> None:
        """Print a human-readable summary of the generated data."""
        print("\n" + "="*60)
        print("📊 GENERATION SUMMARY")
        print("="*60)
        print(f"Title: {data['title']}")
        print(f"Date: {data['date']}")
        print(f"\n📝 Hidden Words ({len(data['hiddenWords'])}):")

        # Group by difficulty
        by_difficulty = {"Easy": [], "Intermediate": [], "Hard": []}
        for word_obj in data["hiddenWords"]:
            by_difficulty[word_obj["difficulty"]].append(word_obj["word"])

        for difficulty, words in by_difficulty.items():
            if words:
                print(f"  {difficulty}: {', '.join(words)}")

        # Check for related words
        related_groups = []
        processed = set()

        for word_obj in data["hiddenWords"]:
            word = word_obj["word"]
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

        print("="*60 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate ClueChain JSON files from paragraph text using Groq API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from a text file with custom title
  python generate_cluechain_json.py --file paragraphs.txt --title "Food Science"

  # Specify output directory and date
  python generate_cluechain_json.py --file paragraphs.txt --date 11-20 --output ./data

  # Use default date (today's MM-DD) and output to current directory
  python generate_cluechain_json.py --file paragraphs.txt
        """
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to the text file containing the paragraph"
    )
    parser.add_argument(
        "--title",
        help="Title for the JSON (optional, defaults to 'ClueChain Challenge')"
    )
    parser.add_argument(
        "--date",
        help="Date in MM-DD format (optional, defaults to today's MM-DD)"
    )
    parser.add_argument(
        "--output",
        default="./assets/data",
        help="Output directory for JSON file (default: ./assets/data)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("❌ Error: GROQ_API_KEY not found in environment variables")
        print("Please create a .env file with your Groq API key:")
        print("  GROQ_API_KEY=your_api_key_here")
        print("\nSee .env.example for template")
        sys.exit(1)

    # Read paragraph from file
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            paragraph = f.read().strip()

        if not paragraph:
            print(f"❌ Error: File {args.file} is empty")
            sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)

    # Generate JSON
    try:
        generator = ClueChainGenerator(api_key)
        result = generator.generate_json(paragraph, args.title, args.date)

        # Save to file
        date = args.date or datetime.now().strftime("%m-%d")
        output_file = generator.save_json(result, args.output, date, args.title)

        # Print summary
        generator.print_summary(result)

        print(f"✅ JSON file saved to: {output_file}")
        print(f"\n💡 Tip: Validate the JSON using:")
        print(f"   python assets/data/json_validator.py {output_file}")

    except ValueError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
