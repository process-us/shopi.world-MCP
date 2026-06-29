"""Shared theme mirror download helpers (delta + full)."""
from __future__ import annotations

import base64
import json
from collections.abc import Callable
from pathlib import Path

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


def load_local_manifest(root: Path) -> dict | None:
    path = root / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(root: Path, manifest: dict) -> None:
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def file_needs_fetch(old: dict | None, new: dict) -> bool:
    if old is None:
        return True
    old_cs, new_cs = old.get("checksumMd5"), new.get("checksumMd5")
    if old_cs and new_cs:
        return old_cs != new_cs
    return old.get("size") != new.get("size")


def compute_download_delta(
    old: dict | None,
    new: dict,
    *,
    force_full: bool = False,
) -> tuple[list[str], list[str], str]:
    """Return (to_fetch, removed, mode) where mode is 'full' or 'delta'."""
    all_names = [f["filename"] for f in new["files"]]
    if force_full or old is None:
        return all_names, [], "full"
    if old.get("themeGid") != new.get("themeGid"):
        return all_names, [], "full"

    old_by_name = {f["filename"]: f for f in old.get("files", [])}
    new_by_name = {f["filename"]: f for f in new["files"]}

    to_fetch = [fn for fn, meta in new_by_name.items() if file_needs_fetch(old_by_name.get(fn), meta)]
    removed = sorted(set(old_by_name) - set(new_by_name))
    return to_fetch, removed, "delta"


def download_file_batches(
    call_tool: Callable[[str, dict], dict],
    root: Path,
    filenames: list[str],
    *,
    dry_run: bool = False,
) -> tuple[int, list[str]]:
    if not filenames:
        return 0, []
    if dry_run:
        return 0, []

    total = 0
    missing_all: list[str] = []
    for i in range(0, len(filenames), BATCH):
        chunk = filenames[i : i + BATCH]
        batch_no = i // BATCH + 1
        batch_total = (len(filenames) + BATCH - 1) // BATCH
        print(f"batch {batch_no}/{batch_total} ({len(chunk)} files)...", flush=True)
        data = call_tool("read_live_theme_mirror_files", {"filenames": chunk})
        total += write_files(root, data.get("files", []))
        missing_all.extend(data.get("missing", []))
    return total, missing_all
