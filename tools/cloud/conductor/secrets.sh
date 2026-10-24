#!/bin/sh
# score-secrets.service: the secrets a tool can only take as a file, written to tmpfs at $XDG_RUNTIME_DIR/score
# (/run/user/<uid>/score, mode 600, gone at reboot), never to disk; run at boot and every hour by its timer.
#   score-lib-deploy-key      the deploy key that may push to score_lib (score_lib's core.sshCommand names this file)
#   google-billing-reader     optional: a service-account JSON for bq (the bill read-back), activated into a gcloud
#                             config on the same tmpfs (CLOUDSDK_CONFIG=$XDG_RUNTIME_DIR/score/gcloud). When the
#                             project holds no such secret, google-billing-reader.note here says so (score.conductor
#                             health carries every *.note here to the Machine card), the books' Google read-back stays
#                             unread, and nothing fails.
# Each is read by name through the secret reader and lands in one rename, so a reader never sees half a file.
set -eu
dir="${XDG_RUNTIME_DIR:?score-secrets: no XDG_RUNTIME_DIR}/score"
reader="${SCORE_SECRET_READER:-/usr/local/bin/score-secret-reader}"
gcloud="${SCORE_GCLOUD:-/opt/google-cloud-sdk/bin/gcloud}"
umask 077
mkdir -p "$dir"
chmod 700 "$dir"

# Write the secret named $1 to $dir/$2, whole, ending in a newline (ssh refuses a key without one). With a third
# argument the secret is optional: when the project holds none, $dir/$2 is removed and the function returns 1.
write_secret() {
  partial="$(mktemp "$dir/.$2.XXXXXX")"
  "$reader" ${3:+--if-present} "$1" > "$partial" || { rm -f "$partial"; echo "score-secrets: reading $1 failed" >&2; exit 1; }
  if [ ! -s "$partial" ]; then
    rm -f "$partial"
    if [ -n "${3:-}" ]; then
      rm -f "$dir/$2"
      return 1
    fi
    echo "score-secrets: the secret $1 is empty" >&2
    exit 1
  fi
  [ "$(tail -c 1 "$partial" | od -An -c | tr -d ' ')" = '\n' ] || echo >> "$partial"
  chmod 600 "$partial"
  mv -f "$partial" "$dir/$2"
}

write_secret score-lib-deploy-key score-lib-deploy-key
note="$dir/google-billing-reader.note"
if write_secret google-billing-reader google-billing-reader.json optional; then
  CLOUDSDK_CONFIG="$dir/gcloud" "$gcloud" auth activate-service-account --quiet \
    --key-file="$dir/google-billing-reader.json" > /dev/null
  rm -f "$note"
  echo "score-secrets: score-lib-deploy-key and google-billing-reader written to $dir"
else
  echo "no google-billing-reader secret: Google's bill is not read on this machine (optional; add the secret to read it)" > "$note"
  echo "score-secrets: score-lib-deploy-key written to $dir; no google-billing-reader secret, skipped"
fi
