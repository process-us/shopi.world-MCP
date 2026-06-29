"""Detect translatable text runs from a store's primary locale script (port of shopi.world locale-text-detect.ts)."""
from __future__ import annotations

import re

SCRIPT_BY_LOCALE: dict[str, re.Pattern[str]] = {
    "he": re.compile(r"[\u0590-\u05FF]"),
    "iw": re.compile(r"[\u0590-\u05FF]"),
    "ar": re.compile(r"[\u0600-\u06FF\u0750-\u077F]"),
    "fa": re.compile(r"[\u0600-\u06FF\u0750-\u077F]"),
    "ru": re.compile(r"[\u0400-\u04FF]"),
    "uk": re.compile(r"[\u0400-\u04FF]"),
    "ja": re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF]"),
    "zh": re.compile(r"[\u4E00-\u9FFF]"),
    "ko": re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF]"),
    "th": re.compile(r"[\u0E00-\u0E7F]"),
    "el": re.compile(r"[\u0370-\u03FF]"),
}

LATIN_LETTERS = re.compile(r"[A-Za-z\u00C0-\u024F]")
NON_LATIN_PRIMARY = set(SCRIPT_BY_LOCALE)


def locale_base(code: str) -> str:
    return code.lower().replace("_", "-").split("-")[0]


def script_re_for_primary_locale(primary_locale: str) -> re.Pattern[str]:
    base = locale_base(primary_locale)
    return SCRIPT_BY_LOCALE.get(base, LATIN_LETTERS)


def split_core(text: str) -> tuple[str, str, str]:
    lead = re.match(r"^\s*", text).group(0)  # type: ignore[union-attr]
    trail = re.search(r"\s*$", text).group(0)  # type: ignore[union-attr]
    core = text[len(lead) : len(text) - len(trail)]
    return lead, core, trail


def is_translatable_run(text: str, primary_locale: str) -> bool:
    _, core, _ = split_core(text)
    if len(core) < 2:
        return False
    if re.match(r"^https?://", core, re.IGNORECASE):
        return False
    if re.fullmatch(r"[\d\s.,:;+\-/%()]+", core):
        return False

    base = locale_base(primary_locale)
    primary_script = script_re_for_primary_locale(primary_locale)

    if base in NON_LATIN_PRIMARY:
        return bool(primary_script.search(core))
    return bool(LATIN_LETTERS.search(core))
