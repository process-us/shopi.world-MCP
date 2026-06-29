#!/usr/bin/env python3
"""Download only changed live theme files via shopi-world MCP (checksum delta).

Compares remote manifest checksumMd5 to local manifest.json from the last sync.
Falls back to full download when manifest.json is missing or themeGid changed.

Usage:
  python3 scripts/download_changed.py ~/dev/my-theme-mirror
  python3 scripts/download_changed.py ~/dev/my-theme-mirror --dry-run
  python3 scripts/download_changed.py ~/dev/my-theme-mirror --full
  python3 scripts/download_changed.py ~/dev/my-theme-mirror --delete-removed
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402
from mirror_download_lib import (  # noqa: E402
    compute_download_delta,
    download_file_batches,
    load_local_manifest,
    save_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delta-download changed live theme files from Shopify via MCP"
    )
    parser.add_argument(
        "mirror",
        nargs="?",
        default=".",
        help="Path to theme mirror directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without fetching file bodies",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full download (ignore local manifest checksums)",
    )
    parser.add_argument(
        "--delete-removed",
        action="store_true",
        help="Delete local theme files removed from the live theme",
    )
    args = parser.parse_args()

    root = Path(args.mirror).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    old = load_local_manifest(root)
    client = connect()
    new = client.call_tool("live_theme_mirror_manifest")

    to_fetch, removed, mode = compute_download_delta(old, new, force_full=args.full)
    print(f"shop: {new['shop']}")
    print(f"sync: {mode} — {len(to_fetch)} to download, {len(removed)} removed on Shopify")

    if to_fetch:
        print("download:")
        for fn in to_fetch:
            print(f"  {fn}")
    if removed:
        print("removed on Shopify (local copy kept unless --delete-removed):")
        for fn in removed:
            print(f"  {fn}")

    if args.dry_run:
        print("dry-run — manifest and files not updated")
        return

    if removed and args.delete_removed:
        for fn in removed:
            path = root / fn
            if path.is_file():
                path.unlink()
                print(f"deleted local: {fn}")

    total, missing_all = download_file_batches(client.call_tool, root, to_fetch)
    save_manifest(root, new)
    print(f"done: wrote {total} file(s), manifest updated ({new['exportedAt']})")
    if missing_all:
        print(f"missing ({len(missing_all)}):", ", ".join(missing_all), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
