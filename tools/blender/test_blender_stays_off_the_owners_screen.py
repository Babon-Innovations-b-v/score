"""No Blender window ever reaches the owner's screen (#128; a Blender window reached it on 2026-10-05), and the
wrapper's other guards hold, all without starting a Blender.

One test drives `session.start`, the real way a Blender starts, through a few start rows in a faked machine (its
free memory, its `ss` listings, its X lock files, a Blender that never runs and a slow add-on answering on a local
port): the memory floor refuses a start, the private display picker skips taken and locked displays, Blender's
environment never carries the owner's DISPLAY or Wayland, a Blender found connected to WSLg's X0 or Wayland is
stopped, and the add-on's answer split over reads is read whole. Beside it, every display under :99 (WSLg's :0
among them) is refused by session.py and by launch.sh, and smoke.py's artifact check reads a folder table.
smoke.py starts a real Blender; this file never does.

The break that turns the test red (applied once each, seen red, reverted):

- refuse_owner_screen's `number < FIRST_PRIVATE_DISPLAY` made `number < 0`: the refused-display rows pass.
- launch.sh's `((display_number < 99))` made `((display_number < 0))`: the refused-display rows reach Xvfb.
- owner_screen_paths drops its `"wayland" in path or`: the leak row's stop names X0 alone.
- private_display ignores the lock files: the leak row starts on :100, which is locked.
- refuse_low_memory's `<` made `>`: the low-memory row starts and the ready rows are refused.
- send stops at a partial answer (its `continue` made `break`): the ready row's ping finds the connection closed.
- glb_ok drops its `length == path.stat().st_size`: the cut-short glb row passes.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/blender/test_blender_stays_off_the_owners_screen.py
"""
import json
import os
import pathlib
import re
import socketserver
import subprocess
import sys
import threading
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import session  # noqa: E402
import smoke  # noqa: E402

BLENDER_PID = 42
FLOOR = session.MIN_FREE_GB

# Blender (pid 42) connects to X0 (the owner's), the private X99 and WSLg's Wayland; pid 7's Wayland is not Blender's.
ON_THE_OWNERS_SCREEN = "\n".join([
    "u_str ESTAB 0 0 * 100 * 200 users:((\"blender\",pid=42,fd=5))",
    "u_str ESTAB 0 0 @/tmp/.X11-unix/X0 200 * 100",
    "u_str ESTAB 0 0 * 101 * 201 users:((\"blender\",pid=42,fd=6))",
    "u_str ESTAB 0 0 @/tmp/.X11-unix/X99 201 * 101",
    "u_str ESTAB 0 0 * 102 * 202 users:((\"blender\",pid=42,fd=7))",
    "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-0 202 * 102",
    "u_str ESTAB 0 0 * 103 * 203 users:((\"other\",pid=7,fd=3))",
    "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-1 203 * 103",
])
# Blender connects only to private displays; pid 7 still holds WSLg's Wayland.
ON_PRIVATE_SCREENS_ONLY = "\n".join([
    "u_str ESTAB 0 0 * 101 * 201 users:((\"blender\",pid=42,fd=6))",
    "u_str ESTAB 0 0 @/tmp/.X11-unix/X99 201 * 101",
    "u_str ESTAB 0 0 * 104 * 204 users:((\"blender\",pid=42,fd=8))",
    "u_str ESTAB 0 0 @/tmp/.X11-unix/X100 204 * 104",
    "u_str ESTAB 0 0 * 103 * 203 users:((\"other\",pid=7,fd=3))",
    "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-1 203 * 103",
])
X0_AND_X99_LISTEN = "u_str LISTEN 0 0 @/tmp/.X11-unix/X0 1 * 0\nu_str LISTEN 0 0 @/tmp/.X11-unix/X99 2 * 0\n"

# (id, free GB, `ss -xlH`, locked displays, `ss -xpH`, the display Blender gets, how the start ends)
START_ROWS = [
    ("too little memory", FLOOR - 0.1, "", [], ON_PRIVATE_SCREENS_ONLY, None, "GB free"),
    ("blender reached X0 and Wayland", FLOOR, X0_AND_X99_LISTEN, [100], ON_THE_OWNERS_SCREEN, 101,
     "owner's screen (/mnt/wslg/runtime-dir/wayland-0, @/tmp/.X11-unix/X0); stopped it"),
    ("exactly the floor, nothing on any display", FLOOR, "", [], ON_PRIVATE_SCREENS_ONLY, 99, "ready"),
    ("plenty free, :99 taken", FLOOR + 2, X0_AND_X99_LISTEN, [], ON_PRIVATE_SCREENS_ONLY, 100, "ready"),
]

# (display, the same display as launch.sh's argument; None: the text "99" is no display number to Python only)
REFUSED_DISPLAYS = [(0, "0"), (1, "1"), (98, "98"), (":0", ":0"), ("x", "x"), ("99", None)]

GLB_HEAD = b"glTF" + (2).to_bytes(4, "little")
WHOLE = {
    "scene.blend": b"BLENDER-v500" + bytes(20),
    "scene.glb": GLB_HEAD + (12).to_bytes(4, "little"),
    "final.png": b"\x89PNG\r\n\x1a\n" + bytes(8) + (512).to_bytes(4, "big") + (288).to_bytes(4, "big"),
}
# (id, the folder's files, the artifact check's problems)
ARTIFACT_ROWS = [
    ("empty folder", {}, ["scene.blend missing", "scene.glb missing", "final.png missing"]),
    ("whole folder", WHOLE, []),
    ("cut-short glb", {**WHOLE, "scene.glb": GLB_HEAD + (99).to_bytes(4, "little")},
     ["scene.glb is not a well-formed glb"]),
]


class SlowAddon(socketserver.BaseRequestHandler):
    """A slow add-on: each command answered in two writes."""

    def handle(self):
        command = json.loads(self.request.recv(65536).decode())
        answer = json.dumps({"status": "success", "result": {"result": f"ran {command['type']}"}}).encode()
        self.request.sendall(answer[:10])
        self.request.sendall(answer[10:])


class NeverRunningBlender:
    """What start's Popen gives back: a process that stays up and never draws."""
    pid = BLENDER_PID

    def __init__(self, launches, command, env, **_):
        launches.append((command, env))

    def poll(self):
        return None


def start_world(monkeypatch, folder, row, addon_port):
    """session.start's machine for one start row; the launches it makes and the stops it calls."""
    _, free, listening, locked, peers, _, _ = row
    folder.mkdir()
    for number in locked:
        (folder / f".X{number}-lock").write_text("")
    launches, stops = [], []
    listings = {"-xlH": listening, "-xpH": peers}
    machine = types.SimpleNamespace(
        run=lambda argv, **_: types.SimpleNamespace(stdout=listings[argv[1]]),
        Popen=lambda command, env, **rest: NeverRunningBlender(launches, command, env, **rest),
        DEVNULL=subprocess.DEVNULL, STDOUT=subprocess.STDOUT)
    monkeypatch.setattr(session, "subprocess", machine)
    monkeypatch.setattr(session, "free_gb", lambda: free)
    monkeypatch.setattr(session, "blender_path", lambda version: pathlib.Path("/opt/blender") / version)
    monkeypatch.setattr(session, "port_open", lambda port=None: bool(launches))  # the add-on answers once launched
    monkeypatch.setattr(session, "session_members", lambda group: [BLENDER_PID])
    monkeypatch.setattr(session, "stop", lambda: stops.append(True))
    monkeypatch.setattr(session, "STATE", folder / "state.json")
    monkeypatch.setattr(session, "LOG", folder / "blender.log")
    monkeypatch.setattr(session.private_display, "__defaults__", (None, folder))
    monkeypatch.setattr(session.send, "__defaults__", (addon_port,))
    return launches, stops


def test_blender_stays_off_the_owners_screen(tmp_path, monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    with socketserver.TCPServer(("127.0.0.1", 0), SlowAddon) as addon:
        port = addon.server_address[1]
        threading.Thread(target=addon.serve_forever, daemon=True).start()
        try:
            for row in START_ROWS:
                name, _, _, _, _, display, ending = row
                with monkeypatch.context() as patch:
                    launches, stops = start_world(patch, tmp_path / name.replace(" ", "-"), row, port)
                    if ending == "ready":
                        session.start("5.0.1", "test", 0)
                        assert session.execute("print(1)", port=port) == "ran execute_code", name
                        assert not stops, name
                    else:
                        with pytest.raises(SystemExit, match=re.escape(ending)):
                            session.start("5.0.1", "test", 0)
                        assert bool(stops) == (display is not None), name
                if display is None:
                    assert launches == [], name
                    continue
                [(command, environment)] = launches
                launch = command.index("bash")
                assert command[launch + 1:launch + 4] == [str(HERE / "launch.sh"), str(display), "/opt/blender/5.0.1"], name
                assert "DISPLAY" not in environment and "WAYLAND_DISPLAY" not in environment, name
                assert environment["PATH"] == os.environ["PATH"], name
                assert os.environ["DISPLAY"] == ":0", name  # the caller's own environment left whole
        finally:
            addon.shutdown()

    for display, shell_display in REFUSED_DISPLAYS:
        with pytest.raises(SystemExit):
            session.refuse_owner_screen(display)
        with pytest.raises(SystemExit):
            session.launch_command("/bin/true", display, [])
        if shell_display is not None:
            done = subprocess.run(["bash", str(HERE / "launch.sh"), shell_display, "true"], capture_output=True,
                                  text=True)
            assert done.returncode == 2 and "refusing display" in done.stderr, display

    for name, files, problems in ARTIFACT_ROWS:
        folder = tmp_path / "artifacts" / name.replace(" ", "-")
        folder.mkdir(parents=True)
        for file_name, content in files.items():
            (folder / file_name).write_bytes(content)
        assert smoke.check_artifacts(folder) == problems, name
