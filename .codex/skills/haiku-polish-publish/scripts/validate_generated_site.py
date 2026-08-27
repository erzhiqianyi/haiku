#!/usr/bin/env python3
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from xml.etree import ElementTree

from haiku_season import validate_poem_season


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.canonical = None
        self.description = None
        self.h1_count = 0
        self.in_title = False
        self.title_parts = []
        self.in_json_ld = False
        self.json_ld_parts = []
        self.json_ld = []
        self.in_location_data = False
        self.location_data_parts = []
        self.location_data = None
        self.feedback_forms = 0
        self.reading_toggles = 0
        self.reading_ruby = 0
        self.kigo_title_reading_ruby = 0
        self.reading_details = 0
        self.in_site_nav = False
        self.site_nav_count = 0
        self.site_nav_hrefs = []
        self.site_header_count = 0
        self.stylesheets = []
        self.home_filter_forms = 0
        self.location_search_inputs = 0
        self.breadcrumbs = 0

    @property
    def title(self):
        return "".join(self.title_parts).strip()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = values.get("class", "").split()
        if tag == "header" and "site-header" in classes:
            self.site_header_count += 1
        if tag == "nav" and values.get("aria-label") == "サイト内ナビゲーション":
            self.in_site_nav = True
            self.site_nav_count += 1
        elif tag == "nav" and values.get("aria-label") == "パンくず":
            self.breadcrumbs += 1
        if tag == "a" and values.get("href"):
            self.anchors.append(values["href"])
            if self.in_site_nav:
                self.site_nav_hrefs.append(values["href"])
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href")
        elif tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(values["href"])
        elif tag == "meta" and values.get("name") == "description":
            self.description = values.get("content")
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "script" and values.get("type") == "application/ld+json":
            self.in_json_ld = True
            self.json_ld_parts = []
        elif tag == "script" and values.get("id") == "location-map-data":
            self.in_location_data = True
            self.location_data_parts = []
        elif tag == "form" and values.get("action") == "/api/feedback":
            self.feedback_forms += 1
        elif tag == "form" and values.get("id") == "haiku-filters":
            self.home_filter_forms += 1
        elif tag == "input" and values.get("id") == "location-search":
            self.location_search_inputs += 1
        elif tag == "button" and "data-readings-toggle" in values:
            self.reading_toggles += 1
        elif tag == "ruby":
            if "reading-ruby" in classes:
                self.reading_ruby += 1
            if "kigo-title-ruby" in classes and "reading-ruby" in classes:
                self.kigo_title_reading_ruby += 1
        elif "reading-detail" in values.get("class", "").split():
            self.reading_details += 1

    def handle_endtag(self, tag):
        if tag == "nav" and self.in_site_nav:
            self.in_site_nav = False
        elif tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_json_ld:
            self.in_json_ld = False
            self.json_ld.append(json.loads("".join(self.json_ld_parts)))
        elif tag == "script" and self.in_location_data:
            self.in_location_data = False
            self.location_data = json.loads("".join(self.location_data_parts))

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_json_ld:
            self.json_ld_parts.append(data)
        if self.in_location_data:
            self.location_data_parts.append(data)


def parse_args():
    parser = argparse.ArgumentParser(description="Validate generated haiku pages, metadata, sitemap, and internal links.")
    parser.add_argument("--repo", default=".")
    return parser.parse_args()


def local_target(public_root, page_path, href):
    if href.startswith(("#", "mailto:", "tel:", "data:")):
        return None
    parsed = urlparse(urljoin(f"https://haiku.erzhiqian.cc/{page_path.relative_to(public_root)}", href))
    if parsed.netloc != "haiku.erzhiqian.cc":
        return None
    path = unquote(parsed.path).lstrip("/")
    if not path:
        return public_root / "index.html"
    target = public_root / path
    if parsed.path.endswith("/"):
        target = target / "index.html"
    return target


def flatten_types(value):
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(flatten_types(item))
        return result
    if isinstance(value, dict):
        result = [value.get("@type")]
        if "@graph" in value:
            result.extend(flatten_types(value["@graph"]))
        return [item for item in result if item]
    return []


HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def relative_luminance(hex_color):
    if not isinstance(hex_color, str) or not HEX_COLOR.fullmatch(hex_color):
        raise ValueError(f"Invalid hex color: {hex_color}")
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = []
    for channel in channels:
        if channel <= 0.03928:
            linear.append(channel / 12.92)
        else:
            linear.append(((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(luminance_a, luminance_b):
    lighter = max(luminance_a, luminance_b)
    darker = min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def validate_visual_contrast(poem):
    bg_color = poem.get("bgColor")
    theme = poem.get("theme")
    try:
        background_luminance = relative_luminance(bg_color)
    except ValueError as error:
        raise SystemExit(f"{poem.get('date')} {poem.get('location')} has invalid bgColor: {error}") from error
    if theme == "dark":
        contrast = contrast_ratio(background_luminance, 1.0)
        if contrast < 4.5:
            raise SystemExit(
                f"Dark theme background is too light for {poem.get('date')} {poem.get('location')}: "
                f"{bg_color} contrast={contrast:.2f}"
            )
    elif theme == "light":
        contrast = contrast_ratio(background_luminance, relative_luminance("#211e18"))
        if contrast < 4.5:
            raise SystemExit(
                f"Light theme background is too dark for {poem.get('date')} {poem.get('location')}: "
                f"{bg_color} contrast={contrast:.2f}"
            )
    else:
        raise SystemExit(f"{poem.get('date')} {poem.get('location')} has invalid theme: {theme}")


def main():
    args = parse_args()
    repo = Path(args.repo).resolve()
    public_root = repo / "public"
    manifest_path = public_root / "content" / "haiku" / "generated" / "page-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    generated_index = json.loads((public_root / "content" / "haiku" / "generated" / "itsuki-haiku.json").read_text(encoding="utf-8"))
    site_meta = json.loads((public_root / "content" / "haiku" / "generated" / "site.json").read_text(encoding="utf-8"))
    season_groups = json.loads((public_root / "content" / "haiku" / "kigo-seasons.json").read_text(encoding="utf-8"))
    library_payload = json.loads((public_root / "content" / "haiku" / "kigo-library.json").read_text(encoding="utf-8"))
    if library_payload.get("schemaVersion") != 2 or not isinstance(library_payload.get("entries"), dict):
        raise SystemExit("kigo-library.json must use schemaVersion 2 and contain an entries object")
    kigo_library = library_payload["entries"]
    explorer_source = (public_root / "assets" / "js" / "haiku-explorer.js").read_text(encoding="utf-8")
    gsi_pale_url = "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png"
    if gsi_pale_url not in explorer_source:
        raise SystemExit("Location map must use the GSI pale tile URL")
    if "cartocdn.com" in explorer_source or "OpenStreetMap" in explorer_source or "CARTO" in explorer_source:
        raise SystemExit("Legacy map tile provider remains in haiku-explorer.js")
    if "https://maps.gsi.go.jp/development/ichiran.html" not in explorer_source:
        raise SystemExit("Location map must display the GSI tile attribution link")
    location_map = json.loads((public_root / "content" / "haiku" / "location-map.json").read_text(encoding="utf-8"))
    for name, entry in location_map.items():
        required = ("lat", "lng", "precision", "prefecture")
        missing_fields = [field for field in required if entry.get(field) is None]
        if missing_fields:
            raise SystemExit(f"Location map entry {name} is missing fields: {missing_fields}")
        if "region" in entry:
            raise SystemExit(f"Location map entry {name} still uses legacy region data")
        if entry["precision"] not in ("point", "area"):
            raise SystemExit(f"Location map entry {name} has invalid precision: {entry['precision']}")
        if not isinstance(entry["lat"], (int, float)) or not -90 <= entry["lat"] <= 90:
            raise SystemExit(f"Location map entry {name} has invalid latitude")
        if not isinstance(entry["lng"], (int, float)) or not -180 <= entry["lng"] <= 180:
            raise SystemExit(f"Location map entry {name} has invalid longitude")
        if not re.fullmatch(r"(?:北海道|東京都|京都府|大阪府|.+県)", entry["prefecture"]):
            raise SystemExit(f"Location map entry {name} has invalid prefecture: {entry['prefecture']}")
    generated_locations = json.loads(
        (public_root / "content" / "haiku" / "generated" / "locations.json").read_text(encoding="utf-8")
    )
    if generated_locations.get("schemaVersion") != 1:
        raise SystemExit("Generated locations.json must use schemaVersion 1")
    kigo_to_season = {}
    for season, values in season_groups.items():
        for value in values:
            if value in kigo_to_season:
                raise SystemExit(f"Kigo appears in more than one season: {value}")
            kigo_to_season[value] = season
    if set(kigo_library) != set(kigo_to_season):
        missing = sorted(set(kigo_to_season) - set(kigo_library))
        extra = sorted(set(kigo_library) - set(kigo_to_season))
        raise SystemExit(f"Kigo library mismatch; missing={missing} extra={extra}")
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
            raise SystemExit(f"Kigo library entry {value} is missing fields: {missing_fields}")
        if entry["season"] != kigo_to_season[value]:
            raise SystemExit(f"Kigo library season mismatch for {value}")
        if not isinstance(entry["imagery"], list) or len(entry["imagery"]) < 3:
            raise SystemExit(f"Kigo library entry {value} needs at least three imagery values")
        if not isinstance(entry["imageryReadings"], list) or len(entry["imageryReadings"]) != len(entry["imagery"]):
            raise SystemExit(f"Kigo library entry {value} has mismatched imagery readings")
        reading_values = [entry["summaryReading"], entry["usageReading"], *entry["imageryReadings"]]
        if any(not isinstance(reading, str) or re.search(r"[\u3400-\u9fff\u30a1-\u30f6]", reading) for reading in reading_values):
            raise SystemExit(f"Kigo library entry {value} must use complete hiragana readings")
        famous = entry.get("famousHaiku")
        if famous:
            famous_required = ("text", "textReading", "author", "authorReading", "sourceName", "sourceUrl")
            missing_famous = [field for field in famous_required if not famous.get(field)]
            if missing_famous:
                raise SystemExit(f"Famous haiku for {value} is missing fields: {missing_famous}")
            famous_readings = [famous["textReading"], famous["authorReading"]]
            if any(not isinstance(reading, str) or re.search(r"[\u3400-\u9fff\u30a1-\u30f6]", reading) for reading in famous_readings):
                raise SystemExit(f"Famous haiku readings for {value} must use complete hiragana readings")
            if not famous["sourceUrl"].startswith("https://"):
                raise SystemExit(f"Famous haiku source for {value} must use HTTPS")
    page_paths = [public_root / "index.html"] + [
        public_root / relative for relative in manifest["files"] if relative.endswith(".html")
    ]

    titles = {}
    canonicals = {}
    missing_links = []
    detail_pages = 0
    feedback_forms = 0
    site_feedback_forms = 0
    pages_with_reading_toggle = 0
    poems_with_season = 0
    generated_kigo = set()
    generated_location_urls = set()

    for month in generated_index.get("months", []):
        month_path = public_root / "content" / "haiku" / "generated" / month["path"]
        month_data = json.loads(month_path.read_text(encoding="utf-8"))
        for poem in month_data.get("poems", []):
            try:
                validate_poem_season(poem)
            except (ValueError, TypeError) as error:
                raise SystemExit(str(error)) from error
            validate_visual_contrast(poem)
            if poem.get("kigo"):
                generated_kigo.add(poem["kigo"])
            if poem.get("locationUrl"):
                generated_location_urls.add(poem["locationUrl"])
            poems_with_season += 1

    missing_library_entries = sorted(generated_kigo - set(kigo_library))
    if missing_library_entries:
        raise SystemExit(f"Generated poems use kigo missing from the library: {missing_library_entries}")

    for page_path in page_paths:
        parser = PageParser()
        parser.feed(page_path.read_text(encoding="utf-8"))
        relative = str(page_path.relative_to(public_root))
        if not parser.title:
            raise SystemExit(f"Missing title: {relative}")
        if parser.title in titles:
            raise SystemExit(f"Duplicate title: {parser.title} ({titles[parser.title]}, {relative})")
        titles[parser.title] = relative
        if not parser.description:
            raise SystemExit(f"Missing description: {relative}")
        if not parser.canonical:
            raise SystemExit(f"Missing canonical: {relative}")
        if parser.canonical in canonicals:
            raise SystemExit(f"Duplicate canonical: {parser.canonical}")
        canonicals[parser.canonical] = relative
        if parser.h1_count != 1:
            raise SystemExit(f"Expected one h1 in {relative}, found {parser.h1_count}")
        if parser.reading_toggles != 1:
            raise SystemExit(f"Expected one reading toggle in {relative}, found {parser.reading_toggles}")
        pages_with_reading_toggle += 1
        if parser.site_header_count != 1:
            raise SystemExit(f"Expected one shared site header in {relative}, found {parser.site_header_count}")
        shared_navigation_path = "/assets/css/haiku-navigation.css"
        stylesheet_paths = {urlparse(href).path for href in parser.stylesheets}
        if shared_navigation_path not in stylesheet_paths:
            raise SystemExit(f"Missing shared navigation stylesheet: {relative}")
        expected_nav_hrefs = ["/", "/archive/", "/kigo/", "/location/", "/feedback/", "/about/"]
        if parser.site_nav_count != 1:
            raise SystemExit(f"Expected one site navigation in {relative}, found {parser.site_nav_count}")
        if parser.site_nav_hrefs != expected_nav_hrefs:
            raise SystemExit(
                f"Inconsistent site navigation in {relative}: {parser.site_nav_hrefs} != {expected_nav_hrefs}"
            )
        feedback_target = public_root / "feedback" / "index.html"
        if not any(local_target(public_root, page_path, href) == feedback_target for href in parser.anchors):
            raise SystemExit(f"Missing feedback navigation link: {relative}")

        if relative.startswith("haiku/"):
            detail_pages += 1
            feedback_forms += parser.feedback_forms
            if parser.reading_ruby < 4:
                raise SystemExit(f"Expected location and three poem readings in {relative}")
            types = [item for block in parser.json_ld for item in flatten_types(block)]
            if "CreativeWork" not in types:
                raise SystemExit(f"Missing CreativeWork JSON-LD: {relative}")
            expected_forms = 1 if site_meta.get("feedbackEnabled", False) else 0
            if parser.feedback_forms != expected_forms:
                raise SystemExit(f"Expected {expected_forms} feedback form(s) in {relative}, found {parser.feedback_forms}")

        if relative == "feedback/index.html":
            site_feedback_forms += parser.feedback_forms
            types = [item for block in parser.json_ld for item in flatten_types(block)]
            if "ContactPage" not in types:
                raise SystemExit("Missing ContactPage JSON-LD: feedback/index.html")
            expected_forms = 1 if site_meta.get("feedbackEnabled", False) else 0
            if parser.feedback_forms != expected_forms:
                raise SystemExit(
                    f"Expected {expected_forms} feedback form(s) in feedback/index.html, found {parser.feedback_forms}"
                )

        if relative == "index.html" and parser.home_filter_forms:
            raise SystemExit("Homepage must open directly to the latest poem without filter controls")

        section_indexes = {
            "archive/index.html",
            "kigo/index.html",
            "location/index.html",
            "location/list/index.html",
            "feedback/index.html",
            "about/index.html",
        }
        is_section_page = relative in section_indexes or re.fullmatch(r"archive/page/\d+/index\.html", relative)
        if is_section_page and parser.breadcrumbs:
            raise SystemExit(f"Section page must not repeat the site navigation as breadcrumbs: {relative}")

        if relative.startswith("kigo/") and relative != "kigo/index.html":
            types = [item for block in parser.json_ld for item in flatten_types(block)]
            if "DefinedTerm" not in types:
                raise SystemExit(f"Missing DefinedTerm JSON-LD: {relative}")
            if parser.kigo_title_reading_ruby != 1:
                raise SystemExit(f"Expected one toggleable kigo title reading in {relative}")
            if parser.reading_details < 1:
                raise SystemExit(f"Expected an explicit toggleable kigo reading in {relative}")

        if relative == "kigo/index.html" and parser.reading_details != len(generated_kigo):
            raise SystemExit(
                f"Expected {len(generated_kigo)} toggleable kigo card readings, found {parser.reading_details}"
            )

        if relative == "location/index.html":
            list_path = "/location/list/"
            if not any(urlparse(urljoin(parser.canonical, href)).path == list_path for href in parser.anchors):
                raise SystemExit("Location map page must link to the standalone list page")
            map_data = parser.location_data
            if not map_data or not isinstance(map_data.get("prefectures"), list):
                raise SystemExit("Location page must contain prefecture-grouped map data")
            if map_data != generated_locations:
                raise SystemExit("Embedded location map data must match generated locations.json")
            prefecture_names = [item.get("name") for item in map_data["prefectures"]]
            if map_data.get("defaultPrefecture") not in prefecture_names:
                raise SystemExit("Location map defaultPrefecture must name a generated prefecture group")
            for prefecture in map_data["prefectures"]:
                locations = prefecture.get("locations")
                if not isinstance(locations, list) or not locations:
                    raise SystemExit(f"Prefecture group {prefecture.get('name')} has no locations")
                if prefecture.get("count") != sum(location.get("count", 0) for location in locations):
                    raise SystemExit(f"Prefecture group {prefecture.get('name')} has an invalid poem count")
                for location in locations:
                    if location.get("prefecture") != prefecture.get("name"):
                        raise SystemExit(f"Location {location.get('name')} is in the wrong prefecture group")
                    if not re.fullmatch(r"\{[^{}|]+\|[^{}|]+\}", location.get("nameRuby", "")):
                        raise SystemExit(f"Location {location.get('name')} is missing its full ruby source")
                    preview_ruby = location.get("previewRuby")
                    if not isinstance(preview_ruby, list) or len(preview_ruby) != 3:
                        raise SystemExit(f"Location {location.get('name')} needs three ruby preview lines")
                    if any(not re.fullmatch(r"\{[^{}|]+\|[^{}|]+\}", line) for line in preview_ruby):
                        raise SystemExit(f"Location {location.get('name')} has an invalid ruby preview line")

        if relative == "location/list/index.html":
            types = [item for block in parser.json_ld for item in flatten_types(block)]
            if "CollectionPage" not in types or "ItemList" not in types:
                raise SystemExit("Location list page needs CollectionPage and ItemList JSON-LD")
            anchor_paths = {urlparse(urljoin(parser.canonical, href)).path for href in parser.anchors}
            missing_locations = sorted(generated_location_urls - anchor_paths)
            if missing_locations:
                raise SystemExit(f"Location list page is missing location links: {missing_locations[:5]}")
            if "/location/" not in anchor_paths:
                raise SystemExit("Location list page must link back to map mode")
            if parser.location_search_inputs != 1:
                raise SystemExit("Location list page must provide one location search input")

        for href in parser.anchors:
            target = local_target(public_root, page_path, href)
            if target is not None and not target.exists():
                missing_links.append(f"{relative} -> {href}")

    if missing_links:
        raise SystemExit("Missing internal links:\n" + "\n".join(missing_links[:20]))

    sitemap_path = public_root / "sitemap.xml"
    sitemap = ElementTree.parse(sitemap_path)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {node.text for node in sitemap.findall("sm:url/sm:loc", namespace)}
    canonical_urls = set(canonicals)
    if sitemap_urls != canonical_urls:
        missing = sorted(canonical_urls - sitemap_urls)
        extra = sorted(sitemap_urls - canonical_urls)
        raise SystemExit(f"Sitemap mismatch; missing={missing[:5]} extra={extra[:5]}")

    print(json.dumps({
        "htmlPages": len(page_paths),
        "detailPages": detail_pages,
        "feedbackForms": feedback_forms,
        "siteFeedbackForms": site_feedback_forms,
        "pagesWithReadingToggle": pages_with_reading_toggle,
        "poemsWithSeason": poems_with_season,
        "kigoLibraryEntries": len(kigo_library),
        "kigoExplanationReadings": sum(2 + len(entry["imageryReadings"]) for entry in kigo_library.values()),
        "generatedKigo": len(generated_kigo),
        "mappedLocations": len(location_map),
        "prefectureGroups": len(generated_locations["prefectures"]),
        "locationListPages": 1,
        "uniqueTitles": len(titles),
        "uniqueCanonicals": len(canonicals),
        "sitemapUrls": len(sitemap_urls),
        "brokenInternalLinks": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
