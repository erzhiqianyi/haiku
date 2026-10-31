# Per-poem background images

Read after the user has chosen a final poem, before landing or publishing it. Generate a separate original image for every new poem; do not reuse a generic image across unrelated poems. No image generation is needed for the five unselected draft candidates.

## Art direction

Read the complete selected poem, reviewed kigo, and location. Translate its central observation into an understated image rather than illustrating every noun. Prefer sparse Japanese watercolor / diluted ink, muted colors, subtle paper texture, and large quiet areas. Keep the subject and season accurate (for example, two October cherry blossoms should not become a springtime tree in full bloom). These images express the poem; they are not documentary photographs of the named location.

Generate portrait art around 1024 × 1536. Keep the central and right-central reading area calm, low contrast, with important motifs away from the edges that `object-fit: cover` may crop. Reserve calm space at the top for navigation and below for links. No text, calligraphy, seals, giant kanji, UI, frames, or watermarks. Simplify the scene if details compete with the poem. Use the scene's palette while maintaining contrast with the chosen light or dark text; image darkness alone does not decide the theme.

Example prompt structure (adapt the scene for each poem):

> Standalone background art for a Japanese haiku reader, portrait 1024x1536. Sparse watercolor and diluted ink on warm ivory paper. [Poem-specific observation, season, light, and mood.] Main visual motifs near the lower and left margins, generous low-contrast negative space in the center and right for an uninterrupted vertical poem. Soft edges, restrained pigment, minimal detail. No text, lettering, calligraphy, seals, frames, or UI.

## Asset and metadata workflow

1. Use built-in image generation through imagegen, with one call per poem. Inspect the actual result for theme, simplicity, reading space, and absence of text.
2. Copy the selected image into `public/assets/images/haiku/YYYY-MM-DD-N.jpg` (or `.webp` / `.png`), where N is its same-day source order / route suffix. Optimize a web copy without deleting the generated original. Avoid overwriting an existing image unless replacement is requested; otherwise use a `-v2` suffix.
3. Record the root-relative URL in the poem's month JSON as `backgroundImage`, or pass it to `add_selected_haiku.py --background-image`. Keep personal notes and prompts out of source Markdown. The source remains four non-empty ruby-annotated lines per poem.
4. Run regeneration and site validation. Both require and validate an image reference for every poem; the add-selected script also requires an image before writing new content. The complete archive has one distinct image per poem, and site validation rejects reused image URLs. Regeneration preserves `backgroundImage` through reading and location corrections.
5. Inspect the homepage and detail page, their reading toggle, mobile crop, and desktop crop. The displayed image is decorative (`alt=""`); the actual haiku remains selectable HTML text. If browser access is blocked, say which checks were completed and which visual checks remain unverified.
6. Stage the image along with the source, month JSON, and generated pages when publication is explicitly requested. Image creation does not itself authorize commit, push, or deployment.

The archive-wide prompt set and palette conventions are recorded in `docs/haiku-backgrounds.json`. Use it as a style reference for new poems rather than copying an existing scene.
