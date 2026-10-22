"""score-update.service: the conductor's checkout follows the hosted cockpit's pin, so one release moves both.
Every 5 minutes (score-update.timer), standard library only, with the system interpreter (the checkout's .venv may be
the thing being re-synced):

    /usr/bin/python3 -I tools/cloud/conductor/update.py [--repo <checkout>]

1. Nothing moves while a run or a sync pass is starting from the checkout itself (a `score run`, `score resume` or
   `score.dashboard sync` process whose working folder is the checkout: a run moves to its own frozen copy as it
   starts, graph/frozen.py, so after that a move cannot reach it), nor while the checkout has tracked changes.
2. The commit to follow is the hosted cockpit's pinned SCORE_COMMIT, read from SCORE_SYNC_URL's /healthz as `commit`.
   Until the cockpit reports it, origin/main, moved only forward (as the PC's sync pulls with --ff-only).
3. `git fetch origin main`; a pin origin/main does not hold is refused (never a commit off main).
4. `git checkout --detach <commit>`, then `uv sync --frozen --group dashboard` when uv.lock or pyproject.toml changed.

It prints one line: what it moved, or why it did not.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[3]
STARTERS = (("score", "run"), ("score", "resume"), ("score.dashboard", "sync"))
LOCK_FILES = ("uv.lock", "pyproject.toml")
UV = os.environ.get("SCORE_UV", "/usr/local/bin/uv")
PROC = pathlib.Path(os.environ.get("SCORE_PROC", "/proc"))


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done


def starting(repo, proc=PROC):
    """The pids of score processes starting from the checkout itself (their working folder is the checkout)."""
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            words = (entry / "cmdline").read_bytes().split(b"\0")
            cwd = pathlib.Path(os.readlink(entry / "cwd"))
        except OSError:
            continue
        text = [word.decode(errors="replace") for word in words]
        pairs = set(zip(text, text[1:]))
        if any(pair in pairs for pair in STARTERS) and cwd == repo:
            found.append(int(entry.name))
    return found


def pinned_commit(sync_url, opener=urllib.request.urlopen):
    """The hosted cockpit's pinned commit from its /healthz (`commit`), or None while it does not report one."""
    if not sync_url:
        return None
    try:
        with opener(f"{sync_url.rstrip('/')}/healthz", timeout=15) as answer:
            commit = json.load(answer).get("commit")
    except (OSError, ValueError):
        return None
    return commit if isinstance(commit, str) and len(commit) >= 7 else None


def target(repo, pin):
    """(commit to check out, how it was chosen); RuntimeError when the pin is off origin/main."""
    if pin:
        if git(repo, "merge-base", "--is-ancestor", pin, "origin/main", check=False).returncode != 0:
            raise RuntimeError(f"the cockpit's pin {pin[:12]} is not on origin/main")
        return git(repo, "rev-parse", f"{pin}^{{commit}}").stdout.strip(), "the cockpit's pin"
    main = git(repo, "rev-parse", "origin/main").stdout.strip()
    if git(repo, "merge-base", "--is-ancestor", "HEAD", main, check=False).returncode != 0:
        raise RuntimeError("HEAD is not behind origin/main, and no pin says where to go")
    return main, "origin/main (the cockpit reports no pin yet)"


def lock_changed(repo, old, new):
    return git(repo, "diff", "--quiet", old, new, "--", *LOCK_FILES, check=False).returncode != 0


def update(repo, sync_url, uv=UV, opener=urllib.request.urlopen, proc=PROC):
    """Move the checkout as the module says; the one line of what happened."""
    busy = starting(repo, proc)
    if busy:
        return f"update: not now, score is starting from the checkout (pid {', '.join(map(str, busy))})"
    if git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        return "update: not now, the checkout has tracked changes"
    git(repo, "fetch", "-q", "origin", "main")
    try:
        commit, why = target(repo, pinned_commit(sync_url, opener))
    except RuntimeError as refused:
        return f"update: refused, {refused}"
    old = git(repo, "rev-parse", "HEAD").stdout.strip()
    if commit == old:
        return f"update: at {commit[:12]}, {why}"
    git(repo, "checkout", "-q", "--detach", commit)
    synced = ""
    if lock_changed(repo, old, commit):
        subprocess.run([uv, "sync", "-q", "--frozen", "--group", "dashboard"], cwd=repo, check=True)
        synced = ", .venv synced"
    return f"update: {old[:12]} -> {commit[:12]}, {why}{synced}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=pathlib.Path, default=REPO)
    options = parser.parse_args(argv)
    print(update(options.repo.resolve(), os.environ.get("SCORE_SYNC_URL")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
