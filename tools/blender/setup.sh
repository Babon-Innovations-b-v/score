#!/usr/bin/env bash
# Build the Blender runtime coding agents drive, once per box (#128). Nothing lands in the repo.
#
#   bash tools/blender/setup.sh
#
# Under ~/.farm-factory-props/blender-mcp (PROPS_HOME moves it):
#   blender-5.0.1/   the version LEGO-Anything's scorer runs (its artifacts must open there)
#   blender-5.2.2/   the latest stable (LTS) on 2026-10-05
#   src/             ahujasid/mcp-for-blender (MIT; the repo LEGO-Anything cites as blender-mcp)
#   env/             its MCP server, the `blender` entry in .mcp.json
#   user/            the Blender user folder the add-on is installed into, apart from any other
# Each Blender is the official build, checked against blender.org's sha256 list. The versions and
# the add-on's commit are pinned here, so a second box gets the same runtime.
set -euo pipefail

HOME_DIR="${PROPS_HOME:-$HOME/.farm-factory-props}/blender-mcp"
ADDON_COMMIT=570ae72ee462f22700dd5e7a6bf11881a216291a
BLENDERS=("5.0.1" "5.2.2")

mkdir -p "$HOME_DIR"

fetch_blender() {
  local version="$1" series tarball
  series="${version%.*}"
  tarball="blender-$version-linux-x64.tar.xz"
  if [[ -x "$HOME_DIR/blender-$version/blender" ]]; then
    echo "Blender $version: already there"
    return
  fi
  echo "Blender $version: downloading"
  curl -fsSL -o "$HOME_DIR/$tarball" "https://download.blender.org/release/Blender$series/$tarball"
  curl -fsSL "https://download.blender.org/release/Blender$series/blender-$version.sha256" \
    | grep " $tarball\$" > "$HOME_DIR/$tarball.sha256"
  (cd "$HOME_DIR" && sha256sum -c "$tarball.sha256")
  tar xJf "$HOME_DIR/$tarball" -C "$HOME_DIR"
  mv "$HOME_DIR/blender-$version-linux-x64" "$HOME_DIR/blender-$version"
  rm "$HOME_DIR/$tarball" "$HOME_DIR/$tarball.sha256"
}

fetch_addon() {
  if [[ -f "$HOME_DIR/src/.commit" && "$(cat "$HOME_DIR/src/.commit")" == "$ADDON_COMMIT" ]]; then
    echo "add-on: already at $ADDON_COMMIT"
    return
  fi
  echo "add-on: downloading $ADDON_COMMIT"
  rm -rf "$HOME_DIR/src" "$HOME_DIR/mcp-for-blender-$ADDON_COMMIT"
  curl -fsSL "https://codeload.github.com/ahujasid/mcp-for-blender/tar.gz/$ADDON_COMMIT" \
    | tar xz -C "$HOME_DIR"
  mv "$HOME_DIR/mcp-for-blender-$ADDON_COMMIT" "$HOME_DIR/src"
  echo "$ADDON_COMMIT" > "$HOME_DIR/src/.commit"
}

build_server() {
  if [[ ! -x "$HOME_DIR/env/bin/python" ]]; then
    uv venv --quiet --python 3.12 "$HOME_DIR/env"
  fi
  uv pip install --quiet --python "$HOME_DIR/env/bin/python" "$HOME_DIR/src"
  echo "MCP server: $HOME_DIR/env/bin/mcp-for-blender"
}

for version in "${BLENDERS[@]}"; do
  fetch_blender "$version"
done
fetch_addon
build_server
