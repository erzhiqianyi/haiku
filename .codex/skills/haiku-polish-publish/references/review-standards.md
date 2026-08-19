# Haiku Review Standards

Use these criteria when reviewing and polishing drafts. Explanations should be in Chinese; candidate haiku text should be in Japanese.

## Professional Review Dimensions

- 季语与季感: Identify the kigo, its season, and whether the season word is functioning as more than a label. If the season word is weak, suggest how to let weather, light, plants, animals, or human behavior carry the season.
- 定型与节奏: Check the approximate mora rhythm. Note 5-7-5, 字余り, 字足らず, and whether the rhythm supports the emotion. Do not force exact form if the poem gains naturalness.
- 切れ与转折: Identify any cut, pause, pivot, or contrast. Distinguish between a true poetic turn and a merely grammatical line break.
- 写生与具体性: Check whether the poem presents observable image, sound, movement, light, texture, or spatial relation. Prefer concrete perception over explanation.
- 措辞与语法: Check particles, verb forms, old/new diction consistency, kana/kanji balance, and whether a phrase sounds like prose.
- 情绪处理: Check whether emotion is shown through image rather than stated directly.
- 余白与读后感: Evaluate what remains unsaid and whether the ending opens resonance.
- 独自性: Name what feels personal or fresh. If the poem is generic, suggest a more precise object or angle.
- 题材伦理与语气: For graves, death, temples, people, children, disasters, or private scenes, keep tone restrained and avoid cheap drama.
- Ruby: For every candidate, generate exactly one full-text annotation for the location and for each haiku line: `{表示全文|その全文のかなよみ}`. Include all kana, particles, punctuation, and ordinary kanji in the reading; never split annotations by character or only annotate difficult words.

## Review Output

Use this structure:

```text
评审
- 季语/季感：
- 定型/节奏：
- 切れ：
- 写生：
- 措辞：
- 余白：
- 总评：

修改建议
- 保留：
- 调整：
- 方向：

五个版本
1. 原句尊重
地点：
...
中文解释：
优化点：
keyword:
bgColor:
theme:
ruby:
```

## Five Variant Styles

1. 原句尊重: Keep location, main image, and emotional direction. Fix only what feels awkward.
2. 古典寄り: Use words like かな, けり, や, しづか, をり only when natural.
3. 現代口語: Make the poem speak plainly without becoming prose.
4. 写生重視: Emphasize observed objects, gesture, light, sound, weather.
5. 余韻重視: Choose a final line that opens resonance rather than closes meaning.

For each variant, include:

- `中文解释`: Explain the reading effect and emotional/visual result in Chinese.
- `优化点`: State the specific craft improvement, such as clearer image, better rhythm, stronger cut, less explanatory diction, richer余白, more natural grammar, or better seasonal function.
- `keyword`, `bgColor`, `theme`, and `ruby`.

End with a recommendation and direct selection prompt: `选一个版本编号，我再写入文件并生成网站数据。`
