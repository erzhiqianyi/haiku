# 俳句内容编写与维护说明

现在项目分成三层：

- 原始写作文件：`public/content/haiku/source/YYYY/MM/DD.md`
- 页面数据：`public/content/haiku/generated/itsuki-haiku.json` 和 `public/content/haiku/generated/YYYY/MM.json`
- 静态发现页：`public/archive/`、`public/haiku/`、`public/kigo/`、`public/location/` 和 `public/sitemap.xml`

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
        page-manifest.json
        2026/
          04.json
          06.json
      kigo-seasons.json
      location-map.json
  archive/
  haiku/
  kigo/
  location/
  sitemap.xml
  robots.txt
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

站点顶部的「読み」设置默认显示汉字读音，读者可以关闭，并会在首页、目录、单句、季语和地点页之间保持选择。这个开关只控制页面中的 `<rt>` 显示；源 Markdown 与生成 JSON 始终保留完整读音，不能因为默认隐藏或读者关闭而删掉注音数据。

## AI 生成字段

Codex 会根据每首俳句的地点和正文生成页面需要的视觉字段：

```json
{
  "season": "秋",
  "kigo": null,
  "keyword": "雨",
  "bgColor": "#dfe9ec",
  "theme": "light"
}
```

生成原则：

- `season` 根据作句日期自动生成，使用俳句季节的固定边界：春 2月4日—5月5日、夏 5月6日—8月7日、秋 8月8日—11月6日、冬 11月7日—2月3日。
- `kigo` 是经审校、且实际出现在三句正文中的季语；没有可靠季语时必须为 `null`。它不从日期、地点、氛围或 `keyword` 猜测。
- `keyword` 用一个汉字表达意境核心。
- `bgColor` 用柔和、低饱和背景色。
- `theme` 只在夜、孤独、夕暗、深色水面等低明度场景用 `dark`。

新增或修改原始 Markdown 后，让 Codex 在发布前重新读取 `source` 日文件，并更新 `generated/itsuki-haiku.json` 以及对应月份 JSON。生成脚本会从日期重新计算 `season`，校验所有地点和句子均为完整读音标记，并校验非空 `kigo` 确实出现在正文中；只更新读音时，原有的 `kigo / keyword / bgColor / theme` 会被保留。

发布前可运行：

```bash
python3 .codex/skills/haiku-polish-publish/scripts/regenerate_generated.py --repo /Users/itsuki/AI/haiku
```

该命令会同时生成：

- 保留原有全屏阅读体验的首页数据。
- 每页 20 首、每首一行的分页目录。
- 每首俳句独立 URL，以及前后句导航。
- 按季语和地点聚合的静态页面。
- 四季流转式季语查询页，以及按区域切换、显示句数聚合提示的地点地图。
- canonical、页面级 JSON-LD、`robots.txt` 和 XML sitemap。

生成后可运行完整站点校验：

```bash
python3 .codex/skills/haiku-polish-publish/scripts/validate_generated_site.py --repo /Users/itsuki/AI/haiku
```

校验器会逐首检查 `season` 是否存在并与日期边界一致，同时检查标题和 canonical 唯一性、详情页结构化数据、站内链接以及 sitemap 覆盖。

`public/content/haiku/kigo-seasons.json` 维护季语本身的春夏秋冬归属；它与按作句日期生成的 `season` 是两个独立概念。首页先按日期季节筛选，再把该季节记录中实际存在的季语作为二级选项。`public/content/haiku/location-map.json` 只保存能够可靠定位的地点坐标、精度和区域；“街角”“部屋”等不应被强行定位的地点继续以文字索引展示。地图初始只打开句数最多的区域，通过区域按钮切换，并把邻近地点聚合为带句数的气泡。

如果脚本提示缺少 metadata，说明某首源俳句还没有 `kigo / keyword / bgColor / theme`，需要先由 Codex 补齐再发布。季语审校记录见 `docs/kigo-audit.md`。

`generated/itsuki-haiku.json` 是索引文件，只保存站点信息和月份列表。具体作品数据在 `generated/YYYY/MM.json` 里。

## 详情页私信表单

每首俳句的详情页都可以生成“この句へひとこと”表单。它是发给作者的非公开私信，不是公开评论区；访客姓名和回复邮箱均可不填，留言最多 1000 字。

发送链路为：

```text
详情页表单 → /api/feedback → Cloudflare Turnstile 验证 → Resend → 作者邮箱
```

`functions/api/feedback.js` 是 Cloudflare Pages Function。它检查同源请求、字段长度、隐藏诱饵字段和 Turnstile 验证结果，再使用纯文本邮件转发。收件邮箱和密钥不能放进 `public/` 或浏览器 JavaScript。

在 Cloudflare Pages 项目的 Settings → Variables and Secrets 中配置：

- `RESEND_API_KEY`：Resend API Key，使用 Secret。
- `FEEDBACK_FROM_EMAIL`：Resend 已验证域名下的发件地址。
- `FEEDBACK_TO_EMAIL`：作者收件地址，使用 Secret。
- `TURNSTILE_SECRET_KEY`：Turnstile Secret Key，使用 Secret。

Turnstile 的 Site Key 本来就是公开值，将它写入 `public/content/haiku/generated/site.json` 的 `turnstileSiteKey`，再重新生成页面。没有 Site Key 时表单仍会展示，但按钮保持禁用并提示“送信の準備中”。如果暂时不希望展示表单，把 `feedbackEnabled` 改为 `false` 后重新生成。

本地需要通过 Wrangler 测试 Function 时，可复制 `.dev.vars.example` 为不会提交的 `.dev.vars` 并填入测试值。正式部署前还需要在 Resend 验证发件域名，并分别给 Preview 和 Production 环境配置变量；收件地址变更无需重新生成静态页面。

## URL 与 SEO 字段

每次重建会为俳句按日期和当日顺序生成稳定地址，例如：

```text
/haiku/2026-08-27-1/
```

详情页标题由首句、地点和日期共同组成；描述中包含完整句文、日期、地点和经审校的季语。`keyword` 仍只是页面背景使用的一个汉字，不作为 SEO 关键词。搜索主题来自页面上真实可见的句文、季语、地点和内部链接；不生成 `meta keywords`。

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
