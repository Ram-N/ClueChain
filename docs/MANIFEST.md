
* Every puzzle JSON has a unique `id`
* Daily puzzles are referenced by `MMDD` and optional `YYYY/MMDD`
* Learning packs are ordered sequences
* All puzzles share the same schema elsewhere

Below are three clean sample manifest files.

---

# 1. `indexes/daily.json`

This file defines:

* how daily fallback works
* which year overrides exist

```json
{
  "collection": "daily",
  "description": "One puzzle per calendar day. Year-specific overrides take precedence over generic MMDD.",
  "fallback": "mmdd",

  "generic_days": [
    "0101", "0102", "0103",
    "0224", "0225",
    "1231"
  ],

  "overrides": {
    "2026": ["0224"],
    "2027": ["0224", "0315"]
  }
}
```

### Serving logic:

1. Today = 2027-02-24
2. Check if `overrides["2027"]` includes `"0224"`
3. If yes → serve `puzzles/daily/yyyy/2027/0224.json`
4. Else → serve `puzzles/daily/mmdd/0224.json`

You don’t need to list all 366 generic days if they always exist. This list is optional. It’s mainly helpful for validation.

---

# 2. `indexes/packs/ai-basics.json`

Structured learning pack. Ordered progression.

```json
{
  "collection": "pack",
  "slug": "ai-basics",
  "title": "AI Foundations",
  "description": "Core AI and ML vocabulary through contextual paragraphs.",
  "difficulty": "beginner",
  "estimated_puzzles": 20,

  "puzzles": [
    {
      "id": "ai-001",
      "path": "puzzles/packs/ai/basics/ai-001.json"
    },
    {
      "id": "ai-002",
      "path": "puzzles/packs/ai/basics/ai-002.json"
    },
    {
      "id": "ai-003",
      "path": "puzzles/packs/ai/basics/ai-003.json"
    }
  ]
}
```

### Why explicit paths?

Because later you might reorganize folders. The manifest remains the source of truth.

You could also omit `path` if your convention is deterministic:
`puzzles/packs/ai/basics/{id}.json`

---

# 3. `indexes/packs/geography-neighbors.json`

This example includes optional metadata like prerequisites and tags.

```json
{
  "collection": "pack",
  "slug": "geography-neighbors",
  "title": "World Neighbors",
  "description": "Geography vocabulary and regional understanding through border-based paragraphs.",
  "difficulty": "intermediate",
  "tags": ["geography", "countries", "maps"],

  "puzzles": [
    {
      "id": "geo-nbr-001",
      "path": "puzzles/packs/geography/neighbors/geo-nbr-001.json"
    },
    {
      "id": "geo-nbr-002",
      "path": "puzzles/packs/geography/neighbors/geo-nbr-002.json"
    },
    {
      "id": "geo-nbr-003",
      "path": "puzzles/packs/geography/neighbors/geo-nbr-003.json"
    }
  ]
}
```

---

# Optional: One Master Packs Index

You may also want:

`indexes/packs.json`

```json
{
  "packs": [
    {
      "slug": "ai-basics",
      "title": "AI Foundations",
      "difficulty": "beginner"
    },
    {
      "slug": "geography-neighbors",
      "title": "World Neighbors",
      "difficulty": "intermediate"
    }
  ]
}
```

This allows your UI to list all available learning packs without scanning directories.

