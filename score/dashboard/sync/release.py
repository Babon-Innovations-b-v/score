"""Move the hosted cockpit to a pushed score commit: the repository that hosts it builds the hosted image from one
pinned commit (an `ARG SCORE_COMMIT=<sha>` line in its Dockerfile), so a release is a change of that line and nothing
else, committed and pushed in the hosting repository's own way.

    .venv/bin/python -m score.dashboard release --host <its repository> --dockerfile <its Dockerfile, in it>
        --subject "<its commit subject, {short} the score commit>" [--commit <sha>] [--trailer "<line>" ...]

It refuses a score commit that origin's main does not hold, or this checkout with changes not committed when the
commit is its HEAD (tree_refusal: what the cockpit runs is what was pushed). It works in a worktree of its own off the
host's origin/main (a shared checkout is never written), commits the one line with the subject, a body of the score
commits since the old pin (short sha and subject, as the host's earlier moves did) and the trailers given, rebases on
the host's main and pushes HEAD to it, then removes its worktree. It prints what it did. Never run by a test against
a real host: its own test uses repositories made in the test.
"""
import pathlib
import re
import tempfile

from score.dashboard.sync.client import git, tree_refusal

PIN = re.compile(r"^(ARG SCORE_COMMIT=)([0-9a-f]{40})[ \t]*$", re.M)
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
    """The host's commit message: the subject ({short} the new commit's short sha), the score commits since the old
    pin one a line (short sha and subject, cut to SUBJECT_WIDTH), then the trailers."""
    lines = ran(repo, "log", "--format=%h%x09%s", "--abbrev=8", f"{old}..{new}").splitlines()
    body = [f"{short} {said[:SUBJECT_WIDTH]}" for short, _, said in (line.partition("\t") for line in lines)]
    return "\n\n".join(part for part in (subject.format(short=new[:8]), "\n".join(body), "\n".join(trailers)) if part)


def committed_and_pushed(work, dockerfile, text, words):
    """Write the Dockerfile in the host's worktree, commit it, rebase on the host's main and push HEAD to it; the
    host's new commit."""
    (work / dockerfile).write_text(text)
    ran(work, "add", "--", dockerfile)
    ran(work, "commit", "-q", "-m", words)
    ran(work, "pull", "-q", "--rebase", "origin", "main")
    ran(work, "push", "-q", "origin", "HEAD:main")
    return ran(work, "rev-parse", "--short=10", "HEAD")


def release(repo, host, dockerfile, subject, commit=None, trailers=()):
    """Pin the host's Dockerfile to a pushed score commit and push it to the host's main; what it did, in words."""
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
    return (f"release: {dockerfile} moved from score {old[:8]} to {new[:8]}; {pushed} pushed to the host's main; "
            f"the host builds the cockpit from it on its own")
