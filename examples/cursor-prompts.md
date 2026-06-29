# Cursor agent prompts

Copy into Cursor chat when **shopi-world** MCP is enabled.

## Verify connection

> Using shopi-world MCP, call `live_theme_mirror_manifest` and tell me my shop name, theme GID, and file count.

## Full backup (first time)

> Back up my full live theme into `./theme-mirror/`: call `live_theme_mirror_manifest`, then `read_live_theme_mirror_files` in batches of 25. Write text as UTF-8 and base64 as binary. Save `manifest.json` at the end. Confirm local file count matches the manifest.

Or run locally:

```bash
python3 ~/dev/shopi-world-mcp/scripts/download_theme_mirror.py ./theme-mirror
```

## Delta pull (Shopify → disk)

After edits in **Shopify admin → Themes → Edit code**:

> Refresh my theme mirror at `./theme-mirror/` with a delta download: call `live_theme_mirror_manifest`, compare each file's `checksumMd5` to local `manifest.json`, then `read_live_theme_mirror_files` only for changed paths. Update `manifest.json` when done. List what changed.

Or run locally:

```bash
./examples/sync-from-shopify.sh ./theme-mirror --dry-run   # preview
./examples/sync-from-shopify.sh ./theme-mirror
```

## Delta push (disk → Shopify)

After local edits in a git-backed mirror:

> Upload only git-changed theme files from `./theme-mirror/` to my live theme using `restore_live_theme_mirror_files`. Skip `.git/`, `scripts/`, and `manifest.json`. Batch by ~100KB payload. Show what you upload before writing.

Or run locally:

```bash
./examples/push-to-shopify.sh ./theme-mirror --dry-run
./examples/push-to-shopify.sh ./theme-mirror
```

## Push specific files (fast path)

> Read `sections/header.liquid` from my live theme and summarize the first 50 lines.

> Update `snippets/kapps-nav-label.liquid` on my live theme with [paste diff]. Use `write_live_theme_file`.

Or from the mirror directory:

```bash
python3 ~/dev/shopi-world-mcp/examples/push-files.py snippets/kapps-nav-label.liquid sections/header.liquid
```

## When restore fails with 413

> `restore_changed.py` failed with 413 on `templates/page.about-us.json`. Split the large `custom_liquid` block into a new snippet and thin the template to `{% render 'about-us-content' %}`. Then push only the changed files.

## Translation audit (greenfield theme)

> Run `audit_theme_i18n.py` on my theme mirror at `./theme-mirror/` with `--primary en` and summarize hardcoded strings I should move to `locales/*.json` and the `t` filter.

Or locally:

```bash
python3 ~/dev/shopi-world-mcp/scripts/audit_theme_i18n.py ./theme-mirror --primary en
```

## Offline localization (cloned theme)

> List translatable Hebrew runs in `./theme-mirror/` using `localize_theme.py --list-runs`, then help me build a glossary JSON for Arabic.

```bash
python3 ~/dev/shopi-world-mcp/scripts/localize_theme.py --mirror ./theme-mirror --primary he --list-runs
```

After glossary is ready:

```bash
python3 ~/dev/shopi-world-mcp/scripts/localize_theme.py --mirror ./theme-mirror --primary he --target ar --glossary ./glossary-ar.json --dry-run
python3 ~/dev/shopi-world-mcp/scripts/restore_changed.py ./theme-mirror --dry-run
```

**Merchant path (no mirror):** use shopi.world → **Languages** → Preview → Apply.
