"""The git side of a checkout: a branch's commit and where it left main, the fix branches on offer, and landing the
chosen branches on main in a fixed order (each rebased on the one before; a conflict refuses the whole landing)."""
import pathlib
import shutil
import subprocess
import tempfile

from score.dashboard.checkout import MAIN, REMOTE


class Conflict(RuntimeError):
    """A branch that does not rebase cleanly onto what landed before it."""


def git(repo, *arguments):
    """git's output in `repo`, stripped; RuntimeError with git's words when it fails."""
    done = subprocess.run(["git", "-C", str(repo), *arguments], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)}: {(done.stderr or done.stdout).strip()}")
    return done.stdout.strip()


def main_ref():
    return f"{REMOTE}/{MAIN}"


def fetch(repo):
    git(repo, "fetch", "-q", REMOTE)


def head(repo, branch):
    """The branch's newest commit."""
    return git(repo, "rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}")


def base(repo, commit):
    """Where `commit` left main."""
    return git(repo, "merge-base", main_ref(), commit)


def fix_branches(repo, prefix):
    """The local branches whose names start with `prefix`, sorted."""
    listed = git(repo, "for-each-ref", "--format=%(refname:short)", f"refs/heads/{prefix}*")
    return sorted(line for line in listed.splitlines() if line)


def landing_order(branches):
    """The fixed order branches land in: by name."""
    return sorted(branches)


def commits_of(repo, since, commit):
    """The commits past `since` up to `commit`, oldest first."""
    return git(repo, "rev-list", "--reverse", f"{since}..{commit}").split()


def conflicted(tree):
    """The files a stopped cherry-pick left in conflict."""
    return git(tree, "diff", "--name-only", "--diff-filter=U").split()


def pick(tree, branch, commits):
    """Apply `commits` on the scratch tree's HEAD, in order; Conflict naming the branch and files when one does not
    apply cleanly (the pick is aborted)."""
    for commit in commits:
        done = subprocess.run(["git", "-C", str(tree), "cherry-pick", "--allow-empty", commit], capture_output=True,
                              text=True)
        if done.returncode != 0:
            files = conflicted(tree)
            subprocess.run(["git", "-C", str(tree), "cherry-pick", "--abort"], capture_output=True)
            raise Conflict(f"{branch} does not rebase onto main after what lands before it: "
                           f"{', '.join(files) or done.stderr.strip()[-300:]}")


def rebased(repo, tree, heads):
    """Rebase each branch of `heads` ({branch: commit}) onto the scratch tree, in the landing order; [{branch,
    commits}] of the new commits each one landed as."""
    landed = []
    for branch in landing_order(heads):
        before = git(tree, "rev-parse", "HEAD")
        pick(tree, branch, commits_of(repo, base(repo, heads[branch]), heads[branch]))
        landed.append({"branch": branch, "commits": commits_of(tree, before, "HEAD")})
    return landed


def scratch(repo, commit):
    """A detached checkout of `commit` in a new temp folder; its path."""
    holder = pathlib.Path(tempfile.mkdtemp(prefix="checkout-"))
    tree = holder / "tree"
    git(repo, "worktree", "add", "-q", "--detach", str(tree), commit)
    return tree


def drop(repo, tree):
    git(repo, "worktree", "remove", "--force", str(tree))
    shutil.rmtree(tree.parent, ignore_errors=True)


def land(repo, heads):
    """Land `heads` ({branch: the commit the owner saw}) on main: fetch, rebase each in the landing order in a scratch
    tree, push the result to main (refused by git when main moved meanwhile); {main_before, main_after, landed}.
    Conflict before anything is pushed when a branch does not rebase cleanly."""
    fetch(repo)
    before = git(repo, "rev-parse", main_ref())
    tree = scratch(repo, before)
    try:
        landed = rebased(repo, tree, heads)
        after = git(tree, "rev-parse", "HEAD")
        git(tree, "push", "-q", REMOTE, f"{after}:refs/heads/{MAIN}")
    finally:
        drop(repo, tree)
    fetch(repo)
    return {"main_before": before, "main_after": after, "landed": landed}


def clean_main_refusal(repo):
    """Why the store machine's checkout cannot take the landed main by a fast-forward (not on main, or changes not
    committed), or None."""
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != MAIN:
        return f"the runner's checkout is on {branch}, not {MAIN}"
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        return "the runner's checkout has changes not committed"
    return None


def fast_forward(repo, commit):
    """Bring the runner's own checkout of main to `commit` (a fast-forward only)."""
    git(repo, "merge", "-q", "--ff-only", commit)
