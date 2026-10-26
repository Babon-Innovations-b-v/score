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
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.graph import frozen  # noqa: E402
from score.store import Store  # noqa: E402

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


def test_removing_the_copy_ends_every_process_still_working_in_it_and_no_other():
    """2026-10-26: six processes of a stopped run worked on in its copy for an hour and held the checkout."""
    repo = a_repo()
    copy = frozen.make(repo, frozen.git(repo, "rev-parse", "HEAD"), tempfile.mkdtemp())
    other = copy.parent / "another-run"
    other.mkdir()
    sleep = [sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"]
    left, elsewhere = subprocess.Popen(sleep, cwd=copy), subprocess.Popen(sleep, cwd=other)
    try:
        time.sleep(0.3)
        assert frozen.users(copy.parent) == {left.pid: copy.name, elsewhere.pid: other.name}  # this one left out
        frozen.OWNED.update(path=copy, handed_on=False)
        frozen.END_GRACE_SECONDS = 0.5
        frozen.remove_owned()
        assert left.wait(5) == -9 and not copy.exists()  # one deaf to SIGTERM gets SIGKILL
        assert elsewhere.poll() is None  # another run's copy is not this one's
    finally:
        frozen.OWNED.update(path=None, handed_on=False)
        elsewhere.kill()
        left.kill()


def test_resume_gives_a_frozen_run_its_copy_back_and_another_worktree_nothing():
    copy = frozen.FOLDER / "20261020-181654-1"
    assert frozen.resumed_env(copy)[frozen.FROZEN] == str(copy) and frozen.resumed_env(copy)[frozen.OWNER] == "1"
    assert frozen.OWNER not in frozen.resumed_env(tempfile.mkdtemp())
    frozen.home_of(copy).mkdir(parents=True)  # a run with a home of its own resumes in it
    assert frozen.resumed_env(copy)["PROPS_HOME"] == str(frozen.home_of(copy))



def a_home():
    """A home with a read-only design (one place's surface data) and a store folder."""
    home = pathlib.Path(tempfile.mkdtemp())
    (home / "design" / "surfaces").mkdir(parents=True)
    (home / "design" / "surfaces" / "hangar.json").write_text('{"takes": 58}')
    (home / "store").mkdir()
    for folder in (home / "design" / "surfaces", home / "design"):
        folder.chmod(0o555)
    return home


def sync_pass_rewrites(home):
    """What a sync pass's prepare does mid-run: the place's surface data rewritten in the real design."""
    folder = home / "design" / "surfaces"
    folder.chmod(0o755)
    (folder / "hangar.json").chmod(0o644)
    (folder / "hangar.json").write_text('{"takes": 62}')


def test_a_runs_home_holds_its_design_as_it_started_and_shares_the_rest():
    home = a_home()
    copy = pathlib.Path(tempfile.mkdtemp()) / "20261025-161109-1"
    own = frozen.home_copy(copy, home)
    sync_pass_rewrites(home)
    assert (own / "design/surfaces/hangar.json").read_text() == '{"takes": 58}'
    (own / "store" / "record.json").write_text("{}")  # the store is the shared one
    assert (home / "store" / "record.json").exists()
    (own / "made").mkdir()  # something the run made at its home's top level
    frozen.home_closed(copy, home)
    assert (home / "made").is_dir() and (own / "made").is_symlink()
    assert (own / "design").is_symlink() and (own / "design/surfaces/hangar.json").read_text() == '{"takes": 62}'


def make_while_the_sync_pass_writes(inputs, out, seed, params):
    """A make during which a sync pass rewrites the design file the node reads (params: the real home)."""
    sync_pass_rewrites(pathlib.Path(params["home"]))
    (out / "palette.txt").write_text(inputs["surfaces"].read_text())


def test_a_design_file_rewritten_mid_run_moves_no_key_of_the_run_and_the_next_run_reads_it():
    """Batch 1, 2026-10-25: prepare rewrote every place's surface data mid-run; finish-route-list@street had "an input
    changed while it ran" and every palette "has not run on its current inputs"."""
    home = a_home()
    own = frozen.home_copy(pathlib.Path(tempfile.mkdtemp()) / "20261025-161109-1", home)
    text = contracts.Contract("toy-text", 1, lambda folder: [])
    stage = graph.Stage("palette", "place", make_while_the_sync_pass_writes, text,
                        (checks.Check("read", lambda output, inputs, evidence: checks.Verdict("read", checks.PASS,
                                                                                               "read")),),
                        files={"surfaces": "{home}/design/surfaces/{place}.json"}, params={"home": str(home)})
    store = Store.in_folder(tempfile.mkdtemp())

    def runner(root):
        return graph.Runner((stage,), graph.Environment("toy", 7, {"home": str(root)}), store,
                            model_record=lambda kind: {"kind": kind})
    running = runner(own)
    before = running.key(stage, "hangar")["key"]
    assert running.run(["hangar"])["palette@hangar"].startswith("made: pass")  # no "input changed while it ran"
    assert runner(own).key(stage, "hangar")["key"] == before  # its later nodes still find it on its inputs
    assert runner(home).key(stage, "hangar")["key"] != before  # the next run's home holds the new file


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
