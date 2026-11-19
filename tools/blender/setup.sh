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
#   libs/            the X/GL libraries Blender links that this box lacks (render.py's default LD_LIBRARY_PATH)
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

# The X and GL libraries a Blender links that this box lacks (a WSL Ubuntu has no libSM or libICE), fetched from the
# distribution's own packages (apt-get download, no root) into libs/, which score/stages/place_build/render.py puts
# on LD_LIBRARY_PATH by default. Only the libraries ldd names missing are copied, so the box's own stay in use.
LIB_PACKAGES=(libsm6 libice6 libuuid1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxext6 libx11-6 libxcb1 libxau6
  libxdmcp6 libbsd0 libmd0 libxkbcommon0 libgl1 libglx0 libglvnd0 libegl1)

missing_libraries() {
  LD_LIBRARY_PATH="$HOME_DIR/libs" ldd "$1" | awk '/not found/ {print $1}' | sort -u
}

fetch_libraries() {
  local blender="$HOME_DIR/blender-${BLENDERS[-1]}/blender" missing debs package name found
  mkdir -p "$HOME_DIR/libs"
  missing="$(missing_libraries "$blender")"
  if [[ -z "$missing" ]]; then
    echo "libraries: none missing"
    return
  fi
  debs="$(mktemp -d)"
  for package in "${LIB_PACKAGES[@]}"; do
    (cd "$debs" && apt-get download -q "$package" >/dev/null 2>&1) || echo "libraries: no package $package here"
  done
  for deb in "$debs"/*.deb; do dpkg -x "$deb" "$debs/tree"; done
  while [[ -n "$missing" ]]; do
    found=0
    for name in $missing; do
      if [[ -e "$debs/tree/usr/lib/x86_64-linux-gnu/$name" ]]; then
        cp -L "$debs/tree/usr/lib/x86_64-linux-gnu/$name" "$HOME_DIR/libs/$name"
        echo "libraries: $name"
        found=1
      fi
    done
    missing="$(missing_libraries "$blender")"
    [[ "$found" == 1 ]] || break
  done
  rm -rf "$debs"
  if [[ -n "$missing" ]]; then
    echo "libraries: still missing $(echo $missing): install them with apt, or copy them into $HOME_DIR/libs" >&2
    exit 1
  fi
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
fetch_libraries
fetch_addon
build_server
