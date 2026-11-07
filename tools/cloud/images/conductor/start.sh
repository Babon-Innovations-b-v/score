#!/bin/sh
# score-conductor-start: the conductor container's start (tools/cloud/k8s/conductor), boot.sh's user part for a pod.
# The checkout is cloned onto the store volume when missing (~/projects/score), its .venv synced from uv.lock, the prop
# environment ($PROPS_HOME/env) once machine.json is there (the restore goes only into an empty home), then the VM's
# always-on units run as one process (units.py). update.py, one of those units, moves the checkout to the cockpit's pin.
set -eu
REPO_URL=https://github.com/Babon-Innovations-b-v/score
repo="$HOME/projects/score"
props="${PROPS_HOME:-$HOME/.farm-factory-props}"
mkdir -p "$HOME/.config/score" "$HOME/.local/bin" "${XDG_RUNTIME_DIR:-/tmp}/score"
if [ ! -d "$repo/.git" ]; then
  git clone -q "$REPO_URL" "$repo"
  echo "score-conductor-start: score cloned to $repo"
fi
/usr/bin/python3 -I "$repo/tools/cloud/conductor/update.py" --repo "$repo" || echo "score-conductor-start: update failed; the checkout stays where it is"
(cd "$repo" && uv sync -q --frozen --group dashboard)
if [ -f "$props/machine.json" ]; then
  UV_PROJECT_ENVIRONMENT="$props/env" uv sync -q --frozen --no-dev --project "$repo"
fi
exec /usr/bin/python3 -I "$repo/tools/cloud/k8s/conductor/units.py"
