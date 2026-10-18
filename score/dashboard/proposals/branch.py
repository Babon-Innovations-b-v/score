"""The git side of a proposal: the branch's commit, what it adds over main, and a scratch checkout of it."""
import contextlib
import pathlib
import re
import shutil
import subprocess
import tempfile

MAIN = "origin/main"
SCOPE = re.compile(r"^[a-z0-9_./-]+: ")


def git(repo, *arguments):
    """git's output in `repo`, stripped; raises with git's words when it fails."""
    done = subprocess.run(["git", "-C", str(repo), *arguments], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)}: {done.stderr.strip()}")
    return done.stdout.strip()


def tip(repo, branch):
    """The branch's newest commit."""
    return git(repo, "rev-parse", "--verify", f"{branch}^{{commit}}")


def base(repo, commit):
    """Where the commit's branch left main."""
    return git(repo, "merge-base", MAIN, commit)


def commits(repo, since, commit):
    """[{sha, subject}] of the commits past `since`, oldest first."""
    lines = git(repo, "log", "--reverse", "--format=%H %s", f"{since}..{commit}").splitlines()
    return [{"sha": sha, "subject": subject} for sha, _, subject in (line.partition(" ") for line in lines)]


def change_sentence(listed):
    """One plain sentence of what the commits change: their subjects without the scope, joined."""
    parts = [SCOPE.sub("", item["subject"]).strip().rstrip(".") for item in listed]
    parts = [part for part in parts if part]
    if not parts:
        return ""
    sentence = "; ".join(parts)
    return sentence[0].upper() + sentence[1:] + "."


@contextlib.contextmanager
def scratch_tree(repo, commit, under):
    """A detached checkout of `commit` in a new folder under `under` while the block runs; removed after."""
    pathlib.Path(under).mkdir(parents=True, exist_ok=True)
    holder = pathlib.Path(tempfile.mkdtemp(prefix="tree-", dir=under))
    tree = holder / "tree"
    git(repo, "worktree", "add", "-q", "--detach", str(tree), commit)
    try:
        yield tree
    finally:
        git(repo, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(holder, ignore_errors=True)
