"""Every accepted output handed to the creator's library the moment it is accepted (owner, 2026-11-02, #40): the
runner's automatic accept and the owner's own, not only through library@<place> at the end of a place's line, so a
cloud run never makes again what a PC run accepted. library@<place> and library-world stay the completion checks.

    handed.start(store, world, commit, route)   # after an accept: one handover process a world, never one an accept
    handed.waiting(store, world, nodes)         # {place or None: [(node, output)]} accepted and not in the library yet
    handed.status_line(store, world, nodes)     # what has not reached the library, and why, in one line
    python -m score.stages.library.handed --world world1 [--commit C --route H]   # the handover process (start's)
    python -m score.stages.library.handed --world world1 --start                  # a sync pass: start it when waiting

The library's command hands a place (or the world's own nodes) at a time, never one output (score_lib handover:
every node of the place that stands accepted), so an accept is handed by handing its place again, and accepts that
come together go in one handover. It is the library rows' own route (backend.py's settings, words and run; its blob
store key from the secret store, in the command's environment only), into `<store root>/library-handed/<world>/
<place or _world>/`: `reads.json` what score asked to hand, `handover.json` the library's report. An output is handed
once a report the library pushed covers it. A handover that fails writes `failed.json` there (its error, when, how
many tries, what waits) and leaves the accept as it is; the next accept, `score run`'s start and every cockpit sync
pass (score/dashboard/sync/client.py `library_handing`) start it again, and `python -m score status` says what waits.

`start` touches `.again` and spawns the handover process only when no other holds the world's `.lock`; the holder
loops while `.again` is there, and looks once more after letting go, so an accept that lands during a handover is
never missed. The process runs from the main checkout (a `score run`'s frozen copy and what runs in it are removed
when the run ends), on the real home, with the run's own commit and route.

In the framework's own files (graph/_code.FRAMEWORK): it decides when the library is handed to, never what an output
is, so no row's key reads it.
"""
import argparse
import contextlib
import datetime
import fcntl
import json
import os
import pathlib
import subprocess
import sys

from score.stages import library
from score.stages.library import backend, handover

FOLDER = "library-handed"
WORLD_FOLDER = "_world"
FAILED, AGAIN, LOCK, NEXT = "failed.json", ".again", ".lock", "next"
LIBRARY_ROWS = (library.PLACE_ROW, library.WORLD_ROW)


def store_root(store):
    """The store's own folder (the one holding objects/), its links resolved: a frozen run's home links the real one."""
    return pathlib.Path(store.objects.root).resolve().parent


def world_folder(store, world):
    return store_root(store) / FOLDER / world


def place_folder(store, world, place):
    return world_folder(store, world) / (place or WORLD_FOLDER)


def nodes_of(table, places):
    """{place or None: [node]} of a stage table's rows, the library rows left out: the world's own nodes under None."""
    rows = [stage for stage in table if stage.name not in LIBRARY_ROWS]
    found = {None: [stage.name for stage in rows if stage.grain == "world"]}
    for place in places:
        found[place] = [f"{stage.name}@{place}" for stage in rows if stage.grain == "place"]
    return found


def covered(store, world, place):
    """{(node, output)} the newest report of the place covers, empty unless the library pushed it."""
    path = place_folder(store, world, place) / handover.REPORT
    if not path.is_file():
        return set()
    report = json.loads(path.read_text())
    if not (report.get("saved") or {}).get("pushed"):
        return set()
    return {(row["node"], row["output"]) for row in report.get("covered", [])}


def waiting(store, world, nodes):
    """{place or None: [(node, output)]} of every accepted output of `nodes` (nodes_of) no pushed report covers."""
    found = {}
    for place, names in nodes.items():
        held = covered(store, world, place)
        accepted = [(node, store.accepted(node)) for node in names]
        left = [(node, output) for node, output in accepted if output and (node, output) not in held]
        if left:
            found[place] = left
    return found


def failure(store, world, place):
    """The place's recorded failed handover, or None."""
    path = place_folder(store, world, place) / FAILED
    return json.loads(path.read_text()) if path.is_file() else None


def hand(store, job, place, outputs):
    """Hand the place (None: the world's own nodes) to the library once, through the library rows' command; its
    report. Raises when the command fails, writes no report on the contract, did not push or left an asked output
    uncovered: the place's last report stays until a new one is on the contract."""
    folder = place_folder(store, job["world"], place)
    out = folder / NEXT
    out.mkdir(parents=True, exist_ok=True)
    (out / handover.REPORT).unlink(missing_ok=True)
    handover.write(out / handover.READS, [{"node": node, "output": output} for node, output in outputs])
    values = backend.settings()
    if backend.kind(values) == backend.NONE:
        raise backend.Misconfigured(handover.NO_LIBRARY)
    run = {"world": job["world"], "place": place, "seed": job["seed"], "commit": job["commit"], "route": job["route"],
           "store": str(store_root(store) / "objects"), "repo": job["repo"], "out": str(out)}
    backend.run(backend.arguments(values, run), values, run["store"], run["repo"])
    if not (out / handover.REPORT).is_file():
        raise RuntimeError(f"the library's handover command wrote no {handover.REPORT} into {out}")
    report = json.loads((out / handover.REPORT).read_text())
    faults = handover.report_faults(report)
    if faults:
        raise RuntimeError(f"the library's report is off its contract: {'; '.join(faults)}")
    os.replace(out / handover.REPORT, folder / handover.REPORT)
    os.replace(out / handover.READS, folder / handover.READS)
    if not report["saved"]["pushed"]:
        raise RuntimeError(f"the library did not push the handover: {report['saved'].get('why') or 'no reason given'}")
    missing = sorted(set(outputs) - {(row["node"], row["output"]) for row in report["covered"]})
    if missing:
        raise RuntimeError("the library's report does not cover " + ", ".join(f"{node} {output[:12]}"
                                                                             for node, output in missing))
    return report


def record_failure(store, world, place, error, outputs):
    """Write the place's failed.json: the error, when, the tries so far, what waits; its record."""
    before = failure(store, world, place) or {}
    record = {"error": f"{type(error).__name__}: {error}", "at": datetime.datetime.now(datetime.UTC).isoformat(
              timespec="seconds"), "tries": before.get("tries", 0) + 1,
              "waiting": [{"node": node, "output": output} for node, output in outputs]}
    path = place_folder(store, world, place) / FAILED
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return record


def hand_waiting(store, world, job_of, nodes):
    """Hand every place with an accepted output waiting, one after another; a line each. A place that fails is
    recorded (record_failure) and the others still go; one that succeeds loses its failed.json. `job_of()` gives
    {world, seed, commit, route, repo}, asked only when something waits."""
    lines = []
    for place, outputs in waiting(store, world, nodes).items():
        try:
            hand(store, job_of(), place, outputs)
        except Exception as error:  # recorded in failed.json, said in the line, shown by status: never silent
            record = record_failure(store, world, place, error, outputs)
            lines.append(f"{place or 'world'}: {len(outputs)} outputs not handed, try {record['tries']}: "
                         f"{record['error']}")
            continue
        (place_folder(store, world, place) / FAILED).unlink(missing_ok=True)
        lines.append(f"{place or 'world'}: {len(outputs)} outputs handed")
    return lines


@contextlib.contextmanager
def held(path):
    """The world's handover lock, without waiting: yields whether this process holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def drain(store, world, job_of, nodes_of_now, say=print):
    """Hand what waits while `.again` is there, under the world's lock; after letting go, look once more, so an
    accept that touched `.again` meanwhile is handed. Returns at once when another process holds the lock."""
    base = world_folder(store, world)
    again = base / AGAIN
    while True:
        with held(base / LOCK) as got:
            if not got:
                return
            while again.exists():
                again.unlink(missing_ok=True)
                for line in hand_waiting(store, world, job_of, nodes_of_now()):
                    say(line)
        if not again.exists():
            return


def spawn(store, job):
    """Start the handover process for `job` ({world, commit, route}), detached, from the main checkout on the real
    home, nothing in its environment naming a run's frozen copy (backend.outside_frozen: a run's ledger tagging on
    PYTHONPATH named it, 2026-11-05); its output in `<store root>/logs/library-handed-<world>.log`."""
    checkout = backend.main_checkout()
    python = checkout / ".venv/bin/python"
    words = [str(python if python.exists() else sys.executable), "-m", "score.stages.library.handed",
             "--world", job["world"]]
    words += [word for option in ("commit", "route") if job.get(option) for word in (f"--{option}", job[option])]
    environment = backend.outside_frozen(dict(os.environ), checkout)
    environment["PROPS_HOME"] = str(store_root(store).parent)
    log = store_root(store) / "logs" / f"library-handed-{job['world']}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as written:
        subprocess.Popen(words, cwd=checkout, env=environment, stdin=subprocess.DEVNULL, stdout=written,
                         stderr=subprocess.STDOUT, start_new_session=True)


def start(store, world, commit=None, route=None):
    """Ask for the world's waiting outputs to be handed: `.again` touched, and the handover process spawned unless
    one holds the lock (it takes this ask on its next loop); its words."""
    base = world_folder(store, world)
    base.mkdir(parents=True, exist_ok=True)
    (base / AGAIN).touch()
    with held(base / LOCK) as free:
        pass
    if not free:
        return "a handover is running: it hands this next"
    spawn(store, {"world": world, "commit": commit, "route": route})
    return "handover started"


def status_line(store, world, nodes):
    """What has not reached the library, by place, and each failing place's error, in one line."""
    found = waiting(store, world, nodes)
    if not found:
        return "library handover: every accepted output is in the library"
    count = sum(len(outputs) for outputs in found.values())
    by_place = ", ".join(f"{place or 'world'} {len(outputs)}" for place, outputs in found.items())
    failing = [(place, failure(store, world, place)) for place in found]
    said = "; ".join(f"{place or 'world'}: {record['error']} at {record['at']} (try {record['tries']})"
                     for place, record in failing if record)
    return (f"library handover: {count} accepted outputs not in the library yet ({by_place})"
            + (f"; failing: {said}, tried again on the next accept and each sync pass" if said else ""))


def parse(argv):
    parser = argparse.ArgumentParser(prog="python -m score.stages.library.handed")
    parser.add_argument("--world", default="world1")
    parser.add_argument("--commit", help="the score commit the outputs are read at (default: this checkout's)")
    parser.add_argument("--route", help="the route the outputs were made under (default: this checkout's)")
    parser.add_argument("--start", action="store_true", help="say what waits and start the handover when any does")
    return parser.parse_args(argv)


def main(argv=None):
    from score import stages
    options = parse(argv)
    runner = stages.runner(world=stages.WORLDS[options.world]())
    store = runner.store

    def nodes_now():
        return nodes_of(runner.stages.values(), stages.places(runner.world, store))
    if options.start:
        line = status_line(store, options.world, nodes_now())
        if waiting(store, options.world, nodes_now()):
            line += f"; {start(store, options.world, options.commit, options.route)}"
        print(line, flush=True)
        return
    job = {}

    def job_of():
        if not job:
            job.update(world=options.world, seed=runner.world.seed, repo=str(library.REPO),
                       commit=options.commit or library.score_commit(),
                       route=options.route or library.runner_route(runner))
        return job
    stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    print(f"{stamp} library handover of {options.world}", flush=True)
    drain(store, options.world, job_of, nodes_now, say=lambda line: print(line, flush=True))
    print(status_line(store, options.world, nodes_now()), flush=True)


if __name__ == "__main__":
    main()
