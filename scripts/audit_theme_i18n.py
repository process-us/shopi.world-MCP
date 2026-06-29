#!/usr/bin/env python3
"""Audit a local theme mirror for greenfield i18n readiness.

Flags hardcoded copy in Liquid / custom_liquid that should use `| t` or locale JSON.
Complements shopi.world theme profile detection on the live theme.

Usage:
  python3 scripts/audit_theme_i18n.py ~/dev/my-theme-mirror
  python3 scripts/audit_theme_i18n.py ~/dev/my-theme-mirror --primary he --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from theme_markup_localize import extract_translatable_runs  # noqa: E402

CUSTOM_LIQUID_TYPES = {"custom-liquid", "custom_liquid"}
T_FILTER_RE = __import__("re").compile(r"\|\s*t\b")
LOCALE_GUARD = "request.locale.iso_code"


def load_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if "*/" in text:
        text = text.split("*/", 1)[1]
    return json.loads(text.strip())


def collect_custom_liquid(json_data: dict) -> list[tuple[str, str]]:
    """(section path, liquid value)"""
    out: list[tuple[str, str]] = []
    sections = json_data.get("sections") or {}
    for sid, section in sections.items():
        if not isinstance(section, dict):
            continue
        if section.get("type") in CUSTOM_LIQUID_TYPES:
            val = (section.get("settings") or {}).get("custom_liquid")
            if isinstance(val, str) and val.strip():
                out.append((f"section:{sid}", val))
        for bid, block in (section.get("blocks") or {}).items():
            if not isinstance(block, dict) or block.get("type") not in CUSTOM_LIQUID_TYPES:
                continue
            val = (block.get("settings") or {}).get("custom_liquid")
            if isinstance(val, str) and val.strip():
                out.append((f"block:{sid}/{bid}", val))
    return out


def audit_mirror(root: Path, primary: str) -> dict:
    locale_files = list(root.glob("locales/*.json"))
    t_uses = 0
    findings: list[dict] = []
    shopi_markers = 0

    for pattern in ("snippets/shopi*.liquid", "snippets/kapps*.liquid", "sections/*shopi*.liquid"):
        shopi_markers += len(list(root.glob(pattern)))

    json_paths = sorted(set(root.glob("templates/*.json")) | set(root.glob("sections/*.json")))
    liquid_paths = sorted(root.glob("sections/*.liquid"))[:60]

    for path in json_paths:
        try:
            data = load_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        rel = str(path.relative_to(root))
        for loc, value in collect_custom_liquid(data):
            runs = extract_translatable_runs(value, primary)
            if runs:
                findings.append({
                    "file": rel,
                    "location": loc,
                    "kind": "custom_liquid",
                    "runs": runs[:5],
                    "runCount": len(runs),
                })

    for path in liquid_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        t_uses += len(T_FILTER_RE.findall(text))
        runs = extract_translatable_runs(text, primary)
        if runs and LOCALE_GUARD not in text:
            findings.append({
                "file": str(path.relative_to(root)),
                "location": "liquid",
                "kind": "section",
                "runs": runs[:5],
                "runCount": len(runs),
            })

    total_runs = sum(f["runCount"] for f in findings)
    profile = "greenfield"
    if shopi_markers or total_runs >= 3:
        profile = "cloned" if t_uses < 20 else "mixed"
    elif total_runs > 0:
        profile = "mixed"

    return {
        "profile": profile,
        "primaryLocale": primary,
        "localeJsonFiles": len(locale_files),
        "tFilterUses": t_uses,
        "shopiThemeMarkers": shopi_markers,
        "translatableRuns": total_runs,
        "findingCount": len(findings),
        "findings": findings,
        "recommendation": _recommendation(profile, total_runs, t_uses),
    }


def _recommendation(profile: str, runs: int, t_uses: int) -> str:
    if profile == "greenfield":
        return "Theme looks i18n-ready. Use bootstrap + theme-translations; avoid theme-content."
    if profile == "cloned":
        return f"Found {runs} baked-in text run(s). Use theme-content or localize_theme.py before relying on t-filter only."
    return f"Mixed: {t_uses} t-filter uses and {runs} baked-in run(s). Migrate custom_liquid to locale keys over time."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mirror", type=Path, help="Theme mirror root")
    parser.add_argument("--primary", default="he", help="Primary locale for script detection (default: he)")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    root = args.mirror.resolve()
    if not root.is_dir():
        raise SystemExit(f"mirror not found: {root}")

    report = audit_mirror(root, args.primary)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print(f"Profile: {report['profile']}")
    print(f"Locale JSON files: {report['localeJsonFiles']}")
    print(f"t-filter uses (sampled sections): {report['tFilterUses']}")
    print(f"Baked-in translatable runs: {report['translatableRuns']}")
    print(f"shopi/kapps theme markers: {report['shopiThemeMarkers']}")
    print()
    print(report["recommendation"])
    print()
    if report["findings"]:
        print("Findings:")
        for f in report["findings"][:25]:
            sample = f["runs"][0] if f["runs"] else ""
            if len(sample) > 80:
                sample = sample[:77] + "…"
            print(f"  {f['file']} ({f['location']}): {f['runCount']} run(s) — e.g. {sample!r}")
        if len(report["findings"]) > 25:
            print(f"  … and {len(report['findings']) - 25} more (use --json)")


if __name__ == "__main__":
    main()
