# 俳句内容编写与维护说明

现在项目分成两层：

- 原始写作文件：`public/content/haiku/source/YYYY/MM/DD.md`
- 页面渲染文件：`public/content/haiku/generated/itsuki-haiku.json` 和 `public/content/haiku/generated/YYYY/MM.json`

你平时只维护 `source` 里的原始 Markdown。`kigo / keyword / bgColor / theme` 不写在原始文档里，由 Codex 读取原文、审校季语后生成到 JSON。假名标注也由 Codex 在润色和落地时生成，草稿不用手动写。

## 目录结构

```text
public/
  content/
    haiku/
      source/
        2026/
          04/
            02.md
            06.md
          06/
            10.md
      generated/
        itsuki-haiku.json
        site.json
        2026/
          04.json
          06.json
```

## 原始文档格式

每天一个文件。每首俳句是一组四行：

```md
舎人公園

雨水や
松葉の先に
しづく満つ
```

第一行是地点。空一行后写三行俳句。

一天内有多首时，继续追加下一组：

```md
舎人公園

雨水や
松葉の先に
しづく満つ

見沼代親水公園

春の水
橋影ゆれて
鳥遠し
```

文件路径提供日期：

```text
public/content/haiku/source/2026/06/10.md
```

页面发布前会从路径生成 `2026-06-10`。

## 假名标注

用户草稿直接写普通文本即可：

```md
万緑や
```

Codex 在指导、候选版本和最终落地时负责补成：

```md
{万緑や風の匂ひ|ばんりょくやかぜのにおい}
```

每个地点和每句俳句各使用一个完整标记；右侧读音覆盖整段文字，包括已经是平假名的部分。页面渲染时会自动按“汉字段 + 相邻假名”紧凑排版，例如：

```html
<ruby>万緑<rt>ばんりょく</rt></ruby>や<ruby>風<rt>かぜ</rt></ruby>の<ruby>匂ひ<rt>におい</rt></ruby>
```

纯假名的句子不会重复显示读音。不要把源文件拆成逐字标记；完整标记是后续生成 JSON、无障碍文本与渲染回退的统一数据格式。

## AI 生成字段

Codex 会根据每首俳句的地点和正文生成页面需要的视觉字段：

```json
{
  "kigo": null,
  "keyword": "雨",
  "bgColor": "#dfe9ec",
  "theme": "light"
}
```

生成原则：

- `kigo` 是经审校、且实际出现在三句正文中的季语；没有可靠季语时必须为 `null`。它不从日期、地点、氛围或 `keyword` 猜测。
- `keyword` 用一个汉字表达意境核心。
- `bgColor` 用柔和、低饱和背景色。
- `theme` 只在夜、孤独、夕暗、深色水面等低明度场景用 `dark`。

新增或修改原始 Markdown 后，让 Codex 在发布前重新读取 `source` 日文件，并更新 `generated/itsuki-haiku.json` 以及对应月份 JSON。生成脚本会校验所有地点和句子均为完整读音标记，并校验非空 `kigo` 确实出现在正文中；只更新读音时，原有的 `kigo / keyword / bgColor / theme` 会被保留。

发布前可运行：

```bash
python3 .codex/skills/haiku-polish-publish/scripts/regenerate_generated.py --repo /Users/itsuki/AI/haiku
```

如果脚本提示缺少 metadata，说明某首源俳句还没有 `kigo / keyword / bgColor / theme`，需要先由 Codex 补齐再发布。季语审校记录见 `docs/kigo-audit.md`。

`generated/itsuki-haiku.json` 是索引文件，只保存站点信息和月份列表。具体作品数据在 `generated/YYYY/MM.json` 里。

## 润色与发布 Skill

草稿阶段可以直接把日期、地点和俳句草稿发给 Codex，并要求使用 `$haiku-polish-publish`。

仓库内的 skill 副本位于 `.codex/skills/haiku-polish-publish/`；个人 Codex 安装副本可从这里同步到 `~/.codex/skills/haiku-polish-publish/`。

流程是：

1. Codex 先从专业俳句评审角度，用中文细分季语、定型、切れ、写生、措辞、余白等问题。
2. Codex 给出具体修改建议。
3. Codex 给出五种风格版本；每个版本都包含中文解释、优化点，并在需要时补假名标注。
4. 你选择一个版本。
5. Codex 写入 `source/YYYY/MM/DD.md`，更新 `generated/itsuki-haiku.json` 和对应月份 JSON。
6. 需要发布时，再让 Codex 提交并推送 Git，站点部署到 `https://haiku.erzhiqian.cc/`。

## 首页数据源

首页通过 `public/index.html` 的 `data-haiku-source` 指向生成文件：

```html
<body data-haiku-source="content/haiku/generated/itsuki-haiku.json">
```
