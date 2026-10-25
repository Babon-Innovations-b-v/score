#!/usr/bin/env bash
# The conductor's boot, run at every boot by score-boot.service (cloud-init.yaml installs it), which first clones this
# repository when missing and moves it to origin/main. Safe to re-run.
#
#   bash tools/cloud/conductor/boot.sh system     # as root, with systemd's and D-Bus's sockets up (score-boot.service)
#   bash tools/cloud/conductor/boot.sh user       # as score, after the system part: the checkout, .venv, units, score_lib
#   bash tools/cloud/conductor/boot.sh env        # as score: the prop environment alone
#
# system: the packages; user score (uid 1100) with linger; the data volume (SCORE_DATA_DEVICE, cloud-init's
#   /etc/score-conductor.env) formatted only when blank and mounted at /home/score/.farm-factory-props through fstab by
#   UUID; restic, uv, the scw CLI, Node.js and the Google Cloud CLI (bq) at pinned versions, each checked against its
#   SHA-256 as .claude/scripts/install-agent-tools.sh does (a mismatch stops the boot and installs nothing); the secret
#   reader and the agents' door in /usr/local/bin; sshd keys-only, no root, user score only.
# user: the checkout cloned when missing (score-update.service moves it later), `uv sync`, gltfpack's pin in the npm
#   cache (score_lib's web copies run it offline), every unit in units/
#   installed as a user unit and enabled; once the move wrote machine.json, the prop environment ($PROPS_HOME/env,
#   the rows' PROPS_PYTHON, never backed up) synced from uv.lock; once ~/.config/scw/config.yaml is there (machine.py up
#   pipes it over ssh), the tmpfs secrets written and score_lib cloned with its deploy key from tmpfs, its .venv synced.
# env: the prop environment alone (the move runs it right after its restore).
#
# SCORE_BOOT_ROOT puts every path under another root (the dry check, machine_test.py, runs it against a temp root
# with its commands shimmed); on the machine it is empty.
set -Eeuo pipefail
# Any failing command stops the boot and names itself, so the boot log says where it stopped.
trap 'code=$?; echo "boot: stopped at boot.sh line $LINENO, exit $code: $BASH_COMMAND" >&2' ERR

ROOT="${SCORE_BOOT_ROOT:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCORE_USER=score
SCORE_UID=1100
REPO_URL=https://github.com/Babon-Innovations-b-v/score
LIB_URL=git@github.com:Babon-Innovations-b-v/score_lib.git
# rsync and ssh: the cloud runners' copies to and from rented machines (batch.copy); ffmpeg: the sound rows' loudness;
# node and npm come from NODE_URL below, not apt (Ubuntu's is older than the film preview's Playwright takes).
APT_PACKAGES=(git sqlite3 ca-certificates curl bzip2 python3 rsync openssh-client ffmpeg)
BIN="$ROOT/usr/local/bin"

RESTIC_VERSION=0.19.1
RESTIC_URL="https://github.com/restic/restic/releases/download/v$RESTIC_VERSION/restic_${RESTIC_VERSION}_linux_amd64.bz2"
RESTIC_SHA256=f415415624dcc452f2a02b8c33641791a8c6d6d3b65bbb3543fcf9a25151585c
UV_VERSION=0.12.23
UV_URL="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz"
UV_SHA256=9167d72b3319674b6303c4cbe071854bba13ebdf3d76b1a7cbdc175471fb66d6
SCW_VERSION=2.65.1
SCW_URL="https://github.com/scaleway/scaleway-cli/releases/download/v$SCW_VERSION/scaleway-cli_${SCW_VERSION}_linux_amd64"
SCW_SHA256=b9ced8bc52c27baba76136a24e65a5e0abd53e9499edf02226513977d45da503
# Node.js (node, npm, npx in /usr/local/bin): the 3D web copies' gltfpack and the film preview's recorder, whose
# playwright@1.62.1 takes node >=20 (its package.json engines). An LTS line; the checksum from the release's SHASUMS256.txt.
NODE_VERSION=24.21.0
NODE_URL="https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.gz"
NODE_SHA256=6e1db87ef58b8819e5d5402eff1536491b18edd8eb7bee5ef7897876e88dc5ff
GCLOUD_VERSION=588.0.0
GCLOUD_URL="https://storage.googleapis.com/cloud-sdk-release/google-cloud-cli-$GCLOUD_VERSION-linux-x86_64.tar.gz"
GCLOUD_SHA256=e38ceac43022bb5a4d94d5a4a9c9c51f90f28c910b59a018ae07011e220c4412
# GitHub's published host keys (api.github.com/meta, 2026-10-22): score_lib's pushes check the host against these only.
GITHUB_KEYS='github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg='
# The deploy templates' slots (score/dashboard/deploy), filled for user score when a unit in units/ carries them.
REPO_SLOT='<path to the score repository>'
ENV_SLOT='<path to the env file kept outside the repo>'
SECRET_SLOT="<the sync token's name in your secret manager>"

say() { printf 'boot: %s\n' "$*"; }

# Download `url` into the folder `dir` as `name` and stop unless its SHA-256 is `sha`.
download_checked() {
  local url="$1" sha="$2" dir="$3" name="$4"
  curl -fsSL -o "$dir/$name" "$url"
  if ! echo "$sha  $dir/$name" | sha256sum -c --quiet - > /dev/null 2>&1; then
    echo "boot: $url does not match its pinned SHA-256; nothing installed" >&2
    exit 1
  fi
}

# Put the executable `source` at `target` in one rename, so a half-written binary is never run.
install_binary() {
  local source="$1" target="$2"
  mkdir -p "$(dirname "$target")"
  install -m 0755 "$source" "$target.new"
  mv -f "$target.new" "$target"
}

install_packages() {
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${APT_PACKAGES[@]}" > /dev/null
  # Ubuntu's older node (apt's nodejs, which boots before 2026-10-25 installed) goes, so only install_node's is found.
  DEBIAN_FRONTEND=noninteractive apt-get remove -y -q nodejs > /dev/null
  say "packages: ${APT_PACKAGES[*]}; apt's nodejs removed"
}

# The film preview's recorder (score/dashboard/films/preview/make.py PLAYWRIGHT): Chromium's system libraries here,
# the browser itself in user score's cache (chromium_browser), so the sync pass can render a locked script's preview.
PLAYWRIGHT="playwright@1.62.1"
chromium_libraries() {
  PATH="$BIN:$PATH" npx -y -p "$PLAYWRIGHT" playwright install-deps chromium > /dev/null
  say "Chromium's libraries for $PLAYWRIGHT"
}

chromium_browser() {
  PATH="$BIN:$PATH" npx -y -p "$PLAYWRIGHT" playwright install chromium > /dev/null
  say "Chromium for $PLAYWRIGHT"
}

# score_lib's web copies run `npx --offline -y gltfpack@<pin>` (its src/score_lib/web3d/pack.py GLTFPACK; this repo's
# tools/review/viewer/export.py GLTFPACK): offline, so the pin must be in user score's npm cache, as bootstrap.sh's
# seed_gltfpack puts it on the PC. Checked by running it from the cache alone (its -h prints its version, exit 1).
GLTFPACK_PIN="gltfpack@0.22.0"
gltfpack_cache() {
  local said version="${GLTFPACK_PIN#gltfpack@}"
  PATH="$BIN:$PATH" npm cache add "$GLTFPACK_PIN" > /dev/null
  said="$(PATH="$BIN:$PATH" npx --offline -y "$GLTFPACK_PIN" -h 2>&1 || true)"
  case "$said" in
    "gltfpack ${version%.*}"*) ;;  # it says its major and minor: "gltfpack 0.22"
    *) echo "boot: $GLTFPACK_PIN does not run from the npm cache: ${said:0:300}" >&2; exit 1 ;;
  esac
  say "$GLTFPACK_PIN in user $SCORE_USER's npm cache"
}

ensure_user() {
  if ! id -u "$SCORE_USER" > /dev/null 2>&1; then
    useradd --uid "$SCORE_UID" --create-home --shell /bin/bash "$SCORE_USER"
  fi
  loginctl enable-linger "$SCORE_USER"
  say "user $SCORE_USER with linger"
}

mount_data() {
  local device="${SCORE_DATA_DEVICE:?boot: SCORE_DATA_DEVICE names no data volume (cloud-init writes it)}"
  local mountpoint="/home/$SCORE_USER/.farm-factory-props" found uuid
  found=0
  blkid -p "$device" > /dev/null 2>&1 || found=$?
  if [ "$found" -eq 2 ]; then
    mkfs.ext4 -q -L score-data "$device"
    say "data volume formatted (it was blank)"
  elif [ "$found" -ne 0 ]; then
    echo "boot: blkid could not read $device (exit $found); not formatting it" >&2
    exit 1
  fi
  uuid="$(blkid -s UUID -o value "$device")"
  [ -n "$uuid" ] || { echo "boot: $device has no UUID" >&2; exit 1; }
  if ! grep -q "^UUID=$uuid " "$ROOT/etc/fstab" 2> /dev/null; then
    echo "UUID=$uuid $mountpoint ext4 defaults,nofail,x-systemd.device-timeout=60 0 2" >> "$ROOT/etc/fstab"
  fi
  mkdir -p "$ROOT$mountpoint"
  if ! mountpoint -q "$ROOT$mountpoint"; then
    # The bare folder under the mount is made immutable: when the volume does not attach at a boot (nofail), the
    # runner, sync and resume fail on it instead of starting an empty store on the root disk.
    chattr +i "$ROOT$mountpoint"
    mount "$ROOT$mountpoint"
  fi
  chown "$SCORE_USER:$SCORE_USER" "$ROOT$mountpoint"
  say "data volume $uuid at $mountpoint"
}

install_restic() {
  local work
  if [ -x "$BIN/restic" ] && "$BIN/restic" version 2> /dev/null | grep -q "^restic $RESTIC_VERSION "; then
    say "restic $RESTIC_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$RESTIC_URL" "$RESTIC_SHA256" "$work" restic.bz2
  bunzip2 -c "$work/restic.bz2" > "$work/restic"
  install_binary "$work/restic" "$BIN/restic"
  rm -rf "$work"
  say "restic $RESTIC_VERSION installed"
}

install_uv() {
  local work
  if [ -x "$BIN/uv" ] && [ "$("$BIN/uv" --version 2> /dev/null | cut -d' ' -f2)" = "$UV_VERSION" ]; then
    say "uv $UV_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$UV_URL" "$UV_SHA256" "$work" uv.tar.gz
  tar -xzf "$work/uv.tar.gz" -C "$work"
  install_binary "$work/uv-x86_64-unknown-linux-gnu/uv" "$BIN/uv"
  install_binary "$work/uv-x86_64-unknown-linux-gnu/uvx" "$BIN/uvx"
  rm -rf "$work"
  say "uv $UV_VERSION installed"
}

install_scw() {
  local work
  if [ -x "$BIN/scw" ] && "$BIN/scw" version 2> /dev/null | grep -Eq "^Version +$SCW_VERSION\$"; then
    say "scw $SCW_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$SCW_URL" "$SCW_SHA256" "$work" scw
  install_binary "$work/scw" "$BIN/scw"
  rm -rf "$work"
  say "scw $SCW_VERSION installed"
}

install_node() {
  local work lib="$ROOT/usr/local/lib/nodejs" name
  if [ -x "$BIN/node" ] && [ "$("$BIN/node" --version 2> /dev/null)" = "v$NODE_VERSION" ]; then
    say "node $NODE_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$NODE_URL" "$NODE_SHA256" "$work" node.tar.gz
  tar -xzf "$work/node.tar.gz" -C "$work"
  mkdir -p "$lib" "$BIN"
  rm -rf "$lib/node-v$NODE_VERSION"
  mv "$work/node-v$NODE_VERSION-linux-x64" "$lib/node-v$NODE_VERSION"
  for name in node npm npx; do
    ln -sfn "/usr/local/lib/nodejs/node-v$NODE_VERSION/bin/$name" "$BIN/$name"
  done
  rm -rf "$work"
  say "node $NODE_VERSION installed (node, npm, npx)"
}

install_gcloud() {
  local work sdk="$ROOT/opt/google-cloud-sdk"
  if [ "$(cat "$sdk/VERSION" 2> /dev/null)" = "$GCLOUD_VERSION" ]; then
    say "google-cloud-cli $GCLOUD_VERSION already installed"
    return
  fi
  work="$(mktemp -d)"
  download_checked "$GCLOUD_URL" "$GCLOUD_SHA256" "$work" gcloud.tar.gz
  tar -xzf "$work/gcloud.tar.gz" -C "$work"
  rm -rf "$sdk.new"
  mkdir -p "$ROOT/opt"
  mv "$work/google-cloud-sdk" "$sdk.new"
  rm -rf "$sdk"
  mv "$sdk.new" "$sdk"
  rm -rf "$work"
  mkdir -p "$BIN"
  ln -sfn /opt/google-cloud-sdk/bin/gcloud "$BIN/gcloud"
  ln -sfn /opt/google-cloud-sdk/bin/bq "$BIN/bq"
  say "google-cloud-cli $GCLOUD_VERSION installed (gcloud, bq)"
}

install_scripts() {
  install_binary "$HERE/secret_reader.sh" "$BIN/score-secret-reader"
  install_binary "$HERE/agent_door.sh" "$BIN/score-agent-door"
  say "score-secret-reader and score-agent-door in /usr/local/bin"
}

harden_ssh() {
  mkdir -p "$ROOT/etc/ssh/sshd_config.d"
  cat > "$ROOT/etc/ssh/sshd_config.d/50-score-conductor.conf" << EOF
# The conductor's sshd (tools/cloud/conductor/boot.sh): keys only, no root, user score only. The agents' key is held
# to /usr/local/bin/score-agent-door by its authorized_keys line.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers $SCORE_USER
EOF
  systemctl try-reload-or-restart ssh.service
  say "sshd: keys only, user $SCORE_USER only"
}

system_part() {
  [ -n "$ROOT" ] || [ "$(id -u)" -eq 0 ] || { echo "boot: the system part runs as root" >&2; exit 1; }
  # cloud-init's bootcmd runs before D-Bus is up; loginctl and the units need it, so stop here and say so.
  if [ ! -S "$ROOT/run/dbus/system_bus_socket" ]; then
    echo "boot: no system bus at /run/dbus/system_bus_socket (run from early boot?); the system part runs from" \
      "score-boot.service after the network is up" >&2
    exit 1
  fi
  install_packages
  ensure_user
  mount_data
  install_restic
  install_uv
  install_scw
  install_node
  chromium_libraries
  install_gcloud
  install_scripts
  harden_ssh
  # user score's manager, for the user part score-boot.service runs next
  systemctl start "user@$SCORE_UID.service"
}

checkout() {
  local repo="$1"
  if [ ! -d "$repo/.git" ]; then
    git clone -q "$REPO_URL" "$repo"
    say "score cloned to $repo"
  fi
  (cd "$repo" && "$BIN/uv" sync -q --frozen --group dashboard)
  say ".venv synced from uv.lock"
}

# The prop environment the rows run their tools in ($PROPS_HOME/env, bootstrap.sh's build_python and update.py's
# re-sync, the same command). Only once the move wrote machine.json: the restore goes only into an empty home.
props_env() {
  local repo="$1" props="$HOME/.farm-factory-props"
  if [ ! -f "$props/machine.json" ]; then
    say "no machine.json yet: the prop environment waits for the move"
    return
  fi
  UV_PROJECT_ENVIRONMENT="$props/env" "$BIN/uv" sync -q --frozen --no-dev --project "$repo"
  say "prop environment synced at $props/env from uv.lock"
}

# A unit's text for user score: the deploy templates' slots filled in; the units' own paths are systemd's %h.
render_unit() {
  sed -e "s|$REPO_SLOT|%h/projects/score|g" -e "s|$ENV_SLOT|%h/.config/score/dashboard.env|g" \
    -e "s|$SECRET_SLOT|score-cockpit-sync-token|g" "$1"
}

install_units() {
  local repo="$1" folder="$HOME/.config/systemd/user" unit name enabled=()
  mkdir -p "$folder"
  for unit in "$repo"/tools/cloud/conductor/units/*.service "$repo"/tools/cloud/conductor/units/*.timer \
    "$repo"/tools/cloud/conductor/units/*.slice; do
    [ -e "$unit" ] || continue
    name="$(basename "$unit")"
    render_unit "$unit" > "$folder/$name"
    if grep -q '^\[Install\]' "$unit"; then enabled+=("$name"); fi
  done
  # score-resume.service is every machine's template; on the conductor it waits for the move (machine.json), since
  # a resume writes runs/ and the move restores only into an empty home.
  mkdir -p "$folder/score-resume.service.d"
  printf '[Unit]\nConditionPathExists=%%h/.farm-factory-props/machine.json\n' > "$folder/score-resume.service.d/conductor.conf"
  systemctl --user daemon-reload
  if [ "${#enabled[@]}" -gt 0 ]; then systemctl --user enable "${enabled[@]}"; fi
  for name in "${enabled[@]}"; do
    case "$name" in *.timer) systemctl --user start "$name" ;; esac
  done
  say "units installed and enabled: ${enabled[*]}"
}

clone_library() {
  local lib="$HOME/projects/score_lib" key="${XDG_RUNTIME_DIR:?}/score/score-lib-deploy-key" known="$HOME/.ssh/known_hosts_github"
  local ssh_command
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"
  printf '%s\n' "$GITHUB_KEYS" > "$known"
  ssh_command="ssh -i $key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$known"
  if [ ! -d "$lib/.git" ]; then
    GIT_SSH_COMMAND="$ssh_command" git clone -q "$LIB_URL" "$lib"
    say "score_lib cloned to $lib"
  fi
  git -C "$lib" config core.sshCommand "$ssh_command"
  # library_files.py runs the library's own command, $lib/.venv/bin/score-lib; the cockpit's lock and withdraw run
  # score-lib from the PATH, whose ~/.local/bin (machine.py env_text) holds this link.
  (cd "$lib" && "$BIN/uv" sync -q --frozen)
  mkdir -p "$HOME/.local/bin"
  ln -sfn "$lib/.venv/bin/score-lib" "$HOME/.local/bin/score-lib"
  say "score-lib at $HOME/.local/bin/score-lib"
}

user_part() {
  local repo="$HOME/projects/score"
  checkout "$repo"
  props_env "$repo"
  chromium_browser
  gltfpack_cache
  install_units "$repo"
  if [ ! -f "$HOME/.config/scw/config.yaml" ]; then
    say "no ~/.config/scw/config.yaml yet: machine.py up pipes it, then runs this part again"
    return
  fi
  systemctl --user start score-secrets.service
  clone_library
  say "secrets on tmpfs, score_lib ready"
}

case "${1:-}" in
  system) system_part ;;
  user) user_part ;;
  env) props_env "$HOME/projects/score" ;;
  *) echo "usage: boot.sh system|user|env" >&2; exit 2 ;;
esac
