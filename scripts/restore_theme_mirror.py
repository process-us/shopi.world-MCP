#!/usr/bin/env python3
"""Restore a local theme mirror to the live MAIN Shopify theme.

Requires token with theme:write (shopi.world Settings → Allow theme writes).

Usage:
  python3 scripts/restore_theme_mirror.py ~/dev/my-theme-mirror
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402

BATCH = 25
TEXT_SUFFIXES = {
    ".liquid", ".json", ".css", ".js", ".svg", ".txt", ".md", ".xml", ".map", ".scss", ".ts"
}
SKIP_NAMES = {"manifest.json", ".gitignore", "README.md", "LICENSE"}


def file_to_export(path: Path, root: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    if path.suffix.lower() in TEXT_SUFFIXES:
        return {"filename": rel, "encoding": "text", "content": path.read_text(encoding="utf-8")}
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

    paths = sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.name not in SKIP_NAMES
        and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )
    exports = [file_to_export(p, root) for p in paths]
    print(f"restore {len(exports)} files from {root}")

    client = connect()
    restored = 0
    theme_gid = ""
    for i in range(0, len(exports), BATCH):
        chunk = exports[i : i + BATCH]
        batch_no = i // BATCH + 1
        batch_total = (len(exports) + BATCH - 1) // BATCH
        print(f"batch {batch_no}/{batch_total} ({len(chunk)} files)...", flush=True)
        result = client.call_tool("restore_live_theme_mirror_files", {"files": chunk})
        theme_gid = result.get("themeGid", theme_gid)
        restored += result.get("restored", len(chunk))

    print(f"done: restored {restored} files to {theme_gid or 'live theme'}")


if __name__ == "__main__":
    main()
