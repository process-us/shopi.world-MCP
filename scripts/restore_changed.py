#!/usr/bin/env python3
"""Push only git-changed theme files from a local mirror to the live Shopify theme.

Requires token with theme:write (shopi.world Settings → Allow theme writes).

Usage:
  python3 scripts/restore_changed.py ~/dev/shopify-theme-mirror
  python3 scripts/restore_changed.py ~/dev/shopify-theme-mirror --dry-run
  python3 scripts/restore_changed.py ~/dev/shopify-theme-mirror --against origin/main

Compares the working tree to --against (default HEAD): unstaged + staged + untracked
theme files. Skips .git/, scripts/, manifest.json, and other non-theme paths (same
rules as restore_theme_mirror.py). Does not upload deletions — Shopify files are
never removed by restore.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402
from restore_theme_mirror import (  # noqa: E402
    batch_exports,
    file_to_export,
    is_theme_mirror_file,
)


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def collect_git_changed_paths(root: Path, against: str) -> list[Path]:
    if not (root / ".git").is_dir():
        raise SystemExit(f"not a git repository: {root}")

    rels: set[str] = set()
    for line in git_output(root, "diff", "--name-only", against).splitlines():
        if line.strip():
            rels.add(line.strip())
    for line in git_output(root, "diff", "--name-only", "--cached", against).splitlines():
        if line.strip():
            rels.add(line.strip())
    for line in git_output(root, "ls-files", "--others", "--exclude-standard").splitlines():
        if line.strip():
            rels.add(line.strip())

    paths: list[Path] = []
    for rel in sorted(rels):
        path = root / rel
        if path.is_file() and is_theme_mirror_file(path, root):
            paths.append(path)
    return paths


def restore_paths(root: Path, paths: list[Path], *, dry_run: bool) -> None:
    if not paths:
        print("no changed theme files to restore")
        return

    print(f"restore {len(paths)} changed theme file(s) from {root}:")
    for p in paths:
        print(f"  {p.relative_to(root).as_posix()}")

    if dry_run:
        print("dry-run — nothing uploaded")
        return

    exports = [file_to_export(p, root) for p in paths]
    batches = batch_exports(exports)
    print(f"uploading in {len(batches)} batch(es)...")

    client = connect()
    restored = 0
    theme_gid = ""
    for batch_no, chunk in enumerate(batches, start=1):
        print(f"batch {batch_no}/{len(batches)} ({len(chunk)} files)...", flush=True)
        result = client.call_tool("restore_live_theme_mirror_files", {"files": chunk})
        theme_gid = result.get("themeGid", theme_gid)
        restored += result.get("restored", len(chunk))

    print(f"done: restored {restored} files to {theme_gid or 'live theme'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore git-changed theme mirror files to Shopify")
    parser.add_argument(
        "mirror",
        nargs="?",
        default=".",
        help="Path to theme mirror (must contain manifest.json)",
    )
    parser.add_argument(
        "--against",
        default="HEAD",
        help="Git ref to compare against (default: HEAD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded without calling MCP",
    )
    args = parser.parse_args()

    root = Path(args.mirror).expanduser().resolve()
    if not (root / "manifest.json").is_file():
        raise SystemExit(f"manifest.json not found in {root}")

    paths = collect_git_changed_paths(root, args.against)
    restore_paths(root, paths, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
