#!/usr/bin/env bash
# Everything the conductor needs before `machine.py up`, in one go, free (no machine, no paid call):
#
#   bash tools/cloud/conductor/prepare.sh [--dry]
#
#   the project score-conductor (SCORE_CONDUCTOR_PROJECT), made when missing
#   the conductor's IAM application, policy and API key: Instances, Block Storage, Secret Manager read, Object Storage
#     and SSH keys in the batch project (farm-factory, SCORE_SECRETS_PROJECT); Object Storage in score-conductor;
#     billing and projects read-only in the organisation. Its key goes into the secret score-conductor-key in
#     score-conductor, which `up` reads by name and pipes over ssh: no secret the conductor's key may read, so only
#     the owner's credential reads it, and it is never written to a file on this PC
#   the size function's application, policy (Instances in score-conductor, Object Storage read) and API key, into the
#     secret score-conductor-size-key, and its caller token, score-conductor-size-token, both in the batch project
#   the backups' restic password, score-backup-restic-password; a copy of the sync token, score-cockpit-sync-token
#     (read with this PC's own reader, SCORE_PC_SECRET_READER); score_lib's deploy key (gh, write access),
#     score-lib-deploy-key; all in the batch project, where the conductor's secret reader reads them
#
# Idempotent: what exists is kept as it is (a policy's rules too) and said; a secret with a version is never made
# again. Every secret value goes from the command that makes it into Secret Manager through a file in memory
# (/dev/shm, mode 600, shredded), never on screen or on disk. google-billing-reader is optional and left to the owner:
# without it the conductor skips Google's bill with a note on the Machine card. --dry prints every call it would make
# (on stderr, like the progress lines) and makes none. In an agent's process it runs only under the owner's recorded
# yes to the switch (score/store/backup/conductor_yes.py), and marks its prepare step done at the end.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
dry=
[ "${1:-}" = --dry ] && dry=1
scw="${SCORE_SCW:-scw}"
gh="${SCORE_GH:-gh}"
pc_reader="${SCORE_PC_SECRET_READER:-$HOME/.local/bin/score-secret-reader}"
batch_name="${SCORE_SECRETS_PROJECT:-farm-factory}"
conductor_name="${SCORE_CONDUCTOR_PROJECT:-score-conductor}"
region=fr-par
lib_repo=Babon-Innovations-b-v/score_lib
umask 077

say() { echo "prepare: $*" >&2; }

# The owner's yes for prepare: `check` or `done` (the owner's own process needs none; a dry run neither).
yes_step() { [ -n "$dry" ] || (cd "$repo" && python3 -m score.store.backup.conductor_yes "$1" prepare); }

# A read's JSON answer; dry: the call printed, an empty list answered.
read_json() { if [ -n "$dry" ]; then echo "scw $*" >&2; echo '[]'; else "$scw" "$@" -o json; fi; }

# A make's JSON answer, never shown; dry: the call printed, a placeholder answered.
make_json() {
  if [ -n "$dry" ]; then
    echo "scw $*" >&2
    echo '{"id": "<new>", "access_key": "<new>", "secret_key": "<new>"}'
  else
    "$scw" "$@" -o json
  fi
}

# A command whose output is a secret value; dry: the command printed, a placeholder answered.
produce() { if [ -n "$dry" ]; then echo "$*" >&2; echo "<value>"; else "$@"; fi; }

# The field $1 of the JSON object on stdin.
field() { python3 -I -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }

# The id of the one item named $1 in the JSON list on stdin, or nothing.
named_id() {
  python3 -I -c '
import json, sys
found = [item["id"] for item in json.load(sys.stdin) or [] if item.get("name") == sys.argv[1]]
if len(found) > 1:
    sys.exit(f"prepare: {len(found)} items named {sys.argv[1]}; resolve that by hand")
print(found[0] if found else "")' "$1"
}

# The secret $1 in project $2: "held" when it has a version, its id when it has none yet, else nothing.
secret_state() {
  read_json secret secret list name="$1" project-id="$2" region="$region" | python3 -I -c '
import json, sys
found = [item for item in json.load(sys.stdin) or [] if item.get("name") == sys.argv[1]]
if len(found) > 1:
    sys.exit(f"prepare: {len(found)} secrets named {sys.argv[1]}; resolve that by hand")
print("" if not found else "held" if found[0].get("version_count") else found[0]["id"])' "$1"
}

# The value on stdin (its trailing newlines dropped) as the first version of the secret $1 in project $2, through a
# file in memory; $3 the id of the secret when it exists without a version.
put_secret() {
  local value file sid="${3:-}"
  value="$(cat)"
  if [ -n "$dry" ]; then
    [ -n "$sid" ] || echo "scw secret secret create name=$1 project-id=$2 region=$region" >&2
    echo "scw secret version create secret-id=<its id> data=@<a file in /dev/shm> region=$region" >&2
    return
  fi
  [ -n "$value" ] || { say "the value for $1 came out empty; nothing stored"; exit 1; }
  file="$(mktemp "$work/secret.XXXXXX")"
  printf '%s' "$value" > "$file"
  [ -n "$sid" ] || sid="$("$scw" secret secret create name="$1" project-id="$2" region="$region" -o json | field id)"
  "$scw" secret version create secret-id="$sid" data=@"$file" region="$region" -o json > /dev/null
  shred -u "$file"
  say "made the secret $1"
}

# Store the output of the command after `--` as the secret $1 in project $2, unless it is held already.
secret() {
  local name="$1" project="$2" state
  shift 3
  state="$(secret_state "$name" "$project")"
  if [ "$state" = held ]; then
    say "have the secret $name"
    return
  fi
  "$@" | put_secret "$name" "$project" "$state"
}

# The id of the project named $1, made when $2 is "make" and it is missing.
project() {
  local id
  id="$(read_json account project list name="$1" | named_id "$1")"
  if [ -z "$id" ] && [ "${2:-}" = make ]; then
    id="$(make_json account project create name="$1" description="SCORE conductor" | field id)"
    say "made the project $1"
  fi
  [ -n "$id" ] || [ -z "$dry" ] || id="<id of $1>"
  [ -n "$id" ] || { say "no project named $1"; exit 1; }
  echo "$id"
}

# The id of the IAM application $1 ($2 its description), made when missing.
application() {
  local id
  id="$(read_json iam application list name="$1" organization-id="$organisation" | named_id "$1")"
  if [ -z "$id" ]; then
    id="$(make_json iam application create name="$1" description="$2" organization-id="$organisation" | field id)"
    say "made the application $1"
  fi
  echo "$id"
}

# The policy $1 for application $2 with the rules after them, made when missing (an existing one is kept as it is).
policy() {
  local name="$1" app="$2"
  shift 2
  if [ -n "$(read_json iam policy list policy-name="$name" organization-id="$organisation" | named_id "$name")" ]; then
    say "have the policy $name (kept as it is)"
    return
  fi
  make_json iam policy create name="$name" application-id="$app" organization-id="$organisation" "$@" > /dev/null
  say "made the policy $name"
}

# A new API key of application $1 (default project $2, description $3), as {access_key, secret_key}.
api_key() {
  make_json iam api-key create application-id="$1" default-project-id="$2" description="$3" | python3 -I -c '
import json, sys
key = json.load(sys.stdin)
print(json.dumps({"access_key": key["access_key"], "secret_key": key["secret_key"]}))'
}

# A new deploy key with write access to score_lib: its private half on stdout, its public half given to GitHub.
lib_key() {
  if [ -n "$dry" ]; then
    echo "ssh-keygen -q -t ed25519 -N '' -C score-conductor -f <a file in /dev/shm>" >&2
    echo "$gh repo deploy-key add <its .pub> -R $lib_repo -w -t score-conductor" >&2
    echo "<value>"
    return
  fi
  ssh-keygen -q -t ed25519 -N "" -C score-conductor -f "$work/lib"
  "$gh" repo deploy-key add "$work/lib.pub" -R "$lib_repo" -w -t score-conductor > /dev/null
  cat "$work/lib"
  shred -u "$work/lib"
  rm -f "$work/lib.pub"
}

yes_step check
if [ -z "$dry" ]; then
  work="$(mktemp -d /dev/shm/score-prepare.XXXXXX)"
  trap 'rm -rf "$work"' EXIT
  organisation="$("$scw" config get default-organization-id)"
else
  organisation="<organisation id>"
fi
batch="$(project "$batch_name")"
conductor="$(project "$conductor_name" make)"

app="$(application score-conductor "SCORE conductor machine")"
policy score-conductor "$app" \
  rules.0.project-ids.0="$batch" rules.0.permission-set-names.0=InstancesFullAccess \
  rules.0.permission-set-names.1=BlockStorageFullAccess rules.0.permission-set-names.2=SecretManagerSecretAccess \
  rules.0.permission-set-names.3=SecretManagerReadOnly rules.0.permission-set-names.4=ObjectStorageFullAccess \
  rules.0.permission-set-names.5=SSHKeysFullAccess rules.0.permission-set-names.6=ContainerRegistryFullAccess \
  rules.1.project-ids.0="$conductor" rules.1.permission-set-names.0=ObjectStorageFullAccess \
  rules.2.organization-id="$organisation" rules.2.permission-set-names.0=BillingReadOnly \
  rules.2.permission-set-names.1=ProjectReadOnly
secret score-conductor-key "$conductor" -- api_key "$app" "$conductor" score-conductor

size="$(application score-conductor-size "grows and shrinks the conductor")"
policy score-conductor-size "$size" \
  rules.0.project-ids.0="$conductor" rules.0.permission-set-names.0=InstancesFullAccess \
  rules.0.permission-set-names.1=ObjectStorageReadOnly
secret score-conductor-size-key "$batch" -- api_key "$size" "$conductor" score-conductor-size
secret score-conductor-size-token "$batch" -- produce openssl rand -hex 32

secret score-backup-restic-password "$batch" -- produce openssl rand -base64 32
secret score-cockpit-sync-token "$batch" -- produce "$pc_reader" score-cockpit-sync-token
secret score-lib-deploy-key "$batch" -- lib_key

say "google-billing-reader is optional: without it the conductor skips Google's bill (a note on the Machine card)"
yes_step done
say "done${dry:+ (dry: nothing made)}"
