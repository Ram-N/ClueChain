## 🤖 AI Agent Technical Specification and Execution Prompt

This document specifies the exact instructions, constraints, and required output format for the 'ClueChain JSON and Hints Generator' task. The LLM must strictly adhere to all rules, formatting, and constraints detailed below.

### 🎯 Role and Goal

**Role:** ClueChain JSON and hints generator.
**Primary Goal:** To process the provided English paragraph and generate a single JSON file containing exactly ten hidden words, their difficulty, and three distinct, scored clues for each.

-----

### 📝 Input Data

The LLM will be provided with three pieces of information, one of which is mandatory:

1.  **Mandatory:** `PARAGRAPH_TEXT` (The English text from which words must be selected).
2.  **Optional:** `TITLE` (If provided, used for the JSON 'title' key).
3.  **Optional:** `DATE` (If provided, used for the JSON 'date' key; otherwise, the current date must be used).

**Example Input (for internal context, do not process):**

> *Input Paragraph: The ancient observatory, perched high upon the mountain peak, offered a profound and breathtaking vista. Astronomers utilize powerful telescopes to study distant galaxies and nebulae, meticulously recording their brightness and spectral shifts. The celestial map is always changing, a testament to the universe's dynamic nature.*
> *Input Title: Astronomical Wonders*

The input paragraph will be in a .txt file.

-----

### 📏 Constraints and Selection Rules (The Ten Hidden Words)

1.  **Quantity:** Exactly **10** single words must be selected. Not 9, not 11.
2.  **Exclusions:**
      * **NO** names or proper nouns (any capitalized word, unless it appears at the start of a sentence and is *not* a proper noun, like "The" or "Astronomers").
      * **NO** compound words (e.g., 'spaceship').
      * **NO** words containing spaces, hyphens, apostrophes, or any other punctuation.
3.  **Difficulty Balance:** The 10 selected words must represent a balanced mix of perceived difficulty: **Easy**, **Intermediate**, and **Hard**. (Aim for approximately 3-4 Easy, 3-4 Intermediate, and 2-3 Hard).
4.  **Source:** All 10 words must be present in the `PARAGRAPH_TEXT`.

-----

### 💡 Clue Generation Rules (Three Types Per Word)

For each of the 10 hidden words, exactly three unique clues must be generated, each adhering to the following type and point criteria.

| Type           | Difficulty & Style                                | Points Range | Definition and Characteristics                                                                                                                                                                    |
| :------------- | :------------------------------------------------ | :----------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Indirect**   | Hard (Lateral Thinking / Riddle Style)            | 5-7 points   | Hints through complex wordplay, subtle puns, or multi-layered interpretation. Requires lateral thinking and an "aha\!" moment. Poetic, humorous, or riddle-like. **Max one to two sentences.**    |
| **Suggestive** | Intermediate (Associative / Characteristic Style) | 3-4 points   | Hints by describing a prominent characteristic, common association, or typical function. Requires a small, simple step of deduction. Clear and concise description. **Max one to two sentences.** |
| **Straight**   | Easy (Direct Definition Style)                    | 1-2 points   | Provides a direct, literal, dictionary-style definition or a very straightforward synonym. Unambiguous and for immediate recognition. **Max one sentence.**                                       |

-----

### 🔗 Thematic Linking Rule

1.  **Identification:** Check if exactly **2 or 3** of the 10 hidden words are thematically related (e.g., all are related to 'space', 'food', or 'time').
2.  **Reciprocal Linking:** If a thematically related group of 2 or 3 is found, the `related_words` list for *each* word in that group must contain the names of the *other* words in that group.
      * *Example:* If W1, W2, and W3 are related, W1's `related_words` must be `["W2", "W3"]`, W2's must be `["W1", "W3"]`, and W3's must be `["W1", "W2"]`.
3.  **No Relation:** If no group of 2 or 3 related words is found, the `related_words` list for all 10 words must be an empty array (`[]`).

-----

### 💾 Output Format Requirements

1.  **File Naming Convention:** The final output must be presented as a single JSON object that, if saved, would be named `ClueChain-YYYY-MM-DD.json`.
      * The **YYYY-MM-DD** must use the current month and day (or the provided `DATE`).
2.  **Structure:** Adhere strictly to the JSON structure provided below.
3.  **Post-Processing List:** After the JSON block, the LLM must provide two simple, non-JSON lists for review:
      * **A List of the 10 Hidden Words.**
      * **A clear Grouping of any 2 or 3 Related Words found.**

-----

### 🖼️ Required JSON Schema

The output must strictly conform to this structure:

```json
{
  "title": "[Use TITLE from input, or 'ClueChain Challenge']",
  "date": "[YYYY-MM-DD based on current date or input DATE]",
  "hiddenWords": [
    {
      "word": "word_1",
      "difficulty": "Easy | Intermediate | Hard",
      "related_words": ["word_x", "word_y"] | [],
      "clues": [
        {
          "clue": "The indirect clue (Max 2 sentences)",
          "type": "Indirect",
          "points": 5 | 6 | 7
        },
        {
          "clue": "The suggestive clue (Max 2 sentences)",
          "type": "Suggestive",
          "points": 3 | 4
        },
        {
          "clue": "The straight clue (Max 1 sentence)",
          "type": "Straight",
          "points": 1 | 2
        }
      ]
    },
    // ... 9 more word objects ...
  ]
}
```

-----

## 🚀 Execution Instruction

**Based on all the rules and constraints above, take the following paragraph and generate the required JSON output, followed by the two non-JSON lists.**

### **PARAGRAPH\_TEXT**

> "Artificial intelligence, or **AI**, is a **branch** of **computer** science that focuses on **creating** **machines** that can **perform** tasks **requiring** **human** intelligence, such as **learning**, **reasoning**, and **problem**-**solving**. The **ultimate** **goal** is to **develop** **sophisticated** systems **capable** of independent thought and **action**."

### **TITLE**
"The Dawn of AI"


Write a Python script that will invoke an LLM. Take in a paragraph/title/date and give me back a JSON.



