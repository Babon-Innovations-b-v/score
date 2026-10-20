"""A run's frozen copy (#45): a clean tree is frozen at HEAD, a tree with changes at one commit of the whole working
tree with neither the index nor the stash moved; the copy is clean at that commit, links the running venv, outlives
a change in the checkout it came from, and is removed with its worktree entry; only the process that owns it removes
it, and `score resume` gives a frozen run its copy back. In a git repository of its own under a fresh PROPS_HOME.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/graph/frozen_test.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.graph import frozen  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test",
           "GIT_COMMITTER_EMAIL": "test@example.invalid"}


def a_repo():
    """A repository with one commit: a tracked file and a .gitignore that leaves out .venv."""
    repo = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "stage.py").write_text("SIZE = 1\n")
    (repo / ".gitignore").write_text(".venv\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "one"], check=True, env={**os.environ, **GIT_ENV})
    return repo


def test_a_clean_tree_is_frozen_at_head_and_a_pull_after_does_not_reach_the_copy():
    repo = a_repo()
    head = frozen.git(repo, "rev-parse", "HEAD")
    commit, changes = frozen.snapshot(repo)
    assert (commit, changes) == (head, False)
    copy = frozen.make(repo, commit, tempfile.mkdtemp())
    (repo / "stage.py").write_text("SIZE = 2\n")  # the checkout moves on
    assert (copy / "stage.py").read_text() == "SIZE = 1\n"
    assert frozen.git(copy, "rev-parse", "HEAD") == head and frozen.git(copy, "status", "--porcelain") == ""
    frozen.remove(copy)
    assert not copy.exists() and str(copy) not in frozen.git(repo, "worktree", "list")


def test_a_tree_with_changes_is_frozen_whole_without_moving_the_index_or_the_stash():
    repo = a_repo()
    os.environ.update(GIT_ENV)
    (repo / "stage.py").write_text("SIZE = 3\n")
    (repo / "new.py").write_text("NEW = True\n")  # untracked: a finish record counts it, so the copy holds it
    commit, changes = frozen.snapshot(repo)
    assert changes and commit != frozen.git(repo, "rev-parse", "HEAD")
    assert frozen.git(repo, "rev-parse", f"{commit}^") == frozen.git(repo, "rev-parse", "HEAD")
    assert frozen.git(repo, "diff", "--cached", "--name-only") == "" and frozen.git(repo, "stash", "list") == ""
    copy = frozen.make(repo, commit, tempfile.mkdtemp())
    assert (copy / "stage.py").read_text() == "SIZE = 3\n" and (copy / "new.py").exists()
    if sys.prefix != sys.base_prefix:
        assert (copy / ".venv").resolve() == pathlib.Path(sys.prefix).resolve()
    assert frozen.git(copy, "status", "--porcelain") == ""  # the linked venv is ignored: the copy is clean
    frozen.remove(copy)


def test_only_the_owner_removes_the_copy_and_never_after_handing_it_on():
    repo = a_repo()
    copy = frozen.make(repo, frozen.git(repo, "rev-parse", "HEAD"), tempfile.mkdtemp())
    os.environ[frozen.FROZEN] = str(copy)
    try:
        assert frozen.inside() and frozen.claim() is None  # frozen, but not its owner: a node, a nested command
        os.environ[frozen.OWNER] = "1"
        assert frozen.claim() == copy and frozen.OWNER not in os.environ  # nothing it starts inherits the mark
        assert frozen.owner_env()[frozen.OWNER] == "1"
        frozen.hand_on()
        frozen.remove_owned()
        assert copy.exists()  # the detached run or the releaser removes it
        frozen.OWNED["handed_on"] = False
        frozen.remove_owned()
        assert not copy.exists()
        frozen.remove_owned()  # once only
    finally:
        os.environ.pop(frozen.FROZEN)
        frozen.OWNED.update(path=None, handed_on=False)


def test_resume_gives_a_frozen_run_its_copy_back_and_another_worktree_nothing():
    copy = frozen.FOLDER / "20261020-181654-1"
    assert frozen.resumed_env(copy)[frozen.FROZEN] == str(copy) and frozen.resumed_env(copy)[frozen.OWNER] == "1"
    assert frozen.OWNER not in frozen.resumed_env(tempfile.mkdtemp())


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
