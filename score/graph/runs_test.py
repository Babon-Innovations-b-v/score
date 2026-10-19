"""The run registry names every run a reboot cut off, and `score resume` starts each again from its own worktree.

Run: .venv/bin/python score/graph/runs_test.py
"""
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.graph import runs, stopped  # noqa: E402
from score.store import partial_of  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]


EARLIER_BOOT = "00000000-0000-0000-0000-000000000000"


def live_store_swept():
    raise AssertionError("a unit test swept the live store's .partial files: pass swept=()")


runs.store_roots = live_store_swept  # C9 review: resume with no `swept` deleted .partial files in the real store


def a_worktree(python=None):
    """A git worktree of the test's own, committed and clean (its .venv ignored), with `python` as its
    .venv/bin/python when given; the folder and its commit."""
    worktree = pathlib.Path(tempfile.mkdtemp())
    (worktree / ".gitignore").write_text(".venv/\nstarts\n")
    if python is not None:
        (worktree / ".venv/bin").mkdir(parents=True)
        (worktree / ".venv/bin/python").write_text(python)
        (worktree / ".venv/bin/python").chmod(0o755)
    git = ["git", "-C", str(worktree), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "the run's code"], check=True)
    return worktree, runs.commit_of(worktree)


def an_entry(folder, name, **fields):
    entry = {"id": name, "argv": ["run", "world1", "--place", "hangar"], "commit": "c0ffee", "worktree": str(REPO),
             "pid": 1, "boot": EARLIER_BOOT, "started": "2026-10-17T08:00:00+00:00", "state": runs.RUNNING,
             **fields}
    (folder / f"{name}.json").write_text(json.dumps(entry))
    return entry


def test_only_a_run_an_earlier_boot_cut_off_is_listed_by_resume_dry():
    home = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree()
    try:
        (home / "runs").mkdir()
        an_entry(home / "runs", "cut-off", worktree=str(worktree), commit=commit)
        an_entry(home / "runs", "other-commit", worktree=str(worktree), commit="c0ffee")
        an_entry(home / "runs", "finished", state=runs.ENDED)
        an_entry(home / "runs", "stopped-by-the-owner", state=runs.STOPPED)
        an_entry(home / "runs", "this-boot", boot=runs.boot_id())  # alive, or killed since boot: never resumed
        an_entry(home / "runs", "before-boots-were-kept", boot=None)
        done = subprocess.run([sys.executable, "-m", "score", "resume", "--dry"], cwd=REPO, capture_output=True,
                              text=True, env={**os.environ, "PROPS_HOME": str(home)})
        assert done.returncode == 0, done.stderr
        lines = done.stdout.strip().splitlines()
        assert lines == [f"would resume cut-off: worktree={worktree} commit={commit[:12]} argv=run world1 --place hangar",
                         f"would skip other-commit: worktree={worktree} commit=c0ffee argv=run world1 --place hangar: "
                         f"its worktree is at {commit[:12]}, not the commit that registered it"], lines
        assert json.loads((home / "runs/cut-off.json").read_text())["state"] == runs.RUNNING  # a dry run marks none
        assert json.loads((home / "runs/other-commit.json").read_text())["state"] == runs.RUNNING
    finally:
        shutil.rmtree(home)
        shutil.rmtree(worktree)


def test_a_registered_run_records_its_arguments_commit_worktree_and_boot_until_it_ends():
    folder = pathlib.Path(tempfile.mkdtemp())
    try:
        path = runs.register(["run", "world1", "--detach", "--jobs", "2"], folder=folder)
        entry = json.loads(path.read_text())
        assert entry["argv"] == ["run", "world1", "--jobs", "2"] and entry["pid"] == os.getpid()
        assert entry["worktree"] == str(REPO) and len(entry["commit"]) == 40 and entry["state"] == runs.RUNNING
        assert entry["boot"] == runs.boot_id()
        assert runs.stranded(folder) == {}  # this boot's
        runs.mark(path, runs.ENDED)
        assert runs.entries(folder)[path]["state"] == runs.ENDED
    finally:
        shutil.rmtree(folder)


def test_a_run_the_owner_stopped_is_marked_stopped_and_a_shutdown_leaves_it_running():
    """C9 review: Ctrl-C, a deliberate kill or a closed session left the run `running`, so resume would buy again
    what the owner chose to stop; only a SIGTERM while the machine shuts down is a reboot's."""
    folder = pathlib.Path(tempfile.mkdtemp())
    shutting_down = runs.shutting_down
    try:
        for number, down, state in ((signal.SIGINT, True, runs.STOPPED), (signal.SIGHUP, True, runs.STOPPED),
                                    (signal.SIGTERM, False, runs.STOPPED), (signal.SIGTERM, True, runs.RUNNING)):
            runs.shutting_down = lambda: down
            path = runs.register(["run", "world1"], folder=folder)
            runs.stopped_by(path, number)
            assert runs.entries(folder)[path]["state"] == state, (number, down)
            path.unlink()
    finally:
        runs.shutting_down = shutting_down
        shutil.rmtree(folder)


def test_score_run_stopped_by_ctrl_c_registers_as_stopped():
    from score import __main__ as command
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = runs.RUNS, {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}

    class Stopped:
        def drive(self, *arguments, **options):
            os.kill(os.getpid(), signal.SIGINT)

    class Options:
        jobs, stage = 1, None
    try:
        runs.RUNS = folder
        try:
            stopped.stop_on_signals(lambda number: None)  # as_run's handlers, installed before driven
            command.driven(Stopped(), [], True, Options(), ["run", "world1"])
        except SystemExit as stop:
            assert stop.code == 128 + signal.SIGINT
        else:
            raise AssertionError("the run went on after Ctrl-C")
        assert [entry["state"] for entry in runs.entries(folder).values()] == [runs.STOPPED]
    finally:
        runs.RUNS = kept[0]
        for number, handler in kept[1].items():
            signal.signal(number, handler)
        shutil.rmtree(folder)


def test_two_resumes_at_once_start_a_run_once():
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\nsleep 0.3; echo started >> "$PWD/starts"\n')
    try:
        an_entry(folder, "cut-off", worktree=str(worktree), commit=commit)
        both = [threading.Thread(target=runs.resume, args=(False, lambda line: None),
                                 kwargs={"folder": folder, "swept": ()}) for _ in range(2)]
        for each in both:
            each.start()
        for each in both:
            each.join()
        assert (worktree / "starts").read_text().splitlines() == ["started"]
    finally:
        shutil.rmtree(folder)
        shutil.rmtree(worktree)


def test_resume_clears_the_partial_files_an_earlier_boot_left():
    """C9 review: a write SIGKILLed or cut by a reboot leaves its .partial file, and nothing removed it."""
    folder, objects = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    try:
        old = partial_of(objects / "records/clean@hangar/k1.json")
        old.write_text("{")
        os.utime(old, (runs.boot_time() - 60, runs.boot_time() - 60))
        new = partial_of(objects / "records/clean@hangar/k2.json")
        new.write_text("{")  # this boot's: a write going on now
        said = []
        runs.resume(False, said.append, folder=folder, swept=(objects,))
        assert not old.exists() and new.exists(), said
        assert any(str(old) in line for line in said), said
    finally:
        shutil.rmtree(folder)
        shutil.rmtree(objects)


def test_resume_starts_a_run_again_detached_from_its_own_worktree_and_marks_it():
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\necho "detached: started in $(pwd) with $*"\n')
    try:
        entry = an_entry(folder, "cut-off", worktree=str(worktree), commit=commit)
        assert runs.restart_command(entry) == [str(worktree / ".venv/bin/python"), "-m", "score", *entry["argv"],
                                               "--detach"]
        said = []
        assert runs.resume(False, said.append, folder=folder, swept=()) == 1
        assert said[0].startswith("resumed cut-off") and f"started in {worktree} with -m score run" in said[0], said
        assert runs.entries(folder)[folder / "cut-off.json"]["state"] == runs.RESUMED
        assert runs.stranded(folder) == {}  # never started twice
    finally:
        shutil.rmtree(folder)
        shutil.rmtree(worktree)


def test_a_run_whose_worktree_is_gone_is_skipped_and_marked_unresumable():
    """C9 review: a skipped run stayed `running`, so every boot tried it again and only a journal line said so."""
    folder = pathlib.Path(tempfile.mkdtemp())
    try:
        an_entry(folder, "orphan", worktree=str(folder / "gone"))
        said = []
        runs.resume(False, said.append, folder=folder, swept=())
        assert said[0].startswith("skipped orphan") and "worktree is gone" in said[0], said
        entry = runs.entries(folder)[folder / "orphan.json"]
        assert entry["state"] == runs.UNRESUMABLE and "worktree is gone" in entry["why"], entry
        assert runs.stranded(folder) == {}  # never tried again
        assert [line.split(":")[0] for line in runs.unresumable(folder)] == ["orphan"]
    finally:
        shutil.rmtree(folder)


def test_a_run_whose_worktree_moved_on_or_has_changes_is_never_started_again():
    """C9 review: resume ran whatever the worktree had checked out at the next boot, maybe days later on another
    branch, with changes not committed too."""
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\necho started >> "$PWD/starts"\n')
    try:
        an_entry(folder, "moved-on", worktree=str(worktree), commit="c0ffee")
        said = []
        runs.resume(False, said.append, folder=folder, swept=())
        (worktree / "stage.py").write_text("changed = True\n")
        an_entry(folder, "changed", worktree=str(worktree), commit=commit)
        runs.resume(False, said.append, folder=folder, swept=())
        assert not (worktree / "starts").exists(), said
        found = runs.entries(folder)
        assert found[folder / "moved-on.json"]["state"] == runs.UNRESUMABLE, said
        assert "not the commit that registered it" in found[folder / "moved-on.json"]["why"]
        assert found[folder / "changed.json"]["state"] == runs.UNRESUMABLE, said
        assert "changes not committed" in found[folder / "changed.json"]["why"]
    finally:
        shutil.rmtree(folder)
        shutil.rmtree(worktree)


def test_a_run_silent_long_before_this_boot_is_not_a_reboots_and_is_never_started_again():
    """C9 review: a run OOM-killed or SIGKILLed stays `running`, and any later boot, days on, bought it again."""
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\necho started >> "$PWD/starts"\n')
    try:
        an_entry(folder, "killed-days-ago", worktree=str(worktree), commit=commit)
        silent = runs.boot_time() - runs.RESUME_WINDOW - 60
        os.utime(folder / "killed-days-ago.json", (silent, silent))
        said = []
        runs.resume(False, said.append, folder=folder, swept=())
        assert not (worktree / "starts").exists(), said
        entry = runs.entries(folder)[folder / "killed-days-ago.json"]
        assert entry["state"] == runs.UNRESUMABLE and "last sign of life" in entry["why"], entry
    finally:
        shutil.rmtree(folder)
        shutil.rmtree(worktree)


def test_a_driving_run_touches_its_entry_so_resume_knows_it_was_alive():
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = runs.HEARTBEAT
    try:
        path = runs.register(["run", "world1"], folder=folder)
        os.utime(path, (1, 1))
        runs.HEARTBEAT = 0.05
        with runs.beating(path):
            time.sleep(0.3)
        assert path.stat().st_mtime > 1
    finally:
        runs.HEARTBEAT = kept
        shutil.rmtree(folder)


def test_a_restart_that_fails_is_marked_unresumable_with_its_error():
    """C9 review: a restart refused (by the rebuy gate, say) stayed `running` and was tried on every boot."""
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\necho "refused: re-buys over EUR 5" >&2; exit 1\n')
    try:
        an_entry(folder, "refused", worktree=str(worktree), commit=commit)
        said = []
        runs.resume(False, said.append, folder=folder, swept=())
        entry = runs.entries(folder)[folder / "refused.json"]
        assert entry["state"] == runs.UNRESUMABLE and "refused: re-buys" in entry["why"], (entry, said)
        assert said[0].startswith("failed refused"), said
    finally:
        shutil.rmtree(folder)
        shutil.rmtree(worktree)


def test_a_stop_as_the_run_registers_leaves_it_stopped_never_running():
    """C9 review: the entry was written before the stopping signals were handled, so a Ctrl-C in between raised
    KeyboardInterrupt and left it `running`, for a later boot to buy again."""
    from score import __main__ as command
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = runs.RUNS, runs.written, {number: signal.getsignal(number) for number in
                                     (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}

    def written_then_stopped(path, entry):
        kept[1](path, entry)
        os.kill(os.getpid(), signal.SIGINT)
        return path

    class Options:
        jobs, stage = 1, None
    try:
        runs.RUNS, runs.written = folder, written_then_stopped
        try:
            stopped.stop_on_signals(lambda number: None)  # as_run's handlers, installed before driven
            command.driven(object(), [], True, Options(), ["run", "world1"])
        except SystemExit as stop:
            assert stop.code == 128 + signal.SIGINT
        assert [entry["state"] for entry in runs.entries(folder).values()] == [runs.STOPPED]
    finally:
        runs.RUNS, runs.written = kept[0], kept[1]
        for number, handler in kept[2].items():
            signal.signal(number, handler)
        shutil.rmtree(folder)


def test_a_detached_run_logs_under_props_home_not_tmp():
    assert runs.LOGS == runs.PROPS_HOME / "logs"


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
