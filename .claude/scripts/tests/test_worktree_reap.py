"""Pin worktree-reap: only a dead session's clean, merged worktree goes; nothing else is touched."""
import json
import os
import shutil
import subprocess

from conftest import SCRIPTS, git


def dead_pid():
    child = subprocess.Popen(["true"])
    child.wait()
    return child.pid


def main_checkout(tmp_path):
    """A clone whose main is on origin, with the reaper copied in."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    main = tmp_path / "main"
    git(tmp_path, "clone", "-q", str(origin), str(main))
    git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "first")
    git(main, "push", "-q", "origin", "main")
    (main / ".claude" / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPTS / "worktree-reap.py", main / ".claude" / "scripts")
    return main


def add_worktree(main, name, pid=None):
    path = main / ".claude" / "worktrees" / name
    git(main, "worktree", "add", "-q", "-b", f"worktree-{name}", str(path))
    if pid is not None:
        git(main, "worktree", "lock", "--reason", f"claude agent {name} (pid {pid} start 1)", str(path))
    return path


def reap(main, hook=False):
    env = {key: value for key, value in os.environ.items() if key != "CLAUDE_HOOK"}
    if hook:
        env["CLAUDE_HOOK"] = "SessionStart"
    return subprocess.run(["python3", main / ".claude" / "scripts" / "worktree-reap.py"],
                          env=env, capture_output=True, text=True)


def branches(main):
    return git(main, "branch", "--format=%(refname:short)").split()


def test_only_a_dead_sessions_clean_merged_worktree_is_reaped(tmp_path):
    main = main_checkout(tmp_path)
    gone = add_worktree(main, "gone", dead_pid())
    dirty = add_worktree(main, "dirty", dead_pid())
    (dirty / "work.txt").write_text("unsaved")
    unmerged = add_worktree(main, "unmerged", dead_pid())
    git(unmerged, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "local")
    live = add_worktree(main, "live", os.getpid())
    kept = add_worktree(main, "kept")

    run = reap(main)
    assert run.returncode == 0
    assert run.stdout == (
        "Reaped 1 orphaned worktree(s): gone. Left 2 stale-locked worktree(s) with uncommitted work: "
        "dirty, unmerged. Recover or discard by hand.\n")
    assert not gone.exists()
    assert all(path.exists() for path in (dirty, unmerged, live, kept))
    assert "worktree-gone" not in branches(main)
    assert {"worktree-dirty", "worktree-unmerged", "worktree-live", "worktree-kept"} <= set(branches(main))


def test_as_a_session_hook_it_speaks_json_and_only_when_it_did_something(tmp_path):
    main = main_checkout(tmp_path)
    add_worktree(main, "live", os.getpid())
    quiet = reap(main, hook=True)
    assert (quiet.returncode, quiet.stdout) == (0, "")

    add_worktree(main, "gone", dead_pid())
    run = reap(main, hook=True)
    assert run.returncode == 0
    assert json.loads(run.stdout) == {"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "Reaped 1 orphaned worktree(s): gone."}}


def test_outside_a_git_repo_it_does_nothing(tmp_path):
    shutil.copy(SCRIPTS / "worktree-reap.py", tmp_path)
    run = subprocess.run(["python3", tmp_path / "worktree-reap.py"], capture_output=True, text=True,
                         env=dict(os.environ, GIT_CEILING_DIRECTORIES=str(tmp_path.parent)))
    assert (run.returncode, run.stdout) == (0, "")
