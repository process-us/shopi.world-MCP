"""Port of shopi.world/server/theme-markup-localize.ts — multi-locale {% case %} wrappers."""
from __future__ import annotations

import re
from collections import defaultdict

from locale_text_detect import is_translatable_run, locale_base, split_core

LOCALE_GUARD = "request.locale.iso_code"

RAW_BLOCK_RE = re.compile(
    r"(\{%-?\s*raw\s*-?%\})([\s\S]*?)(\{%-?\s*endraw\s*-?%\})",
    re.IGNORECASE,
)

TOKEN_RE = re.compile(
    "|".join(
        [
            r"\{%-?\s*case\s+request\.locale\.iso_code\s*-?%\}[\s\S]*?\{%-?\s*endcase\s*-?%\}",
            r"\{%-?\s*if\s+request\.locale\.iso_code\s*==\s*'[^']*'\s*-?%\}[\s\S]*?\{%-?\s*endif\s*-?%\}",
            r"<style[\s\S]*?</style>",
            r"<script[\s\S]*?</script>",
            r"<!--[\s\S]*?-->",
            r"\{%-?\s*comment\s*-?%\}[\s\S]*?\{%-?\s*endcomment\s*-?%\}",
            r"\{%-?\s*schema\s*-?%\}[\s\S]*?\{%-?\s*endschema\s*-?%\}",
            r"\{%-?\s*stylesheet[\s\S]*?\{%-?\s*endstylesheet\s*-?%\}",
            r"\{%-?\s*javascript\s*-?%\}[\s\S]*?\{%-?\s*endjavascript\s*-?%\}",
            r"<[^>]+>",
            r"\{\{[\s\S]*?\}\}",
            r"\{%[\s\S]*?%\}",
        ]
    ),
    re.IGNORECASE,
)

CASE_FENCED_RE = re.compile(
    r"\{%-?\s*endraw\s*-?%\}\{%-?\s*case\s+request\.locale\.iso_code\s*-?%\}[\s\S]*?\{%-?\s*else\s*-?%\}([\s\S]*?)\{%-?\s*endcase\s*-?%\}\{%-?\s*raw\s*-?%\}",
    re.IGNORECASE,
)
CASE_PLAIN_RE = re.compile(
    r"\{%-?\s*case\s+request\.locale\.iso_code\s*-?%\}[\s\S]*?\{%-?\s*else\s*-?%\}([\s\S]*?)\{%-?\s*endcase\s*-?%\}",
    re.IGNORECASE,
)
COND_FENCED_RE = re.compile(
    r"\{%-?\s*endraw\s*-?%\}\{%-?\s*if\s+request\.locale\.iso_code\s*==\s*'([^']*)'\s*-?%\}([\s\S]*?)\{%-?\s*else\s*-?%\}([\s\S]*?)\{%-?\s*endif\s*-?%\}\{%-?\s*raw\s*-?%\}",
    re.IGNORECASE,
)
COND_PLAIN_RE = re.compile(
    r"\{%-?\s*if\s+request\.locale\.iso_code\s*==\s*'([^']*)'\s*-?%\}([\s\S]*?)\{%-?\s*else\s*-?%\}([\s\S]*?)\{%-?\s*endif\s*-?%\}",
    re.IGNORECASE,
)
WHEN_RE = re.compile(
    r"\{%-?\s*when\s+'([^']+)'\s*-?%\}([\s\S]*?)(?=\{%-?\s*when\s+'|\{%-?\s*else\s*-?%|\{%-?\s*endcase\s*-?%|$)",
    re.IGNORECASE,
)
CASE_INNER_RE = re.compile(
    r"\{%-?\s*case\s+request\.locale\.iso_code\s*-?%\}([\s\S]*?)\{%-?\s*else\s*-?%\}",
    re.IGNORECASE,
)


def _trim_core(s: str) -> str:
    return split_core(s)[1]


def collect_locale_variants(markup: str) -> dict[str, dict[str, str]]:
    """source core → locale base → translated text."""
    variants: dict[str, dict[str, str]] = defaultdict(dict)

    def add(source: str, locale: str, translated: str) -> None:
        core = _trim_core(source)
        text = _trim_core(translated)
        if not core or not text:
            return
        variants[core][locale_base(locale)] = text

    for m in COND_PLAIN_RE.finditer(markup):
        add(m.group(3), m.group(1), m.group(2))
    for m in COND_FENCED_RE.finditer(markup):
        add(m.group(3), m.group(1), m.group(2))

    def parse_case(full: str, else_source: str) -> None:
        inner_m = CASE_INNER_RE.search(full)
        if not inner_m:
            return
        for w in WHEN_RE.finditer(inner_m.group(1)):
            add(else_source, w.group(1), w.group(2))

    for m in CASE_PLAIN_RE.finditer(markup):
        parse_case(m.group(0), m.group(1))
    for m in CASE_FENCED_RE.finditer(markup):
        parse_case(m.group(0), m.group(1))

    return dict(variants)


def unwrap_locale_conditionals(markup: str) -> str:
    if not markup or LOCALE_GUARD not in markup:
        return markup
    markup = CASE_FENCED_RE.sub(r"\1", markup)
    markup = CASE_PLAIN_RE.sub(r"\1", markup)
    markup = COND_FENCED_RE.sub(r"\3", markup)
    return COND_PLAIN_RE.sub(r"\3", markup)


def _walk_chunk(text: str, in_raw: bool, on_text):
    out = []
    last = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > last:
            out.append(on_text(text[last : m.start()], in_raw))
        out.append(m.group(0))
        last = m.end()
    if last < len(text):
        out.append(on_text(text[last:], in_raw))
    return "".join(out)


def _transform(markup: str, on_text):
    out = []
    last = 0
    for m in RAW_BLOCK_RE.finditer(markup):
        out.append(_walk_chunk(markup[last : m.start()], False, on_text))
        out.append(m.group(1))
        out.append(_walk_chunk(m.group(2), True, on_text))
        out.append(m.group(3))
        last = m.end()
    out.append(_walk_chunk(markup[last:], False, on_text))
    return "".join(out)


def extract_translatable_runs(markup: str, primary_locale: str) -> list[str]:
    runs: set[str] = set()

    def on_text(text: str, _in_raw: bool) -> str:
        if is_translatable_run(text, primary_locale):
            runs.add(split_core(text)[1])
        return text

    _transform(markup, on_text)
    return sorted(runs)


def extract_hebrew_runs(markup: str) -> list[str]:
    return extract_translatable_runs(markup, "he")


def localize_markup(
    markup: str,
    *,
    primary_locale: str,
    target_locale: str,
    translations: dict[str, str],
) -> tuple[str, int]:
    if not markup:
        return markup, 0

    preserved = collect_locale_variants(markup)
    base = locale_base(target_locale)
    wrapped = 0
    unwrapped = unwrap_locale_conditionals(markup)

    def on_text(text: str, in_raw: bool) -> str:
        nonlocal wrapped
        if not is_translatable_run(text, primary_locale):
            return text
        lead, core, trail = split_core(text)
        target = translations.get(core)
        if not target or not target.strip() or target.strip() == core:
            return text

        row = dict(preserved.get(core, {}))
        row[base] = target.strip()
        wrapped += 1

        whens = "".join(
            f"{{% when '{loc}' %}}{txt}"
            for loc, txt in sorted(row.items())
        )
        cond = f"{{% case request.locale.iso_code %}}{whens}{{% else %}}{core}{{% endcase %}}"
        if in_raw:
            return f"{lead}{{% endraw %}}{cond}{{% raw %}}{trail}"
        return f"{lead}{cond}{trail}"

    return _transform(unwrapped, on_text), wrapped
