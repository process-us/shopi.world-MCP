"""Minimal shopi.world MCP HTTP client (stdlib only)."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

DEFAULT_MCP_URL = "https://fronts.me/shopify/mcp"


def mcp_url() -> str:
    return os.environ.get("SHOPI_MCP_URL", DEFAULT_MCP_URL)


def load_token() -> str:
    if token := os.environ.get("SHOPI_MCP_TOKEN"):
        return token.strip()
    cfg_path = Path.home() / ".cursor" / "mcp.json"
    if not cfg_path.is_file():
        raise RuntimeError(
            "No token found. Set SHOPI_MCP_TOKEN or add shopi-world to ~/.cursor/mcp.json "
            "(see examples/mcp.json.example)"
        )
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    auth = cfg["mcpServers"]["shopi-world"]["headers"]["Authorization"]
    return auth.split(" ", 1)[1]


class ShopiWorldMcpClient:
    def __init__(self, token: str, url: str | None = None):
        self.url = url or mcp_url()
        self.token = token
        self.cookie: str | None = None
        self.req_id = 0

    def _post(self, body: dict) -> dict:
        self.req_id += 1
        payload = {**body, "jsonrpc": "2.0", "id": self.req_id}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=300) as res:
            if set_cookie := res.headers.get("Set-Cookie"):
                self.cookie = set_cookie.split(";", 1)[0]
            text = res.read().decode()
        m = re.search(r"data: (\{.*\})\s*$", text, re.S)
        if not m:
            raise RuntimeError(f"Bad MCP response: {text[:500]}")
        out = json.loads(m.group(1))
        if "error" in out:
            raise RuntimeError(out["error"])
        return out

    def start(self) -> None:
        self._post(
            {
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "shopi-world-mcp-client", "version": "1"},
                },
            }
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        req = urllib.request.Request(
            self.url,
            data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            res.read()

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        out = self._post(
            {
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        result = out["result"]
        if result.get("isError"):
            raise RuntimeError(result["content"][0]["text"])
        return json.loads(result["content"][0]["text"])


def connect() -> ShopiWorldMcpClient:
    client = ShopiWorldMcpClient(load_token())
    client.start()
    return client
