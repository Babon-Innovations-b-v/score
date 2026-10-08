#!/usr/bin/env python3
"""Reap orphaned git worktrees left behind by crashed Claude sessions.

Each Claude worktree under .claude/worktrees/ is locked while its session is
live; the lock reason carries the session pid. On a clean exit the harness
removes the worktree, but on a crash the lock survives and every later session
skips it as "in use by another live session" forever. This reaper reclaims
those orphans.

A worktree is reaped only when it is safe:
  - its lock pid is dead (the session that made it is gone), AND
  - the tree is clean: no uncommitted changes and no commits missing upstream.
Dirty orphans are left in place and reported, never deleted, so no work is lost.

Read-only on anything it does not own: unlocked worktrees (a session chose to
keep them, or a human made them by hand) are never touched.

Run standalone (`python3 .claude/scripts/worktree-reap.py`) or via the
SessionStart hook. Exit status is always 0 so it never blocks a session.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LOCK_PID_RE = re.compile(r"pid (\d+)")


def git_out(args, cwd=None):
    """Run git, returning (returncode, stripped stdout)."""
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )
    return proc.returncode, proc.stdout.strip()


def resolve_paths():
    """Locate the main worktree and the shared gitdir from wherever we run.

    A SessionStart hook may fire inside a linked worktree, where `.git` is a
    file, not a directory. Ask git rather than guessing the layout.
    """
    start = Path(__file__).resolve().parent
    code, common = git_out(["rev-parse", "--path-format=absolute",
                            "--git-common-dir"], cwd=start)
    if code != 0:
        return None, None
    git_common_dir = Path(common)
    # The main worktree is the parent of the shared .git directory.
    main_root = git_common_dir.parent
    worktrees_dir = main_root / ".claude" / "worktrees"
    return worktrees_dir, git_common_dir


def pid_alive(pid):
    """True if a process with this pid currently exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # It exists; we just can't signal it.
        return True
    return True


def lock_pid(git_common_dir, worktree_name):
    """The pid recorded in this worktree's lock file, or None if unlocked."""
    lock_file = git_common_dir / "worktrees" / worktree_name / "locked"
    if not lock_file.is_file():
        return None
    match = LOCK_PID_RE.search(lock_file.read_text())
    return int(match.group(1)) if match else None


def is_clean(worktree_path):
    """True when the worktree holds no work that would be lost by removing it.

    Two conditions, both required:
      - no uncommitted changes (porcelain, which also flags untracked files);
      - HEAD is already an ancestor of origin/main.

    In this repo `main` is the deploy interface, so once a worktree's commits
    have landed on origin/main the branch is disposable, even with no upstream
    tracking ref. We compare against the local origin/main (no network fetch):
    if it is stale and behind, the worst case is a still-merged worktree is
    kept, never that unmerged work is deleted.
    """
    code, dirty = git_out(["status", "--porcelain"], cwd=worktree_path)
    if code != 0 or dirty:
        return False
    # HEAD must already be on origin/main. Missing ref -> keep, do not reap.
    code, _ = git_out(
        ["merge-base", "--is-ancestor", "HEAD", "origin/main"],
        cwd=worktree_path,
    )
    return code == 0


def reap():
    worktrees_dir, git_common_dir = resolve_paths()
    if worktrees_dir is None or not worktrees_dir.is_dir():
        return [], [], []

    self_root = Path(__file__).resolve().parents[2]
    reaped, kept_dirty, skipped_live = [], [], []

    for entry in sorted(worktrees_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if entry == self_root:
            # Never reap the worktree this hook is itself running inside.
            continue
        pid = lock_pid(git_common_dir, name)
        if pid is None:
            # Unlocked: not ours to reclaim.
            continue
        if pid_alive(pid):
            skipped_live.append(name)
            continue
        # Stale lock: the session that made it is dead.
        if not is_clean(entry):
            kept_dirty.append(name)
            continue
        # Remember the branch so we can drop it too once the worktree is gone.
        _, branch = git_out(["symbolic-ref", "--short", "HEAD"], cwd=entry)
        git_out(["worktree", "unlock", str(entry)], cwd=worktrees_dir)
        code, _ = git_out(["worktree", "remove", "--force", str(entry)],
                          cwd=worktrees_dir)
        if code != 0:
            kept_dirty.append(name)
            continue
        reaped.append(name)
        # Delete the auto-generated worktree branch (is_clean already proved it
        # is on origin/main). Only the EnterWorktree "worktree-*" naming, so a
        # meaningfully-named branch is never touched.
        if branch.startswith("worktree-"):
            git_out(["branch", "-D", branch], cwd=worktrees_dir)

    if reaped:
        git_out(["worktree", "prune"], cwd=worktrees_dir)
    return reaped, kept_dirty, skipped_live


def main():
    reaped, kept_dirty, _ = reap()
    lines = []
    if reaped:
        lines.append(f"Reaped {len(reaped)} orphaned worktree(s): {', '.join(reaped)}.")
    if kept_dirty:
        lines.append(
            f"Left {len(kept_dirty)} stale-locked worktree(s) with uncommitted work: "
            f"{', '.join(kept_dirty)}. Recover or discard by hand."
        )
    context = " ".join(lines)

    # SessionStart hook contract: emit additionalContext only when there is
    # something worth telling the session about.
    if context and os.environ.get("CLAUDE_HOOK") == "SessionStart":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }))
    elif context:
        print(context)
    sys.exit(0)


if __name__ == "__main__":
    main()
