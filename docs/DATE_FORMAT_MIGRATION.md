# Date Format Migration: YYYY-MM-DD → MM-DD

## Summary

Migrated ClueChain from year-specific puzzle files (`2025-07-15.json`) to year-agnostic format (`07-15.json`). This allows 366 puzzles to repeat annually without year-specific content.

## Changes Made

### 1. File Renaming ✅
- All JSON files renamed from `YYYY-MM-DD.json` to `MM-DD.json`
- 22 existing files migrated (all July 2025 puzzles)
- Date field inside each JSON updated from `"2025-07-15"` to `"07-15"`

**Before:**
```
assets/data/2025-07-01.json
assets/data/2025-07-02_Sedaris.json
...
```

**After:**
```
assets/data/07-01.json
assets/data/07-02_Sedaris.json
...
```

### 2. Code Updates ✅

#### `js/game-controller.js`
- **Removed:** Hybrid recycling system (lines 408-440)
- **Changed:** Date matching logic to use MM-DD format
- **Before:** Complex year-mapping logic to recycle 2025 content
- **After:** Simple MM-DD string matching

```javascript
// NEW CODE (simplified)
const month = String(currentDate.getMonth() + 1).padStart(2, '0');
const day = String(currentDate.getDate()).padStart(2, '0');
const formattedDate = `${month}-${day}`;

selectedParagraph = allParagraphs.find(paragraph => {
  return paragraph.date === formattedDate;
});
```

#### `assets/data/index.json`
- Updated all file paths from `2025-07-XX.json` to `07-XX.json`

### 3. Script Updates ✅

#### `scripts/generate_cluechain_json.py`
- Changed default date format from `%Y-%m-%d` to `%m-%d`
- Updated all documentation strings
- Modified filename generation to use MM-DD

**Before:**
```python
date = datetime.now().strftime("%Y-%m-%d")
```

**After:**
```python
date = datetime.now().strftime("%m-%d")
```

### 4. Documentation Updates ✅

Updated the following files:
- `CLAUDE.md` - Added content format section
- `scripts/README.md` - Updated date format examples
- `docs/SETUP_GUIDE.md` - Updated all command examples
- `docs/DATE_FORMAT_MIGRATION.md` (this file)

## Leap Year Handling

- `02-29.json` can be created and will be available
- On non-leap years, the date Feb 29 doesn't exist, so the puzzle is naturally skipped
- No special code needed for leap year handling

## Benefits

1. **Simplified Logic:** Removed 30+ lines of hybrid recycling code
2. **Better Performance:** No date mapping calculations needed
3. **Clearer Intent:** File naming matches actual usage pattern
4. **Easier Maintenance:** Only need 366 puzzles maximum
5. **Future-Proof:** Works indefinitely without year updates

## Migration Verification

To verify the migration worked:

1. **Check file listing:**
```bash
ls assets/data/*.json | head
# Should show: 07-01.json, 07-02_Sedaris.json, etc.
```

2. **Verify JSON content:**
```bash
cat assets/data/07-01.json | grep '"date"'
# Should show: "date": "07-01"
```

3. **Test loading:**
- Start local server: `python3 -m http.server`
- Open http://localhost:8000
- Navigate to July dates using calendar
- Verify puzzles load correctly

## Breaking Changes

### What Changed
- **File names:** All data files use MM-DD format
- **Date field:** JSON date property is now MM-DD string
- **Hybrid recycling:** Removed completely

### What Stayed the Same
- Game functionality unchanged
- UI/UX identical
- LocalStorage keys unchanged (backward compatible)
- No impact on guest mode or authentication

## Future Content Creation

When creating new puzzles:

```bash
# Use MM-DD format for dates
python scripts/generate_cluechain_json.py \
  --file my_paragraph.txt \
  --title "My Puzzle" \
  --date 11-20

# Output: assets/data/11-20_My_Puzzle.json
```

## Rollback Plan

If needed to rollback:

```bash
# 1. Rename files back
cd assets/data
for file in ??-*.json; do
  newname="2025-$file"
  mv "$file" "$newname"
done

# 2. Update date fields inside JSONs
for file in 2025-*.json; do
  mmdd=$(echo "$file" | grep -oE '[0-9]{2}-[0-9]{2}')
  sed -i "s/\"date\": \"${mmdd}\"/\"date\": \"2025-${mmdd}\"/" "$file"
done

# 3. Restore game-controller.js from git
git checkout HEAD -- js/game-controller.js

# 4. Restore index.json
git checkout HEAD -- assets/data/index.json
```

## Timeline

- **Migration Date:** 2026-02-13
- **Files Migrated:** 22 July puzzles
- **Code Changes:** 3 files
- **Documentation Updates:** 4 files
- **Breaking Changes:** None (backward compatible)

## Next Steps

1. ✅ Test game with existing July puzzles
2. ✅ Verify date navigation works
3. 🔲 Create puzzles for remaining months (August-June)
4. 🔲 Update index.json as new puzzles are added
5. 🔲 Consider automation for index.json updates

## Notes

- The old hybrid recycling approach was clever but unnecessary
- MM-DD format is standard for recurring annual events
- This aligns with how most daily puzzle games work (Wordle, Crosswords, etc.)
- Database schema (when implemented) should also use MM-DD for game_scores/activities
