#!/usr/bin/env bash
# Install and configure the agent tools this repo wires in, at pinned versions.
#
#   bash .claude/scripts/install-agent-tools.sh
#
# codebase-memory-mcp (pinned in vendor/codebase-memory-mcp/release.env) into ~/.local/bin and
# Bun (claude-mem's runtime, pinned below) into ~/.bun/bin, each checked against its SHA-256;
# claude-mem's settings; the vendored claude-mem plugin for this project (not globally); and the
# repo indexed once into the code graph. The archive's own install.sh is not run: it would register
# the server and hooks in ~/.claude.json and ~/.claude, and this repo registers them itself
# (.mcp.json, .claude/settings.json). Safe to re-run.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=/dev/null
source "$REPO/vendor/codebase-memory-mcp/release.env"
BIN_DIR="${CBM_BIN_DIR:-$HOME/.local/bin}"
BUN_VERSION=1.4.2
BUN_URL="https://github.com/oven-sh/bun/releases/download/bun-v$BUN_VERSION/bun-linux-x64.zip"
BUN_SHA256=36368faef7527875d5ffa52e53cd48021741f2a83eb6208a8dd64068d422a913
CLAUDE_MEM_DIR="${CLAUDE_MEM_DATA_DIR:-$HOME/.claude-mem}"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

say() { printf '%s\n' "$*"; }

# The repo's main checkout, also when this script runs from one of its worktrees.
main_checkout_path() {
  dirname "$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)"
}

# Download `url` into the empty folder `dir` as `name` and stop unless its SHA-256 is `sha`.
download_checked() {
  local url="$1" sha="$2" dir="$3" name="$4"
  curl -fsSL -o "$dir/$name" "$url"
  echo "$sha  $dir/$name" | sha256sum -c --quiet -
}

# Put the executable `source` at `target` in one rename, so a half-written binary is never run.
install_binary() {
  local source="$1" target="$2"
  mkdir -p "$(dirname "$target")"
  install -m 0755 "$source" "$target.new"
  mv -f "$target.new" "$target"
}

install_codebase_memory() {
  local target="$BIN_DIR/codebase-memory-mcp" work
  if [ -x "$target" ] && "$target" --version 2>/dev/null | grep -qx "codebase-memory-mcp $CBM_VERSION"; then
    say "codebase-memory-mcp: $CBM_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$CBM_URL" "$CBM_SHA256" "$work" "$CBM_ARCHIVE"
  tar -xzf "$work/$CBM_ARCHIVE" -C "$work" codebase-memory-mcp
  install_binary "$work/codebase-memory-mcp" "$target"
  rm -rf "$work"
  say "codebase-memory-mcp: installed $("$target" --version)"
}

install_bun() {
  local target="$HOME/.bun/bin/bun" work
  if [ -x "$target" ] && [ "$("$target" --version 2>/dev/null)" = "$BUN_VERSION" ]; then
    say "bun: $BUN_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$BUN_URL" "$BUN_SHA256" "$work" bun.zip
  python3 -I -m zipfile -e "$work/bun.zip" "$work"
  install_binary "$work/bun-linux-x64/bun" "$target"
  rm -rf "$work"
  say "bun: installed $("$target" --version) at $target"
}

# Merge this repo's choices into ~/.claude-mem/settings.json, keeping any other key already there.
write_claude_mem_settings() {
  mkdir -p "$CLAUDE_MEM_DIR"
  python3 -I - "$CLAUDE_MEM_DIR/settings.json" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
settings = json.loads(path.read_text()) if path.exists() else {}
settings.update({
    "CLAUDE_MEM_TELEMETRY": "0",
    "CLAUDE_MEM_TELEMETRY_ERRORS": "0",
    "CLAUDE_MEM_CHROMA_ENABLED": "false",
    "CLAUDE_MEM_FILE_READ_GATE_ENABLED": "false",
    "CLAUDE_MEM_CONTEXT_OBSERVATION_TYPES": "decision,bugfix",
    "CLAUDE_MEM_SKIP_SUBAGENT_OBSERVATIONS": "false",
})
path.write_text(json.dumps(settings, indent=2) + "\n")
PY
  say "claude-mem: settings in $CLAUDE_MEM_DIR/settings.json"
}

# Key every checkout under the main one (its .claude/worktrees/ included) as one claude-mem
# project, "score", through a named environment (CLAUDE_MEM_PROJECT_ENVIRONMENTS). Without it each
# worktree is its own project ("score/<worktree>"), so a lesson one sub-agent records never
# reaches a sibling's session start. Other environments already in the file are kept.
write_claude_mem_project_environment() {
  local main_checkout
  main_checkout="$(main_checkout_path)"
  python3 -I - "$CLAUDE_MEM_DIR/settings.json" "$main_checkout" <<'PY'
import json, pathlib, sys
path, main_checkout = pathlib.Path(sys.argv[1]), sys.argv[2]
settings = json.loads(path.read_text()) if path.exists() else {}
environments = settings.get("CLAUDE_MEM_PROJECT_ENVIRONMENTS") or []
if isinstance(environments, str):
    environments = json.loads(environments) if environments.strip() else []
environments = [entry for entry in environments if entry.get("name") != "score"]
environments.append({"name": "score", "patterns": [f"{main_checkout}/**"]})
settings["CLAUDE_MEM_PROJECT_ENVIRONMENTS"] = environments
path.write_text(json.dumps(settings, indent=2) + "\n")
PY
  say "claude-mem: every checkout under $main_checkout is the project \"score\""
}

# Record telemetry as declined in ~/.claude-mem/telemetry.json, so it stays off even for a
# worker started without this repo's DO_NOT_TRACK in its environment.
write_claude_mem_telemetry_off() {
  python3 -I - "$CLAUDE_MEM_DIR/telemetry.json" <<'PY'
import datetime, json, pathlib, sys, uuid
path = pathlib.Path(sys.argv[1])
config = json.loads(path.read_text()) if path.exists() else {}
config["installId"] = config.get("installId") or str(uuid.uuid4())
config["enabled"] = False
config["decidedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
path.write_text(json.dumps(config, indent=2) + "\n")
PY
  say "claude-mem: telemetry declined in $CLAUDE_MEM_DIR/telemetry.json"
}

# ponytail offers, once, to add its status line to ~/.claude/settings.json; its own flag file
# marks the offer as seen.
mark_ponytail_statusline_seen() {
  local flag="$CLAUDE_DIR/.ponytail-statusline-nudged"
  [ -e "$flag" ] || : > "$flag"
  say "ponytail: status line offer marked as seen"
}

# Install the vendored claude-mem plugin into Claude Code's plugin cache for this project. The
# repo's .claude/settings.json declares the marketplace by a relative path, which a headless
# session cannot install from, so the marketplace is added here by its absolute path in the main
# checkout (a worktree's copy would vanish with the worktree; this one's is used only while the
# main checkout has none yet); the CLI writes that path into .claude/settings.json, and the
# committed file is put back.
install_claude_mem_plugin() {
  local settings="$REPO/.claude/settings.json" source saved
  source="$(main_checkout_path)/vendor/claude-mem"
  [ -d "$source" ] || source="$REPO/vendor/claude-mem"
  saved="$(mktemp)"
  cp "$settings" "$saved"
  (cd "$REPO" && claude plugin marketplace add "$source" --scope project >/dev/null \
    && claude plugin install claude-mem@thedotmack --scope project >/dev/null)
  cp "$saved" "$settings"
  rm -f "$saved"
  say "claude-mem: plugin installed for this project from $source"
}

index_repo() {
  "$BIN_DIR/codebase-memory-mcp" cli --quiet index_repository --repo-path "$REPO" >/dev/null
  say "codebase-memory-mcp: indexed $REPO"
}

install_codebase_memory
install_bun
write_claude_mem_settings
write_claude_mem_project_environment
write_claude_mem_telemetry_off
mark_ponytail_statusline_seen
install_claude_mem_plugin
index_repo
