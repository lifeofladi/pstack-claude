#!/bin/sh
# Copies pstack's agent definitions into the user-level agents directory so
# `subagent_type: "panel-correctness"` and friends resolve with their model and
# effort tier baked in. Re-running overwrites the same six files. New agents
# register when the next session starts.
set -eu

here="$(cd "$(dirname "$0")/.." && pwd)"
dest="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agents"

mkdir -p "$dest"
for agent in "$here"/agents/*.md; do
  cp "$agent" "$dest/"
  echo "installed $dest/$(basename "$agent")"
done
echo "agents load on the next session start"
