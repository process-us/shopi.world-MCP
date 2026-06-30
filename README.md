# shopi.world MCP — theme files for Cursor

Connect **Cursor** (or any MCP client) to your Shopify store’s **theme files** through the [shopi.world](https://fronts.me/shopify/) app.

- Read and write **live theme** Liquid, JSON, CSS, JS, and assets
- **Full theme backup** to a local git repo (300+ files on typical Dawn themes)
- **Restore** from a local mirror back to Shopify
- No Shopify Admin API keys in Cursor — one per-shop token from the embedded app

**MCP endpoint:** `https://fronts.me/shopify/mcp`

**Also in this repo:** theme backup/restore scripts **and** offline translation tools for multilingual stores. See [Translation guide](#translation-guide) below.

---

## Table of contents

1. [Quick start](#quick-start) — token, Cursor config, first backup
2. [What’s in this repo](#whats-in-this-repo)
3. [Workflows](#workflows) — backup, delta sync, restore
4. [Translation guide](#translation-guide) — **merchants & developers**
5. [Migrating from WordPress](#migrating-from-wordpress-or-another-platform)
6. [Troubleshooting](#troubleshooting)

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

### 5. Day-to-day sync (delta)

After the first full backup, pull only files that changed on Shopify:

```bash
python3 ~/dev/shopi-world-mcp/scripts/download_changed.py ~/dev/my-theme-mirror --dry-run
python3 ~/dev/shopi-world-mcp/scripts/download_changed.py ~/dev/my-theme-mirror
```

See [examples/](examples/) for shell wrappers and Cursor prompts.

---

## What’s in this repo

| Path | Purpose |
|------|---------|
| [scripts/download_theme_mirror.py](scripts/download_theme_mirror.py) | Full backup → local folder |
| [scripts/download_changed.py](scripts/download_changed.py) | Changed files only → local folder (checksum delta; daily pull from Shopify) |
| [scripts/restore_theme_mirror.py](scripts/restore_theme_mirror.py) | Local folder → live theme |
| [scripts/restore_changed.py](scripts/restore_changed.py) | Git-changed files only → live theme (daily push to Shopify) |
| [scripts/upload_theme_assets_from_urls.py](scripts/upload_theme_assets_from_urls.py) | Large theme assets via server-side URL download (bypasses MCP payload limit) |
| [scripts/localize_theme.py](scripts/localize_theme.py) | Wrap baked-in copy in `{% case request.locale.iso_code %}` (offline, glossary-driven) |
| [scripts/audit_theme_i18n.py](scripts/audit_theme_i18n.py) | Audit mirror for hardcoded copy vs `t` filter (greenfield readiness) |
| [scripts/theme_markup_localize.py](scripts/theme_markup_localize.py) | Core Liquid localizer (used by `localize_theme.py`) |
| [scripts/locale_text_detect.py](scripts/locale_text_detect.py) | Primary-locale script detection for translatable runs |
| [scripts/mirror_download_lib.py](scripts/mirror_download_lib.py) | Shared delta/full download helpers |
| [scripts/mcp_client.py](scripts/mcp_client.py) | Minimal Python MCP HTTP client |
| [snippets/](snippets/) | Copy-paste helpers (Python / Node) |
| [examples/](examples/) | MCP config, sync scripts, glossary sample, Cursor prompts |
| [docs/TOOLS.md](docs/TOOLS.md) | Full MCP tool reference |

---

## Workflows

### Full backup vs delta pull

| Situation | Command |
|-----------|---------|
| First backup, or no local `manifest.json` | `download_theme_mirror.py` |
| Live theme switched (`themeGid` changed) | `download_theme_mirror.py` (auto-detected) |
| Edited files in Shopify Theme Editor | `download_changed.py` |
| Force re-download everything | `download_changed.py --full` |

**Delta pull** compares remote `checksumMd5` (from `live_theme_mirror_manifest`) to your local [`manifest.json`](examples/manifest.json.example) from the last sync. Only changed or new file bodies are downloaded. See [examples/sync-from-shopify.sh](examples/sync-from-shopify.sh).

**Delta push** (`restore_changed.py`) compares your working tree to git `HEAD` (or `--against`) and uploads only changed theme files. See [examples/push-to-shopify.sh](examples/push-to-shopify.sh).

### Backup (Shopify → disk) — first time

```bash
python3 scripts/download_theme_mirror.py ./theme-mirror
```

### Delta pull (Shopify → disk)

After editing in **Shopify admin → Themes → Edit code**:

```bash
python3 scripts/download_changed.py ./theme-mirror
python3 scripts/download_changed.py ./theme-mirror --dry-run          # preview only
python3 scripts/download_changed.py ./theme-mirror --full             # ignore local checksums
python3 scripts/download_changed.py ./theme-mirror --delete-removed   # delete local orphans
```

| Flag | Effect |
|------|--------|
| `--dry-run` | List changed paths; do not fetch bodies or update `manifest.json` |
| `--full` | Download every file (same as first backup, but reuses existing folder) |
| `--delete-removed` | Remove local copies of files deleted on Shopify |

**Cursor agent:**

> Refresh my theme mirror at `./theme-mirror/` with a delta download: `live_theme_mirror_manifest`, compare checksums to local `manifest.json`, then `read_live_theme_mirror_files` only for changed files. Update `manifest.json`.

More prompts: [examples/cursor-prompts.md](examples/cursor-prompts.md)

### Edit a single file

> Read `sections/header.liquid` from my live theme and show me the first 50 lines.

> Update the footer CSS in `assets/section-footer.css` on my live theme. (needs write token)

Push a few files from your mirror without git:

```bash
cd ./theme-mirror
python3 ~/path/to/shopi-world-mcp/examples/push-files.py sections/header.liquid snippets/foo.liquid
```

**Cursor agent (full backup):**

> Back up my full live theme into `./theme-mirror/`: `live_theme_mirror_manifest`, then `read_live_theme_mirror_files` in batches of 25. Text as UTF-8, base64 as binary. Match manifest file count.

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

| Flag | Effect |
|------|--------|
| `--dry-run` | List files that would upload; no MCP calls |
| `--against REF` | Compare working tree to git ref (default: `HEAD`) |

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

---

## Translation guide

Multilingual Shopify stores need **two different kinds of work**:

1. **Translate content** — strings in theme files, menus, product copy (shopi.world app, Shopify admin, or local scripts).
2. **Push theme files** — this repo’s MCP scripts upload the result to your live theme.

**MCP does not machine-translate.** It is the last mile after translation.

### Choose your workflow

| You are… | Theme type | What to use |
|----------|------------|-------------|
| **Merchant** (no code) | Any | [shopi.world](https://fronts.me/shopify/) → **Languages** tab |
| **Merchant** | Standard Dawn / `t` filter theme | Languages → **Bootstrap** + **Apply** (auto-detects greenfield) |
| **Merchant** | Cloned marketing site (baked HTML) | Languages → **Apply** (includes theme-content + metafields) |
| **Developer** | Cloned / custom_liquid HTML | `localize_theme.py` + glossary → `restore_changed.py` |
| **Developer** | Standard Dawn i18n | `audit_theme_i18n.py` → fix issues → `restore_changed.py` |
| **Anyone** | Product titles only | Shopify **Translate & Adapt** (not theme files) |

### What gets translated where

| Content | Tool | Uploaded via MCP? |
|---------|------|-----------------|
| Cart, search, checkout (Dawn UI) | `locales/*.json` or Languages **Bootstrap** | Yes |
| Theme editor text, menus, pages | Languages **Apply** (`theme-translations`) | No — Shopify Translation API |
| Marketing HTML in `custom_liquid` | Languages **Apply** or `localize_theme.py` | Yes |
| `shopi.*` product metafields (cloned PDPs) | Languages **Apply** (`theme-content`) | No — metafield translations in Shopify |
| Product titles & descriptions | Translate & Adapt or shopi.world WPML sync | No |
| Glossary JSON, Python scripts | Local only | **No** — `scripts/` excluded on restore |

### Merchant workflow (shopi.world app)

No SSH, no local mirror required.

1. Install [shopi.world](https://fronts.me/shopify/) and connect your store.
2. **Shopify Admin → Settings → Languages** — add and **publish** target locales (e.g. Arabic, French).
3. Open shopi.world → **Languages** (`/languages`).
4. Review **Theme translation profile** (greenfield / cloned / mixed) — the app picks the right pipeline.
5. Optional: edit **Glossary** (source → target pairs) for domain-specific phrases.
6. Click **Preview**, then **Apply** for your target locale.

| Button | What it does |
|--------|----------------|
| **Bootstrap theme locales** | Creates/updates `locales/<locale>.json` from your default locale file |
| **Preview** | Dry-run — shows counts, no writes |
| **Apply** | Runs recommended steps for your theme profile |
| **Apply + baked-in HTML** | (Greenfield only) Also runs in-theme HTML rewrite if needed |
| **Sync product translations** | WPML → Shopify (requires WooCommerce connection) |

**Greenfield themes** (Dawn with `{{ 'key' \| t }}`): profile shows *Standard theme (i18n)* — Apply runs bootstrap + theme-translations only.

**Cloned themes** (marketing HTML in templates): profile shows *Cloned / baked-in HTML* — Apply also rewrites Liquid and translates `shopi.*` metafields.

After Apply, if you use a **local mirror**, pull changes from Shopify:

```bash
python3 scripts/download_changed.py ~/dev/my-theme-mirror
```

### Developer workflow — cloned themes (`localize_theme.py`)

For themes with **primary-language copy baked into** `custom_liquid`, snippets, or custom sections — typical after a site clone.

**Prerequisites:** local theme mirror (see [Quick start](#quick-start)), Python 3, glossary JSON.

```bash
# 0. Clone this repo if you haven't
git clone https://github.com/process-us/shopi-world-mcp.git
cd shopi-world-mcp

# 1. Back up live theme (first time only)
python3 scripts/download_theme_mirror.py ~/dev/my-theme-mirror

# 2. List strings that need glossary entries
python3 scripts/localize_theme.py \
  --mirror ~/dev/my-theme-mirror \
  --primary he \
  --list-runs

# 3. Create glossary (flat JSON: primary text → translation)
#    See examples/glossary-ar.json.example
cat > /tmp/glossary-ar.json <<'EOF'
{
  "טקסט בעברית": "النص العربي"
}
EOF

# 4. Apply locale wrappers ({% case request.locale.iso_code %})
python3 scripts/localize_theme.py \
  --mirror ~/dev/my-theme-mirror \
  --primary he \
  --target ar \
  --glossary /tmp/glossary-ar.json

# Multiple targets in one glossary file:
# { "ar": { "שלום": "مرحبا" }, "fr": { "שלום": "Bonjour" } }
python3 scripts/localize_theme.py \
  --mirror ~/dev/my-theme-mirror \
  --primary he \
  --target ar,fr \
  --glossary ./glossary.json

# 5. Review and push to live theme
cd ~/dev/my-theme-mirror
git diff
python3 ~/dev/shopi-world-mcp/scripts/restore_changed.py . --dry-run
python3 ~/dev/shopi-world-mcp/scripts/restore_changed.py .
```

**`localize_theme.py` flags**

| Flag | Effect |
|------|--------|
| `--mirror PATH` | Theme mirror root (required) |
| `--primary LOCALE` | Primary locale for script detection (default `he`) |
| `--target LOCALES` | Comma-separated, e.g. `ar` or `ar,fr` |
| `--glossary FILE` | Flat JSON (one target) or nested by locale (multiple targets) |
| `--glossary-dir DIR` | Per-locale files: `ar.json`, `fr.json`, … |
| `--scope all\|homepage` | `all` = templates + sections; `homepage` = `index.json` only |
| `--extra-glob PATTERN` | Repeatable, e.g. `snippets/shopi*.liquid` |
| `--list-runs` | Print unique source strings (build your glossary) |
| `--dry-run` | Report without writing files |

**Liquid pattern** — keep primary copy in `{% else %}`, add targets with `{% when %}`:

```liquid
{% case request.locale.iso_code %}
  {% when 'ar' %}النص العربي
  {% else %}טקסט בעברית
{% endcase %}
```

Never replace primary-language strings in source files with translations.

### Developer workflow — greenfield themes (`audit_theme_i18n.py`)

For **standard Dawn-style** themes that use `{{ 'sections.header.menu' | t }}` and `locales/*.json`.

```bash
# Audit mirror before push
python3 scripts/audit_theme_i18n.py ~/dev/my-theme-mirror
python3 scripts/audit_theme_i18n.py ~/dev/my-theme-mirror --primary en --json

# Fix any reported hardcoded strings → use | t + locales/*.json
# Machine-translate theme editor strings via shopi.world Languages → Apply
# Push locale file edits:
python3 scripts/restore_changed.py ~/dev/my-theme-mirror
```

Profile **greenfield** → you do **not** need `localize_theme.py`.

### Shopify locale URLs

| URL | Language |
|-----|----------|
| `https://your-store.myshopify.com/` | Primary (e.g. Hebrew, English) |
| `https://your-store.myshopify.com/ar` | Arabic |
| `https://your-store.myshopify.com/fr` | French |

Dawn UI strings (cart, checkout) → edit `locales/ar.json`, not hardcoded Liquid.

### Typical mirror layout

```text
theme-mirror/
  manifest.json              # local only — never uploaded
  locales/
    en.default.json
    ar.json
  templates/index.json
  snippets/my-hero.liquid
  glossary-ar.json             # local only (or use shopi.world Languages glossary UI)
  scripts/                     # local only — never uploaded
  .git/                        # local only — never uploaded
```

### End-to-end example (developer, cloned store)

```bash
# Translate offline
python3 scripts/localize_theme.py --mirror ./theme-mirror --primary he --target ar \
  --glossary ./glossary-ar.json --dry-run
python3 scripts/localize_theme.py --mirror ./theme-mirror --primary he --target ar \
  --glossary ./glossary-ar.json

# Push + verify on /ar
python3 scripts/restore_changed.py ./theme-mirror
open "https://YOUR-STORE.myshopify.com/ar"
```

---

### Recommended dev loop (git + delta sync)

After the initial backup, most day-to-day work looks like this:

```bash
cd ~/dev/my-theme-mirror
# edit files locally (Cursor, VS Code, etc.)
git diff                                    # review
python3 ~/path/to/shopi-world-mcp/scripts/restore_changed.py . --dry-run
python3 ~/path/to/shopi-world-mcp/scripts/restore_changed.py .
```

Pulled edits from Shopify admin:

```bash
python3 ~/path/to/shopi-world-mcp/scripts/download_changed.py . --dry-run
python3 ~/path/to/shopi-world-mcp/scripts/download_changed.py .
git diff && git commit -am "Sync from Shopify"
```

`restore_changed.py` compares your working tree to git `HEAD` (or `--against origin/main`) and uploads only changed theme files. `download_changed.py` compares remote checksums to `manifest.json` and downloads only changed file bodies. Use these instead of full restore/download whenever possible.

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
| Marketing HTML in `custom_liquid` / cloned snippets | `{% case request.locale.iso_code %}` or shopi.world Languages **Apply** |

Never bulk-replace Hebrew with Arabic in source files — use locale conditionals (`{% case %}`) or Shopify’s translation system.

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
  manifest.json              # local only — delta sync index (see examples/manifest.json.example)
  config/settings_data.json
  sections/header.liquid
  assets/logo.png
  locales/ar.json
  ...
  .git/                      # optional local git — never uploaded
  scripts/                   # optional local tooling — never uploaded
```

**Tip:** Run `git init` inside `theme-mirror/` for version control. Restore ignores `.git` entirely.

`manifest.json` is written by `download_theme_mirror.py` and `download_changed.py`. Each entry includes `checksumMd5` — the delta pull compares this to the remote manifest and skips unchanged files.

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
| `upload_theme_assets_from_urls` | write | Download URL(s) server-side and upsert theme assets (large images) |
| `live_theme_drift` | read | Compare live theme vs last shopi.world snapshot |
| `live_theme_file_events` | read | Recent tracked writes (MCP audit log) |
| `refresh_live_theme_manifest_snapshot` | write | Pull full live manifest as drift baseline |
| `read_live_theme_file` | read | Single text file |
| `write_live_theme_file` | write | Save single text file |

Full list: [docs/TOOLS.md](docs/TOOLS.md)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **401** | Regenerate token in shopi.world Settings |
| **Write denied** | Create token with *Allow theme writes* |
| **413 Payload Too Large** | One or more files exceed ~100KB encoded in a single batch — use `restore_changed.py` to narrow scope; split large `custom_liquid` into `snippets/`; use `upload_theme_assets_from_urls.py` for large `assets/*` images |
| **413 after partial restore** | Earlier batches may have succeeded — fix/split the failing file, run `restore_changed.py` again |
| **File is not valid JSON** | Usually a `locales/*.json` banner comment — use the latest `restore_theme_mirror.py` (strips it automatically) |
| **Red dot on MCP** | Toggle shopi-world off/on in Cursor |
| **Script: no token** | Set `SHOPI_MCP_TOKEN` or fix `~/.cursor/mcp.json` |
| **`url` transport fails** | Fallback config below |

**mcp-remote fallback** (if Cursor `url` mode fails): see [examples/mcp-remote.json.example](examples/mcp-remote.json.example)

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

- **App:** [fronts.me/shopify](https://fronts.me/shopify/) — embedded app + **Languages** tab for merchants
- **Translation guide:** [README § Translation guide](#translation-guide)
- **Shopify app:** install from your shopi.world Partner listing / Shopify admin
