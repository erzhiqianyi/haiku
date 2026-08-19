#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


FULL_RUBY_LINE = re.compile(r"^\{[^{}|]+\|[^{}|]+\}$")


def parse_args():
    parser = argparse.ArgumentParser(description="Regenerate generated haiku JSON from daily source files.")
    parser.add_argument("--repo", default=".", help="Path to the haiku repository.")
    parser.add_argument("--generated", default="public/content/haiku/generated/itsuki-haiku.json")
    parser.add_argument("--site", default="public/content/haiku/generated/site.json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def poem_key(poem):
    def display_text(value):
        return re.sub(r"\{([^{}|]+)\|[^{}|]+\}", r"\1", value)

    return "\n".join(display_text(value) for value in [poem["date"], poem["location"], *poem["lines"]])


def parse_day_file(path):
    year = path.parents[1].name
    month = path.parent.name
    day = path.stem
    source_ref = str(path.relative_to(path.parents[5]))
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) % 4 != 0:
        raise SystemExit(f"{path} must contain 4 non-empty lines per poem: location, 3 haiku lines")
    incomplete_ruby = [line for line in lines if not FULL_RUBY_LINE.fullmatch(line)]
    if incomplete_ruby:
        raise SystemExit(f"{path} must use one complete ruby annotation for every location and haiku line: {incomplete_ruby[0]}")

    poems = []
    for index in range(0, len(lines), 4):
        location, *haiku_lines = lines[index:index + 4]
        date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        poems.append({
            "source": source_ref,
            "date": date,
            "location": location,
            "lines": haiku_lines,
            "_order": len(poems),
        })
    return poems


def load_source_poems(source_root):
    poems = []
    for path in sorted(source_root.glob("*/*/*.md")):
        poems.extend(parse_day_file(path))
    return poems


def main():
    args = parse_args()
    repo = Path(args.repo).resolve()
    generated_path = repo / args.generated
    generated_root = generated_path.parent
    site_path = repo / args.site
    source_root = repo / "public" / "content" / "haiku" / "source"
    existing = json.loads(generated_path.read_text(encoding="utf-8"))
    site_meta = json.loads(site_path.read_text(encoding="utf-8")) if site_path.exists() else existing.get("meta", {})

    existing_poems = []
    if existing.get("poems"):
        existing_poems.extend(existing.get("poems", []))
    for month in existing.get("months", []):
        month_path = generated_root / month["path"]
        if month_path.exists():
            existing_poems.extend(json.loads(month_path.read_text(encoding="utf-8")).get("poems", []))
    visuals = {poem_key(poem): poem for poem in existing_poems}

    regenerated = []
    missing = []
    for poem in load_source_poems(source_root):
        visual = visuals.get(poem_key(poem))
        if not visual:
            missing.append({k: poem[k] for k in ("source", "date", "location", "lines")})
            continue
        poem.update({
            "keyword": visual["keyword"],
            "bgColor": visual["bgColor"],
            "theme": visual["theme"],
        })
        regenerated.append(poem)

    if missing:
        print(json.dumps({"missingMetadata": missing}, ensure_ascii=False, indent=2))
        raise SystemExit("Missing metadata for source poems; generate keyword/bgColor/theme first.")

    regenerated.sort(key=lambda poem: (poem["date"], -poem["_order"]), reverse=True)
    for poem in regenerated:
        poem.pop("_order", None)

    by_month = {}
    for poem in regenerated:
        month_key = poem["date"][:7].replace("-", "/")
        by_month.setdefault(month_key, []).append(poem)

    months = []
    for month_key in sorted(by_month.keys(), reverse=True):
        year, month = month_key.split("/")
        months.append({
            "id": f"{year}-{month}",
            "path": f"{year}/{month}.json",
            "count": len(by_month[month_key]),
        })

    output = {
        "meta": site_meta,
        "months": months,
    }

    if args.dry_run:
        print(json.dumps({"poems": len(regenerated), "months": months, "first": regenerated[0] if regenerated else None}, ensure_ascii=False, indent=2))
        return

    for month_key, poems in by_month.items():
        year, month = month_key.split("/")
        month_path = generated_root / year / f"{month}.json"
        month_path.parent.mkdir(parents=True, exist_ok=True)
        month_path.write_text(json.dumps({"poems": poems}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    site_path.write_text(json.dumps(site_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generated_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"generatedFile": str(generated_path), "months": len(months), "poems": len(regenerated)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
