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
| [scripts/restore_changed.py](scripts/restore_changed.py) | Git-changed files only → live theme (daily workflow) |
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

**Changed files only** (faster after local edits in a git-backed mirror):

```bash
python3 scripts/restore_changed.py ./theme-mirror
python3 scripts/restore_changed.py ./theme-mirror --dry-run   # preview
python3 scripts/restore_changed.py ./theme-mirror --against origin/main
```

Requires **Allow theme writes** on your token.

The restore script uploads **theme files only**. It automatically skips:

| Skipped | Why |
|---------|-----|
| `.git/` | Version control — never belongs on Shopify |
| `scripts/` | Local tooling (translation scripts, etc.) |
| `manifest.json` | Local backup index only |
| Hidden paths (`.cursor/`, etc.) | Not theme assets |

Keep your git repo at the mirror root if you like (`git init` in `theme-mirror/`) — restore will not upload `.git`.

**Payload limits:** MCP requests have a practical body-size cap (~100KB per batch). The script batches by size (not a fixed file count). Very large single files (e.g. a 200KB `templates/index.json` with embedded HTML) may return **413 Payload Too Large** — split heavy `custom_liquid` blocks into `snippets/` and `{% render %}` them from the template instead.

**Locale JSON files** (`locales/*.json`) often start with Shopify’s auto-generated `/* … */` banner. The script strips that banner on upload when needed so MCP JSON validation passes (Shopify stores the JSON body either way).

### Multilingual stores (Hebrew + Arabic)

Shopify locale URLs work like this:

| URL | Language |
|-----|----------|
| `https://your-store.myshopify.com/` | Primary (e.g. Hebrew) |
| `https://your-store.myshopify.com/ar` | Arabic (`locales/ar.json` + locale-aware Liquid) |
| `https://your-store.myshopify.com/en` | English (`locales/en.default.json`) |

**Do not replace** Hebrew strings in theme files with Arabic. Keep Hebrew as the default and wrap baked-in copy:

```liquid
{% if request.locale.iso_code == 'ar' %}النص العربي{% else %}טקסט בעברית{% endif %}
```

- **Dawn UI strings** (cart, checkout, search) → edit `locales/ar.json` / `locales/he.json`, not hardcoded Liquid.
- **Marketing HTML in `custom_liquid`** → locale conditionals as above (shopi.world’s theme clone uses the same pattern).

If you maintain a mirror with translation tooling, keep scripts **outside** the upload path (e.g. `theme-mirror/scripts/` is excluded automatically) or in a separate repo.

### Refresh backup

Re-run `download_theme_mirror.py` — overwrites local files and updates `manifest.json`.

### Recommended dev loop (git + push changed only)

After the initial backup, most day-to-day work looks like this:

```bash
cd ~/dev/my-theme-mirror
# edit files locally (Cursor, VS Code, etc.)
git diff                                    # review
python3 ~/path/to/shopi-world-mcp/scripts/restore_changed.py . --dry-run
python3 ~/path/to/shopi-world-mcp/scripts/restore_changed.py .
```

`restore_changed.py` compares your working tree to git `HEAD` (or `--against origin/main`) and uploads only changed theme files. Use this instead of a full restore whenever possible — it is faster and avoids re-sending hundreds of unchanged files.

Commit in the mirror repo when a change set is good; restore does **not** require a commit, but git makes `--dry-run` reviews and rollbacks much easier.

---

## Migrating from WordPress (or another platform)

Common patterns when cloning a marketing site into a Shopify theme mirror:

### Links

| Do | Don't |
|----|--------|
| `/pages/{handle}`, `/products/{handle}`, `/collections/{handle}` | `https://old-site.com/...` |
| `{{ product.url }}` / `{{ all_products['handle'].url }}` | Hardcoded product URLs |
| `mailto:support@yourdomain.com` | — (email on your domain is fine during migration) |

Audit leftovers before go-live:

```bash
rg 'old-domain\.com' ~/dev/my-theme-mirror --glob '!scripts/*' --glob '!locales/*'
```

### Assets still hosted on the old site

Download into the mirror and reference via Shopify assets:

```bash
curl -sL 'https://old-site.com/path/to/file.svg' -o ~/dev/my-theme-mirror/assets/file.svg
```

```liquid
<img src="{{ 'file.svg' | asset_url }}" alt="">
```

Theme `assets/` **are** uploaded on restore (unlike `scripts/`).

### Product names in marketing sections

Hardcoded titles break on `/ar` if Shopify has Arabic product translations in admin. Prefer:

```liquid
{% assign p = all_products['magnesium-liposomal'] %}
<h3>{{ p.title }}</h3>
<a href="{{ p.url }}">…</a>
```

Handles can include non-Latin characters (e.g. Hebrew). List live handles with:

```bash
curl -sL 'https://YOUR-STORE.myshopify.com/products.json?limit=250' | python3 -c "
import json,sys
for p in json.load(sys.stdin)['products']:
    print(p['handle'], '|', p['title'])
"
```

### Baked-in copy vs Dawn UI strings

| Content type | Where to translate |
|--------------|-------------------|
| Cart, search, checkout labels | `locales/ar.json`, `locales/he.json` |
| Marketing HTML in `custom_liquid` / cloned snippets | `{% if request.locale.iso_code == 'ar' %}…{% else %}…{% endif %}` |

Never bulk-replace Hebrew with Arabic in source files — use locale conditionals or Shopify’s translation system.

### Cloned HTML gotchas

WordPress exports often omit JavaScript behavior. After restore, manually verify on the live store:

- Carousels / review sliders (may need `scroll-snap` or small inline scripts)
- Mobile footer accordions (toggle a class like `is-open` on click)
- Video / story sections (sticky player, product overlay links)

Fix in `snippets/` when possible so the fix is small enough to upload via MCP.

---

## When a single file is too large for MCP (413)

Restore batches cap at **~100KB total payload** per MCP call. A **single** file larger than that fails even alone — typical culprits:

- `templates/page.*.json` with huge embedded `custom_liquid` HTML (80–150KB+)
- Oversized `sections/*.liquid` cloned from another CMS

**Fix (preferred):** extract HTML into `snippets/my-section.liquid` and thin the template:

```json
"custom_liquid": "{% render 'my-section' %}"
```

`templates/index.json` is often split this way (hero, products, footer snippets, etc.).

**If you cannot refactor yet:**

1. Upload the oversized template once via **Shopify Admin → Online Store → Themes → Edit code** (no MCP size limit).
2. Or apply a **small runtime patch** in `layout/theme.liquid` / a tiny snippet (e.g. rewrite legacy `src` URLs on a specific `page.handle`) — document it as temporary.

After a failed restore, earlier batches may already have succeeded; re-run `restore_changed.py` — only remaining changed files are retried.

---

## Document your store in the mirror

Keep a `README.md` at the mirror root (not uploaded to Shopify) with:

- Live shop URL and planned custom domain
- All `/pages/*`, `/products/*`, `/collections/*` handles (refresh from Storefront JSON APIs)
- Internal links used in the theme and which file defines them
- Allowed external links (Instagram, WhatsApp, fonts)
- Footer links that still need pages created in Shopify admin

This gives the next developer (or Cursor agent) a map without re-scanning the whole theme.

---

## Local mirror layout

```text
theme-mirror/
  manifest.json              # local only — not uploaded on restore
  config/settings_data.json
  sections/header.liquid
  assets/logo.png
  locales/ar.json
  ...
  .git/                      # optional local git — never uploaded
  scripts/                   # optional local tooling — never uploaded
```

**Tip:** Run `git init` inside `theme-mirror/` for version control. Restore ignores `.git` entirely.

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
| **413 Payload Too Large** | One or more files exceed ~100KB encoded in a single batch — use `restore_changed.py` to narrow scope; split large `custom_liquid` into `snippets/`; upload oversized `templates/page.*.json` via Theme Editor |
| **413 after partial restore** | Earlier batches may have succeeded — fix/split the failing file, run `restore_changed.py` again |
| **File is not valid JSON** | Usually a `locales/*.json` banner comment — use the latest `restore_theme_mirror.py` (strips it automatically) |
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

- **25 files** max per `read_live_theme_mirror_files` / `restore_live_theme_mirror_files` MCP call (hard server limit)
- **Restore script** batches by ~100KB payload and max 3 files per call to avoid **413** errors
- **Single file** larger than ~100KB cannot be restored via MCP — split into snippets or use Theme Editor (see above)
- **Never uploads** `.git/`, `scripts/`, `manifest.json`, or hidden paths
- **Never auto-publishes** a theme — edits go to the current live theme only
- Restore does **not** delete remote files missing from your mirror
- Tokens are shop-scoped; revoke in Settings anytime

---

## License

MIT — see [LICENSE](LICENSE).

## Links

- **App:** [fronts.me/shopify](https://fronts.me/shopify/)
- **Shopify app:** install from your shopi.world Partner listing / Shopify admin
