#!/usr/bin/env python3
"""Restore a local theme mirror to the live MAIN Shopify theme.

Requires token with theme:write (shopi.world Settings → Allow theme writes).

Usage:
  python3 scripts/restore_theme_mirror.py ~/dev/my-theme-mirror
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402

TEXT_SUFFIXES = {
    ".liquid", ".json", ".css", ".js", ".svg", ".txt", ".md", ".xml", ".map", ".scss", ".ts"
}
SKIP_NAMES = {"manifest.json", ".gitignore", "README.md", "LICENSE"}
# Never upload VCS, tooling, or hidden paths to Shopify.
SKIP_DIR_PARTS = frozenset({".git", "scripts", "node_modules", "__pycache__"})
MAX_BATCH_BYTES = 100_000
MAX_BATCH_FILES = 3


def is_theme_mirror_file(path: Path, root: Path) -> bool:
    if not path.is_file() or path.name in SKIP_NAMES:
        return False
    parts = path.relative_to(root).parts
    if not parts:
        return False
    if parts[0] in SKIP_DIR_PARTS:
        return False
    if any(part.startswith(".") for part in parts):
        return False
    return True


def collect_mirror_paths(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if is_theme_mirror_file(p, root))


def batch_exports(exports: list[dict], max_bytes: int = MAX_BATCH_BYTES) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for item in exports:
        est = len(json.dumps(item))
        if current and (size + est > max_bytes or len(current) >= MAX_BATCH_FILES):
            batches.append(current)
            current = []
            size = 0
        current.append(item)
        size += est
    if current:
        batches.append(current)
    return batches


def strip_leading_json_comment(body: str) -> str:
    return re.sub(r"^\uFEFF?\s*/\*[\s\S]*?\*/\s*", "", body)


def theme_json_for_upload(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        return strip_leading_json_comment(text)


def file_to_export(path: Path, root: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    if path.suffix.lower() in TEXT_SUFFIXES:
        content = theme_json_for_upload(path) if path.suffix.lower() == ".json" else path.read_text(encoding="utf-8")
        return {"filename": rel, "encoding": "text", "content": content}
    return {
        "filename": rel,
        "encoding": "base64",
        "content": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def main() -> None:
    root = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd()
    if not (root / "manifest.json").is_file():
        print(f"manifest.json not found in {root}", file=sys.stderr)
        sys.exit(1)

    paths = collect_mirror_paths(root)
    exports = [file_to_export(p, root) for p in paths]
    batches = batch_exports(exports)
    print(f"restore {len(exports)} theme files from {root} ({len(batches)} batches)")

    client = connect()
    restored = 0
    theme_gid = ""
    for batch_no, chunk in enumerate(batches, start=1):
        print(f"batch {batch_no}/{len(batches)} ({len(chunk)} files)...", flush=True)
        result = client.call_tool("restore_live_theme_mirror_files", {"files": chunk})
        theme_gid = result.get("themeGid", theme_gid)
        restored += result.get("restored", len(chunk))

    print(f"done: restored {restored} files to {theme_gid or 'live theme'}")


if __name__ == "__main__":
    main()
