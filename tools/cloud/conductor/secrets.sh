#!/bin/sh
# score-secrets.service: the secrets a tool can only take as a file, written to tmpfs at $XDG_RUNTIME_DIR/score
# (/run/user/<uid>/score, mode 600, gone at reboot), never to disk; run at boot and every hour by its timer.
#   score-lib-deploy-key      the deploy key that may push to score_lib (score_lib's core.sshCommand names this file)
#   google-billing-reader     a service-account JSON for bq (the bill read-back), activated into a gcloud config
#                             that lives on the same tmpfs (CLOUDSDK_CONFIG=$XDG_RUNTIME_DIR/score/gcloud)
# Each is read by name through the secret reader and lands in one rename, so a reader never sees half a file.
set -eu
dir="${XDG_RUNTIME_DIR:?score-secrets: no XDG_RUNTIME_DIR}/score"
reader="${SCORE_SECRET_READER:-/usr/local/bin/score-secret-reader}"
gcloud="${SCORE_GCLOUD:-/opt/google-cloud-sdk/bin/gcloud}"
umask 077
mkdir -p "$dir"
chmod 700 "$dir"

# Write the secret named $1 to $dir/$2, whole, ending in a newline (ssh refuses a key without one).
write_secret() {
  partial="$(mktemp "$dir/.$2.XXXXXX")"
  "$reader" "$1" > "$partial"
  if [ ! -s "$partial" ]; then
    rm -f "$partial"
    echo "score-secrets: the secret $1 is empty" >&2
    exit 1
  fi
  [ "$(tail -c 1 "$partial" | od -An -c | tr -d ' ')" = '\n' ] || echo >> "$partial"
  chmod 600 "$partial"
  mv -f "$partial" "$dir/$2"
}

write_secret score-lib-deploy-key score-lib-deploy-key
write_secret google-billing-reader google-billing-reader.json
CLOUDSDK_CONFIG="$dir/gcloud" "$gcloud" auth activate-service-account --quiet \
  --key-file="$dir/google-billing-reader.json" > /dev/null
echo "score-secrets: score-lib-deploy-key and google-billing-reader written to $dir"
