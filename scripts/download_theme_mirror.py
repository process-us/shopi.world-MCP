#!/usr/bin/env python3
"""Download full live Shopify theme mirror via shopi-world MCP.

Usage:
  python3 scripts/download_theme_mirror.py ~/dev/my-theme-mirror
  SHOPI_MCP_TOKEN=sw_mcp_... python3 scripts/download_theme_mirror.py ./theme-mirror
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402
from mirror_download_lib import download_file_batches, save_manifest  # noqa: E402


def main() -> None:
    root = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd()
    root.mkdir(parents=True, exist_ok=True)

    client = connect()
    manifest = client.call_tool("live_theme_mirror_manifest")
    filenames = [f["filename"] for f in manifest["files"]]
    print(f"shop: {manifest['shop']}")
    print(f"files: {len(filenames)} → {root}")

    total, missing_all = download_file_batches(client.call_tool, root, filenames)
    save_manifest(root, manifest)
    print(f"done: wrote {total} files")
    if missing_all:
        print(f"missing ({len(missing_all)}):", ", ".join(missing_all), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
