# Kigo Library Reference

Use this reference when adding or changing a `kigo` after the user has selected a final haiku version.

## Files and ownership

- `public/content/haiku/kigo-seasons.json` is the compact season index used to arrange the four-season portal.
- `public/content/haiku/kigo-library.json` is the canonical editorial record for readings, explanations, usage, imagery, and verified famous examples.
- Generated HTML under `public/kigo/` is output. Never edit those pages by hand.

The key in `entries` must be exactly the same string stored in a poem's `kigo` field and visibly present in one of its three lines.

## Required entry schema

Use top-level `schemaVersion: 2`. Version 2 keeps every displayed explanatory text paired with its full reading.

```json
{
  "reading": "かんゆるむ",
  "season": "春",
  "summary": "冬の厳しい寒さが少しずつほどけ、空気や水、土に春の気配が戻りはじめること。",
  "summaryReading": "ふゆのきびしいさむさがすこしずつほどけ、くうきやみず、つちにはるのけはいがもどりはじめること。",
  "usage": "早春、まだ冷えを残しながらも、日差しや風のやわらかさに季節の変化を感じた場面に使います。",
  "usageReading": "そうしゅん、まだひえをのこしながらも、ひざしやかぜのやわらかさにきせつのへんかをかんじたばめんにつかいます。",
  "imagery": [
    "ほどける冷気",
    "淡い日差し",
    "春への安堵"
  ],
  "imageryReadings": [
    "ほどけるれいき",
    "あわいひざし",
    "はるへのあんど"
  ]
}
```

Rules:

- `reading`: write the normal hiragana reading used by the displayed kigo. If multiple readings are established, put the page's primary reading here and explain the alternative briefly in `summary`.
- `season`: use the traditional haiku season, one of `春 / 夏 / 秋 / 冬 / 新年`. It is not derived from the poem date.
- `summary`: explain what the word denotes in one or two original Japanese sentences. Do not paste a dictionary or saijiki entry.
- `summaryReading`: give the complete hiragana reading of `summary`, preserving kana and punctuation in order.
- `usage`: say what kinds of observed scene or emotional turn make the kigo effective. Avoid a generic sentence that could fit every kigo.
- `usageReading`: give the complete hiragana reading of `usage`, preserving kana and punctuation in order.
- `imagery`: add at least three short, concrete associations. Mix sensory image and emotional implication when appropriate.
- `imageryReadings`: provide one complete hiragana reading for every `imagery` item, in the same order.

## Optional famous haiku

Add `famousHaiku` only when all four fields have been verified:

```json
{
  "famousHaiku": {
    "text": "夏草や兵どもが夢の跡",
    "textReading": "なつくさやつわものどもがゆめのあと",
    "author": "松尾芭蕉",
    "authorReading": "まつおばしょう",
    "sourceName": "Wikisource『芭蕉俳句全集』",
    "sourceUrl": "https://example.com/verified-source"
  }
}
```

- Prefer public-domain classical haiku and primary, library, museum, university, government, or reliable literary archive sources.
- Verify spelling and historical kana against the linked source. Do not silently combine variants from different editions.
- `textReading` and `authorReading` are required when a famous example is present. Write complete hiragana readings for the displayed haiku and author name so the global 読み setting can control them.
- A kigo page without a famous example is complete. Omission is better than an uncertain quotation or attribution.
- Keep the quote limited to one haiku per kigo page.

## Workflow

1. Confirm that the selected kigo occurs exactly in the displayed poem text.
2. Check whether the exact key already exists in both kigo files.
3. If new, research the traditional season and reading, then write the library entry in original prose.
4. Add a famous haiku only when its exact text and attribution are verified from the linked source.
5. Regenerate JSON and pages.
6. Run `validate_generated_site.py`; it enforces complete field coverage, matching season indexes, verified-source field shape, and `DefinedTerm` metadata on every generated kigo page.
