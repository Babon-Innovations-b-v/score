"""The conductor's score_lib checkout against its origin (the door's `score-lib status | pull`, 2026-10-28).

    status(root)   # fetched first: HEAD, its upstream, ahead and behind, local changes, the newest push that landed
    pull(root)     # fast-forward only; refused with what is in the way (local changes, local commits)

boot.sh clones score_lib once and nothing pulls it, while score's library rows (`score-lib handover`), concept locks
(`score-lib concept`) and the cockpit's lock and withdraw commit and push from it: a stale checkout fails those pushes
non-fast-forward. No push attempt is logged on score's side (each command's words go back to its caller only), so
the newest push is read from git's own reflog of the upstream ref, which a push that landed writes ("update by
push"); a failed push leaves no trace there, its commits show as ahead.
"""
import subprocess

LISTED = 10  # items a summary shows; the rest in the detail file


def git(root, *words):
    """One git command in the checkout; the finished process, its output as text."""
    return subprocess.run(["git", "-C", str(root), *words], capture_output=True, text=True)


def said(done):
    """A git command's last line of output, for a refusal's words."""
    lines = (done.stderr or done.stdout or "").strip().splitlines()
    return lines[-1] if lines else f"exit {done.returncode}"


def lines_of(root, *words):
    """A git command's output lines; [] when it fails."""
    done = git(root, *words)
    return done.stdout.strip().splitlines() if done.returncode == 0 else []


def head(root):
    """HEAD as `<short sha> <commit time> <subject>`."""
    return git(root, "log", "-1", "--format=%h %cI %s").stdout.strip()


def last_push(root, upstream):
    """The newest reflog line of the upstream ref that a push wrote, else None."""
    for line in lines_of(root, "reflog", "show", "--date=iso", "--format=%gd %h %gs", f"refs/remotes/{upstream}"):
        if "update by push" in line:
            return line
    return None


def status(root):
    """The checkout against its origin after a fetch: {head, upstream, fetch, ahead, behind, changes, local_commits,
    incoming, last_push}; fetch is "" when it worked, else its words (the counts then against the last fetch)."""
    fetched = git(root, "fetch", "-q", "origin")
    upstream = git(root, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip()
    found = {"head": head(root), "upstream": upstream,
             "fetch": "" if fetched.returncode == 0 else said(fetched),
             "changes": lines_of(root, "status", "--porcelain"), "local_commits": [], "incoming": [],
             "ahead": 0, "behind": 0, "last_push": None}
    if not upstream:
        return found
    found["local_commits"] = lines_of(root, "log", "--format=%h %cI %s", "@{upstream}..HEAD")
    found["incoming"] = lines_of(root, "log", "--format=%h %cI %s", "HEAD..@{upstream}")
    found["ahead"], found["behind"] = len(found["local_commits"]), len(found["incoming"])
    found["last_push"] = last_push(root, upstream)
    return found


def pull(root):
    """Fast-forward the checkout to its upstream after a fetch; (found, refusal): refusal is "" when it moved or had
    nothing to move, else why, with found's changes and local_commits naming what is in the way."""
    found = status(root)
    if found["fetch"]:
        return found, f"the fetch failed: {found['fetch']}"
    if not found["upstream"]:
        return found, "the branch has no upstream"
    if found["changes"] or found["local_commits"]:
        return found, (f"{len(found['changes'])} local changes and {len(found['local_commits'])} local commits: "
                       "a fast-forward only pull moves nothing")
    if found["behind"]:
        moved = git(root, "merge", "-q", "--ff-only", "@{upstream}")
        if moved.returncode != 0:
            return found, f"the fast-forward failed: {said(moved)}"
    return found, ""
