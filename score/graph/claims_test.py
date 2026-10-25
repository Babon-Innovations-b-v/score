"""One commit per store (graph/runs.py's claims, C10), both ways, on a registry folder of its own: a live run from
another commit is refused and named; a claim whose pid is gone is ignored; a run at the same commit joins with
disjoint nodes and is refused with shared ones it would make (environment nodes every place reads count only while
not made); a pid reused by another process is not the run; a released run frees the store; a worktree with tracked changes not committed is refused
without --uncommitted when it would buy a paid row, and registers as a commit of its own.

Run: .venv/bin/python score/graph/claims_test.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.graph import runs  # noqa: E402


def a_live_pid():
    """A process of this test's own that stays alive (the test's own pid is the registering run's)."""
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])


def a_dead_pid():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_another_commit_live_is_refused_and_named(folder, other):
    assert runs.claim("aaa111", ["draw@hangar"], other.pid, worktree="/work/one", folder=folder) is None
    refused = runs.claim("bbb222", ["bake@garage"], os.getpid(), worktree="/work/two", folder=folder)
    assert refused and f"pid {other.pid}" in refused and "aaa111" in refused and "/work/one" in refused, refused
    assert runs.claim_refusal("bbb222", ["bake@garage"], folder=folder) == refused


def test_a_dead_pid_is_ignored(folder):
    assert runs.claim("aaa111", ["draw@hangar"], a_dead_pid(), worktree="/work/one", folder=folder) is None
    assert runs.claim("bbb222", ["draw@hangar"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)


def test_same_commit_joins_only_with_disjoint_nodes(folder, other):
    assert runs.claim("aaa111", ["draw@hangar", "terrain"], other.pid, worktree="/work/one", folder=folder) is None
    assert runs.claim("aaa111", ["draw@garage"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)
    refused = runs.claim("aaa111", ["terrain", "draw@garage"], os.getpid(), worktree="/work/two", folder=folder)
    assert refused and "terrain" in refused and f"pid {other.pid}" in refused, refused


def test_a_released_run_frees_the_store(folder, other):
    assert runs.claim("aaa111", ["draw@hangar"], other.pid, worktree="/work/one", folder=folder) is None
    runs.unclaim(other.pid, folder=folder)
    assert runs.claim("bbb222", ["draw@hangar"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)


def test_a_reused_pid_is_not_the_run_that_registered(folder, other):
    """A dead run's pid taken by an unrelated process: its start time is not the registered one, so it is dead."""
    assert runs.claim("aaa111", ["draw@hangar"], other.pid, worktree="/work/one", folder=folder) is None
    path = folder / "active.json"
    entries = json.loads(path.read_text())
    entries[str(other.pid)]["started"] = "1"  # the run that registered started at another time
    path.write_text(json.dumps(entries))
    assert runs.claim("bbb222", ["draw@hangar"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)


def test_two_places_of_world1_at_one_commit_both_run_once_the_world_nodes_stand(folder, other):
    """Fault (review of C10): every place reads world nodes (terrain) and other shared nodes, so comparing every
    planned node refused the second `score run world1 --place <place>` always. Only nodes a run would make count."""
    from score import graph, stages
    from score.store import Store
    runner = stages.runner(store=Store.in_folder(tempfile.mkdtemp()), world=stages.WORLDS["world1"]())
    airlock, camp = (runner.line_nodes([place], False) for place in ("airlock", "camp"))
    shared = {graph.node_name(*node) for node in airlock} & {graph.node_name(*node) for node in camp}
    assert "terrain" in shared, shared
    # every node the two lines share stands (the world's terrain, the shared people line's rows since c9455eca)
    runner.standing = lambda stage, place, gapped=False: None if graph.node_name(stage, place) in shared else "never ran"
    assert runs.claim("aaa111", runs.would_make(runner, airlock), other.pid, worktree="/work/one",
                         folder=folder) is None
    assert runs.claim("aaa111", runs.would_make(runner, camp), os.getpid(), worktree="/work/two",
                         folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)
    standing = shared - {"terrain"}  # terrain not made yet: both would make it
    runner.standing = lambda stage, place, gapped=False: None if graph.node_name(stage, place) in standing else "never ran"
    runs.unclaim(other.pid, folder=folder)
    assert runs.claim("aaa111", runs.would_make(runner, airlock), other.pid, worktree="/work/one",
                         folder=folder) is None
    refused = runs.claim("aaa111", runs.would_make(runner, camp), os.getpid(), worktree="/work/two",
                            folder=folder)
    assert refused and "terrain" in refused, refused


def test_changes_not_committed(folder):
    assert runs.dirty_refusal(True, uncommitted=False, paid=True)
    assert runs.dirty_refusal(True, uncommitted=True, paid=True) is None
    assert runs.dirty_refusal(True, uncommitted=False, paid=False) is None  # a free run keeps running as it is
    assert runs.dirty_refusal(False, uncommitted=False, paid=True) is None
    assert runs.identity("aaa111", True, "/work/one") != runs.identity("aaa111", True, "/work/two") != "aaa111"
    assert runs.identity("aaa111", False, "/work/one") == "aaa111"


def test_an_untracked_scratch_file_is_not_a_change(folder):
    repo = pathlib.Path(tempfile.mkdtemp())
    for command in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "one"]):
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *command], check=True)
    (repo / "scratch.txt").write_text("notes")
    assert not runs.tracked_changes(repo)
    (repo / "kept.txt").write_text("a")
    subprocess.run(["git", "-C", str(repo), "add", "kept.txt"], check=True)
    assert runs.tracked_changes(repo)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for test in [value for name, value in sorted(globals().items()) if name.startswith("test_")]:
        other = a_live_pid()
        try:
            arguments = {"folder": pathlib.Path(tempfile.mkdtemp()) / "runs", "other": other}
            test(**{name: arguments[name] for name in test.__code__.co_varnames[:test.__code__.co_argcount]})
        finally:
            other.kill()
            other.wait()
        print(f"ok {test.__name__}")
    print("runs_test: all passed")
