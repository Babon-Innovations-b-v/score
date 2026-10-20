"""A run's frozen copy of the code (#45): every `score run` drives from a git worktree of its own at one commit, under
$PROPS_HOME/frozen, made as it starts and removed once it and everything it left running have ended. A pull or a push
in the checkout it was started from can then never change its inputs mid-run (2026-10-20: earth-kit@airlock's 14 bake
jobs on 3 L4s, EUR 0.53, thrown away when the main checkout was pulled under its run).

    frozen.enter(argv)    # a run not frozen yet: make its copy and start the run again inside it (never returns)
    frozen.claim()        # at a run's start: the copy this process must remove, or None
    frozen.hand_on()      # another process removes it now (the detached run, the run's releaser)
    frozen.remove_owned() # remove it, once

A clean tree is frozen at HEAD. A tree with changes (a --uncommitted run; untracked files count) is frozen at one commit
of the whole working tree, written through a throwaway index with HEAD its parent, so neither the index nor the stash
moves; SCORE_FROZEN_CHANGES then says so, and the run still registers as uncommitted. The copy links the running
Python's venv as `.venv` (ignored, so the copy stays clean and its records name its commit). SCORE_FROZEN names the
copy for every process the run starts, so none freezes again; SCORE_FROZEN_OWNER is read and dropped by the one process
that owns the copy (the run, or the detached run it hands it on to), so only that one removes it.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time

from score.store import PROPS_HOME

FOLDER = PROPS_HOME / "frozen"
FROZEN, OWNER, CHANGES = "SCORE_FROZEN", "SCORE_FROZEN_OWNER", "SCORE_FROZEN_CHANGES"
OWNED = {"path": None, "handed_on": False}


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


def remove(path):
    """Remove a frozen copy and its worktree entry."""
    common = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    done = subprocess.run(["git", "--git-dir", common, "worktree", "remove", "--force", str(path)],
                          capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"frozen copy {path} not removed: {done.stderr.strip()}")


def enter(argv, repo):
    """Freeze `repo` and start `python -m score <argv>` again inside the copy, in this process, as its owner."""
    commit, changes = snapshot(repo)
    path = make(repo, commit)
    env = {**os.environ, FROZEN: str(path), OWNER: "1", **({CHANGES: "1"} if changes else {})}
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
    """Remove the copy this process owns, unless it handed it on or removed it already."""
    path = OWNED["path"]
    if path is None or OWNED["handed_on"]:
        return
    OWNED["path"] = None
    if path.exists():
        remove(path)


def resumed_env(worktree):
    """The environment `score resume` restarts a registered run with: a run from a frozen copy owns that copy again."""
    worktree = pathlib.Path(worktree)
    if worktree.parent != FOLDER:
        return dict(os.environ)
    return {**os.environ, FROZEN: str(worktree), OWNER: "1"}
