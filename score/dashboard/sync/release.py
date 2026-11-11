"""Move the hosted cockpit to a pushed score commit: the repository that hosts it builds the hosted image from one
pinned commit (an `ARG SCORE_COMMIT=<sha>` line in its Dockerfile), so a release is a change of that line and nothing
else, committed and pushed in the hosting repository's own way.

    .venv/bin/python -m score.dashboard release --host <its repository> --dockerfile <its Dockerfile, in it>
        --subject "<its commit subject, {short} the score commit>" [--commit <sha>] [--trailer "<line>" ...]

It refuses a score commit that origin's main does not hold, or this checkout with changes not committed when the
commit is its HEAD (tree_refusal: what the cockpit runs is what was pushed). It works in a worktree of its own off the
host's origin/main (a shared checkout is never written), commits the one line with the subject, a body of the score
commits since the old pin (short sha and subject, as the host's earlier moves did) and the trailers given, rebases on
the host's main and pushes HEAD to it, then removes its worktree. Then it moves the conductor's own checkout (the one
the agents' door runs from) to the same commit through the door's `release-pin` (door_asked): the conductor follows
the cockpit's pin, which moves only once the host has built its image, so the door ran old code after a release
(2026-11-11). A door that cannot be reached fails nothing already pushed: the line says so, and the checkout follows
the pin once the host has built. It prints what it did. Never run by a test against a real host or door: its own test
uses repositories made in the test and a door of its own.
"""
import pathlib
import re
import subprocess
import sys
import tempfile

from score.dashboard.sync.client import git, tree_refusal

PIN = re.compile(r"^(ARG SCORE_COMMIT=)([0-9a-f]{40})[ \t]*$", re.M)
DOOR = pathlib.Path("tools") / "cloud" / "conductor" / "door_service.py"  # in the score checkout: `ask`
DOOR_SECONDS = 1200  # the conductor's update: a checkout, perhaps a uv sync and the units
SUBJECT_WIDTH = 80  # a score commit's subject in the body, cut as the host's earlier moves were


class Refused(Exception):
    """A release that may not go ahead; its words."""


def ran(repo, *args):
    """A git command's output in `repo`; Refused with its error when it fails."""
    done = git(repo, *args)
    if done.returncode != 0:
        raise Refused(f"git {' '.join(args[:2])} in {repo} failed: "
                      f"{(done.stderr.strip().splitlines() or ['no output'])[-1]}")
    return done.stdout.strip()


def score_commit(repo, commit):
    """The full sha of the score commit to release (HEAD when None); Refused when it may not go out."""
    full = ran(repo, "rev-parse", "--verify", f"{commit or 'HEAD'}^{{commit}}")
    if full == ran(repo, "rev-parse", "HEAD"):
        refused = tree_refusal(repo)
    else:
        ran(repo, "fetch", "-q", "origin", "main")
        refused = None if git(repo, "merge-base", "--is-ancestor", full, "FETCH_HEAD").returncode == 0 else (
            f"commit {full[:8]} is not on origin's main: push it first")
    if refused:
        raise Refused(refused)
    return full


def pinned(text):
    """The commit a Dockerfile pins (its one ARG SCORE_COMMIT line); Refused without exactly one."""
    found = PIN.findall(text)
    if len(found) != 1:
        raise Refused(f"expected one `ARG SCORE_COMMIT=<sha>` line, found {len(found)}")
    return found[0][1]


def repinned(text, commit):
    """The Dockerfile's text pinned to `commit`, nothing else changed."""
    return PIN.sub(lambda match: match.group(1) + commit, text)


def message(repo, old, new, subject, trailers):
    """The host's commit message: the subject ({short} replaced by the new commit's short sha, any other brace kept
    as written), the score commits since the old pin one a line (short sha and subject, cut to SUBJECT_WIDTH), then
    the trailers."""
    lines = ran(repo, "log", "--format=%h%x09%s", "--abbrev=8", f"{old}..{new}").splitlines()
    body = [f"{short} {said[:SUBJECT_WIDTH]}" for short, _, said in (line.partition("\t") for line in lines)]
    return "\n\n".join(part for part in (subject.replace("{short}", new[:8]), "\n".join(body), "\n".join(trailers))
                       if part)


def committed_and_pushed(work, dockerfile, text, words):
    """Write the Dockerfile in the host's worktree, commit it, rebase on the host's main and push HEAD to it; the
    host's new commit."""
    (work / dockerfile).write_text(text)
    ran(work, "add", "--", dockerfile)
    ran(work, "commit", "-q", "-m", words)
    ran(work, "pull", "-q", "--rebase", "origin", "main")
    ran(work, "push", "-q", "origin", "HEAD:main")
    return ran(work, "rev-parse", "--short=10", "HEAD")


def inside(dockerfile):
    """The Dockerfile's path inside the host's repository; Refused for one that could leave it (absolute, or `..`)."""
    path = pathlib.PurePosixPath(dockerfile)
    if path.is_absolute() or ".." in path.parts:
        raise Refused(f"--dockerfile {dockerfile}: give its path inside the host's repository, as git names it")
    return str(path)


def door_asked(repo, command):
    """(exit code, its words) of one command through the agents' door (door_service.py ask, from the score checkout
    `repo`); a door that cannot be reached is a non-zero code with why."""
    try:
        done = subprocess.run([sys.executable, str(pathlib.Path(repo) / DOOR), "ask", command], capture_output=True,
                              text=True, timeout=DOOR_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as unreached:
        return 1, f"the door could not be asked ({unreached})"
    words = done.stdout.strip() or (done.stderr.strip().splitlines() or ["no output"])[-1]
    return done.returncode, words


def conductor_moved(repo, new, old, door):
    """The conductor's checkout moved to `new` through the door's release-pin (`door(repo, command)`, door_asked);
    what the release's line adds."""
    code, said = door(repo, f"release-pin {new} {old}")
    if code != 0:
        return f"; the conductor's checkout NOT moved (door exit {code}: {said}): it follows once the host has built"
    return f"; the conductor: {said}"


def release(repo, host, dockerfile, subject, commit=None, trailers=(), door=None):
    """Pin the host's Dockerfile to a pushed score commit and push it to the host's main, then (with `door`,
    door_asked) move the conductor's checkout to it; what it did, in words."""
    dockerfile = inside(dockerfile)
    new = score_commit(repo, commit)
    ran(host, "fetch", "-q", "origin", "main")
    with tempfile.TemporaryDirectory() as made:
        work = pathlib.Path(made) / "release"
        ran(host, "worktree", "add", "-q", "--detach", str(work), "FETCH_HEAD")
        try:
            text = (work / dockerfile).read_text()
            old = pinned(text)
            if old == new:
                return f"release: {dockerfile} already pins score {new[:8]}; nothing to do"
            pushed = committed_and_pushed(work, dockerfile, repinned(text, new),
                                          message(repo, old, new, subject, trailers))
        finally:
            git(host, "worktree", "remove", "--force", str(work))
    moved = conductor_moved(repo, new, old, door) if door else ""
    return (f"release: {dockerfile} moved from score {old[:8]} to {new[:8]}; {pushed} pushed to the host's main; "
            f"the host builds the cockpit from it on its own{moved}")
