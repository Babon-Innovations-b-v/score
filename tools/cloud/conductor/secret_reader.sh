#!/bin/sh
# The conductor's secret reader, installed by boot.sh as /usr/local/bin/score-secret-reader and named by
# SCORE_SECRET_READER in ~/.config/score/dashboard.env: prints the latest value of the secret its one argument names,
# from Scaleway Secret Manager, to stdout only, never a file. The project is looked up by its name
# (SCORE_SECRETS_PROJECT) on every read, so no project id is written anywhere. It reads as user score's one credential,
# ~/.config/scw/config.yaml. Full paths: systemd gives a unit a short PATH.
set -eu
[ "$#" -eq 1 ] || { echo "usage: score-secret-reader <secret name>" >&2; exit 2; }
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
"$scw" secret version access-by-path secret-name="$1" project-id="$id" revision=latest region="$region" -o json \
  | "$python" -I -c 'import base64, json, sys; sys.stdout.write(base64.b64decode(json.load(sys.stdin)["data"]).decode())'
