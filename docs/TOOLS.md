# MCP tools reference

Hosted endpoint: `https://fronts.me/shopify/mcp`  
Auth: `Authorization: Bearer sw_mcp_…` (per-shop token from shopi.world Settings)

## Scopes

| Token scope | Allows |
|-------------|--------|
| `theme:read` | All read tools (default) |
| `theme:write` | Write + restore tools (enable *Allow theme writes* when creating token) |

## All tools

| Tool | Scope | Description |
|------|-------|-------------|
| `list_theme_projects` | read | Theme clone projects for the shop |
| `get_theme_project` | read | One project’s metadata |
| `list_theme_files` | read | Editable text files on a project theme (`ready` status) |
| `read_theme_file` | read | One project file (working copy → live fallback) |
| `list_live_theme_files` | read | Filenames on published **MAIN** theme |
| `read_live_theme_file` | read | One text file from live MAIN theme |
| `list_theme_backups` | read | In-app backups for a project |
| `write_theme_file` | write | Save one file on a project theme |
| `write_live_theme_file` | write | Save one text file on live MAIN theme |
| `live_theme_mirror_manifest` | read | Full MAIN theme file list + metadata |
| `read_live_theme_mirror_files` | read | Batch read up to **25** files (text + base64) |
| `restore_live_theme_mirror_files` | write | Batch restore up to **25** files to live MAIN theme |
| `upload_theme_assets_from_urls` | write | Download URL(s) server-side and upsert theme assets (large images) |
| `live_theme_drift` | read | Compare live MAIN theme vs last shopi.world checksum snapshot |
| `live_theme_file_events` | read | Recent tracked writes to live theme (audit log) |
| `refresh_live_theme_manifest_snapshot` | write | Pull full live manifest as drift baseline |

## Drift detection

After MCP restores (or **Backup → Update baseline** in shopi.world), the server stores a per-shop checksum snapshot. `live_theme_drift` reports files changed on Shopify outside tracked writes (e.g. theme editor).

### `live_theme_drift`

**Input:** `{}`

**Output:** `{ themeGid, hasSnapshot, snapshotAt, liveAt, unchanged, added[], removed[], changed[{ filename, snapshotChecksum, liveChecksum, snapshotSize, liveSize }] }`

### `upload_theme_assets_from_urls`

**Input:**

```json
{
  "files": [
    { "url": "https://example.com/image.jpg", "filename": "assets/home-cat-example.jpg" }
  ]
}
```

Paths must start with `assets/`. Server downloads and upserts — no base64 in the MCP request. Requires `theme:write`.

## Mirror tools (backup / restore)

### `live_theme_mirror_manifest`

**Input:** `{}`

**Output:** `{ version, shop, themeGid, exportedAt, fileCount, files: [{ filename, checksumMd5, size, contentType, updatedAt }] }`

`checksumMd5` drives delta download (`download_changed.py`). `updatedAt` is Shopify’s last-modified time (informational).

See [examples/manifest.json.example](../examples/manifest.json.example) and [examples/cursor-prompts.md](../examples/cursor-prompts.md).

### `read_live_theme_mirror_files`

**Input:**

```json
{ "filenames": ["config/settings_data.json", "sections/header.liquid"] }
```

Max 25 paths per call.

**Output:**

```json
{
  "themeGid": "gid://shopify/OnlineStoreTheme/…",
  "files": [
    { "filename": "…", "encoding": "text", "content": "…" },
    { "filename": "…", "encoding": "base64", "content": "…" }
  ],
  "missing": []
}
```

### `restore_live_theme_mirror_files`

**Input:**

```json
{
  "files": [
    { "filename": "sections/foo.liquid", "encoding": "text", "content": "…" },
    { "filename": "assets/logo.png", "encoding": "base64", "content": "…" }
  ]
}
```

Max 25 files per call. Requires `theme:write`.

**Payload note:** Although the tool accepts up to 25 files, the restore scripts batch by **~100KB total encoded payload** per request. A single file larger than that (common for cloned `templates/page.*.json`) will return **413** even when uploaded alone — extract content to `snippets/` or use the Theme Editor.

**Output:** `{ "themeGid": "…", "restored": 2 }`

## Behavior

- Edits target the **published (MAIN)** theme unless a project tool is used.
- **Never auto-publishes** a different theme.
- Restore is **upsert-only** — files not in your mirror are not deleted on Shopify.
- `.json` files are validated before upload.

## HTTP / custom clients

MCP uses **Streamable HTTP** (SSE). See `scripts/mcp_client.py` for a minimal Python client, or use Cursor’s built-in MCP transport.

Initialize sequence:

1. `POST` `initialize` → capture `Set-Cookie` session
2. `POST` `notifications/initialized` (with cookie)
3. `POST` `tools/call` with `{ "name": "…", "arguments": { … } }`

Example `tools/call` body:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "read_live_theme_file",
    "arguments": { "filename": "config/settings_data.json" }
  },
  "id": 2
}
```

Response `result.content[0].text` is a JSON string (tool-specific payload).
