#!/usr/bin/env bash
# Delta push: upload only git-changed theme files from a local mirror to the live theme.
# Requires token with Allow theme writes.
#
# Usage:
#   ./examples/push-to-shopify.sh ~/dev/my-theme-mirror
#   ./examples/push-to-shopify.sh ~/dev/my-theme-mirror --dry-run
#   ./examples/push-to-shopify.sh ~/dev/my-theme-mirror --against origin/main
set -euo pipefail

MIRROR="${1:?usage: push-to-shopify.sh MIRROR_DIR [--dry-run] [--against REF]}"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SHOPI_WORLD_MCP:-$(cd "$SCRIPT_DIR/.." && pwd)}"

python3 "$REPO_ROOT/scripts/restore_changed.py" "$MIRROR" "$@"
