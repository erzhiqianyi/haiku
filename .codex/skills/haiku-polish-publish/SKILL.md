---
name: haiku-polish-publish
description: Review, polish, annotate readings for, and publish Japanese haiku drafts for itsuki's haiku website. Use when the user provides a haiku draft, dated haiku note, rough 5-7-5 text, or asks for 俳句润色, 俳句添削, five style variants, automatic ruby generation, writing haiku source files, updating generated site data, preparing a deployable static page, or committing/publishing to https://haiku.erzhiqian.cc/.
---

# Haiku Polish Publish

## Overview

Use this skill for itsuki's personal haiku site workflow: critique a draft as a haiku reviewer, propose five distinct polished versions, wait for the user's selection, then write the selected version into the site source and generated metadata.

## Project Shape

The repo is expected to look like:

```text
public/content/haiku/source/YYYY/MM/DD.md
public/content/haiku/generated/itsuki-haiku.json
public/content/haiku/generated/YYYY/MM.json
public/index.html
```

Source files are intentionally simple. Each poem block is:

```text
Location

line 1
line 2
line 3
```

One date file may contain multiple blocks separated by a blank line.

Users should write plain text drafts. Codex is responsible for adding full-line ruby source notation to the location and every final haiku line, such as `{東京駅|とうきょうえき}` and `{万緑や風の匂ひ|ばんりょくやかぜのにおい}`.

## Required Workflow

1. Parse the user's draft date, location, and three haiku lines.
2. Review before editing in Chinese, with professional haiku criteria: seasonal word, form/rhythm, cut/pause, image and scene, diction, grammar/orthography, originality, and余白.
3. Give concrete revision advice in Chinese, including what to preserve, what to weaken, and the main editing direction.
4. Propose exactly five versions with distinct styles:
   - 原句尊重: minimal correction, preserves the draft's center.
   - 古典寄り: more traditional diction or grammar.
   - 現代口語: natural contemporary phrasing.
   - 写生重視: concrete visual observation.
   - 余韻重視: quieter, more suggestive ending.
5. For each version, include the location and three lines with full-text ruby notation using `{表示全文|ぜんぶのよみ}` (including kana already present), `中文解释`, `优化点`, suggested `kigo`, `keyword`, `bgColor`, and `theme`.
6. Stop and ask the user to choose one version before editing files. Do not write project files at the review stage.
7. After the user selects a version, write it to the date source file and update the generated index plus the relevant month JSON. Derive `season` from the poem date; never ask the user to supply it.
8. Validate the page data and, if a preview server is available, verify browser rendering.
9. Commit and push only when the user explicitly asks to commit, submit, publish, deploy, or says 提交/发布. Cloudflare deployment is expected to follow from Git deployment to `https://haiku.erzhiqian.cc/`.

## Review Standards

Load `references/review-standards.md` when drafting critique or five variants.

Use Chinese for critique, explanation, and recommendations. Use Japanese for haiku candidate text. Preserve intentional nonstandard text only when it adds voice; otherwise suggest natural Japanese.

Make the critique professional and specific, but keep it readable. The user should understand why each revision works and still be able to choose quickly.

Do not ask the user to add furigana manually. Add exactly one ruby annotation for the location and for each complete haiku line in every candidate version and in the final file: `{表示全文|その全文のかなよみ}`. The reading must cover every character in the text, including kana, particles, punctuation, and obvious everyday kanji; do not split it into per-kanji annotations. Keep the displayed text in its intended kanji/kana form and put its full hiragana reading on the right side of `|`.

### Ruby Rendering Contract

The source and generated JSON preserve one complete ruby annotation per location or line. The renderer uses that complete reading to place ruby beside each kanji run separated by kana, so `{夏の朝|なつのあさ}` renders as `夏／なつ` and `朝／あさ`. A line written only in kana renders without redundant ruby. Do not pre-split final source into per-kanji annotations: the full-line form is the durable content contract and supports regeneration, accessibility labels, and fallback rendering.

Generate these readings as part of the skill workflow; never ask the user to supply them and never defer pronunciation inference to the browser. Before landing a selected poem, verify the location and all three lines against the intended Japanese reading, including historical kana or place-name readings. `regenerate_generated.py` must reject missing or partial annotations.

The published site exposes one persistent `読み` setting backed by the same local-storage key on every page. Generated markup must use `reading-ruby` on every kanji run in locations, haiku lines, and kigo-library explanations, while keeping the full-line source annotation unchanged. Kigo title ruby and explicit reading labels or card readings are reading UI; mark them with `reading-ruby` or `reading-detail` so the same setting controls them. The setting is visible by default, may be hidden by the reader, and applies across the homepage, archive, individual poem, kigo, and location pages. Do not infer readings in the browser. After frontend changes, verify both states across page navigation and confirm that hiding readings removes only `rt` and explicit reading UI, not displayed text.

Always run `regenerate_generated.py` after source edits. It validates that every non-empty source line is a complete ruby annotation and preserves existing visual metadata when only ruby readings change.

## Metadata

Generate:

- `season`: the season of the poem date, generated deterministically from the date boundary contract below.
- `kigo`: the reviewed seasonal word exactly as it appears in the three displayed lines, or `null` when no reliable seasonal word is present. Do not infer a kigo from the date, location, general mood, or the one-character keyword.
- `keyword`: one kanji, usually an image/emotion core rather than a literal noun.
- `bgColor`: soft, low-saturation hex color.
- `theme`: `light` unless the poem's scene is night, darkness, isolation, or heavy shadow.
- `bgColor` and `theme` must keep readable contrast. If `theme` is `dark`, use a genuinely dark background for light text. If `theme` is `light`, use a pale background for dark text. `validate_generated_site.py` rejects weak contrast before publishing.

### Date Season Contract

Keep `season` separate from the seasonal classification of `kigo`. `season` records when the poem was written; `kigo` records the seasonal word actually used in the poem. They may differ and neither field overrides the other.

Derive `season` from the ISO date with the deterministic boundaries in `scripts/haiku_season.py`:

- `春`: February 4 through May 5.
- `夏`: May 6 through August 7.
- `秋`: August 8 through November 6.
- `冬`: November 7 through February 3.

Every generated poem object must contain exactly one of `春 / 夏 / 秋 / 冬` in `season`. Do not preserve a stale stored value during regeneration; recalculate it from `date`. Before publishing, run `validate_generated_site.py`, which checks every generated poem against the same boundary function.

### Kigo Library Contract

Treat `public/content/haiku/kigo-library.json` as the site's canonical kigo reference library. When a selected poem introduces a kigo that is not already present, add the exact displayed kigo to both `public/content/haiku/kigo-seasons.json` and the library before regenerating pages. Never substitute a broader or similar seasonal word merely to reuse an existing entry.

Every library entry must include a reading, its traditional kigo season, an original concise explanation, when the word is effective in a haiku, at least three concrete associations, and full hiragana readings for each of those displayed texts. A famous haiku is optional. Include one only after verifying the exact text, author, complete hiragana readings for both the displayed haiku and author name, and a durable HTTPS source; never generate or attribute a plausible-sounding example. Follow the schema and editorial rules in [references/kigo-library.md](references/kigo-library.md).

The poem's date-derived `season` and the library entry's traditional kigo `season` remain separate facts. For example, a poem written in August may contain an autumn kigo. Do not rewrite either value to make them agree.

### Location Map Contract

Treat `public/content/haiku/location-map.json` as the canonical geospatial metadata for poem locations. Every location placed on the map must include `lat`, `lng`, `precision`, and the full Japanese `prefecture` name. Use `東京都`, `京都府`, `大阪府`, `北海道`, or a name ending in `県`; do not store broad regions such as `関東`, `東海`, or `関西`.

Keep the poem's displayed location concise. Do not prefix `東京都` or another prefecture to the source poem merely for grouping. The page generator writes `public/content/haiku/generated/locations.json`, groups its data by prefecture, calculates each prefecture's poem count, and embeds the same dataset in the map page. Abstract places that should not be pinned to a stable coordinate may remain absent from `location-map.json` and appear in the unplaced index.

Keep the location portal in two crawlable modes: `/location/` is the interactive map, while `/location/list/` is a standalone, server-rendered list grouped by prefecture. Link the modes with real `<a href>` elements, give each page its own title, description, canonical URL, and structured data, and include both canonical URLs in the sitemap. The list page must expose every location page through ordinary HTML links and must remain useful without loading the map JavaScript.

When landing or correcting a location, follow the schema and precision rules in [references/location-map.md](references/location-map.md). Regeneration and `validate_generated_site.py` must succeed before publishing.

## Landing Selected Version

Use `scripts/add_selected_haiku.py` after the user selects. Pass the location and final three lines with Codex-generated full-text ruby notation, and metadata.

Example:

```bash
python3 .codex/skills/haiku-polish-publish/scripts/add_selected_haiku.py \
  --repo /Users/itsuki/AI/haiku \
  --date 2026-05-24 \
  --location '{東京駅|とうきょうえき}' \
  --line '{東京駅|とうきょうえき}' \
  --line '{小さき手を振る|ちいさきてをふる}' \
  --line '{夏曇|なつぐもり}' \
  --kigo 夏曇 \
  --keyword 手 \
  --bg-color '#e6e8e4' \
  --theme light
```

The script appends to `source/YYYY/MM/DD.md`, derives `season`, inserts the poem into the relevant `generated/YYYY/MM.json`, updates the `generated/itsuki-haiku.json` index, and keeps the site deployable. Regenerate JSON from daily source before publishing when many edits have accumulated.

After running it, validate:

```bash
node --check public/assets/js/haiku-renderer.js
node --check public/assets/js/haiku-explorer.js
python3 -m json.tool public/content/haiku/generated/itsuki-haiku.json >/dev/null
python3 .codex/skills/haiku-polish-publish/scripts/validate_generated_site.py --repo /Users/itsuki/AI/haiku
```

Before publishing, regenerate generated data from daily source. This writes `generated/itsuki-haiku.json` as an index and writes the month files under `generated/YYYY/MM.json`:

```bash
python3 .codex/skills/haiku-polish-publish/scripts/regenerate_generated.py --repo /Users/itsuki/AI/haiku
```

If it reports incomplete ruby or missing metadata, correct the source poem first; then add any missing `kigo`, `keyword`, `bgColor`, and `theme` through the selected-version workflow. Pass `--kigo none` only after review confirms that the poem has no reliable seasonal word; this writes JSON `null`.

If publishing, inspect `git status --short`, stage only relevant files, commit with a clear message, push, then report that deployment should update `https://haiku.erzhiqian.cc/`.
