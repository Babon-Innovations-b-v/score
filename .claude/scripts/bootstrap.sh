#!/usr/bin/env bash
# Get a fresh machine working in this repo.
#
#   bash .claude/scripts/bootstrap.sh
#
# Two jobs: link Claude's memory folder into the tracked repo so memory survives a
# wiped machine, and report anything else the loop needs that is not here yet.
# Safe to re-run: every step skips what is already done.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_MEM="$REPO/.claude/memory"

say() { printf '%s\n' "$*"; }

# --- 1. Link Claude's memory folder into the repo --------------------------
# Claude Code stores memory at ~/.claude/projects/<encoded-repo-path>/memory, where
# the encoded path is the absolute repo path with every / turned into -. Point that
# folder at the repo's tracked .claude/memory so memory rides along with git, and the
# Stop hook in .claude/settings.json commits and pushes it.
link_memory() {
  local enc target
  enc="$(printf '%s' "$REPO" | sed 's#/#-#g')"
  target="$HOME/.claude/projects/$enc/memory"
  mkdir -p "$REPO_MEM" "$(dirname "$target")"

  if [ -L "$target" ]; then
    if [ "$(readlink -f "$target")" = "$REPO_MEM" ]; then
      say "memory: already linked"
      return
    fi
    rm "$target"
    ln -s "$REPO_MEM" "$target"
    say "memory: relinked $target -> $REPO_MEM"
    return
  fi

  if [ -d "$target" ]; then
    # A real folder with real memories in it. Move it aside rather than lose it,
    # then copy its contents into the repo so nothing is dropped.
    cp -a "$target/." "$REPO_MEM/" 2>/dev/null || true
    mv "$target" "$target.bak.$$"
    ln -s "$REPO_MEM" "$target"
    say "memory: existing folder copied into the repo and saved to $target.bak.$$"
    return
  fi

  ln -s "$REPO_MEM" "$target"
  say "memory: linked $target -> $REPO_MEM"
}

# --- 2. Report what the loop still needs -----------------------------------
check_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    say "gh: NOT INSTALLED. to-prd, triage, close and my-issues all go through it."
    say "    https://cli.github.com  (or: brew install gh / apt install gh)"
    return
  fi
  if ! gh auth status >/dev/null 2>&1; then
    say "gh: installed but not logged in. Run: gh auth login"
    return
  fi
  say "gh: ready ($(gh api user --jq .login 2>/dev/null || echo 'unknown user'))"
}

check_project_json() {
  local cfg="$REPO/.claude/project.json"
  local repo_field
  repo_field="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('repo',''))" "$cfg" 2>/dev/null || echo '')"
  if [ -z "$repo_field" ]; then
    say "project.json: not filled in yet. Run: python3 .claude/scripts/setup-github.py --board"
  else
    say "project.json: $repo_field"
  fi
}

# --- 3. Use the repo's own git hooks ---------------------------------------
# .githooks/pre-commit refuses a commit that leaves the paper's PDF and LaTeX older than
# its Markdown draft.
use_repo_hooks() {
  git -C "$REPO" config core.hooksPath .githooks
  say "git hooks: .githooks"
}

link_memory
use_repo_hooks
check_gh
check_project_json
say ""
say "Next: fill the placeholders in CLAUDE.md, then start a session and describe the first task."
