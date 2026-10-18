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
import sys
import tempfile
import threading
import time
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
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
    return graph.Runner((clean, COUNT), graph.World("toy", 7, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
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
    return data, graph.World("toy", 7, {"data": data})


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


def a_failing_runner(code, times):
    world = a_world_of(["hangar"])[1]
    return graph.Runner((graph.Stage("maps", "place", failing_with(code, times), TEXT, MET),), world,
                        Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})


def test_a_transient_error_runs_the_node_again_with_growing_waits():
    graph.RETRY_WAIT = 0
    runner = a_failing_runner(500, 2)
    found = runner.drive(["hangar"], say=quiet)
    assert found == {"maps@hangar": "made: pass, accepted automatically"}, found
    log = runner.desk("logs", "maps@hangar", ".log").read_text()
    assert "try 2 of 5 in 0 s" in log and "try 3 of 5" in log and "try 4 of 5" not in log, log


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


def test_status_walks_the_store_once_and_works_out_each_key_once():
    """Fault (2026-10-12): a run's closing status walked the whole store for every lookup and worked out each key once
    a path through the nodes reading it; `score status` on world 1 took over five minutes."""
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
    assert walks == ["", ""], walks  # one walk a pass
    assert sorted(keys) == sorted(2 * [(stage, place) for stage in ("clean", "count") for place in PLACES]), keys
    assert runner.remembered is None and "keys" not in vars(runner.store.objects)


def test_detach_returns_at_once_with_the_log_its_result_line_last():
    from score import __main__ as command
    printed = io.StringIO()
    started = time.time()
    with contextlib.redirect_stdout(printed):
        command.detach(["-c", "import time; time.sleep(3); print('the run went on')", command.DETACH])
    assert time.time() - started < 2.5, time.time() - started
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    assert printed.getvalue().startswith("detached: started pid=") and log.exists(), printed.getvalue()
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
    with contextlib.redirect_stdout(printed):
        command.detach(["-c", "import time; print('working', flush=True); time.sleep(60)", command.DETACH])
    pid = int(printed.getvalue().split("pid=")[1].split()[0])
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    deadline = time.time() + 30
    while "working" not in log.read_text() and time.time() < deadline:
        time.sleep(0.1)
    os.killpg(pid, signal.SIGTERM)  # the session detach started: its process group
    while "detached:" not in log.read_text() and time.time() < deadline:
        time.sleep(0.1)
    lines = log.read_text().splitlines()
    assert lines[-1].startswith("detached: stopped by signal 15 exit=143 ") and f"log={log}" in lines[-1], lines


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
