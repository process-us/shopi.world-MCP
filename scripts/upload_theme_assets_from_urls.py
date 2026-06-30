#!/usr/bin/env python3
"""Upload large theme assets via shopi.world MCP (server-side download; no payload limit)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import connect  # noqa: E402

HOME_CATEGORY_ASSETS = [
    {
        "filename": "assets/home-cat-liposomal.jpg",
        "url": "https://kapps.com/wp-content/uploads/2025/07/%D7%A7%D7%98%D7%92%D7%95%D7%A8%D7%99%D7%95%D7%AA-%D7%9C%D7%99%D7%A4%D7%95%D7%96%D7%95%D7%9E%D7%9C%D7%99.jpg",
    },
    {
        "filename": "assets/home-cat-vitamins.jpg",
        "url": "https://kapps.com/wp-content/uploads/2025/07/%D7%A7%D7%98%D7%92%D7%95%D7%A8%D7%99%D7%95%D7%AA-%D7%95%D7%99%D7%98%D7%9E%D7%99%D7%A0%D7%99%D7%9D.jpg",
    },
    {
        "filename": "assets/home-cat-formulas.jpg",
        "url": "https://kapps.com/wp-content/uploads/2025/07/%D7%A7%D7%98%D7%92%D7%95%D7%A8%D7%99%D7%95%D7%AA-%D7%A4%D7%95%D7%A8%D7%9E%D7%95%D7%9C%D7%95%D7%AA-1.jpg",
    },
]


def main() -> None:
    files = HOME_CATEGORY_ASSETS
    if len(sys.argv) > 1 and sys.argv[1] == "--manifest":
        manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        files = manifest["files"]
    client = connect()
    result = client.call_tool("upload_theme_assets_from_urls", {"files": files})
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
