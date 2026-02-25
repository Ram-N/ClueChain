#!/usr/bin/env python3
"""
ClueChain JSON and Hints Generator

Generates ClueChain puzzle JSON from paragraph text.
Primary backend: Groq (fast, free tier).
Fallback backend: OpenRouter / Gemini Flash Lite (cheap, high quality).

Usage:
    python generate_cluechain_json.py --file paragraph.txt --title "Title" --date 07-15
    python generate_cluechain_json.py --file paragraph.txt --model openrouter

Requirements:
    - GROQ_API_KEY and/or OPENROUTER_API_KEY in .env file
"""

import argparse
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

# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

GROQ_MODEL       = "llama-3.3-70b-versatile"
OPENROUTER_BASE  = "https://openrouter.ai/api/v1"

_model_config_path = Path(__file__).parent / "model-config.json"
if _model_config_path.exists():
    with open(_model_config_path) as _f:
        OPENROUTER_MODEL = json.load(_f).get("openrouter_model", "google/gemini-2.0-flash-lite-001")
else:
    OPENROUTER_MODEL = "google/gemini-2.0-flash-lite-001"


def _make_groq_client(api_key: str):
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        raise ImportError("groq package not installed. Run: uv pip install groq")


def _make_openrouter_client(api_key: str):
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE)
    except ImportError:
        raise ImportError("openai package not installed. Run: uv pip install openai")


def _call_llm(client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Call either Groq or OpenRouter (both are OpenAI-compatible) and return raw content."""
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
# Generator class
# ---------------------------------------------------------------------------

class ClueChainGenerator:
    """Generates ClueChain JSON files.

    backend: 'groq' (default) | 'openrouter'
    Falls back to openrouter automatically when groq exhausts all retries.
    """

    def __init__(self, groq_key: Optional[str] = None,
                 openrouter_key: Optional[str] = None,
                 backend: str = "groq"):
        self.groq_key         = groq_key
        self.openrouter_key   = openrouter_key
        self.backend          = backend  # 'groq' | 'openrouter'

        # Eagerly validate requested backend
        if backend == "groq" and not groq_key:
            raise ValueError("GROQ_API_KEY required for groq backend")
        if backend == "openrouter" and not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY required for openrouter backend")

    def _client_and_model(self, backend: str):
        if backend == "groq":
            return _make_groq_client(self.groq_key), GROQ_MODEL
        else:
            return _make_openrouter_client(self.openrouter_key), OPENROUTER_MODEL

    # ------------------------------------------------------------------
    # Prompt builders (shared by both backends)
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return """You are a ClueChain JSON and hints generator. Your task is to analyze an English paragraph and generate a structured JSON output with exactly 10 hidden words and their clues.

⚠️  ABSOLUTE RULE — NEVER BREAK THIS:
Do NOT include the hidden word (or any of its inflected forms: plurals, past tense,
gerunds, etc.) anywhere in any of that word's clues. This is the most common mistake
and will always cause the puzzle to fail. If you catch yourself writing the answer into
a clue, rewrite the clue from scratch without it.

CRITICAL RULES FOR WORD SELECTION:
1. Select EXACTLY 10 single words (no more, no less)
2. EXCLUDE:
   - Short words: any word with 3 or fewer letters (e.g., 'the', 'run', 'big') — minimum 4 letters
   - Proper nouns, names, places, brands: even if lowercase in the text (e.g., 'google', 'london')
   - Made-up or invented words that don't appear in a standard English dictionary
   - Compound words (e.g., 'spaceship')
   - Words with spaces, hyphens, apostrophes, or punctuation
   - Any word that appears in the TITLE (case-insensitive) — title words are already visible to the player and must never be hidden
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
- 🚫 NEVER use the hidden word (or its inflections) anywhere in its clues. Not even
  once. Not even as part of an example sentence. Write around it entirely.

THEMATIC LINKING:
- If exactly 2-3 words are thematically related, populate their related_words arrays
- Each word in the group must list the OTHER words in the group
- If no group of 2-3 exists, all related_words arrays must be empty []

OUTPUT FORMAT:
Respond with ONLY valid JSON matching this exact structure. Do not include any additional text, explanations, or markdown formatting."""

    def _build_user_prompt(self, paragraph: str, title: Optional[str], date: str) -> str:
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
- Check for 2-3 word thematic groups and link them properly
- NEVER use a word from the title "{title_text}" as a hidden word
- NEVER write the hidden word into any of its own clues (not even as an example)"""

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _title_word_violations(self, data: Dict, title: str) -> List[str]:
        """Return hidden words that appear in the title."""
        title_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", title)}
        return [
            w["word"] for w in data.get("hiddenWords", [])
            if w.get("word", "").lower() in title_words
        ]

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
                                date: str, backend: str, max_retries: int) -> Dict:
        """Try to generate using a specific backend, with retries for title violations."""
        client, model = self._client_and_model(backend)
        title_text    = title or "ClueChain Challenge"
        system_prompt = self._build_system_prompt()
        user_prompt   = self._build_user_prompt(paragraph, title, date)
        last_error    = "Unknown error"

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"       ↻ Retry {attempt}/{max_retries}...")

            content = _call_llm(client, model, system_prompt, user_prompt)
            result  = json.loads(content)

            if "text" not in result:
                result["text"] = paragraph
            if "id" not in result:
                result["id"] = f"ClueChain-{datetime.now().year}-{date}"

            violations = self._title_word_violations(result, title_text)
            if violations:
                print(f"       ⚠️  Title-word violation: {violations} — retrying...")
                last_error = f"Hidden words contain title words: {violations}"
                continue

            self._validate_json(result)
            return result

        raise ValueError(f"[{backend}] Failed after {max_retries} attempts: {last_error}")

    # ------------------------------------------------------------------
    # Public generate (with automatic fallback)
    # ------------------------------------------------------------------

    def generate_json(self, paragraph: str, title: Optional[str] = None,
                      date: Optional[str] = None, max_retries: int = 3) -> Dict:
        """
        Generate ClueChain JSON. Uses the configured primary backend.
        If the primary fails all retries, automatically falls back to OpenRouter
        (if the key is available), rather than raising immediately.
        """
        if not date:
            date = datetime.now().strftime("%m-%d")

        title_text = title or "ClueChain Challenge"
        print(f"🚀 Generating ClueChain JSON...")
        print(f"   Title: {title_text}  |  Date: {date}  |  Backend: {self.backend}")
        print(f"   Paragraph length: {len(paragraph)} characters")

        try:
            return self._generate_with_backend(paragraph, title, date,
                                               self.backend, max_retries)
        except (ValueError, Exception) as primary_err:
            # Determine fallback backend
            fallback = "openrouter" if self.backend == "groq" else "groq"
            fallback_key = (self.openrouter_key if fallback == "openrouter"
                            else self.groq_key)

            if not fallback_key:
                raise ValueError(
                    f"Primary backend ({self.backend}) failed and no fallback key available.\n"
                    f"Error: {primary_err}"
                )

            print(f"\n   ⚠️  Primary backend ({self.backend}) failed: {primary_err}")
            print(f"   🔄 Falling back to {fallback} ({OPENROUTER_MODEL if fallback == 'openrouter' else GROQ_MODEL})...")

            return self._generate_with_backend(paragraph, title, date,
                                               fallback, max_retries)

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
  # Default: Groq primary, OpenRouter fallback
  python generate_cluechain_json.py --file paragraph.txt --title "Food Science"

  # Force OpenRouter (Gemini Flash Lite)
  python generate_cluechain_json.py --file paragraph.txt --model openrouter

  # Specify date and output directory
  python generate_cluechain_json.py --file paragraph.txt --date 11-20 --output ./data
        """
    )
    parser.add_argument("--file",   required=True,        help="Path to paragraph text file")
    parser.add_argument("--title",                        help="Title (defaults to 'ClueChain Challenge')")
    parser.add_argument("--date",                         help="Date in MM-DD format (defaults to today)")
    parser.add_argument("--output", default="./assets/data/puzzles/daily/mmdd", help="Output directory")
    parser.add_argument("--model",  default="groq",
                        choices=["groq", "openrouter"],
                        help="Primary backend: groq (default) or openrouter")
    args = parser.parse_args()

    load_dotenv()
    groq_key       = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # Validate that the requested primary backend has a key
    if args.model == "groq" and not groq_key:
        print("❌ Error: GROQ_API_KEY not set. Add it to your .env file.")
        sys.exit(1)
    if args.model == "openrouter" and not openrouter_key:
        print("❌ Error: OPENROUTER_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    # Warn if fallback key is missing (non-fatal)
    if args.model == "groq" and not openrouter_key:
        print("⚠️  OPENROUTER_API_KEY not set — no fallback available if Groq fails.")
    if args.model == "openrouter" and not groq_key:
        print("⚠️  GROQ_API_KEY not set — no fallback available if OpenRouter fails.")

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
            openrouter_key=openrouter_key,
            backend=args.model,
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
