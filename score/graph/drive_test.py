"""The runner drives every line to its end with no agent in the loop: it gathers a gate's missing evidence itself,
starts each node the moment the nodes it reads stand accepted, and a node that fails, errors or is blocked stops its
own line only, with a plain fault report. A toy table of two stages, two places, in a store of its own.

Fault (the owner, 2026-10-11): agents walked every job through its steps by hand, starting each cloud step, polling
it with sleep loops and starting the next, each holding hundreds of thousands of tokens of context.

Run: .venv/bin/python score/graph/drive_test.py
"""
import contextlib
import io
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
compute.ledger().open_books_for_tests(tempfile.mkdtemp())  # this month's books known: paid paths open
from score.graph import stopped  # noqa: E402
from score.store import Store  # noqa: E402

PLACES = ("hangar", "station")


def make_clean(inputs, out, seed, params):
    print("cleaning", inputs["brief"])
    if "explode" in inputs["brief"].read_text():
        raise RuntimeError("the cleaner fell over")
    if "quit" in inputs["brief"].read_text():
        raise SystemExit("the cleaner quit: no such material")
    (out / "clean.txt").write_text(inputs["brief"].read_text().upper())


def gather_limit(output, inputs, folder):
    with (data_of(inputs) / "gathered.txt").open("a") as gathered:  # each node runs in a process of its own
        gathered.write(f"{output.name} {os.environ.get(compute.TICKET)}\n")
    path = folder / "limit.json"
    path.write_text(json.dumps({"limit": 5}))
    return path


def judge_words(output, inputs, evidence):
    words = len((output / "clean.txt").read_text().split())
    limit = json.loads(evidence.read_text())["limit"]
    return checks.Verdict("words", checks.PASS if words <= limit else checks.FAIL, f"{words} words, limit {limit}",
                          {"words": words}, {"words": "lower"}, (f"{words - limit} words too many",) if words > limit
                          else ())


def judge_shout(output, inputs, evidence):
    shouted = "!" in (output / "clean.txt").read_text()
    return checks.Verdict("shout", checks.FAIL if shouted else checks.PASS, "shouts" if shouted else "no shouting")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text(str(len((inputs["clean"] / "clean.txt").read_text())))


def judge_count(output, inputs, evidence):
    return checks.Verdict("counted", checks.PASS, "a count was written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
WORDS = checks.Check("words", judge_words, evidence="a word limit")
COUNT = graph.Stage("count", "place", make_count, TEXT, (checks.Check("counted", judge_count),),
                    after={"clean": ("toy-text", 1)})


def a_runner(briefs, euros=None):
    data = pathlib.Path(tempfile.mkdtemp())
    for place, brief in briefs.items():
        (data / place).mkdir()
        (data / place / "brief.txt").write_text(brief)
    clean = graph.Stage("clean", "place", make_clean, TEXT, (WORDS, checks.Check("shout", judge_shout)),
                        files={"brief": "{data}/{place}/brief.txt"}, gatherers={"words": (gather_limit, euros)})
    return graph.Runner((clean, COUNT), graph.Environment("toy", 7, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                        model_record=lambda kind: {"kind": kind})


def data_of(inputs):
    return inputs["brief"].parents[1]


def gathered(runner):
    """Each gather's (output, spend ticket), as the nodes' processes wrote them."""
    path = runner.world.roots["data"] / "gathered.txt"
    return [tuple(line.split(" ", 1)) for line in path.read_text().splitlines()] if path.exists() else []


def quiet(line):
    pass


def report_of(runner, node):
    return runner.store.cache.parent / "faults" / f"{node}.txt"


def test_a_line_runs_to_its_end_its_evidence_gathered_by_the_runner():
    runner = a_runner({"hangar": "a ship", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"] == ("made: unknown; gathered words: judged again, output kept: pass, accepted "
                                     "automatically"), found
    assert found["count@hangar"] == found["count@station"] == "made: pass, accepted automatically", found
    assert len(gathered(runner)) == 2
    assert all(state == "done" for state, _ in runner.lines(PLACES).values()), runner.lines(PLACES)
    assert not (runner.store.cache.parent / "faults").exists()
    assert set(runner.drive(PLACES, say=quiet).values()) == {"fresh"} and len(gathered(runner)) == 2


def test_a_failing_gate_stops_its_own_line_only_with_a_fault_report():
    runner = a_runner({"hangar": "a ship in a very long dark hall", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["count@hangar"] == "not run: its line stopped at clean@hangar", found
    assert found["count@station"] == "made: pass, accepted automatically", found
    report = report_of(runner, "clean@hangar").read_text()
    assert "why its line stopped: clean@hangar answered fail: words: 8 words, limit 5" in report, report
    assert '  words: fail: 8 words, limit 5\n    measures: {"words": 8}\n    - 3 words too many' in report, report
    assert "cleaning" in report and "python -m score run toy --place hangar" in report, report
    lines = runner.lines(PLACES)
    assert lines["hangar"][0] == f"stopped at clean@hangar: fault report {report_of(runner, 'clean@hangar')}", lines
    assert lines["station"][0] == "done", lines

    (runner.world.roots["data"] / "hangar" / "brief.txt").write_text("a ship")  # put right: the line goes on
    found = runner.drive(PLACES, say=quiet)
    assert found["count@hangar"] == "made: pass, accepted automatically", found
    assert not report_of(runner, "clean@hangar").exists()


def test_nothing_is_gathered_for_an_output_another_gate_fails():
    runner = a_runner({"hangar": "a ship!"})
    found = runner.drive(["hangar"], say=quiet)
    assert found["clean@hangar"].startswith("made: fail; fault report"), found
    assert gathered(runner) == []
    assert "shout: fail: shouts" in report_of(runner, "clean@hangar").read_text()


def test_an_error_stops_its_line_with_its_traceback_in_the_report():
    runner = a_runner({"hangar": "explode", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("error: RuntimeError: the cleaner fell over; fault report"), found
    assert found["count@hangar"] == "not run: its line stopped at clean@hangar"
    assert found["count@station"] == "made: pass, accepted automatically", found
    report = report_of(runner, "clean@hangar").read_text()
    assert "Traceback" in report and "the cleaner fell over" in report, report


def test_a_system_exit_is_an_error_with_its_message_in_the_report():
    """surfaces-lists@lab, 2026-10-12: a SystemExit in a make ended the node's process with exit code 1 and nothing said."""
    runner = a_runner({"hangar": "quit", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("error: SystemExit: the cleaner quit: no such material; fault report"), found
    assert "the cleaner quit" in report_of(runner, "clean@hangar").read_text()
    assert found["count@station"] == "made: pass, accepted automatically", found


def test_a_missing_input_stops_its_line_with_a_fault_report():
    runner = a_runner({"station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("blocked: clean@hangar: its input brief is missing"), found
    assert "its input brief is missing" in report_of(runner, "clean@hangar").read_text()
    assert found["count@station"] == "made: pass, accepted automatically", found


def test_a_paid_gather_runs_inside_the_runners_clearance():
    books = compute.ledger()
    books.entries = lambda: []
    runner = a_runner({"hangar": "a ship"}, euros=0.2)
    assert runner.drive(["hangar"], say=quiet)["count@hangar"] == "made: pass, accepted automatically"
    key = runner.key(runner.stages["clean"], "hangar")["key"]
    assert [ticket for _, ticket in gathered(runner)] == [f"clean@hangar {key}"]
    assert runner.store.clearances("clean@hangar", key)[0]["euros"] == 0.2


# --- lines side by side ----------------------------------------------------------------------------------------------

MEETING_SECONDS = 20


def meeting(data, me, others):
    """A make that says it started, then waits until every other named make started too: done one at a time, the
    first waits alone and fails."""
    def make(inputs, out, seed, params):
        (data / f"{me}.started").touch()
        deadline = time.monotonic() + MEETING_SECONDS
        while not all((data / f"{other}.started").exists() for other in others):
            if time.monotonic() > deadline:
                raise RuntimeError(f"{me} waited alone: {', '.join(others)} never started beside it")
            time.sleep(0.05)
        (out / "met.txt").write_text(me)
    return make


def meet_the_other_places(data):
    """A place's make that meets every other place's (its place is its declared input's folder name)."""
    def make(inputs, out, seed, params):
        place = inputs["place"].name
        meeting(data, place, [other for other in PLACES if other != place])(inputs, out, seed, params)
    return make


def made_once(data):
    def make(inputs, out, seed, params):
        with (data / "ground-made.txt").open("a") as made:
            made.write("made\n")
        (out / "ground.txt").write_text("ground")
    return make


def judge_met(output, inputs, evidence):
    return checks.Verdict("met", checks.PASS, "it ran")


MET = (checks.Check("met", judge_met),)


def a_world_of(places):
    data = pathlib.Path(tempfile.mkdtemp())
    for place in places:
        (data / place).mkdir()
    return data, graph.Environment("toy", 7, {"data": data})


def test_lines_run_side_by_side_and_one_line_waiting_holds_up_no_other():
    """Fault (the owner, 2026-10-11: nothing waits for the slowest): the drive ran one node at a time, so while one
    place waited on the cloud every other place waited too."""
    data, world = a_world_of(PLACES)
    meet = graph.Stage("meet", "place", meet_the_other_places(data), TEXT, MET, files={"place": "{data}/{place}"})
    runner = graph.Runner((meet,), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    started = time.monotonic()
    found = runner.drive(PLACES, say=quiet)
    assert set(found.values()) == {"made: pass, accepted automatically"}, found
    assert time.monotonic() - started < MEETING_SECONDS


def test_nodes_of_one_line_that_read_nothing_of_each_other_run_side_by_side():
    data, world = a_world_of(["hangar"])
    first = graph.Stage("first", "place", meeting(data, "first", ["second"]), TEXT, MET)
    second = graph.Stage("second", "place", meeting(data, "second", ["first"]), TEXT, MET)
    runner = graph.Runner((first, second), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet)
    assert set(found.values()) == {"made: pass, accepted automatically"}, found


def test_a_world_node_every_line_reads_is_made_once_and_each_line_waits_on_it_alone():
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_count_of_ground, TEXT, MET, after={"ground": ("toy-text", 1)})
    runner = graph.Runner((ground, build), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    found = runner.drive(PLACES, say=quiet)
    assert set(found.values()) == {"made: pass, accepted automatically"}, found
    assert list(found) == ["ground", "build@hangar", "build@station"], found
    assert (data / "ground-made.txt").read_text() == "made\n"


def test_a_places_own_lines_run_only_the_world_nodes_they_read():
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    sky = graph.Stage("sky", "world", meeting(data, "sky", ["never"]), TEXT, MET)  # no place reads it
    build = graph.Stage("build", "place", make_count_of_ground, TEXT, MET, after={"ground": ("toy-text", 1)})
    runner = graph.Runner((ground, sky, build), world, Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet, whole=False)
    assert found == {"ground": "made: pass, accepted automatically",
                     "build@hangar": "made: pass, accepted automatically"}, found
    assert set(runner.lines(["hangar"], whole=False)) == {"world", "hangar"}
    assert list(runner.lines(["hangar"], whole=False)["world"][1]) == ["ground"]


def test_a_line_run_for_one_stage_runs_it_and_what_it_reads_alone():
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_count_of_ground, TEXT, MET, after={"ground": ("toy-text", 1)})
    other = graph.Stage("other", "place", meeting(data, "other", ["never"]), TEXT, MET)  # a row the run leaves alone
    runner = graph.Runner((ground, build, other), world, Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet, whole=False, only=["build"])
    assert set(found) == {"ground", "build@hangar"}, found
    assert set(runner.lines(["hangar"], whole=False, only=["build"])["hangar"][1]) == {"build@hangar"}


def failing_with(code, times):
    """A make that raises an HTTP `code` error on its first `times` tries in its process, then writes."""
    tries = []

    def make(inputs, out, seed, params):
        tries.append(1)
        if len(tries) <= times:
            raise urllib.error.HTTPError("https://images.example", code, "server", {}, None)
        (out / "made.txt").write_text(f"made on try {len(tries)}")
    return make


def a_failing_runner(code, times, paid=False):
    world = a_world_of(["hangar"])[1]
    return graph.Runner((graph.Stage("maps", "place", failing_with(code, times), TEXT, MET, paid=paid, euros=0.1),),
                        world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})


def test_a_transient_error_runs_the_node_again_with_growing_waits():
    graph.RETRY_WAIT = 0
    runner = a_failing_runner(500, 2)
    found = runner.drive(["hangar"], say=quiet)
    assert found == {"maps@hangar": "made: pass, accepted automatically"}, found
    log = runner.desk("logs", "maps@hangar", ".log").read_text()
    assert "try 2 of 5 in 0 s" in log and "try 3 of 5" in log and "try 4 of 5" not in log, log


def test_a_paid_node_is_never_run_again():
    graph.RETRY_WAIT = 0
    runner = a_failing_runner(500, 1, paid=True)
    runner.cleared = lambda node, euros: contextlib.nullcontext()  # no clearance to buy in a test
    found = runner.drive(["hangar"], say=quiet)
    assert found["maps@hangar"].startswith("error: HTTPError: HTTP Error 500"), found
    assert "transient error" not in runner.desk("logs", "maps@hangar", ".log").read_text()


def test_a_lasting_or_not_transient_error_stops_its_line():
    graph.RETRY_WAIT = 0
    for code, times in ((503, graph.RETRIES + 1), (404, 1)):
        runner = a_failing_runner(code, times)
        found = runner.drive(["hangar"], say=quiet)
        assert found["maps@hangar"].startswith(f"error: HTTPError: HTTP Error {code}"), found
        log = runner.desk("logs", "maps@hangar", ".log").read_text()
        assert log.count("transient error") == times - 1, log
    assert graph.transient(TimeoutError()) and graph.transient(ConnectionResetError())
    assert graph.transient(urllib.error.URLError(ConnectionRefusedError())) and not graph.transient(ValueError())


def make_count_of_ground(inputs, out, seed, params):
    (out / "built.txt").write_text((inputs["ground"] / "ground.txt").read_text())


def make_leaving_a_thread(inputs, out, seed, params):
    threading.Thread(target=threading.Event().wait).start()  # never ends, and not a daemon
    (out / "made.txt").write_text("made")


def hung(signal_number, frame):
    raise RuntimeError("the drive did not end")  # not an OSError: a wait swallows those


def test_a_node_that_leaves_a_thread_running_does_not_hold_up_the_drive():
    """Fault (2026-10-12): two `score run`s did all their work and never exited."""
    world = a_world_of(["hangar"])[1]
    runner = graph.Runner((graph.Stage("maps", "place", make_leaving_a_thread, TEXT, MET),), world,
                          Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    signal.signal(signal.SIGALRM, hung)
    signal.alarm(60)
    try:
        assert runner.drive(["hangar"], say=quiet) == {"maps@hangar": "made: pass, accepted automatically"}
    finally:
        signal.alarm(0)


CHILD_THREADS = "import os; print(os.environ['OMP_NUM_THREADS'], os.environ['NUMBA_NUM_THREADS'])"


def live_openblas_threads():
    """The pool size each OpenBLAS loaded in this process runs its work on now (not what its variable says)."""
    import ctypes
    sizes = []
    for library in graph.loaded_openblas():
        handle = ctypes.CDLL(library)
        getter = next(getattr(handle, name.replace("_set_", "_get_")) for name in graph.OPENBLAS_SETTERS
                      if hasattr(handle, name))
        sizes.append(getter())
    return sizes


def make_thread_note(inputs, out, seed, params):
    own = f"{os.environ['OMP_NUM_THREADS']} {os.environ['NUMBA_NUM_THREADS']}"
    child = subprocess.run([sys.executable, "-c", CHILD_THREADS], capture_output=True, text=True, check=True)
    pools = " ".join(str(size) for size in live_openblas_threads())
    (out / "threads.txt").write_text(f"{own}\n{child.stdout.strip()}\n{pools}")


def thread_note(jobs, cores=24):
    """The thread note one node writes when `jobs` nodes share `cores`, numpy and scipy's OpenBLAS loaded in the
    drive before it forks (as score.stages loads them)."""
    import numpy  # noqa: F401
    import scipy.linalg  # noqa: F401
    world = a_world_of(["hangar"])[1]
    runner = graph.Runner((graph.Stage("threads", "place", make_thread_note, TEXT, MET),), world,
                          Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    real_count = os.cpu_count
    os.cpu_count = lambda: cores
    try:
        assert runner.drive(["hangar"], say=quiet, jobs=jobs) == {
            "threads@hangar": "made: pass, accepted automatically"}
    finally:
        os.cpu_count = real_count
    return (runner.store.checkout(runner.store.accepted("threads@hangar")) / "threads.txt").read_text().splitlines()


def test_six_jobs_on_twenty_four_cores_give_each_node_and_its_child_four_threads():
    """Fault (C11, 2026-10-17): six local nodes each sized their thread pools to every core and overloaded the PC.
    The OpenBLAS numpy and scipy loaded before the fork is resized in the node too, not only its variable."""
    lines = thread_note(6)
    assert lines[:2] == ["4 4", "4 4"], lines
    assert lines[2].split() and set(lines[2].split()) == {"4"}, lines
    assert graph.oversubscribed(6) is None and "--oversubscribe" in graph.oversubscribed(30)


def test_a_smaller_thread_count_the_owner_set_is_kept():
    """Review (C11): OMP_NUM_THREADS=1 set by the owner was raised to the node's share."""
    own = os.environ.get("OMP_NUM_THREADS")
    os.environ["OMP_NUM_THREADS"] = "1"
    try:
        lines = thread_note(6)
    finally:
        if own is None:
            del os.environ["OMP_NUM_THREADS"]
        else:
            os.environ["OMP_NUM_THREADS"] = own
    assert lines[:2] == ["1 4", "1 4"], lines


def test_a_cap_that_fails_shows_its_cause_in_the_nodes_fault_report():
    """Review (C11): a cap that raised in the node's process before its log opened ended the node with 'its process
    ended without saying what it did' and an empty log tail, on every line."""
    import numpy  # noqa: F401 - its OpenBLAS loaded before the fork, as score.stages loads it
    world = a_world_of(["hangar"])[1]
    runner = graph.Runner((graph.Stage("threads", "place", make_thread_note, TEXT, MET),), world,
                          Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    setters = graph.OPENBLAS_SETTERS
    graph.OPENBLAS_SETTERS = ("no_such_setter",)
    try:
        did = runner.drive(["hangar"], say=quiet, jobs=6)["threads@hangar"]
    finally:
        graph.OPENBLAS_SETTERS = setters
    assert "pool cannot be capped" in did and "without saying" not in did, did
    report = runner.desk("faults", "threads@hangar", ".txt").read_text()
    assert "RuntimeError" in report and "  | " in report and "pool cannot be capped" in report, report


def with_omp(value, act):
    """act() with OMP_NUM_THREADS set to `value`, the owner's own put back after."""
    own = os.environ.get("OMP_NUM_THREADS")
    os.environ["OMP_NUM_THREADS"] = value
    try:
        return act()
    finally:
        if own is None:
            del os.environ["OMP_NUM_THREADS"]
        else:
            os.environ["OMP_NUM_THREADS"] = own


def test_a_thread_variable_that_is_not_a_count_is_refused_plainly_and_an_empty_one_is_unset():
    """Review (C11): OMP_NUM_THREADS='' (export OMP_NUM_THREADS=), '4,2' and 'auto' each crashed every node."""
    from score import __main__ as command
    assert with_omp("", lambda: thread_note(6))[:2] == ["4 4", "4 4"]
    for value in ("4,2", "auto", "0"):
        try:
            with_omp(value, command.checked_thread_variables)
        except SystemExit as refusal:
            assert str(refusal) == (f"refused: OMP_NUM_THREADS={value!r} is not a thread count (a whole number "
                                    "above 0); unset it or set one"), refusal
        else:
            raise AssertionError(f"OMP_NUM_THREADS={value!r} was taken")


def test_score_run_refuses_more_jobs_than_cores_without_oversubscribe_and_any_jobs_under_one():
    """Review (C11): --jobs 0 ended in a ZeroDivisionError traceback, and the refusal had no test."""
    from score import __main__ as command
    real_count = os.cpu_count
    os.cpu_count = lambda: 24
    try:
        for jobs in ("8", "24"):
            command.checked_threads(command.parse(["run", "world1", "--jobs", jobs]))
        command.checked_threads(command.parse(["run", "world1", "--jobs", "25", "--oversubscribe"]))
        try:
            command.checked_threads(command.parse(["run", "world1", "--jobs", "25"]))
        except SystemExit as refusal:
            assert str(refusal).startswith("refused: 25 jobs") and "--oversubscribe" in str(refusal), refusal
        else:
            raise AssertionError("25 jobs on 24 cores ran without --oversubscribe")
    finally:
        os.cpu_count = real_count
    for jobs in ("0", "-2"):
        printed = io.StringIO()
        try:
            with contextlib.redirect_stderr(printed):
                command.parse(["run", "world1", "--jobs", jobs])
        except SystemExit as refusal:
            assert refusal.code == 2 and "at least 1" in printed.getvalue(), printed.getvalue()
        else:
            raise AssertionError(f"--jobs {jobs} was taken")


def test_status_lists_each_prefix_once_and_works_out_each_key_once():
    """Fault (2026-10-12): a run's closing status walked the whole store for every lookup and worked out each key once
    a path through the nodes reading it; `score status` on world 1 took over five minutes. Fault (2026-10-16): the
    fix walked the whole store once a pass, once per finished node, which held runs at their end."""
    runner = a_runner({"hangar": "a ship", "station": "a hub"})
    runner.drive(PLACES, say=quiet)
    walks, keys = [], []
    store_class, walk, work_out = type(runner.store.objects), type(runner.store.objects).keys, graph.Runner.worked_out_key
    store_class.keys = lambda self, prefix: walks.append(prefix) or walk(self, prefix)
    graph.Runner.worked_out_key = lambda self, stage, place: keys.append((stage.name, place)) or work_out(self, stage,
                                                                                                         place)
    try:
        assert all(state == "done" for state, _ in runner.lines(PLACES).values())
        assert "accepted" in runner.status(PLACES)["count@hangar"]
    finally:
        store_class.keys, graph.Runner.worked_out_key = walk, work_out
    assert walks and "" not in walks, walks  # never the whole store
    assert len(walks) == 2 * len(set(walks)), walks  # each prefix once a pass
    assert sorted(keys) == sorted(2 * [(stage, place) for stage in ("clean", "count") for place in PLACES]), keys
    assert runner.remembered is None and "keys" not in vars(runner.store.objects)


@contextlib.contextmanager
def logs_in_tmp():
    """A detached run's logs in a folder of the test's own, never the real $PROPS_HOME/logs; that folder."""
    from score.graph import runs
    kept, runs.LOGS = runs.LOGS, pathlib.Path(tempfile.mkdtemp())
    try:
        yield runs.LOGS
    finally:
        runs.LOGS = kept


def test_detach_returns_at_once_with_the_log_its_result_line_last():
    from score import __main__ as command
    printed = io.StringIO()
    started = time.time()
    with contextlib.redirect_stdout(printed), logs_in_tmp() as logs:
        command.detach(["-c", "import time; time.sleep(3); print('the run went on')", command.DETACH])
    assert time.time() - started < 2.5, time.time() - started
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    assert log.parent == logs, log
    assert printed.getvalue().splitlines()[-1].startswith("detached: started pid=") and log.exists(), printed.getvalue()
    deadline = time.time() + 60
    while "detached:" not in log.read_text() and time.time() < deadline:
        time.sleep(0.5)
    lines = log.read_text().splitlines()
    assert lines[0] == "the run went on" and lines[-1].startswith("detached: ok exit=0 "), lines


def test_a_detached_run_stopped_by_a_signal_still_ends_with_its_line():
    """Fault (2026-10-12): a run whose process group was sent SIGTERM ended its log with no line."""
    import signal
    from score import __main__ as command
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed), logs_in_tmp() as logs:
        command.detach(["-c", "import time; print('working', flush=True); time.sleep(60)", command.DETACH])
    pid = int(printed.getvalue().split("pid=")[1].split()[0])
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    assert log.parent == logs, log
    deadline = time.time() + 30
    while "working" not in log.read_text() and time.time() < deadline:
        time.sleep(0.1)
    os.killpg(pid, signal.SIGTERM)  # the session detach started: its process group
    while "detached:" not in log.read_text() and time.time() < deadline:
        time.sleep(0.1)
    lines = log.read_text().splitlines()
    assert lines[-1].startswith("detached: stopped by signal 15 exit=143 ") and f"log={log}" in lines[-1], lines


# A `score run` in miniature: it becomes a run and installs its stop handler as score/__main__ does, forks a node that
# waits, and starts a fake batch that stops on SIGTERM and one that ignores it; it writes its run id and every pid.
STOPPED_RUN = """
import json, os, pathlib, signal, subprocess, sys, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command
from score.adapters import compute
folder = pathlib.Path(sys.argv[2])
runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))


def drive():
    run_id = os.environ[command.RUN_ID]
    (folder / "reservations.json").write_text(json.dumps({
        compute.graph.now(): {"euros": 2.0, "run": run_id},
        "2099-01-01T00:00:00+00:00": {"euros": 1.0, "run": "other"}}))
    if sys.argv[3] == "fails":
        raise RuntimeError("the drive fell over")
    pids = []
    node = os.fork()
    if node == 0:
        time.sleep(120)
        os._exit(0)
    pids.append(node)
    batch = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    stubborn = subprocess.Popen([sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, "
                                 "signal.SIG_IGN); open(__import__('sys').argv[1], 'w').write('ready'); time.sleep(120)",
                                 str(folder / "stubborn-ready")])
    pids += [batch.pid, stubborn.pid]
    while not (folder / "stubborn-ready").exists():
        time.sleep(0.05)
    (folder / "pids.json").write_text(json.dumps({"run": run_id, "pids": pids}))
    time.sleep(120)


command.as_run(runner, drive)
"""


def alive(pid):
    """Whether a process is there and not a zombie."""
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0] != "Z"
    except OSError:
        return False


def test_a_stopped_run_ends_every_process_it_started_and_releases_its_reservations():
    """Fault (2026-10-17): runs stopped from outside left their nodes and batches running, renting on."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="stopped-run-"))
    environment = {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}
    run = subprocess.Popen([sys.executable, "-c", STOPPED_RUN, str(pathlib.Path(__file__).resolve().parents[2]),
                            str(folder), "waits"], env=environment, stdout=subprocess.PIPE, text=True, start_new_session=True)
    deadline = time.time() + 60
    while not (folder / "pids.json").exists() and time.time() < deadline:
        time.sleep(0.1)
    started = json.loads((folder / "pids.json").read_text())
    assert all(map(alive, started["pids"])), started
    stopped_at = time.time()
    run.send_signal(signal.SIGTERM)  # to the run's pid alone, not its group
    output, _ = run.communicate(timeout=60)
    while any(map(alive, started["pids"])) and time.time() < stopped_at + 35:
        time.sleep(0.2)
    assert not any(map(alive, started["pids"])), [pid for pid in started["pids"] if alive(pid)]
    assert run.returncode == 143 and "score run: stopped by signal 15" in output, (run.returncode, output)
    assert "SIGKILL to 1 processes" in output, output  # the one that ignored SIGTERM, after the grace
    held = json.loads((folder / "reservations.json").read_text())
    assert [reserved["run"] for reserved in held.values()] == ["other"], held


def test_a_run_whose_drive_fails_still_releases_its_reservations():
    """Review of C7 (2026-10-17): the release ran only after a drive that returned, so a drive that raised left the
    run's spend reservations held and its machine counts folder behind."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="failed-run-"))
    environment = {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}
    run = subprocess.run([sys.executable, "-c", STOPPED_RUN, str(pathlib.Path(__file__).resolve().parents[2]),
                          str(folder), "fails"], env=environment, capture_output=True, text=True, timeout=60,
                         start_new_session=True)
    assert run.returncode == 1 and "the drive fell over" in run.stderr, (run.returncode, run.stderr)
    held = json.loads((folder / "reservations.json").read_text())
    assert [reserved["run"] for reserved in held.values()] == ["other"], held


# A fake cloud batch holding three machines, each deleted through batch.delete_machine (as batch.run's end does)
# taking argv[3] seconds; it writes "ready" once its stop handler is in.
SLOW_BATCH = """
import pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import batch
from provider import cloud
folder, seconds = pathlib.Path(sys.argv[2]), float(sys.argv[3])


def delete(server_id, zone):
    time.sleep(seconds)
    with (folder / "deletes.txt").open("a") as deletes:
        deletes.write(server_id + chr(10))
    return True


cloud.delete = delete
batch.stop_on_signals()
machines = [{"id": f"machine-{number}", "zone": "zone-a", "deleted": None, "watchdog": 999999999,
             "folder": folder / f"machine-{number}", "created": time.time(), "kind": None, "healthy": False}
            for number in range(3)]
try:
    (folder / "ready").write_text("ready")
    time.sleep(120)
finally:
    for machine in machines:
        batch.delete_machine(machine)
"""
# A `score run` in miniature whose one node runs SLOW_BATCH (argv[5]) from tools/props/cloud, its output piped to the
# node as a stage's subprocess.run does; the run's grace is argv[3] seconds, each delete argv[4].
GROUP_RUN = """
import json, os, pathlib, subprocess, sys, threading, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command, graph
from score.adapters import compute
folder, cloud = pathlib.Path(sys.argv[2]), str(pathlib.Path(sys.argv[1]) / "tools/props/cloud")
command.STOP_GRACE_SECONDS = float(sys.argv[3])
runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))


def drive():
    leader = os.getpid()
    (folder / "reservations.json").write_text(json.dumps({compute.graph.now(): {"euros": 2.0,
                                                                                 "run": os.environ[command.RUN_ID]}}))
    if os.fork() == 0:  # a node, as Runner.start forks one
        threading.Thread(target=graph.watch_runner, args=(leader, 0.2), daemon=True).start()
        done = subprocess.run([sys.executable, "-c", sys.argv[5], cloud, str(folder), sys.argv[4]],
                              capture_output=True, text=True)
        (folder / "batch.log").write_text(done.stdout + done.stderr)
        os._exit(0)
    time.sleep(120)


command.as_run(runner, drive)
"""


def group_run(grace, delete_seconds):
    """A GROUP_RUN started in a session of its own, once its batch is ready; the process and its folder."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="group-run-"))
    environment = {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}
    run = subprocess.Popen([sys.executable, "-c", GROUP_RUN, str(pathlib.Path(__file__).resolve().parents[2]),
                            str(folder), str(grace), str(delete_seconds), SLOW_BATCH], env=environment,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    deadline = time.time() + 60
    while not (folder / "ready").exists() and time.time() < deadline:
        time.sleep(0.05)
    assert (folder / "ready").exists(), "the fake batch never started"
    return run, folder


def deleted_by(folder, run, within=60):
    """The machine ids the run's batch deleted, once the run and its batch have ended (or `within` seconds); and the
    run's output."""
    output, _ = run.communicate(timeout=within)
    deadline = time.time() + within
    while not (folder / "batch.log").exists() and time.time() < deadline:
        time.sleep(0.1)
    deletes = folder / "deletes.txt"
    return (deletes.read_text().split() if deletes.exists() else []), output


def test_a_run_signalled_as_a_whole_group_lets_its_batch_delete_every_machine():
    """Review of C7 (2026-10-17): Ctrl-C, a closed terminal or `kill -- -<pgid>` gives every batch the signal, and
    the run's own SIGTERM to the group moments later broke the batch's delete loop: 0 of 3 machines deleted."""
    for number in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
        run, folder = group_run(30, 0.3)
        os.killpg(run.pid, number)
        deleted, output = deleted_by(folder, run)
        assert deleted == ["machine-0", "machine-1", "machine-2"], (number, deleted, output)


def test_a_stopped_run_never_kills_a_cloud_batch_still_deleting_after_its_grace():
    """Review of C7 (2026-10-17): the SIGKILL after the grace cut a batch's deletes short, and its machines billed on
    until their self-delete."""
    run, folder = group_run(1, 0.8)
    run.send_signal(signal.SIGTERM)  # the run alone: it sends the group its stop itself
    deleted, output = deleted_by(folder, run)
    assert deleted == ["machine-0", "machine-1", "machine-2"], (deleted, output)
    assert "SIGKILL" not in output, output


def test_a_stopped_run_holds_its_reservations_until_its_cloud_tools_have_ended():
    """Review of C7 (2026-10-17): a stopped run released its spend reservations and its machine counts as it exited,
    while the cloud tools it spared were still deleting machines that billed."""
    run, folder = group_run(1, 1.5)
    run.send_signal(signal.SIGTERM)  # the run alone: it passes its stop on itself
    run.wait(timeout=60)
    deletes = folder / "deletes.txt"
    still = deletes.read_text().split() if deletes.exists() else []
    assert len(still) < 3, still  # the run ended before its batch had deleted everything
    held = json.loads((folder / "reservations.json").read_text())
    assert len(held) == 1, held  # the run's reservation stays while its machines are being deleted
    deadline = time.time() + 30
    while time.time() < deadline and json.loads((folder / "reservations.json").read_text()):
        time.sleep(0.1)
    assert deletes.read_text().split() == ["machine-0", "machine-1", "machine-2"]
    assert json.loads((folder / "reservations.json").read_text()) == {}  # released once the batch had ended
    assert not list(folder.rglob("runs/*")), list(folder.rglob("runs/*"))


# GROUP_RUN with a node whose main thread runs no handler for argv[6] seconds after the batch starts (long C code: its
# signals wait, as the run's own window passes).
STUCK_GROUP_RUN = """
import os, pathlib, signal, subprocess, sys, threading, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command, graph
folder, cloud = pathlib.Path(sys.argv[2]), str(pathlib.Path(sys.argv[1]) / "tools/props/cloud")
command.STOP_GRACE_SECONDS = float(sys.argv[3])
runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))


def drive():
    leader = os.getpid()
    if os.fork() == 0:
        threading.Thread(target=graph.watch_runner, args=(leader, 0.2), daemon=True).start()
        batch = subprocess.Popen([sys.executable, "-c", sys.argv[5], cloud, str(folder), sys.argv[4]],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while not (folder / "ready").exists():
            time.sleep(0.05)
        every = set(signal.Signals)
        signal.pthread_sigmask(signal.SIG_BLOCK, every)
        time.sleep(float(sys.argv[6]))
        signal.pthread_sigmask(signal.SIG_UNBLOCK, every)
        output, _ = batch.communicate()
        (folder / "batch.log").write_text(output)
        os._exit(0)
    time.sleep(120)


command.as_run(runner, drive)
"""


def test_a_group_stop_reaches_a_batch_once_while_its_node_is_busy_in_long_code():
    """Review of C7 (2026-10-17): a node whose main thread ran no handler within the run's 1 s window showed no stop, so
    the run sent its own SIGTERM to the whole group as well, a batch's second signal, and the batch left its deletes."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="stuck-group-run-"))
    environment = {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}
    run = subprocess.Popen([sys.executable, "-c", STUCK_GROUP_RUN, str(pathlib.Path(__file__).resolve().parents[2]),
                            str(folder), "30", "0.8", SLOW_BATCH, "3"], env=environment,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    deadline = time.time() + 60
    while not (folder / "ready").exists() and time.time() < deadline:
        time.sleep(0.05)
    time.sleep(0.5)  # the node's main thread is in its stretch now
    os.killpg(run.pid, signal.SIGTERM)
    deleted, output = deleted_by(folder, run)
    assert deleted == ["machine-0", "machine-1", "machine-2"], (deleted, output)


# A shell pipeline's later stage (`... | score run`): its process group is the pipeline's, led by the first stage, and
# holds the terminal. Run in a session of its own, a pseudo-terminal its controlling terminal.
PIPELINE_RUN = """
import fcntl, os, signal, sys, termios, time
sys.path.insert(0, sys.argv[1])
from score import __main__ as command
_, terminal = os.openpty()
fcntl.ioctl(terminal, termios.TIOCSCTTY, 0)
first = os.fork()
if first == 0:
    time.sleep(30)
    os._exit(0)
os.setpgid(first, first)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)
os.tcsetpgrp(terminal, first)
later = os.fork()
if later == 0:
    while os.getpgrp() != first:
        time.sleep(0.01)
    command.become_run()
    os._exit(0 if os.tcgetpgrp(terminal) == os.getpid() else 3)
os.setpgid(later, first)
_, status = os.waitpid(later, 0)
os.kill(first, signal.SIGKILL)
sys.exit(os.waitstatus_to_exitcode(status))
"""


def test_a_run_late_in_a_shell_pipeline_keeps_the_terminal_so_ctrl_c_reaches_it():
    """Review of C7 (2026-10-17): leading a group of its own took a pipeline's later stage out of the terminal's
    foreground group, so Ctrl-C no longer reached the run."""
    done = subprocess.run([sys.executable, "-c", PIPELINE_RUN, str(pathlib.Path(__file__).resolve().parents[2])],
                          capture_output=True, text=True, timeout=60, start_new_session=True)
    assert done.returncode == 0, (done.returncode, done.stderr)


# The same pipeline's later stage as a whole run (score/__main__'s as_run) whose drive returns: the terminal must go
# back to the group that held it, or a script's later read from it stops on SIGTTIN and Ctrl-C reaches nothing.
PIPELINE_RUN_ENDS = """
import fcntl, os, pathlib, signal, sys, tempfile, termios, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command
_, terminal = os.openpty()
fcntl.ioctl(terminal, termios.TIOCSCTTY, 0)
first = os.fork()
if first == 0:
    time.sleep(30)
    os._exit(0)
os.setpgid(first, first)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)
os.tcsetpgrp(terminal, first)
later = os.fork()
if later == 0:
    while os.getpgrp() != first:
        time.sleep(0.01)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="pipeline-run-"))
    runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))
    held = []
    command.as_run(runner, lambda: held.append(os.tcgetpgrp(terminal) == os.getpid()))
    os._exit(0 if held == [True] and os.tcgetpgrp(terminal) == first else 3)
os.setpgid(later, first)
_, status = os.waitpid(later, 0)
os.kill(first, signal.SIGKILL)
sys.exit(os.waitstatus_to_exitcode(status))
"""


def test_a_run_late_in_a_shell_pipeline_gives_the_terminal_back_when_it_ends():
    """Review of C7 (2026-10-17): a run that took the terminal for its own group never gave it back, leaving a dead
    group in the foreground."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="pipeline-ends-"))
    done = subprocess.run([sys.executable, "-c", PIPELINE_RUN_ENDS, str(pathlib.Path(__file__).resolve().parents[2])],
                          capture_output=True, text=True, timeout=60, start_new_session=True,
                          env={**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")})
    assert done.returncode == 0, (done.returncode, done.stderr)


def test_conclude_lists_only_the_runs_own_prefixes_in_a_large_store():
    """A store of 50,000 unrelated keys: a finished node's verdict lists only its run's nodes' prefixes, within 1 s."""
    runner = a_runner({"hangar": "a ship", "station": "a hub"})
    runner.drive(PLACES, say=quiet)
    root = runner.store.objects.root
    for area in ("records", "judgements", "accepts"):
        for folder in range(250):
            unrelated = root / area / f"elsewhere{folder}@far"
            unrelated.mkdir(parents=True)
            for index in range(67):
                (unrelated / f"{index}.json").write_text("{}")
    store_class, walk, walks = type(runner.store.objects), type(runner.store.objects).keys, []
    store_class.keys = lambda self, prefix: walks.append(prefix) or walk(self, prefix)
    try:
        started = time.monotonic()
        assert runner.conclude(runner.stages["count"], "hangar", "made") == ("made", True)
        took = time.monotonic() - started
    finally:
        store_class.keys = walk
    assert took < 1.0, took
    nodes = {f"{stage}@{place}" for stage in ("clean", "count") for place in PLACES}
    assert walks and all(prefix.split("/")[1] in nodes for prefix in walks), walks


def slow_runner(seconds):
    """A one-node run whose make takes `seconds`."""
    def make_slowly(inputs, out, seed, params):
        time.sleep(seconds)
        (out / "made.txt").write_text("made")
    world = a_world_of(["hangar"])[1]
    return graph.Runner((graph.Stage("slow", "place", make_slowly, TEXT, MET),), world,
                        Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})


@contextlib.contextmanager
def heartbeat_every(seconds):
    before, graph.HEARTBEAT = graph.HEARTBEAT, seconds
    try:
        yield
    finally:
        graph.HEARTBEAT = before


def test_a_long_node_has_heartbeats_before_it_ends():
    """Fault (2026-10-16): runs failed or sat idle quietly, and outside watchers stopped live ones. The 2-minute beat
    and 3-minute node scaled down to 0.3 s and 1.5 s."""
    said = []
    with heartbeat_every(0.3):
        found = slow_runner(1.5).drive(["hangar"], say=said.append, gauges=lambda: "EUR 0.00 so far")
    assert found == {"slow@hangar": "made: pass, accepted automatically"}, found
    ended = said.index("slow@hangar: made: pass, accepted automatically")
    beats = [line for line in said[:ended] if line.startswith("heartbeat ")]
    assert len(beats) >= 3, said
    assert beats[0].endswith(": rows done 0, running 1, queued 0; EUR 0.00 so far"), beats


def test_a_gauge_that_fails_is_said_in_its_beat_and_the_drive_goes_on():
    """Review (C8): a gauge that raised (a ledger line half written by another worktree's batch) ended the drive with
    its nodes still running."""
    said = []
    with heartbeat_every(0.2):
        found = slow_runner(1).drive(["hangar"], say=said.append, gauges=lambda: 1 / 0)
    assert found == {"slow@hangar": "made: pass, accepted automatically"}, found
    beats = [line for line in said if line.startswith("heartbeat ")]
    assert beats and beats[0].endswith("; gauges unreadable: ZeroDivisionError: division by zero"), said


def test_a_stages_own_drive_says_no_heartbeat_or_exit_line():
    """Review (C8): stage code drives too (compare.py); its output carries no beats and no `exit:` a watcher reads as
    the run's end."""
    said = []
    with heartbeat_every(0.1):
        slow_runner(0.6).drive(["hangar"], say=said.append)
    assert not [line for line in said if line.startswith(("heartbeat ", "exit:"))], said


def run_options(stage=None):
    import argparse
    return argparse.Namespace(jobs=graph.JOBS, stage=stage, command="run")


def run_printing(runner, places, whole=False):
    """score run's drive, closing status and exit line on `runner`; (what it printed as lines, the lines)."""
    from score import __main__ as command
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        lines = command.run_with_exit_line(runner, places, whole, run_options(), ["run", "world1"])
    return printed.getvalue().splitlines(), lines


def test_a_run_ends_with_its_exit_line_after_its_line_states():
    """Review (C8): the exit line came before the closing status, the pass that can hang."""
    printed, lines = run_printing(slow_runner(0.2), ["hangar"])
    assert printed[-2:] == ["hangar: done", "exit: ok, 1 of 1 lines done, 1 rows ran"], printed
    assert lines["hangar"][0] == "done"


def test_a_run_whose_line_stopped_says_stopped_in_its_exit_line():
    """Review (C8): `exit: ok` was said for a run main then ended with 1, its not-run rows counted as ended."""
    printed, lines = run_printing(a_runner({"hangar": "explode", "station": "a hub"}), list(PLACES))
    assert printed[-1] == "exit: stopped, 1 of 2 lines done, 1 stopped, 3 rows ran, 1 not run", printed
    assert lines["hangar"][0].startswith("stopped at clean@hangar")


def test_a_run_that_raises_ends_with_an_exit_line():
    runner = slow_runner(0.2)

    def broken(*arguments):
        raise RuntimeError("the store is unreadable")
    runner.lines = broken
    from score import __main__ as command
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        try:
            command.run_with_exit_line(runner, ["hangar"], False, run_options(), ["run", "world1"])
            raise AssertionError("the run did not raise")
        except RuntimeError:
            pass
    assert printed.getvalue().splitlines()[-1] == "exit: error: RuntimeError: the store is unreadable", printed


def test_a_run_stopped_by_sigterm_ends_with_an_exit_line():
    from score import __main__ as command
    from score.graph import stopped
    said = pathlib.Path(tempfile.mkdtemp()) / "said.txt"

    def driving():
        sys.stdout = said.open("a", buffering=1)
        stopped.stop_on_signals(lambda number: print(f"score run: stopped by signal {number}", flush=True))
        command.run_with_exit_line(slow_runner(5), ["hangar"], False, run_options(), ["run", "world1"])
    process = graph.FORK.Process(target=driving)
    process.start()
    time.sleep(1)
    os.kill(process.pid, signal.SIGTERM)
    process.join(30)
    lines = said.read_text().splitlines()
    assert process.exitcode == 143, process.exitcode
    assert lines[-2:] == ["score run: stopped by signal 15", "exit: stopped by signal 15, exit 143"], lines


def test_the_run_gauges_count_only_this_runs_rows():
    """Review (C8): the gauges summed every batch any worktree recorded and counted every open paid run in the store."""
    from score import __main__ as command
    books = compute.ledger()
    runner = slow_runner(0)
    here = books.origin()["worktree"]
    rows = [{"worktree": here, "ticket": "slow@hangar k1", "started": "2026-10-17T10:00:00Z", "euros": 2.5},
            {"worktree": here, "ticket": "other@far k2", "started": "2026-10-17T10:00:00Z", "euros": 7.0},
            {"worktree": "elsewhere", "ticket": "slow@hangar k3", "started": "2026-10-17T10:00:00Z", "euros": 9.0},
            {"worktree": here, "ticket": "slow@hangar k4", "started": "2026-10-17T08:00:00Z", "euros": 4.0}]
    before, books.entries = books.entries, lambda: rows
    held = {graph.now(): {"node": "slow@hangar"}}
    held[graph.now()] = {"node": "other@far"}
    (runner.store.cache.parent / "reservations.json").write_text(json.dumps(held))
    try:
        said = command.run_gauges(runner, ["hangar"], False, None, "2026-10-17T09:00:00Z")()
    finally:
        books.entries = before
    assert said == "this run's rows: paid runs open 1, EUR 2.50 in the ledger since the run started", said


def test_a_detached_run_refused_on_the_store_ends_with_the_refusal_as_its_line():
    """Review of C10: a run that registered between the check and the detached run's own registration refuses it;
    the start line says it may still be refused, and the refusal is its result line, not a plain failure."""
    from score import __main__ as command
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed), logs_in_tmp():
        command.detach(["-c", "import sys; print('refused: run pid 7 holds the store', file=sys.stderr); "
                        f"sys.exit({stopped.REFUSED})", command.DETACH])
    assert "may still be refused" in printed.getvalue(), printed.getvalue()
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    deadline = time.time() + 60
    while "detached:" not in log.read_text() and time.time() < deadline:
        time.sleep(0.2)
    lines = log.read_text().splitlines()
    assert lines[-1].startswith(f"detached: refused: run pid 7 holds the store exit={stopped.REFUSED} "), lines


# --- runs side by side on one store ----------------------------------------------------------------------------------

def made_slowly(data):
    """A make that counts its makes in a file and takes a second: two runs of it at once would overlap."""
    def make(inputs, out, seed, params):
        with (data / "made.txt").open("a") as made:
            made.write("made\n")
        time.sleep(1)
        (out / "made.txt").write_text("made")
    return make


def two_runners_on_one_store(stages_of):
    """Two runners (two `score run`s from two checkouts) over one store, their stages from stages_of(data)."""
    data, world = a_world_of(["hangar"])
    store = tempfile.mkdtemp()
    return data, [graph.Runner(stages_of(data), world, Store.in_folder(store), model_record=lambda kind: {})
                  for _ in range(2)]


def drive_in_a_process(runner, places):
    """Drive the runner in a forked process; (process, the pipe its result comes back on)."""
    receiving, sending = graph.FORK.Pipe(duplex=False)
    process = graph.FORK.Process(target=lambda: sending.send(runner.drive(places, say=quiet)))
    process.start()
    return process, receiving


def test_two_runs_of_one_node_at_once_make_it_once_and_both_stand():
    """Fault (2026-10-12): two runs made people-segvigen at once; the second paid again, then failed on the first's
    record (FileExistsError)."""
    data, runners = two_runners_on_one_store(lambda data: (graph.Stage("slow", "place", made_slowly(data), TEXT, MET),))
    started = [drive_in_a_process(runner, ["hangar"]) for runner in runners]
    found = [receiving.recv() for _, receiving in started]
    for process, _ in started:
        process.join()
    assert (data / "made.txt").read_text() == "made\n", found
    assert sorted(result["slow@hangar"] for result in found) == ["fresh", "made: pass, accepted automatically"], found


def test_a_record_another_run_stored_first_is_taken_as_made():
    """A run that does not take the lock (an older checkout's) stored the key first: this run's record is refused by
    the store and the stored one stands, never an error."""
    data, runners = two_runners_on_one_store(lambda data: (graph.Stage("slow", "place", made_slowly(data), TEXT, MET),))
    stage = runners[0].stages["slow"]
    keyed = runners[0].key(stage, "hangar")
    first = runners[0].make(stage, "hangar", keyed)
    assert runners[1].make(stage, "hangar", keyed) == first
    judged = runners[0].judge(stage, "hangar", first)
    assert runners[1].judge(stage, "hangar", first) == judged


def test_a_lock_held_past_its_wait_blocks_and_makes_nothing():
    data, runners = two_runners_on_one_store(lambda data: (graph.Stage("slow", "place", made_slowly(data), TEXT, MET),))
    runner, saved = runners[0], (graph.LOCK_WAIT, graph.LOCK_POLL)
    graph.LOCK_WAIT, graph.LOCK_POLL = 0.2, 0.05
    try:
        key = runner.key(runner.stages["slow"], "hangar")["key"]
        with runner.held("slow@hangar", key):  # another open of the lock file: another run holding it
            did = runner.run_node(runner.stages["slow"], "hangar")
    finally:
        graph.LOCK_WAIT, graph.LOCK_POLL = saved
    assert did.startswith("blocked: slow@hangar: another run has held its lock") and "pid" in did, did
    assert not (data / "made.txt").exists()
    assert runner.run_node(runner.stages["slow"], "hangar") == "made: pass, accepted automatically"


def make_note(inputs, out, seed, params):
    (out / "note.txt").write_text(inputs["note"].read_text())


def test_a_run_never_accepts_over_an_output_a_newer_commit_made_under_another_key():
    """Fault (2026-10-12): a runner in an older worktree accepted terrain's old output over the newer accepted one."""
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "note.txt").write_text("new")
    note = graph.Stage("note", "place", make_note, TEXT, MET, files={"note": "{data}/{place}/note.txt"})
    runner = graph.Runner((note,), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    assert runner.run_node(note, "hangar") == "made: pass, accepted automatically"
    newer = runner.store.accepted("note@hangar")
    (data / "hangar" / "note.txt").write_text("old")  # the older checkout's input: another key
    saved = graph._code.holds
    graph._code.holds = lambda commit: False  # the accepted output's commit is one this checkout lacks
    try:
        did = runner.run_node(note, "hangar")
    finally:
        graph._code.holds = saved
    assert did.startswith("made: pass, not accepted: key differs from the accepted one") and "pull main" in did, did
    assert runner.store.accepted("note@hangar") == newer
    (data / "hangar" / "note.txt").write_text("newest")  # a run whose checkout holds the accepted one's commit
    assert runner.run_node(note, "hangar") == "made: pass, accepted automatically"
    assert runner.store.accepted("note@hangar") != newer


def make_failing(inputs, out, seed, params):
    raise RuntimeError("names failed")


def test_once_a_line_stops_nothing_later_on_it_starts():
    """Fault (2026-10-12): the people line stopped at people-names, then still started people-segvigen, which reads
    people-maps, not people-names. A node already running when the line stops may finish."""
    data, world = a_world_of(["hangar"])
    slow = graph.Stage("slow", "place", made_slowly(data), TEXT, MET)
    names = graph.Stage("names", "place", make_failing, TEXT, MET)
    after_slow = graph.Stage("after-slow", "place", make_count_of_slow, TEXT, MET, after={"slow": ("toy-text", 1)})
    runner = graph.Runner((slow, names, after_slow), world, Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet)
    assert found["names@hangar"].startswith("error: RuntimeError: names failed"), found
    assert found["slow@hangar"] == "made: pass, accepted automatically", found
    assert found["after-slow@hangar"] == "not run: its line stopped at names@hangar", found


def make_count_of_slow(inputs, out, seed, params):
    (out / "count.txt").write_text((inputs["slow"] / "made.txt").read_text())


def make_writing_into_its_input(inputs, out, seed, params):
    (inputs["slow"] / "saved-over.txt").write_text("a save into the input")
    (out / "count.txt").write_text("counted")


def test_a_make_that_writes_into_its_input_fails_and_stores_nothing():
    """Fault (2026-10-12): light@camp's make saved over its read-only input."""
    data, world = a_world_of(["hangar"])
    slow = graph.Stage("slow", "place", made_slowly(data), TEXT, MET)
    writer = graph.Stage("writer", "place", make_writing_into_its_input, TEXT, MET, after={"slow": ("toy-text", 1)})
    runner = graph.Runner((slow, writer), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet)
    assert found["writer@hangar"].startswith("error: RuntimeError: writer@hangar: its make wrote into its read-only "
                                             "input slow"), found
    assert runner.store.records("writer@hangar") == []


def judge_gapped(output, inputs, evidence):
    return checks.Verdict(graph.GAPPED, checks.FAIL, "hangar: a named gap", findings=("hangar: no made model",))


def judge_brief_fault(output, inputs, evidence):
    faulty = "fault" in inputs["brief"].read_text()
    return checks.Verdict("other", checks.FAIL if faulty else checks.PASS, "a fault no gap names" if faulty else "ok")


def gapped_runner(brief):
    """A completion gate that fails its named gap, and one ungapped fault when the brief says so; a film that reads it
    gapped and a count that does not."""
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "brief.txt").write_text(brief)
    complete = graph.Stage("complete", "place", make_clean, TEXT,
                           (checks.Check(graph.GAPPED, judge_gapped), checks.Check("other", judge_brief_fault)),
                           files={"brief": "{data}/{place}/brief.txt"})
    film = graph.Stage("film", "place", make_film, TEXT, MET, after={"complete": ("toy-text", 1)},
                       gapped=("complete",))
    count = graph.Stage("count", "place", make_film, TEXT, MET, after={"complete": ("toy-text", 1)})
    return graph.Runner((complete, film, count), world, Store.in_folder(tempfile.mkdtemp()),
                        model_record=lambda kind: {})


def make_film(inputs, out, seed, params):
    (out / "film.txt").write_text((inputs["complete"] / "clean.txt").read_text())


def test_a_gapped_reader_runs_past_a_gate_that_fails_only_on_its_named_gaps():
    """The overseer, 2026-10-15: demo-film runs on a place whose complete fails only on its named gaps; the gate
    still fails by name, and a reader that does not read it gapped stops."""
    runner = gapped_runner("a ship")
    found = runner.drive(["hangar"], say=quiet)
    assert found["complete@hangar"].startswith("made: fail, accepted automatically; fault report"), found
    assert found["film@hangar"] == "made: pass, accepted automatically", found
    assert found["count@hangar"] == "not run: its line stopped at complete@hangar", found
    # Taken by the runner as complete apart from named gaps (overseer, 2026-10-17), its status recorded and shown.
    output = runner.store.accepted("complete@hangar")
    assert output and runner.store.accepts("complete@hangar")[-1]["status"] == "complete apart from named gaps (1)"
    assert runner.status(["hangar"])["complete@hangar"] == "complete apart from named gaps (1), accepted"
    assert "stale" not in runner.status(["hangar"])["film@hangar"]


def test_a_gapped_reader_stops_on_a_fault_no_gap_names():
    runner = gapped_runner("a ship with a fault")
    found = runner.drive(["hangar"], say=quiet)
    assert found["film@hangar"] == "not run: its line stopped at complete@hangar", found
    assert runner.run_node(runner.stages["film"], "hangar").startswith("blocked: complete@hangar answered fail")
    assert runner.store.accepted("complete@hangar") is None  # a fail no gap names is never taken


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
