#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


FULL_RUBY_LINE = re.compile(r"^\{[^{}|]+\|[^{}|]+\}$")


def parse_args():
    parser = argparse.ArgumentParser(description="Append selected haiku to source files and generated site data.")
    parser.add_argument("--repo", default=".", help="Path to the haiku repository.")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format.")
    parser.add_argument("--location", required=True)
    parser.add_argument("--line", action="append", required=True, help="Haiku line. Pass exactly three times.")
    parser.add_argument("--keyword", required=True, help="One kanji watermark keyword.")
    parser.add_argument("--bg-color", required=True, help="Hex background color.")
    parser.add_argument("--theme", choices=["light", "dark"], required=True)
    parser.add_argument("--generated", default="public/content/haiku/generated/itsuki-haiku.json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate(args):
    parts = args.date.split("-")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise SystemExit("--date must be YYYY-MM-DD")
    if len(args.line) != 3:
        raise SystemExit("--line must be passed exactly three times")
    for label, value in [("--location", args.location), *(('--line', line) for line in args.line)]:
        if not FULL_RUBY_LINE.fullmatch(value):
            raise SystemExit(f"{label} must be one complete ruby annotation: {{display text|full hiragana reading}}")
    if len(args.keyword) != 1:
        raise SystemExit("--keyword must be exactly one character")
    if not args.bg_color.startswith("#") or len(args.bg_color) != 7:
        raise SystemExit("--bg-color must be a #RRGGBB hex color")


def source_path(repo, date):
    year, month, day = date.split("-")
    return repo / "public" / "content" / "haiku" / "source" / year / month / f"{day}.md"


def source_ref(date):
    year, month, day = date.split("-")
    return f"content/haiku/source/{year}/{month}/{day}.md"


def append_source(path, location, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    block = "\n".join([location, "", *lines]).rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8").strip():
        text = path.read_text(encoding="utf-8").rstrip() + "\n\n" + block
    else:
        text = block
    path.write_text(text, encoding="utf-8")


def poem_sort_key(poem):
    source = poem.get("source", "")
    # Preserve same-day insertion order by keeping the current list stable.
    return poem.get("date", ""), source


def update_generated(path, poem):
    generated_root = path.parent
    data = json.loads(path.read_text(encoding="utf-8"))
    month_id = poem["date"][:7]
    month_path = generated_root / month_id[:4] / f"{month_id[5:7]}.json"
    if month_path.exists():
        month_data = json.loads(month_path.read_text(encoding="utf-8"))
    else:
        month_data = {"poems": []}
    poems = month_data.setdefault("poems", [])
    poems.append(poem)
    poems.sort(key=poem_sort_key, reverse=True)
    month_path.parent.mkdir(parents=True, exist_ok=True)
    month_path.write_text(json.dumps(month_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    months = [month for month in data.get("months", []) if month.get("id") != month_id]
    months.append({"id": month_id, "path": f"{month_id[:4]}/{month_id[5:7]}.json", "count": len(poems)})
    months.sort(key=lambda month: month["id"], reverse=True)
    data["months"] = months
    data.pop("poems", None)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    validate(args)
    repo = Path(args.repo).resolve()
    generated_path = repo / args.generated
    src_path = source_path(repo, args.date)
    poem = {
        "source": source_ref(args.date),
        "date": args.date,
        "location": args.location,
        "keyword": args.keyword,
        "bgColor": args.bg_color,
        "theme": args.theme,
        "lines": args.line,
    }

    if args.dry_run:
        print(json.dumps({"sourceFile": str(src_path), "generatedFile": str(generated_path), "poem": poem}, ensure_ascii=False, indent=2))
        return

    append_source(src_path, args.location, args.line)
    update_generated(generated_path, poem)
    print(json.dumps({"sourceFile": str(src_path), "generatedFile": str(generated_path), "poem": poem}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
