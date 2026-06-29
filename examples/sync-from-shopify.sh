#!/usr/bin/env bash
# Delta pull: download only theme files that changed on Shopify since last sync.
#
# Usage:
#   ./examples/sync-from-shopify.sh ~/dev/my-theme-mirror
#   ./examples/sync-from-shopify.sh ~/dev/my-theme-mirror --dry-run
#   ./examples/sync-from-shopify.sh ~/dev/my-theme-mirror --full
#   ./examples/sync-from-shopify.sh ~/dev/my-theme-mirror --delete-removed
set -euo pipefail

MIRROR="${1:?usage: sync-from-shopify.sh MIRROR_DIR [--dry-run|--full|--delete-removed]}"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SHOPI_WORLD_MCP:-$(cd "$SCRIPT_DIR/.." && pwd)}"

python3 "$REPO_ROOT/scripts/download_changed.py" "$MIRROR" "$@"
