# Examples

Copy-paste configs and scripts for common shopi.world MCP workflows.

## Theme backup & sync

| File | Purpose |
|------|---------|
| [mcp.json.example](mcp.json.example) | Cursor MCP config (URL transport) |
| [mcp-remote.json.example](mcp-remote.json.example) | Cursor fallback via `mcp-remote` |
| [manifest.json.example](manifest.json.example) | Local `manifest.json` shape (delta sync index) |
| [sync-from-shopify.sh](sync-from-shopify.sh) | Delta pull: Shopify → local mirror |
| [push-to-shopify.sh](push-to-shopify.sh) | Delta push: git-changed files → Shopify |
| [push-files.py](push-files.py) | Push one or more files by path (no git required) |
| [cursor-prompts.md](cursor-prompts.md) | Ready-made Cursor agent prompts |

## Translation

| File | Purpose |
|------|---------|
| [glossary-ar.json.example](glossary-ar.json.example) | Sample glossary for `localize_theme.py` |

**Cloned theme (baked HTML):**

```bash
python3 ../scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --list-runs
python3 ../scripts/localize_theme.py --mirror ~/dev/my-theme-mirror --primary he --target ar \
  --glossary glossary-ar.json.example
python3 ../scripts/restore_changed.py ~/dev/my-theme-mirror
```

**Greenfield theme (Dawn `t` filter):**

```bash
python3 ../scripts/audit_theme_i18n.py ~/dev/my-theme-mirror --primary en
# Fix issues, then push — or use shopi.world Languages → Apply for MT
```

**Merchant (no local mirror):** [shopi.world Languages tab](https://fronts.me/shopify/) — see [README Translation guide](../README.md#translation-guide).

---

All shell/Python examples assume you cloned [shopi-world-mcp](https://github.com/process-us/shopi-world-mcp) and have a token in `~/.cursor/mcp.json` or `SHOPI_MCP_TOKEN`.

```bash
export SHOPI_WORLD_MCP=~/dev/shopi-world-mcp   # optional — scripts auto-detect repo root
export SHOPI_MCP_TOKEN=sw_mcp_xxxxxxxx           # optional if already in ~/.cursor/mcp.json
```
