#!/usr/bin/env python3
import html
import json
import math
import re
from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

from haiku_season import season_for_date


RUBY_VALUE = re.compile(r"^\{([^{}|]+)\|([^{}|]+)\}$")
KANJI_CHUNKS = re.compile(r"[\u3400-\u9fff\u3005\u3006\u30f6]+|[^\u3400-\u9fff\u3005\u3006\u30f6]+")
KANJI_ONLY = re.compile(r"^[\u3400-\u9fff\u3005\u3006\u30f6]+$")
SEASON_READINGS = {"春": "はる", "夏": "なつ", "秋": "あき", "冬": "ふゆ", "新年": "しんねん"}
ALLOWED_GENERATED_PREFIXES = (
    "about/",
    "archive/",
    "feedback/",
    "haiku/",
    "kigo/",
    "location/",
    "content/haiku/generated/locations.json",
)


def plain_text(value):
    return re.sub(r"\{([^{}|]+)\|[^{}|]+\}", r"\1", str(value or ""))


def to_hiragana(value):
    return "".join(chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character for character in str(value))


def literal_reading_candidates(value):
    normalized = to_hiragana(value)
    modernized = normalized.replace("ひ", "い").replace("ふ", "う")
    return (normalized,) if modernized == normalized else (normalized, modernized)


def compact_ruby_markup(base, reading):
    chunks = KANJI_CHUNKS.findall(str(base))
    normalized_reading = to_hiragana(reading)
    if not any(KANJI_ONLY.fullmatch(chunk) for chunk in chunks):
        return html.escape(base)

    @lru_cache(maxsize=None)
    def render_chunks(index, reading_index):
        if index == len(chunks):
            return "" if reading_index == len(normalized_reading) else None

        chunk = chunks[index]
        if not KANJI_ONLY.fullmatch(chunk):
            for expected in literal_reading_candidates(chunk):
                if not normalized_reading.startswith(expected, reading_index):
                    continue
                rest = render_chunks(index + 1, reading_index + len(expected))
                if rest is not None:
                    return f"{html.escape(chunk)}{rest}"
            return None

        for end in range(reading_index + 1, len(normalized_reading) + 1):
            rest = render_chunks(index + 1, end)
            if rest is not None:
                ruby_reading = str(reading)[reading_index:end]
                return (
                    f'<ruby class="reading-ruby">{html.escape(chunk)}'
                    f'<rt>{html.escape(ruby_reading)}</rt></ruby>{rest}'
                )
        return None

    rendered = render_chunks(0, 0)
    if rendered is not None:
        return rendered
    return f'<ruby class="reading-ruby">{html.escape(base)}<rt>{html.escape(reading)}</rt></ruby>'


def ruby_markup(value):
    source = str(value or "")
    match = RUBY_VALUE.fullmatch(source)
    if not match:
        return html.escape(source)
    return compact_ruby_markup(*match.groups())


def ruby_sentence(parts):
    rendered = []
    for part in parts:
        if isinstance(part, tuple):
            rendered.append(compact_ruby_markup(part[0], part[1]))
        else:
            rendered.append(html.escape(str(part)))
    return "".join(rendered)


def japanese_date(value):
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(value or ""))
    if not match:
        return str(value or "")
    year, month, day = (int(part) for part in match.groups())
    return f"{year}年{month}月{day}日"


def safe_segment(value):
    return str(value).strip().replace("/", "／").replace("\\", "＼")


def tag_path(kind, value):
    segment = safe_segment(value)
    return f"/{kind}/{quote(segment, safe='')}/"


def absolute_url(base_url, path):
    return f"{base_url.rstrip('/')}{path}"


def assign_routes(poems):
    date_counts = defaultdict(int)
    for poem in poems:
        date_counts[poem["date"]] += 1
        slug = f"{poem['date']}-{date_counts[poem['date']]}"
        location = plain_text(poem.get("location"))
        poem["slug"] = slug
        poem["url"] = f"/haiku/{slug}/"
        poem["locationUrl"] = tag_path("location", location)
        poem["kigoUrl"] = tag_path("kigo", poem["kigo"]) if poem.get("kigo") else None


def json_ld_markup(items):
    payload = items[0] if len(items) == 1 else items
    source = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{source}</script>'


def breadcrumb_data(base_url, items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": name,
                "item": absolute_url(base_url, path),
            }
            for index, (name, path) in enumerate(items)
        ],
    }


def breadcrumb_markup(items):
    parts = []
    for index, (name, path) in enumerate(items):
        if index == len(items) - 1:
            parts.append(f"<span>{html.escape(name)}</span>")
        else:
            parts.append(f'<a href="{html.escape(path)}">{html.escape(name)}</a><span aria-hidden="true">／</span>')
    return f'<nav class="breadcrumbs" aria-label="パンくず">{"".join(parts)}</nav>'


def page_shell(
    site_meta,
    title,
    description,
    canonical_path,
    body,
    structured_data,
    page_class="page-shell",
    og_type="website",
    extra_head="",
    extra_body="",
    body_attributes="",
):
    base_url = site_meta.get("baseUrl", "https://haiku.erzhiqian.cc").rstrip("/")
    canonical = absolute_url(base_url, canonical_path)
    cover = site_meta.get("cover", "")
    author = site_meta.get("author", "itsuki")
    analytics_id = site_meta.get("analyticsId", "G-QWHNC8JJ2Q")
    analytics = ""
    if analytics_id:
        safe_id = html.escape(analytics_id, quote=True)
        analytics = f"""
  <script async src="https://www.googletagmanager.com/gtag/js?id={safe_id}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{safe_id}');
  </script>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="author" content="{html.escape(author, quote=True)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  <meta property="og:type" content="{html.escape(og_type, quote=True)}">
  <meta property="og:url" content="{html.escape(canonical, quote=True)}">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:image" content="{html.escape(cover, quote=True)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title, quote=True)}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{html.escape(cover, quote=True)}">
  {json_ld_markup(structured_data)}
  {analytics}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400&amp;family=Shippori+Mincho:wght@400;500&amp;family=Space+Mono&amp;display=swap" rel="stylesheet">
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="/assets/css/haiku-pages.css?v=20260827-reading-switch-v1">
  <link rel="stylesheet" href="/assets/css/haiku-navigation.css?v=20260827-reading-switch-v1">
  {extra_head}
</head>
<body {body_attributes}>
  <header class="site-header">
    <a class="wordmark" href="/">樹の句帖</a>
    <nav class="site-nav" aria-label="サイト内ナビゲーション">
      <a href="/">全句帖</a>
      <a href="/archive/">句の一覧</a>
      <a href="/kigo/">季語</a>
      <a href="/location/">地図</a>
      <a href="/feedback/">感想</a>
      <a href="/about/">紹介</a>
      <button class="readings-toggle" type="button" data-readings-toggle aria-pressed="true" title="漢字の読みを隠す">読み</button>
    </nav>
  </header>
  <main class="{html.escape(page_class, quote=True)}">
{body}
  </main>
  <footer class="site-footer">
    <span>{html.escape(site_meta.get('copyright', '© itsuki'))}</span>
    <a href="https://x.com/itsuki_maer" rel="me noopener noreferrer">X @itsuki_maer</a>
  </footer>
  <script src="/assets/js/haiku-readings.js?v=20260827-readings-v1"></script>
  {extra_body}
</body>
</html>
"""


def archive_row(poem):
    lines = [ruby_markup(line) for line in poem["lines"]]
    joined = '<span class="row-divider" aria-hidden="true">／</span>'.join(lines)
    location = ruby_markup(poem["location"])
    date = html.escape(poem["date"])
    return f"""      <a class="archive-row" href="{html.escape(poem['url'], quote=True)}">
        <span class="row-poem">{joined}</span>
        <span class="row-meta"><time datetime="{date}">{html.escape(japanese_date(poem['date']))}</time><span>{location}</span></span>
      </a>"""


def pagination_markup(current, total):
    links = []
    for page in range(1, total + 1):
        path = "/archive/" if page == 1 else f"/archive/page/{page}/"
        if page == current:
            links.append(f'<span aria-current="page">{page}</span>')
        else:
            links.append(f'<a href="{path}" aria-label="{page}ページ目">{page}</a>')
    return f'<nav class="pager" aria-label="一覧のページ">{"".join(links)}</nav>'


def tag_cloud(title, items, kind):
    links = []
    for value, poems in sorted(items.items(), key=lambda item: item[0]):
        label = ruby_markup(poems[0]["location"]) if kind == "location" else html.escape(value)
        links.append(
            f'<a class="tag-link" href="{tag_path(kind, value)}"><span>{label}</span><span class="tag-count">{len(poems)}</span></a>'
        )
    return f'<section><h2><a class="inline-link" href="/{kind}/">{html.escape(title)}</a></h2><div class="tag-list">{"".join(links)}</div></section>'


def kigo_title_markup(value, entry):
    reading = entry["reading"]
    label = f"{value}（{reading}）"
    return (
        f'<ruby class="kigo-title-ruby reading-ruby" aria-label="{html.escape(label, quote=True)}">'
        f'{html.escape(value)}<rt>{html.escape(reading)}</rt></ruby>'
    )


def kigo_card(value, poems, season, entry):
    poem = poems[0]
    preview = "／".join(plain_text(line) for line in poem["lines"])
    preview_markup = '<span class="row-divider" aria-hidden="true">／</span>'.join(
        ruby_markup(line) for line in poem["lines"]
    )
    location = plain_text(poem["location"])
    reading = entry["reading"]
    search_value = " ".join((value, reading, season, preview, location, *entry["imagery"]))
    return f"""        <a class="kigo-card" href="{html.escape(tag_path('kigo', value), quote=True)}" data-kigo-search="{html.escape(search_value, quote=True)}">
          <span class="kigo-card-name"><span class="kigo-card-word">{html.escape(value)}</span><span class="kigo-card-reading reading-detail">{html.escape(reading)}</span></span>
          <span class="kigo-card-count">{len(poems):02d} 句</span>
          <span class="kigo-card-preview">{preview_markup}</span>
          <span class="kigo-card-place">{ruby_markup(poem['location'])}</span>
        </a>"""


def kigo_guide_markup(value, entry):
    imagery = "".join(
        f"<li>{compact_ruby_markup(item, reading)}</li>"
        for item, reading in zip(entry["imagery"], entry["imageryReadings"])
    )
    famous = entry.get("famousHaiku")
    season_markup = compact_ruby_markup(
        f"{entry['season']}の季語",
        f"{SEASON_READINGS[entry['season']]}のきご",
    )
    famous_markup = ""
    if famous:
        famous_markup = f"""      <figure class="kigo-famous">
        <p class="kigo-guide-label">{compact_ruby_markup('名句に見る', 'めいくにみる')}</p>
        <blockquote>{compact_ruby_markup(famous['text'], famous['textReading'])}</blockquote>
        <figcaption>
          <span>{compact_ruby_markup(famous['author'], famous['authorReading'])}</span>
          <a href="{html.escape(famous['sourceUrl'], quote=True)}" target="_blank" rel="noopener noreferrer">{compact_ruby_markup('出典', 'しゅってん')}　{html.escape(famous['sourceName'])}</a>
        </figcaption>
      </figure>"""

    return f"""    <section class="kigo-guide" aria-labelledby="kigo-guide-title">
      <div class="kigo-guide-heading">
        <p class="kigo-guide-label">Kigo note</p>
        <h2 id="kigo-guide-title">{compact_ruby_markup('季語をひらく', 'きごをひらく')}</h2>
        <p><span>{season_markup}</span><span class="reading-detail">読み　{html.escape(entry['reading'])}</span></p>
      </div>
      <div class="kigo-guide-grid">
        <section class="kigo-guide-panel">
          <p class="kigo-guide-label">{compact_ruby_markup('意味', 'いみ')}</p>
          <p>{compact_ruby_markup(entry['summary'], entry['summaryReading'])}</p>
        </section>
        <section class="kigo-guide-panel">
          <p class="kigo-guide-label">{compact_ruby_markup('いつ使うか', 'いつつかうか')}</p>
          <p>{compact_ruby_markup(entry['usage'], entry['usageReading'])}</p>
        </section>
      </div>
      <div class="kigo-imagery">
        <p class="kigo-guide-label">{compact_ruby_markup('呼び起こす景色', 'よびおこすけしき')}</p>
        <ul>{imagery}</ul>
      </div>
{famous_markup}
    </section>"""


def location_card(index, value, poems, map_entry):
    preview = "／".join(plain_text(line) for line in poems[0]["lines"])
    preview_markup = '<span class="row-divider" aria-hidden="true">／</span>'.join(
        ruby_markup(line) for line in poems[0]["lines"]
    )
    precision = "おおよその位置" if map_entry.get("precision") == "area" else "句の場所"
    return f"""        <article class="location-card" data-location-index="{index}">
          <div>
            <a class="location-card-name" href="{html.escape(tag_path('location', value), quote=True)}">{ruby_markup(poems[0]['location'])}</a>
            <span class="location-card-meta">{len(poems)}句・{precision}</span>
            <p aria-label="{html.escape(preview, quote=True)}">{preview_markup}</p>
          </div>
          <button class="map-focus" type="button" data-map-focus="{index}">地図で見る</button>
        </article>"""


def location_view_switch(current):
    map_current = ' aria-current="page"' if current == "map" else ""
    list_current = ' aria-current="page"' if current == "list" else ""
    return f"""    <nav class="location-view-switch" aria-label="場所の表示方法">
      <a href="/location/"{map_current}><span>Map</span>地図で探す</a>
      <a href="/location/list/"{list_current}><span>Index</span>一覧で探す</a>
    </nav>"""


def location_list_row(entry, prefecture):
    preview_markup = '<span class="row-divider" aria-hidden="true">／</span>'.join(
        ruby_markup(line) for line in entry["previewRuby"]
    )
    if not entry.get("mapped", True):
        precision = "言葉のまま残す場所"
    else:
        precision = "おおよその場所" if entry["precision"] == "area" else "句の場所"
    name_match = RUBY_VALUE.fullmatch(entry.get("nameRuby", ""))
    name_reading = name_match.group(2) if name_match else ""
    search_value = " ".join((entry["name"], name_reading, prefecture, entry["preview"]))
    return f"""        <article class="location-list-row" data-location-search="{html.escape(search_value, quote=True)}">
          <div class="location-list-name">
            <h3><a href="{html.escape(entry['url'], quote=True)}">{ruby_markup(entry['nameRuby'])}</a></h3>
            <span>{html.escape(precision)}</span>
          </div>
          <p class="location-list-preview">{preview_markup}</p>
          <span class="location-list-count"><strong>{entry['count']}</strong>句</span>
        </article>"""


def related_list(poems):
    if not poems:
        return '<p class="page-lead">関連する句はまだありません。</p>'
    items = []
    for poem in poems[:4]:
        first_line = ruby_markup(poem["lines"][0])
        items.append(
            f'<li><a href="{html.escape(poem["url"], quote=True)}"><span>{first_line}</span><time datetime="{html.escape(poem["date"])}">{html.escape(japanese_date(poem["date"]))}</time></a></li>'
        )
    return f'<ul class="related-list">{"".join(items)}</ul>'


def switch_item(poem, label):
    if not poem:
        return f'<span><span class="switch-label">{html.escape(label)}</span><span class="switch-poem">—</span></span>'
    first_line = ruby_markup(poem["lines"][0])
    return f'<a href="{html.escape(poem["url"], quote=True)}"><span class="switch-label">{html.escape(label)}</span><span class="switch-poem">{first_line}</span></a>'


def feedback_section(
    poem,
    title,
    site_meta,
    heading="この句へひとこと",
    lead="感じたことを、作者へそっと届けられます。内容は公開されません。",
    eyebrow="Letter",
):
    if not site_meta.get("feedbackEnabled", False):
        return "", ""

    site_key = str(site_meta.get("turnstileSiteKey", "")).strip()
    challenge = ""
    setup_note = ""
    disabled = ""
    scripts = '<script src="/assets/js/haiku-feedback.js?v=20260827-feedback-v1"></script>'
    if site_key:
        challenge = (
            f'<div class="cf-turnstile" data-sitekey="{html.escape(site_key, quote=True)}" '
            'data-action="haiku_feedback" data-theme="light"></div>'
        )
        scripts = (
            '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>\n  '
            + scripts
        )
    else:
        disabled = " disabled"
        setup_note = '<p class="feedback-setup">現在、送信の準備中です。</p>'

    return f"""      <section class="feedback-block" id="feedback" aria-labelledby="feedback-title">
        <p class="eyebrow">{html.escape(eyebrow)}</p>
        <h2 id="feedback-title">{html.escape(heading)}</h2>
        <p class="feedback-lead">{html.escape(lead)}</p>
        <form class="feedback-form" action="/api/feedback" method="post" data-feedback-form>
          <input type="hidden" name="poemPath" value="{html.escape(poem['url'], quote=True)}">
          <input type="hidden" name="poemTitle" value="{html.escape(title, quote=True)}">
          <div class="feedback-fields">
            <label><span>お名前 <small>任意</small></span><input type="text" name="name" maxlength="60" autocomplete="name"></label>
            <label><span>返信先メール <small>任意</small></span><input type="email" name="email" maxlength="254" autocomplete="email" inputmode="email"></label>
          </div>
          <label class="feedback-message">
            <span>メッセージ</span>
            <textarea name="message" rows="6" maxlength="1000" required></textarea>
            <small class="feedback-count" data-feedback-count>0 / 1000</small>
          </label>
          <label class="feedback-honeypot" aria-hidden="true">ウェブサイト<input type="text" name="website" tabindex="-1" autocomplete="off"></label>
          <div class="feedback-action">
            <div>{challenge}{setup_note}</div>
            <button type="submit"{disabled}>作者へ送る</button>
          </div>
          <p class="feedback-note">入力内容は、このメッセージの送信と返信にだけ使用します。</p>
          <p class="feedback-status" data-feedback-status role="status" aria-live="polite"></p>
        </form>
      </section>""", scripts


def write_page(public_root, relative_path, content, written):
    target = public_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    written.add(relative_path)


def cleanup_stale_pages(public_root, manifest_path, written):
    if not manifest_path.exists():
        return
    try:
        previous = set(json.loads(manifest_path.read_text(encoding="utf-8")).get("files", []))
    except (json.JSONDecodeError, OSError):
        return

    for relative_path in sorted(previous - written):
        if relative_path not in {"sitemap.xml", "robots.txt"} and not relative_path.startswith(ALLOWED_GENERATED_PREFIXES):
            continue
        target = public_root / relative_path
        if not target.is_file():
            continue
        target.unlink()
        parent = target.parent
        while parent != public_root and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def generate_site_pages(repo, poems, site_meta):
    public_root = repo / "public"
    generated_root = public_root / "content" / "haiku" / "generated"
    manifest_path = generated_root / "page-manifest.json"
    base_url = site_meta.get("baseUrl", "https://haiku.erzhiqian.cc").rstrip("/")
    page_size = max(1, int(site_meta.get("archivePageSize", 20)))
    author = site_meta.get("author", "itsuki")
    written = set()
    canonical_paths = ["/"]

    seasons_path = public_root / "content" / "haiku" / "kigo-seasons.json"
    library_path = public_root / "content" / "haiku" / "kigo-library.json"
    locations_path = public_root / "content" / "haiku" / "location-map.json"
    season_groups = json.loads(seasons_path.read_text(encoding="utf-8"))
    library_payload = json.loads(library_path.read_text(encoding="utf-8"))
    if library_payload.get("schemaVersion") != 2 or not isinstance(library_payload.get("entries"), dict):
        raise ValueError("kigo-library.json must use schemaVersion 2 and contain an entries object")
    kigo_library = library_payload["entries"]
    location_map = json.loads(locations_path.read_text(encoding="utf-8"))
    kigo_to_season = {}
    for season, values in season_groups.items():
        for value in values:
            if value in kigo_to_season:
                raise ValueError(f"Kigo appears in more than one season: {value}")
            kigo_to_season[value] = season

    if set(kigo_library) != set(kigo_to_season):
        missing = sorted(set(kigo_to_season) - set(kigo_library))
        extra = sorted(set(kigo_library) - set(kigo_to_season))
        raise ValueError(f"Kigo library mismatch; missing={missing} extra={extra}")
    for value, entry in kigo_library.items():
        required = (
            "reading",
            "season",
            "summary",
            "summaryReading",
            "usage",
            "usageReading",
            "imagery",
            "imageryReadings",
        )
        missing_fields = [field for field in required if not entry.get(field)]
        if missing_fields:
            raise ValueError(f"Kigo library entry {value} is missing fields: {missing_fields}")
        if entry["season"] != kigo_to_season[value]:
            raise ValueError(
                f"Kigo library season mismatch for {value}: {entry['season']} != {kigo_to_season[value]}"
            )
        if len(entry["imageryReadings"]) != len(entry["imagery"]):
            raise ValueError(f"Kigo library imagery reading mismatch for {value}")

    by_location = defaultdict(list)
    by_kigo = defaultdict(list)
    for poem in poems:
        by_location[plain_text(poem["location"])].append(poem)
        if poem.get("kigo"):
            by_kigo[poem["kigo"]].append(poem)

    unknown_kigo = sorted(set(by_kigo) - set(kigo_to_season))
    if unknown_kigo:
        raise ValueError(f"Add unknown kigo to kigo-seasons.json and kigo-library.json: {unknown_kigo}")

    total_pages = max(1, math.ceil(len(poems) / page_size))
    for page_number in range(1, total_pages + 1):
        start = (page_number - 1) * page_size
        page_poems = poems[start:start + page_size]
        canonical_path = "/archive/" if page_number == 1 else f"/archive/page/{page_number}/"
        relative_path = "archive/index.html" if page_number == 1 else f"archive/page/{page_number}/index.html"
        title = "句の一覧｜樹の句帖" if page_number == 1 else f"句の一覧 {page_number}ページ｜樹の句帖"
        description = f"itsukiの俳句全{len(poems)}句を、日付と場所とともに一行ずつ読む一覧。{page_number}/{total_pages}ページ。"
        tag_sections = ""
        if page_number == 1:
            tag_sections = (
                '<div class="tag-clouds">'
                + tag_cloud("季語から読む", by_kigo, "kigo")
                + tag_cloud("場所から読む", by_location, "location")
                + "</div>"
            )
        body = f"""    <p class="eyebrow">Archive</p>
    <h1 class="page-title">句の一覧</h1>
    <p class="page-lead">一句を一行にまとめ、日付と場所から辿れる目次です。各行から、その句だけを読むページへ移動できます。</p>
    <div class="archive-summary"><span>{len(poems)} HAIKU</span><span>{page_number} / {total_pages}</span></div>
    <div class="archive-list">
{chr(10).join(archive_row(poem) for poem in page_poems)}
    </div>
    {pagination_markup(page_number, total_pages)}
    {tag_sections}"""
        data = [
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": title,
                "description": description,
                "url": absolute_url(base_url, canonical_path),
                "inLanguage": "ja",
            },
            breadcrumb_data(base_url, [("樹の句帖", "/"), ("句の一覧", canonical_path)]),
        ]
        write_page(public_root, relative_path, page_shell(site_meta, title, description, canonical_path, body, data), written)
        canonical_paths.append(canonical_path)

    season_order = [season for season in ("春", "夏", "秋", "冬", "新年", "余白") if season_groups.get(season)]
    season_labels = {
        "春": ("Spring", "ほどける光"),
        "夏": ("Summer", "満ちる緑"),
        "秋": ("Autumn", "澄みゆく夜"),
        "冬": ("Winter", "静まる影"),
        "新年": ("New Year", "あらたな暦"),
        "余白": ("Unsorted", "季節を待つ言葉"),
    }
    orbit_links = "".join(
        f'<a href="#season-{html.escape(season)}" data-season-link="{html.escape(season)}" role="tab" aria-controls="season-{html.escape(season)}"><span>{html.escape(season)}</span></a>'
        for season in season_order
    )
    season_sections = []
    for season in season_order:
        english, phrase = season_labels[season]
        cards = "\n".join(
            kigo_card(value, by_kigo[value], season, kigo_library[value])
            for value in season_groups[season]
            if value in by_kigo
        )
        poem_count = sum(len(by_kigo[value]) for value in season_groups[season] if value in by_kigo)
        season_sections.append(f"""      <section class="season-section" id="season-{html.escape(season)}" data-season-section="{html.escape(season)}" data-season-english="{html.escape(english)}" data-season-phrase="{html.escape(phrase)}" data-season-count="{poem_count}" role="tabpanel">
        <div class="kigo-grid">
{cards}
        </div>
      </section>""")

    kigo_path = "/kigo/"
    kigo_title = "季語から読む俳句｜四季を巡る季語庫｜樹の句帖"
    kigo_description = f"春夏秋冬を巡りながら、{len(by_kigo)}の季語の読み、意味、使い方とitsukiの俳句を探せる季語庫。季語名や読み、句の言葉で検索できます。"
    season_word_data = {
        season: [value for value in season_groups[season] if value in by_kigo]
        for season in season_order
    }
    season_word_json = json.dumps(season_word_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    default_kigo_season = season_for_date(date.today().isoformat())
    default_english, default_phrase = season_labels[default_kigo_season]
    default_count = sum(
        len(by_kigo[value])
        for value in season_groups[default_kigo_season]
        if value in by_kigo
    )
    kigo_body = f"""    <section class="kigo-portal" aria-labelledby="kigo-title">
      <div class="kigo-intro">
        <p class="eyebrow">Seasonal words</p>
        <h1 class="page-title" id="kigo-title">季語を巡る</h1>
        <p class="page-lead">春から夏へ、秋から冬へ。季語を暦の輪に置き、読みと意味から一句へ辿る頁です。</p>
        <p class="search-status" id="kigo-search-status" role="status" aria-live="polite">{len(by_kigo)}の季語</p>
        <div class="kigo-current-season" aria-live="polite">
          <p id="kigo-current-season-en">{html.escape(default_english)}</p>
          <h2 id="kigo-current-season-name">{html.escape(default_kigo_season)}</h2>
          <span id="kigo-current-season-meta">{html.escape(default_phrase)}・{default_count}句</span>
        </div>
      </div>
      <nav class="season-orbit" aria-label="季節を選ぶ" role="tablist">
        <span class="orbit-core" aria-hidden="true">季</span>
        <span class="season-whispers" id="season-whispers" aria-hidden="true"></span>
        {orbit_links}
      </nav>
    </section>
    <div class="season-stream">
{chr(10).join(season_sections)}
    </div>
    <script id="kigo-season-data" type="application/json">{season_word_json}</script>"""
    kigo_data = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": kigo_title,
            "description": kigo_description,
            "url": absolute_url(base_url, kigo_path),
            "inLanguage": "ja",
            "about": "俳句の季語",
        },
        breadcrumb_data(base_url, [("樹の句帖", "/"), ("季語", kigo_path)]),
    ]
    explorer_script = '<script src="/assets/js/haiku-explorer.js?v=20260827-explorer-v4"></script>'
    write_page(
        public_root,
        "kigo/index.html",
        page_shell(
            site_meta,
            kigo_title,
            kigo_description,
            kigo_path,
            kigo_body,
            kigo_data,
            page_class="page-shell kigo-page",
            extra_body=explorer_script,
            body_attributes=f'data-explorer="kigo" data-current-season="{html.escape(default_kigo_season, quote=True)}"',
        ),
        written,
    )
    canonical_paths.append(kigo_path)

    mapped_locations = []
    unmapped_locations = []
    for value, grouped_poems in sorted(by_location.items(), key=lambda item: item[0]):
        map_entry = location_map.get(value)
        if not map_entry:
            unmapped_locations.append((value, grouped_poems))
            continue
        seasons = [poem.get("season", "余白") for poem in grouped_poems]
        dominant_season = max(set(seasons), key=seasons.count) if seasons else "余白"
        mapped_locations.append({
            "name": value,
            "nameRuby": grouped_poems[0]["location"],
            "mapped": True,
            "url": tag_path("location", value),
            "count": len(grouped_poems),
            "lat": map_entry["lat"],
            "lng": map_entry["lng"],
            "precision": map_entry.get("precision", "point"),
            "prefecture": map_entry["prefecture"],
            "season": dominant_season,
            "preview": "／".join(plain_text(line) for line in grouped_poems[0]["lines"]),
            "previewRuby": grouped_poems[0]["lines"],
        })

    prefecture_counts = defaultdict(int)
    prefecture_locations = defaultdict(list)
    for entry in mapped_locations:
        prefecture = entry["prefecture"]
        prefecture_counts[prefecture] += entry["count"]
        prefecture_locations[prefecture].append(entry)
    prefectures = sorted(prefecture_counts, key=lambda value: (-prefecture_counts[value], value))
    default_prefecture = prefectures[0]
    prefecture_buttons = "".join(
        f'<button type="button" data-map-prefecture="{html.escape(prefecture, quote=True)}" aria-pressed="{"true" if prefecture == default_prefecture else "false"}"><span>{html.escape(prefecture)}</span><small>{prefecture_counts[prefecture]}句</small></button>'
        for prefecture in prefectures
    )
    grouped_prefectures = [
        {
            "name": prefecture,
            "count": prefecture_counts[prefecture],
            "locations": prefecture_locations[prefecture],
        }
        for prefecture in prefectures
    ]
    location_dataset = {
        "schemaVersion": 1,
        "prefectures": grouped_prefectures,
        "defaultPrefecture": default_prefecture,
    }
    map_json = json.dumps(
        location_dataset,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    write_page(
        public_root,
        "content/haiku/generated/locations.json",
        json.dumps(location_dataset, ensure_ascii=False, indent=2) + "\n",
        written,
    )
    mapped_links = "".join(
        f'<a class="tag-link" href="{html.escape(entry["url"], quote=True)}"><span>{ruby_markup(entry["nameRuby"])}</span><span class="tag-count">{entry["count"]}</span></a>'
        for entry in mapped_locations
    )
    unmapped_links = "".join(
        f'<a class="tag-link" href="{html.escape(tag_path("location", value), quote=True)}"><span>{ruby_markup(grouped_poems[0]["location"])}</span><span class="tag-count">{len(grouped_poems)}</span></a>'
        for value, grouped_poems in unmapped_locations
    )
    unmapped_section = ""
    if unmapped_links:
        unmapped_section = f"""    <section class="unmapped-places">
      <h2>地図に置かない場所</h2>
      <p>街角や部屋など、一点に決めない方がよい場所は、言葉のまま残しています。</p>
      <div class="tag-list">{unmapped_links}</div>
    </section>"""
    location_path = "/location/"
    location_title = "俳句の場所を地図から読む｜樹の句帖"
    location_description = f"itsukiが俳句を詠んだ{len(by_location)}の場所を、都道府県ごとに地図から辿るページ。各地点から、その土地で詠んだ俳句を読めます。"
    location_body = f"""{location_view_switch('map')}
    <section class="map-intro">
      <p class="eyebrow">Places in verse</p>
      <h1 class="page-title">句の生まれた場所</h1>
      <p class="page-lead">句のある都道府県を切り替えて辿る地図です。数字はその場所、または近くの場所にある句の数を表します。</p>
      <div class="map-legend" aria-label="地図の季節色">
        <span data-season="春">春</span><span data-season="夏">夏</span><span data-season="秋">秋</span><span data-season="冬">冬</span>
      </div>
    </section>
    <nav class="map-prefectures" aria-label="地図に表示する都道府県">
      {prefecture_buttons}
    </nav>
    <section class="map-stage" aria-label="俳句の場所の地図">
      <div class="map-prefecture-caption" aria-live="polite"><span id="map-prefecture-name">{html.escape(default_prefecture)}</span><small id="map-prefecture-count">{prefecture_counts[default_prefecture]}句</small></div>
        <div id="haiku-map"></div>
      <p class="map-note">地名だけの記録は、おおよその位置に置いています。地図 <a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener noreferrer">国土地理院・地理院タイル（淡色地図）</a></p>
      <p class="map-fallback" id="map-fallback" hidden>地図を読み込めませんでした。下の地名索引から句を読むことができます。</p>
    </section>
    <details class="map-place-index">
      <summary>地名索引を見る</summary>
      <div class="tag-list">{mapped_links}</div>
    </details>
{unmapped_section}
    <script id="location-map-data" type="application/json">{map_json}</script>"""
    location_data = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": location_title,
            "description": location_description,
            "url": absolute_url(base_url, location_path),
            "inLanguage": "ja",
            "about": "俳句を詠んだ場所",
        },
        breadcrumb_data(base_url, [("樹の句帖", "/"), ("場所の地図", location_path)]),
    ]
    leaflet_head = """<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">"""
    leaflet_scripts = """<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <script src="/assets/js/haiku-explorer.js?v=20260827-explorer-v4"></script>"""
    write_page(
        public_root,
        "location/index.html",
        page_shell(
            site_meta,
            location_title,
            location_description,
            location_path,
            location_body,
            location_data,
            page_class="page-shell location-page",
            extra_head=leaflet_head,
            extra_body=leaflet_scripts,
            body_attributes='data-explorer="location"',
        ),
        written,
    )
    canonical_paths.append(location_path)

    unmapped_list_entries = [
        {
            "name": value,
            "nameRuby": grouped_poems[0]["location"],
            "mapped": False,
            "url": tag_path("location", value),
            "count": len(grouped_poems),
            "precision": "area",
            "previewRuby": grouped_poems[0]["lines"],
        }
        for value, grouped_poems in unmapped_locations
    ]
    list_groups = list(grouped_prefectures)
    if unmapped_list_entries:
        list_groups.append({
            "name": "地図に置かない場所",
            "count": sum(entry["count"] for entry in unmapped_list_entries),
            "locations": unmapped_list_entries,
        })

    prefecture_index_links = "".join(
        f'<a href="#location-group-{index}"><span>{html.escape(group["name"])}</span><small>{len(group["locations"])}地点・{group["count"]}句</small></a>'
        for index, group in enumerate(list_groups, start=1)
    )
    location_list_sections = []
    for index, group in enumerate(list_groups, start=1):
        rows = "\n".join(location_list_row(entry, group["name"]) for entry in group["locations"])
        location_list_sections.append(f"""    <section class="location-list-group" id="location-group-{index}" data-location-group>
      <header class="location-list-heading">
        <p>{index:02d}</p>
        <h2>{html.escape(group['name'])}</h2>
        <span>{len(group['locations'])}地点・{group['count']}句</span>
      </header>
      <div class="location-list-rows">
{rows}
      </div>
    </section>""")

    location_list_path = "/location/list/"
    location_list_title = "俳句の場所一覧｜都道府県から読む｜樹の句帖"
    location_list_description = (
        f"itsukiの俳句{len(poems)}句を、{len(prefectures)}都道府県・{len(by_location)}地点から探せる場所一覧。"
        "地名、代表句、句数から各場所の俳句へ辿れます。"
    )
    location_list_body = f"""{location_view_switch('list')}
    <section class="location-list-intro">
      <p class="eyebrow">Places index</p>
      <h1 class="page-title">俳句を場所から読む</h1>
      <p class="page-lead">句が生まれた場所を、都道府県ごとの一覧にしました。地名と代表する一句から、その土地に連なる句へ辿れます。</p>
      <div class="location-list-stats" aria-label="場所一覧の集計">
        <span><strong>{len(by_location)}</strong> Places</span>
        <span><strong>{len(prefectures)}</strong> Prefectures</span>
        <span><strong>{len(poems)}</strong> Haiku</span>
      </div>
      <label class="kigo-search location-search">
        <span>場所を探す</span>
        <input id="location-search" type="search" placeholder="舎人、図書館、東京都…" autocomplete="off">
      </label>
      <p class="search-status" id="location-search-status" role="status" aria-live="polite">{len(by_location)}の場所</p>
    </section>
    <nav class="location-prefecture-index" aria-label="都道府県の目次">
      {prefecture_index_links}
    </nav>
    <div class="location-list-stream">
{chr(10).join(location_list_sections)}
    </div>"""
    all_list_entries = [entry for group in list_groups for entry in group["locations"]]
    location_list_data = [
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": location_list_title,
            "description": location_list_description,
            "url": absolute_url(base_url, location_list_path),
            "inLanguage": "ja",
            "about": "俳句を詠んだ場所の一覧",
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "樹の句帖 場所一覧",
            "numberOfItems": len(all_list_entries),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "item": {
                        "@type": "CollectionPage",
                        "name": f"{entry['name']}の俳句",
                        "url": absolute_url(base_url, entry["url"]),
                    },
                }
                for position, entry in enumerate(all_list_entries, start=1)
            ],
        },
        breadcrumb_data(
            base_url,
            [("樹の句帖", "/"), ("場所", location_path), ("場所一覧", location_list_path)],
        ),
    ]
    write_page(
        public_root,
        "location/list/index.html",
        page_shell(
            site_meta,
            location_list_title,
            location_list_description,
            location_list_path,
            location_list_body,
            location_list_data,
            page_class="page-shell location-list-page",
            extra_body='<script src="/assets/js/haiku-explorer.js?v=20260827-explorer-v4"></script>',
        ),
        written,
    )
    canonical_paths.append(location_list_path)

    about_path = "/about/"
    about_title = "樹の句帖について｜itsukiの俳句"
    about_description = (
        f"樹の句帖は、itsukiが日々の場所と季節から詠んだ俳句{len(poems)}句を集めた個人句帖。"
        f"{len(by_kigo)}の季語と{len(by_location)}の場所から読むことができます。"
    )
    about_story_1 = ruby_sentence([
        ("大学", "だいがく"), "のころから、", ("俳句", "はいく"), "という", ("短", "みじか"), "い",
        ("詩", "し"), "のかたちに", ("少", "すこ"), "し", ("興味", "きょうみ"), "がありました。はじめに",
        ("触", "ふ"), "れたのは", ("日本語", "にほんご"), "の", ("原文", "げんぶん"), "ではなく、",
        ("中国語", "ちゅうごくご"), "に", ("訳", "やく"), "された", ("俳句", "はいく"), "でした。"
    ])
    about_story_2 = ruby_sentence([
        "2026", ("年", "ねん"), "の", ("春", "はる"), "、", ("日本", "にほん"), "へ", ("向", "む"),
        "かう", ("日本航空", "にほんこうくう"), "の", ("機内", "きない"), "で、", ("俳句", "はいく"),
        "を", ("紹介", "しょうかい"), "する", ("小", "ちい"), "さな", ("電子書籍", "でんししょせき"),
        "を", ("読", "よ"), "みました。", ("俳句", "はいく"), "とは", ("何", "なに"), "か、",
        ("何", "なに"), "を", ("表", "あらわ"), "すものなのかをやさしく", ("説明", "せつめい"),
        "した", ("本", "ほん"), "でした。", ("十分", "じゅうぶん"), "に", ("読", "よ"), "み",
        ("取", "と"), "れたわけではありません。それでも、ある", ("一瞬", "いっしゅん"), "の",
        ("心持", "こころも"), "ちを、", ("少", "すく"), "ない", ("言葉", "ことば"), "と",
        ("決", "き"), "まった", ("形", "かたち"), "に", ("託", "たく"), "すという", ("考", "かんが"),
        "え", ("方", "かた"), "が", ("強", "つよ"), "く", ("残", "のこ"), "りました。"
    ])
    about_story_3 = ruby_sentence([
        ("着陸", "ちゃくりく"), "が", ("近", "ちか"), "づくころ、", ("高", "たか"), "い",
        ("空", "そら"), "に", ("一輪", "いちりん"), "の", ("明月", "めいげつ"), "が",
        ("見", "み"), "えました。", ("試", "ため"), "しに", ("始", "はじ"), "めた",
        ("日本語", "にほんご"), "が、いつの", ("間", "ま"), "にか", ("自分", "じぶん"), "を",
        ("日本", "にほん"), "へ", ("連", "つ"), "れてきたことが、", ("少", "すこ"), "し",
        ("夢", "ゆめ"), "のようでした。", ("異国", "いこく"), "の", ("空", "そら"), "に",
        ("来", "き"), "ても、", ("月", "つき"), "は", ("同", "おな"), "じでした。その",
        ("気持", "きも"), "ちから、", ("最初", "さいしょ"), "の", ("一句", "いっく"), "が",
        ("生", "う"), "まれました。"
    ])
    about_origin_caption = ruby_sentence([
        ("原案", "げんあん"), "は「", ("春", "はる"), "の", ("始", "はじ"), "まる　",
        ("新", "あたら"), "しいところで", ("日本", "にほん"), "　", ("同", "おな"), "じ",
        ("月", "つき"), "」。", ("俳句", "はいく"), "の", ("形", "かたち"), "からは",
        ("遠", "とお"), "いけれど、その", ("時", "とき"), "の", ("気持", "きも"), "ちは",
        ("確", "たし"), "かにそこにありました。"
    ])
    about_story_4 = ruby_sentence([
        ("俳句", "はいく"), "を", ("書", "か"), "くことは、", ("日本語", "にほんご"), "を",
        ("学", "まな"), "ぶひとつの", ("方法", "ほうほう"), "にもなりました。はじめは",
        ("場面", "ばめん"), "を", ("言葉", "ことば"), "にして、", ("人工知能", "じんこうちのう"),
        "に「この", ("景色", "けしき"), "にはどんな", ("俳句", "はいく"), "が", ("合", "あ"),
        "うか」と", ("尋", "たず"), "ねるところから", ("始", "はじ"), "まりました。",
        ("助言", "じょげん"), "を", ("受", "う"), "けながら、", ("単語", "たんご"), "も",
        ("文法", "ぶんぽう"), "も", ("少", "すこ"), "しずつ", ("覚", "おぼ"), "えていきました。"
    ])
    about_story_5 = ruby_sentence([
        ("来日", "らいにち"), "して", ("五日目", "いつかめ"), "の", ("午後", "ごご"), "、",
        ("荒川土手", "あらかわどて"), "を", ("歩", "ある"), "いているとき、", ("自分", "じぶん"),
        "の", ("俳句", "はいく"), "を", ("置", "お"), "いておく", ("場所", "ばしょ"), "を",
        ("作", "つく"), "ろうと", ("思", "おも"), "いました。それが、この", ("樹", "いつき"),
        "の", ("句帖", "くちょう"), "の", ("始", "はじ"), "まりです。", ("毎日", "まいにち"),
        "の", ("新", "あたら"), "しい", ("発見", "はっけん"), "を、まだ", ("拙", "つたな"),
        "い", ("日本語", "にほんご"), "で", ("一句", "いっく"), "にし、", ("人工知能", "じんこうちのう"),
        "の", ("添削", "てんさく"), "と", ("対話", "たいわ"), "しながら", ("続", "つづ"), "けました。"
    ])
    about_story_6 = (
        ruby_sentence([
            "その", ("後", "ご"), "、", ("図書館", "としょかん"), "で", ("俳句", "はいく"), "の",
            ("本", "ほん"), "を", ("借", "か"), "り、", ("少", "すこ"), "しずつ", ("本格的", "ほんかくてき"),
            "に", ("学", "まな"), "び", ("始", "はじ"), "めました。2026", ("年", "ねん"), "4",
            ("月", "がつ"), "19", ("日", "にち"), "には、", ("足立区", "あだちく"), "の"
        ])
        + '<a class="inline-link" href="https://www.adachi-chuohonchocenter.net/lecture/event/post_388.html" target="_blank" rel="noopener noreferrer">'
        + ruby_sentence(["やよい", ("図書館", "としょかん")])
        + "</a>"
        + ruby_sentence([
            "で", ("開", "ひら"), "かれた", ("俳句", "はいく"), "サロンにも", ("参加", "さんか"),
            "しました。", ("日本語", "にほんご"), "はまだ", ("十分", "じゅうぶん"), "ではありませんでしたが、",
            ("参加者", "さんかしゃ"), "のみなさんは", ("親切", "しんせつ"), "で、", ("特", "とく"), "に",
            ("青樹先生", "せいじゅせんせい"), "からいただいた", ("励", "はげ"), "ましと", ("助言", "じょげん"),
            "は、", ("大", "おお"), "きな", ("支", "ささ"), "えになりました。"
        ])
    )
    about_story_7 = ruby_sentence([
        "いまも", ("月一回", "つきいっかい"), "のサロンに", ("通", "かよ"), "いながら、",
        ("旅行先", "りょこうさき"), "でも", ("句", "く"), "を", ("試", "こころ"), "みています。2026",
        ("年", "ねん"), "8", ("月", "がつ"), "、JLPTの", ("教材", "きょうざい"), "を", ("買", "か"), "いに",
        ("行", "い"), "ったとき、", ("小川軽舟先生", "おがわけいしゅうせんせい"), "の『",
        ("俳句", "はいく"), "の", ("仕組", "しく"), "み』を", ("一冊", "いっさつ"), ("買", "か"),
        "いました。", ("図書館", "としょかん"), "で", ("借", "か"), "りる", ("本", "ほん"),
        "はいつか", ("返", "かえ"), "しますが、", ("手元", "てもと"), "に", ("置", "お"),
        "ける", ("一冊", "いっさつ"), "ができたことで、いつでも", ("戻", "もど"), "れる",
        ("学", "まな"), "びの", ("場所", "ばしょ"), "ができました。"
    ])
    about_body = f"""    <section class="about-hero" aria-labelledby="about-title">
      <p class="eyebrow">About</p>
      <h1 class="page-title" id="about-title">{compact_ruby_markup('樹の句帖について', 'いつきのくちょうについて')}</h1>
      <p class="page-lead">{compact_ruby_markup('日々の場所、季節の言葉、ふと残った景色を、一句ずつ置いていく個人の俳句帖です。', 'ひびのばしょ、きせつのことば、ふとのこったけしきを、いっくずつおいていくこじんのはいくちょうです。')}</p>
      <div class="about-stats" aria-label="句帖の統計">
        <a href="/archive/" aria-label="俳句{len(poems)}句を句の一覧で読む"><strong>{len(poems)}</strong><span>俳句</span><small>句の一覧へ</small></a>
        <a href="/kigo/" aria-label="季語{len(by_kigo)}語を季語ページで読む"><strong>{len(by_kigo)}</strong><span>季語</span><small>季語へ</small></a>
        <a href="/location/list/" aria-label="場所{len(by_location)}件を場所一覧で読む"><strong>{len(by_location)}</strong><span>場所</span><small>場所一覧へ</small></a>
        <a href="/location/" aria-label="地図の地点{len(location_map)}件を地図で読む"><strong>{len(location_map)}</strong><span>地図の地点</span><small>地図へ</small></a>
      </div>
    </section>
    <section class="about-story" aria-labelledby="about-story-title">
      <p class="eyebrow">Story</p>
      <h2 id="about-story-title">{compact_ruby_markup('俳句との出会い', 'はいくとのであい')}</h2>
      <p>{about_story_1}</p>
      <p>{about_story_2}</p>
      <p>{about_story_3}</p>
      <figure class="about-origin-poem">
        <blockquote>{compact_ruby_markup('春風や　新天地にも　同じ月', 'はるかぜや　しんてんちにも　おなじつき')}</blockquote>
        <figcaption>{about_origin_caption}</figcaption>
      </figure>
      <p>{about_story_4}</p>
      <p>{about_story_5}</p>
      <p>{about_story_6}</p>
      <p>{about_story_7}</p>
    </section>"""
    about_data = [
        {
            "@context": "https://schema.org",
            "@type": "AboutPage",
            "name": about_title,
            "description": about_description,
            "url": absolute_url(base_url, about_path),
            "inLanguage": "ja",
            "isPartOf": {"@type": "WebSite", "name": "樹の句帖", "url": absolute_url(base_url, "/")},
            "about": {"@type": "Person", "name": author},
        },
        breadcrumb_data(base_url, [("樹の句帖", "/"), ("紹介", about_path)]),
    ]
    write_page(
        public_root,
        "about/index.html",
        page_shell(
            site_meta,
            about_title,
            about_description,
            about_path,
            about_body,
            about_data,
            page_class="page-shell about-page",
        ),
        written,
    )
    canonical_paths.append(about_path)

    feedback_path = "/feedback/"
    feedback_title = "感想を送る｜樹の句帖"
    feedback_description = "樹の句帖の俳句やサイトについて、公開されないメッセージを作者へ送れるページです。"
    feedback_markup, feedback_scripts = feedback_section(
        {"url": feedback_path},
        "樹の句帖",
        site_meta,
        heading="樹の句帖へひとこと",
        lead="句の感想や、サイトを読んで気づいたことを作者へ届けられます。内容は公開されません。",
        eyebrow="Feedback",
    )
    if not feedback_markup:
        feedback_markup = '<p class="page-lead feedback-unavailable">現在、感想の受付を準備しています。</p>'
    feedback_body = f"""    <p class="eyebrow">Letter to itsuki</p>
    <h1 class="page-title">感想を送る</h1>
    <p class="page-lead">心に残った一句や、句帖を巡って感じたことを、静かな手紙のようにお寄せください。</p>
{feedback_markup}"""
    feedback_data = [
        {
            "@context": "https://schema.org",
            "@type": "ContactPage",
            "name": feedback_title,
            "description": feedback_description,
            "url": absolute_url(base_url, feedback_path),
            "inLanguage": "ja",
            "isPartOf": {"@type": "WebSite", "name": "樹の句帖", "url": absolute_url(base_url, "/")},
        },
        breadcrumb_data(base_url, [("樹の句帖", "/"), ("感想", feedback_path)]),
    ]
    write_page(
        public_root,
        "feedback/index.html",
        page_shell(
            site_meta,
            feedback_title,
            feedback_description,
            feedback_path,
            feedback_body,
            feedback_data,
            page_class="page-shell feedback-page",
            extra_body=feedback_scripts,
        ),
        written,
    )
    canonical_paths.append(feedback_path)

    for index, poem in enumerate(poems):
        location = plain_text(poem["location"])
        plain_lines = [plain_text(line) for line in poem["lines"]]
        joined_lines = "／".join(plain_lines)
        date_label = japanese_date(poem["date"])
        title = f"{plain_lines[0]}｜{location}の俳句（{poem['date']}）｜樹の句帖"
        if poem.get("kigo"):
            description = f"「{joined_lines}」。{date_label}、{location}で詠んだitsukiの俳句。季語は「{poem['kigo']}」。"
        else:
            description = f"「{joined_lines}」。{date_label}、{location}で詠んだitsukiの俳句。"

        related_location = [candidate for candidate in by_location[location] if candidate["url"] != poem["url"]]
        related_kigo = [candidate for candidate in by_kigo.get(poem.get("kigo"), []) if candidate["url"] != poem["url"]]
        kigo_tag = ""
        if poem.get("kigo"):
            kigo_tag = f'<a class="tag-link" href="{html.escape(poem["kigoUrl"], quote=True)}">季語　{html.escape(poem["kigo"])}</a>'

        theme_dark = poem.get("theme") == "dark"
        detail_style = (
            f"--detail-bg:{html.escape(poem.get('bgColor', '#f7f5ef'), quote=True)};"
            f"--detail-ink:{'#f1eee5' if theme_dark else '#24211b'};"
            f"--detail-muted:{'#bbb7ae' if theme_dark else '#5f5a50'};"
        )
        lines_markup = "".join(f"<span>{ruby_markup(line)}</span>" for line in poem["lines"])
        about = f"{date_label}、{location}で詠んだ一句です。"
        if poem.get("kigo"):
            about += f"季語は「{poem['kigo']}」。"
        about += "句、季語、場所のリンクから、同じ言葉や土地に連なる別の句へ移れます。"
        feedback_markup, feedback_scripts = feedback_section(poem, joined_lines, site_meta)

        body = f"""    <section class="detail-hero" style="{detail_style}">
      <article class="detail-poem">
        <div class="detail-meta"><span>{ruby_markup(poem['location'])}</span><time datetime="{html.escape(poem['date'])}">{html.escape(date_label)}</time></div>
        <h1 class="detail-title">{lines_markup}</h1>
        <nav class="detail-tags" aria-label="句のタグ">
          {kigo_tag}
          <a class="tag-link" href="{html.escape(poem['locationUrl'], quote=True)}">場所　{html.escape(location)}</a>
        </nav>
      </article>
    </section>
    <div class="detail-context">
      {breadcrumb_markup([('樹の句帖', '/'), ('句の一覧', '/archive/'), (plain_lines[0], poem['url'])])}
      <section class="context-block">
        <h2>この句について</h2>
        <p>{html.escape(about)}</p>
      </section>
      <div class="related-grid">
        <section class="related-block"><h2>{html.escape(location)}で詠んだ句</h2>{related_list(related_location)}</section>
        <section class="related-block"><h2>{'季語「' + html.escape(poem['kigo']) + '」の句' if poem.get('kigo') else '近くの句'}</h2>{related_list(related_kigo)}</section>
      </div>
      <nav class="detail-switch" aria-label="前後の句">
        {switch_item(poems[index - 1] if index > 0 else None, '前の句')}
        {switch_item(poems[index + 1] if index + 1 < len(poems) else None, '次の句')}
      </nav>
{feedback_markup}
    </div>"""
        keywords = ["俳句", "現代俳句", location, poem["season"]]
        if poem.get("kigo"):
            keywords.append(poem["kigo"])
        data = [
            {
                "@context": "https://schema.org",
                "@type": "CreativeWork",
                "name": joined_lines,
                "text": "\n".join(plain_lines),
                "url": absolute_url(base_url, poem["url"]),
                "inLanguage": "ja",
                "genre": "俳句",
                "dateCreated": poem["date"],
                "creator": {"@type": "Person", "name": author},
                "locationCreated": {"@type": "Place", "name": location},
                "keywords": keywords,
                "isPartOf": {"@type": "WebSite", "name": "樹の句帖", "url": absolute_url(base_url, "/")},
            },
            breadcrumb_data(base_url, [("樹の句帖", "/"), ("句の一覧", "/archive/"), (plain_lines[0], poem["url"])]),
        ]
        relative_path = f"haiku/{poem['slug']}/index.html"
        write_page(
            public_root,
            relative_path,
            page_shell(
                site_meta,
                title,
                description,
                poem["url"],
                body,
                data,
                page_class="detail-main",
                og_type="article",
                extra_body=feedback_scripts,
            ),
            written,
        )
        canonical_paths.append(poem["url"])

    for kind, groups, heading_label in (
        ("kigo", by_kigo, "季語"),
        ("location", by_location, "場所"),
    ):
        for value, grouped_poems in groups.items():
            canonical_path = tag_path(kind, value)
            relative_path = f"{kind}/{safe_segment(value)}/index.html"
            index_label = "季語" if kind == "kigo" else "場所の地図"
            index_path = f"/{kind}/"
            if kind == "kigo":
                entry = kigo_library[value]
                reading = entry["reading"]
                season_label_markup = compact_ruby_markup(
                    f"季語・{entry['season']}",
                    f"きご・{SEASON_READINGS[entry['season']]}",
                )
                title = f"季語「{value}（{reading}）」の意味と俳句 {len(grouped_poems)}句｜樹の句帖"
                description = (
                    f"季語「{value}（{reading}）」は{entry['summary']}"
                    f"使い方と意象、itsukiの俳句{len(grouped_poems)}句を紹介します。"
                )
                body = f"""    {breadcrumb_markup([('樹の句帖', '/'), (index_label, index_path), (value, canonical_path)])}
    <p class="eyebrow">{season_label_markup}</p>
    <h1 class="page-title kigo-detail-title">{kigo_title_markup(value, entry)}</h1>
    <p class="page-lead kigo-detail-lead">{compact_ruby_markup(entry['summary'], entry['summaryReading'])}</p>
{kigo_guide_markup(value, entry)}
    <section class="kigo-poems" aria-labelledby="kigo-poems-title">
      <div class="archive-summary"><h2 id="kigo-poems-title">{compact_ruby_markup('この季語で詠んだ句', 'このきごでよんだく')}</h2><span>{len(grouped_poems)} HAIKU</span></div>
      <div class="archive-list">
{chr(10).join(archive_row(poem) for poem in grouped_poems)}
      </div>
    </section>"""
                data = [
                    {
                        "@context": "https://schema.org",
                        "@type": "CollectionPage",
                        "name": title,
                        "description": description,
                        "url": absolute_url(base_url, canonical_path),
                        "inLanguage": "ja",
                        "about": {"@type": "DefinedTerm", "name": value, "alternateName": reading},
                    },
                    {
                        "@context": "https://schema.org",
                        "@type": "DefinedTerm",
                        "name": value,
                        "alternateName": reading,
                        "description": entry["summary"],
                        "url": absolute_url(base_url, canonical_path),
                        "inDefinedTermSet": {
                            "@type": "DefinedTermSet",
                            "name": "樹の句帖 季語庫",
                            "url": absolute_url(base_url, "/kigo/"),
                        },
                    },
                    breadcrumb_data(base_url, [("樹の句帖", "/"), (index_label, index_path), (value, canonical_path)]),
                ]
            else:
                title = f"{value}の俳句 {len(grouped_poems)}句｜樹の句帖"
                description = f"{value}で詠んだitsukiの俳句を{len(grouped_poems)}句まとめた場所別ページ。季語と日付から各句を読めます。"
                lead = f"{value}で詠んだ句をまとめています。"
                body = f"""    {breadcrumb_markup([('樹の句帖', '/'), (index_label, index_path), (value, canonical_path)])}
    <p class="eyebrow">{html.escape(heading_label)}</p>
    <h1 class="page-title">{ruby_markup(grouped_poems[0]['location'])}</h1>
    <p class="page-lead">{html.escape(lead)}句を開くと、同じ季語や場所に連なる別の句へ移れます。</p>
    <div class="archive-summary"><span>{len(grouped_poems)} HAIKU</span></div>
    <div class="archive-list">
{chr(10).join(archive_row(poem) for poem in grouped_poems)}
    </div>"""
                data = [
                    {
                        "@context": "https://schema.org",
                        "@type": "CollectionPage",
                        "name": title,
                        "description": description,
                        "url": absolute_url(base_url, canonical_path),
                        "inLanguage": "ja",
                        "about": value,
                    },
                    breadcrumb_data(base_url, [("樹の句帖", "/"), (index_label, index_path), (value, canonical_path)]),
                ]
            write_page(public_root, relative_path, page_shell(site_meta, title, description, canonical_path, body, data), written)
            canonical_paths.append(canonical_path)

    sitemap_urls = "\n".join(
        f"  <url><loc>{xml_escape(absolute_url(base_url, path))}</loc></url>" for path in canonical_paths
    )
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap_urls}\n</urlset>\n'
    write_page(public_root, "sitemap.xml", sitemap, written)
    write_page(public_root, "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n", written)

    cleanup_stale_pages(public_root, manifest_path, written)
    manifest_path.write_text(json.dumps({"files": sorted(written)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "archivePages": total_pages,
        "detailPages": len(poems),
        "kigoPages": len(by_kigo),
        "locationPages": len(by_location),
        "sitemapUrls": len(canonical_paths),
    }
