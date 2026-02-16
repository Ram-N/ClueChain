#!/bin/bash
# Validate all batch-generated JSON files
# Usage: ./scripts/validate_batch.sh [pattern]
# Example: ./scripts/validate_batch.sh "*-13-FOOD-*.json"

PATTERN="${1:-*-13-*.json}"
VALIDATOR="assets/data/json_validator.py"

echo "🔍 Validating files matching: $PATTERN"
echo "═══════════════════════════════════════════"

count=0
passed=0
failed=0

for file in assets/data/$PATTERN; do
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
