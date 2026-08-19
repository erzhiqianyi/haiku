# Repository Guidelines

## Project Structure & Module Organization

This repository is a static haiku site. The published page is `public/index.html`, with styles in `public/assets/css/haiku-scroll.css` and browser logic in `public/assets/js/haiku-renderer.js`.

Haiku content has two layers:

- `public/content/haiku/source/YYYY/MM/DD.md`: human-maintained daily source files.
- `public/content/haiku/generated/`: site data consumed by the page, including `itsuki-haiku.json`, `site.json`, and monthly `YYYY/MM.json` files.

Use `templates/haiku-day.md` for new daily source examples. Keep authoring workflow details in `docs/haiku-authoring.md`; do not duplicate long process notes in this file.

## Build, Test, and Development Commands

- `python3 -m http.server 8799 --directory public`: serve the static site locally at `http://127.0.0.1:8799/`.
- `node --check public/assets/js/haiku-renderer.js`: validate JavaScript syntax.
- `python3 -m json.tool public/content/haiku/generated/itsuki-haiku.json >/dev/null`: validate the generated index JSON.
- `python3 .codex/skills/haiku-polish-publish/scripts/regenerate_generated.py --repo /Users/itsuki/AI/haiku`: rebuild generated JSON from source files before publishing.

There is no package manager manifest or bundled test runner in this repo.

## Coding Style & Naming Conventions

Use two-space indentation in HTML/CSS and four-space indentation in JavaScript, matching the existing files. Prefer plain, dependency-free browser JavaScript. Keep filenames lowercase with hyphenated names for assets, and date-based paths for haiku source files.

For haiku source blocks, use:

```md
Location

line 1
line 2
line 3
```

Use ruby source notation only where helpful for reading: `{漢字|かな}`.

## Testing Guidelines

For content changes, regenerate JSON, validate JSON, and preview the page locally. For frontend changes, run `node --check` and manually verify scrolling, background color/theme changes, ruby rendering, and mobile layout in a browser. There is no formal coverage target.

## Commit & Pull Request Guidelines

Recent history uses short messages such as `update` and date stamps like `2026-04-19`; keep commits concise but prefer clearer scopes, for example `add 2026-06-26 haiku` or `update renderer ruby handling`.

Pull requests should state what changed, list validation commands run, and include screenshots only when layout or visual behavior changed.

## Agent-Specific Instructions

When polishing or publishing haiku drafts, use `$haiku-polish-publish`. Write project files only after the user chooses a final version. Do not commit, push, or publish unless explicitly asked.
