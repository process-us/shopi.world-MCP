#!/usr/bin/env python3
"""Wrap primary-locale copy in {% case request.locale.iso_code %} for offline theme mirrors.

Port of shopi.world theme-content-localize (markup path only). Use with glossary JSON;
push results via restore_changed.py.

Examples:
  # List strings to translate (build your glossary)
  python3 scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --list-runs

  # Apply Arabic from a flat glossary
  python3 scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --target ar \\
    --glossary ./glossary-ar.json

  # Multiple targets (nested glossary or per-locale files in --glossary-dir)
  python3 scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --target ar,fr \\
    --glossary ./glossary.json

  # Homepage only (templates/index.json)
  python3 scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --target ar \\
    --glossary ./glossary-ar.json --scope homepage

  # Preview without writing
  python3 scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --target ar \\
    --glossary ./glossary-ar.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from theme_markup_localize import (  # noqa: E402
    extract_translatable_runs,
    localize_markup,
    unwrap_locale_conditionals,
)

CUSTOM_LIQUID_TYPES = {"custom-liquid", "custom_liquid"}


def load_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if "*/" in text:
        text = text.split("*/", 1)[1]
    return json.loads(text.strip())


def save_json(path: Path, data: dict, with_header: bool) -> None:
    header = ""
    if with_header:
        raw = path.read_text(encoding="utf-8")
        header = raw.split("*/", 1)[0] + "*/\n" if "*/" in raw else ""
    path.write_text(header + json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def custom_liquid_setters(node: dict) -> list:
    if not isinstance(node, dict) or node.get("type") not in CUSTOM_LIQUID_TYPES:
        return []
    settings = node.setdefault("settings", {})
    val = settings.get("custom_liquid")
    if not isinstance(val, str) or not val.strip():
        return []
    return [(val, lambda v, s=settings: s.__setitem__("custom_liquid", v))]


def collect_json_setters(data: dict) -> list:
    out = []
    for section in (data.get("sections") or {}).values():
        if not isinstance(section, dict):
            continue
        out.extend(custom_liquid_setters(section))
        for block in (section.get("blocks") or {}).values():
            out.extend(custom_liquid_setters(block))
    return out


def target_paths(root: Path, scope: str, extra_globs: list[str]) -> list[Path]:
    if scope == "homepage":
        paths = [root / "templates/index.json"]
        return [p for p in paths if p.exists()]

    paths: list[Path] = []
    paths.extend(root.glob("templates/*.json"))
    paths.extend(root.glob("sections/*.json"))
    paths.extend(root.glob("sections/*.liquid"))
    for pattern in extra_globs:
        paths.extend(root.glob(pattern))
    return sorted(set(p for p in paths if p.is_file()))


def load_glossary_for_target(
    glossary_path: Path | None,
    glossary_dir: Path | None,
    target: str,
    all_targets: list[str],
) -> dict[str, str]:
    base = target.lower().split("-")[0]

    if glossary_dir:
        per_locale = glossary_dir / f"{base}.json"
        if per_locale.exists():
            data = json.loads(per_locale.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        raise SystemExit(f"missing glossary file: {per_locale}")

    if not glossary_path:
        raise SystemExit("--glossary or --glossary-dir required unless --list-runs")

    raw = json.loads(glossary_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"glossary must be a JSON object: {glossary_path}")

    if len(all_targets) == 1:
        return {str(k): str(v) for k, v in raw.items()}

    nested = raw.get(base)
    if isinstance(nested, dict):
        return {str(k): str(v) for k, v in nested.items()}

    # Flat glossary reused for every target (unusual but allowed)
    if all(isinstance(v, str) for v in raw.values()):
        return {str(k): str(v) for k, v in raw.items()}

    raise SystemExit(
        f"glossary {glossary_path} must nest translations under '{base}' "
        f"when using multiple --target locales"
    )


def localize_path(
    path: Path,
    *,
    primary_locale: str,
    target_locale: str,
    translations: dict[str, str],
    dry_run: bool,
) -> int:
    if path.suffix == ".json":
        raw = path.read_text(encoding="utf-8")
        has_header = "*/" in raw
        data = load_json(path)
        wrapped = 0
        for value, setter in collect_json_setters(data):
            out, n = localize_markup(
                unwrap_locale_conditionals(value),
                primary_locale=primary_locale,
                target_locale=target_locale,
                translations=translations,
            )
            if n:
                if not dry_run:
                    setter(out)
                wrapped += n
        if wrapped and not dry_run:
            save_json(path, data, has_header)
        return wrapped

    if path.suffix == ".liquid":
        raw = path.read_text(encoding="utf-8")
        out, n = localize_markup(
            unwrap_locale_conditionals(raw),
            primary_locale=primary_locale,
            target_locale=target_locale,
            translations=translations,
        )
        if n and not dry_run:
            path.write_text(out, encoding="utf-8")
        return n

    return 0


def collect_all_runs(paths: list[Path], primary_locale: str) -> list[str]:
    runs: set[str] = set()
    for path in paths:
        if path.suffix == ".json":
            data = load_json(path)
            for value, _ in collect_json_setters(data):
                runs.update(extract_translatable_runs(value, primary_locale))
        elif path.suffix == ".liquid":
            runs.update(
                extract_translatable_runs(path.read_text(encoding="utf-8"), primary_locale)
            )
    return sorted(runs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mirror", type=Path, required=True, help="Local theme mirror root")
    parser.add_argument("--primary", default="he", help="Primary locale (source script), default: he")
    parser.add_argument("--target", help="Comma-separated target locales, e.g. ar or ar,fr")
    parser.add_argument("--glossary", type=Path, help="Glossary JSON (flat or nested by locale)")
    parser.add_argument(
        "--glossary-dir",
        type=Path,
        help="Directory with per-locale files, e.g. ar.json, fr.json",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "homepage"),
        default="all",
        help="all = templates + sections JSON/Liquid; homepage = index.json only",
    )
    parser.add_argument(
        "--extra-glob",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Extra glob under mirror root (repeatable), e.g. 'snippets/shopi*.liquid'",
    )
    parser.add_argument("--list-runs", action="store_true", help="Print unique source strings as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    args = parser.parse_args()

    root = args.mirror.resolve()
    if not root.is_dir():
        raise SystemExit(f"mirror not found: {root}")

    paths = target_paths(root, args.scope, args.extra_glob)
    if not paths:
        raise SystemExit(f"no theme files under {root} (scope={args.scope})")

    if args.list_runs:
        runs = collect_all_runs(paths, args.primary)
        print(json.dumps(runs, ensure_ascii=False, indent=2))
        print(f"# {len(runs)} unique runs in {len(paths)} files", file=sys.stderr)
        return

    if not args.target:
        raise SystemExit("--target is required unless --list-runs")

    targets = [t.strip() for t in args.target.split(",") if t.strip()]
    if not targets:
        raise SystemExit("no locales in --target")

    total_runs = 0
    total_files = 0

    for target in targets:
        glossary = load_glossary_for_target(args.glossary, args.glossary_dir, target, targets)
        if not glossary:
            print(f"warning: empty glossary for {target}", file=sys.stderr)

        locale_files = 0
        locale_runs = 0
        for path in paths:
            n = localize_path(
                path,
                primary_locale=args.primary,
                target_locale=target,
                translations=glossary,
                dry_run=args.dry_run,
            )
            if n:
                rel = path.relative_to(root)
                mode = "would localize" if args.dry_run else "localized"
                print(f"{mode}: {rel} ({n} runs) → {target}")
                locale_runs += n
                locale_files += 1

        total_runs += locale_runs
        total_files = max(total_files, locale_files)
        print(f"target {target}: {locale_files} files, {locale_runs} runs wrapped")

    suffix = " (dry run)" if args.dry_run else ""
    print(
        f"done — primary={args.primary} targets={','.join(targets)} "
        f"scope={args.scope}{suffix}"
    )
    if not args.dry_run and total_runs:
        print(
            "next: review git diff, then push with "
            "python3 scripts/restore_changed.py <mirror>"
        )


if __name__ == "__main__":
    main()
