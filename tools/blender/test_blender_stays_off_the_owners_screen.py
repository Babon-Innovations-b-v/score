"""No Blender window ever reaches the owner's screen (#128; a Blender window reached it on 2026-10-05), and the
wrapper's other guards hold, all without starting a Blender.

A display under :99 (WSLg's :0 among them) is refused by session.py and by launch.sh, Blender's environment never
carries the owner's DISPLAY or Wayland, and a Blender found connected to WSLg's X0 or Wayland is recognised from `ss`
output. Also the memory floor, the private display picker, the add-on's command framing (an answer split over reads)
and smoke.py's artifact check. smoke.py starts a real Blender; this file never does.

The break that turns each test red (applied once each, seen red, reverted):

- test_only_a_private_display_is_ever_opened: refuse_owner_screen's `number < FIRST_PRIVATE_DISPLAY` made
  `number < 0`.
- test_launch_sh_refuses_the_owners_screen: launch.sh's `((display_number < 99))` made `((display_number < 0))`.
- test_blender_on_the_owners_screen_is_recognised: owner_screen_paths drops its `"wayland" in path or`.
- test_the_display_picker_skips_taken_and_locked_displays: private_display ignores the lock files.
- test_too_little_memory_refuses_a_start: refuse_low_memory's `<` made `>`.
- test_a_split_answer_is_read_whole: send stops at a partial answer (its `continue` made `break`).
- test_the_artifact_check_catches_a_missing_or_cut_short_file: glb_ok drops its `length == path.stat().st_size`.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/blender/test_blender_stays_off_the_owners_screen.py
"""
import json
import pathlib
import socketserver
import subprocess
import sys
import threading

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import session  # noqa: E402
import smoke  # noqa: E402


def test_only_a_private_display_is_ever_opened():
    for display in (0, 1, 98, "99"):
        with pytest.raises(SystemExit):
            session.refuse_owner_screen(display)
        with pytest.raises(SystemExit):
            session.launch_command("/bin/true", display, [])
    assert session.refuse_owner_screen(99) == 99
    command = session.launch_command("/bin/true", 99, ["-b"])
    assert command[command.index("bash") + 1].endswith("launch.sh") and command[command.index("bash") + 2] == "99"
    owner = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "PATH": "/usr/bin"}
    environment = session.launch_environment(owner, "5.0.1")
    assert "DISPLAY" not in environment and "WAYLAND_DISPLAY" not in environment
    assert environment["PATH"] == "/usr/bin" and owner["DISPLAY"] == ":0"  # the caller's own copy left whole


@pytest.mark.parametrize("display", ["0", "1", "98", ":0", "x"])
def test_launch_sh_refuses_the_owners_screen(display):
    done = subprocess.run(["bash", str(HERE / "launch.sh"), display, "true"], capture_output=True, text=True)
    assert done.returncode == 2 and "refusing display" in done.stderr


def test_blender_on_the_owners_screen_is_recognised():
    """Blender (pid 42) holds three sockets: to X0 (the owner's), to the private X99 and to WSLg's Wayland; another
    process's Wayland socket is not Blender's."""
    listing = "\n".join([
        "u_str ESTAB 0 0 * 100 * 200 users:((\"blender\",pid=42,fd=5))",
        "u_str ESTAB 0 0 @/tmp/.X11-unix/X0 200 * 100",
        "u_str ESTAB 0 0 * 101 * 201 users:((\"blender\",pid=42,fd=6))",
        "u_str ESTAB 0 0 @/tmp/.X11-unix/X99 201 * 101",
        "u_str ESTAB 0 0 * 102 * 202 users:((\"blender\",pid=42,fd=7))",
        "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-0 202 * 102",
        "u_str ESTAB 0 0 * 103 * 203 users:((\"other\",pid=7,fd=3))",
        "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-1 203 * 103",
    ])
    peers = session.socket_peers([42], listing)
    assert peers == {"@/tmp/.X11-unix/X0", "@/tmp/.X11-unix/X99", "/mnt/wslg/runtime-dir/wayland-0"}
    assert session.owner_screen_paths(peers) == ["/mnt/wslg/runtime-dir/wayland-0", "@/tmp/.X11-unix/X0"]
    assert session.owner_screen_paths({"@/tmp/.X11-unix/X99", "@/tmp/.X11-unix/X100"}) == []


def test_the_display_picker_skips_taken_and_locked_displays(tmp_path):
    listening = "u_str LISTEN 0 0 @/tmp/.X11-unix/X0 1 * 0\nu_str LISTEN 0 0 @/tmp/.X11-unix/X99 2 * 0\n"
    (tmp_path / ".X100-lock").write_text("")
    assert session.private_display(listening, tmp_path) == 101  # :99 listens, :100 is locked
    assert session.private_display("", tmp_path / "none") == 99


def test_too_little_memory_refuses_a_start():
    with pytest.raises(SystemExit):
        session.refuse_low_memory(5.0, 10.0)
    session.refuse_low_memory(20.0, 10.0)
    session.refuse_low_memory(10.0, 10.0)  # exactly the floor is enough


class SlowAddon(socketserver.BaseRequestHandler):
    """A slow add-on: one command answered in two writes."""

    def handle(self):
        command = json.loads(self.request.recv(65536).decode())
        answer = json.dumps({"status": "success", "result": {"result": f"ran {command['type']}"}}).encode()
        self.request.sendall(answer[:10])
        self.request.sendall(answer[10:])


def test_a_split_answer_is_read_whole():
    with socketserver.TCPServer(("127.0.0.1", 0), SlowAddon) as server:
        threading.Thread(target=server.handle_request, daemon=True).start()
        assert session.execute("print(1)", port=server.server_address[1]) == "ran execute_code"


def test_the_artifact_check_catches_a_missing_or_cut_short_file(tmp_path):
    assert smoke.check_artifacts(tmp_path) == ["scene.blend missing", "scene.glb missing", "final.png missing"]
    (tmp_path / "scene.blend").write_bytes(b"BLENDER-v500" + bytes(20))
    (tmp_path / "scene.glb").write_bytes(b"glTF" + (2).to_bytes(4, "little") + (12).to_bytes(4, "little"))
    (tmp_path / "final.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(8) + (512).to_bytes(4, "big")
                                         + (288).to_bytes(4, "big"))
    assert smoke.check_artifacts(tmp_path) == []
    (tmp_path / "scene.glb").write_bytes(b"glTF" + (2).to_bytes(4, "little") + (99).to_bytes(4, "little"))
    assert smoke.check_artifacts(tmp_path) == ["scene.glb is not a well-formed glb"]
