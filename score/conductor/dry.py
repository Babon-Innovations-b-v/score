"""The conductor's free end-to-end check, in a home of its own, spending nothing.

    python -m score.conductor dry      # one line; the detail in $PROPS_HOME/logs/conductor-dry-<time>.json

`python -m score.conductor dry` starts this module in a fresh temp PROPS_HOME under SCORE_FREE_ONLY=1, as a conductor
(machine.json, and SCORE_CONDUCTOR_SIZE_URL naming a local stand-in for the size function that records each ask),
from a frozen copy of the code. It walks the conductor's operations on a fixture design (a toy environment, `dry`, two
places with a brief each, one free stage), through the real `score` command (`child`: the command with the toy
environment added to its table):

1. plan: `score plan dry` lists both nodes to run and no buy;
2. waiting for size: `score run dry --jobs <cores + 1>` registers as waiting-for-size and the size timer asks the
   stand-in to grow; the grow's power-off is a SIGKILL;
3. resume: `score resume` at another boot id, on the batch size's cores, starts the waiting run from its frozen copy
   (its restart the toy command, not detached), which drives both lines to done;
4. memory guard: a drive under a faked available memory, the floor SCORE_MIN_FREE_GB, holds the second node until the
   first, still short of its stage's peak, has ended;
5. health and logs: written and read back;
6. shrink: the size timer, idle past its time at the batch size, asks the stand-in to shrink;
7. kill switch: stop_all ends a live fake run, releases a fake parked machine and writes the free-only latch.

Every step's result goes to the detail file; the line says how many passed. In an agent's process (the agents' door
runs every command as one) two steps check the refusal instead, as they must: step 2's `score run` is refused (an
agent's run never grows the machine), and the waiting run is then started through size.wait_for_grow itself; step 7's
stop_all is refused, and its stop path runs without the barrier (kill.stop_everything) on the temp home's fake run.
"""
import datetime
import http.server
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback

from score import checks, contracts, conductor, graph
from score.store import PROPS_HOME, running_under_agent

REPO = pathlib.Path(__file__).resolve().parents[2]
WORLD = "dry"
PLACES = ("north", "south")
TOKEN = "dry-size-token"
STEP_SECONDS = 30  # how long a step waits for what it looks for


# --- the fixture: a toy environment of one free stage ---------------------------------------------------------------

def make_brief(inputs, out, seed, params):
    (out / "brief.txt").write_text(inputs["brief"].read_text().upper())


def judge_brief(output, inputs, evidence):
    written = (output / "brief.txt").read_text().strip()
    return checks.Verdict("written", checks.PASS if written else checks.FAIL, "a brief was written" if written
                          else "the brief is empty")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("dry-text", 1, text_faults)
BRIEF = graph.Stage("brief", "place", make_brief, TEXT, (checks.Check("written", judge_brief),),
                    files={"brief": "{data}/{place}/brief.txt"})


def design():
    """The fixture design's folder."""
    return PROPS_HOME / "dry-design"


def dry_world():
    return graph.Environment(WORLD, 1, {"data": design()})


def write_design():
    for place in PLACES:
        (design() / place).mkdir(parents=True, exist_ok=True)
        (design() / place / "brief.txt").write_text(f"the {place} room, one crate")


# --- the stand-in size function ------------------------------------------------------------------------------------

class SizeFunction(http.server.BaseHTTPRequestHandler):
    """Records each ask ({action, token_ok}) in the server's `asks`."""

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        from score.conductor import size
        self.server.asks.append({"action": body.get("action"), "token_ok": self.headers.get(size.HEADER) == TOKEN})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"dry: noted")

    def log_message(self, *arguments):
        pass


def size_function():
    """A local stand-in for the size function, serving in a thread; the server (its `asks`, its url)."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SizeFunction)
    server.asks = []
    server.url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# --- the child: the real `score` command with the toy environment --------------------------------------------------

def child(argv):
    """Run `score <argv>` with the toy environment in its table; `--cores N` first fakes this machine's cores, and the
    size timer is asked in this process instead of through systemd."""
    from score import __main__ as command
    from score import stages
    from score.conductor import size
    if argv[:1] == ["--cores"]:
        cores, argv = int(argv[1]), argv[2:]
        os.cpu_count = lambda: cores
    stages.WORLDS[WORLD] = dry_world
    stages.TABLES[WORLD] = (BRIEF,)
    size.start_size_service = lambda: bool(size.tick(say=lambda line: print(line, flush=True)))
    if argv[:1] == ["wait"]:  # the waiting run itself, past the gate an agent's run is refused at
        size.wait_for_grow([word for word in argv[2:]], int(argv[1]), say=lambda line: print(line, flush=True))
    command.main(argv)


def child_command(*words, cores=None):
    return [sys.executable, "-m", "score.conductor.dry", "child", *(["--cores", str(cores)] if cores else []), *words]


# --- the steps -----------------------------------------------------------------------------------------------------

def waited(condition, seconds=STEP_SECONDS):
    """Whether `condition()` came true within `seconds`."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.2)
    return False


def step_plan(copy, env):
    done = subprocess.run(child_command("plan", WORLD, *places_words(), "--json"), cwd=copy, env=env,
                          capture_output=True, text=True, timeout=120)
    plan = json.loads(done.stdout.strip().splitlines()[-1])
    nodes = sorted(plan["to_run"])
    ok = done.returncode == 0 and nodes == [f"brief@{place}" for place in PLACES] and not plan["buys"]
    return ok, {"to_run": nodes, "buys": plan["buys"], "refusal": plan["refusal"]}


def places_words():
    return [word for place in PLACES for word in ("--place", place)]


def step_wait(copy, env, server, record):
    """`score run` with more jobs than cores waits for size and the grow is asked; in an agent's process the run is
    refused, and the waiting run is started through size.wait_for_grow itself."""
    from score.graph import runs
    jobs = record["batch_cores"]
    argv = ["run", WORLD, *places_words(), "--jobs", str(jobs)]
    refused = None
    if running_under_agent():
        done = subprocess.run(child_command(*argv), cwd=copy, env=env, capture_output=True, text=True, timeout=120)
        refused = (done.returncode, done.stderr.strip()[-400:])
        argv = ["wait", str(jobs), *argv]
    process = subprocess.Popen(child_command(*argv), cwd=copy, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    registered = waited(lambda: bool(runs.waiting()) and any(ask["action"] == "grow" for ask in server.asks))
    process.send_signal(signal.SIGKILL)  # the grow's power-off
    output = process.communicate()[0]
    entries = list(runs.waiting().values())
    ok = (registered and len(entries) == 1 and entries[0]["jobs"] == jobs and server.asks[0]["token_ok"]
          and (refused is None or (refused[0] != 0 and "refused" in refused[1])))
    return ok, {"asks": list(server.asks), "waiting": [entry["id"] for entry in entries], "agents_run": refused,
                "output": output[-1500:]}


def step_resume(copy, record):
    from score.graph import runs
    from score.store import Store
    kept = runs.boot_id, os.cpu_count, runs.restart_command
    said = []
    runs.boot_id = lambda: "dry-boot-after-the-grow"
    os.cpu_count = lambda: record["batch_cores"]
    runs.restart_command = lambda entry: child_command(*entry["argv"], cores=record["batch_cores"])
    try:
        found = runs.resume(False, said.append, swept=())
    finally:
        runs.boot_id, os.cpu_count, runs.restart_command = kept
    states = {entry["id"]: entry["state"] for entry in runs.entries().values()}
    store = Store.default()
    accepted = {place: store.accepted(f"brief@{place}") is not None for place in PLACES}
    ok = found == 1 and sorted(states.values()) == [runs.ENDED, runs.RESUMED] and all(accepted.values())
    return ok, {"said": said, "states": states, "accepted": accepted}


def make_held(inputs, out, seed, params):
    (out / "times.txt").write_text(f"{time.time()}\n")
    time.sleep(1.0)  # the second node waits on this one's end, never on time passing
    (out / "times.txt").write_text(f"{(out / 'times.txt').read_text()}{time.time()}\n")


def judge_held(output, inputs, evidence):
    return checks.Verdict("timed", checks.PASS, "both times written")


def step_memory(home):
    """Two nodes ready at once with room for one (10 GB available, a 4 GB floor and a 4 GB guess for a stage never
    measured): the second starts only once the first ended, however long it ran, and the hold is said (the poll
    shortened for the check). The start is read at the runner's own starts, not inside the node."""
    from score.store import Store
    held = graph.Stage("held", "place", make_held, TEXT, (checks.Check("timed", judge_held),),
                       files={"brief": "{data}/{place}/brief.txt"})
    runner = graph.Runner((held,), dry_world(), Store.in_folder(home / "memory-store"), model_record=lambda kind: {})
    kept, floor, said, started = (graph.AVAILABLE, graph.MEMORY_POLL), os.environ.get(graph.FLOOR_VARIABLE), [], []
    start = runner.start
    runner.start = lambda stage, place, threads: started.append(time.time()) or start(stage, place, threads)
    os.environ[graph.FLOOR_VARIABLE] = "4"
    graph.AVAILABLE, graph.MEMORY_POLL = lambda: 10 * 2**30, 0.2
    try:
        found = runner.drive(list(PLACES), say=said.append, jobs=2, whole=False)
    finally:
        graph.AVAILABLE, graph.MEMORY_POLL = kept
        os.environ.pop(graph.FLOOR_VARIABLE)
        os.environ.update({graph.FLOOR_VARIABLE: floor} if floor is not None else {})
    times = {place: [float(line) for line in (runner.store.checkout(runner.store.accepted(f"held@{place}"))
                                              / "times.txt").read_text().split()] for place in PLACES}
    first, second = sorted(times.values())
    ok = (set(found.values()) == {"made: pass, accepted automatically"} and len(started) == 2
          and started[1] >= first[1]
          and any(line.startswith("memory:") for line in said))
    return ok, {"found": found, "times": times, "started": started, "said": said}


def step_health(home):
    from score.conductor import health, logs
    path = health.write(path=home / "health.json")
    written = json.loads(path.read_text())
    tails = logs.tails(10)
    (home / "tails.json").write_text(json.dumps(tails, indent=1))
    ok = written["machine"] == WORLD and written["cores"] >= 1 and set(written["units"]) == set(health.UNITS)
    return ok, {"health": written, "tails": sorted(tails)}


def step_shrink(server, record):
    from score.conductor import size
    from score.graph import runs
    kept = os.cpu_count
    os.cpu_count = lambda: record["batch_cores"]
    idle = {"claims": 0, "running": 0, "waiting": 0, "wanted": 0, "parked": 0, "frozen": 0}
    later = runs.boot_time() + (size.IDLE_MINUTES + 1) * 60
    try:
        early = size.tick(say=lambda line: None, now=runs.boot_time() + 60, view=idle, state_path=size.STATE)
        found = size.tick(say=lambda line: None, now=max(later, time.time() + (size.IDLE_MINUTES + 1) * 60),
                          view=idle, state_path=size.STATE)
    finally:
        os.cpu_count = kept
    ok = early["action"] is None and found["action"] == size.SHRINK and server.asks[-1]["action"] == "shrink"
    return ok, {"early": early, "shrink": found, "asks": list(server.asks)}


def step_kill(home):
    from score.conductor import kill
    from score.graph import runs
    fake = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    runs.claim("dry-commit", ["brief@north"], fake.pid)
    parked = PROPS_HOME / "cloud" / "parked"
    parked.mkdir(parents=True, exist_ok=True)
    (parked / "dry-machine.json").write_text(json.dumps({"id": "dry-machine", "zone": "nowhere", "token": "t"}))
    released, refused = [], None
    if running_under_agent():
        try:
            kill.stop_all("dry", "the dry check")
        except PermissionError as refusal:
            refused = str(refusal)
    report = kill.stop_everything("dry", "the dry check", release=lambda *machine: released.append(machine))
    ended = waited(lambda: fake.poll() is not None, 10)
    ok = (ended and fake.pid in report["runs"] and released == [("dry-machine", "nowhere", "t")]
          and conductor.free_only() and (refused is not None or not running_under_agent()))
    return ok, {"report": report, "ended": ended, "agents_stop_all": refused}


def walk(record, server, copy, env, home):
    """Every step in order, each one's (ok, detail) or its error; the results."""
    steps = [("plan", lambda: step_plan(copy, env)), ("waiting for size", lambda: step_wait(copy, env, server, record)),
             ("resume", lambda: step_resume(copy, record)), ("memory guard", lambda: step_memory(home)),
             ("health and logs", lambda: step_health(home)), ("shrink", lambda: step_shrink(server, record)),
             ("kill switch", lambda: step_kill(home))]
    results = []
    for name, step in steps:
        started = time.monotonic()
        try:
            ok, detail = step()
        except Exception:  # noqa: BLE001 - a failed step is said in the detail, and the rest still run
            ok, detail = False, {"error": traceback.format_exc()[-3000:]}
        results.append({"step": name, "ok": ok, "seconds": round(time.monotonic() - started, 1), **detail})
    return results


def inside(detail):
    """The check itself, in the temp home this process was started in; the detail file written, results returned."""
    from score.graph import frozen
    home = PROPS_HOME
    write_design()
    server = size_function()
    record = {"name": WORLD, "zone": "nowhere", "idle_type": "DRY-IDLE", "batch_type": "DRY-BATCH",
              "idle_cores": conductor.cores(), "batch_cores": conductor.cores() + 1, "project": "dry-conductor"}
    conductor.MACHINE.write_text(json.dumps(record))
    reader = home / "secret-reader"
    reader.write_text(f"#!/bin/sh\necho {TOKEN}\n")
    reader.chmod(0o700)
    # the toy's nodes take 0.2-0.3 GB: a 1 GB floor, so this PC's live memory holds no step up (each node's room is
    # its stage's peak beside the floor, a stage never measured given the floor: 2026-10-28, 9.9 GB free held resume)
    os.environ.update({conductor.SIZE_URL: server.url, "SCORE_SECRET_READER": str(reader), graph.FLOOR_VARIABLE: "1"})
    commit, _ = frozen.snapshot(REPO)
    copy = frozen.make(REPO, commit)
    env = {**os.environ, frozen.FROZEN: str(copy)}
    try:
        results = walk(record, server, copy, env, home)
    finally:
        server.shutdown()
        if copy.exists():  # the resumed run owned it and may have removed it already
            frozen.remove(copy)
    pathlib.Path(detail).write_text(json.dumps(results, indent=1, default=str))
    return results


def detail_path():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    return PROPS_HOME / "logs" / f"conductor-dry-{stamp}.json"


def start():
    """`python -m score.conductor dry`: the check in a fresh temp home, free only; its one line, its exit code."""
    detail = detail_path()
    detail.parent.mkdir(parents=True, exist_ok=True)
    home = pathlib.Path(tempfile.mkdtemp(prefix="score-conductor-dry-"))
    env = {**os.environ, "PROPS_HOME": str(home), conductor.FREE_ONLY: "1", "PROPS_WORK": str(home / "work")}
    env.pop(conductor.SIZE_URL, None)
    try:
        done = subprocess.run([sys.executable, "-m", "score.conductor.dry", "inside", str(detail)], cwd=REPO, env=env,
                              capture_output=True, text=True, timeout=600)
    finally:
        shutil.rmtree(home, ignore_errors=True)
    if not detail.exists():
        error = done.stdout[-2000:] + done.stderr[-3000:]
        detail.write_text(json.dumps([{"step": "start", "ok": False, "error": error}], indent=1))
    results = json.loads(detail.read_text())
    failed = [result["step"] for result in results if not result["ok"]]
    line = (f"conductor dry: {len(results) - len(failed)} of {len(results)} steps passed"
            + (f", failed: {', '.join(failed)}" if failed else "") + f"; detail {detail}")
    return line, 0 if not failed else 1


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2:])
    elif sys.argv[1] == "inside":
        inside(sys.argv[2])
