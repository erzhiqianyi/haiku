# Design QA

## Comparison target

- Source visual truth: `/Users/itsuki/AI/haiku/design.html`
- Source captures: `/tmp/haiku-design-qa/design-reference-1440x900.png`, `/tmp/haiku-design-qa/design-reference-poem-1440x900.png`, `/tmp/haiku-design-qa/design-reference-mobile-poem-390x844.png`
- Implementation: `http://127.0.0.1:8799/`
- Implementation captures: `/tmp/haiku-design-qa/implementation-desktop-intro-1440x900.png`, `/tmp/haiku-design-qa/implementation-desktop-poem-1440x900.png`, `/tmp/haiku-design-qa/implementation-mobile-poem-390x844.png`
- Combined comparison evidence: `/tmp/haiku-design-qa/comparison-desktop-intro.png`, `/tmp/haiku-design-qa/comparison-desktop-poem.png`, `/tmp/haiku-design-qa/comparison-mobile-poem.png`

## Normalization

- Desktop CSS viewport: 1440 x 900; both source and implementation captures are 1425 x 891 pixels after the in-app browser excludes its scrollbar/chrome area.
- Mobile CSS viewport: 390 x 844; both source and implementation captures are 375 x 812 pixels after the same browser exclusion.
- Density: source and implementation were captured in the same browser at the same scale; no density conversion was needed.
- States: collection cover, first light poem, second dark poem, and first poem at the mobile breakpoint.

## Findings

No actionable P0, P1, or P2 visual differences remain.

- Fonts and typography: Shippori Mincho, Noto Serif JP, and Space Mono match the reference hierarchy. Display size, ruby scale, line height, letter spacing, and line offsets match at desktop and mobile.
- Spacing and layout rhythm: full-height snap leaves, fixed chrome, content frame, staggered lines, inline seasonal-word underline, right rail, and mobile padding align with the intended reading behavior.
- Colors and visual tokens: poem background and dark theme come from the existing JSON. Light-theme accents are derived from each poem background and dark themes use the reference warm accent. Contrast remains readable.
- Image quality and asset fidelity: the design uses typographic ghost keywords and a subtle paper-grain layer rather than photographic content. Both are reproduced without placeholder imagery.
- Copy and content: collection title, count, dates, location, poem text, author links, and readings use the repository's real generated data.
- Metadata behavior: every generated poem now has a reviewed `kigo` field. Reviewed strings render with the label `季語`; poems with `kigo: null` fall back to the durable one-character `keyword` under `けふの一字`.

## Focused region comparison

- Cover focus: title size, title spacing, subtitle, poem count, fixed wordmark, signature, and right rail.
- Poem focus: location/date row, all three ruby lines, staggered margins, seasonal-word underline, ghost keyword, and metadata marker.
- Mobile focus: 390 x 844 first-poem composition, rail visibility, safe edge spacing, ghost keyword crop, and footer signature.

## Interaction and runtime checks

- Tested right-rail navigation and active-item tracking.
- Tested Arrow Down and Home keyboard navigation.
- Tested music play and stop states with updated accessible labels.
- Tested automatic light/dark theme switching across consecutive poems.
- Checked the browser console after interaction: no errors.
- Confirmed the Google tag script remains present with measurement ID `G-QWHNC8JJ2Q`.

## Comparison history

1. Initial implementation had a smaller desktop cover title. The cover typography was changed to the reference clamp/weight/spacing, and poem lines were restored to stretch across the reference content frame. Post-fix evidence: `comparison-desktop-intro.png` and `comparison-desktop-poem.png`.
2. Initial implementation inferred seasonal terms in browser code. That inference was removed. A later corpus review added durable `kigo` data to every poem record, with `null` for poems without a reliable seasonal word; the renderer now consumes only that reviewed data.
3. The first light poem initially used the default brown accent. Accent color is now derived from the poem background, matching the reference's blue-green treatment while preserving warm dark-theme accents. Post-fix evidence: `comparison-desktop-poem.png` and `comparison-mobile-poem.png`.
4. The underline was initially implemented as a fixed decoration beneath line three. It now marks the reviewed `kigo` wherever that text occurs in the three poem lines; `kigo: null` produces no poem-text underline.

## Kigo follow-up

- Corpus decisions, ambiguous readings, multiple-season-word choices, and date/season mismatches are recorded in `docs/kigo-audit.md`.

final result: passed
