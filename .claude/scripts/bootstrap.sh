#!/usr/bin/env bash
# Get a fresh machine working in this repo.
#
#   bash .claude/scripts/bootstrap.sh
#
# Link Claude's memory folder into the repo (git-ignored: the repo is public), use the
# repo's git hooks, build the framework's Python from uv.lock, and report anything else the loop
# needs that is not here yet.
# Safe to re-run: every step skips what is already done.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_MEM="$REPO/.claude/memory"

say() { printf '%s\n' "$*"; }

# --- 1. Link Claude's memory folder into the repo --------------------------
# Claude Code stores memory at ~/.claude/projects/<encoded-repo-path>/memory, where
# the encoded path is the absolute repo path with every / turned into -. Point that
# folder at the repo's .claude/memory. That folder is git-ignored, so memory stays on this
# machine and is never pushed to the public repository.
link_memory() {
  local enc target
  enc="$(printf '%s' "$REPO" | sed 's#/#-#g')"
  target="$HOME/.claude/projects/$enc/memory"
  mkdir -p "$REPO_MEM" "$(dirname "$target")"
  if [ -L "$target" ] && [ "$(readlink -f "$target")" = "$REPO_MEM" ]; then
    say "memory: already linked"
    return
  fi
  local message="memory: linked $target -> $REPO_MEM"
  if [ -L "$target" ]; then
    rm "$target"
    message="memory: relinked $target -> $REPO_MEM"
  elif [ -d "$target" ]; then
    # A real folder with real memories in it: copy them into the repo, then move it aside.
    cp -a "$target/." "$REPO_MEM/" 2>/dev/null || true
    mv "$target" "$target.bak.$$"
    message="memory: existing folder copied into the repo and saved to $target.bak.$$"
  fi
  ln -s "$REPO_MEM" "$target"
  say "$message"
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
  local repo_field
  repo_field="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('repo',''))" \
    "$REPO/.claude/project.json" 2>/dev/null || echo '')"
  if [ -z "$repo_field" ]; then
    say "project.json: not filled in yet. Run: python3 .claude/scripts/setup-github.py --board"
  else
    say "project.json: $repo_field"
  fi
}

# The store's backups (score/store/backup) run restic; its tests skip without it.
check_restic() {
  if ! command -v restic >/dev/null 2>&1; then
    say "restic: NOT INSTALLED. The store's backups and the move need it (the conductor's boot installs it pinned)."
    say "    https://restic.readthedocs.io/en/stable/020_installation.html"
    return
  fi
  say "restic: $(restic version | cut -d' ' -f2)"
}

# --- 3. Use the repo's own git hooks ---------------------------------------
# .githooks/pre-commit refuses a commit that leaves the paper's PDF and LaTeX older than
# its Markdown draft.
use_repo_hooks() {
  git -C "$REPO" config core.hooksPath .githooks
  say "git hooks: .githooks"
}

# --- 4. The framework's Python, from uv.lock -------------------------------
# `.venv` is the repo's own (`make env`). The cloud machine runner (blender_cloud.py's CLOUD_PYTHON) and
# the animal route still call the first environment's per-box interpreter, PROPS_HOME's env/bin/python (default
# ~/.farm-factory-props, as tools/props/paths.py reads it): build that path from the same lock when it is
# missing, so a fresh box runs them with nothing copied over.
build_python() {
  if ! command -v uv >/dev/null 2>&1; then
    say "uv: NOT INSTALLED. The framework's Python needs it: https://docs.astral.sh/uv/"
    return
  fi
  (cd "$REPO" && uv sync -q --frozen)
  say "python: .venv from uv.lock"
  local runtime="${PROPS_HOME:-$HOME/.farm-factory-props}/env"
  if [ -x "$runtime/bin/python" ]; then
    say "runtime python: already at $runtime"
    return
  fi
  UV_PROJECT_ENVIRONMENT="$runtime" uv sync -q --frozen --no-dev --project "$REPO"
  say "runtime python: built at $runtime from uv.lock"
}

# --- 5. gltfpack for score_lib's web copies (#34) ---------------------------
# score_lib's web3d/pack.py runs `npx --offline gltfpack@<pin>`: seed that pin into the npm cache.
GLTFPACK_PIN="gltfpack@0.22.0"  # keep equal to GLTFPACK in score_lib's src/score_lib/web3d/pack.py
seed_gltfpack() {
  if ! command -v npm >/dev/null 2>&1; then
    say "gltfpack: npm NOT INSTALLED. score_lib's web copies need Node.js"
    return
  fi
  npm cache add "$GLTFPACK_PIN" >/dev/null
  say "gltfpack: $GLTFPACK_PIN in the npm cache"
}

link_memory
use_repo_hooks
build_python
seed_gltfpack
check_gh
check_restic
check_project_json
say ""
say "Next: fill the placeholders in CLAUDE.md, then start a session and describe the first task."
