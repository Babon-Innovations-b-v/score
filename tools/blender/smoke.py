"""The Blender route end to end: start Blender, build a cube scene through the MCP add-on, write
LEGO-Anything's three artifacts, check them, stop Blender (#128). Not in the gate: it starts a
Blender, which takes the machine's gate lock and about a minute.

    python3 tools/blender/smoke.py [--version 5.0.1|5.2.2] [--out <folder>]

Exit 0 with a line per artifact when every file is there and well formed.
"""
import argparse
import pathlib
import struct
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import session  # noqa: E402


def blend_ok(path):
    return path.read_bytes()[:7] == b"BLENDER"


def glb_ok(path):
    """A binary glTF 2 whose header length matches the file."""
    head = path.read_bytes()[:12]
    if len(head) < 12:
        return False
    magic, version, length = struct.unpack("<4sII", head)
    return magic == b"glTF" and version == 2 and length == path.stat().st_size


def png_size(path):
    """(width, height) of a PNG, or None when the file is not one."""
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def check_artifacts(folder):
    """Problems with a LEGO artifact folder, one line each; empty when it is whole."""
    problems = []
    checks = {"scene.blend": blend_ok, "scene.glb": glb_ok, "final.png": png_size}
    for name, check in checks.items():
        path = folder / name
        if not path.exists():
            problems.append(f"{name} missing")
        elif not check(path):
            problems.append(f"{name} is not a well-formed {name.split('.')[1]}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default=session.DEFAULT_VERSION, choices=session.VERSIONS)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("/tmp/farm-factory-blender-smoke"))
    arguments = parser.parse_args(argv)
    folder = arguments.out.expanduser().resolve() / arguments.version
    began = time.time()
    session.start(arguments.version, "smoke test", wait_seconds=600)
    started = session.read_state()["session"]
    try:
        print(session.execute(session.inside_call("smoke_scene", "build()")).strip())
        print(session.execute(session.inside_call("artifacts", f"write({str(folder)!r})")).strip())
    finally:
        session.stop()
    problems = check_artifacts(folder)
    if session.session_members(started):
        problems.append(f"processes left after stop: {session.session_members(started)}")
    for problem in problems:
        print(f"FAIL  {problem}")
    if problems:
        return 1
    print(f"PASS  Blender {arguments.version}: scene.blend, scene.glb, final.png "
          f"{png_size(folder / 'final.png')} in {folder}, {time.time() - began:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
