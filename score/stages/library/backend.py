"""The library backend: which library a world's outputs are handed to, and the one command that hands them.

    values = backend.settings()              # SCORE_LIB_* from the environment, else the checkout beside score's
    backend.kind(values)                     # "command" or "none"
    backend.identity(values)                 # {"backend", "library"}: the library rows' params, so a new library re-keys them
    backend.arguments(values, run)           # the handover command, word for word, from SCORE_LIB_HANDOVER
    backend.run(words, store, repo)          # runs it once; its output goes to the node's log

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
"""
import os
import pathlib
import shlex
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/library"))
import library_files  # noqa: E402

VARIABLES = ("SCORE_LIB_BACKEND", "SCORE_LIB_ROOT", "SCORE_LIB_COMMAND", "SCORE_LIB_BLOBS_DIR", "SCORE_LIB_HANDOVER")
COMMAND, NONE = "command", "none"
DEFAULT_COMMAND = "score-lib"
DEFAULT_TEMPLATE = ("{command} --root {root} handover --world {world} --place {place} --seed {seed} --commit {commit} "
                    "--store {store} --repo {repo} --out {out}")
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
    commit, store, repo, out}); an option whose value is a missing place (the world's own node) is left out."""
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


def run(words, values, store, repo):
    """Run the handover command once; its output into this process's own (the node's log). A non-zero exit raises
    RuntimeError; a run past TIMEOUT raises TimeoutError, which the runner tries again (graph.transient)."""
    print("library handover:", shlex.join(words), flush=True)
    try:
        done = subprocess.run(words, env=command_environment(values, store, repo), timeout=TIMEOUT,
                              cwd=values["SCORE_LIB_ROOT"])
    except subprocess.TimeoutExpired as expired:
        raise TimeoutError(f"the library's handover ran past {TIMEOUT} s") from expired
    except FileNotFoundError as missing:
        raise RuntimeError(f"the library has no handover command here: {missing}") from missing
    if done.returncode != 0:
        raise RuntimeError(f"the library's handover command exited {done.returncode} (its words are in the log above; "
                           "a library without `handover` has no handover command yet)")
