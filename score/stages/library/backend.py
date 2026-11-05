"""The library backend: which library a world's outputs are handed to, and the one command that hands them.

    values = backend.settings()              # SCORE_LIB_* from the environment, else the checkout beside score's
    backend.kind(values)                     # "command" or "none"
    backend.identity(values)                 # {"backend", "library"}: the library rows' params, so a new library re-keys them
    backend.arguments(values, run)           # the handover command, word for word, from SCORE_LIB_HANDOVER
    backend.run(words, store, repo)          # runs it once; its output goes to the node's log
    backend.outside_frozen(environment, checkout)  # the environment with nothing in it naming a run's frozen copy

score never imports the library's code: it runs the library's own command and reads the report the command writes
(`handover.json`, contract library-handover v1, handover.py). Every setting is an environment variable, the names the
cockpit already uses (score/dashboard/site/settings.py), so any library with a command of this shape plugs in:

    SCORE_LIB_BACKEND    command (the only backend today) or none; unset with SCORE_LIB_ROOT set means command
    SCORE_LIB_ROOT       the library's folder
    SCORE_LIB_COMMAND    the library's command (default score-lib)
    SCORE_LIB_BLOBS_DIR  the library's blob folder, handed on to the command's environment
    SCORE_LIB_HANDOVER   the command template (DEFAULT_TEMPLATE); {command} is the command's own words

A run an agent starts without these variables still finds the library: SCORE_LIB_ROOT and SCORE_LIB_COMMAND default to
the score_lib checkout beside score's own, and the command's blob store, when none is set, to the cloud backend's
object store with its key from the secret store, in the command's environment only (tools/library/library_files.py
`defaults`, `blob_store`). No settings file (owner, 2026-10-20).

The command never names a run's frozen copy (graph/frozen.py: <home>/frozen/<copy>, its home <copy>.home), neither in
its words nor in its environment (SCORE_FROZEN, PROPS_HOME, the run's ledger tagging on PYTHONPATH, SCORE_REPO,
--repo, --out): a path in a copy is the same path in the main checkout (the library reads score through git's objects,
which every copy shares), one in a copy's home the real home's (`outside_frozen`, handed.spawn's environment too). It
runs in a process group of its own, ended with the call, so nothing of it outlives its row. The conductor then never
counts a copy as busy while a handover runs (2026-11-05: every carry, clean-cache and clean-frozen refused "a run is
live" for as long as one ran, a run long ended).
"""
import os
import pathlib
import shlex
import signal
import subprocess
import sys
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/library"))
import library_files  # noqa: E402

from score.store import PROPS_HOME  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
FROZEN_VARIABLES = ("SCORE_FROZEN", "SCORE_FROZEN_OWNER", "SCORE_FROZEN_CHANGES")
VARIABLES = ("SCORE_LIB_BACKEND", "SCORE_LIB_ROOT", "SCORE_LIB_COMMAND", "SCORE_LIB_BLOBS_DIR", "SCORE_LIB_HANDOVER")
COMMAND, NONE = "command", "none"
DEFAULT_COMMAND = "score-lib"
DEFAULT_TEMPLATE = ("{command} --root {root} handover --world {world} --place {place} --seed {seed} --commit {commit} "
                    "--route {route} --store {store} --repo {repo} --out {out}")
# One handover run may take this long before it counts as a dropped connection (graph.transient: tried again).
TIMEOUT = 1800


class Misconfigured(RuntimeError):
    """The library settings name a backend that cannot run as set."""


def settings():
    """The SCORE_LIB_* settings: each from the environment, else its default (library_files.defaults), else unset."""
    defaults = library_files.defaults()
    found = {name: os.environ.get(name, "").strip() or defaults.get(name, "") for name in VARIABLES}
    return {name: value for name, value in found.items() if value}


def kind(values):
    """The configured backend: SCORE_LIB_BACKEND, else command when a library folder is set, else none."""
    chosen = values.get("SCORE_LIB_BACKEND") or (COMMAND if values.get("SCORE_LIB_ROOT") else NONE)
    if chosen not in (COMMAND, NONE):
        raise Misconfigured(f"SCORE_LIB_BACKEND is {chosen!r}: the backends are {COMMAND} and {NONE}")
    return chosen


def library_identity(root):
    """The library's identity: its repository's first commit, else its folder (a library that is not a repository)."""
    found = subprocess.run(["git", "-C", str(root), "rev-list", "--max-parents=0", "HEAD"], capture_output=True,
                           text=True)
    commits = sorted(found.stdout.split()) if found.returncode == 0 else []
    return commits[0] if commits else str(pathlib.Path(root).resolve())


def identity(values=None):
    """{"backend", "library"}: the configured backend and the library's identity ("" for none)."""
    values = settings() if values is None else values
    chosen = kind(values)
    if chosen == NONE:
        return {"backend": NONE, "library": ""}
    root = values.get("SCORE_LIB_ROOT")
    return {"backend": chosen, "library": library_identity(root) if root else ""}


def arguments(values, run):
    """The handover command's words from the template, each placeholder filled from `run` ({world, place, seed,
    commit, route, store, repo, out}); an option whose value is a missing place (the world's own node) is left out."""
    if not values.get("SCORE_LIB_ROOT"):
        raise Misconfigured("the command backend needs SCORE_LIB_ROOT, the library's folder")
    filled = {**run, "root": values["SCORE_LIB_ROOT"]}
    template = shlex.split(values.get("SCORE_LIB_HANDOVER") or DEFAULT_TEMPLATE)
    words, index = [], 0
    while index < len(template):
        word = template[index]
        following = template[index + 1] if index + 1 < len(template) else ""
        if word.startswith("--") and "{place}" in following and filled.get("place") is None:
            index += 2
            continue
        if word == "{command}":
            words += shlex.split(values.get("SCORE_LIB_COMMAND") or DEFAULT_COMMAND)
        else:
            words.append(word.format(**filled))
        index += 1
    return words


def command_environment(values, store, repo):
    """This process's environment with the store, the repository and the library settings named for the command, and
    the cloud's blob store when none is set."""
    return library_files.blob_store({**os.environ, **values, "SCORE_STORE": str(store), "SCORE_REPO": str(repo)})


def main_checkout():
    """The repository's main checkout: the one every worktree and a run's frozen copy share their objects with."""
    common = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    return pathlib.Path(common).parent


def real_home(environment):
    """The real PROPS_HOME of `environment`: the one its frozen copy lies under, else its PROPS_HOME (a copy's home's
    real one)."""
    if environment.get("SCORE_FROZEN"):
        return pathlib.Path(environment["SCORE_FROZEN"]).parent.parent
    home = pathlib.Path(environment.get("PROPS_HOME") or PROPS_HOME)
    return home.parent.parent if home.parent.name == "frozen" and home.name.endswith(".home") else home


def outside(word, home, checkout):
    """`word` with each path in it (each of a path list) that lies in a copy under `home`/frozen moved out: in a
    copy, the same path in `checkout`; in a copy's home, the same path in `home`."""
    folders = (home / "frozen", (home / "frozen").resolve())
    parts = []
    for part in word.split(os.pathsep):
        path = pathlib.Path(part)
        folder = next((folder for folder in folders
                       if path.is_absolute() and path.is_relative_to(folder) and path != folder), None)
        if folder is not None:
            copy, *rest = path.relative_to(folder).parts
            part = str(pathlib.Path(home if copy.endswith(".home") else checkout, *rest))
        parts.append(part)
    return os.pathsep.join(parts)


def outside_frozen(environment, checkout):
    """`environment` naming no run's frozen copy: the SCORE_FROZEN marks dropped, PROPS_HOME the real home, every
    other path in a copy moved out of it (`outside`)."""
    home = real_home(environment)
    found = {name: outside(value, home, checkout) for name, value in environment.items()
             if name not in FROZEN_VARIABLES}
    return {**found, "PROPS_HOME": str(home)}


def ended(group):
    """End whatever is left of the command's process group (a child it left running)."""
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass  # nothing of it is left


def passed_on(group):
    """While the command runs, a SIGTERM or SIGINT this process gets is sent on to the command's own process group
    first, then handled as before: in a session of its own, the run's stop sent to its group would never reach it, and
    a stopped run would wait out TIMEOUT or leave score-lib saving into the library after the stop (review of
    2026-11-05). {signal: handler before} to put back; none off the main thread, where no handler can be set."""
    if threading.current_thread() is not threading.main_thread():
        return {}
    before = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}

    def forward(number, frame):
        try:
            os.killpg(group, number)
        except ProcessLookupError:
            pass  # the command already ended
        handler = before[number]
        if callable(handler):
            handler(number, frame)
        elif handler == signal.SIG_DFL:
            signal.signal(number, signal.SIG_DFL)
            os.kill(os.getpid(), number)
    for number in before:
        signal.signal(number, forward)
    return before


def run(words, values, store, repo):
    """Run the handover command once, its words and environment naming no frozen copy (`outside_frozen`), in a
    process group of its own ended with the call however it ends; its output into this process's own (the node's
    log). A non-zero exit raises RuntimeError; a run past TIMEOUT raises TimeoutError, which the runner tries again
    (graph.transient)."""
    checkout, home = main_checkout(), real_home(os.environ)
    words = [outside(word, home, checkout) for word in words]
    print("library handover:", shlex.join(words), flush=True)
    try:
        process = subprocess.Popen(words, env=outside_frozen(command_environment(values, store, repo), checkout),
                                   cwd=values["SCORE_LIB_ROOT"], start_new_session=True)
    except FileNotFoundError as missing:
        raise RuntimeError(f"the library has no handover command here: {missing}") from missing
    passed = passed_on(process.pid)
    try:
        returncode = process.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired as expired:
        raise TimeoutError(f"the library's handover ran past {TIMEOUT} s") from expired
    finally:
        for number, before in passed.items():
            signal.signal(number, before)
        ended(process.pid)
        process.wait()
    if returncode != 0:
        raise RuntimeError(f"the library's handover command exited {returncode} (its words are in the log above; "
                           "a library without `handover` has no handover command yet)")
