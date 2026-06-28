import base64
from pathlib import Path


def write_mirror_file(root: Path, file: dict) -> None:
    """Write one file from read_live_theme_mirror_files response."""
    dest = root / file["filename"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if file["encoding"] == "text":
        dest.write_text(file["content"], encoding="utf-8")
    else:
        dest.write_bytes(base64.b64decode(file["content"]))
