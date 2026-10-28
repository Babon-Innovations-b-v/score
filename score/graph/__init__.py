"""The stage runner, in Infinigen's run_stage shape: a stage table in code, a seed per node, prerequisites, and a finish
record for every output, so a changed input reruns only what it reaches.

    runner = Runner(stages, environment, store)
    runner.run(places)        # {node: what it did}: made, judged again, fresh, accepted, or blocked and why
    runner.drive(places)      # every line to its end, evidence gathered; a line that stops leaves a fault report
    runner.lines(places)      # {line: (its state, {node: state})}, running nothing
    runner.status(places)     # {node: its state and why}, running nothing
    runner.why(node)          # the node's records back through every earlier stage it read
    runner.ticket(node)       # the node's key, only when every prerequisite passed and is accepted (paid runs)
    runner.stale(node)        # the earlier nodes whose accepted output moved since the node's accepted output read them

A node is one stage for one place (`stage@place`), or for the whole environment (`stage`). Its key hashes the stage's name
and grain, its computed code version (the stage's and its checks' modules and every repository module they import),
its parameters, its seed, its pinned images and models, and the key of every input: an environment file's or seed folder's
content hash, or an earlier node's accepted output. A node whose key has a finish record is not made again. Its gates
are judged again, without remaking it, when a check's evidence changes.

Every output is checked against its stage's contract and stamped with it (score.contracts) before it is stored; one
off its contract is not stored. A node reads an earlier output only when its stamp is the schema and version the node
expects, and only when every earlier stage it reads has a finish record for its current key, a judgement on its
current evidence that passed (or whose failed checks the owner waived for that key), and an accept of that very
output. The runner gives that accept by itself (review.accept_automatically) when the output passed, nothing got worse
than the accepted output and the owner never rejected it; otherwise the new output lands beside the accepted one and
waits for the owner. When he rejects an accepted output, its node's accepted output moves back, and every later node
whose accepted output read the rejected one is stale (`stale`, shown in status): its key now names the output
accepted before, so its next run makes (or finds) the output that reads that one.
A new output that fails its gates is made once more with a fresh seed when that is free here (`after_failure`); a
second failure, or a paid remake, goes on the owner's list, priced (REMAKES).
A paid stage runs cleared by the runner (score.adapters.compute: its inputs pass and its stop has room for its
estimate, `Stage.euros`), inside that clearance's ticket.

`drive` is the runner with no agent in the loop: it runs each node, every line side by side and each node in a process
of its own, once the nodes it reads stand accepted, gathers a check's missing evidence itself (`Stage.gatherers`, a paid
one cleared like a paid stage; only when nothing else blocks the node, so nothing is spent on an output that fails
anyway), and waits on every cloud step itself. A node that does not end accepted (a gate failed or answered unknown, an
input is missing, it errored or waits for the owner) stops its own line only: the nodes after it are not run, and it
leaves a plain fault report (`faults/<node>.txt` beside the store: the node, the cause, every blocking check's reason,
measures and findings, and the tail of its log, `logs/<node>.log`) for an agent or the owner to be pointed at. A node
that stands removes its old report. Once a node stops its line, every node that reads it (directly or through another
node) is not run; a node on that line that reads nothing of it still runs, so a failure is a gap, not a stopped line.

Runs side by side on one store make a node's key one at a time (`held`, a file lock in `locks/` beside the store): a
second run waits, then finds the first's record and makes nothing. A record or judgement another run stored first is
taken as made.
"""
import contextlib
import contextvars
import datetime
import fcntl
import inspect
import json
import multiprocessing
import multiprocessing.connection
import os
import pathlib
import platform
import shutil
import signal
import sys
import threading
import time
import traceback
import urllib.error
from dataclasses import dataclass, field
from typing import Callable

from score import checks, contracts, review
from score.adapters import models
from score.graph import _code, stopped
import score.store as score_store
from score.store import durable, file_hash, listing_hash, text_hash, tree_files, tree_listing

GRAINS = ("world", "place")
# What a place's files need on disk before they are worked out, each a function of the place (the stage table puts
# the Pixal3D takes the library holds back in work/pixal: tools/library/pixal_takes.py). It makes nothing new: the
# same bytes come back, so no key moves.
PLACE_READS = []
WORLD_LINE = "world"
LOG_TAIL = 40
NOT_RUN = " has not run on its current inputs"  # usable's cause; a fault report names what moved its key
# A failed output's note, once per key in the store (the count that keeps a node to one free remake across runs and
# restarts): remakes/<node>/<key>.json, `then` "remake" (its key's attempt 2 is made), "owner" (on his list, priced),
# "fix" (a row of cached model asks: same question, same answer) or "done" (attempt 2's own outcome). Each note is also
# a line of the runner's remake log beside the store, and an "owner" one a line of the owner's list there (owner,
# 2026-10-28).
REMAKES = "remakes/"
REMAKE_LOG, OWNER_LIST = ("remakes", "notes", ".jsonl"), ("remakes", "owner-list", ".jsonl")
# The model asks answered from a cache by their request (google_spend's batch route, the claude-code adapter): a row
# whose own files are or import one is made again only when its key moves (owner, 2026-10-28: "it should only
# actually retry if the prompt changed").
CACHED_ASKS = {_code.REPO / name for name in ("score/stages/surfaces/route_ask.py", "score/stages/surfaces/claude_asks.py",
                                              "score/stages/effects/asked.py", "score/adapters/models/claude_code.py")}
SAME_ANSWER = "same question, same answer: needs a source fix (prompt or inputs)"
# Nodes the drive runs at once: most wait on a rented machine, the rest work on this PC's cores.
JOBS = 8
# How often a node's process checks that its runner is still there (watch_runner).
RUNNER_POLL_SECONDS = 2
# A drive says a heartbeat line (rows done, running and queued, and the run's gauges) every HEARTBEAT seconds, so a run
# that is alive says so and a quiet log means a dead run (2026-10-16: runs failed or sat idle for hours unseen).
HEARTBEAT = 120
# The drive starts a node only while this PC's available memory, less what each running node is still expected to
# take (its stage's measured peak less what its process tree holds now; a node that ended holds none) and less the
# new node's own peak, stays at MEMORY_FLOOR or above; it reads again every MEMORY_POLL seconds. A stage's peak is the
# most memory one of its nodes' process trees held, by proportional share (Pss, smaps_rollup: a node forked from the
# drive and its Blender and pool children share pages, which an RSS sum counted once per process: 15.8 GB kept for
# finish-route-views nodes holding 2.5 GB, 2026-10-28), read by the node itself and by the drive, whichever is more,
# kept per stage in memory/peaks-made.json beside the store (peaks.json and peaks-pss.json, kept before a node that
# made nothing was left out, are no longer read); a stage never measured is given MEMORY_FLOOR. 2026-10-28:
# five finish-route-views nodes grew to 4.8-6.4 GB each minutes after their start and took this PC to 7 GB free
# (the rule then reserved a floor only for a node's first minute). This PC (43 GB) has run out of memory before. Measured 2026-10-22 (peak RSS of the make, imports included): plan@hub 0.21 GB,
# earth-seed@greenhouse 0.22 GB, the assembly, completion, earth-seed, scene-record and terrain test makes 0.22-0.28
# GB (a node waiting on a rented machine not measured). 6 GB is far over those, for the nodes not measured yet.
MEMORY_FLOOR = 6 * 2**30
MEMORY_POLL = 30
# A ready node whose peak does not fit is passed over and the nodes after it that fit start (2026-10-28: one 6 GB node
# at the head held 122 small ready nodes and five of eight slots empty for 29 min); one passed over on MEMORY_SKIPS
# turns holds every node after it until it fits, so a large node is never starved by small ones.
MEMORY_SKIPS = 10
# A node whose process tree ran one of these clients holds its real memory in a container, outside its tree (trees_held:
# a Blender node measured 0.1 GB while its container held 3.7 GB, 2026-10-28): its stage keeps no peak below the default.
CONTAINER_CLIENTS = ("blender_cloud.py",)
# A node's process reads its own tree's memory every MEMORY_SAMPLE seconds for the peak it reports (watch_memory).
MEMORY_SAMPLE = 5
# Where the process readings come from (the tests give a folder of their own).
PROC = "/proc"
# A machine whose memory wants another floor names it in GB (score/conductor: SCORE_MIN_FREE_GB on the conductor).
FLOOR_VARIABLE = "SCORE_MIN_FREE_GB"
# The thread-pool variables every node's process sets before its make starts (lowered only: a smaller value the owner
# set stands), so the libraries first loaded in the node and every child it starts share this PC's cores among the
# nodes running at once: six nodes each sizing a pool to every core overloaded the PC for hours (C11, 2026-10-17).
THREAD_VARIABLES = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS")
# A library the drive loaded before it forked (score.stages loads numpy's and scipy's OpenBLAS) sized its pool then
# and never reads the variables again: each node resizes those pools by the first of these setters each one has.
OPENBLAS_SETTERS = ("openblas_set_num_threads", "openblas_set_num_threads64_", "scipy_openblas_set_num_threads",
                    "scipy_openblas_set_num_threads64_")
# The completion gate's check that fails a place's accepted gaps by name (score/review GAPPED).
GAPPED = review.GAPPED
# Each node runs in a forked process: its output (and its children's) goes to its own log, and the toy stages of the
# tests need no import by name. The drive itself starts no threads, so forking it is safe.
FORK = multiprocessing.get_context("fork")
FORK_WAIT = multiprocessing.connection.wait
# A node that errors on a transient fault (a server's 5xx, a timeout, a dropped connection: eight places' maps on the
# image model's HTTP 500s, 2026-10-12) runs again up to RETRIES times, waiting RETRY_WAIT seconds, doubled each try,
# when it is free: a paid node's failure is a gap, never rerun inside the batch (ADR-0005, #30).
RETRIES, RETRY_WAIT = 4, 30
# Runs side by side on one store (17 agents' runs, 2026-10-12: people-segvigen bought twice) make a node's key one at a
# time: a second run waits on the first's lock, then finds its record. One held longer than LOCK_WAIT seconds blocks
# the waiter rather than be broken, so nothing is paid twice; a holder's death lets go of its lock at once.
LOCK_WAIT, LOCK_POLL = 6 * 3600, 2
# The folder a node makes into, named for its make and the processes it starts, so a cloud runner can keep each
# finished job under the node's key and a rerun pay only for the jobs it lacks (tools/cloud/kept.py, C21).
MAKING = "SCORE_MAKING"
# A free-only run (`score run --free`, or any run under SCORE_FREE_ONLY=1: the agents' door, before the owner's Buy)
# runs every free node whose inputs stand and leaves each paid node that does not already stand accepted, as a line
# waits on a block: not cleared, not an error. A node reading one waits on it (FREE_WAITS).
PAID_LEFT = "not run: paid, left for the Buy"
FREE_WAITS = "not run: waits on {node}, paid, left for the Buy"
# A free-only run on this PC's card (SCORE_CLOUD=local, tools/cloud/backends/local.py; owner, 2026-10-27) runs its
# paid nodes too, with no clearance: their machine work costs nothing there, and every real paid point (Google, a
# rent, the cluster) refuses with no ticket and under SCORE_FREE_ONLY, so such a node fails, saying what it would buy.
THIS_PC = ("SCORE_CLOUD", "local")


def on_this_pc():
    """Whether this run's machine work runs on this PC's own card (SCORE_CLOUD=local), where it costs nothing."""
    return os.environ.get(THIS_PC[0]) == THIS_PC[1]


def transient(error):
    """True for an error a later try may not meet: an HTTP 5xx, a timeout or a dropped or refused connection."""
    if isinstance(error, urllib.error.HTTPError):
        return error.code >= 500
    if isinstance(error, urllib.error.URLError) and isinstance(error.reason, BaseException):
        return transient(error.reason)
    return isinstance(error, (TimeoutError, ConnectionError))


class Blocked(Exception):
    """A node cannot run: an input is missing, or an earlier node failed, answered unknown or is not accepted."""


def passes_euros_on(code):
    """Whether a function takes `euros` or any keyword (a table helper that hands a row's estimate on)."""
    return "euros" in code.co_varnames[:code.co_argcount + code.co_kwonlyargcount] or bool(code.co_flags & inspect.CO_VARKEYWORDS)


def row_written_at():
    """`<file>:<line>` of the stage row being built: the first caller outside this module and the dataclass
    machinery, or, while that caller is a helper of the same file that hands `euros` on, the line calling it."""
    frame = sys._getframe(1)
    while frame.f_code.co_filename in (__file__, "<string>") or frame.f_code.co_filename.endswith("dataclasses.py"):
        frame = frame.f_back
    while (frame.f_back is not None and frame.f_back.f_code.co_filename == frame.f_code.co_filename
           and passes_euros_on(frame.f_code)):
        frame = frame.f_back
    path = pathlib.Path(frame.f_code.co_filename)
    return f"{path.relative_to(_code.REPO) if path.is_relative_to(_code.REPO) else path}:{frame.f_lineno}"


def replaced_row():
    """The row a dataclasses.replace call is building this one from, or None outside one: `obj` of replace, or
    `self` of the _replace it calls on Python 3.13 and later (the innermost frame there)."""
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_code.co_name in ("replace", "_replace") and frame.f_code.co_filename.endswith("dataclasses.py"):
            return frame.f_locals.get("obj", frame.f_locals.get("self"))
        frame = frame.f_back
    return None


# The object filter's names while a selecting stage's files function runs (Runner.files_of), else None.
SELECTED = contextvars.ContextVar("selected objects", default=None)


def selected():
    """The names the runner's object filter keeps, inside a selecting stage's files function; None otherwise."""
    return SELECTED.get()


@dataclass(frozen=True)
class Stage:
    """One row of the stage table.

    make(inputs, out, seed, params) writes the stage's output into the folder `out`; `inputs` maps each input's
    name to a path (an environment file or seed folder in place, an earlier stage's accepted output checked out).
    contract: the output's schema, version and units (score.contracts.Contract); every stage has one.
    files: {name: path pattern}, formatted with the environment's roots and {place}; or a function of the place giving that
    map, for a stage whose environment files differ by place (the surface stage's takes, listed in each place's data).
    after: {earlier stage: (schema, version) this one was written for}, the stages whose accepted output it reads.
    params: {name: value} in the key and handed to make; a callable value is worked out from the runner when the node
    is keyed (the library rows' route, from the runner's code versions).
    models: pinned image kinds whose record (image digest, model revisions) goes into the key (score.adapters.models).
    paid, euros: a stage that rents, and its run's estimate in euros, cleared against its stop.
    forecast: for a paid stage that prices its own make from what it reads, forecast(inputs) gives its run's forecast
    ({euros (its high), minutes, high_minutes, measured}) from the node's checked-out inputs: its clearance reserves
    that figure in place of the stage's measured runs or estimate, so the clearance and the make's own check against
    it are one number (demo-film: its frames' forecast; fault 2026-10-25, a film cleared at EUR 3.50 and forecast at
    77.71 Blocked itself, and measured runs of 96-frame films cleared 192-frame ones). None: compute.run_forecast.
    gatherers: {check name: (gather, euros or None)}, how the runner's drive makes a check's missing evidence:
    gather(output, inputs, folder) writes it and returns its file; a paid one names its estimate in euros. Kept out of
    score.checks on purpose: every stage's code version hashes that module, so a change there reruns every stage.
    applies: for a place stage, applies(place) is False for a place the stage has nothing to do for (its environment data
    says so): that place's line has no such node. None: every place.
    beside, neighbours: for a place stage that reads other places' outputs, {earlier stage: (schema, version)} read
    for each place neighbours(place) names (its input `<stage>@<other place>`), versioned and waited on like `after`;
    an environment stage's neighbours(None) names the places it reads, each stage only where it applies.
    The table refuses a stage that reads itself through what it reads, after or beside (Runner.reached); two places
    that show each other read a stage that reads nothing back, so they make no cycle.
    optional: names in `after` the node reads only while usable (passed, accepted, on its current key); one that is
    not is left out of its reads and its key, so the node runs with what has passed and runs again once it is (the
    characters layer's dress rows: a place lays the people whose look is accepted and names the rest, 2026-10-13).
    gapped: names in `after` the node also reads when their only blocking check is GAPPED, the place's accepted gaps
    (a dated decision): the output on its current key, which the runner never accepts as it fails, unless the owner
    rejected it; any other fault still stops the node (demo-film on complete, the overseer, 2026-10-15).
    upward: its `beside` reads go up to the outside shells that hold this place (an inside place reads its outside shell's
    split, CONTEXT.md "shapes first"), never back down, so a loop through them in the table is the same route one scale
    down: the table's loop check leaves those reads out, and `neighbours` must refuse a place that holds itself.
    downward: its `beside` reads go down to the child scenes this place holds (a parent scene's tree reads each child
    scene's own tree, CONTEXT.md "parent scene"), never back up, so its beside reads may name the stage itself: the
    table's loop check leaves them out as it does an upward stage's, and `neighbours` must refuse a place that holds
    itself or a scene above it, the drive making each child's node before its parent's.
    selects: its make takes the runner's object filter (`score run --object`, Runner.objects): the node's params
    gain `objects`, the sorted names it keeps, so a filtered output has a key of its own and its make handles only
    those objects of its place; while its files function runs, `selected()` gives those names, so another object's
    files neither key nor block it (the table's wrappers call files with the place alone). A stage without it runs
    whole under a filter.
    euros_from: where the row naming its estimate is written, `<file>:<line>` (set when the row is built: the line
    that builds it, through a helper of the same file that passes its `euros` on), so a guess says where it comes
    from. Never in a key.
    """
    name: str
    grain: str
    make: Callable
    contract: contracts.Contract
    checks: tuple = ()
    files: dict | Callable = field(default_factory=dict)
    after: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    paid: bool = False
    euros: float = None
    forecast: Callable = None
    models: tuple = ()
    gatherers: dict = field(default_factory=dict)
    applies: Callable = None
    beside: dict = field(default_factory=dict)
    neighbours: Callable = None
    optional: tuple = ()
    gapped: tuple = ()
    upward: bool = False
    downward: bool = False
    selects: bool = False
    euros_from: str = field(default=None, init=False, compare=False)

    def __post_init__(self):
        if self.euros is not None:
            earlier = replaced_row()
            kept = earlier is not None and earlier.euros == self.euros and earlier.euros_from
            object.__setattr__(self, "euros_from", kept or row_written_at())
        if self.grain not in GRAINS:
            raise ValueError(f"stage {self.name}: grain {self.grain!r} is not one of {GRAINS}")
        if not isinstance(self.contract, contracts.Contract):
            raise TypeError(f"stage {self.name}: its output needs a contract (score.contracts), not {self.contract!r}")
        if not isinstance(self.after, dict):
            raise TypeError(f"stage {self.name}: after maps each earlier stage to the (schema, version) it expects")
        if set(self.optional) - set(self.after):
            raise ValueError(f"stage {self.name}: optional names a stage it does not read after")
        if set(self.gapped) - set(self.after):
            raise ValueError(f"stage {self.name}: gapped names a stage it does not read after")


@dataclass(frozen=True)
class Environment:
    """An environment's name, its seed and the folders its file patterns name ({data}, {seeds}, ...)."""
    name: str
    seed: int
    roots: dict

    @classmethod
    def from_file(cls, path, **roots):
        """An environment from its record ({"name", "seed"}), with the roots its stages' files are found under."""
        record = json.loads(pathlib.Path(path).read_text())
        return cls(record["name"], record["seed"], roots)


# The old name, kept for score/stages/images/__init__.py, which names it: that file is in the images nodes' code
# version, so renaming it there moves their keys; it goes with the images stage's next re-make.
World = Environment


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


def node_seed(world_seed, stage, place):
    """The seed of one node, from the environment's seed, the stage and the place: never a typed number."""
    return int(text_hash(f"{world_seed}/{stage}/{place}")[:8], 16)


BYTECODE_REASON = "same sources, bytecode left out of the key"
NO_OP_REASON = "same result: every change since it was made is proved a no-op for it"
NARROWING_REASON = "same reads: every file its key reads today reads as it did when it was made"
WORDS_REASON = "same meaning: every file its key reads today reads as when it was made, or differs only in words"
# The key parts a narrowing carry needs the same: all but the code version and the declared files' hashes.
NARROWING_SAME = ("contract", "expects", "params", "seed", "models", "after", "beside")


def made_by(record):
    """The commit and code version that made a record's output: what it carried when it was kept over a key move
    (its carried "made by"), its own otherwise."""
    return record.get("carried", {}).get("made by") or {"commit": record["commit"], "code": record["code"]}


def bytecode(relative):
    """True for Python's bytecode (a __pycache__ folder's file or a .pyc): each checkout writes its own beside the
    sources it runs, so a key that hashed it moved with the worktree a run came from (#67, 2026-10-13)."""
    return relative.endswith(".pyc") or "__pycache__" in relative.split("/")


# {(device, inode, size, mtime ns, ctime ns): sha256} of the files source_hash read: a status of environment 1 hashed
# 38,078 files for 1,065 nodes (65 of its 91 s, 2026-10-27), the same input folders again for every node reading
# them. Any write moves a file's ctime, so a hit is the same bytes and every key is as without it; a file changed in
# the last SETTLED_NS is never kept (its clock ticks coarser than a write: the racy-file rule of version control).
HASHED = {}
SETTLED_NS = 2 * 10**9


def stamped_hash(path):
    """file_hash of `path`, read again only when its stat stamp (HASHED) changed or it changed lately."""
    found = os.stat(path)
    stamp = (found.st_dev, found.st_ino, found.st_size, found.st_mtime_ns, found.st_ctime_ns)
    if stamp in HASHED:
        return HASHED[stamp]
    digest = file_hash(path)
    if time.time_ns() - max(found.st_mtime_ns, found.st_ctime_ns) > SETTLED_NS:
        HASHED[stamp] = digest
    return digest


def source_hash(path):
    """An environment file's or folder's hash as a key part: the store's tree hash of it, its bytecode left out."""
    return listing_hash({name: stamped_hash(found) for name, found in tree_files(path).items() if not bytecode(name)})


def watch_runner(runner_pid, every=None):
    """In a node's process: once its runner (`runner_pid`, its parent) is gone, SIGTERM to the runner's whole process
    group when the runner led one (`score run`: each batch in it deletes its machines). A runner that led no group (any
    runner but `score run`) installed no stop handler for its nodes, so its node lives on as before and its batch ends
    its own way: a node ended here broke the pipe its batch writes to, and the batch's delete loop with it (review of
    C7, 2026-10-17). The group gets one SIGTERM, never a second (a batch stops deleting at its second signal): none
    when this node already shows a stop (the group was signalled), and only from the one process that makes the
    runner's stop mark (stopped.claim_stop; the runner makes it when it passed its stop on). Checked every
    RUNNER_POLL_SECONDS; never returns while the runner lives."""
    mark = stopped.stop_mark(runner_pid)
    while os.getppid() == runner_pid:
        time.sleep(every or RUNNER_POLL_SECONDS)
    if os.getpgrp() == runner_pid and not stopped.shows_stop(os.getpid()) and stopped.claim_stop(mark):
        os.killpg(runner_pid, signal.SIGTERM)


def finish_record(node, keyed, output, stage_name, started, clock):
    """A node's finish record: its output under `keyed` (the key and everything it hashes), the commit and machine,
    and the make's start (`started`, a time) and length (from `clock`, time.monotonic at its start)."""
    return {"node": node, "key": keyed["key"], "output": output, "stage": stage_name, "place": keyed["place"],
            "code": keyed["code"], "contract": keyed["contract"], "expects": keyed["expects"],
            "params": keyed["params"], "seed": keyed["seed"], "files": keyed["files"], "after": keyed["after"],
            "models": keyed["models"], **({"beside": keyed["beside"]} if "beside" in keyed else {}),
            **({"remake": keyed["remake"]} if "remake" in keyed else {}),
            **_code.git_commit(),
            "machine": platform.node(), "started": started, "finished": now(),
            "minutes": round((time.monotonic() - clock) / 60, 3), "euros": 0}


def asks_cached(stage):
    """True for a row whose own files (the framework's left out) are or import a cached model ask (CACHED_ASKS)."""
    own = [path for path in _code.start_files(code_functions(stage)) if not _code.in_framework(path, _code.FRAMEWORK)]
    return any(path in CACHED_ASKS or CACHED_ASKS & set(_code.live_imports(path)) for path in own)


def node_name(stage, place):
    return stage.name if stage.grain == "world" else f"{stage.name}@{place}"


def stage_code(stage):
    """A stage's code version: the hash of its make's, checks' and file map's source files and their imports."""
    return listing_hash(_code.code_version(code_functions(stage), file_hash))


def code_functions(stage):
    """The functions whose source files and imports are a stage's code version: its make's, checks' and file map's."""
    return [stage.make, stage.contract.faults, *(check.judge for check in stage.checks),
            *([stage.files] if callable(stage.files) else []), *([stage.neighbours] if stage.neighbours else [])]


@contextlib.contextmanager
def logged(path):
    """This process's and its children's output (file descriptors 1 and 2) into the log file while the block runs."""
    sys.stdout.flush()
    sys.stderr.flush()
    saved = os.dup(1), os.dup(2)
    with open(path, "w") as log:
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        try:
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            for descriptor, copy in zip((1, 2), saved):
                os.dup2(copy, descriptor)
                os.close(copy)


def available_memory():
    """This PC's available memory in bytes (MemAvailable of /proc/meminfo)."""
    with open("/proc/meminfo") as meminfo:
        for line in meminfo:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("/proc/meminfo has no MemAvailable line")


AVAILABLE = available_memory  # the tests give a fake reading


def memory_floor():
    """The memory one node is given room for, in bytes: SCORE_MIN_FREE_GB when set, else MEMORY_FLOOR."""
    named = os.environ.get(FLOOR_VARIABLE)
    return int(float(named) * 2**30) if named else MEMORY_FLOOR


def memory_room(running, expected):
    """True when this PC's available memory, less what each running node is still expected to take (`running`:
    (its stage's peak, what it holds now) in bytes) and less a new node's `expected` peak, stays at the floor
    (memory_floor) or above."""
    coming = sum(max(0, peak - holds) for peak, holds in running)
    return AVAILABLE() - coming - expected >= memory_floor()


def process_table():
    """{pid: (parent pid, resident bytes)} of every process on this PC (PROC/<pid>/stat)."""
    page, table = os.sysconf("SC_PAGE_SIZE"), {}
    for entry in os.scandir(PROC):
        if entry.name.isdigit():
            with contextlib.suppress(OSError, ValueError, IndexError):  # a process that ended while it was read
                fields = pathlib.Path(entry.path, "stat").read_text().rsplit(")", 1)[1].split()
                table[int(entry.name)] = (int(fields[1]), int(fields[21]) * page)
    return table


def proportional_bytes(pid, resident):
    """The bytes process `pid` holds as its share of every page (Pss of PROC/<pid>/smaps_rollup): a page shared with
    its parent or children counts once over them all, not once each; `resident` where that file cannot be read."""
    with contextlib.suppress(OSError, ValueError, StopIteration):
        with open(os.path.join(PROC, str(pid), "smaps_rollup")) as rollup:
            return int(next(line for line in rollup if line.startswith("Pss:")).split()[1]) * 1024
    return resident


def trees_held(pids):
    """{each of `pids`: the bytes its process and every descendant hold now, by proportional share
    (proportional_bytes)} (0 once it is gone)."""
    table, children = process_table(), {}
    for pid, (parent, _) in table.items():
        children.setdefault(parent, []).append(pid)
    held = {}
    for root in pids:
        tree, total = [root], 0
        while tree:
            pid = tree.pop()
            if pid in table:
                total += proportional_bytes(pid, table[pid][1])
            tree += children.get(pid, [])
        held[root] = total
    return held


HELD = trees_held  # the tests give a fake reading


def watch_memory(high, every=None):
    """In a node's process: keep in `high` ([bytes, whether a container client ran]) the most its process tree held
    (trees_held) and whether its tree ran a container client (ran_container_client), read every MEMORY_SAMPLE seconds;
    never returns."""
    while True:
        high[0] = max(high[0], HELD([os.getpid()])[os.getpid()])
        high[1] = high[1] or ran_container_client(os.getpid())
        time.sleep(every or MEMORY_SAMPLE)


def ran_container_client(root):
    """Whether a process under `root` (PROC/<pid>/cmdline) runs one of CONTAINER_CLIENTS."""
    children = {}
    for pid, (parent, _) in process_table().items():
        children.setdefault(parent, []).append(pid)
    tree = list(children.get(root, []))
    while tree:
        pid = tree.pop()
        with contextlib.suppress(OSError):
            words = pathlib.Path(PROC, str(pid), "cmdline").read_bytes().split(b"\0")
            if any(os.path.basename(word.decode(errors="replace")) in CONTAINER_CLIENTS for word in words):
                return True
        tree += children.get(pid, [])
    return False


def unsettled(optional, line, stood, stopped):
    """A waiting node's `optional` reads (Runner.optional_nodes) the drive still makes (in its `line`, neither stood
    nor stopped): the node waits on them, then reads each that stood and runs without each that stopped
    (Runner.reads)."""
    return [name for name in optional if name in line and name not in stood and name not in stopped]


def kept(known, node, what, work, *args):
    """work(*args), kept in `known` ({node: {what: answer}}) across a drive's turns until forget drops the node."""
    answers = known.setdefault(node, {})
    if what not in answers:
        answers[what] = work(*args)
    return answers[what]


def forget(known, ended):
    """Drop from `known` each waiting node the nodes that just ended (`ended`) may have moved: every node when an
    environment node ended, else every environment node, every node of an ended node's place (the place's plan may be
    what ended: a stage's `applies` reads it) and every node that reads an ended node."""
    places = {node.partition("@")[2] for node in ended}
    if "" in places:
        known.clear()
        return
    for node in [node for node, answers in known.items() if not node.partition("@")[2]
                 or node.partition("@")[2] in places
                 or not ended.isdisjoint([*answers.get("earlier", ()), *answers.get("optional", ())])]:
        del known[node]


def node_threads(jobs):
    """The threads each of `jobs` nodes at once may use: this PC's cores shared out, at least one."""
    return max(1, (os.cpu_count() or 1) // jobs)


def oversubscribed(jobs):
    """Why `jobs` nodes at once, each with its node_threads, would ask for more threads than this PC has cores; None
    when they fit."""
    cores, threads = os.cpu_count() or 1, node_threads(jobs)
    if jobs * threads <= cores:
        return None
    return (f"{jobs} jobs of {threads} thread(s) each ask for {jobs * threads} threads on {cores} cores; lower --jobs "
            "or pass --oversubscribe")


def cap_threads(threads):
    """This process's thread pools, those already loaded included, and every child it starts run on at most
    `threads`."""
    cap_thread_variables(threads)
    resize_loaded_openblas(int(os.environ["OPENBLAS_NUM_THREADS"]))


def cap_thread_variables(threads):
    """Lower each THREAD_VARIABLES to `threads`; a smaller value already set stands."""
    for variable, own in owner_thread_counts().items():
        os.environ[variable] = str(threads if own is None else min(own, threads))


def owner_thread_counts():
    """{each THREAD_VARIABLES: the thread count the owner set in it, None when unset or empty}; a ValueError naming
    one set to anything but a whole number above 0 (OpenMP's '4,2', 'auto')."""
    counts = {}
    for variable in THREAD_VARIABLES:
        own = os.environ.get(variable, "").strip()
        if own and not (own.isdigit() and int(own) > 0):
            raise ValueError(f"{variable}={own!r} is not a thread count (a whole number above 0); unset it or set one")
        counts[variable] = int(own) if own else None
    return counts


def loaded_openblas():
    """The OpenBLAS libraries this process has loaded, by path."""
    with open("/proc/self/maps") as maps:
        paths = {line.split()[-1] for line in maps if line.rstrip().endswith(".so") or ".so." in line}
    return sorted(path for path in paths if "openblas" in pathlib.Path(path).name.lower())


def resize_loaded_openblas(threads):
    """Size the pool of every OpenBLAS this process has already loaded to `threads`."""
    import ctypes
    for library in loaded_openblas():
        handle = ctypes.CDLL(library)
        setter = next((name for name in OPENBLAS_SETTERS if hasattr(handle, name)), None)
        if setter is None:
            raise RuntimeError(f"{library}: an OpenBLAS with none of {OPENBLAS_SETTERS}; its pool cannot be capped")
        getattr(handle, setter)(threads)


def no_bytecode():
    """This process and every make and child process it starts write no bytecode: a .pyc written into a declared
    code folder mid-run (tools/characters/maker, 2026-10-13) read as an input changed while the node ran, and the
    paid try stored nothing."""
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


WHOLE_WALK = score_store.runtime_store.FolderStore.keys


def scoped_keys(self, prefix):
    """FolderStore.keys walking only the prefix's own folder: the store's own walks every file under the root
    (millions of blobs) on each call, which held an environment run at one core for hours, 25 rows in 3.5 h (2026-10-14: 261
    of a status's 389 s). The same keys, sorted, as WHOLE_WALK gives."""
    folder = self.root / prefix.rsplit("/", 1)[0] if "/" in prefix else self.root
    if not folder.is_dir():
        return []
    found = (str(path.relative_to(self.root)) for path in folder.rglob("*")
             if path.is_file() and not path.name.endswith(".partial"))
    return sorted(key for key in found if key.startswith(prefix))


def listed_once(keys):
    """keys(prefix), each prefix listed once: a pass that writes nothing reads one listing per prefix."""
    listings = {}

    def listing(prefix):
        if prefix not in listings:
            listings[prefix] = keys(prefix)
        return list(listings[prefix])
    return listing


def scoped(store):
    """Every folder store in this process listed by scoped_keys (a stage's own Store.default() too: the neighbours'
    record_of opens one), the store as given. Set here, in the runner, since the store's own module is in every
    stage's code version and an edit there moves every key."""
    score_store.runtime_store.FolderStore.keys = scoped_keys
    return store


def gone(folder):
    """Remove a make's folder however the make ended (2026-10-27: failed makes' folders filled store/cache/making; a
    paid run's finished jobs are kept apart, tools/cloud/kept.py). One a killed make leaves, or one not removable here,
    the sync pass sweeps once no run is live (score/conductor/disk.py clean-cache --making-only)."""
    for path in [folder, *pathlib.Path(folder).rglob("*")]:
        with contextlib.suppress(OSError):  # gone meanwhile: nothing to open up
            if path.is_dir() and not path.is_symlink():
                path.chmod(0o755)  # a make may copy a read-only folder in
    shutil.rmtree(folder, ignore_errors=True)


@contextlib.contextmanager
def making_in(folder):
    """Name the folder a node makes into (MAKING) for its make and the processes it starts, while the block runs."""
    before = os.environ.get(MAKING)
    os.environ[MAKING] = str(folder)
    try:
        yield
    finally:
        if before is None:
            os.environ.pop(MAKING, None)
        else:
            os.environ[MAKING] = before


def heartbeat_line(done, running, queued, gauges):
    """The drive's heartbeat: rows done, running and queued, then what `gauges()` says."""
    return f"heartbeat {now()}: rows done {done}, running {running}, queued {queued}; {read_gauges(gauges)}"


def read_gauges(gauges):
    """What `gauges()` says, or why it could not be read: a gauge reads files other runs write (the shared ledger, the
    reservations), and one it cannot read never ends a drive whose nodes are still running."""
    try:
        return gauges()
    except Exception as error:  # noqa: BLE001 - said in the beat; the drive goes on
        return f"gauges unreadable: {type(error).__name__}: {error}"


class Runner:
    def __init__(self, stages, world, store, model_record=None):
        no_bytecode()
        durable.install()  # synced writes and quarantining reads, here and not in the store's module: in no row's key
        self.stages = {stage.name: stage for stage in stages}
        self.world = world
        self.store = scoped(store)
        self.model_record = model_record or models.record
        self.code_versions = {}
        self.remembered = None  # inside `still`: {(what, node): its value or its Blocked}
        self.driving = None  # (nodes running, monotonic time) at the end of drive's last pass: score run's watchdog
        self.began = {}  # {node: epoch seconds its process started} (start): score run's pool forecast (row_due)
        self.objects = None  # the object filter (`score run --object`): the names a selecting stage keeps, or None
        self.free_only = False  # a free-only run (PAID_LEFT): nothing cleared, paid nodes left for the Buy
        self.bought = False  # a bought batch (his checkout or benchmark grant): a passing worse output is accepted
        unknown = {before for stage in stages for before in (*stage.after, *stage.beside)} - set(self.stages)
        if unknown:
            raise ValueError(f"stages read stages the table lacks: {sorted(unknown)}")
        looping = sorted(name for name in self.stages if name in self.reached(name))
        if looping:
            raise ValueError(f"stages read themselves through what they read, after or beside (a cycle between "
                             f"places): {looping}")

    def reached(self, name):
        """Every stage a stage reads, after or beside, directly or through what those read. A stage graph without a
        loop has no node cycle: after is in one place, and a beside read is another place's node of a stage that
        never reads back to this one (the assembly reads the claiming place's bake beside it; neighbours reads the
        assembly beside it). An upward stage's beside reads are left out: they go up to the place holding this one,
        so its loop is the route one scale down, never a node cycle (`Stage.upward`); a downward stage's too: they go
        down to the scenes this one holds (`Stage.downward`)."""
        found, todo = set(), list(self.read_stages(self.stages[name]))
        while todo:
            before = todo.pop()
            if before not in found:
                found.add(before)
                todo += self.read_stages(self.stages[before])
        return found

    @staticmethod
    def read_stages(stage):
        """The stages one stage reads that can close a loop: its after, and its beside unless it is upward or
        downward."""
        return [*stage.after, *(() if stage.upward or stage.downward else stage.beside)]

    @contextlib.contextmanager
    def still(self):
        """A pass that writes nothing to the store (status, lines, a finished node's verdict): each prefix it looks up
        is listed once, not once a lookup, and only the run's own nodes' prefixes are listed, never the whole store (a
        walk of the whole store per finished node held world runs at their end and slowed every run beside them,
        2026-10-16); each node's key and staleness are worked out once, not once a path through the nodes that read it
        (both recurse through every node a node reads; a run's closing status took longer than its run)."""
        if self.remembered is not None:
            yield
            return
        from score.review import plans  # each place's plan read once too (plans.one_moment): the pass writes nothing
        self.store.objects.keys = listed_once(self.store.objects.keys)
        self.remembered = {}
        try:
            with plans.one_moment():
                yield
        finally:
            del self.store.objects.keys
            self.remembered = None

    def remember(self, what, node, work):
        """work() once a `still` pass (its Blocked too); outside one, every time."""
        if self.remembered is None:
            return work()
        if (what, node) not in self.remembered:
            try:
                self.remembered[what, node] = work()
            except Blocked as block:
                self.remembered[what, node] = block
        found = self.remembered[what, node]
        if isinstance(found, Blocked):
            raise found
        return found

    # --- keys --------------------------------------------------------------------------------------------------

    def code(self, stage):
        """The stage's computed code version: its make's and its checks' source files and their imports (once a run)."""
        if stage.name not in self.code_versions:
            self.code_versions[stage.name] = stage_code(stage)
        return self.code_versions[stage.name]

    def files_of(self, stage, place):
        """{name: path pattern} of the environment files the node reads (worked out once a `still` pass)."""
        if not callable(stage.files):
            return stage.files

        def worked_out():
            for read in PLACE_READS:
                read(place)
            with self.selection(stage):
                return stage.files(place)
        return self.remember("files", node_name(stage, place), worked_out)

    @contextlib.contextmanager
    def selection(self, stage):
        """The object filter's names as `selected()` while the block runs, for a stage that selects (its files, and
        the units its forecast counts: gaps price.rule_units); no filter for any other."""
        if not (self.objects and stage.selects):
            yield
            return
        token = SELECTED.set(frozenset(self.objects))
        try:
            yield
        finally:
            SELECTED.reset(token)

    def file_path(self, stage, name, place):
        pattern = self.files_of(stage, place)[name]
        pattern = pattern[0] if isinstance(pattern, tuple) else pattern
        return pathlib.Path(pattern.format(place=place, **self.world.roots))

    def file_keys(self, stage, place):
        """{name: content hash} of each environment file or seed folder the node reads; a missing one blocks. A file
        declared as (pattern, part) is keyed by part(path), the text of the part of it the stage reads (terrain
        reads only its ground's surfaces of the library), so a change elsewhere in the file moves no key."""
        keys = {}
        for name, pattern in self.files_of(stage, place).items():
            path = self.file_path(stage, name, place)
            if not path.exists():
                raise Blocked(f"{node_name(stage, place)}: its input {name} is missing ({path})")
            keys[name] = text_hash(pattern[1](path)) if isinstance(pattern, tuple) else source_hash(path)
        return keys

    def usable(self, before, place, wanted, gapped=False):
        """The output of an earlier node that passed its gates on its current evidence, that stands accepted, and
        whose stamp is the (schema, version) wanted; `gapped`: or that fails only on its accepted gaps (Stage.gapped)
        and the owner did not reject."""
        stage = self.stages[before]
        node = node_name(stage, place)
        key = self.key(stage, place)["key"]
        record = self.store.record(node, key)
        if record is None:
            raise Blocked(f"{node}{NOT_RUN}")
        judgement = self.store.judgement(node, key, self.evidence_state(stage, record["output"]))
        if judgement is None:
            raise Blocked(f"{node} is not judged on its current evidence")
        waived = self.store.waivers(node, key)
        on_gaps = gapped and review.fails_only_on_gaps(judgement["verdicts"], waived) and \
            not self.store.rejected(node, record["output"])
        if checks.blocks(checks.standing(judgement["verdicts"], waived)) and not on_gaps:
            reasons = "; ".join(f"{name}: {verdict['reason']}" for name, verdict in judgement["verdicts"].items()
                                if checks.blocks(verdict["answer"]) and name not in waived)
            raise Blocked(f"{node} answered {judgement['answer']}: {reasons}")
        accepted = self.store.accepted(node)
        if accepted != record["output"] and not on_gaps:
            raise Blocked(f"{node}'s output {record['output'][:12]} is not accepted"
                          + (f" (accepted: {accepted[:12]})" if accepted else ""))
        try:
            contracts.expect(wanted, self.store.read_file(record["output"], contracts.STAMP), node)
        except contracts.Mismatch as mismatch:
            raise Blocked(str(mismatch)) from mismatch
        return record["output"]

    def key(self, stage, place):
        """The node's key and everything it hashes; raises Blocked when an input is missing or not usable."""
        return self.remember("key", node_name(stage, place), lambda: self.worked_out_key(stage, place))

    def own_parts(self, stage, place):
        """The node's key parts that are not earlier nodes' outputs (its after and beside)."""
        return {"stage": stage.name, "grain": stage.grain, "place": place if stage.grain == "place" else None,
                "code": self.code(stage), "contract": stage.contract.stamp_of(),
                "expects": {before: list(wanted) for before, wanted in self.reads(stage, place).items()},
                "params": self.params_of(stage),
                "seed": node_seed(self.world.seed, stage.name, place if stage.grain == "place" else None),
                "files": self.file_keys(stage, place),
                "models": {kind: self.model_record(kind) for kind in stage.models}}

    def params_of(self, stage):
        """The stage's params, a callable one worked out from this runner (the library rows' route), with the object
        filter's sorted names as `objects` for a stage that selects."""
        params = {name: value(self) if callable(value) else value for name, value in stage.params.items()}
        if self.objects and stage.selects:
            return {**params, "objects": sorted(self.objects)}
        return params

    def worked_out_key(self, stage, place):
        """The node's key worked out from its inputs (`key`)."""
        parts = {**self.own_parts(stage, place),
                 "after": {before: self.usable(before, place, wanted, before in stage.gapped)
                           for before, wanted in self.reads(stage, place).items()}}
        beside = self.besides(stage, place)
        if beside:  # only a stage that reads beside has this part, so no other node's key moves
            parts["beside"] = {node: self.usable(before, other, wanted)
                               for node, (before, other, wanted) in beside.items()}
        key = text_hash(json.dumps(parts, sort_keys=True))
        note = self.store.read(f"{REMAKES}{node_name(stage, place)}/{key}.json")
        if note and note["then"] == "remake":  # only then a remake part: no other node's key moves
            failed = ", ".join(sorted(note["failed"]))
            parts = {**parts, "seed": node_seed(self.world.seed, f"{stage.name}#remake", parts["place"]),
                     "remake": {"attempt": 2, "after": key, "failed": sorted(note["failed"]),
                                "why": f"automatic free remake, attempt 2, after {failed}"}}
            key = text_hash(json.dumps(parts, sort_keys=True))
        return {**parts, "key": key}

    def besides(self, stage, place):
        """{node: (earlier stage, other place, (schema, version))} the node reads of other places (its `beside`, for
        each of its neighbours). An environment stage's neighbours(None) names the places it reads (the environment's
        film reads the films its script shows), each only for an earlier stage that applies there."""
        if not stage.beside or (place is None and stage.grain != "world"):
            return {}
        return {node_name(self.stages[before], other): (before, other, wanted)
                for other in stage.neighbours(place) for before, wanted in stage.beside.items()
                if place is not None or self.stages[before].applies is None or self.stages[before].applies(other)}

    def reads(self, stage, place, every=False):
        """{earlier stage: (schema, version)} the node reads: its `after`, less a place stage that has nothing to do
        for this place (its `applies`), which the node then reads without, and less an optional read not usable now
        (`every`: with it, every read it takes once all it may read is made)."""
        found = {before: wanted for before, wanted in stage.after.items()
                 if place is None or self.stages[before].applies is None or self.stages[before].applies(place)}
        return {before: wanted for before, wanted in found.items()
                if every or before not in stage.optional or self.usable_now(before, place, wanted)}

    def optional_nodes(self, stage, place):
        """The nodes of the node's optional reads (every one that applies, usable or not)."""
        return [node_name(self.stages[before], place) for before in self.reads(stage, place, every=True)
                if before in stage.optional]

    def usable_now(self, before, place, wanted):
        """True when an earlier node's output is usable (`usable`) now."""
        try:
            self.usable(before, place, wanted)
        except Blocked:
            return False
        return True

    def evidence_state(self, stage, output):
        """The hash of every check's evidence on an output ("none" for a check that needs none)."""
        state = {check.name: (self.store.evidence_hash(check.name, output) or "missing") if check.evidence else "none"
                 for check in stage.checks}
        return text_hash(json.dumps(state, sort_keys=True))

    # --- making and judging ------------------------------------------------------------------------------------

    def input_paths(self, stage, place, keyed):
        """{name: path} the stage's make reads: environment files in place, earlier outputs checked out."""
        paths = {name: self.file_path(stage, name, place) for name in self.files_of(stage, place)}
        paths.update({before: self.store.checkout(output) for before, output in keyed["after"].items()})
        paths.update({node: self.store.checkout(output) for node, output in keyed.get("beside", {}).items()})
        return paths

    def spending(self, stage, node, inputs):
        """For a paid stage, its clearance's ticket named for the rent points while it makes (at the stage's own
        forecast of its `inputs` where it has one); else nothing."""
        if not stage.paid:
            return contextlib.nullcontext()
        if stage.forecast:
            return self.cleared(node, stage.euros, lambda: stage.forecast(inputs))
        return self.cleared(node, stage.euros)

    def cleared(self, node, euros, forecast=None):
        """The node's clearance at `euros` (or at what `forecast()` gives, the stage's own forecast), named for the
        rent points while the block runs; Blocked when refused, and always in a free-only run (a paid gatherer of a
        free node), before the clearance is asked."""
        if self.free_only and on_this_pc():
            return contextlib.nullcontext()  # THIS_PC: no ticket, so only this PC's card is free to it
        if self.free_only:
            raise Blocked(f"{node}: a paid step ({euros} EUR) is not cleared in a free-only run: left for the Buy")
        from score.adapters import compute  # here: compute imports this module for its tickets
        try:
            return compute.spending(compute.clearance(self, node, euros, forecast() if forecast else None))
        except compute.Refused as refusal:
            raise Blocked(str(refusal)) from refusal

    @contextlib.contextmanager
    def held(self, node, key):
        """The lock of one node's key (or of one piece of its evidence) across every run on this store, held while
        the block runs: a file lock the system lets go of when its process dies. A run that finds it held waits;
        held past LOCK_WAIT, Blocked, naming the holder."""
        path = self.desk("locks", f"{node}/{key}", ".lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+") as lock:
            deadline = time.monotonic() + LOCK_WAIT
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        lock.seek(0)
                        raise Blocked(f"{node}: another run has held its lock over {LOCK_WAIT} s "
                                      f"({lock.read().strip() or 'holder unknown'}); not made again here") from None
                    time.sleep(LOCK_POLL)
            lock.truncate(0)
            lock.write(f"pid {os.getpid()} on {platform.node()} since {now()}\n")
            lock.flush()
            yield

    def make(self, stage, place, keyed):
        """Make the node's output, store it and write its finish record; the record (another run's, when one stored
        this key first: it is taken as made)."""
        node = node_name(stage, place)
        inputs = self.input_paths(stage, place, keyed)
        cleared = self.spending(stage, node, inputs)
        out = self.store.making(keyed["key"])
        started, clock = now(), time.monotonic()
        try:
            with cleared, making_in(out):
                stage.make(inputs, out, keyed["seed"], keyed["params"])
            if self.file_keys(stage, place) != keyed["files"]:
                raise RuntimeError(f"{node}: an input changed while it ran; nothing is stored")
            self.unchanged_checkouts(node, inputs, keyed)
            contracts.stamp(stage.contract, out)
            output = self.store.put_tree(out)
        finally:
            gone(out)
        self.drop_kept(node, keyed["key"])
        return self.write_finish(node, keyed, finish_record(node, keyed, output, stage.name, started, clock))

    def write_finish(self, node, keyed, record):
        """Store a node's finish record; the record that stands (another run's, when one stored this key first)."""
        try:
            self.store.write_record(node, keyed["key"], record)
        except FileExistsError:  # another run (one not taking the lock) stored this key first: its record stands
            return self.store.record(node, keyed["key"])
        return record

    def drop_kept(self, node, key):
        """Remove the jobs kept for an earlier try of this key (tools/cloud/kept.py): its output is stored."""
        folder = self.store.cache.parent / "kept" / node / key
        if folder.exists():
            shutil.rmtree(folder)

    def unchanged_checkouts(self, node, inputs, keyed):
        """Raise when the make wrote into an earlier output's read-only checkout (light@camp saved over its input,
        2026-10-12): every other node reading that checkout would read the changed copy."""
        outputs = {**keyed["after"], **keyed.get("beside", {})}
        changed = sorted(name for name, output in outputs.items()
                         if tree_listing(inputs[name]) != self.store.listing(output))
        if changed:
            raise RuntimeError(f"{node}: its make wrote into its read-only input {', '.join(changed)} (write only "
                               "into the output folder); nothing is stored")

    def judge(self, stage, place, record):
        """Judge a stored output with the stage's gates on their current evidence and keep the judgement."""
        output = self.store.checkout(record["output"])
        inputs = self.input_paths(stage, place, record)
        verdicts = [checks.judge(check, output, inputs, self.store.evidence_file(check.name, record["output"]))
                    for check in stage.checks]
        judgement = {"node": record["node"], "key": record["key"], "output": record["output"],
                     "evidence": self.evidence_state(stage, record["output"]), "at": now(),
                     "answer": checks.overall(verdicts), "verdicts": checks.scorecard(verdicts)}
        try:
            self.store.write_judgement(record["node"], record["key"], judgement["evidence"], judgement)
        except FileExistsError:  # another run judged it first: its judgement stands
            return self.store.judgement(record["node"], record["key"], judgement["evidence"])
        return judgement

    def run_node(self, stage, place):
        """Make the node if its key has no record, judge it if its evidence state has no judgement, accept it when it
        passed and got no worse; what it did. It holds the node's key's lock throughout, so of two runs wanting one
        key the second waits and finds the first's record."""
        try:
            keyed = self.key(stage, place)
            with self.held(node_name(stage, place), keyed["key"]):
                did = self.run_held(stage, place, keyed)
        except Blocked as block:
            return f"blocked: {block}"
        return self.after_failure(stage, place, keyed, did)

    def after_failure(self, stage, place, keyed, did):
        """Once the node's output failed its gates (fail, the owner's waivers counted; not unknown, not only its
        accepted gaps, not accepted): noted, then made once more with a fresh seed when that is free here (its key's
        `remake` part, run at once), else on the owner's list, priced; attempt 2's outcome is noted too, a failure
        on his list. What it did."""
        failed, answer = self.failed_checks(stage, place, keyed)
        second = "remake" in keyed
        if not failed:
            if second and answer == checks.PASS:
                self.note(stage, place, keyed, {}, "done")
            return did
        free = (not stage.paid and not any(euros for _, euros in stage.gatherers.values())) or on_this_pc()
        then = "fix" if not second and asks_cached(stage) else "remake" if free and not second else "owner"
        if not self.note(stage, place, keyed, failed, then):
            return did  # noted by an earlier run: its remake, or the owner's list, has it
        if then == "fix":
            return f"{did}; {SAME_ANSWER}"
        if then == "owner":
            return f"{did}; {'the second failure' if second else 'a paid remake'}: on the owner's list, priced"
        return f"{did}; automatic free remake, attempt 2, after {', '.join(sorted(failed))}: " \
               f"{self.run_node(stage, place)}"

    def failed_checks(self, stage, place, keyed):
        """({check: verdict} of the node's output's failed checks when its answer on its current evidence is fail,
        the owner's waivers counted, and it neither stands accepted nor fails only on its accepted gaps, else {};
        that answer, or None when it is not judged)."""
        node = node_name(stage, place)
        record = self.store.record(node, keyed["key"])
        judgement = record and self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"]))
        if not judgement:
            return {}, None
        waived = self.store.waivers(node, keyed["key"])
        answer = checks.standing(judgement["verdicts"], waived)
        if answer != checks.FAIL or review.fails_only_on_gaps(judgement["verdicts"], waived) or \
                self.store.accepted(node) == record["output"]:
            return {}, answer
        return {name: verdict for name, verdict in judgement["verdicts"].items()
                if verdict["answer"] == checks.FAIL and name not in waived}, answer

    def note(self, stage, place, keyed, failed, then):
        """Note one failed output (or attempt 2's outcome) once: in the store under its key (REMAKES), then a line of
        the remake log and, for `then` "owner", of the owner's list, priced; False when it was noted already."""
        node = node_name(stage, place)
        entry = {"node": node, "key": keyed["key"], "attempt": 2 if "remake" in keyed else 1, "at": now(),
                 "output": self.store.record(node, keyed["key"])["output"], "then": then,
                 "failed": {name: {part: verdict[part] for part in ("reason", "measures", "findings")}
                            for name, verdict in failed.items()}}
        if "remake" in keyed:
            entry["first"] = keyed["remake"]["after"]
        if then == "fix":
            entry["why"] = SAME_ANSWER
        if then == "owner":
            entry["euros"] = self.price(stage, place, keyed)
            entry["why"] = "both attempts failed" if "remake" in keyed else "its remake is paid"
        try:
            self.store.write_once(f"{REMAKES}{node}/{keyed['key']}.json", entry)
        except FileExistsError:
            return False
        for desk in (REMAKE_LOG, OWNER_LIST)[:2 if then == "owner" else 1]:
            path = self.desk(*desk)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as lines:
                lines.write(json.dumps(entry, sort_keys=True) + "\n")
        return True

    def price(self, stage, place, keyed):
        """The node's forecast price in euros: its own forecast of its inputs, else its row's estimate (0, free)."""
        if stage.forecast:
            return stage.forecast(self.input_paths(stage, place, keyed))["euros"]
        return stage.euros or 0.0

    def run_held(self, stage, place, keyed):
        """`run_node` under the node's key's lock."""
        node = node_name(stage, place)
        record = self.store.record(node, keyed["key"])
        keeps = "remake" not in keyed  # a remake is made, never its accepted output kept
        if keeps and record is None and hasattr(stage.files, "carried"):  # its accepted output, its inputs the same
            record = stage.files.carried(self, stage, place, keyed)
        if keeps and record is None:  # its accepted output, kept when only bytecode moved its key (#67)
            record = self.kept_over_bytecode(stage, place, keyed)
        if keeps and record is None:  # its accepted output, kept when every file its key reads today reads as then
            record = self.kept_by_narrowing(stage, place, keyed)
        if keeps and record is None:  # its accepted output, kept when a stored proof says every change is a no-op
            record = self.kept_by_proof(stage, place, keyed)
        made = record is None
        if made:
            try:
                record = self.make(stage, place, keyed)
            except contracts.Broken as broken:
                return f"broken: {broken}"
        if self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"])) is not None:
            done = "fresh"
        else:
            judgement = self.judge(stage, place, record)
            done = f"{'made' if made else 'judged again, output kept'}: {judgement['answer']}"
        if self.store.accepted(node) == record["output"]:
            return done
        newer = self.newer_accepted(node, keyed["key"])
        if newer:
            return f"{done}, not accepted: {newer}"
        judged = review.newest_judgement(self.store, record)
        against = self.rejudged_accepted(stage, place) if judged and (judged["answer"] == checks.PASS or (
            review.fails_only_on_gaps(judged["verdicts"], self.store.waivers(node, keyed["key"])))) else None
        accepted = review.accept_automatically(self.store, node, record["output"], against, self.bought)
        return f"{done}, accepted automatically" if accepted else done

    def rejudged_accepted(self, stage, place):
        """The accepted output's scorecard judged now, by today's gates on today's environment files (its accepted gaps among
        them, so a gap moves the same faults on both sides), not kept: what a new output is compared with, so both
        are measured alike (assembly@lab, 2026-10-15: its accepted output was judged on 10-11 before the triage asked
        each foot, so the chairs' caster read as two new faults). None when nothing is accepted."""
        node = node_name(stage, place)
        accepted = self.store.accepted(node)
        record = review.record_of(self.store, node, accepted) if accepted else None
        if record is None:
            return None
        output = self.store.checkout(accepted)
        inputs = self.input_paths(stage, place, record)
        stored = review.newest_judgement(self.store, record)
        card = {}
        for check in stage.checks:
            try:
                card.update(checks.scorecard([checks.judge(check, output, inputs,
                                                           self.store.evidence_file(check.name, accepted))]))
            except Exception as error:  # a gate newer than the output's own schema: its stored verdict stands
                if stored and check.name in stored["verdicts"]:
                    card[check.name] = {**stored["verdicts"][check.name],
                                        "not judged again": f"{type(error).__name__}: {error}"}
        return card

    def bytecode_proof(self, stage, place, keyed):
        """{file name: its recorded hash, its sources' hash at the record's commit and now} when the node's accepted
        output differs from `keyed` only by bytecode in declared repository files (#67: keys hashed each checkout's
        __pycache__ until 2026-10-13): a record of a committed tree, every other key part the same, and each file
        that moved, rebuilt from git at the record's commit, hashing as it does now. None otherwise."""
        node = node_name(stage, place)
        accepted = self.store.accepted(node)
        record = review.record_of(self.store, node, accepted) if accepted else None
        if record is None or record.get("uncommitted", True) or not record.get("commit"):
            return None
        if any(record.get(part) != keyed.get(part) for part in ("code", "contract", "expects", "params", "seed",
                                                                 "models", "after", "beside")):
            return None
        if set(record["files"]) != set(keyed["files"]):
            return None
        proof = {}
        for name in sorted(name for name in keyed["files"] if record["files"][name] != keyed["files"][name]):
            path = self.file_path(stage, name, place).resolve()
            if isinstance(self.files_of(stage, place)[name], tuple) or not path.is_relative_to(_code.REPO):
                return None
            then = _code.source_hash_at(record["commit"], path.relative_to(_code.REPO).as_posix())
            if then != keyed["files"][name]:
                return None
            proof[name] = {"recorded": record["files"][name], "at its commit": then, "now": keyed["files"][name]}
        return {"record": record, "files": proof} if proof else None

    def kept_over_bytecode(self, stage, place, keyed):
        """The node's accepted output stored under `keyed` when only bytecode moved its key (bytecode_proof): its
        record and judgements copied, the record naming the reason, both keys, the commit that made it and the proof.
        Its new record, or None (the runner then makes the node)."""
        proved = self.bytecode_proof(stage, place, keyed)
        if proved is None:
            return None
        node, record = node_name(stage, place), proved["record"]
        new = {**record, "key": keyed["key"], "files": keyed["files"],
               "carried": {"reason": BYTECODE_REASON, "from key": record["key"], "to key": keyed["key"],
                           "made by": {"commit": record["commit"], "code": record["code"]},
                           "sources": proved["files"]}}
        try:
            self.store.write_record(node, keyed["key"], new)
        except FileExistsError:  # another run kept it first
            return self.store.record(node, keyed["key"])
        for judgement in self.store.judgements(node, record["key"]):
            self.store.write_judgement(node, keyed["key"], judgement["evidence"],
                                       {**judgement, "key": keyed["key"], "carried": new["carried"]})
        return new

    def changes_since(self, stage, place, keyed):
        """(the accepted output's record, the repository files changed since its commit that moved its key) when
        only its code and declared repository files moved: a record of a committed tree, every other key part the
        same. None otherwise, or when no changed file accounts for the move."""
        node = node_name(stage, place)
        accepted = self.store.accepted(node)
        record = review.record_of(self.store, node, accepted) if accepted else None
        if record is None or record.get("uncommitted", True) or not record.get("commit"):
            return None
        if any(record.get(part) != keyed.get(part) for part in ("contract", "expects", "params", "seed", "models",
                                                                 "after", "beside")):
            return None
        if set(record["files"]) != set(keyed["files"]):
            return None
        paths = []
        if record["code"] != keyed["code"]:
            paths += [str(path.relative_to(_code.REPO)) for path in _code.source_files(code_functions(stage))]
        for name in keyed["files"]:
            if record["files"][name] != keyed["files"][name]:
                path = self.file_path(stage, name, place).resolve()
                if not path.is_relative_to(_code.REPO):
                    return None
                paths.append(path.relative_to(_code.REPO).as_posix())
        changed = _code.changed_since(record["commit"], paths) if paths else []
        return (record, changed) if changed else None

    def no_op_proof(self, stage, place, keyed):
        """The stored proof that the node's code and file changes since its accepted output leave its result as it
        is: JSON stored as evidence on the output under check `no-op-<new key>` ({"from key": the record's key, "to
        key": the new key, "no-ops": {changed file: why its change leaves this node's result as it was}}), naming
        every changed file (changes_since). {"record", "changed", "proof", "check"} when it holds, else None."""
        found = self.changes_since(stage, place, keyed)
        if found is None:
            return None
        record, changed = found
        check = f"no-op-{keyed['key']}"
        path = self.store.evidence_file(check, record["output"])
        if path is None:
            return None
        proof = json.loads(pathlib.Path(path).read_text())
        if proof.get("from key") != record["key"] or proof.get("to key") != keyed["key"]:
            return None
        if any(not str(proof.get("no-ops", {}).get(name, "")).strip() for name in changed):
            return None
        return {"record": record, "changed": changed, "proof": proof, "check": check}

    def kept_by_proof(self, stage, place, keyed):
        """The node's accepted output stored under `keyed` when a stored proof says its changes are no-ops for it
        (no_op_proof): its record and judgements copied, the record naming both keys, the commit and code that made
        it and the proof. Its new record, or None (the runner then makes the node)."""
        proved = self.no_op_proof(stage, place, keyed)
        if proved is None:
            return None
        node, record = node_name(stage, place), proved["record"]
        new = {**record, "key": keyed["key"], "code": keyed["code"], "files": keyed["files"],
               "carried": {"reason": NO_OP_REASON, "from key": record["key"], "to key": keyed["key"],
                           "made by": {"commit": record["commit"], "code": record["code"]},
                           "proof": self.store.evidence_key(proved["check"], record["output"]),
                           "no-ops": {name: proved["proof"]["no-ops"][name] for name in proved["changed"]}}}
        try:
            self.store.write_record(node, keyed["key"], new)
        except FileExistsError:  # another run kept it first
            return self.store.record(node, keyed["key"])
        for judgement in self.store.judgements(node, record["key"]):
            self.store.write_judgement(node, keyed["key"], judgement["evidence"],
                                       {**judgement, "key": keyed["key"], "carried": new["carried"]})
        return new

    def narrowed(self, stage, place, keyed):
        """(the node's accepted output's record, the files it reads only reworded since) when its key only got
        narrower, or its code changed only in words (comments, blank lines, layout, docstrings: _code.words_only): a
        record of a committed tree, every key part but code and files the same, the code version rebuilt from git at the record's commit (today's
        start files followed with that commit's FRAMEWORK, after this Python's version) equal to the record's, today's
        code version a part of it (each file today reads, the Python version too, read as it was then, or a Python file
        only reworded since), and each
        declared file hashing as recorded (a repository one: or as git rebuilds it at that commit). A module moved
        into FRAMEWORK, or an import dropped by a file that was itself not read, is kept so, with no proof file; a
        make, check or file map wired to another function, or another Python, is not. Each file the key no longer reads
        (the moved module, and what was read only through it) must still be in the tree and read as it did then, so a
        module moved and edited in one change is made again. A record kept so before is judged against what made it
        (its carried "made by"), so plumbing moved over several commits keeps it each time. None otherwise."""
        node = node_name(stage, place)
        accepted = self.store.accepted(node)
        record = review.record_of(self.store, node, accepted) if accepted else None
        if record is None or record.get("uncommitted", True) or not record.get("commit"):
            return None
        made = made_by(record)
        if any(record.get(part) != keyed.get(part) for part in NARROWING_SAME):
            return None
        if set(record["files"]) != set(keyed["files"]):
            return None
        for name in sorted(name for name in keyed["files"] if record["files"][name] != keyed["files"][name]):
            path = self.file_path(stage, name, place).resolve()
            if isinstance(self.files_of(stage, place)[name], tuple) or not path.is_relative_to(_code.REPO):
                return None
            if _code.source_hash_at(made["commit"], path.relative_to(_code.REPO).as_posix()) != keyed["files"][name]:
                return None
        then = _code.code_version_at(made["commit"], code_functions(stage))
        if then is None or listing_hash(then) != made["code"]:
            return None
        now = _code.code_version(code_functions(stage), file_hash)
        reads = {entry.rsplit(" ", 1)[0] for entry in now}
        reworded = sorted(reads - {entry.rsplit(" ", 1)[0] for entry in set(now) & set(then)})
        if not {entry.rsplit(" ", 1)[0] for entry in then} >= reads or \
                reworded and not _code.words_only(made["commit"], reworded, reads):
            return None
        dropped = {entry for entry in then if entry.rsplit(" ", 1)[0] not in reads}
        return (record, reworded) if _code.unchanged(dropped, file_hash) else None

    def narrowing_proof(self, stage, place, keyed):
        """The node's accepted output's record when its key only got narrower or its code was only reworded
        (narrowed), else None."""
        found = self.narrowed(stage, place, keyed)
        return found and found[0]

    def kept_by_narrowing(self, stage, place, keyed):
        """The node's accepted output stored under `keyed` when every file its key reads today reads as it did when
        that output was made, or differs from then only in words (narrowed): its record and judgements copied, the
        record naming the reason, both keys, the commit and code that made it and any file only reworded. Its new
        record, or None (the runner then makes the node)."""
        found = self.narrowed(stage, place, keyed)
        if found is None:
            return None
        record, reworded = found
        node = node_name(stage, place)
        new = {**record, "key": keyed["key"], "code": keyed["code"], "files": keyed["files"],
               "carried": {"reason": WORDS_REASON if reworded else NARROWING_REASON, "from key": record["key"],
                           "to key": keyed["key"], "made by": made_by(record),
                           **({"words only": reworded} if reworded else {})}}
        try:
            self.store.write_record(node, keyed["key"], new)
        except FileExistsError:  # another run kept it first
            return self.store.record(node, keyed["key"])
        for judgement in self.store.judgements(node, record["key"]):
            self.store.write_judgement(node, keyed["key"], judgement["evidence"],
                                       {**judgement, "key": keyed["key"], "carried": new["carried"]})
        return new

    def newer_accepted(self, node, key):
        """Why this run must not accept over the node's accepted output: it was made under another key by a commit
        this checkout does not hold (a runner in an older worktree accepted terrain's old output over the new one,
        2026-10-12); None when the accepted output has this key, or was made by this commit or one before it."""
        accepted = self.store.accepted(node)
        records = [record for record in self.store.records(node) if record["output"] == accepted]
        if not records or any(record["key"] == key for record in records):
            return None
        commits = [record.get("commit") for record in records]
        if any(commit and _code.holds(commit) for commit in commits):
            return None
        return (f"key differs from the accepted one ({accepted[:12]}, made at commit "
                f"{(commits[-1] or 'unknown')[:8]}, which this checkout does not hold); pull main")

    def nodes(self, places):
        """Every (stage, place) in table order: an environment stage once, a place stage once per place."""
        for stage in self.stages.values():
            for place in ([None] if stage.grain == "world" else places):
                if place is None or stage.applies is None or stage.applies(place):
                    yield stage, place

    def missing_inputs(self, nodes):
        """Every declared input a run could never make itself that is missing, of the `nodes` it plans: its environment data
        and repository files ({data}, {repo}; a bake's job and entries are declared there), each as "node: input
        (path)". A run refuses on any, before anything starts (the ship run of 2026-10-14 22:55 spent EUR 13.58 on
        machines, then stopped on missing seed records). Files the run makes as it goes (the Pixal3D takes under {home}) are left to their rows."""
        found = []
        for stage, place in nodes:
            try:
                declared = self.files_of(stage, place)
            except (OSError, KeyError, ValueError) as unreadable:  # its data names nothing it can list: say so
                found.append(f"{node_name(stage, place)}: its world files cannot be listed ({unreadable})")
                continue
            for name, pattern in declared.items():
                pattern = pattern[0] if isinstance(pattern, tuple) else pattern
                if not pattern.startswith(("{data}", "{repo}")):
                    continue
                path = self.file_path(stage, name, place)
                if not path.exists():
                    found.append(f"{node_name(stage, place)}: {name} ({path})")
        return found

    def line_nodes(self, places, whole, only=None):
        """The nodes a drive runs: every one of `nodes` for the whole environment, else the places' own and only the environment
        nodes they read (directly or through another environment node); `only` (stage names) keeps those stages' nodes and
        the nodes they read, place by place: a stage one place reads (the garage's motion its motion models layer, and so
        its surface line) is not run for a place that does not read it. A node name in `only` (`demo-film@hub`) keeps
        that one node, so one run can hold a benchmark batch of different stages at different places. An environment
        stage named in `only` with places given is kept too, with what it reads: `--place people --stage people-look-<look>`
        is the people line and the bodies that read it beside, in one run (#26). Every node a chosen node reads, its
        optional reads too (usable now or not: a Buy makes them, the characters layer's people), is in the run, a line
        no place given owns (the people's) with it, whole or not."""
        found = list(self.nodes(places))
        named = set()
        if only:
            reading = [(stage, place) for stage, place in found
                       if stage.name in only or node_name(stage, place) in only]
            names = {node_name(*node) for node in reading}
            named = set(names)
            while reading:
                for before in self.read_nodes(*reading.pop(), every=True):
                    if node_name(*before) not in names:
                        names.add(node_name(*before))
                        reading.append(before)
            found = [(stage, place) for stage, place in found if node_name(stage, place) in names]
        chosen = found if whole else [(stage, place) for stage, place in found
                                      if stage.grain == "place" or node_name(stage, place) in named]
        names, reading = {node_name(*node) for node in chosen}, list(chosen)
        while reading:  # the environment nodes and other places' nodes the places read, and what those read
            for before in self.read_nodes(*reading.pop(), every=True):
                if node_name(*before) not in names:
                    names.add(node_name(*before))
                    reading.append(before)
        others = sorted({place for stage, place in self.nodes_named(names)} - {None} - set(places))
        return [node for node in self.nodes([*places, *others]) if node_name(*node) in names]

    def nodes_named(self, names):
        """(stage, place) of each node name."""
        for name in names:
            stage_name, _, place = name.partition("@")
            yield self.stages[stage_name], place or None

    def read_nodes(self, stage, place, every=False):
        """(stage, place) of every node this node reads: its own place's or the environment's, and other places'
        (`every`: its optional reads too, usable now or not, Runner.reads); once a `still` pass (a price walks each
        node's reads from every chain through it)."""
        def worked_out():
            own = [(self.stages[before], place if self.stages[before].grain == "place" else None)
                   for before in self.reads(stage, place, every)]
            return own + [(self.stages[before], other) for before, other, _ in self.besides(stage, place).values()]
        return list(self.remember(("read nodes", every), node_name(stage, place), worked_out))

    def run(self, places):
        """Run every node in table order; {node: what it did}."""
        return {node_name(stage, place): self.run_node(stage, place) for stage, place in self.nodes(places)}

    # --- driving lines -----------------------------------------------------------------------------------------

    def desk(self, area, node, suffix):
        """A node's file in one of the runner's own areas beside the store (faults, logs)."""
        return self.store.cache.parent / area / f"{node}{suffix}"

    def earlier(self, stage, place):
        """The nodes this node reads."""
        return [node_name(self.stages[before], place) for before in self.reads(stage, place)] + list(
            self.besides(stage, place))

    def gatherable(self, stage, place):
        """The checks whose missing evidence the runner can gather, when they alone keep the node from passing (none
        when another check blocks, or the node has no judgement on its current key)."""
        node = node_name(stage, place)
        keyed = self.key(stage, place)
        record = self.store.record(node, keyed["key"])
        judgement = record and self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"]))
        if not judgement:
            return []
        waived = self.store.waivers(node, keyed["key"])
        blocking = {name for name, verdict in judgement["verdicts"].items()
                    if checks.blocks(verdict["answer"]) and name not in waived}
        missing = {name for name in stage.gatherers if self.store.evidence_hash(name, record["output"]) is None}
        return sorted(blocking) if blocking and blocking <= missing else []

    def gather(self, stage, place, wanted):
        """Make each wanted check's evidence on the node's output (a paid one inside its clearance) and store it."""
        node = node_name(stage, place)
        keyed = self.key(stage, place)
        output = self.store.record(node, keyed["key"])["output"]
        for name in wanted:
            with self.held(node, f"evidence-{name}-{output}"):
                if self.store.evidence_hash(name, output) is None:  # else another run gathered it while this waited
                    self.gather_one(stage, place, keyed, name, output)

    def gather_one(self, stage, place, keyed, name, output):
        """Make one check's evidence on the node's output and store it (another run's, stored first, stands)."""
        gather, euros = stage.gatherers[name]
        folder = self.store.making(f"evidence-{name}-{output}")
        try:
            with self.cleared(node_name(stage, place), euros) if euros else contextlib.nullcontext():
                found = gather(self.store.checkout(output), self.input_paths(stage, place, keyed), folder)
            with contextlib.suppress(FileExistsError):  # another run stored it first: its evidence stands
                self.store.put_evidence(name, output, found)
        finally:
            gone(folder)

    def drive_node(self, stage, place, threads):
        """Run one node, its thread pools capped at `threads` first, gathering the evidence it lacks and judging it
        again; what it did. Its output, a raised error's traceback included (a failed cap's too), goes to its log."""
        log = self.desk("logs", node_name(stage, place), ".log")
        log.parent.mkdir(parents=True, exist_ok=True)
        with logged(log):
            try:
                cap_threads(threads)
                did = self.run_retrying(stage, place)
                wanted = [] if did.startswith(("blocked", "broken")) else self.gatherable(stage, place)
                if wanted:
                    self.gather(stage, place, wanted)
                    did = f"{did}; gathered {', '.join(wanted)}: {self.run_retrying(stage, place)}"
                return did
            except (Exception, SystemExit) as error:  # noqa: BLE001 - a SystemExit too
                traceback.print_exc()
                return f"error: {type(error).__name__}: {error}"

    def run_retrying(self, stage, place):
        """run_node; a free stage's transient error (`transient`) runs it again up to RETRIES times with growing
        waits, a paid stage's goes up at once (ADR-0005)."""
        for attempt in range(RETRIES + 1):
            try:
                return self.run_node(stage, place)
            except Exception as error:  # noqa: BLE001 - one not transient, or the last try's, goes up as it was
                if stage.paid or attempt == RETRIES or not transient(error):
                    raise
                wait = RETRY_WAIT * 2 ** attempt
                traceback.print_exc()
                print(f"transient error, try {attempt + 2} of {RETRIES + 1} in {wait} s", flush=True)
                time.sleep(wait)

    def standing(self, stage, place, gapped=False):
        """None when the node's current output passed and stands accepted (`gapped`: or fails only on its accepted
        gaps); else why not."""
        try:
            self.usable(stage.name, place, (stage.contract.schema, stage.contract.version), gapped)
        except Blocked as block:
            return str(block)
        return None

    def fault_report(self, stage, place, did, cause):
        """Write the node's plain fault report (what it did, why its line stopped, every blocking check's reason,
        measures and findings, its log's tail); its path."""
        node = node_name(stage, place)
        line = place or WORLD_LINE
        lines = [f"fault: {node} (line {line}, world {self.world.name}, {now()})", f"what the runner did: {did}",
                 f"why its line stopped: {cause}", ""]
        lines += self.moved_inputs(cause)
        lines += self.blocking_checks(stage, place)
        lines += self.remake_lines(stage, place)
        log = self.desk("logs", node, ".log")
        tail = log.read_text(errors="replace").splitlines()[-LOG_TAIL:] if log.exists() else []
        lines += [f"log: {log} (its last {len(tail)} lines)", *(f"  | {text}" for text in tail), "",
                  f"its records: python -m score.stages why {node}",
                  f"to go on once the cause is put right: python -m score run {self.world.name}"
                  + (f" --place {place}" if place else "")]
        path = self.desk("faults", node, ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
        return path

    def moved_inputs(self, cause):
        """Report lines naming what moved an earlier node's key since its last record, when that is why the line stopped
        (Batch 1 try 4, 2026-10-25: twenty lines stopped on "finish-route-palette@<place> has not run on its current
        inputs" and nothing said a sync pass had rewritten the design under the run)."""
        if not cause.endswith(NOT_RUN):
            return []
        stage, place = next(self.nodes_named([cause[:-len(NOT_RUN)]]))
        try:
            keyed = self.key(stage, place)
        except Blocked as block:
            return [f"its key cannot be worked out: {block}", ""]
        return [f"what moved its key since its last record: {', '.join(self.stale_reasons(stage, place, keyed))}", ""]

    def remake_lines(self, stage, place):
        """Report lines of the node's failed attempts (its key's notes, REMAKES) and where an owner's one went."""
        node = node_name(stage, place)
        try:
            keyed = self.key(stage, place)
        except Blocked:
            return []
        keys = ([keyed["remake"]["after"]] if "remake" in keyed else []) + [keyed["key"]]
        notes = [note for key in keys if (note := self.store.read(f"{REMAKES}{node}/{key}.json"))]
        lines = [f"attempt {note['attempt']} (key {note['key'][:12]}, output {note['output'][:12]}) failed "
                 f"{', '.join(sorted(note['failed']))}: then {note['then']}" for note in notes if note["failed"]]
        if notes and notes[-1]["then"] == "fix":
            lines.append(SAME_ANSWER)
        if notes and notes[-1]["then"] == "owner":
            lines.append(f"{notes[-1]['why']}: on the owner's list, priced EUR {notes[-1]['euros']:.2f} "
                         f"({self.desk(*OWNER_LIST)})")
        return lines + [""] if lines else []

    def blocking_checks(self, stage, place):
        """The node's newest judgement's blocking checks as report lines: answer, reason, measures, findings."""
        node = node_name(stage, place)
        try:
            key = self.key(stage, place)["key"]
        except Blocked:
            return []
        judgements = self.store.judgements(node, key)
        if not judgements:
            return []
        waived = self.store.waivers(node, key)
        lines = [f"checks ({judgements[-1]['answer']}, output {judgements[-1]['output'][:12]}):"]
        for name, verdict in judgements[-1]["verdicts"].items():
            if not checks.blocks(verdict["answer"]) or name in waived:
                continue
            lines += [f"  {name}: {verdict['answer']}: {verdict['reason']}",
                      f"    measures: {json.dumps(verdict['measures'], sort_keys=True)}",
                      *(f"    - {finding}" for finding in verdict["findings"])]
        return lines + [""]

    def start(self, stage, place, threads):
        """Start one node in a process of its own (forked: its output goes to its own log), its thread pools and its
        children's capped at `threads`; {its result pipe: (stage, place, process)}."""
        receiving, sending = FORK.Pipe(duplex=False)
        sys.stdout.flush()
        sys.stderr.flush()
        process = FORK.Process(target=self.node_process, args=(stage, place, sending, os.getpid(), threads),
                               name=node_name(stage, place))
        process.start()
        self.began[node_name(stage, place)] = time.time()
        sending.close()
        return {receiving: (stage, place, process)}

    def node_process(self, stage, place, sending, runner_pid, threads):
        """In the node's own process: drive it, its thread pools capped at `threads`, send back what it did and end
        the process at once: a thread its make left running (a library's pool, a read that never returns) would
        otherwise hold the process at its exit, and the drive's join with it, after the node is done. Its runner's
        death ends it (watch_runner)."""
        threading.Thread(target=watch_runner, args=(runner_pid,), daemon=True).start()
        high = [0, False]  # the most this node's process tree held, and whether it ran a container client
        threading.Thread(target=watch_memory, args=(high,), daemon=True).start()
        try:
            did = self.drive_node(stage, place, threads)
        except BaseException as error:  # noqa: BLE001 - raised where its log could not take it (Batch 1, a full disk)
            did = f"error: {type(error).__name__}: {error}; raised outside its log:\n{traceback.format_exc()}"
        sending.send((did, max(high[0], HELD([os.getpid()])[os.getpid()]),
                      high[1] or ran_container_client(os.getpid())))
        sending.close()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

    def outcome(self, receiving, process):
        """(What a node's process did, once it ended: an error when it ended without saying; the most bytes its
        process tree held (trees_held) as it said, 0 when it did not say; whether its tree ran a container client)."""
        try:
            did, peak, contained = receiving.recv()
        except EOFError:
            did, peak, contained = None, 0, False
        receiving.close()
        process.join()
        return (did or f"error: its process ended (exit code {process.exitcode}) without saying what it did", peak,
                contained)

    def peaks(self):
        """{stage: the most bytes one of its nodes' process trees held (trees_held)}, as kept beside the store (none
        yet: {})."""
        path = self.desk("memory", "peaks-made", ".json")
        return json.loads(path.read_text()) if path.exists() else {}

    def keep_peak(self, stage, peak):
        """Keep `peak` bytes as the stage's peak when it is more than the one kept; the peaks kept."""
        peaks = self.peaks()
        if peak > peaks.get(stage, 0):
            peaks[stage] = peak
            path = self.desk("memory", "peaks-made", ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            spare = path.with_suffix(f".{os.getpid()}")
            spare.write_text(json.dumps(peaks, indent=1, sort_keys=True) + "\n")
            os.replace(spare, path)
        return peaks

    def coming(self, running, peaks, seen):
        """[(each running node's stage peak, what its process tree holds now)], the most each was seen to hold kept
        in `seen` ({node: bytes}); a node whose process has ended is reaped (is_alive: waitpid, WNOHANG) and holds
        none, though its outcome is not read yet."""
        alive = [(stage, place, process) for stage, place, process in running.values() if process.is_alive()]
        held = HELD([process.pid for _, _, process in alive])
        found = []
        for stage, place, process in alive:
            node = node_name(stage, place)
            seen[node] = max(seen.get(node, 0), held[process.pid])
            found.append((peaks.get(stage.name, memory_floor()), held[process.pid]))
        return found

    def conclude(self, stage, place, did):
        """A finished node's fault report when it does not stand, else its old report removed; (what it did, whether
        it stands)."""
        with self.still():
            cause = self.standing(stage, place)
            if cause:
                return f"{did}; fault report {self.fault_report(stage, place, did, cause)}", False
        report = self.desk("faults", node_name(stage, place), ".txt")
        if report.exists():
            report.unlink()
        return did, True

    def drive(self, places, say=print, jobs=JOBS, whole=True, only=None, gauges=None):
        """Run every line to its end with no one in the loop, the lines side by side: each node starts in a process of
        its own the moment every node it reads stands accepted, at most `jobs` at once and only while this PC has
        memory for its stage's peak beside the running nodes' (memory_room), so a line waiting on a cloud step holds up no other line, and nodes of one line that read nothing of each other run side by side. An environment
        node is made once and each line that reads it waits on it alone. A node that does not end accepted stops its
        own line and leaves a fault report: every node that reads it, directly or through another, is not run, and a node
        on that line that reads nothing of it still runs; a node waits on its optional reads the drive makes too and
        runs without one that stops (unsettled); {node: what it did}, in table order. `whole` False drives the places'
        lines alone, with only the environment nodes they read; `only` (stage names) those stages and the ones they read.
        `gauges`, given by score run alone (a stage's own drive says no beats), is called every HEARTBEAT seconds for
        the text a heartbeat line carries (the run's euros so far, its paid runs open)."""
        chosen = self.line_nodes(places, whole, only)
        waiting, line = list(chosen), {node_name(*node) for node in chosen}
        done, stopped, stood, running = {}, {}, set(), {}
        on_gaps = set()  # stopped nodes that fail only on their accepted gaps: a stage's `gapped` reads them
        beat_at = time.monotonic() + HEARTBEAT
        threads = node_threads(jobs)
        peaks, seen, told = self.peaks(), {}, False  # seen: the most each running node held; told: the wait was said
        # known: what each waiting node reads, kept across turns (forget; all of it again every HEARTBEAT seconds, so a
        # plan edited under the run is read again); skips: the turns each ready node did not fit; finished: the result
        # pipes of the nodes that ended, concluded at the next turn's start inside that turn's one still pass
        known, known_at, skips, finished = {}, time.monotonic(), {}, []
        self.driving = (0, time.monotonic())
        while waiting or running:
            if time.monotonic() - known_at >= HEARTBEAT:
                known, known_at = {}, time.monotonic()
            # reap first: a node that ended since the wait is concluded now and holds no memory in this pass
            others = [pipe for pipe in running if pipe not in finished]
            finished = [*finished, *(FORK_WAIT(others, timeout=0) if others else [])]
            held = line_held = False  # a ready node waits for memory; once one waited too long, every node after it
            ready = []  # started once the pass is over: a forked node must not inherit its remembered keys
            with self.still():  # each key and plan worked out once a pass (Batch 1, 2026-10-25: a pass took 12 min)
                ended = set()
                for receiving in finished:
                    stage, place, process = running.pop(receiving)
                    node = node_name(stage, place)
                    did, peak, contained = self.outcome(receiving, process)  # an ended node holds no memory
                    peaks = self.measured(stage, did, max(peak, seen.pop(node, 0)), contained, peaks)
                    done[node], stands = self.conclude(stage, place, did)
                    if stands:
                        stood.add(node)
                    else:
                        stopped[node] = node
                        if self.standing(stage, place, gapped=True) is None:
                            on_gaps.add(node)
                    ended.add(node)
                    say(f"{node}: {done[node]}")
                finished = []
                forget(known, ended)
                coming = self.coming(running, peaks, seen)  # what the running nodes may still take (memory_room)
                for stage, place in list(waiting):
                    node = node_name(stage, place)
                    earlier = kept(known, node, "earlier", self.earlier, stage, place)
                    passes = {before for before in on_gaps if before.partition("@")[0] in stage.gapped}
                    waits = [stopped[before] for before in earlier if before in stopped and before not in passes]
                    if waits:
                        waiting.remove((stage, place))
                        stopped[node] = waits[0]
                        done[node] = (FREE_WAITS.format(node=waits[0]) if done.get(waits[0]) == PAID_LEFT
                                      else f"not run: its line stopped at {waits[0]}")
                        say(f"{node}: {done[node]}")
                    elif stood.union(passes).issuperset(earlier) and \
                            kept(known, node, "left", self.left_for_buy, stage, place):
                        waiting.remove((stage, place))
                        stopped[node], done[node] = node, PAID_LEFT
                        say(f"{node}: {done[node]}")
                    elif stood.union(passes).issuperset(earlier) and len(running) + len(ready) < jobs and \
                            not unsettled(kept(known, node, "optional", self.optional_nodes, stage, place), line,
                                          stood, stopped):
                        expected = peaks.get(stage.name, memory_floor())
                        if line_held or not memory_room(coming, expected):
                            held = True  # this node waits; the nodes after it that fit still start
                            if not line_held:
                                skips[node] = skips.get(node, 0) + 1
                                line_held = skips[node] > MEMORY_SKIPS  # passed over too long: it goes next
                            continue
                        skips.pop(node, None)
                        waiting.remove((stage, place))
                        ready.append((stage, place))
                        coming.append((expected, 0))
            for stage, place in ready:
                running.update(self.start(stage, place, threads))
            self.driving = (len(running), time.monotonic())
            if held and not told:
                say(f"memory: {AVAILABLE() / 2**30:.1f} GB available, {len(running)} running; ready nodes wait for "
                    f"{memory_floor() / 2**30:.0f} GB to stay free beside the running and starting nodes' peaks")
            told = held
            if not running:
                if not held:
                    break
                time.sleep(MEMORY_POLL)  # nothing runs and no room: wait for this PC's memory
                continue
            if gauges and time.monotonic() >= beat_at:
                say(heartbeat_line(len(done), len(running), len(waiting), gauges))
                beat_at = time.monotonic() + HEARTBEAT
            beat_in = max(0.0, beat_at - time.monotonic()) if gauges else None  # no beats: wait for a node alone
            if held:  # read the memory again within MEMORY_POLL
                beat_in = MEMORY_POLL if beat_in is None else min(beat_in, MEMORY_POLL)
            finished = FORK_WAIT(list(running), timeout=beat_in)  # concluded at the next turn's start
        return {node_name(stage, place): done[node_name(stage, place)] for stage, place in chosen
                if node_name(stage, place) in done}

    def measured(self, stage, did, peak, contained, peaks):
        """The stage peaks kept once a node of `stage` ended, having done `did` with its tree holding at most `peak`
        bytes: raised to it when the node made its output or held more than its stage's peak; a node whose tree ran a
        container client (`contained`, CONTAINER_CLIENTS) counts as holding the default at least."""
        peak = max(peak, memory_floor()) if contained else peak
        # a node that made nothing (its output found made) measured none of its stage's work, so it never brings a
        # stage under its default (2026-10-28: quick ones kept finish-route-views low, 7 real ones started)
        if "made: " in did or peak > peaks.get(stage.name, memory_floor()):
            return self.keep_peak(stage.name, peak)
        return peaks

    def left_for_buy(self, stage, place):
        """In a free-only run, whether a paid node is left for the Buy: it does not already stand accepted (one that
        does is run as any, which finds its record and pays nothing)."""
        if not (self.free_only and stage.paid) or on_this_pc():
            return False
        with self.still():
            return self.standing(stage, place) is not None

    def lines(self, places, whole=True, only=None):
        """{line: (its state, {node: state})}, running nothing: the environment's own nodes are one line, each place's
        another (`whole` False: only the environment nodes the places read). A line is done when every node stands
        accepted, else stopped (a fault report waits) or waiting at its first node that does not stand."""
        found = {}
        with self.still():
            for stage, place in self.line_nodes(places, whole, only):
                self.add_to_line(found, stage, place)
        return found

    def add_to_line(self, found, stage, place):
        """One node's state into its line's entry of `lines`, the line stopped or waiting at it when it does not
        stand and nothing before it in the line stopped it."""
        node, line = node_name(stage, place), place or WORLD_LINE
        summary, nodes = found.get(line, ("done", {}))
        nodes[node] = self.node_state(stage, place)
        if summary == "done" and self.standing(stage, place):
            report = self.desk("faults", node, ".txt")
            summary = f"stopped at {node}: fault report {report}" if report.exists() else f"waits at {node}"
        found[line] = (summary, nodes)

    # --- reading ---------------------------------------------------------------------------------------------

    def stale_reasons(self, stage, place, keyed):
        """Why a node's last record is not its current key: what changed, by part."""
        records = self.store.records(node_name(stage, place))
        if not records:
            return ["never ran"]
        last = records[-1]
        changed = [part for part in ("code", "contract", "expects", "params", "seed", "files", "after", "models")
                   if last.get(part) != keyed[part]]
        reasons = [f"{part} changed" for part in changed if part not in ("files", "after")]
        for part in ("files", "after", "beside"):
            if last.get(part, {}) != keyed.get(part, {}):
                reasons += [f"{name} changed" for name in sorted(set(last.get(part, {})) | set(keyed.get(part, {})))
                            if last.get(part, {}).get(name) != keyed.get(part, {}).get(name)]
        return reasons

    def node_status(self, stage, place):
        """One node's state, running nothing: blocked, to run (and why), to judge, or its answer and accept."""
        node = node_name(stage, place)
        try:
            keyed = self.key(stage, place)
        except Blocked as block:
            return f"blocked: {block}"
        record = self.store.record(node, keyed["key"])
        if record is None:
            return "to run: " + ", ".join(self.stale_reasons(stage, place, keyed))
        judgement = self.store.judgement(node, keyed["key"], self.evidence_state(stage, record["output"]))
        if judgement is None:
            return "to judge: its evidence changed"
        accepted = self.store.accepted(node) == record["output"]
        waived = sorted(self.store.waivers(node, keyed["key"]))
        answer = review.gapped_status(judgement["verdicts"], waived) or judgement["answer"]
        return (f"{answer}{', waived: ' + ', '.join(waived) if waived else ''}, "
                f"{'accepted' if accepted else 'not accepted'}")

    def status(self, places):
        """{node: its state, and the earlier nodes its accepted output went stale on}, running nothing."""
        with self.still():
            return {node_name(stage, place): self.node_state(stage, place) for stage, place in self.nodes(places)}

    def node_state(self, stage, place):
        """One node's status, and the earlier nodes its accepted output went stale on."""
        stale = self.stale(node_name(stage, place))
        return self.node_status(stage, place) + (f", its accepted output is stale: {', '.join(stale)} moved"
                                                  if stale else "")

    def stale(self, node):
        """The earlier nodes whose accepted output is no longer the one the node's accepted output read (an owner's
        reject moved it back), or is itself stale; none when the node has no accepted output."""
        return self.remember("stale", node, lambda: self.worked_out_stale(node))

    def worked_out_stale(self, node):
        """`stale` worked out from the store."""
        accepted = self.store.accepted(node)
        record = review.record_of(self.store, node, accepted) if accepted else None
        if record is None:
            return []
        place = node.partition("@")[2] or None
        # A record can name an earlier stage this table does not hold (another runner's, or a line's stage not merged
        # here, writing into the same store): it cannot be followed, so the node is stale on it, said, never a crash.
        unknown = [f"{before} (a stage this table does not hold)" for before in record["after"]
                   if before not in self.stages]
        earlier = {node_name(self.stages[before], place): output for before, output in record["after"].items()
                   if before in self.stages}
        earlier.update(record.get("beside", {}))
        return unknown + [before for before, output in earlier.items()
                          if self.store.accepted(before) != output or self.stale(before)]

    def ticket(self, node):
        """The node's current key, for a paid run's submit: only when every prerequisite passed and is accepted."""
        stage_name, _, place = node.partition("@")
        keyed = self.key(self.stages[stage_name], place or None)
        return {"node": node, "key": keyed["key"], "after": keyed["after"]}

    def why(self, node, depth=0):
        """A node's newest record and judgement as lines, then each earlier node it read, indented."""
        stage_name, _, place = node.partition("@")
        records = self.store.records(node)
        if not records:
            return ["  " * depth + f"{node}: no finish record"]
        record = records[-1]
        judgements = self.store.judgements(node, record["key"])
        answer = judgements[-1]["answer"] if judgements else "not judged"
        accepted = self.store.accepted(node)
        lines = ["  " * depth + f"{node}: output {record['output'][:12]} {answer}, "
                 f"{'accepted' if accepted == record['output'] else 'not accepted'}; key {record['key'][:12]}, "
                 f"code {record['code'][:12]}, commit {record['commit'][:8]}, seed {record['seed']}, "
                 f"files {', '.join(f'{name} {sha[:12]}' for name, sha in record['files'].items()) or 'none'}"]
        for before in self.read_nodes(self.stages[stage_name], place or None):
            lines += self.why(node_name(*before), depth + 1)
        return lines
