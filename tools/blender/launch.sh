#!/usr/bin/env bash
# The one way a Blender with a window starts: on a private Xvfb screen, never the owner's.
#
#   bash tools/blender/launch.sh <display number, 99 or more> <blender> [blender arguments]
#
# Called by session.py, which also holds the Blender lock around it. WSLg shows every Linux window
# on the Windows desktop through DISPLAY=:0 or the wayland-0 socket (a Blender window reached the
# owner's screen on 2026-10-05), so this starts its own Xvfb on :N, points DISPLAY there, makes
# sure Blender cannot find any Wayland socket, and stops the Xvfb when Blender ends.
set -euo pipefail

display_number="${1:?display number}"
shift
if ! [[ "$display_number" =~ ^[0-9]+$ ]] || ((display_number < 99)); then
  echo "launch.sh: refusing display :$display_number; only a private Xvfb display (:99 up)" >&2
  exit 2
fi

runtime="/tmp/farm-factory-blender-runtime-$(id -u)"
mkdir -p "$runtime"
chmod 700 "$runtime"

Xvfb ":$display_number" -screen 0 1920x1080x24 -nolisten tcp -noreset &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT

# WSLg mounts /tmp/.X11-unix read-only, so Xvfb listens only on its abstract socket; wait for that.
listening() { ss -xlH | grep -q "@/tmp/.X11-unix/X$display_number "; }
for _ in $(seq 1 50); do
  listening && break
  sleep 0.1
done
listening || { echo "launch.sh: Xvfb :$display_number did not start" >&2; exit 3; }

export DISPLAY=":$display_number"
# A name with no socket behind it, in a runtime folder with nothing in it: no Wayland to fall back to.
export WAYLAND_DISPLAY="farm-factory-no-wayland"
export XDG_RUNTIME_DIR="$runtime"
"$@"
