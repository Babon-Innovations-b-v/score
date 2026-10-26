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


def test_a_run_waiting_for_size_is_left_on_too_few_cores_and_resumed_on_the_batch_size():
    """The conductor: a run asking for more cores than the machine has waits for the grow, and the boot on the batch
    size starts it like a cut-off run; a boot on the idle size (a maintenance reboot) leaves it waiting."""
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\necho "detached: started with $*"\n')
    cores = os.cpu_count
    try:
        an_entry(folder, "waiting", worktree=str(worktree), commit=commit, state=runs.WAITING, jobs=16,
                 argv=["run", "world1", "--jobs", "16"])
        an_entry(folder, "waiting-this-boot", state=runs.WAITING, jobs=16, boot=runs.boot_id())
        assert list(runs.stranded(folder)) == [folder / "waiting.json"]
        said = []
        os.cpu_count = lambda: 2
        assert runs.resume(False, said.append, folder=folder, swept=()) == 1
        assert said[0].startswith("left waiting") and "still waiting for size: it asks for 16 jobs" in said[0], said
        assert runs.entries(folder)[folder / "waiting.json"]["state"] == runs.WAITING
        os.cpu_count = lambda: 16
        said.clear()
        runs.resume(False, said.append, folder=folder, swept=())
        assert said[0].startswith("resumed waiting") and "--jobs 16 --detach" in said[0], said
        assert runs.entries(folder)[folder / "waiting.json"]["state"] == runs.RESUMED
        assert [entry["id"] for entry in runs.waiting(folder).values()] == ["waiting-this-boot"]
    finally:
        os.cpu_count = cores
        shutil.rmtree(folder)
        shutil.rmtree(worktree)


def test_a_sigterm_during_a_resize_the_size_timer_asked_for_leaves_the_run_as_it_was():
    """The conductor's grow or shrink powers the machine off: its SIGTERM is a shutdown's even when systemd cannot
    say so yet, and the owner's own SIGTERM outside a resize, or to a run registered after the ask, still stops it."""
    from score import conductor
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = runs.shutting_down, conductor.RESIZING
    runs.shutting_down = lambda: False
    conductor.RESIZING = folder / "resizing.json"
    try:
        # the last: a run registered a minute after the ask (his Buy after a resize the function refused)
        for marked, state in ((0, runs.WAITING), (-conductor.RESIZE_WINDOW - 60, runs.STOPPED), (None, runs.STOPPED),
                              (60, runs.STOPPED)):
            path = runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=folder)
            if marked is not None:
                registered = runs.registered_at(path)
                asked = registered - 60 if marked == 60 else time.time() + marked
                conductor.RESIZING.write_text(json.dumps({"action": "grow", "at": asked}))
            runs.stopped_by(path, signal.SIGTERM)
            assert runs.entries(folder)[path]["state"] == state, (marked, state)
            path.unlink()
            conductor.RESIZING.unlink(missing_ok=True)
    finally:
        runs.shutting_down, conductor.RESIZING = kept
        shutil.rmtree(folder)


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


def test_the_claims_beside_the_entries_are_not_a_run():
    """C9 and C10 share runs/: the store's claims (active.json) are never read as a run's entry."""
    folder = pathlib.Path(tempfile.mkdtemp())
    try:
        assert runs.claim("aaa111", ["draw@hangar"], os.getpid(), worktree="/work/one", folder=folder) is None
        entry = an_entry(folder, "20261017T080000-1")
        assert (folder / runs.ACTIVE).exists() and list(runs.entries(folder).values()) == [entry]
    finally:
        shutil.rmtree(folder)


def test_the_pool_rents_each_machine_its_start_up_before_its_first_job_and_lets_it_go_over_a_longer_gap():
    """Owner, 2026-10-25: "cant u just do the start up earlier then when u need them again" (Batch 1: three
    processor machines idle an hour, ten cards idle while the close-ups ran 2.5 h). A forecast of when each pooled
    row's first job is due (the rows it reads still to run, at their minutes): a machine is held from its start-up
    (the lead) before that, and let go while its next job is further away."""
    import datetime
    import types
    from score import __main__ as command
    reads = {"close@a": [], "model@a": ["close@a"], "bake@a": ["model@a"], "pixal@a": ["close@a"],
             "finish@a": ["pixal@a"], "judge@a": ["finish@a"]}
    started = time.time() - 60
    standing = {}

    def ends(node):
        standing[node] = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    runner = types.SimpleNamespace(
        store=types.SimpleNamespace(current_accept=standing.get),
        nodes_named=lambda names: iter([(name, None) for name in names]),
        earlier=lambda node, _place: reads[node],
        desk=lambda area, node, ending: pathlib.Path(tempfile.gettempdir()) / "no-such-fault" / f"{node}{ending}")
    leads = {False: 8.0, True: 8.0}  # each class's measured start-up and its margin (pool.leads)
    kept = command.POOLED_ROWS[:], dict(command.PAID_MINUTES)
    command.POOLED_ROWS[:] = [("bake@a", "a", 2, True), ("pixal@a", "a", 3, False), ("judge@a", "j", 1, False)]
    command.PAID_MINUTES.clear()
    command.PAID_MINUTES.update({"close@a": 150.0, "model@a": 30.0, "bake@a": 20.0, "pixal@a": 60.0,
                                 "finish@a": 40.0, "judge@a": 10.0})
    try:
        assert command.due_rows(runner, started, leads) == []  # the close-ups first: nothing rented for 2.5 h
        ends("close@a")
        assert command.due_rows(runner, started, leads) == [("a", 3, False)]  # Pixal3D due now; the bake 30 min on
        command.PAID_MINUTES["model@a"] = 6.0
        assert ("a", 2, True) in command.due_rows(runner, started, leads)  # due in 6 min, within its 8 min lead
        for node in ("pixal@a", "model@a", "bake@a"):
            ends(node)
        assert command.due_rows(runner, started, leads) == []  # the judge 40 min away: its card goes meanwhile
        command.PAID_MINUTES["finish@a"] = 5.0
        assert command.due_rows(runner, started, leads) == [("j", 1, False)]  # a 5 min gap: the card is held
    finally:
        command.POOLED_ROWS[:] = kept[0]
        command.PAID_MINUTES.clear()
        command.PAID_MINUTES.update(kept[1])
    chain = {"c": ["b"], "b": ["a"], "a": []}
    assert command.due_in("c", chain.get, lambda node: 10.0, lambda node: "stopped" if node == "a" else "todo",
                          {}) == float("inf")  # a row it reads stopped: never due


def test_a_pool_holding_no_machine_while_rows_are_due_on_it_is_said_with_why():
    """Fault of 2026-10-26: a benchmark's Pixal3D rows waited an hour on a pool whose card had gone (every card class
    sold out) and the run's log said nothing. Its heartbeat says it once the pool is empty POOL_EMPTY_SAY_SECONDS
    while rows are due, with the collector's last line, then each POOL_EMPTY_SAY_SECONDS; quiet with a machine in."""
    import contextlib
    import io
    import types
    from score import __main__ as command
    state = {"members": [], "plan": {"collector": os.getpid()}}
    pool = types.SimpleNamespace(members=lambda run_id: state["members"], current=lambda run_id: state["plan"],
                                 collector_alive=lambda plan: True,
                                 collector_said=lambda run_id: "[cloud] pool: 1 card(s) short, none in stock")
    due, step = [("a", 3, False)], command.POOL_EMPTY_SAY_SECONDS

    def said(now):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            command.said_empty_pool(pool, "run", due, now)
        return out.getvalue()
    command.POOL_EMPTY.clear()
    try:
        assert said(1000.0) == "" and said(1000.0 + step - 1) == ""  # a pool just opened: its first card is coming
        line = said(1000.0 + step)
        assert "no machine for 10 min while 1 row is due" in line and "none in stock" in line, line
        assert said(1000.0 + step + 60) == ""  # said again only after another POOL_EMPTY_SAY_SECONDS
        state["plan"] = None
        assert "it is closed" in said(1000.0 + 2 * step)
        state["members"] = [{"id": "card-1"}]
        assert said(1000.0 + 3 * step) == "" and command.POOL_EMPTY == {}  # a machine in: quiet, counted afresh
    finally:
        command.POOL_EMPTY.clear()


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
