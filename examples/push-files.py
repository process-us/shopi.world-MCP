#!/usr/bin/env python3
"""Push specific local theme files to the live theme (no git required).

Usage (from your theme mirror directory):
  python3 ~/dev/shopi-world-mcp/examples/push-files.py sections/header.liquid snippets/foo.liquid
  python3 ~/dev/shopi-world-mcp/examples/push-files.py assets/theme.css

Requires token with Allow theme writes. Reads SHOPI_MCP_TOKEN or ~/.cursor/mcp.json.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Allow running from any cwd — add shopi-world-mcp/scripts to path
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))
from mcp_client import connect  # noqa: E402


def prepare_json_upload(code: str) -> str:
    # Shopify locale/template JSON may start with a /* banner — MCP rejects strict JSON with it.
    return re.sub(r"^\s*/\*.*?\*/\s*", "", code, flags=re.S)


def main() -> None:
    rels = sys.argv[1:]
    if not rels:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    root = Path.cwd()
    client = connect()

    for rel in rels:
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"not found: {path}")

        code = path.read_text(encoding="utf-8")
        if rel.endswith(".json"):
            code = prepare_json_upload(code)

        result = client.call_tool("write_live_theme_file", {"file": rel, "code": code})
        nbytes = result.get("bytes", len(code.encode()))
        print(f"pushed {rel} ({nbytes} bytes)")


if __name__ == "__main__":
    main()
