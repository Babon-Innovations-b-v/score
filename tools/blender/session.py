"""Start, drive and stop the one Blender coding agents build scenes in (#128).

    python3 tools/blender/session.py start [--version 5.0.1|5.2.2] [--who "<session>"]
    python3 tools/blender/session.py status
    python3 tools/blender/session.py run <script.py>          # run a file inside the running Blender
    python3 tools/blender/session.py artifacts <folder>      # scene.blend, scene.glb, final.png
    python3 tools/blender/session.py stop
    python3 tools/blender/session.py batch <script.py> [-- args]  # a `blender -b` job, no window

No Blender window ever reaches the owner's screen (one did on 2026-10-05: WSLg shows every Linux
window on the Windows desktop). Every Blender starts through launch.sh on a private Xvfb display
(:99 up), drawing in software on the processor; the owner's :0 is refused, and a started Blender
found connected to WSLg's screen anyway is stopped at once. A job that needs no window runs with
`-b` (`batch`). The MCP add-on needs one: it serves agents from Blender's interface timers, which a
`-b` Blender never runs, so `start` gives it the Xvfb screen. The add-on listens on
127.0.0.1:PORT; the `blender` MCP server in .mcp.json and `run` here both talk to it.

One heavy local job at a time on the machine: the launch holds `flock` on LOCK, the test gate's
machine-wide lock (tools/test/lock/), for Blender's whole life, so a Blender, a test gate and a
game shot never run at once (WSL ran out of memory twice on 2026-10-05 with them side by side),
and it is let go however Blender ends. Stop a started Blender before running the gate: the gate
waits for it. Blender starts only with MIN_FREE_GB of memory free, and a watchdog stops it after
MAX_HOURS. `stop` stops only the Blender this file started, by the process
group it recorded.
"""
import argparse
import json
import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
INSIDE = HERE / "inside"
RUNTIME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "blender-mcp"
VERSIONS = ("5.0.1", "5.2.2")
# LEGO-Anything's scorer runs Blender 5.0.1, and a .blend saved by a newer Blender is not promised
# to open in an older one, so the benchmark's version is the default; 5.2.2 is the latest stable.
DEFAULT_VERSION = "5.0.1"
# Not the add-on's 9876, which a Blender on the Windows side may hold through WSL's localhost.
PORT = int(os.environ.get("FARM_BLENDER_PORT", "9877"))
# The test gate's lock, the one every heavy local job takes; GATE_LOCK moves it, as in lock.sh.
LOCK = pathlib.Path(os.environ.get("GATE_LOCK", "/tmp/farm-factory-gate.lock"))
# Written into LOCK once it is held, the line a waiting gate prints, as lock.sh's take_gate_lock does.
HOLDER_LINE = 'printf "%s in %s (tools/blender)\\n" "$$" "' + str(HERE.parents[1]) + '" >"$0"; exec "$@"'
STATE = pathlib.Path(os.environ.get("FARM_BLENDER_STATE", "/tmp/farm-factory-blender.json"))
LOG = pathlib.Path(os.environ.get("FARM_BLENDER_LOG", "/tmp/farm-factory-blender.log"))
# 16 GB kept spare for the rest of the machine, as the test gate keeps, plus what one
# software-drawn Blender takes.
MIN_FREE_GB = float(os.environ.get("FARM_MIN_FREE_GB", "18"))
MAX_HOURS = float(os.environ.get("FARM_BLENDER_MAX_HOURS", "3"))
FIRST_PRIVATE_DISPLAY = 99
START_SECONDS = 90
COMMAND_SECONDS = 600


def blender_path(version):
    if version not in VERSIONS:
        raise SystemExit(f"Blender {version} is not set up; pick one of {', '.join(VERSIONS)}")
    path = RUNTIME / f"blender-{version}" / "blender"
    if not path.exists():
        raise SystemExit(f"{path} is missing; run: bash tools/blender/setup.sh")
    return path


def free_gb(meminfo="/proc/meminfo"):
    """MemAvailable in GB."""
    for line in pathlib.Path(meminfo).read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    raise RuntimeError(f"no MemAvailable in {meminfo}")


def refuse_low_memory(available_gb, floor_gb=MIN_FREE_GB):
    """Stop here when the machine has less than the floor free."""
    if available_gb < floor_gb:
        raise SystemExit(
            f"only {available_gb:.1f} GB free, Blender needs {floor_gb:.0f} GB free to start "
            "(16 GB kept spare); wait for another run to finish, or set FARM_MIN_FREE_GB")


def refuse_owner_screen(number):
    """A display number Blender may open a window on: a private Xvfb one, :99 or more."""
    if not isinstance(number, int) or number < FIRST_PRIVATE_DISPLAY:
        raise SystemExit(f"refusing display :{number}; Blender windows go only on a private "
                         f"Xvfb display (:{FIRST_PRIVATE_DISPLAY} up), never the owner's screen")
    return number


def private_display(listening=None, locks=pathlib.Path("/tmp")):
    """The first free X display from :99 up. WSLg's /tmp/.X11-unix is read-only, so an Xvfb here
    is seen by its abstract socket (`ss -xlH`) and its lock file."""
    if listening is None:
        listening = subprocess.run(["ss", "-xlH"], capture_output=True, text=True, check=True).stdout
    taken = {int(number) for number in re.findall(r"/tmp/\.X11-unix/X(\d+)\s", listening + " ")}
    number = FIRST_PRIVATE_DISPLAY
    while number in taken or (locks / f".X{number}-lock").exists():
        number += 1
    return refuse_owner_screen(number)


def launch_environment(base, version):
    """What Blender starts with besides its screen, which launch.sh sets: software drawing, its
    own user folder, no telemetry, and none of the owner's screen."""
    environment = dict(base)
    environment.pop("WAYLAND_DISPLAY", None)
    environment.pop("DISPLAY", None)
    environment["LIBGL_ALWAYS_SOFTWARE"] = "1"
    environment["GALLIUM_DRIVER"] = "llvmpipe"
    environment["DISABLE_TELEMETRY"] = "true"
    environment["BLENDERMCP_NO_UPDATE_CHECK"] = "1"
    environment["BLENDER_USER_RESOURCES"] = str(RUNTIME / "user" / version)
    environment["FARM_BLENDER_PORT"] = str(PORT)
    environment["FARM_BLENDER_ADDON"] = str(RUNTIME / "src" / "addon.py")
    return environment


def launch_command(blender, display, blender_arguments, wait_seconds=0, lock=LOCK, max_hours=MAX_HOURS):
    """Blender on a private Xvfb display (launch.sh), under the gate lock and the watchdog."""
    return [
        "flock", "-w", str(wait_seconds), str(lock), "sh", "-c", HOLDER_LINE, str(lock),
        "timeout", "--kill-after=30", f"{int(max_hours * 3600)}",
        "bash", str(HERE / "launch.sh"), str(refuse_owner_screen(display)),
        str(blender), *blender_arguments,
    ]


def interface_arguments():
    """Blender with its interface, the MCP add-on started by startup.py."""
    return ["--gpu-backend", "opengl", "-setaudio", "None", "--python", str(INSIDE / "startup.py")]


def socket_peers(member_pids, listing):
    """The socket paths the given processes are connected to, from `ss -xpH` output."""
    pids = {str(pid) for pid in member_pids}
    path_of, wanted = {}, set()
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) < 8:
            continue
        local_path, local_inode, peer_inode = fields[4], fields[5], fields[7]
        path_of[local_inode] = local_path
        if pids & set(re.findall(r"pid=(\d+)", line)):
            wanted.add(peer_inode)
    return {path_of[inode] for inode in wanted if path_of.get(inode, "*") != "*"}


def owner_screen_paths(peers):
    """The peer paths that reach the owner's screen: WSLg's Wayland, or an X display under :99."""
    found = []
    for path in peers:
        plain = path.lstrip("@")
        display = re.search(r"\.X11-unix/X(\d+)$", plain)
        if "wayland" in plain or (display and int(display.group(1)) < FIRST_PRIVATE_DISPLAY):
            found.append(path)
    return sorted(found)


def session_members(session):
    """Every process in the session `start` began; `timeout` moves its child to a group of its own,
    so the process group alone misses Blender and Xvfb."""
    found = []
    for entry in pathlib.Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                gone = (entry / "stat").read_text().rsplit(")", 1)[1].split()[0] == "Z"
                if not gone and os.getsid(int(entry.name)) == session:
                    found.append(int(entry.name))
            except (ProcessLookupError, PermissionError, FileNotFoundError):
                continue
    return found


def refuse_window_on_owner_screen(session):
    """Stop Blender at once if it reached the owner's screen after all."""
    listing = subprocess.run(["ss", "-xpH"], capture_output=True, text=True, check=True).stdout
    leaks = owner_screen_paths(socket_peers(session_members(session), listing))
    if leaks:
        stop()
        raise SystemExit(f"Blender connected to the owner's screen ({', '.join(leaks)}); stopped it")


def read_state(state=STATE):
    try:
        return json.loads(pathlib.Path(state).read_text())
    except FileNotFoundError:
        return None


def alive(session):
    return bool(session_members(session))


def port_open(port=PORT, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        return probe.connect_ex((host, port)) == 0


def send(command, port=PORT, timeout=COMMAND_SECONDS):
    """One command to the add-on, its JSON answer back. The add-on frames by whole JSON objects."""
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.settimeout(timeout)
        connection.sendall(json.dumps(command).encode("utf-8"))
        received = b""
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            received += chunk
            try:
                return json.loads(received.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    raise ConnectionError(f"Blender closed the connection after {len(received)} bytes")


def execute(code, port=PORT):
    """Run Python inside Blender; its printed output back, or SystemExit with Blender's error."""
    answer = send({"type": "execute_code", "params": {"code": code}}, port=port)
    if answer.get("status") != "success":
        raise SystemExit(f"Blender: {answer.get('message', answer)}")
    return answer.get("result", {}).get("result", "")


def inside_call(module, call):
    """Code that imports one of inside/'s modules in Blender and calls it."""
    return (f"import sys, importlib\nsys.path.insert(0, {str(INSIDE)!r})\n"
            f"import {module}\nimportlib.reload({module})\n{module}.{call}\n")


def start(version, who, wait_seconds):
    state = read_state()
    if state and alive(state["session"]):
        raise SystemExit(f"Blender already running for {state['who']} (session "
                         f"{state['group']}, port {state['port']}); use it or stop it first")
    refuse_low_memory(free_gb())
    if port_open():
        raise SystemExit(f"port {PORT} is taken by something else; set FARM_BLENDER_PORT")
    command = launch_command(blender_path(version), private_display(), interface_arguments(), wait_seconds)
    with open(LOG, "w") as log:
        process = subprocess.Popen(
            command, env=launch_environment(os.environ, version), stdout=log,
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True, cwd="/tmp")
    STATE.write_text(json.dumps({"session": process.pid, "port": PORT, "who": who,
                                 "version": version, "log": str(LOG), "started": time.time()}))
    deadline = time.time() + wait_seconds + START_SECONDS
    while time.time() < deadline:
        if process.poll() is not None:
            STATE.unlink(missing_ok=True)
            raise SystemExit(f"Blender ended at start (exit {process.returncode}; "
                             f"exit 1 with no log means a gate, a shot or another Blender holds {LOCK}); see {LOG}")
        refuse_window_on_owner_screen(process.pid)
        if port_open() and send({"type": "ping"}).get("status") == "success":
            print(f"Blender {version} ready on 127.0.0.1:{PORT} (session {process.pid})")
            return
        time.sleep(1)
    stop()
    raise SystemExit(f"Blender did not answer within {START_SECONDS} s; see {LOG}")


def batch(version, script, script_arguments, wait_seconds):
    """A `blender -b` job (no window, no add-on) under the same lock; its exit code back."""
    refuse_low_memory(free_gb())
    blender_arguments = ["-b", "-setaudio", "None", "--python-exit-code", "1", "--python", str(script), "--", *script_arguments]
    command = launch_command(blender_path(version), private_display(), blender_arguments, wait_seconds)
    return subprocess.run(command, env=launch_environment(os.environ, version),
                          stdin=subprocess.DEVNULL, cwd="/tmp").returncode


def signal_session(session, number):
    for pid in session_members(session):
        try:
            os.kill(pid, number)
        except ProcessLookupError:
            continue


def stop():
    state = read_state()
    if not state:
        print("no Blender recorded")
        return
    session = state["session"]
    signal_session(session, signal.SIGTERM)
    for _ in range(20):
        if not session_members(session):
            break
        time.sleep(0.5)
    signal_session(session, signal.SIGKILL)
    STATE.unlink(missing_ok=True)
    print(f"Blender stopped (session {session})")


def status():
    state = read_state()
    if not state or not alive(state["session"]):
        print("no Blender running")
        return
    minutes = (time.time() - state["started"]) / 60
    print(f"Blender {state['version']} for {state['who']}, {minutes:.0f} min, port {state['port']}, "
          f"answers: {port_open(state['port'])}, log {state['log']}")


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("start", "batch"):
        action = actions.add_parser(name)
        action.add_argument("--version", default=DEFAULT_VERSION, choices=VERSIONS)
        action.add_argument("--wait", type=int, default=1800,
                            help="seconds to wait for the gate lock, which a whole gate holds")
    actions.choices["start"].add_argument("--who", default=os.environ.get("USER", "someone"))
    actions.choices["batch"].add_argument("script", type=pathlib.Path)
    actions.choices["batch"].add_argument("script_arguments", nargs="*")
    actions.add_parser("status")
    actions.add_parser("stop")
    actions.add_parser("run").add_argument("script", type=pathlib.Path)
    actions.add_parser("artifacts").add_argument("folder", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse(argv)
    if arguments.action == "start":
        start(arguments.version, arguments.who, arguments.wait)
    elif arguments.action == "batch":
        return batch(arguments.version, arguments.script.resolve(), arguments.script_arguments, arguments.wait)
    elif arguments.action == "stop":
        stop()
    elif arguments.action == "status":
        status()
    elif arguments.action == "run":
        print(execute(arguments.script.read_text()))
    else:
        folder = arguments.folder.expanduser().resolve()
        print(execute(inside_call("artifacts", f"write({str(folder)!r})")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
