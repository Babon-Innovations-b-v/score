"""score-update.service: the conductor's checkout follows the hosted cockpit's pin, so one release moves both.
Before every sync pass (score-sync.service's ExecStartPre, `install-sync --no-pull`) and every 5 minutes for an idle
conductor (score-update.timer), standard library only, with the system interpreter (the checkout's .venv may be the
thing being re-synced). The pass's own call sees no sync process yet: systemd starts the pass only after it, so it
moves the checkout (2026-10-24: with the timer alone a pass always ran, as a pass outlasts 5 minutes, and the checkout
never moved). Two calls at once take turns on a lock in the checkout's .git folder.

    /usr/bin/python3 -I tools/cloud/conductor/update.py [--repo <checkout>]

1. Nothing moves while a run is starting from the checkout itself (a `score run` or `score resume` process whose
   working folder is the checkout: a run moves to its own frozen copy as it starts, graph/frozen.py, so after that a
   move cannot reach it), nor while the checkout has tracked changes. A sync pass is not a run: it holds back only a
   move that changes uv.lock (step 4), since a pass outlasts the 5-minute timer and the next starts right after it,
   so counting it kept the checkout on an old commit all morning (2026-10-25, the Buy's retry ran old code).
2. The commit to follow is the hosted cockpit's pinned SCORE_COMMIT, read from SCORE_SYNC_URL's /api/sync/pin as
   `commit`, signed in by the sync token (read by name through SCORE_SECRET_READER, as the sync pass reads it). Not
   /healthz: the hosting proxy answers that with a body of its own. A pin that cannot be read moves nothing; only a
   cockpit that answers with no commit (an image built without SCORE_COMMIT), or no SCORE_SYNC_URL, falls back to
   origin/main, moved only forward (as the PC's sync pulls with --ff-only).
   The pin read is kept in $PROPS_HOME/conductor/pin.json with this call's line (`said`), so the health record shows a
   checkout off the pin and why.
3. `git fetch origin main`; a pin origin/main does not hold is refused (never a commit off main).
4. Nothing moves while a process works in a frozen copy under $PROPS_HOME/frozen (a live run): every run's copy links
   this checkout's .venv in (graph/frozen.py) and its rows run the prop environment, and its own steps reach the
   checkout's tools, so the move waits and goes on at the first tick after the run ends. A sync pass from the checkout
   holds back only a move that changes uv.lock or pyproject.toml; the pass's own ExecStartPre makes that move before
   its sync process starts. The line says when the installed sync unit has no such ExecStartPre (2026-10-26: the
   checkout lagged the pin 2.5 hours on a unit installed before it; boot.sh now installs it every boot).
5. `git checkout --detach <commit>`, then `uv sync --frozen --group dashboard` when uv.lock or pyproject.toml changed,
   and the prop environment ($PROPS_HOME/env, boot.sh props_env) synced the same way once the move made machine.json,
   on that change or whenever it is missing (left out of every backup; nothing runs boot.sh at a reboot).
6. Whatever moved, score_lib's checkout beside it gets a machine's git identity when git knows no user.email there
   (2026-10-28: boot.sh's clone had none, so every take-in, handover, concept lock and cockpit lock failed its commit,
   "unable to auto-detect email address"). Set in its own config, every process committing there has it.

It prints one line: what it moved, or why it did not.
"""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[3]
STARTERS = (("score", "run"), ("score", "resume"))
SYNCING = (("score.dashboard", "sync"),)  # a sync pass: holds back only a uv.lock move
LOCK_FILES = ("uv.lock", "pyproject.toml")
UV = os.environ.get("SCORE_UV", "/usr/local/bin/uv")
PROC = pathlib.Path(os.environ.get("SCORE_PROC", "/proc"))
HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
SECRET = "score-cockpit-sync-token"  # score/dashboard/sync/timer.py SECRET
PIN_PATH = "/api/sync/pin"  # score/dashboard/sync/endpoints.py pin
# score_lib's commits from the conductor: a machine's name, never a person's or an account's (a public repository).
LIBRARY_COMMITTER = (("user.name", "SCORE conductor"), ("user.email", "conductor@score.invalid"))
SYNC_UNIT = (pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "systemd" / "user"
             / "score-sync.service")  # score/dashboard/sync/timer.py install, --no-pull: UPDATE before each pass


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done


def starting(repo, proc=PROC, starters=STARTERS):
    """The pids of score processes of `starters` started from the checkout itself (their working folder is it)."""
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
        if any(pair in pairs for pair in starters) and cwd == repo:
            found.append(int(entry.name))
    return found


def sync_token(environ=os.environ):
    """The sync token, read by name through the env file's SCORE_SECRET_READER; RuntimeError when it cannot be."""
    reader = environ.get("SCORE_SECRET_READER", "")
    if not reader:
        raise RuntimeError("no SCORE_SECRET_READER to read the sync token with")
    done = subprocess.run([reader, SECRET], capture_output=True, text=True)
    if done.returncode != 0 or not done.stdout.strip():
        raise RuntimeError(f"the sync token could not be read ({reader} {SECRET}: exit {done.returncode})")
    return done.stdout.strip()


def pinned_commit(sync_url, token, opener=urllib.request.urlopen):
    """The hosted cockpit's pinned commit from /api/sync/pin (`commit`), None while it reports none or no sync URL is
    set; RuntimeError when it cannot be read (`token` a callable giving the sync token)."""
    if not sync_url:
        return None
    try:
        asked = urllib.request.Request(f"{sync_url.rstrip('/')}{PIN_PATH}",
                                       headers={"Authorization": f"Bearer {token()}"})
        with opener(asked, timeout=15) as answer:
            commit = json.load(answer).get("commit")
    except (OSError, ValueError) as unread:
        raise RuntimeError(f"the cockpit's pin could not be read: {unread}") from unread
    return commit if isinstance(commit, str) and len(commit) >= 7 else None


def pin_noted(home, pin):
    """Keep the pin last read in home/conductor/pin.json ({at, pin}), for the Machine card (score.conductor.health)."""
    path = home / "conductor" / "pin.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"pin.json.{os.getpid()}.partial")
    at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    partial.write_text(json.dumps({"at": at, "pin": pin}))
    os.replace(partial, path)


def said_noted(home, line):
    """Add this call's line to home/conductor/pin.json as `said`, so the health record says why a checkout is off."""
    path = home / "conductor" / "pin.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    noted = json.loads(path.read_text()) if path.is_file() else {}
    partial = path.with_name(f"pin.json.{os.getpid()}.partial")
    partial.write_text(json.dumps({**noted, "said": line}))
    os.replace(partial, path)


def pass_updates_first(sync_unit=SYNC_UNIT):
    """Whether the installed sync unit runs this update before each pass (its ExecStartPre names update.py)."""
    try:
        lines = sync_unit.read_text().splitlines()
    except OSError:
        return False
    return any(line.startswith("ExecStartPre=") and "conductor/update.py" in line for line in lines)


def frozen_users(home=HOME, proc=PROC):
    """The pids working in a frozen copy under home/frozen: live runs, each on this checkout's .venv."""
    folder = home / "frozen"
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd = pathlib.Path(os.readlink(entry / "cwd"))
        except OSError:
            continue
        if folder in cwd.parents:
            found.append(int(entry.name))
    return found


def named(proc, pid):
    """`pid <n>: <its command line>`, cut to 120 characters, so the line says which process holds the checkout."""
    try:
        words = (proc / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        words = "gone"
    return f"pid {pid}: {words[:120]}"


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


def props_env(repo, home, uv, changed):
    """Sync the prop environment (home/env, boot.sh props_env) once the move made machine.json, when uv.lock
    `changed` or it is missing (a backup leaves it out); what the line adds."""
    if not (home / "machine.json").exists() or not (changed or not (home / "env" / "bin" / "python").exists()):
        return ""
    subprocess.run([uv, "sync", "-q", "--frozen", "--no-dev", "--project", str(repo)], check=True,
                   env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(home / "env")})
    return ", the prop environment synced"


def update(repo, sync_url, uv=UV, opener=urllib.request.urlopen, proc=PROC, token=sync_token, home=HOME,
           sync_unit=SYNC_UNIT):
    """Move the checkout as the module says; the one line of what happened, also noted for the health record."""
    line = moved(repo, sync_url, uv, opener, proc, token, home, sync_unit)
    line += library_identified(repo.parent / "score_lib")
    said_noted(home, line)
    return line


def library_identified(library):
    """LIBRARY_COMMITTER set in the checkout `library` when git knows no user.email there; what it did, in words."""
    if not (library / ".git").exists() or git(library, "config", "user.email", check=False).returncode == 0:
        return ""
    for key, value in LIBRARY_COMMITTER:
        git(library, "config", key, value)
    return f"; {library} given its committer {LIBRARY_COMMITTER[0][1]}"


def moved(repo, sync_url, uv, opener, proc, token, home, sync_unit):
    """Move the checkout as the module says; the one line of what happened."""
    busy = starting(repo, proc)
    if busy:
        return f"update: not now, score is starting from the checkout (pid {', '.join(map(str, busy))})"
    if git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        return "update: not now, the checkout has tracked changes"
    git(repo, "fetch", "-q", "origin", "main")
    try:
        pin = pinned_commit(sync_url, token, opener)
    except RuntimeError as unread:
        return f"update: not now, {unread}"
    pin_noted(home, pin)
    try:
        commit, why = target(repo, pin)
    except RuntimeError as refused:
        return f"update: refused, {refused}"
    old = git(repo, "rev-parse", "HEAD").stdout.strip()
    if commit == old:
        return f"update: at {commit[:12]}, {why}{props_env(repo, home, uv, False)}"
    runs = frozen_users(home, proc)
    if runs:
        return (f"update: not now, a live run works from the checkout ({'; '.join(named(proc, pid) for pid in runs)}); "
                f"{commit[:12]} moves after it ends")
    passes = starting(repo, proc, SYNCING) if lock_changed(repo, old, commit) else []
    if passes:
        unit = "" if pass_updates_first(sync_unit) else (
            f"; {sync_unit} runs no update before its pass, so passes back to back hold it: boot.sh installs it "
            f"(install-sync --no-pull) at the next boot")
        return (f"update: not now, {commit[:12]} changes uv.lock and a sync pass uses .venv "
                f"(pid {', '.join(map(str, passes))}){unit}")
    git(repo, "checkout", "-q", "--detach", commit)
    synced = ""
    if lock_changed(repo, old, commit):
        subprocess.run([uv, "sync", "-q", "--frozen", "--group", "dashboard"], cwd=repo, check=True)
        synced = ", .venv synced"
    synced += props_env(repo, home, uv, lock_changed(repo, old, commit))
    return f"update: {old[:12]} -> {commit[:12]}, {why}{synced}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=pathlib.Path, default=REPO)
    options = parser.parse_args(argv)
    with open(options.repo.resolve() / ".git" / "score-update.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # score-update.service and a pass's ExecStartPre never move it together
        print(update(options.repo.resolve(), os.environ.get("SCORE_SYNC_URL")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
