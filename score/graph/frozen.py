"""A run's frozen copy of the code (#45): every `score run` drives from a git worktree of its own at one commit, under
$PROPS_HOME/frozen, made as it starts and removed once it and everything it left running have ended. A pull or a push
in the checkout it was started from can then never change its inputs mid-run (2026-10-20: earth-kit@airlock's 14 bake
jobs on 3 L4s, EUR 0.53, thrown away when the main checkout was pulled under its run).

    frozen.enter(argv)    # a run not frozen yet: make its copy and start the run again inside it (never returns)
    frozen.claim()        # at a run's start: the copy this process must remove, or None
    frozen.hand_on()      # another process removes it now (the detached run, the run's releaser)
    frozen.remove_owned() # end every process still working in it (end_users), then remove it, once
    frozen.users(folder)  # {pid: copy name} of every process working in a copy under `folder`
    frozen.end(pids)      # SIGTERM, then SIGKILL after END_GRACE_SECONDS; [{pid, command}] of those it ended
    frozen.home_copy(path)  # the run's own home beside its copy: the design copied, the rest linked (enter does it)

A clean tree is frozen at HEAD. A tree with changes (a --uncommitted run; untracked files count) is frozen at one commit
of the whole working tree, written through a throwaway index with HEAD its parent, so neither the index nor the stash
moves; SCORE_FROZEN_CHANGES then says so, and the run still registers as uncommitted. The copy links the running
Python's venv as `.venv` (ignored, so the copy stays clean and its records name its commit). SCORE_FROZEN names the
copy for every process the run starts, so none freezes again; SCORE_FROZEN_OWNER is read and dropped by the one process
that owns the copy (the run, or the detached run it hands it on to), so only that one removes it.

The design is frozen too: the run's PROPS_HOME is a home of its own beside the copy (`<copy>.home`), its design
folder a copy of $PROPS_HOME/design as the run starts and every other entry a link to the real one, so the store,
the work folder and the logs are the shared ones. A sync pass, a lock or an edit that rewrites the design during the
run reaches the next run, never this one (Batch 1, 2026-10-25: prepare rewrote every place's surface data mid-run, 58
takes to 62, and every finish-route-palette and finish-route-list on it had "not run on its current inputs" or had
"an input changed while it ran"). Same content, same keys: a key hashes a file's bytes, never its path. Once the run
ends its design copy goes and a link to the real design takes its place, so a path the run printed or recorded
(its log, a fault report) still opens; an entry the run made at the home's top level is moved into the real home
and linked the same way.
"""
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from score.store import PROPS_HOME

FOLDER = PROPS_HOME / "frozen"
FROZEN, OWNER, CHANGES = "SCORE_FROZEN", "SCORE_FROZEN_OWNER", "SCORE_FROZEN_CHANGES"
OWNED = {"path": None, "handed_on": False}
# How long a process left working in a copy has to end on SIGTERM before SIGKILL (end).
END_GRACE_SECONDS = 10


def git(repo, *words, env=None):
    """A git command's output in `repo`; raises when it fails."""
    done = subprocess.run(["git", "-C", str(repo), *words], capture_output=True, text=True, env=env)
    if done.returncode:
        raise RuntimeError(f"git {' '.join(words)} in {repo}: {done.stderr.strip()}")
    return done.stdout.strip()


def snapshot(repo):
    """(the commit that holds the working tree as it is, whether it has changes not committed): HEAD when clean."""
    if not git(repo, "status", "--porcelain"):
        return git(repo, "rev-parse", "HEAD"), False
    with tempfile.TemporaryDirectory() as folder:
        env = {**os.environ, "GIT_INDEX_FILE": str(pathlib.Path(folder) / "index")}
        git(repo, "read-tree", "HEAD", env=env)
        git(repo, "add", "-A", env=env)
        tree = git(repo, "write-tree", env=env)
        return git(repo, "commit-tree", tree, "-p", "HEAD", "-m", f"score run: {repo}'s working tree, frozen",
                   env=env), True


def make(repo, commit, folder=None):
    """A worktree of `repo` at `commit` under `folder` (FOLDER), the running venv linked in as .venv; its path."""
    path = pathlib.Path(folder or FOLDER) / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "--detach", str(path), commit)
    if sys.prefix != sys.base_prefix:
        (path / ".venv").symlink_to(pathlib.Path(sys.prefix).resolve())
    return path


def home_of(path):
    """The run's own home beside the frozen copy at `path`."""
    return pathlib.Path(f"{path}.home")


def home_copy(path, home=PROPS_HOME):
    """The run's own home beside the copy at `path` (module docstring): `home`'s design copied, every other entry
    linked; its path."""
    own = home_of(path)
    own.mkdir()
    for entry in home.iterdir():
        if entry.name == "design" and entry.is_dir():
            shutil.copytree(entry, own / "design", symlinks=True)
        else:
            (own / entry.name).symlink_to(entry.resolve())
    return own


def home_closed(path, home):
    """The run at `path` ended: its design copy replaced by a link to `home`'s design, and every entry it made at its
    own home's top level moved into `home` (one `home` has already is left, and named in the error)."""
    own = home_of(path)
    if not own.is_dir():
        return
    left = []
    for entry in sorted(own.iterdir()):
        if entry.is_symlink():
            continue
        if entry.name == "design" and (home / "design").exists():
            writable(entry)
            shutil.rmtree(entry)
            entry.symlink_to((home / "design").resolve())
        elif (home / entry.name).exists():
            left.append(entry.name)
        else:
            shutil.move(entry, home / entry.name)
            entry.symlink_to((home / entry.name).resolve())
    if left:
        raise RuntimeError(f"{own}: {', '.join(left)} made by the run at its home's top level, and the home has one: "
                           "left there")


def writable(folder):
    """Let the owner write every folder under `folder` (a copied design is read-only), so it can be removed."""
    for found in (folder, *folder.rglob("*")):
        if found.is_dir() and not found.is_symlink():
            found.chmod(found.stat().st_mode | 0o700)


def remove(path, home=None):
    """Remove a frozen copy and its worktree entry, and close its run's home (home_closed) against `home` (the home
    whose frozen folder holds the copy)."""
    common = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    done = subprocess.run(["git", "--git-dir", common, "worktree", "remove", "--force", str(path)],
                          capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"frozen copy {path} not removed: {done.stderr.strip()}")
    home_closed(path, home or pathlib.Path(path).parent.parent)


def enter(argv, repo):
    """Freeze `repo` and start `python -m score <argv>` again inside the copy, in this process, as its owner."""
    commit, changes = snapshot(repo)
    path = make(repo, commit)
    env = {**os.environ, FROZEN: str(path), OWNER: "1", "PROPS_HOME": str(home_copy(path)),
           **({CHANGES: "1"} if changes else {})}
    print(f"score run: frozen at {commit[:12]} in {path}", flush=True)
    os.chdir(path)
    os.execve(sys.executable, [sys.executable, "-m", "score", *argv], env)


def inside():
    """Whether this process runs from a frozen copy."""
    return bool(os.environ.get(FROZEN))


def had_changes():
    """Whether the checkout this run was frozen from had changes not committed."""
    return bool(os.environ.get(CHANGES))


def claim():
    """Take the copy this process owns (its OWNER mark dropped from the environment, so nothing it starts inherits
    it); its path, or None."""
    if os.environ.pop(OWNER, None) and inside():
        OWNED.update(path=pathlib.Path(os.environ[FROZEN]), handed_on=False)
    return OWNED["path"]


def owner_env():
    """The environment for the process this one hands its copy on to."""
    return {**os.environ, OWNER: "1"}


def hand_on():
    """Another process removes the copy: this one leaves it."""
    OWNED["handed_on"] = True


def remove_owned():
    """Remove the copy this process owns, unless it handed it on or removed it already: first every process still
    working in it ended (a run's leftovers never hold the checkout, score-update), then the copy."""
    path = OWNED["path"]
    if path is None or OWNED["handed_on"]:
        return
    OWNED["path"] = None
    end([pid for pid, name in users(path.parent).items() if name == path.name])
    if path.exists():
        remove(path)


def ancestors():
    """This process and every process above it."""
    found, pid = set(), os.getpid()
    while pid > 1 and pid not in found:
        found.add(pid)
        try:
            pid = int((pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split())[1])
        except (OSError, IndexError, ValueError):
            break
    return found


def users(folder=None):
    """{pid: copy name} of every process whose working folder is in a copy under `folder` (FOLDER) or its home, a
    copy removed under it too, this process and its ancestors left out (2026-10-26: six processes of a stopped run
    worked on in its copy for an hour and held the checkout, score-update)."""
    folder, spare, found = pathlib.Path(folder or FOLDER), ancestors(), {}
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) in spare:
            continue
        try:
            cwd = pathlib.Path(os.readlink(entry / "cwd").removesuffix(" (deleted)"))
        except OSError:
            continue
        if cwd.is_relative_to(folder) and cwd != folder:
            found[int(entry.name)] = cwd.relative_to(folder).parts[0].removesuffix(".home")
    return found


def command(pid):
    """A process's command line as one line, \"\" when it is gone."""
    try:
        return pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        return ""


def alive(pid):
    """Whether a process is there and not a zombie."""
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0] != "Z"
    except (OSError, IndexError):
        return False


def end(pids, grace=None):
    """End `pids`: SIGTERM, then SIGKILL to those left after `grace` seconds (END_GRACE_SECONDS); [{pid, command}] of
    those signalled."""
    ended = [{"pid": pid, "command": command(pid)} for pid in pids]
    for pid in pids:
        signalled(pid, signal.SIGTERM)
    deadline = time.time() + (END_GRACE_SECONDS if grace is None else grace)
    while any(map(alive, pids)) and time.time() < deadline:
        time.sleep(0.1)
    for pid in filter(alive, pids):
        signalled(pid, signal.SIGKILL)
    return ended


def signalled(pid, number):
    """Send a signal to a process that may have ended meanwhile."""
    try:
        os.kill(pid, number)
    except ProcessLookupError:
        pass


def resumed_env(worktree):
    """The environment `score resume` restarts a registered run with: a run from a frozen copy owns that copy again."""
    worktree = pathlib.Path(worktree)
    if worktree.parent != FOLDER:
        return dict(os.environ)
    own = {"PROPS_HOME": str(home_of(worktree))} if home_of(worktree).is_dir() else {}
    return {**os.environ, FROZEN: str(worktree), OWNER: "1", **own}
