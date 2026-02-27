#!/usr/bin/env python3
import sys
import json
import re
import os

REQUIRED_TOP_KEYS = ['date', 'title', 'text', 'hiddenWords']
OPTIONAL_TOP_KEYS = ['id']  # Legacy field from old format
DATE_REGEX = r'^\d{2}-\d{2}$'  # MM-DD format (year-agnostic)
DIFFICULTY_LEVELS = ['Easy', 'Intermediate', 'Medium', 'Hard']
CLUE_TYPES = ['Indirect', 'Suggestive', 'Straight']


def validate_json(data):
    errors = []

    # Check top-level keys
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"Missing top-level key: '{key}'")

    # Check date format
    if 'date' in data and not re.match(DATE_REGEX, data['date']):
        errors.append(f"Invalid date format: '{data['date']}' (expected MM-DD)")

    # Check that no hidden word appears in the title
    title_words = set()
    if 'title' in data and isinstance(data['title'], str):
        title_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", data['title'])}

    # Check hiddenWords
    if 'hiddenWords' in data:
        hw = data['hiddenWords']
        if not isinstance(hw, list):
            errors.append("'hiddenWords' is not a list")
        elif len(hw) != 10:
            errors.append(f"'hiddenWords' must contain exactly 10 entries, found {len(hw)}")
        else:
            for i, word_entry in enumerate(hw):
                prefix = f"hiddenWords[{i}]"

                # Check required keys in word_entry
                for sub_key in ['word', 'difficulty', 'clues', 'related_words']:
                    if sub_key not in word_entry:
                        errors.append(f"{prefix}: Missing key '{sub_key}'")

                # Check word does not appear in the title
                if 'word' in word_entry and title_words:
                    if word_entry['word'].lower() in title_words:
                        errors.append(f"{prefix}: word '{word_entry['word']}' appears in the title and must not be hidden")

                # Check difficulty level
                if 'difficulty' in word_entry and word_entry['difficulty'] not in DIFFICULTY_LEVELS:
                    errors.append(f"{prefix}: Invalid difficulty '{word_entry['difficulty']}'")

                # Check clues
                if 'clues' in word_entry:
                    clues = word_entry['clues']
                    if not isinstance(clues, list) or len(clues) != 3:
                        errors.append(f"{prefix}: 'clues' must be a list of 3 items")
                    else:
                        hidden_word = word_entry.get('word', '').lower()
                        for j, clue in enumerate(clues):
                            clue_prefix = f"{prefix}.clues[{j}]"

                            # Check clue keys
                            for clue_key in ['type', 'clue', 'points']:
                                if clue_key not in clue:
                                    errors.append(f"{clue_prefix}: Missing key '{clue_key}'")

                            # Validate clue fields
                            if 'type' in clue and clue['type'] not in CLUE_TYPES:
                                errors.append(f"{clue_prefix}: Invalid type '{clue['type']}'")

                            if 'clue' in clue and not isinstance(clue['clue'], str):
                                errors.append(f"{clue_prefix}: 'clue' must be a string")

                            if 'points' in clue and not isinstance(clue['points'], int):
                                errors.append(f"{clue_prefix}: 'points' must be an integer")

                            # Check that the clue text does not contain the hidden word
                            if hidden_word and 'clue' in clue and isinstance(clue['clue'], str):
                                clue_words = re.findall(r"[a-zA-Z]+", clue['clue'].lower())
                                if hidden_word in clue_words:
                                    errors.append(f"{clue_prefix}: clue text contains the hidden word '{word_entry['word']}'")

                # Check related_words
                if 'related_words' in word_entry:
                    related = word_entry['related_words']
                    if not isinstance(related, list):
                        errors.append(f"{prefix}: 'related_words' must be a list")
                    elif len(related) > 3:
                        errors.append(f"{prefix}: 'related_words' cannot have more than 3 items")

    return errors

def main():
    if len(sys.argv) != 2:
        print("Usage: jsonvalidator <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        sys.exit(1)

    # --- Date filename vs. internal date check ---
    # Extract date from filename (expecting MM-DD.json or MM-DD_Title.json)
    base = os.path.basename(filename)
    match = re.match(r"(\d{2}-\d{2})", base)
    file_date = match.group(1) if match else None
    json_date = data.get('date')
    if file_date and json_date:
        if file_date != json_date:
            print(f"Error: Date in filename ({file_date}) does not match date in JSON ({json_date})")
            sys.exit(1)
        else:
            print(f"Date verified and okay: {file_date} matches {json_date}")
    elif file_date:
        print(f"Error: No 'date' key found in JSON to compare with filename date {file_date}")
        sys.exit(1)
    # else: if no date in filename, skip this check

    errors = validate_json(data)
    if errors:
        print("Validation FAILED with the following errors:")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)
    else:
        print("Validation PASSED: JSON is valid.")
        sys.exit(0)

if __name__ == '__main__':
    main()
