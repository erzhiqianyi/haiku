"""Local, per-poem background asset contract shared by publishing scripts."""
import re
from pathlib import Path


def validate_background(repo, image):
    if not isinstance(image, str) or not re.fullmatch(r"/assets/images/haiku/[a-z0-9-]+\.(?:jpg|jpeg|png|webp)", image):
        raise SystemExit("backgroundImage must be a local /assets/images/haiku/<name> image URL")
    public = (Path(repo) / "public").resolve()
    path = (public / image.lstrip("/")).resolve()
    if not path.is_relative_to(public) or not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"Missing or empty haiku background: {image}")
    signatures = {".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".png": b"\x89PNG\r\n\x1a\n", ".webp": b"RIFF"}
    head = path.read_bytes()[:12]
    if not head.startswith(signatures[path.suffix]) or (path.suffix == ".webp" and head[8:12] != b"WEBP"):
        raise SystemExit(f"Invalid image file: {image}")
    return image
