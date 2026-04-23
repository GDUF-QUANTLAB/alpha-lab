#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${SOURCE_ROOT:-$(cd -- "$REPO_ROOT/.." && pwd)}"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="--dry-run"
fi

sync_one() {
  local repo_name="$1"
  local src_pkg_rel="$2"
  local dst_pkg_rel="$3"

  local src_pkg="$SOURCE_ROOT/$repo_name/$src_pkg_rel"
  local dst_pkg="$REPO_ROOT/$dst_pkg_rel"

  if [[ ! -d "$src_pkg" ]]; then
    echo "skip: source package not found: $src_pkg" >&2
    return 1
  fi

  echo "sync: $src_pkg -> $dst_pkg"
  mkdir -p "$dst_pkg"
  rsync -a --delete $DRY_RUN \
    --exclude "__pycache__/" \
    --exclude ".pytest_cache/" \
    --exclude ".ruff_cache/" \
    --exclude "*.pyc" \
    "$src_pkg/" "$dst_pkg/"
}

sync_one "blazestore" "blazestore" "blazestore"
sync_one "clickhouse_df" "clickhouse_df" "clickhouse_df"
sync_one "xcals" "xcals" "xcals"
sync_one "ygo" "ygo" "ygo"

echo "done"
