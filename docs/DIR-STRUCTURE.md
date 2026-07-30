Proposed directory structures that stay simple for adding “learning packs” (AI, geography, etc.). 


## Recommended: everything is a “puzzle”, grouped by “collections”

Think of “Daily” and “AI Basics” as just different collections. The daily calendar is just one collection with a schedule.

```
assets/data/
  puzzles/
    daily/
      mmdd/
        0224.json
        0225.json
        0229.json
      yyyy/
        2027/
          0224.json
          0225.json

    packs/
      ai/
        basics/
          ai-001.json
          ai-002.json
      geography/
        neighbors/
          geo-nbr-001.json
      history/
        ww2/
          hist-ww2-001.json

  indexes/
    daily.json
    packs.json
```

### How serving works with this structure

* If `puzzles/daily/yyyy/2027/0224.json` exists, serve it.
* Else serve `puzzles/daily/mmdd/0224.json`.
* For learning mode, you serve by pack path and order.

### Why this scales

* Daily content and topic content share the same JSON schema.
* You can add new “collections” without inventing new directory conventions.
* You can keep IDs stable (`ai-001`, `hist-ww2-003`) even if you move files later.


### Small extra suggestion (helps later)

Add a light “manifest” file per collection so you don’t have to scan directories at runtime:

```
assets/data/indexes/daily.json
assets/data/indexes/packs/ai-basics.json
```

