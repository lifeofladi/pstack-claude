#!/bin/sh
# Copies pstack's agent definitions to where Claude Code discovers them, so
# `subagent_type: "panel-correctness"` and friends resolve with their model and
# effort tier baked in. Discovery happens once, at process start, so a copy
# made now serves the next session, never the current one.
#
#   install-agents.sh            user level, ~/.claude/agents/, this machine only
#   install-agents.sh --project  this repo's .claude/agents/, commit it and every
#                                session on the repo has the seats, cloud included
set -eu

here="$(cd "$(dirname "$0")/.." && pwd)"
case "${1:-}" in
  --project) dest="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/agents" ;;
  "") dest="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agents" ;;
  *) echo "usage: $0 [--project]" >&2; exit 2 ;;
esac

mkdir -p "$dest"
for agent in "$here"/agents/*.md; do
  cp "$agent" "$dest/"
  echo "installed $dest/$(basename "$agent")"
done
echo "agents are discovered at session start, so these load in the next session"
[ "${1:-}" = "--project" ] && echo "commit $dest so cloud sessions on this repo start with them"
exit 0
