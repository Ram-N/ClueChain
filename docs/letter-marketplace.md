# Letter Marketplace Mechanics

This document explains how the letter marketplace and letter counting system works in ClueChain, both for developers debugging the system and for end players.

## How Letter Counts Work

The letter marketplace displays tiles for each letter of the alphabet. Each tile shows a count of how many times that letter appears in the remaining hidden parts of words that haven't been found yet.

### Key Concepts

1. **Letter Counts**: The number shown on each letter tile represents how many instances of that letter are still hidden in unfound words.

2. **Zero Count Behavior**: When a letter count drops to zero, the tile turns gray, indicating there are no more instances of this letter to be found.

3. **Selected Letters**: The vowel and two consonants selected at the beginning of the game remain blue even when their count drops to zero.

4. **Purchased Letters**: Letters that have been purchased turn red and their counts are removed.

## Letter Count Logic

The letter counting system follows these rules:

### 1. Initial Count Calculation

When the game starts:
- All letters in all hidden words are counted
- The initially selected vowel and two consonants are excluded from the count
- Letters in revealed word suffixes are excluded from the count

### 2. Count Updates

Letter counts are updated when:
- A word is found (all letters in that word are removed from the count)
- A letter is purchased (all instances of that letter are removed from the count)
- A word suffix is revealed (all letters in the suffix are removed from the count)

## Examples

### Example 1: Basic Counting

If the hidden words are "cat", "dog", and "fish", the initial letter counts would be:
- a: 1
- c: 1
- d: 1
- f: 1
- g: 1
- h: 1
- i: 1
- o: 1
- s: 1
- t: 1

### Example 2: Suffix Revealing

If the hidden word is "thirst" and the suffix "st" has been revealed:
- The letters 's' and 't' from the suffix are not counted
- The letter 't' would show a count of 1 (not 0) because there are two 't's in the word - one at the beginning and one in the revealed suffix
- Only the 't' in the revealed suffix is excluded from the count
- If there were other hidden words with 't', those would also be counted

### Example 3: Multiple Occurrences

If the hidden words are "letter" and "button":
- The letter 't' would show a count of 4 (2 in "letter" and 2 in "button")
- If the player finds "letter", the count for 't' would decrease to 2
- If the player purchases the letter 't', the count would drop to 0 and the tile would turn gray

### Example 4: Initial Selection

If the player initially selects vowel 'e' and consonants 't' and 'n', and the hidden words are "letter" and "button":
- The 'e' in "letter" (1) is not counted since 'e' was selected
- The 't's in "letter" (2) are not counted since 't' was selected
- The 'n' in "button" (1) is not counted since 'n' was selected
- The tile for 't' would remain blue (selected) even though it appears in the words

## For Players

### Understanding the Letter Marketplace

As a player, here's what you need to know about the letter tiles:

- **Numbers on tiles**: Show how many of that letter remain hidden in unfound words
- **Blue tiles**: Your initially selected letters (1 vowel, 2 consonants)
- **Red tiles**: Letters you've purchased to reveal
- **Gray tiles**: Letters that no longer appear in any hidden words
- **Regular tiles**: Letters that appear at least once in the remaining hidden words

### Strategic Tips

1. **Zero Count Tiles**: If a tile has turned gray (showing no count), don't waste points purchasing it - it doesn't appear in any remaining hidden words.

2. **High Count Letters**: Letters with high counts appear frequently in the remaining hidden words and might be good candidates for purchase.

3. **Word Endings**: Remember that revealed suffixes (like "-ing", "-ly", "-er") remove those letters from the counts, which might explain why certain letter counts are lower than expected.

## For Developers

### Implementation Details

The letter counting system is implemented through several key functions:

1. `initializeLetterCounts()`: Sets up initial letter counts, excluding selected letters and revealed suffixes.

2. `updateLetterCounts(word)`: Updates counts when a word is found, removing all letters in that word from the counts.

3. `clearLetterCount(letter)`: Removes a letter entirely from the counts when purchased.

4. `updateLetterCountsForWordSuffix(wordIndex)`: Updates counts when a suffix is revealed.

5. `updateLetterCounts()` (in ui-manager.js): Updates the UI to reflect current letter counts and applies the "empty" styling to zero-count tiles.

### Debugging Letter Counts

When debugging letter count issues, check:

1. Whether the suffix detection is working correctly (using `getWordSuffix()`)
2. Whether the letter exclusion for suffixes is working (in `maskWordWithPurchases()`)
3. That letter counts are properly decremented when words are found
4. That the initial letter selection is properly excluded from counts

The console logs detailed information about suffix detection and letter count updates that can be helpful for debugging.