#!/usr/bin/env python3
"""Download full live Shopify theme mirror via shopi-world MCP.

Usage:
  python3 scripts/download_theme_mirror.py ~/dev/my-theme-mirror
  SHOPI_MCP_TOKEN=sw_mcp_... python3 scripts/download_theme_mirror.py ./theme-mirror
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402

BATCH = 25


def write_files(root: Path, files: list[dict]) -> int:
    n = 0
    for f in files:
        dest = root / f["filename"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if f["encoding"] == "text":
            dest.write_text(f["content"], encoding="utf-8")
        else:
            dest.write_bytes(base64.b64decode(f["content"]))
        n += 1
    return n


def main() -> None:
    root = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd()
    root.mkdir(parents=True, exist_ok=True)

    client = connect()
    manifest = client.call_tool("live_theme_mirror_manifest")
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    filenames = [f["filename"] for f in manifest["files"]]
    print(f"shop: {manifest['shop']}")
    print(f"files: {len(filenames)} → {root}")

    total = 0
    missing_all: list[str] = []
    for i in range(0, len(filenames), BATCH):
        chunk = filenames[i : i + BATCH]
        batch_no = i // BATCH + 1
        batch_total = (len(filenames) + BATCH - 1) // BATCH
        print(f"batch {batch_no}/{batch_total} ({len(chunk)} files)...", flush=True)
        data = client.call_tool("read_live_theme_mirror_files", {"filenames": chunk})
        total += write_files(root, data.get("files", []))
        missing_all.extend(data.get("missing", []))

    print(f"done: wrote {total} files")
    if missing_all:
        print(f"missing ({len(missing_all)}):", ", ".join(missing_all), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
