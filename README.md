# shopi.world MCP — theme files for Cursor

Connect **Cursor** (or any MCP client) to your Shopify store’s **theme files** through the [shopi.world](https://fronts.me/shopify/) app.

- Read and write **live theme** Liquid, JSON, CSS, JS, and assets
- **Full theme backup** to a local git repo (300+ files on typical Dawn themes)
- **Restore** from a local mirror back to Shopify
- No Shopify Admin API keys in Cursor — one per-shop token from the embedded app

**MCP endpoint:** `https://fronts.me/shopify/mcp`

---

## Quick start

### 1. Get a token (Shopify admin)

1. Install / open **shopi.world** in your Shopify admin.
2. Go to **Settings** → **Cursor integration (MCP)**.
3. **Create API token** (shown once — save it).
4. Enable **Allow theme writes** only if you need save/restore.
5. Click **Copy Cursor config**.

### 2. Configure Cursor

Merge into `~/.cursor/mcp.json` (see [examples/mcp.json.example](examples/mcp.json.example)):

```json
{
  "mcpServers": {
    "shopi-world": {
      "url": "https://fronts.me/shopify/mcp",
      "headers": {
        "Authorization": "Bearer sw_mcp_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Restart Cursor, or toggle **shopi-world** under **Settings → Tools & MCP**.

### 3. Verify

In Cursor chat:

> Using shopi-world MCP, call `live_theme_mirror_manifest` and tell me my shop name and file count.

### 4. Back up your theme

```bash
git clone https://github.com/process-us/shopi-world-mcp.git
cd shopi-world-mcp

mkdir -p ~/dev/my-theme-mirror
python3 scripts/download_theme_mirror.py ~/dev/my-theme-mirror

cd ~/dev/my-theme-mirror
git init && git add . && git commit -m "Initial live theme backup"
```

The script uses your token from `~/.cursor/mcp.json`, or set `SHOPI_MCP_TOKEN`.

---

## What’s in this repo

| Path | Purpose |
|------|---------|
| [scripts/download_theme_mirror.py](scripts/download_theme_mirror.py) | Full backup → local folder |
| [scripts/restore_theme_mirror.py](scripts/restore_theme_mirror.py) | Local folder → live theme |
| [scripts/mcp_client.py](scripts/mcp_client.py) | Minimal Python MCP HTTP client |
| [snippets/](snippets/) | Copy-paste helpers (Python / Node) |
| [examples/mcp.json.example](examples/mcp.json.example) | Cursor config template |
| [docs/TOOLS.md](docs/TOOLS.md) | Full MCP tool reference |

---

## Workflows

### Backup (Shopify → disk)

**Script (recommended):**

```bash
python3 scripts/download_theme_mirror.py ./theme-mirror
```

**Cursor agent:**

> Back up my full live theme into `./theme-mirror/`: `live_theme_mirror_manifest`, then `read_live_theme_mirror_files` in batches of 25. Text as UTF-8, base64 as binary. Match manifest file count.

### Edit a single file

> Read `sections/header.liquid` from my live theme and show me the first 50 lines.

> Update the footer CSS in `assets/section-footer.css` on my live theme. (needs write token)

### Restore (disk → Shopify)

**Warning:** changes the **live** theme shoppers see.

```bash
python3 scripts/restore_theme_mirror.py ./theme-mirror
```

Requires **Allow theme writes** on your token.

### Refresh backup

Re-run `download_theme_mirror.py` — overwrites local files and updates `manifest.json`.

---

## Local mirror layout

```text
theme-mirror/
  manifest.json              # from live_theme_mirror_manifest
  config/settings_data.json
  sections/header.liquid
  assets/logo.png
  ...
```

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SHOPI_MCP_TOKEN` | from `~/.cursor/mcp.json` | Bearer token `sw_mcp_…` |
| `SHOPI_MCP_URL` | `https://fronts.me/shopify/mcp` | MCP endpoint |

```bash
export SHOPI_MCP_TOKEN=sw_mcp_xxxxxxxx
python3 scripts/download_theme_mirror.py ./theme-mirror
```

---

## Code snippets

**Python** — write one file from a mirror read response:

```python
# snippets/write_mirror_file.py
import base64
from pathlib import Path

def write_mirror_file(root: Path, file: dict) -> None:
    dest = root / file["filename"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if file["encoding"] == "text":
        dest.write_text(file["content"], encoding="utf-8")
    else:
        dest.write_bytes(base64.b64decode(file["content"]))
```

**Node** — same:

```javascript
// snippets/write_mirror_file.mjs
import fs from "fs";
import path from "path";

export function writeMirrorFile(root, file) {
  const dest = path.join(root, file.filename);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (file.encoding === "text") fs.writeFileSync(dest, file.content, "utf8");
  else fs.writeFileSync(dest, Buffer.from(file.content, "base64"));
}
```

**Custom Python client:**

```python
from scripts.mcp_client import connect

client = connect()
manifest = client.call_tool("live_theme_mirror_manifest")
print(manifest["shop"], manifest["fileCount"])

data = client.call_tool("read_live_theme_mirror_files", {
    "filenames": ["config/settings_data.json"],
})
print(data["files"][0]["filename"])
```

---

## MCP tools (summary)

| Tool | Scope | Use |
|------|-------|-----|
| `live_theme_mirror_manifest` | read | List all theme files (backup step 1) |
| `read_live_theme_mirror_files` | read | Download up to 25 files (backup step 2) |
| `restore_live_theme_mirror_files` | write | Upload up to 25 files (restore) |
| `read_live_theme_file` | read | Single text file |
| `write_live_theme_file` | write | Save single text file |

Full list: [docs/TOOLS.md](docs/TOOLS.md)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **401** | Regenerate token in shopi.world Settings |
| **Write denied** | Create token with *Allow theme writes* |
| **Red dot on MCP** | Toggle shopi-world off/on in Cursor |
| **Script: no token** | Set `SHOPI_MCP_TOKEN` or fix `~/.cursor/mcp.json` |
| **`url` transport fails** | Fallback config below |

**mcp-remote fallback** (if Cursor `url` mode fails):

```json
"shopi-world": {
  "command": "npx",
  "args": ["-y", "mcp-remote@latest", "https://fronts.me/shopify/mcp"],
  "env": { "AUTHORIZATION": "Bearer sw_mcp_YOUR_TOKEN_HERE" }
}
```

---

## Limits & safety

- **25 files** per mirror read/restore call
- **Never auto-publishes** a theme — edits go to the current live theme only
- Restore does **not** delete remote files missing from your mirror
- Tokens are shop-scoped; revoke in Settings anytime

---

## License

MIT — see [LICENSE](LICENSE).

## Links

- **App:** [fronts.me/shopify](https://fronts.me/shopify/)
- **Shopify app:** install from your shopi.world Partner listing / Shopify admin
