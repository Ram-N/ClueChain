# ClueChain Skills

Custom skills for ClueChain puzzle management.

## Available Skills

### `/batch-puzzles` - Batch Puzzle Generator

Automates the complete workflow for generating 12 monthly puzzles from a multi-paragraph file.

**Usage:**
```
/batch-puzzles --file paragraphs_food.txt --category FOOD --day 13
```

Or naturally spoken:
```
batch generator paragraphs_food.txt FOOD 13
generate batch puzzles from paragraphs_food.txt, category COLORS, day 18
```

**What it does:**
1. ✅ Generates 12 JSON puzzle files (one per month)
2. ✅ Shows hidden words (Easy/Intermediate/Hard) for each as they're generated
3. ✅ Validates all generated files
4. ✅ Updates `index.json` automatically
5. ✅ Supports resume if generation fails midway

**Parameters:**
- `file`: Filename in `assets/data/library/` (required)
- `category`: Category name in UPPERCASE (required)
- `day`: Day of month 1-31 (required)

**Examples:**
```
/batch-puzzles --file paragraphs_food.txt --category FOOD --day 13
/batch-puzzles --file geography-17th.txt --category GEOGRAPHY --day 17
```

**Time:** ~6-10 minutes for 12 paragraphs

---

## How Skills Work

Skills are invoked with `/skill-name` or by speaking the parameters naturally. Claude will:
1. Parse your intent and extract parameters
2. Execute the skill's workflow
3. Report progress and results
4. Handle errors gracefully

## Adding New Skills

Create a new `.md` file in `.claude/skills/` with:
- Clear usage examples
- Parameter descriptions
- Implementation steps
- Error handling guidelines

See `batch-puzzles.md` for a complete example.
