#!/bin/bash
# Validate all batch-generated JSON files
# Usage: ./scripts/validate_batch.sh [pattern]
# Example: ./scripts/validate_batch.sh "12*.json"   (all day-12 files)
#          ./scripts/validate_batch.sh "0112.json"   (single file)
# Default: validates all *.json files in puzzles/daily/mmdd/

PATTERN="${1:-*.json}"
VALIDATOR="assets/data/json_validator.py"

# Support new directory structure: check puzzles/daily/mmdd/ first, then assets/data/ fallback
if ls assets/data/puzzles/daily/mmdd/$PATTERN 1>/dev/null 2>&1; then
    SEARCH_DIR="assets/data/puzzles/daily/mmdd"
else
    SEARCH_DIR="assets/data"
fi

echo "🔍 Validating files matching: $PATTERN  (in $SEARCH_DIR)"
echo "═══════════════════════════════════════════"

count=0
passed=0
failed=0

for file in $SEARCH_DIR/$PATTERN; do
    if [ -f "$file" ]; then
        count=$((count + 1))
        filename=$(basename "$file")
        echo -n "[$count] $filename ... "

        if python "$VALIDATOR" "$file" > /dev/null 2>&1; then
            echo "✅ PASSED"
            passed=$((passed + 1))
        else
            echo "❌ FAILED"
            failed=$((failed + 1))
        fi
    fi
done

echo "═══════════════════════════════════════════"
echo "📊 Total: $count | Passed: $passed | Failed: $failed"

if [ $failed -eq 0 ] && [ $count -gt 0 ]; then
    echo "✅ All files validated successfully!"
    exit 0
else
    exit 1
fi
