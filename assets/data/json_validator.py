#!/usr/bin/env python3
import sys
import json
import re
import os

REQUIRED_TOP_KEYS = ['id', 'date', 'title', 'text', 'hiddenWords']
DATE_REGEX = r'^\d{4}-\d{2}-\d{2}$'
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
        errors.append(f"Invalid date format: '{data['date']}' (expected YYYY-MM-DD)")

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

                # Check difficulty level
                if 'difficulty' in word_entry and word_entry['difficulty'] not in DIFFICULTY_LEVELS:
                    errors.append(f"{prefix}: Invalid difficulty '{word_entry['difficulty']}'")

                # Check clues
                if 'clues' in word_entry:
                    clues = word_entry['clues']
                    if not isinstance(clues, list) or len(clues) != 3:
                        errors.append(f"{prefix}: 'clues' must be a list of 3 items")
                    else:
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
    # Extract date from filename (expecting YYYY-MM-DD.json)
    base = os.path.basename(filename)
    match = re.match(r"(\d{4}-\d{2}-\d{2})", base)
    file_date = match.group(1) if match else None
    json_date = data.get('date')
    if file_date and json_date:
        file_date_comp = file_date.replace('-', '')
        json_date_comp = json_date.replace('-', '')
        if file_date_comp != json_date_comp:
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
