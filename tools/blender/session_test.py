"""Check the Blender wrapper's guards without starting a Blender (#128).

Above all: no Blender window on the owner's screen. A display under :99 (WSLg's :0 among them) is
refused by session.py and by launch.sh, the environment never carries the owner's DISPLAY or
Wayland, and a Blender connected to WSLg's screen is recognised. Also the memory floor, the
display picker, the add-on's command framing and the artifact check. smoke.py starts a real one.

Run: python3 tools/blender/session_test.py
"""
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import session  # noqa: E402
import smoke  # noqa: E402

_failures = []


def check(what, held):
    print(("PASS  " if held else "FAIL  ") + what)
    if not held:
        _failures.append(what)


def refused(call):
    try:
        call()
    except SystemExit:
        return True
    return False


def check_owner_screen_refused():
    check("display :0 refused", refused(lambda: session.refuse_owner_screen(0)))
    check("display :98 refused", refused(lambda: session.refuse_owner_screen(98)))
    check("display :99 allowed", session.refuse_owner_screen(99) == 99)
    owner = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "PATH": "/usr/bin"}
    environment = session.launch_environment(owner, "5.0.1")
    check("the owner's DISPLAY and Wayland are not passed on",
          "DISPLAY" not in environment and "WAYLAND_DISPLAY" not in environment)
    check("launch command refuses :0",
          refused(lambda: session.launch_command("/bin/true", 0, [])))
    command = session.launch_command("/bin/true", 99, ["-b"])
    check("launch command goes through launch.sh on :99",
          command[command.index("bash") + 1].endswith("launch.sh") and "99" in command)


def check_launch_script_refuses_owner_screen():
    for display in ("0", "1", "98", ":0", "x"):
        result = subprocess.run(["bash", str(HERE / "launch.sh"), display, "true"],
                                capture_output=True, text=True)
        check(f"launch.sh refuses display {display!r}", result.returncode == 2)


def check_owner_screen_seen():
    listing = "\n".join([
        "u_str ESTAB 0 0 * 100 * 200 users:((\"blender\",pid=42,fd=5))",
        "u_str ESTAB 0 0 @/tmp/.X11-unix/X0 200 * 100",
        "u_str ESTAB 0 0 * 101 * 201 users:((\"blender\",pid=42,fd=6))",
        "u_str ESTAB 0 0 @/tmp/.X11-unix/X99 201 * 101",
        "u_str ESTAB 0 0 * 102 * 202 users:((\"blender\",pid=42,fd=7))",
        "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-0 202 * 102",
        "u_str ESTAB 0 0 * 103 * 203 users:((\"other\",pid=7,fd=3))",
        "u_str ESTAB 0 0 /mnt/wslg/runtime-dir/wayland-0 203 * 103",
    ])
    peers = session.socket_peers([42], listing)
    check("Blender's peers read from ss", peers == {"@/tmp/.X11-unix/X0", "@/tmp/.X11-unix/X99",
                                                    "/mnt/wslg/runtime-dir/wayland-0"})
    check("X0 and WSLg's Wayland flagged, the private :99 not",
          session.owner_screen_paths(peers) == ["/mnt/wslg/runtime-dir/wayland-0", "@/tmp/.X11-unix/X0"])
    check("a private screen alone is clean", session.owner_screen_paths({"@/tmp/.X11-unix/X99"}) == [])


def check_display_picker():
    with tempfile.TemporaryDirectory() as locks:
        listing = "u_str LISTEN 0 0 @/tmp/.X11-unix/X0 1 * 0\nu_str LISTEN 0 0 @/tmp/.X11-unix/X99 2 * 0\n"
        pathlib.Path(locks, ".X100-lock").write_text("")
        check("picks the first free private display", session.private_display(listing, pathlib.Path(locks)) == 101)


def check_memory_floor():
    check("too little memory refused", refused(lambda: session.refuse_low_memory(5.0, 10.0)))
    check("enough memory allowed", not refused(lambda: session.refuse_low_memory(20.0, 10.0)))


def fake_addon(listener):
    """Answer one command in two pieces, as a slow add-on might."""
    connection, _ = listener.accept()
    command = json.loads(connection.recv(65536).decode())
    answer = json.dumps({"status": "success", "result": {"result": f"ran {command['type']}"}}).encode()
    connection.sendall(answer[:10])
    connection.sendall(answer[10:])
    connection.close()


def check_command_framing():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    threading.Thread(target=fake_addon, args=(listener,), daemon=True).start()
    check("a split answer is read whole", session.execute("print(1)", port=port) == "ran execute_code")
    listener.close()


def check_artifact_check():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        check("an empty folder is three problems", len(smoke.check_artifacts(folder)) == 3)
        (folder / "scene.blend").write_bytes(b"BLENDER-v500" + bytes(20))
        (folder / "scene.glb").write_bytes(b"glTF" + (2).to_bytes(4, "little") + (12).to_bytes(4, "little"))
        (folder / "final.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(8) + (512).to_bytes(4, "big") + (288).to_bytes(4, "big"))
        check("a whole folder passes", smoke.check_artifacts(folder) == [])
        (folder / "scene.glb").write_bytes(b"glTF" + (2).to_bytes(4, "little") + (99).to_bytes(4, "little"))
        check("a cut-short glb is caught", smoke.check_artifacts(folder) == ["scene.glb is not a well-formed glb"])


check_owner_screen_refused()
check_launch_script_refuses_owner_screen()
check_owner_screen_seen()
check_display_picker()
check_memory_floor()
check_command_framing()
check_artifact_check()
sys.exit(1 if _failures else 0)
