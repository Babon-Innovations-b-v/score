#!/bin/sh
# The conductor's secret reader, installed by boot.sh as /usr/local/bin/score-secret-reader and named by
# SCORE_SECRET_READER in ~/.config/score/dashboard.env: prints the latest value of the secret its one argument names,
# from Scaleway Secret Manager, to stdout only, never a file. The project is looked up by its name
# (SCORE_SECRETS_PROJECT) on every read, so no project id is written anywhere. It reads as user score's one credential,
# ~/.config/scw/config.yaml. Full paths: systemd gives a unit a short PATH. With --if-present, a secret the project does
# not hold prints nothing and exits 0 (an optional one: google-billing-reader); any other failure still fails.
set -eu
optional=
[ "${1:-}" = --if-present ] && { optional=1; shift; }
[ "$#" -eq 1 ] || { echo "usage: score-secret-reader [--if-present] <secret name>" >&2; exit 2; }
project="${SCORE_SECRETS_PROJECT:?score-secret-reader: SCORE_SECRETS_PROJECT names no project}"
region="${SCORE_SECRETS_REGION:-fr-par}"
scw="${SCORE_SCW:-/usr/local/bin/scw}"
python="${SCORE_READER_PYTHON:-/usr/bin/python3}"
id="$("$scw" account project list name="$project" -o json | "$python" -I -c '
import json, sys
name = sys.argv[1]
found = [project["id"] for project in json.load(sys.stdin) if project["name"] == name]
if len(found) != 1:
    sys.exit(f"score-secret-reader: expected one Scaleway project named {name}, found {len(found)}")
print(found[0])' "$project")"
if [ -n "$optional" ]; then
  held="$("$scw" secret secret list name="$1" project-id="$id" region="$region" -o json | "$python" -I -c '
import json, sys
print(sum(1 for secret in json.load(sys.stdin) or [] if secret["name"] == sys.argv[1]))' "$1")"
  [ "$held" -gt 0 ] || exit 0
fi
"$scw" secret version access-by-path secret-name="$1" project-id="$id" revision=latest region="$region" -o json \
  | "$python" -I -c 'import base64, json, sys; sys.stdout.write(base64.b64decode(json.load(sys.stdin)["data"]).decode())'
