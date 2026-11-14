"""The runner (score/graph) makes each node's key once, only from inputs that passed and stand accepted, and a node that
does not end accepted stops only the nodes that read it; around it, a run claims its store and its frozen code,
says what it would buy, ends with one line and stops everything it started. Toy stage tables in stores, homes and
git repositories of their own; every answer is worked out by hand from the toy data (the words in a brief, the nodes
a table reads), never by the code under test.

Each test's docstring names a break in the code (`Break: <file>: '<old>' -> '<new>'`, one exact replacement) that
turns it red; each was applied once and seen red, then put back.

Tests of `score/__main__.py`'s run machinery (detach, the exit line, gauges, the pool's timing, stop handling) sit
here because they drive the runner and graph/stopped.py, graph/runs.py and graph/frozen.py through it.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/graph/test_a_key_is_made_once_from_accepted_inputs.py
"""
import argparse
import concurrent.futures
import contextlib
import dataclasses
import datetime
import functools
import importlib
import io
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import types
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
# Each OpenBLAS this process loads (score.stages loads numpy's and scipy's) sized at one thread when it loads, before
# the imports below: a pool sized at load to every core is what a forked node's resize (graph.cap_threads) starts again
# in the child, every thread spinning idle before it sleeps, about 1.4 s of CPU a node on 24 cores and 235 s of the
# file's 246 (2026-11-08: 52-61 s on the gate's pod against its 60). The thread tests resize past it (thread_note).
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from score import checks, conductor, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402

from score.graph import _code, chain, frozen, rebuy, runs, stopped  # noqa: E402
from score.graph._toys import (  # noqa: E402
    CLEAN, COUNT, DESIGNED, KEPT, PASSES, PEEK, POD_TABLE, READS, RECORDED, TAKES, TEXT, WORDS, judge_shout,
    make_clean, make_count)
from score.store import Store, file_hash, partial_of, tree_hash  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
PLACES = ("hangar", "station")
BOOKS_FOLDER = tempfile.mkdtemp()


def quiet(line):
    pass


@pytest.fixture(autouse=True)
def no_cloud_bill_and_no_memory_taken(monkeypatch):
    """No cloud: the provider's bill is never read here; this month's books known, so paid paths open; toy nodes
    take no memory (the memory tests fake their own readings). Patched per test so the next test file gets the
    real ones."""
    monkeypatch.setattr(compute, "cloud_bill", lambda: 0.0)
    monkeypatch.setattr(compute.ledger(), "BOOKS", compute.ledger().BOOKS)  # recorded: open_books_for_tests moves it
    compute.ledger().open_books_for_tests(BOOKS_FOLDER)
    monkeypatch.setattr(graph, "AVAILABLE", lambda: 2**50)
    monkeypatch.setattr(graph, "TOTAL", lambda: 2**50)


@pytest.fixture(autouse=True)
def store_writes_land_unsynced(monkeypatch):
    """The store's writes land whole and moved into place as in a run (score/store/durable.py), opened as there, but
    not fsynced: nothing here reboots to need it, and on the cluster gate's disk this file took 146 s against 120 s
    with /tmp in memory. A node forked from this process gets the same."""
    from score.store import durable
    monkeypatch.setattr(durable, "synced", lambda path: os.close(os.open(path, os.O_RDONLY)))


@pytest.fixture(scope="module", autouse=True)
def the_import_path_a_runs_table_leaves():
    """The import path as this file's imports leave it before any code version: the stages' folders (a run's table
    import), the cluster door's and the cloud tools' (tools/cloud/batch). Tests here import them and work the path
    out again (search_folders), and each new path parsed every file behind every stage again (live_imports keys on
    it): five times over the file, a third of its time on 2 CPUs."""
    from score import __main__ as command
    from score.graph import pod
    from score.stages import physics  # noqa: F401
    from score.stages.surfaces import route_list, scene_palette  # noqa: F401
    pod.cluster_door()
    command.cloud_tool("batch")
    _code.search_folders.cache_clear()


CHECKOUT = {}  # this checkout's commit and whether it has changes, as _code.git_commit read them once


@pytest.fixture(autouse=True)
def the_checkouts_commit_read_once(monkeypatch):
    """A finish record's commit (_code.git_commit) read once for this checkout, which no test here commits to or
    edits: each make read it again, `git rev-parse` and `git status` from the node's process, two thirds of a toy
    node's time. A repository of a test's own (a_repo_of_its_own) is read each time, as in a run."""
    read = _code.git_commit
    if not CHECKOUT:
        CHECKOUT.update(read())
    monkeypatch.setattr(_code, "git_commit", lambda: dict(CHECKOUT) if _code.REPO == REPO else read())


@pytest.fixture(autouse=True)
def one_openblas_thread_a_node(monkeypatch):
    """Each toy node's OpenBLAS pool kept at one thread (an owner's smaller count stands, graph.cap_thread_variables):
    sized to the cores over --jobs, a node forked from this process started that many OpenBLAS threads that spun
    idle, 26 s of CPU for a 4 s test on 24 cores, and on a loaded box with few CPUs the file ran past its 120 s. The
    thread tests unset it (thread_note)."""
    monkeypatch.setenv("OPENBLAS_NUM_THREADS", "1")


@pytest.fixture(autouse=True)
def nodes_print_to_their_file_descriptors(monkeypatch):
    """A node's process prints and writes tracebacks on file descriptors 1 and 2, as in a run, where its log takes
    them over (graph.logged); under pytest its streams would be pytest's own and the log would stay empty."""
    node_process = graph.Runner.node_process

    def on_descriptors(self, *arguments):
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
        node_process(self, *arguments)
    monkeypatch.setattr(graph.Runner, "node_process", on_descriptors)


# The environment this file started in: the runs of a waiting part (run_ahead) take it, never a test's patched one.
ENVIRON = {**os.environ, "OPENBLAS_NUM_THREADS": "1"}
WAITING_PARTS = {}  # a test's name: its waiting part (run_ahead)
AHEAD = {}  # a test's name: the future of its waiting part, started as the file started


def run_ahead(test):
    """Mark a function as `test`'s waiting part: runs of processes of their own (a `score run` in miniature, a script)
    that the test signals and waits on, reading and patching nothing of this process. It starts with the file, one
    part after another beside the other tests, and gives the test what it saw; the test checks it (ahead)."""
    def marked(part):
        WAITING_PARTS[test] = part
        return part
    return marked


@pytest.fixture(scope="module", autouse=True)
def waiting_parts_run_ahead(request):
    """The waiting parts (run_ahead) of the tests this session runs, started at once one after another in a thread
    of their own: most of their time is a grace, a delete or a process's start waited out, which the tests before
    them use (in the cluster gate they were 21 s of the file's 89)."""
    chosen = {item.name for item in request.session.items}
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        AHEAD.update({test: pool.submit(part) for test, part in WAITING_PARTS.items() if test in chosen})
        yield
        for future in AHEAD.values():
            future.cancel()
        AHEAD.clear()


def ahead(test):
    """What `test`'s waiting part saw: as started ahead (waiting_parts_run_ahead), or run now."""
    future = AHEAD.pop(test, None)
    return future.result() if future else WAITING_PARTS[test]()


# --- the toy table (score/graph/_toys.py): its worlds, store and runner ---------------------------------------------

def a_world(briefs):
    data = pathlib.Path(tempfile.mkdtemp())
    for place, text in briefs.items():
        (data / place).mkdir()
        if text is not None:
            (data / place / "brief.txt").write_text(text)
    return graph.Environment("toy", 7, {"data": data})


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def a_runner(world, store, stages=(CLEAN, COUNT)):
    return graph.Runner(stages, world, store, model_record=lambda kind: {"kind": kind})


def brief(world, place, text):
    (world.roots["data"] / place / "brief.txt").write_text(text)


def give_evidence(store, runner, place, limit):
    """A word limit as clean@place's evidence; its output."""
    output = store.record(f"clean@{place}", runner.key(runner.stages["clean"], place)["key"])["output"]
    path = pathlib.Path(tempfile.mkdtemp()) / "limit.json"
    path.write_text(json.dumps({"limit": limit}))
    store.put_evidence("words", output, path)
    return output


def ready_world():
    """Both places made, given a limit of 10 words and accepted; the world, store and clean outputs."""
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), a_store()
    runner = a_runner(world, store)
    runner.run(PLACES)
    outputs = {place: give_evidence(store, runner, place, 10) for place in PLACES}
    runner.run(PLACES)
    return world, store, outputs


def accepted_text(store, node, name):
    return (store.checkout(store.accepted(node)) / name).read_text()


MADE = pathlib.Path(tempfile.mkdtemp()) / "made.txt"  # a line a make, a forked run's makes too
CLEAN_SECONDS = [0]  # how long clean's make takes: two runs of it at once overlap


def makes_logged():
    """The makes logged since MADE was emptied, in turn."""
    return MADE.read_text().split() if MADE.exists() else []


def make_logged_clean(inputs, out, seed, params):
    with MADE.open("a") as log:
        log.write("clean\n")
    time.sleep(CLEAN_SECONDS[0])
    make_clean(inputs, out, seed, params)


def make_logged_count(inputs, out, seed, params):
    with MADE.open("a") as log:
        log.write("count\n")
    make_count(inputs, out, seed, params)


def make_takes(inputs, out, seed, params):
    (out / "takes.txt").write_text(json.dumps(params.get("retake")))


TAKEN = graph.Stage("takes", "place", make_takes, TEXT, PASSES, retakes=True)  # a row that retakes, reading nothing
LOGGED = (dataclasses.replace(CLEAN, make=make_logged_clean), dataclasses.replace(COUNT, make=make_logged_count),
          TAKEN)


def code_tar(folder):
    """This tree's score/, tools/ and uv.lock as a pod's code archive (the working files, as a frozen commit of an
    uncommitted tree archives them)."""
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                             "score", "tools", "uv.lock"], capture_output=True, check=True).stdout.decode()
    tar = folder / "code.tar"
    with tarfile.open(tar, "w") as archive:
        for name in filter(None, listed.split("\0")):
            if (REPO / name).is_file():
                archive.add(REPO / name, arcname=name)
    return tar


def a_pod_job(runner, stage, place, keyed, tree, bucket_root, folder, away=None):
    """The node's job for a pod running `tree`, pushed, the file `away` removed once pushed (the pod places it); its
    job file."""
    from score.graph import pod
    from score.store import offload
    job = pod.job_of(runner, stage, place, keyed, tree.name, "score.graph._toys:POD_TABLE")
    pod.pushed(runner, job, offload.FolderBucket(bucket_root), known=folder / "pushed")
    if away:
        away.unlink()
    work = pathlib.Path(tempfile.mkdtemp(dir=folder))
    (work / "job.json").write_text(json.dumps(job))
    return work / "job.json"


def in_pods(jobs, tree, bucket_root, folder):
    """Each job made by `python -m score.graph.pod run` from `tree`, each in an empty home of its own, the pods side by
    side (each works its code version out cold, about a second: the file's time budget); their manifests in order."""
    def made(job):
        pod_process(job, job.parent / "manifest.json", tree, bucket_root, folder)
        return json.loads((job.parent / "manifest.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(len(jobs)) as pool:
        return list(pool.map(made, jobs))


def pod_process(job, manifest, tree, bucket_root, folder):
    """`python -m score.graph.pod run` of the job at `job` from `tree`, in an empty home, its manifest to `manifest`."""
    home = pathlib.Path(tempfile.mkdtemp(dir=folder)) / "home"
    environ = {name: value for name, value in os.environ.items() if name != "SCORE_UV_LOCK"}
    subprocess.run([sys.executable, "-m", "score.graph.pod", "run", str(job), str(manifest),
                    "--cache", str(folder / "cache")], cwd=tree, check=True, capture_output=True,
                   env={**environ, "PROPS_HOME": str(home), "SCORE_POD_BUCKET": f"folder:{bucket_root}"})


def without_times(record):
    return {name: value for name, value in record.items()
            if name not in ("started", "finished", "minutes", "machine", "pod", "commit", "uncommitted")}


def a_pod_makes_what_the_runner_makes(monkeypatch):
    """A node made in a pod (score/graph/pod.py) gives Runner.make's output and record; a blob the bucket does not
    answer for refuses the manifest and stores nothing; a tree, lock or code version not the key's refuses and the
    node is made here; an undeclared store read is named, a blob written (a kept take's) is none; a row whose files
    the home's locked designs decide declares in the pod what it declares here, and so does one whose files the
    store's accepts decide; of two manifests for one key the first record stands; the takes a pod made and kept
    are kept here, and the next pod making the node puts them back instead of making them again, the same
    listing."""
    from score.graph import pod
    from score.store import offload
    folder = pathlib.Path(tempfile.mkdtemp())
    bucket_root = folder / "bucket"
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub", "dock": "a dock"}), a_store()
    runner = a_runner(world, store, (CLEAN,))
    runner.run(PLACES)
    for place in PLACES:
        give_evidence(store, runner, place, 10)
    runner.run(PLACES)
    twin = Store.in_folder(tempfile.mkdtemp())
    shutil.copytree(store.objects.root, twin.objects.root, dirs_exist_ok=True)
    runner, local = a_runner(world, store, POD_TABLE), a_runner(world, twin, POD_TABLE)
    home = Store.default()  # the store a row's file list reads its accepts from (light's: Store.default())
    shutil.copytree(store.objects.root, home.objects.root, dirs_exist_ok=True)
    home_runner = a_runner(world, home, POD_TABLE)
    offload.install(lambda: offload.FolderBucket(bucket_root))
    tree = pod.unpack(code_tar(folder), folder / "cache")
    assert pod.tree_refusal({"code": "0" * 64}).startswith("code: ")
    monkeypatch.setenv("SCORE_UV_LOCK", "0" * 64)
    assert pod.tree_refusal({"code": _code.REPO.name}).startswith("lock: ")
    monkeypatch.delenv("SCORE_UV_LOCK")
    jobs, made_here = [], []
    for stage, place in ((COUNT, "hangar"), (CLEAN, "dock")):
        keyed, away = runner.key(stage, place), world.roots["data"] / place / "brief.txt"
        made_here.append((stage, place, keyed, away, away.read_bytes()))
        jobs.append(a_pod_job(runner, stage, place, keyed, tree, bucket_root, folder, away if stage is CLEAN else None))
    station = runner.key(COUNT, "station")
    jobs.append(a_pod_job(runner, COUNT, "station", {**station, "code": "0" * 64}, tree, bucket_root, folder))
    jobs.append(a_pod_job(runner, PEEK, "hangar", runner.key(PEEK, "hangar"), tree, bucket_root, folder))
    plan = pathlib.Path(os.environ["PROPS_HOME"]) / "design" / "plans" / "hangar.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("{}")
    designed = [(runner, stage, runner.key(stage, "hangar")) for stage in (KEPT, DESIGNED)]
    designed.append((home_runner, RECORDED, home_runner.key(RECORDED, "hangar")))
    jobs += [a_pod_job(maker, stage, "hangar", keyed, tree, bucket_root, folder) for maker, stage, keyed in designed]
    manifests = in_pods(jobs, tree, bucket_root, folder)
    for (stage, place, keyed, away, written), manifest in zip(made_here, manifests):
        assert "listing" in manifest, {name: manifest.get(name) for name in ("refused", "undeclared", "error", "broken")}
        assert away.read_bytes() == written  # the pod placed the declared brief from the bucket
        wrong = {**manifest, "sizes": {sha: size + 1 for sha, size in manifest["sizes"].items()}}
        with pytest.raises(RuntimeError, match=pod.NOT_PROVEN):
            pod.collect(runner, stage, place, keyed, wrong)
        assert store.record(graph.node_name(stage, place), keyed["key"]) is None
        made, there = pod.collect(runner, stage, place, keyed, manifest), local.make(stage, place, keyed)
        assert without_times(made) == without_times(there) and "pod" in made
        node, judged = graph.node_name(stage, place), local.judge(stage, place, there)
        assert store.judgement(node, keyed["key"], judged["evidence"])["verdicts"] == judged["verdicts"]
        assert pod.collect(runner, stage, place, keyed, manifest) == made and len(store.records(node)) == 1
        name = "count.txt" if stage is COUNT else "clean.txt"
        assert (store.checkout(made["output"]) / name).read_text() == (twin.checkout(there["output"]) / name).read_text()
    refused, peeked = manifests[2:4]
    assert refused["refused"].startswith("code version: "), refused
    assert "pod" not in pod.collect(runner, COUNT, "station", station, refused)  # made here instead
    assert peeked.get("undeclared") == ["records/clean@hangar/any.json"], peeked
    for (maker, stage, keyed), manifest in zip(designed, manifests[4:]):
        assert "listing" in manifest, {name: manifest.get(name) for name in ("refused", "undeclared", "error", "broken")}
        assert pod.collect(maker, stage, "hangar", keyed, manifest, record=False) == \
            local.make(stage, "hangar", keyed)["output"]
    plan.unlink()
    keyed = runner.key(TAKES, "hangar")
    first = in_pods([a_pod_job(runner, TAKES, "hangar", keyed, tree, bucket_root, folder)], tree, bucket_root, folder)[0]
    assert len(first.get("kept", ())) == 2, first
    pod.collect(runner, TAKES, "hangar", keyed, first)
    again = a_pod_job(runner, TAKES, "hangar", keyed, tree, bucket_root, folder)
    assert set(json.loads(again.read_text())["kept"]) == set(first["kept"])
    second = in_pods([again], tree, bucket_root, folder)[0]
    assert second.get("kept") == {} and second.get("listing") == first["listing"], second
    assert fetched_side_by_side(pod, offload, folder, bucket_root) > 1

    # Runner.make of a stage made in pods (pod.dispatches): its job run on the cluster (cluster_jobs.run, here the
    # worker's part played in a subprocess) and collected; a job that did not finish is made here.
    cluster_jobs, sent = pod.cluster_door()[0], []

    class Named(offload.FolderBucket):
        name = "store"

    def ran_here(kind, jobs, who, classes=None, image=None, **_):
        inputs = {entry["path"]: entry["local"] for entry in jobs[0]["inputs"]}
        sent.append((kind, image, jobs[0]["env"], jobs[0]["cards"], classes))
        pod_process(inputs["/work/in/job.json"], jobs[0]["outputs"][0]["local"],
                    pod.unpack(inputs["/work/in/code.tar"], folder / "cache"), bucket_root, folder)
        return []
    offload.install(lambda: Named(bucket_root))
    monkeypatch.setattr(cluster_jobs, "run", ran_here)
    monkeypatch.setattr(pod, "dispatches", lambda stage: True)
    monkeypatch.setattr(pod, "TABLE", "score.graph._toys:POD_TABLE")
    monkeypatch.setattr(pod, "code_archive", lambda: folder / "code.tar")
    monkeypatch.setenv(pod.CLASSES_VARIABLE, "cpu-32c-64gb")
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)
    cleared = []  # a free node with no run-wide ticket is cleared on its own, at the pod's forecast
    monkeypatch.setattr(runner, "cleared", lambda node, euros, forecast: cleared.append((node, euros, forecast()))
                        or contextlib.nullcontext())
    keyed = runner.key(KEPT, "station")
    made, there = runner.make(KEPT, "station", keyed), local.make_here(KEPT, "station", keyed)
    assert without_times(made) == without_times(there) and "pod" in made, made
    assert sent == [("runner", "runner", {pod.STORE_VARIABLE: "store"}, 0, ["cpu-32c-64gb"])], sent
    assert cleared == [("kept@station", pod.POD_FORECAST["euros"], pod.POD_FORECAST)], cleared
    monkeypatch.setattr(cluster_jobs, "run", lambda *arguments, **named: [0])
    keyed = runner.key(PEEK, "station")
    assert "pod" not in runner.make(PEEK, "station", keyed) and store.record("peek@station", keyed["key"])


def fetched_side_by_side(pod, offload, folder, bucket_root):
    """32 blobs prefetched into an empty cache from a bucket that takes 50 ms a fetch; the most fetches at once."""
    shas, lock, at_once = [], threading.Lock(), {"now": 0, "most": 0}
    for index in range(32):
        blob = folder / "many" / f"{index}.bin"
        blob.parent.mkdir(exist_ok=True)
        blob.write_bytes(f"blob {index}".encode())
        shas.append(file_hash(blob))
        offload.push(blob, shas[-1], offload.FolderBucket(bucket_root))

    class Slow(offload.FolderBucket):
        def fetch(self, key, destination):
            with lock:
                at_once["now"] += 1
                at_once["most"] = max(at_once["most"], at_once["now"])
            time.sleep(0.05)
            super().fetch(key, destination)
            with lock:
                at_once["now"] -= 1
    offload.install(lambda: Slow(bucket_root))
    pod.prefetched(folder / "cache-many", shas)
    offload.install(lambda: offload.FolderBucket(bucket_root))
    assert all((folder / "cache-many" / "objects" / offload.blob_key(sha)).is_file() for sha in shas)
    return at_once["most"]


# --- keys: made once, judged again on new evidence, made again only where a change reaches ----------------------------

def test_a_key_is_made_once_and_a_change_remakes_only_what_it_reaches(monkeypatch):
    """New evidence judges an output again without making it again, and the runner accepts it; nothing changed makes
    nothing; a brief changed remakes its clean alone (the station's line stays fresh, the accepted output stays until
    the new one passes); a brief that cleans to the same text makes nothing after it. Seeds differ by environment,
    stage and place and hold for the same ones. An accepted record naming a stage the table lacks is stale, not a
    crash (fault 2026-10-12: status crashed).
    The runner accepts by itself only what passed and got no worse (owner, 2026-10-11, 'why are you asking this?':
    every output waited for his typed accept): the hall's longer brief passes its limit of 10 but is worse than the
    accepted 5, so it is not accepted and what reads it is blocked; inside a bought batch (owner, 2026-10-27) that
    passing worse output is accepted, its drop written down for review after the batch, never a wait; a brief of 2
    words is better: accepted; the owner's reject of it moves the accept back, never taken again by the runner, and
    leaves what read it stale, and its row is keyed once more (an again part, after the key he rejected; 2026-11-04),
    made and kept out, never a third time. His reject beside it of the retaking row's output naming takes
    (review.reject `takes`; owner, 2026-10-28: a failing object remade once, free) keys that row anew, its params'
    retake those takes, attempt 1, after the key he rejected, and the same run makes and accepts the retake, which
    follows a key moved by code before it ran and stays where it was made and kept; a later reject naming no takes
    keys nothing new.
    A key made in a pod is the same record (a_pod_makes_what_the_runner_makes).
    Two runs of one key at once make it once (2026-10-12: two runs made people-segvigen at once; the second paid
    again, then failed on the first's record): the second waits on the key's lock and finds the first's record; a
    record or judgement another run stored first is taken as made; a lock held past its wait blocks and makes nothing.
    Break: score/graph/__init__.py: '                with self.held(node_name(stage, place), keyed["key"]):' ->
    '                with contextlib.nullcontext():'
    Break: score/graph/__init__.py: '(self.store.evidence_hash(check.name, output) or "missing") if check.evidence
    else "none"' -> '"none"'
    Break: score/graph/__init__.py: 'text_hash(f"{world_seed}/{stage}/{place}")' -> 'text_hash(f"{world_seed}/{stage}")'
    Break: score/graph/__init__.py: '                   if before in self.stages}' -> '                   }'
    Break: score/graph/__init__.py: 'against = self.rejudged_accepted(stage, place) if judged' -> 'against = {} if
    judged'
    Break: score/graph/__init__.py: 'against, self.bought)' -> 'against)'
    Break: score/graph/__init__.py: '"files": self.file_keys(stage, place),' -> '"files": {},'
    Break: score/graph/pod.py: '    proven(bucket or offload.bucket_now(), manifest, node)\n' -> '' (the pod's
    manifest stored without its blobs proven).
    Break: score/graph/pod.py: 'FETCHES = 16' -> 'FETCHES = 1' (a pod's input blobs fetched one at a time).
    Break: score/graph/pod.py: 'and not offload.writing() and' -> 'and' (a kept take's new blob named an undeclared
    read, finish-route-views@tube 2026-11-07).
    Break: score/graph/pod.py: '"design": designs()}' -> '"design": {}}' (the pod's table, without the home's
    designs, declares a seed nothing makes, light-layer@tube 2026-11-07).
    Break: score/graph/pod.py: '**store_reads(runner, stage, place),' ->
    '"records": {}, "listed": [],' (the pod's
    sandbox, without the accepts and rejects a row's file list reads, works another list out, light@campgrounds
    2026-11-08).
    Break: score/graph/pod.py: '"kept": kept_module().calls_of(runner.making_code(stage, place, keyed))}' ->
    '"kept": {}}' (a pod's home holds no kept take, so it makes every take again, finish-route-views@campgrounds
    2026-11-08: 25 min against 0.06).
    Break: score/graph/pod.py: '    kept_back(manifest)\n' -> '' (the takes a pod made are never kept here).
    Break: score/graph/pod.py: '    kept_module().taken(found)\n' -> '' (the job's kept takes never written in the
    pod's home).
    Break: score/graph/__init__.py: '        if pod.dispatches(stage):' -> '        if False:' (Runner.make never sends
    a pod stage's node to the cluster, #76 S8).
    Break: score/graph/pod.py: '"HEAD^{tree}"' -> '"HEAD"' (each run's frozen commit a new code archive, tube
    rehearsal 2026-11-07).
    Break: score/graph/pod.py: 'if os.environ.get(compute.TICKET):' -> 'if True:' (a free node sent to a pod with
    no clearance of its own, tube rehearsal 2026-11-07).
    Break: score/graph/__init__.py: '        if stage.retakes:  # only' -> '        if False:  # only'; or
    again_parts' `return parts, text_hash(...)` -> `return parts, key` (a rejected record still reads as fresh); or
    retake_parts' `if record is None and (pending := self.pending_retake(node)):` -> `if False:` (a retake lost when
    the key moves by code before it runs, workshop's arm 2026-11-09); or retake_parts'
    `if self.store.record(node, followed[1]) or` -> `if` (a retake made and kept under a moved key lost again, its
    line stopped: checkout 71); or `or not self.retake_answered(node, pending)` left out (a retake made again after
    it was kept)."""
    assert graph.node_seed(7, "clean", "hangar") == graph.node_seed(7, "clean", "hangar")
    assert len({graph.node_seed(7, "clean", "hangar"), graph.node_seed(7, "clean", "station"),
                graph.node_seed(7, "count", "hangar"), graph.node_seed(8, "clean", "hangar")}) == 4
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), a_store()
    runner = a_runner(world, store, LOGGED)
    made = runner.run(PLACES)
    assert all(made[f"takes@{place}"] == "made: pass, accepted automatically" for place in PLACES), made
    outputs = {place: give_evidence(store, runner, place, 10) for place in PLACES}
    MADE.write_text("")
    found = runner.run(PLACES)
    assert found == {f"{stage}@{place}": status for place in PLACES for stage, status in (
        ("clean", "judged again, output kept: pass, accepted automatically"),
        ("count", "made: pass, accepted automatically"), ("takes", "fresh"))}, found
    assert makes_logged() == ["count", "count"]
    for place in PLACES:
        assert store.accepts(f"clean@{place}")[-1]["by"] == "runner"
        assert store.accepted(f"clean@{place}") == outputs[place]
    lone = a_runner(world, store, (dataclasses.replace(COUNT, after={}),))  # count's records name clean
    assert lone.stale("count@hangar") == ["clean (a stage this table does not hold)"]
    assert lone.status(["hangar"])["count@hangar"].endswith("clean (a stage this table does not hold) moved")
    MADE.write_text("")
    assert set(a_runner(world, store, LOGGED).run(PLACES).values()) == {"fresh"} and makes_logged() == []
    brief(world, "hangar", "a ship in a dark hall")
    runner = a_runner(world, store, LOGGED)
    assert runner.status(PLACES)["clean@hangar"] == "to run: brief changed"
    monkeypatch.setattr(graph, "LOCK_POLL", 0.05)  # the second run takes the lock once the first lets it go
    CLEAN_SECONDS[0] = 0.5  # two runs on the store at once, forked together: their cleans would overlap
    started = [run_in_a_process(a_runner(world, store, LOGGED), PLACES) for _ in range(2)]
    both = [receiving.recv() for _, receiving in started]
    for process, _ in started:
        process.join()
    CLEAN_SECONDS[0] = 0
    assert makes_logged() == ["clean"], both  # the second waited on the key's lock and found the first's record
    assert sorted(found["clean@hangar"] for found in both) == ["fresh", "made: unknown"], both  # no word limit yet
    for found in both:
        assert found["count@hangar"].startswith("blocked: clean@hangar answered unknown: words: no evidence"), found
        assert found["clean@station"] == found["count@station"] == "fresh", found
    assert store.accepted("clean@hangar") == outputs["hangar"]
    keyed = runner.key(runner.stages["clean"], "hangar")  # a record and a judgement another run stored first stand
    record = store.record("clean@hangar", keyed["key"])
    assert runner.make(runner.stages["clean"], "hangar", keyed) == record
    judged = store.judgement("clean@hangar", keyed["key"], runner.evidence_state(runner.stages["clean"],
                                                                                  record["output"]))
    assert judged and runner.judge(runner.stages["clean"], "hangar", record) == judged
    MADE.write_text("")
    brief(world, "station", "A HUB")  # the same text once cleaned
    runner = a_runner(world, store, LOGGED)
    with monkeypatch.context() as waiting:  # another run holds clean@station's key past the wait: nothing is made
        waiting.setattr(graph, "LOCK_WAIT", 0.2)
        with a_runner(world, store, LOGGED).held("clean@station", runner.key(runner.stages["clean"], "station")["key"]):
            did = runner.run_node(runner.stages["clean"], "station")
    assert did.startswith("blocked: clean@station: another run has held its lock") and "pid" in did, did
    assert makes_logged() == []
    found = runner.run(PLACES)
    assert found["clean@station"] == "made: pass" and found["count@station"] == "fresh", found
    assert makes_logged() == ["clean"]
    assert len(store.records("clean@station")) == 2  # both finish records kept
    worse = give_evidence(store, a_runner(world, store, LOGGED), "hangar", 10)
    found = a_runner(world, store, LOGGED).run(PLACES)
    assert found["clean@hangar"] == "judged again, output kept: pass", found
    assert found["count@hangar"] == (f"blocked: clean@hangar's output {worse[:12]} is not accepted "
                                     f"(accepted: {outputs['hangar'][:12]})"), found
    assert store.accepted("clean@hangar") == outputs["hangar"]
    runner = a_runner(world, store, LOGGED)
    runner.bought = True
    found = runner.run(PLACES)
    assert found["clean@hangar"] == "fresh, accepted automatically" and store.accepted("clean@hangar") == worse, found
    given = store.accepts("clean@hangar")[-1]
    assert given["worse_reason"] == review.IN_BATCH and given["worse"], given
    assert given["status"].startswith("to review after the batch, worse: "), given
    brief(world, "hangar", "a ship")
    runner = a_runner(world, store, LOGGED)
    runner.run(PLACES)
    better = give_evidence(store, runner, "hangar", 10)
    found = a_runner(world, store, LOGGED).run(PLACES)
    assert found["clean@hangar"].endswith("accepted automatically") and store.accepted("clean@hangar") == better
    assert found["count@hangar"] == "made: pass, accepted automatically", found
    rejected = runner.key(runner.stages["clean"], "hangar")["key"]  # the key whose output he rejects
    first = runner.key(TAKEN, "hangar")["key"]  # the retaking row's key, its output rejected naming takes
    review.reject(store, "clean@hangar", better, "owner", "the hall is gone")
    review.reject(store, "takes@hangar", store.accepted("takes@hangar"), "owner", "a block", takes=("seat-s1",))
    assert store.accepted("clean@hangar") == worse  # back to the accept before it, the bought batch's
    runner = a_runner(world, store, LOGGED)
    assert runner.stale("count@hangar") == ["clean@hangar"] and runner.stale("count@station") == []
    assert runner.status(PLACES)["count@hangar"].endswith("its accepted output is stale: clean@hangar moved")
    again = runner.key(runner.stages["clean"], "hangar")
    assert again["again"]["after"] == rejected and again["key"] != rejected, again
    keyed = runner.key(TAKEN, "hangar")
    assert keyed["params"]["retake"] == {"takes": ["seat-s1"], "attempt": 1, "after": first}, keyed["params"]
    moved = dataclasses.replace(TAKEN, params={"moved": "by code"})  # its key moved before the retake ran
    shifted = a_runner(world, store, (*LOGGED[:2], moved)).key(moved, "hangar")
    assert shifted["params"].get("retake", {}).get("takes") == ["seat-s1"], shifted["params"]  # the retake follows it
    MADE.write_text("")
    found = a_runner(world, store, (*LOGGED[:2], moved)).run(PLACES)
    # made once again after his reject (again_parts); the same bytes come back, still rejected, so count stays blocked
    assert found["clean@hangar"] == "made: pass" and found["count@hangar"].startswith("blocked: clean@hangar's output")
    assert found["takes@hangar"].endswith("accepted automatically"), found  # the retake, made under the moved key
    assert found["takes@station"] == "made: pass", found  # moved by code too, no retake: its bytes the accepted ones
    assert makes_logged() == ["clean"]
    after = a_runner(world, store, (*LOGGED[:2], moved))
    assert after.key(after.stages["clean"], "hangar")["key"] == again["key"]  # never a third make
    kept = after.key(moved, "hangar")  # made and kept there: its key stays (checkout 71)
    assert kept["key"] == shifted["key"] and store.record("takes@hangar", kept["key"]), kept["params"]
    assert runner.run(["hangar"])["takes@hangar"].endswith("accepted automatically")
    later = dataclasses.replace(TAKEN, params={"moved": "by code again"})  # a later move leaves no record there
    assert "retake" not in a_runner(world, store, (later,)).key(later, "hangar")["params"]  # retaken: never again
    retaken = store.accepted("takes@hangar")
    assert json.loads((store.checkout(retaken) / "takes.txt").read_text())["takes"] == ["seat-s1"]
    review.reject(store, "takes@hangar", retaken, "owner", "no")
    assert a_runner(world, store, (TAKEN,)).key(TAKEN, "hangar")["key"] == keyed["key"]  # no takes: nothing new
    one_tree_one_code_archive()  # before the pod check patches code_archive
    a_pod_makes_what_the_runner_makes(monkeypatch)


def one_tree_one_code_archive():
    """Two commits of one tree (each run's frozen commit) give one code archive, byte for byte, so the queue's workers
    upload and unpack it once; a changed file gives another."""
    from score.graph import pod
    repo, folder = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    environ = {**os.environ, **GIT_ENV}

    def git(*command):
        subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", *command], check=True,
                       capture_output=True, env=environ)
    (repo / "made.py").write_text("print('one')\n")
    git("init", "-q")
    git("add", ".")
    git("commit", "-qm", "one")
    first = pod.code_archive(folder, repo).read_bytes()
    environ.update(GIT_AUTHOR_DATE="2001-01-01T00:00:00Z", GIT_COMMITTER_DATE="2001-01-01T00:00:00Z")
    git("commit", "-q", "--allow-empty", "-m", "two")
    assert pod.code_archive(folder, repo).read_bytes() == first
    (repo / "made.py").write_text("print('two')\n")
    git("commit", "-qam", "three")
    assert pod.code_archive(folder, repo).read_bytes() != first


# --- a failed output is made once more when that is free (owner, 2026-10-28: "the goal was getting to the film") -----

# a free node's failed output is made once more (the toy make ignores the seed, so it fails again)
SECOND_FAILURE = ("judged again, output kept: fail; automatic free remake, attempt 2, after words: made: fail; "
                  "the second failure: on the owner's list, priced")


def make_seeded(inputs, out, seed, params):
    (out / "seed.txt").write_text(str(seed))


def judge_first_seed(output, inputs, evidence):
    seed = int((output / "seed.txt").read_text())
    first = seed == graph.node_seed(7, "pick", "hangar")  # the node's own seed, worked out by hand
    return checks.Verdict("first-seed", checks.FAIL if first else checks.PASS, "the first seed" if first else "another",
                          {"seed": seed})


PICK = graph.Stage("pick", "place", make_seeded, TEXT, (checks.Check("first-seed", judge_first_seed),))


def noted(runner, name):
    path = runner.store.cache.parent / "remakes" / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_a_node_works_out_its_key_in_a_still_of_its_own_the_drive_s_key_and_makes_outside_it(monkeypatch):
    """2026-10-30: a node's process worked out its key outside a still, every read listed again: 6-15 min before a
    make of seconds (sim-body, characters-layer). run_node works it out in a still of its own, the key the drive's
    still gives, closed before the make writes, so what the make stores is read fresh (a free remake's re-key, below).
    Break: score/graph/__init__.py: '        with self.still():\n            return self.key(stage, place)'
    -> '        if True:\n            return self.key(stage, place)'
    #76 (build spec S7): with hundreds of nodes in flight each process's key walk would be the bound, so the drive
    hands the key of its pass to the node's process (start's `given`), which under the node's lock re-checks every
    earlier output it reads and its files: unmoved, it is made on that key with no walk of its own; an upstream accept
    that moved between the pass and the lock re-keys it (here: blocked on the moved accept) and no record is written
    under the stale key. Break: score/graph/__init__.py: 'if drives and self.moved_since(stage, place, drives):' ->
    'if False:' -> count made on the stale key."""
    marked = make_marked("clean")
    runner = a_runner(a_world({"hangar": "a ship"}), a_store(), (marked, COUNT))
    keyed, made, worked_out, make = [], [], graph.Runner.worked_out_key, graph.Runner.make
    monkeypatch.setattr(graph.Runner, "worked_out_key", lambda self, stage, place: keyed.append(
        self.remembered is not None) or worked_out(self, stage, place))
    monkeypatch.setattr(graph.Runner, "make", lambda self, stage, place, key: made.append(
        self.remembered is None) or make(self, stage, place, key))
    assert set(runner.run(["hangar"]).values()) == {ACCEPTED}
    assert keyed and all(keyed) and made == [True, True], (keyed, made)
    with runner.still():  # as the drive works them out
        driven = {stage.name: runner.key(stage, "hangar")["key"] for stage in (marked, COUNT)}
    assert all(runner.store.record(f"{name}@hangar", key) for name, key in driven.items()), driven

    store = a_store()
    a_runner(a_world({"hangar": "a ship"}), store, (marked,)).run(["hangar"])
    both = a_runner(a_world({"hangar": "a ship"}), store, (marked, COUNT))
    with both.still():  # the drive's pass
        given = both.key(COUNT, "hangar")
    walks = len(keyed)
    unmoved = a_runner(a_world({"hangar": "a ship"}), Store.in_folder(tempfile.mkdtemp()), (marked, COUNT))
    shutil.copytree(store.objects.root, unmoved.store.objects.root, dirs_exist_ok=True)
    assert unmoved.run_node(COUNT, "hangar", given) == ACCEPTED and len(keyed) == walks  # no walk of its own
    assert unmoved.store.record("count@hangar", given["key"])
    # 2026-11-11: a fresh node's process then walked its whole reads again outside a pass for its gatherable checks,
    # holding its job slot 1-8 min. Break: 'self.gatherable(stage, place, self.ran)' -> 'self.gatherable(stage, place)'
    monkeypatch.setattr(graph, "cap_threads", lambda threads: None)  # in this process: the tests' pools stay theirs
    assert unmoved.drive_node(COUNT, "hangar", 1, given) == "fresh" and len(keyed) == walks, keyed
    moved = pathlib.Path(tempfile.mkdtemp())
    (moved / "clean.txt").write_text("moved")
    contracts.stamp(TEXT, moved)
    output = store.put_tree(moved)
    store.write_accept("clean@hangar", {"node": "clean@hangar", "output": output, "at": graph.now(), "by": "test"})
    did = both.run_node(COUNT, "hangar", given)
    assert did.startswith("blocked: clean@hangar") and store.record("count@hangar", given["key"]) is None, did


def judge_parts(output, inputs, evidence):
    return checks.Verdict("parts", checks.FAIL, "a model made upstream lacks its parts", findings=("crate: no lid",))


def judge_gaps(output, inputs, evidence):
    """Accepted gaps naming the objects of the brief's words ("hatch hatch": one object, "hatch ship": two)."""
    objects = inputs["brief"].read_text().split()
    return checks.Verdict(graph.GAPPED, checks.FAIL, "batch gaps", {"gaps": len(objects)}, {"gaps": "lower"},
                          tuple(f"{name}: no model: {name}: none" for name in objects))


SHOUT = graph.Stage("clean", "place", make_clean, TEXT, (checks.Check("shout", judge_shout),),
                    files={"brief": "{data}/{place}/brief.txt"})
PAID_SHOUT = dataclasses.replace(SHOUT, paid=True, euros=0.4)
UNSEEDED_PARTS = graph.Stage("pick", "place", make_seeded, TEXT, (checks.Check("parts", judge_parts),), seeded=False)
GAPPED_ROW = graph.Stage("gapped", "place", make_seeded, TEXT, (checks.Check(graph.GAPPED, judge_gaps),),
                         files={"brief": "{data}/{place}/brief.txt"}, seeded=False)
FIRST_SEED = {"first-seed": {"seed": graph.node_seed(7, "pick", "hangar")}}  # the node's own seed, by hand
REMADE = "automatic free remake, attempt 2, after "
GAPS = "its accepted gaps name 2 objects, at most 1 passes on to the film"

# A failed output's fate, one row a world: (id, stage, the hangar's brief, its make asks a cache, this PC's card,
# what the run did, the notes [(attempt, then, {failed check: measures}, a fix's why)], the owner's list
# [(attempt, why, euros)], the records under the node, the standing record's remake why). Worked out by hand from the toy rows: PICK fails
# only on its own first seed; SHOUT fails on "!" whatever its seed; parts fails always; gaps count the brief's words.
FATES = [
    ("free-remake-passes", PICK, "a ship", False, None,
     f"made: fail; {REMADE}first-seed: made: pass, accepted automatically",
     [(1, "remake", FIRST_SEED, None), (2, "done", {}, None)], [], 2, f"{REMADE}first-seed"),
    ("free-remake-fails-again", SHOUT, "a ship!", False, None,
     f"made: fail; {REMADE}shout: made: fail; the second failure: on the owner's list, priced",
     [(1, "remake", {"shout": {}}, None), (2, "owner", {"shout": {}}, None)], [(2, "both attempts failed", 0.0)], 2,
     f"{REMADE}shout"),
    ("paid-off-this-pc", PAID_SHOUT, "a ship!", False, None,
     "made: fail; a paid remake: on the owner's list, priced",
     [(1, "owner", {"shout": {}}, None)], [(1, "its remake is paid", 0.4)], 1, None),
    ("paid-on-this-pcs-card", PAID_SHOUT, "a ship!", False, "local",
     f"made: fail; {REMADE}shout: made: fail; the second failure: on the owner's list, priced",
     [(1, "remake", {"shout": {}}, None), (2, "owner", {"shout": {}}, None)], [(2, "both attempts failed", 0.4)], 2,
     f"{REMADE}shout"),
    ("cached-asks", PICK, "a ship", True, None, f"made: fail; {graph.SAME_ANSWER}",
     [(1, "fix", FIRST_SEED, graph.SAME_ANSWER)], [], 1, None),
    ("check-of-inputs", UNSEEDED_PARTS, "a ship", False, None,
     f"made: fail; {graph.SAME_INPUTS}: crate: no lid",
     [(1, "fix", {"parts": {}}, f"{graph.SAME_INPUTS}: crate: no lid")], [], 1, None),
    ("one-gap-object", GAPPED_ROW, "hatch hatch", False, None, "made: fail, accepted automatically", [], [], 1, None),
    ("two-gap-objects", GAPPED_ROW, "hatch ship", False, None, f"made: fail; {GAPS}: on the owner's list, priced",
     [(1, "owner", {graph.GAPPED: {"gaps": 2}}, None)], [(1, GAPS, 0.0)], 1, None),
]


def test_a_failed_output_is_made_once_more_only_when_free_and_otherwise_noted_for_a_fix_or_the_owner(monkeypatch):
    """Owner, 2026-10-28: "the goal was getting to the film". A free node's failed output is made once more with a
    fresh seed: a pass is accepted, its record and the remake log naming the failed check with its measures; a second
    failure, or a paid remake off this PC, goes on the owner's list at its price with every attempt in its fault
    report (on this PC's card a paid row is remade). A failed row of cached model asks ("it should only actually
    retry if the prompt changed"; the finish route's list asks through the cached Claude and Google routes, the stage
    table's own files do not count) or a check of inputs (likeness@airlock 2026-10-29: a row whose make never uses its
    seed, remade, failed the same way and went to the owner's list) is noted once for a source fix, its failing
    objects named, never remade, never listed; the table marks its check rows and sim-body (no random start,
    2026-10-30). A row failing only on accepted gaps naming one object is accepted; two go on the owner's list with
    the count (shiplock's complete, nine gap objects accepted automatically 2026-11-12). A later drive of any of
    them remakes, notes and lists nothing more.
    Break: score/graph/__init__.py: '        if note and note["then"] == "remake":' -> '        if False:'
    Break: score/graph/__init__.py: '    def run_node(self, stage, place, given=None):\n' -> the same line, then
    '        with self.still():\n            return self.run_node_whole(stage, place, given)\n\n    def
    run_node_whole(self, stage, place, given=None):\n' (run_node's body under one still pass: the re-key reads the
    first key, kept in the pass, and the remake stores nothing new).
    Break: score/graph/__init__.py: 'else "remake" if free and not second else "owner"' -> 'else "remake" if free else
    "owner"'
    Break: score/graph/__init__.py: '        then = "fix" if not second and (not stage.seeded or asks_cached(stage)) else' -> '        then = "fix" if not second and not stage.seeded else'
    Break: score/graph/__init__.py: '        then = "fix" if not second and (not stage.seeded or asks_cached(stage)) else' -> '        then = "fix" if not second and asks_cached(stage) else'
    Break: score/stages/__init__.py: '"light", "motion", "sim-body")' -> '"light", "motion")'
    Break: score/graph/__init__.py: 'then = "owner" if too_many_gaps(failed) else then' -> 'then = then'
    Break: score/graph/__init__.py: 'entry["why"] = fix_why(stage, entry["failed"])' -> 'entry["why"] = ", ".join(
    entry["failed"])' (the note's why names the checks, not the findings)
    Break: score/graph/__init__.py: 'self.evidence_state(stage, record["output"])) is not None:' -> '... is not None
    and False:' (a later run judges the standing output again)"""
    from score import stages
    from score.stages import physics
    from score.stages.surfaces import route_list
    _code.search_folders.cache_clear()  # its folders on the path, as a run's table import puts them before any key
    for make, cached in ((route_list.make_list, True), (physics.make_trial, False)):  # trial: only via the table
        assert graph.asks_cached(dataclasses.replace(PICK, make=make)) is cached, make
    assert {row.name for row in stages.STAGES if not row.seeded} == set(stages.UNSEEDED)
    assert not next(row for row in stages.STAGES if row.name == "sim-body").seeded  # its remakes were byte-identical
    asks = graph.CACHED_ASKS
    for name, stage, text, cached, here, did, notes, owner, records, remade in FATES:
        monkeypatch.setattr(graph, "CACHED_ASKS", {pathlib.Path(__file__).resolve()} if cached else asks)
        monkeypatch.setattr(graph, "on_this_pc", lambda: here == "local")
        world, store = a_world({"hangar": text}), a_store()
        runner = a_runner(world, store, (stage,))
        monkeypatch.setattr(runner, "cleared", lambda node, euros, forecast=None: contextlib.nullcontext())
        node = f"{stage.name}@hangar"
        assert runner.run(["hangar"]) == {node: did}, name
        written = noted(runner, "notes")
        assert [(entry["attempt"], entry["then"], {check: verdict["measures"] for check, verdict in
                 entry["failed"].items()}, entry["why"] if entry["then"] == "fix" else None)
                for entry in written] == notes, (name, written)
        listed = noted(runner, "owner-list")
        assert [(entry["node"], entry["attempt"], entry["why"], entry["euros"]) for entry in listed] == \
            [(node, *entry) for entry in owner], (name, listed)
        record = store.record(node, runner.key(stage, "hangar")["key"])
        assert len(store.records(node)) == records and record.get("remake", {}).get("why") == remade, (name, record)
        stands = did.endswith("accepted automatically")
        assert store.accepted(node) == (record["output"] if stands else None), name
        runner.drive(["hangar"], say=quiet)
        assert noted(runner, "notes") == written and noted(runner, "owner-list") == listed, name
        assert len(store.records(node)) == records, (name, store.records(node))
        assert not stands or a_runner(world, store, (stage,)).run(["hangar"]) == {node: "fresh"}, name
        if written and not stands:  # a noted node that does not stand: every attempt in its fault report
            text = report_of(runner, node).read_text()
            assert all(f"attempt {entry['attempt']} (key " in text for entry in written if entry["failed"]), name
            assert all(f"{entry['why']}: on the owner's list, priced EUR {entry['euros']:.2f}" in text
                       for entry in listed) and all(entry["why"] in text for entry in written[-1:]
                                                     if entry["then"] == "fix"), (name, text)


def make_maybe(inputs, out, seed, params):
    (out / "maybe.txt").write_text("read clean" if "clean" in inputs else "clean not usable: left out")


def make_tally(inputs, out, seed, params):
    (out / "tally.txt").write_text("read clean" if "clean" in inputs else "read without clean")


def place_briefs(place):
    """The hangar reads a second file only it has."""
    return {"brief": "{data}/{place}/brief.txt", **({"notes": "{data}/hangar/notes.txt"} if place == "hangar" else {})}


def test_a_node_reads_only_inputs_that_exist_apply_and_stand_and_a_failed_gate_passes_only_waived_for_its_key():
    """One world of four places and one table: clean (no node at the dock; the hangar's also reads notes), maybe
    (reads clean optionally) and tally (reads clean). A missing input blocks its node and each place is keyed on its own
    files; the dock's tally reads without clean; maybe leaves clean out while it is blocked, unknown or failed and takes
    it once it stands; a failed clean (7 words, limit 2) blocks tally until the owner's waiver for that key, which is
    shown, and a new key (8 words) fails again. Before the run starts, the inputs it could never make are named (node,
    input, path): the hangar's notes and the shed's brief, never a file the run makes as it goes (under {home}), and
    none once they exist (the ship run of 2026-10-14 spent EUR 13.58, then stopped on missing seed records).
    Break: score/graph/__init__.py: '                if not pattern.startswith(("{data}", "{repo}")):' -> '                if False:'
    Break: score/graph/__init__.py: '            if not path.exists():\n                raise Blocked(f"{node_name(stage, place)}: its input' -> '            if False:\n                raise Blocked(f"{node_name(stage, place)}: its input'
    Break: score/graph/__init__.py: '                if place is None or stage.applies is None or stage.applies(place):' -> '                if True:'
    Break: score/graph/__init__.py: 'if every or before not in stage.optional or self.usable_now(before, place, wanted)}' -> 'if True}'
    Break: score/graph/__init__.py: 'if checks.blocks(checks.standing(judgement["verdicts"], waived)) and not on_gaps:' -> 'if checks.blocks(checks.standing(judgement["verdicts"], set())) and not on_gaps:'"""
    places = ("hangar", "station", "dock", "shed")
    world = a_world({"hangar": "a ship in a very long hall", "station": "a hub", "dock": None, "shed": None})
    world = graph.Environment("toy", 7, {**world.roots, "home": str(tempfile.mkdtemp())})
    data = world.roots["data"]
    clean = dataclasses.replace(CLEAN, files=place_briefs, applies=lambda place: place != "dock")
    taken = graph.Stage("taken", "place", make_seen, TEXT, SEEN, files={"take": "{home}/takes/{place}.glb"})
    maybe = graph.Stage("maybe", "place", make_maybe, TEXT, PASSES, after={"clean": READS}, optional=("clean",))
    tally = graph.Stage("tally", "place", make_tally, TEXT, PASSES, after={"clean": READS})
    store, table = a_store(), (clean, maybe, tally)
    runner = a_runner(world, store, table)
    assert [node for node in runner.status(places) if node.startswith("clean@")] == [
        "clean@hangar", "clean@station", "clean@shed"]
    planned = [(clean, "hangar"), (clean, "station"), (clean, "shed"), (taken, "hangar")]
    assert runner.missing_inputs(planned) == [f"clean@hangar: notes ({data / 'hangar/notes.txt'})",
                                              f"clean@shed: brief ({data / 'shed/brief.txt'})"]
    found = runner.run(places)  # the hangar's notes are not written yet; the shed has no brief
    assert found["clean@hangar"].startswith("blocked: clean@hangar: its input notes"), found
    assert found["clean@shed"].startswith("blocked: clean@shed: its input brief is missing"), found
    assert found["tally@dock"] == "made: pass, accepted automatically", found
    assert accepted_text(store, "tally@dock", "tally.txt") == "read without clean"
    assert runner.earlier(tally, "dock") == [] and runner.earlier(tally, "hangar") == ["clean@hangar"]
    assert found["maybe@hangar"].startswith("made: pass"), found
    (data / "hangar" / "notes.txt").write_text("notes")
    assert runner.missing_inputs([(clean, "hangar"), (clean, "station")]) == []
    assert set(runner.key(clean, "hangar")["files"]) == {"brief", "notes"}
    assert set(runner.key(clean, "station")["files"]) == {"brief"}
    found = a_runner(world, store, table).run(["hangar"])  # clean unknown: no word limit yet
    assert found["tally@hangar"].startswith("blocked: clean@hangar answered unknown"), found
    assert found["maybe@hangar"] == "fresh", found
    output = give_evidence(store, a_runner(world, store, table), "hangar", 2)  # 7 words: clean fails
    found = a_runner(world, store, table).run(["hangar"])
    assert found == {"clean@hangar": SECOND_FAILURE, "maybe@hangar": "fresh",
                     "tally@hangar": "blocked: clean@hangar answered fail: words: 7 words, limit 2"}, found
    assert accepted_text(store, "maybe@hangar", "maybe.txt") == "clean not usable: left out"
    key = runner.key(clean, "hangar")["key"]
    store.write_waiver("clean@hangar", key, "words", {"by": "owner", "reason": "a long name", "at": graph.now()})
    found = a_runner(world, store, table).run(["hangar"])
    assert found["clean@hangar"] == "fresh, accepted automatically", found
    assert found["tally@hangar"] == "made: pass, accepted automatically", found
    assert store.accepted("clean@hangar") == output
    assert a_runner(world, store, table).status(["hangar"])["clean@hangar"] == "fail, waived: words, accepted"
    brief(world, "hangar", "a ship in a very long dark hall")
    a_runner(world, store, table).run(["hangar"])
    give_evidence(store, a_runner(world, store, table), "hangar", 2)
    found = a_runner(world, store, table).run(["hangar"])
    assert found["tally@hangar"] == "blocked: clean@hangar answered fail: words: 8 words, limit 2", found
    brief(world, "hangar", "a hall")
    a_runner(world, store, table).run(["hangar"])
    give_evidence(store, a_runner(world, store, table), "hangar", 2)
    found = a_runner(world, store, table).run(["hangar"])
    assert found["maybe@hangar"].startswith("made: pass"), found
    assert accepted_text(store, "maybe@hangar", "maybe.txt") == "read clean"


def make_writing(inputs, out, seed, params):
    """Writes each of params' `writes` ([declared input, file name]) in the folder that input is or lies in, as another
    agent's pull or the make itself would; with `imports`, imports made_here from its declared code folder, in its own
    process and in a child's."""
    for name, written in params.get("writes", ()):
        folder = inputs[name] if inputs[name].is_dir() else inputs[name].parent
        (folder / written).parent.mkdir(parents=True, exist_ok=True)
        (folder / written).write_text("pulled in mid-run")
    if params.get("imports"):
        sys.path.insert(0, str(inputs["code"]))
        try:
            import made_here  # noqa: F401
        finally:
            sys.path.remove(str(inputs["code"]))
            sys.modules.pop("made_here", None)
        subprocess.run([sys.executable, "-c", "import made_here"], cwd=inputs["code"], check=True)
    (out / "clean.txt").write_text("made")


BRIEF, CODE, PLACE = {"brief": "{data}/{place}/brief.txt"}, {"code": "{data}/code"}, {"place": "{data}/{place}"}
DROPPED = "dropped: clean@hangar: an input changed while it ran"
# A make that writes into its world as it runs. Each row: its declared files; its params (make_writing); then what it
# pins: how its run ends (`made: pass`, or dropped with no record kept), and the declared folder it leaves exactly as
# it was, no __pycache__ in it (None: none).
MOVED_UNDER = {
    "a-pull-beside-its-brief-outside-its-key": (BRIEF, {"writes": [["brief", "notes.txt"]]}, "made: pass", None),
    "its-own-brief-moved": (BRIEF, {"writes": [["brief", "notes.txt"], ["brief", "brief.txt"]]}, DROPPED, None),
    "a-code-folder-it-imports-in-two-processes": (CODE, {"imports": True}, "made: pass", "code"),
    "bytecode-in-a-folder-it-reads": (PLACE, {"writes": [["place", "__pycache__/brief.cpython-312.pyc"],
                                                         ["place", "stray.pyc"]]}, "made: pass", None),
    "a-source-in-a-folder-it-reads": (PLACE, {"writes": [["place", "notes.txt"]]}, DROPPED, None),
}


@pytest.mark.parametrize("row", MOVED_UNDER.values(), ids=MOVED_UNDER.keys())
def test_a_make_is_dropped_only_when_a_non_bytecode_input_in_its_key_moved_under_it(row):
    """#45: earth-kit@airlock's 14 paid bake jobs were thrown away when the checkout moved under its run: a make is
    dropped, nothing kept, only when a file in its key moved while it ran. #67: each checkout writes its own
    __pycache__ into a declared code folder, and keys hashed it: a node's import leaves its code folder as it was, and
    bytecode in a declared folder is no input, while a source there is.
    Break: score/graph/__init__.py: 'if self.file_keys(stage, place) != keyed["files"]:' -> 'if False:' -> its own
    brief and a source in its folder are kept.
    Break: score/graph/__init__.py: 'for name, found in tree_files(path).items() if not bytecode(name)})' ->
    'for name, found in tree_files(path).items()})' -> the bytecode row is dropped."""
    files, params, ends, left_alone = row
    world, store = a_world({"hangar": "a ship"}), a_store()
    (world.roots["data"] / "code").mkdir()
    (world.roots["data"] / "code" / "made_here.py").write_text("WORD = 'made'\n")
    before = tree_hash(world.roots["data"] / "code")
    stage = graph.Stage("clean", "place", make_writing, TEXT, PASSES, files=files, params=params)
    try:
        did = a_runner(world, store, (stage,)).run(["hangar"])["clean@hangar"]
    except RuntimeError as error:
        did = f"dropped: {error}"
    assert did.startswith(ends) and bool(store.records("clean@hangar")) == (ends != DROPPED), (did, ends)
    if left_alone:
        assert tree_hash(world.roots["data"] / left_alone) == before
        assert not (world.roots["data"] / left_alone / "__pycache__").exists()


TICKETS = []


def make_paid(inputs, out, seed, params):
    TICKETS.append(os.environ.get(compute.TICKET))
    make_count(inputs, out, seed, params)


def make_nothing_written(inputs, out, seed, params):
    (out / "notes.md").write_text("no text file")


def test_an_accepted_output_is_traced_stamped_and_read_only_on_its_contract_and_clearance(monkeypatch):
    """One ready world (both places made and accepted); `why` walks count@hangar back to its brief, every output
    carries its contract stamp, and one run of a table holding a reader of a newer contract version, a paid stage with
    no estimate, a priced paid stage and a stage writing off its contract answers each on its own terms.
    Fault (review of step 0, 2026-10-11): no output carried a schema or version, and nothing checked one.
    Break: score/graph/__init__.py: '            lines += self.why(node_name(*before), depth + 1)' -> '            pass'
    Break: score/graph/__init__.py: '        if not stage.paid:\n            return contextlib.nullcontext()' -> '        if True:\n            return contextlib.nullcontext()'
    Break: score/graph/__init__.py: '        contracts.stamp(stage.contract, out)\n' -> '\n'"""
    world, store, outputs = ready_world()
    lines = a_runner(world, store).why("count@hangar")
    assert lines[0].startswith("count@hangar: output") and "pass, accepted" in lines[0]
    assert lines[1].startswith("  clean@hangar: output") and "pass, accepted" in lines[1]
    assert f"brief {tree_hash(world.roots['data'] / 'hangar' / 'brief.txt')[:12]}" in lines[1]
    stamp = json.loads((store.checkout(outputs["hangar"]) / contracts.STAMP).read_text())
    assert stamp == {"schema": "toy-text", "version": 1, "units": {}}
    assert store.records("clean@hangar")[-1]["contract"] == stamp
    monkeypatch.setattr(compute.ledger(), "entries", lambda: [])
    TICKETS.clear()
    newer = dataclasses.replace(COUNT, after={"clean": ("toy-text", 2)})
    unpriced = graph.Stage("render", "place", make_paid, TEXT, PASSES, after={"clean": READS}, paid=True)
    paid = dataclasses.replace(unpriced, name="paid", euros=0.5)
    notext = graph.Stage("notext", "place", make_nothing_written, TEXT, files={"brief": "{data}/{place}/brief.txt"})
    runner = a_runner(world, store, (CLEAN, newer, unpriced, paid, notext))
    found = runner.run(["hangar"])
    assert found["count@hangar"] == "blocked: clean@hangar's output is toy-text v1; expected toy-text v2", found
    assert "needs its estimate" in found["render@hangar"], found
    assert found["paid@hangar"] == "made: pass, accepted automatically", found
    key = runner.ticket("paid@hangar")["key"]
    assert TICKETS == [f"paid@hangar {key}"] and store.spend_yes("paid@hangar", key) is None
    assert found["notext@hangar"] == "broken: off its contract toy-text v1: no text file", found
    assert store.records("notext@hangar") == []
    with pytest.raises(TypeError, match="contract"):
        graph.Stage("clean", "place", make_clean, None)


# --- the code version: every repository file a stage's functions import, however the path is ordered ----------------

@contextlib.contextmanager
def modules_of_its_own(prefix, files):
    """{relative path: text} written under a folder of the repository's own (the code version follows repository files
    only), each top folder put first on the path while the block runs; yields the folder."""
    root = pathlib.Path(tempfile.mkdtemp(prefix=prefix, dir=REPO / "score/graph"))
    saved = list(sys.path)
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    try:
        yield root
    finally:
        sys.path[:] = saved
        for name in files:
            sys.modules.pop(pathlib.Path(name).stem, None)
        _code.search_folders.cache_clear()
        shutil.rmtree(root)


CODE_FILES = {"start/follow_start.py": "def work():\n    import follow_inner\n    return follow_inner.VALUE\n",
              "inner/follow_inner.py": "import numpy\nVALUE = 1\n",
              "start/follow_judge.py": "def judge(output, inputs, evidence):\n    return None\n",
              "start/follow_wrap.py": "import functools\n\n\ndef wrap(judge):\n"
                                      "    return functools.wraps(judge)(lambda output, inputs, evidence: None)\n",
              "first/top_of_order.py": "import shared_name\n\n\ndef work():\n    return shared_name\n",
              "one/shared_name.py": "VALUE = 1\n", "other/shared_name.py": "VALUE = 2\n",
              "later/shared_name.py": "VALUE = 3\n",
              "start/edited_start.py": "def work():\n    return 1\n", "start/edited_added.py": "VALUE = 1\n"}


def versioned(functions, root):
    """The files of `functions`' code version (_code.source_files), relative to `root`."""
    return {path.relative_to(root).as_posix() for path in _code.source_files(functions)}


WIRING = ("score/review/", "score/stages/people", "score/conductor/", "score/store/")


def test_the_code_version_is_every_repository_file_a_stages_functions_import_and_only_those():
    """Each set of functions, read through the real import walk (_code.source_files, _code.code_version), versions
    exactly the repository files it imports (a row: the files it must hold, the files and folders it must not).
    Toy modules of their own: a function importing inside its body a module from another path folder is followed
    there; a judge wrapped elsewhere (functools.wraps) is hashed from its own module too (the surface stage's guarded
    checks); the venv (numpy) never. A name two path folders hold is hashed from both, in either order (a row's key
    moved between two runs with no file changed, 2026-10-11); a folder put on the path after the first code version
    gives no stage another same-named module (stages_test's earlier tests gave effects-layer triage.py, 2026-10-13).
    The import walk is cached a process (#49), and an import added to a file is followed at the next read.
    The real table: scene_palette's `from score.stages.shapes_first import align` reads the loop's package, whose rows
    wire the whole prop route: none of it is in the palette's code version (2026-10-28: a likeness_row edit moved
    body-face). The palette's and surface-library's whole code versions (make, faults, judge, files) hold no review
    page, people row, conductor or store either: scene_library's file map read only the design folders' paths off
    review/plans and review/scene_sky, which put concepts, reading, plan_writing, people_bodies/bodies.py, the
    conductor and the store in its key (7f68af46, 6456c223, cd5d01c8 and d2f47c01..cac0d843 each re-asked the paid
    row, 2026-11-03).
    Break: score/graph/_code.py: 'for node in ast.walk(ast.parse(source, str(path))):' -> 'for node in ast.parse(source, str(path)).body:'
    Break: score/graph/_code.py: 'if known is None or known[0] != stamp or not all(module.is_file() for module in known[1]):' -> 'if known is None:'
    Break: score/graph/_code.py: '            if is_file(path)}' -> '            if is_file(path) and path == next(candidate for candidate, _ in repository_candidates(name, search_folders(), REPO, OUTSIDE) if is_file(candidate))}'
    Breaks: score/graph/_code.py: '"score/stages/shapes_first/__init__.py",' -> ''; score/stages/surfaces/
    scene_library.py plan_files: `prop_env.PROPS_HOME / "design" / "plans"` -> `plans.KEPT`, with `from score.review
    import plans` back inside the function."""
    toy = {"start/follow_start.py", "inner/follow_inner.py", "start/follow_wrap.py", "start/follow_judge.py",
           "first/top_of_order.py", "one/shared_name.py", "other/shared_name.py", "start/edited_start.py"}
    rows = []  # (name, versioned files, files it must hold, files it must not, folders it must not, only `holds`)
    with modules_of_its_own("_code_version_", CODE_FILES) as root:
        sys.path[:0] = [str(root / name) for name in ("start", "inner", "first")]
        import edited_start
        import follow_judge
        import follow_start
        import follow_wrap
        for order in (("one", "other"), ("other", "one")):
            sys.path[3:3] = [str(root / name) for name in order]
            _code.search_folders.cache_clear()
            sys.modules.pop("top_of_order", None)
            import top_of_order
            functions = [follow_start.work, follow_wrap.wrap(follow_judge.judge), top_of_order.work, edited_start.work]
            rows.append((f"toy, path {'-'.join(order)}", versioned(functions, root), toy, set(), (), True))
            del sys.path[3:5]
        sys.path[3:3] = [str(root / "one"), str(root / "other")]
        _code.search_folders.cache_clear()
        before = _code.code_version(functions, lambda path: "same")
        sys.path.insert(0, str(root / "later"))
        assert _code.code_version(functions, lambda path: "same") == before
        (root / "start/edited_start.py").write_text("import edited_added\n\n\ndef work():\n    return 1\n")
        after = _code.code_version(functions, lambda path: "same")
        assert [part for part in after if part not in before] == [
            f"{(root / 'start/edited_added.py').relative_to(REPO).as_posix()} same"], after
    from score.stages import surfaces
    from score.stages.surfaces import scene_palette
    _code.search_folders.cache_clear()  # the stage's folders on the path, as a run's table import puts them first
    rows.append(("scene_palette.files", versioned([scene_palette.files], _code.REPO),
                 {"score/stages/shapes_first/align.py"},  # what it calls stays in
                 {"score/stages/shapes_first/__init__.py", "score/stages/props/likeness_row.py",
                  "score/stages/props/thin_straight.py"}, (), False))
    rows += [(row.name, versioned(graph.code_functions(row), _code.REPO),
              {"score/stages/surfaces/scene_palette.py"}, set(), WIRING, False)  # what it reads stays in
             for row in surfaces.ROWS if row.name in ("finish-route-palette", "surface-library")]
    assert sorted(row[0] for row in rows[3:]) == ["finish-route-palette", "surface-library"], [row[0] for row in rows]
    for name, files, holds, refused, folders, only in rows:
        assert files == holds if only else holds <= files, (name, sorted(files ^ holds if only else holds - files))
        wrong = {path for path in files if path in refused or path.startswith(folders)}
        assert not wrong, (name, sorted(wrong))


# --- reads beside: other places' outputs, an environment's, up to a shell and down to child scenes -----------------

def make_show(inputs, out, seed, params):
    """Its own clean text, and every other place's read beside, in order."""
    others = sorted(name for name in inputs if name.startswith("clean@"))
    own = ["clean"] if "clean" in inputs else []
    (out / "show.txt").write_text(" ".join((inputs[name] / "clean.txt").read_text() for name in [*own, *others]))


SHOW = graph.Stage("show", "place", make_show, TEXT, PASSES, after={"clean": READS}, beside={"clean": READS},
                   neighbours=lambda place: [other for other in PLACES if other != place])


def make_outlined(inputs, out, seed, params):
    """Its own clean text, after its shell's split where it has one."""
    shells = [(inputs[name] / "split.txt").read_text() for name in sorted(inputs) if name.startswith("split@")]
    (out / "outlined.txt").write_text(" ".join([*shells, (inputs["clean"] / "clean.txt").read_text()]))


def make_split(inputs, out, seed, params):
    (out / "split.txt").write_text("SPLIT " + (inputs["outlined"] / "outlined.txt").read_text())


def make_tree(inputs, out, seed, params):
    """Its own clean text, then each child scene's tree in brackets."""
    held = [(inputs[name] / "tree.txt").read_text() for name in sorted(inputs) if name.startswith("tree@")]
    (out / "tree.txt").write_text((inputs["clean"] / "clean.txt").read_text() + "".join(f"[{tree}]" for tree in held))


OUTLINED = graph.Stage("outlined", "place", make_outlined, TEXT, PASSES, after={"clean": READS},
                       beside={"split": READS}, upward=True,
                       neighbours=lambda place: ["station"] if place == "hangar" else [])
SPLIT = graph.Stage("split", "place", make_split, TEXT, PASSES, after={"outlined": READS})
HOLDS = {"base": ["hangar"], "hangar": ["station"]}
TREE = graph.Stage("tree", "place", make_tree, TEXT, PASSES, after={"clean": READS}, beside={"tree": READS},
                   downward=True, neighbours=lambda place: HOLDS.get(place, []))
HANGAR_ONLY = dataclasses.replace(COUNT, name="hangar only", applies=lambda place: place == "hangar")
WHOLE = graph.Stage("whole", "world", make_show, TEXT, PASSES, beside={"clean": READS, "hangar only": READS},
                    neighbours=lambda place: list(PLACES))
TWO_PLACES = {"hangar": "a ship in a hall", "station": "a hub"}


@dataclasses.dataclass(frozen=True)
class Beside:
    """A table whose node reads other places beside: the scenes made and accepted first, the places driven, the node
    and its file, what it reads earlier and beside, its accepted text worked out by hand from the briefs; tables of
    the same stages that are refused as a cycle and that stand; the line the drive lists, and the status once the
    station's brief is rewritten otherwise (None: not asked of this row)."""
    briefs: dict
    stages: tuple
    drive: tuple
    whole: bool
    stage: graph.Stage
    place: str
    file: str
    earlier: list
    beside: tuple
    text: str
    refused: tuple = ()
    stands: tuple = ()
    line: list = None
    stale: str = None


READ_BESIDE = {
    # Fault (2026-10-12): a place's references to the places it shows pointed at old seed files.
    "a place shows the others": Beside(
        TWO_PLACES, (CLEAN, COUNT, SHOW), ("hangar",), False, SHOW, "hangar", "show.txt",
        ["clean@hangar", "clean@station"], ("clean@station",), "A SHIP IN A HALL A HUB",
        refused=((CLEAN, dataclasses.replace(SHOW, name="loop", beside={"loop": READS})),),
        stands=((CLEAN, COUNT, SHOW, dataclasses.replace(SHOW, name="show again", after={"show": READS},
                                                         beside={"show": READS})),),
        line=["clean@hangar", "clean@station", "count@hangar", "show@hangar"],
        stale="to run: clean@station changed, its accepted output is stale: clean@station moved"),
    # #28: the environment's film reads every place film its script shows, a row only where it applies.
    "the film reads each place where its row applies": Beside(
        TWO_PLACES, (CLEAN, COUNT, HANGAR_ONLY, WHOLE), PLACES, True, WHOLE, None, "show.txt",
        ["clean@hangar", "hangar only@hangar", "clean@station"],
        ("clean@hangar", "hangar only@hangar", "clean@station"), "A SHIP IN A HALL A HUB"),
    # Shapes first (CONTEXT.md): an inside place reads its outside shell's split, which reads the shell's own node.
    "an inside place reads its shell one scale up": Beside(
        TWO_PLACES, (CLEAN, COUNT, OUTLINED, SPLIT), ("hangar",), False, OUTLINED, "hangar", "outlined.txt",
        ["clean@hangar", "split@station"], ("split@station",), "SPLIT A HUB A SHIP IN A HALL",
        refused=((CLEAN, COUNT, dataclasses.replace(OUTLINED, upward=False), SPLIT),)),
    # A parent scene's tree reads each child scene's tree, the grandchild's made first.
    "a parent scene reads its children one scale down": Beside(
        {"base": "a moon base", **TWO_PLACES}, (CLEAN, COUNT, TREE), ("base",), False, TREE, "base", "tree.txt",
        ["clean@base", "tree@hangar"], ("tree@hangar",), "A MOON BASE[A SHIP IN A HALL[A HUB]]",
        refused=((CLEAN, COUNT, dataclasses.replace(TREE, downward=False)),)),
}


def accepted_scenes(briefs):
    """Every scene made, given a limit of 10 words and accepted; the world and store."""
    world, store = a_world(briefs), a_store()
    runner = a_runner(world, store)
    runner.run(list(briefs))
    for place in briefs:
        give_evidence(store, runner, place, 10)
    runner.run(list(briefs))
    return world, store


@pytest.mark.parametrize("row", READ_BESIDE.values(), ids=READ_BESIDE.keys())
def test_a_node_reads_other_places_beside_versioned_waited_on_and_only_where_declared(row):
    """A node reading other places beside waits on their accepted outputs, keys on them and makes from them: a place
    showing the others, the environment's film reading each place film only where its row applies, an inside place
    reading its shell's split (a loop in the table, none in the nodes) and a parent scene its children's trees. The
    shown station's brief rewritten the same keeps the show's key, otherwise stales it. A stage reading itself beside,
    or a loop through beside not declared upward or downward, is refused as a cycle; a chain read beside with no loop
    stands.
    Break: score/graph/__init__.py: '        if beside:  # only a stage that reads beside' -> '        if False:  # only a stage that reads beside'
    Break: score/graph/__init__.py: 'if place is not None or self.stages[before].applies is None or self.stages[before].applies(other)}' -> '}'
    Break: score/graph/__init__.py: '        return [*stage.after, *(() if stage.upward or stage.downward else stage.beside)]' -> '        return [*stage.after]'"""
    world, store = accepted_scenes(row.briefs)
    runner = a_runner(world, store, row.stages)
    node = graph.node_name(row.stage, row.place)
    assert runner.earlier(row.stage, row.place) == row.earlier
    if row.line is not None:
        assert [graph.node_name(*each) for each in runner.line_nodes(list(row.drive), whole=False)] == row.line
    found = runner.drive(list(row.drive), say=quiet, jobs=1, whole=row.whole)
    assert found[node] == "made: pass, accepted automatically", found
    assert accepted_text(store, node, row.file) == row.text
    assert runner.key(row.stage, row.place)["beside"] == {name: store.accepted(name) for name in row.beside}
    if row.stale is not None:
        brief(world, "station", row.briefs["station"])
        assert runner.status([row.place])[node] == "pass, accepted"
        brief(world, "station", "a ring")
        runner.run(["station"])
        give_evidence(store, runner, "station", 10)
        runner.run(["station"])
        assert runner.status([row.place])[node] == row.stale
    for stages in row.refused:
        with pytest.raises(ValueError, match="cycle"):
            a_runner(world, store, stages)
    for stages in row.stands:
        a_runner(world, store, stages)


GATHER = graph.Stage("gather", "world", make_show, TEXT, PASSES, beside={"clean": READS},
                     neighbours=lambda place: ["hangar"])


def test_a_run_holds_the_nodes_it_names_and_what_they_read_place_by_place(monkeypatch):
    """#26: `--place people --stage <body>` keeps an environment row named with the place, where before it was left
    out; an environment stage not named stays out; one node named by itself is a run of its own. `--phase` (#21) is
    --stage with every stage of that phase, never the whole environment, and an unknown phase is refused; several
    phases, repeated or as a comma list, are all kept, not only the last.
    Break: score/graph/__init__.py: '                                      if stage.grain == "place" or node_name(stage, place) in named]' -> '                                      if stage.grain == "place"]'
    Break: score/__main__.py: '        stages_held = phases.stages_of(phase, list(table))' -> '        stages_held = []'
    Break: score/__main__.py: '        command.add_argument("--phase", action="extend", type=phase_list,' -> '        command.add_argument("--phase", type=lambda given: phase_list(given)[-1:],'"""
    world, store, _ = ready_world()
    runner = a_runner(world, store, (CLEAN, COUNT, GATHER))
    names = {graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False, only=["gather"])}
    assert names == {"clean@hangar", "gather"}, names
    names = {graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False, only=["count"])}
    assert names == {"clean@hangar", "count@hangar"}, names
    names = {graph.node_name(*node) for node in runner.line_nodes(list(PLACES), whole=False, only=["count@station"])}
    assert names == {"clean@station", "count@station"}, names
    from score import __main__ as command
    from score.stages import phases
    monkeypatch.setattr(phases, "PHASES", (("early", ("clean",)), ("late", ("count", "gather"))))
    monkeypatch.setattr(phases, "NAMES", ("early", "late"))
    late = command.phase_stages(argparse.Namespace(phase="late", stage=None), runner.stages)
    assert late == ["count", "gather"], late
    names = {graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False, only=late)}
    assert names == {"clean@hangar", "count@hangar", "gather"}, names
    assert command.phase_stages(argparse.Namespace(phase=None, stage=["count"]), runner.stages) == ["count"]
    both = command.phase_stages(command.parse(["plan", "world1", "--phase", "late,early"]), runner.stages)
    assert both == ["clean", "count", "gather"], both
    assert command.parse(["plan", "world1", "--phase", "early", "--phase", "late"]).phase == ["early", "late"]
    with pytest.raises(SystemExit, match="holds no stage"):
        command.phase_stages(argparse.Namespace(phase="early", stage=None), {"count": COUNT})
    printed = io.StringIO()
    with contextlib.redirect_stderr(printed), pytest.raises(SystemExit):
        command.parse(["run", "world1", "--phase", "lighting"])
    assert "invalid choice: 'lighting'" in printed.getvalue(), printed.getvalue()


# --- an accepted output kept under a moved key: bytecode alone, a no-op proof, a narrower key, words only ----------

def judge_seen(output, inputs, evidence):
    return checks.Verdict("seen", checks.PASS, "it was made")


def make_seen(inputs, out, seed, params):
    (out / "seen.txt").write_text("seen")


SEEN = (checks.Check("seen", judge_seen),)
SOURCES = graph.Stage("seen", "place", make_seen, TEXT, SEEN, files={"code": "{repo}/score/checks"})
NOTED = graph.Stage("noted", "place", make_seen, TEXT, SEEN, files={"notes": "{repo}/CLAUDE.md"})


def git_out(*command):
    return subprocess.run(["git", "-C", str(_code.REPO), *command], capture_output=True, text=True,
                          check=True).stdout.split()


def as_it_read_then(path):
    return "the file as it read then"


@dataclasses.dataclass(frozen=True)
class Proved:
    """An output made at a commit (HEAD, or the root commit at this index of `git rev-list --max-parents=0 HEAD`) by
    a runner hashing its sources as given, then keyed again today; the no-op proof put beside it (None: none); whether
    it is kept, and if so for what reason."""
    stage: graph.Stage
    source_hash: object
    root: object  # None: HEAD; else the index into the root commits
    no_ops: dict
    reason: str


PROVED = {
    # #67: seen@hangar made by a runner that still hashed score/checks' __pycache__.
    "bytecode moved, sources as now": Proved(SOURCES, tree_hash, None, None, graph.BYTECODE_REASON),
    "bytecode moved, no score/checks at that commit": Proved(SOURCES, tree_hash, -1, None, None),
    # noted@hangar made at the first commit (the root rev-list lists first), when CLAUDE.md read otherwise.
    "a changed file, no proof": Proved(NOTED, as_it_read_then, 0, None, None),
    "a proof leaving the changed file out": Proved(NOTED, as_it_read_then, 0, {"README.md": "not read"}, None),
    "a proof naming every changed file": Proved(NOTED, as_it_read_then, 0,
                                                {"CLAUDE.md": "only its wording changed"}, graph.NO_OP_REASON),
}


@pytest.mark.parametrize("row", PROVED.values(), ids=PROVED.keys())
def test_an_output_is_kept_over_a_moved_key_only_when_proved_and_its_record_names_the_proof(row, monkeypatch):
    """An accepted output whose key moved is kept, the proof in its record, only when the move is bytecode alone with
    its sources as at its commit, or a no-op proof names every changed file; otherwise it is made again.
    Break: score/graph/__init__.py: '        proved = self.bytecode_proof(stage, place, keyed)\n        if proved is None:' -> '        proved = None\n        if proved is None:'
    Break: score/graph/__init__.py: 'if any(not str(proof.get("no-ops", {}).get(name, "")).strip() for name in changed):' -> 'if False:'"""
    cache = _code.REPO / "score/checks/__pycache__"
    if not any(cache.glob("*.pyc")):
        import py_compile
        py_compile.compile(str(_code.REPO / "score/checks/__init__.py"))
    world = graph.Environment("toy", 7, {"data": str(tempfile.mkdtemp()), "repo": str(_code.REPO)})
    commit = git_out("rev-parse", "HEAD")[-1] if row.root is None else git_out(
        "rev-list", "--max-parents=0", "HEAD")[row.root]
    node = graph.node_name(row.stage, "hangar")
    store = a_store()
    with monkeypatch.context() as patched:
        patched.setattr(graph, "source_hash", row.source_hash)
        patched.setattr(_code, "git_commit", lambda: {"commit": commit, "uncommitted": False})
        assert a_runner(world, store, (row.stage,)).run(["hangar"])[node].endswith("accepted automatically")
    runner = a_runner(world, store, (row.stage,))
    keyed = runner.key(row.stage, "hangar")
    old = store.records(node)[0]
    assert store.record(node, keyed["key"]) is None  # its key moved
    if row.no_ops is not None:
        proof = pathlib.Path(tempfile.mkdtemp()) / "proof.json"
        proof.write_text(json.dumps({"from key": old["key"], "to key": keyed["key"], "no-ops": row.no_ops}))
        store.put_evidence(f"no-op-{keyed['key']}", old["output"], proof)
    done = runner.run(["hangar"])[node]
    assert done == ("fresh" if row.reason else "made: pass"), done
    if row.reason:
        carried = store.record(node, keyed["key"])["carried"]
        assert carried["reason"] == row.reason and carried["made by"]["commit"] == commit
        if row.reason == graph.BYTECODE_REASON:
            assert carried["sources"]["code"]["at its commit"] == keyed["files"]["code"]
        else:
            assert carried["no-ops"] == row.no_ops and carried["from key"] == old["key"]


STAGE_SOURCE = """import {helper}
import {other}


def make(inputs, out, seed, params):
    (out / "made.txt").write_text({helper}.WORD + {other}.WORD + inputs["seeds"].read_text())
"""
OTHER_SOURCE = """def make(inputs, out, seed, params):
    (out / "made.txt").write_text("TOTALLY DIFFERENT " + inputs["seeds"].read_text())
"""
GATE_SOURCE = """from score import checks


def judge(output, inputs, evidence):
    rusted = (inputs["seeds"].parent / "rusted").exists()  # read by no key: what a gate may see change under a lock
    return checks.Verdict("seen", checks.FAIL if rusted else checks.PASS, "rusted" if rusted else "it was made")
"""


def stage_source(case):
    return STAGE_SOURCE.format(helper=f"narrow_h{case}", other=f"narrow_g{case}")


@contextlib.contextmanager
def a_repo_of_its_own(case):
    """A committed git repository taken as the repository while the block runs: `narrow_a<case>` imports
    `narrow_h<case>` (which imports `narrow_j<case>`) and `narrow_g<case>`; `narrow_b<case>` has a make of its own,
    `narrow_k<case>` a gate; a FRAMEWORK of none. Yields (its folder, the stage module)."""
    repo = pathlib.Path(tempfile.mkdtemp(prefix="narrow_repo_")).resolve()
    (repo / f"narrow_h{case}.py").write_text(f'import narrow_j{case}\nWORD = "kept " + narrow_j{case}.WORD\n')
    (repo / f"narrow_j{case}.py").write_text('WORD = "joined "\n')
    (repo / f"narrow_g{case}.py").write_text('WORD = "also "\n')
    (repo / f"narrow_a{case}.py").write_text(stage_source(case))
    (repo / f"narrow_b{case}.py").write_text(OTHER_SOURCE)
    (repo / f"narrow_k{case}.py").write_text(GATE_SOURCE)
    (repo / "score" / "graph").mkdir(parents=True)
    (repo / "score" / "graph" / "_code.py").write_text("FRAMEWORK = {REPO / name for name in ()}\n")
    (repo / ".gitignore").write_text("__pycache__/\n")
    for command in (["init", "-q"], ["add", "."], ["-c", "user.name=test", "-c", "user.email=test@test", "commit",
                                                   "-qm", "a stage and its helper"]):
        subprocess.run(["git", "-C", str(repo), *command], check=True)
    saved = _code.REPO, _code.OUTSIDE, _code.FRAMEWORK, _code.search_folders
    _code.REPO, _code.OUTSIDE, _code.FRAMEWORK = repo, (repo / ".git",), set(_code.FRAMEWORK)
    _code.search_folders = lambda: (repo,)
    sys.path.insert(0, str(repo))
    try:
        yield repo, importlib.import_module(f"narrow_a{case}")
    finally:
        sys.path.remove(str(repo))
        _code.REPO, _code.OUTSIDE, _code.FRAMEWORK, _code.search_folders = saved


def test_an_output_whose_key_only_got_narrower_or_reworded_is_kept_and_a_changed_read_is_made_again():
    """A stage A importing helper H, made and accepted: H moved into FRAMEWORK moves A's key and the runner keeps A's
    output, no proof file and no make (rebuy counts no buy); A's own file edited, its {seeds} file changed, its make
    wired to another function (B), another Python, H edited, a file read only through H (J) edited or deleted make A
    again. A second narrowing (G moved too) is kept as well, still naming what made it. Nothing moved, A and G
    reworded only (comments, blank lines, layout, docstrings) keep it, the record naming them; a docstring changed in
    a file that reads `__doc__`, or a type hint, makes A again. A's phase locked (Runner.lock_phase): its own file
    edited keeps it, the record "kept by the phase lock of <time>", status naming the lock and A kept by it; its
    {seeds} file changed (an input) makes A again; unlocked, its own file edited makes A again (case 1). Locked, a
    code file of the repository declared as A's since keeps it, a data file so declared makes it again (2026-11-11:
    70c87a4a declared props/railing_hold.py for pixal and likeness, made again at 18 locked places). Locked, with
    its gate in a file of its own (K): its own file edited while that unchanged gate would fail it today keeps it (a
    gate not changed since the lock is not judged again: checkout 47, 2026-11-07, pixal and closeup bought again);
    K edited so the gate fails the locked output, or cannot tell (unknown), makes A again (2026-11-07, 796d7a76's paint
    gate, hub's console: unknown on the paint made before it). Locked, then dropped from its phase (drop_from_phase):
    its own file edited makes A again (2026-11-08: campgrounds' tower held by an old lock); dropped only after its lock
    carried it onto a moved key, its key moves on and A is made again, then stays on that key (2026-11-11:
    earth-seed@docking_airlock kept its ochre deck after its drop). `score plan`'s to_run
    (buy_check) lists A exactly when the runner makes it, never when it keeps it (2026-11-10: 559 shown, about 8 made).
    A's code version rebuilt at a commit a second time resolves no path again (2026-11-11: resolving was 104 of a
    camp plan's 370 s, rebuilt at every commit a record was made at); a pass that writes nothing reads each phase lock
    once (2026-11-11: a plan read and parsed all 685 of them again for every key).
    Break: score/graph/_code.py: '@functools.cache\ndef relative_in(' -> 'def relative_in('
    Break: score/graph/__init__.py: 'return list(self.remember("phase locks", self.world.name, self.read_phase_locks))' -> 'return self.read_phase_locks()'
    Break: score/graph/__init__.py: '        if any(node in lock.get("dropped", ()) and lock["at"] >= locks[-1]["at"] for lock in every):' -> '        if False:'
    Break: score/graph/__init__.py: '        if not drops:' -> '        if True:'
    Break: score/graph/__init__.py: '        return (record, reworded) if _code.unchanged(dropped, file_hash) else None' -> '        return (record, reworded)'
    Break: score/graph/__init__.py: '        if not all(self.code_file(stage, name, place) for name in keyed["files"]' -> '        if False and not all(self.code_file(stage, name, place) for name in keyed["files"]'
    Break: score/graph/__init__.py: 'not set(record["files"]) <= set(keyed["files"]):' -> 'set(record["files"]) != set(keyed["files"]):'
    Break: score/graph/__init__.py: 'if record["files"].get(name) != keyed["files"][name]):' -> 'if name in record["files"] and record["files"][name] != keyed["files"][name]):'
    Break: score/graph/__init__.py: '        if self.gates_moved(stage, locks[-1]) and self.fails_today(stage, place, record):' -> '        if self.fails_today(stage, place, record):'
    Break: score/graph/__init__.py: '        if self.gates_moved(stage, locks[-1]) and self.fails_today(stage, place, record):' -> '        if False:'
    Break: score/graph/__init__.py: 'if checks.blocks(verdict["answer"]) and name not in waived]' -> 'if verdict["answer"] == checks.FAIL and name not in waived]'
    Break: score/__main__.py: 'if state.startswith("to run") and node not in kept}' -> 'if state.startswith("to run")}'
    Break: score/graph/rebuy.py: '                    kept.add(node)' -> '                    pass'"""
    from score import __main__ as command
    for case, change, kept in ((0, None, True), (1, "own file", False), (2, "seeds", False),
                               (3, "make swapped", False), (4, "python", False), (5, "helper edited", False),
                               (6, "read through helper edited", False), (7, "second narrowing", True),
                               (8, "read through helper deleted", False), (9, "words only", True),
                               (10, "read docstring changed", False), (11, "type hint", False),
                               (12, "own file, phase locked", True), (13, "seeds, phase locked", False),
                               (14, "own file, gate fails, phase locked", True),
                               (15, "gate edited, phase locked", False),
                               (16, "gate edited to unknown, phase locked", False),
                               (17, "own file, dropped, phase locked", False),
                               (18, "code file declared, phase locked", True),
                               (19, "data file declared, phase locked", False)):
        seeds = pathlib.Path(tempfile.mkdtemp())
        (seeds / "hangar.txt").write_text("a seed")
        world = graph.Environment("toy", 7, {"seeds": str(seeds)})
        store = a_store()
        with a_repo_of_its_own(case) as (repo, module):
            gate = (checks.Check("seen", importlib.import_module(f"narrow_k{case}").judge),) if case >= 14 else SEEN
            stage = graph.Stage("narrow", "place", module.make, TEXT, gate, files={"seeds": "{seeds}/{place}.txt"})
            if change == "read docstring changed":
                (repo / f"narrow_g{case}.py").write_text('"""also """\nWORD = __doc__\n')
                subprocess.run(["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@test", "commit",
                                "-qam", "a usage text"], check=True)
            first = a_runner(world, store, (stage,)).run(["hangar"])["narrow@hangar"]
            assert first == "made: pass, accepted automatically", first
            old = store.records("narrow@hangar")[0]
            lock = None
            if (change or "").endswith(", phase locked"):
                lock = a_runner(world, store, (stage,)).lock_phase("props", [(stage, "hangar")])
                assert lock["nodes"] == {"narrow@hangar": {"output": old["output"], "key": old["key"],
                                                           "commit": old["commit"]}} and lock["n"] == 1, lock
                reads, read = [], store.read  # a pass that writes nothing reads the locks once, not once a node
                store.read = lambda key: reads.append(key) or read(key)
                try:
                    with (locking := a_runner(world, store, (stage,))).still():
                        assert locking.phase_locks() == locking.phase_locks() == [lock], lock
                finally:
                    del store.read
                assert [key for key in reads if key.startswith(graph.PHASE_LOCKS)] == ["phase-locks/toy/props/1.json"], \
                    reads
                change = change.removesuffix(", phase locked")
            if change == "own file, dropped":  # taken out of its phase's locks since: a code change makes it again
                dropped = a_runner(world, store, (stage,)).drop_from_phase("props", ["narrow"])  # by its stage
                assert dropped["dropped"] == ["narrow", "narrow@hangar"] and dropped["nodes"] == {} and \
                    dropped["n"] == 2, dropped
                change = "own file"
            if change in ("code file declared", "data file declared"):  # a file of its own since: code or data
                held = repo / ("data/hold.txt" if change == "data file declared" else f"narrow_g{case}.py")
                held.parent.mkdir(exist_ok=True)
                held.exists() or held.write_text("held\n")
                stage = dataclasses.replace(stage, files={**stage.files, "hold": str(held)})
            if change == "own file, gate fails":  # the gate's code as at the lock, failing the locked output today
                (seeds / "rusted").write_text("rust")
                change = "own file"
            if change not in ("words only", "read docstring changed", "type hint"):
                _code.FRAMEWORK.add(repo / f"narrow_h{case}.py")
            edits = {"own file": (f"narrow_a{case}.py", stage_source(case) + "EXTRA = 1\n"),
                     "words only": (f"narrow_a{case}.py", '"""A stage."""\n\n# made here\n' + stage_source(
                         case).replace("    (out", '    """It makes made.txt."""\n    (out')),
                     "read docstring changed": (f"narrow_g{case}.py", '"""other """\nWORD = __doc__\n'),
                     "type hint": (f"narrow_g{case}.py", 'WORD: str = "also "\n'),
                     "helper edited": (f"narrow_h{case}.py", 'WORD = "another word "\n'),
                     "gate edited": (f"narrow_k{case}.py", GATE_SOURCE.replace("checks.FAIL if rusted", "checks.FAIL if True")),
                     "gate edited to unknown": (f"narrow_k{case}.py", GATE_SOURCE.replace(
                         "checks.FAIL if rusted", "checks.UNKNOWN if True")),
                     "read through helper edited": (f"narrow_j{case}.py", 'WORD = "another word "\n')}
            if change in edits:
                (repo / edits[change][0]).write_text(edits[change][1])
            if change == "words only":
                (repo / f"narrow_g{case}.py").write_text('WORD = (\n    "also "  # a word\n)\n')
            if change == "read through helper deleted":
                (repo / f"narrow_j{case}.py").unlink()
            if change == "seeds":
                (seeds / "hangar.txt").write_text("another seed")
            if change == "make swapped":
                stage = dataclasses.replace(stage, make=importlib.import_module(f"narrow_b{case}").make)
            if (change or "").startswith("gate edited"):  # the judge as its file reads now
                stage = dataclasses.replace(stage, checks=(checks.Check("seen", importlib.reload(
                    importlib.import_module(f"narrow_k{case}")).judge),))
            python = _code.sys
            if change == "python":
                _code.sys = types.SimpleNamespace(version_info=types.SimpleNamespace(major=3, minor=99), path=sys.path)
            try:
                runner = a_runner(world, store, (stage,))
                keyed = runner.key(stage, "hangar")
                assert keyed["key"] != old["key"] and store.record("narrow@hangar", keyed["key"]) is None
                assert (rebuy.to_make(runner, stage, "hangar", [], {}) is rebuy.KEPT) == kept, change
                if case == 0:  # rebuilt again at that commit, no path is resolved again (a camp plan: 104 of 370 s)
                    starts = tuple(_code.start_files(graph.code_functions(stage)))
                    then, resolved, resolve = _code.rebuilt_at(old["commit"], starts), [], pathlib.Path.resolve
                    pathlib.Path.resolve = lambda path, *given, **named: resolved.append(path) or resolve(
                        path, *given, **named)
                    try:
                        again = _code.rebuilt_at(old["commit"], starts)
                    finally:
                        pathlib.Path.resolve = resolve
                    assert then and again == then and not resolved, resolved
                planned = command.buy_check(runner, ["hangar"], True, None, None)  # `score plan`'s to_run: the same
                assert ("narrow@hangar" in planned["to_run"]) != kept, (change, planned["to_run"])  # rows the drive makes
                done = runner.run(["hangar"])["narrow@hangar"]
            finally:
                _code.sys = python
            assert done.startswith("fresh" if kept else "made: fail" if change == "gate edited" else "made: unknown"
                                   if change == "gate edited to unknown" else "made: pass"), (change, done)
            record = store.record("narrow@hangar", keyed["key"])
            made_by = {"commit": old["commit"], "code": old["code"]}
            if lock:
                assert runner.phase_lock_lines()[0].endswith(
                    f"1 nodes locked, {int(kept)} kept by it" + (": narrow@hangar" if kept else "")), change
            if lock and kept:
                assert record["output"] == old["output"] and record["carried"] == {
                    "reason": graph.PHASE_REASON.format(at=lock["at"]), "phase": "props", "lock": 1,
                    "from key": old["key"], "to key": keyed["key"], "made by": made_by}
                if case == 12:  # dropped after that carry: its key moves on and it is made (dropped_parts)
                    a_runner(world, store, (stage,)).drop_from_phase("props", ["narrow@hangar"])
                    runner = a_runner(world, store, (stage,))
                    moved = runner.key(stage, "hangar")
                    assert moved["key"] != keyed["key"] and moved["dropped"]["after"] == keyed["key"], moved
                    assert runner.node_status(stage, "hangar").endswith(", dropped from its phase by props lock 2")
                    assert runner.run(["hangar"])["narrow@hangar"].startswith("made: pass")
                    assert "carried" not in store.record("narrow@hangar", moved["key"])
                    assert a_runner(world, store, (stage,)).key(stage, "hangar")["key"] == moved["key"]
            elif change == "words only":
                assert record["output"] == old["output"] and record["carried"] == {
                    "reason": graph.WORDS_REASON, "from key": old["key"], "to key": keyed["key"], "made by": made_by,
                    "words only": [f"narrow_a{case}.py", f"narrow_g{case}.py"]}
            elif kept:
                assert record["output"] == old["output"] and record["code"] == keyed["code"]
                assert record["carried"] == {"reason": graph.NARROWING_REASON, "from key": old["key"],
                                             "to key": keyed["key"], "made by": made_by}
                assert store.judgement("narrow@hangar", keyed["key"], runner.evidence_state(stage, old["output"]))
                if change == "second narrowing":
                    _code.FRAMEWORK.add(repo / f"narrow_g{case}.py")
                    runner = a_runner(world, store, (stage,))
                    again = runner.key(stage, "hangar")
                    assert again["key"] != keyed["key"] and runner.run(["hangar"])["narrow@hangar"].startswith("fresh")
                    assert store.record("narrow@hangar", again["key"])["carried"] == {
                        "reason": graph.NARROWING_REASON, "from key": keyed["key"], "to key": again["key"],
                        "made by": made_by}
            else:
                assert "carried" not in record


STRICT = {"on": False, "old schema": False}  # the toy gate's code before (off) and after (on) it saw a fault


def judge_marks(output, inputs, evidence):
    if STRICT["old schema"] and (output / "clean.txt").read_text().startswith("A "):
        raise KeyError("layers")  # today's gate reading a field the old output never wrote
    marks = (output / "clean.txt").read_text().split().count("X") if STRICT["on"] else 0
    return checks.Verdict("marks", checks.PASS, f"{marks} marks", {"marks": marks}, {"marks": "lower"})


MARKS = graph.Stage("clean", "place", make_clean, TEXT, (checks.Check("marks", judge_marks),),
                    files={"brief": "{data}/{place}/brief.txt"})


def test_the_accepted_output_is_judged_again_by_todays_gates_before_comparing():
    """assembly@lab, 2026-10-15: its accepted output was judged before the triage asked each foot, so the chairs'
    caster read as two new faults. "a x" accepted with 0 marks seen; today's gate sees its 1 mark, so "b x" (1 mark)
    is no worse and accepted, "c x x" (2) is worse and waits. A gate that cannot judge the accepted output again
    compares its stored verdict (0 marks against 1: worse, waits).
    Break: score/graph/__init__.py: 'against = self.rejudged_accepted(stage, place) if judged' -> 'against = None if judged'"""
    world, store = a_world({"hangar": "a x"}), a_store()
    try:
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == "made: pass, accepted automatically"
        STRICT["on"] = True
        brief(world, "hangar", "b x")
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == (
            "made: pass, accepted automatically")
        accepted = store.accepted("clean@hangar")
        brief(world, "hangar", "c x x")
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == "made: pass"
        assert store.accepted("clean@hangar") == accepted
        world, store = a_world({"hangar": "a x"}), a_store()
        STRICT.update({"on": False})
        a_runner(world, store, (MARKS,)).run(["hangar"])
        STRICT.update({"on": True, "old schema": True})
        brief(world, "hangar", "b x")
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == "made: pass"
    finally:
        STRICT.update({"on": False, "old schema": False})


# --- the drive: every line to its end, no agent in the loop; a node that does not stand stops only what reads it ----
# Fault (owner, 2026-10-11): agents walked every job through its steps by hand, polling each cloud step.

def gather_limit(output, inputs, folder):
    """A word limit of 5, written down for the test (each node runs in a process of its own)."""
    with (inputs["brief"].parents[1] / "gathered.txt").open("a") as gathered:
        gathered.write(f"{output.name} {os.environ.get(compute.TICKET)}\n")
    path = folder / "limit.json"
    path.write_text(json.dumps({"limit": 5}))
    return path


def a_driven_runner(briefs, euros=None, more=()):
    """clean (gated on a gathered limit of 5 words and on shouting) and count, with `more` stages after them."""
    clean = graph.Stage("clean", "place", make_clean, TEXT, (WORDS, checks.Check("shout", judge_shout)),
                        files={"brief": "{data}/{place}/brief.txt"}, gatherers={"words": (gather_limit, euros)})
    return a_runner(a_world(briefs), a_store(), (clean, COUNT, *more))


def gathered(runner):
    """Each gather's (output, spend ticket), as the nodes' processes wrote them."""
    path = runner.world.roots["data"] / "gathered.txt"
    return [tuple(line.split(" ", 1)) for line in path.read_text().splitlines()] if path.exists() else []


def report_of(runner, node):
    return runner.store.cache.parent / "faults" / f"{node}.txt"


ACCEPTED = "made: pass, accepted automatically"


def make_echo(inputs, out, seed, params):
    (out / "echo.txt").write_text(inputs["brief"].read_text())


def make_failing(inputs, out, seed, params):
    raise RuntimeError("names failed")


# Each place's brief, chosen for the one way its line ends in the drive below.
DRIVEN = {"dock": "a ship",                           # passes: its line runs to its end, gathering a paid limit
          "station": "a hub",                         # passes, then its brief moves under the run
          "hangar": "a ship in a very long dark hall",  # 8 words against the gathered 5: its gate fails, then put right
          "loud": "a ship!",                          # shouts: another gate fails, so nothing is gathered
          "boom": "explode", "halt": "quit", "bare": None,  # an error, an exit, a missing input
          "pier": "a pier"}                           # its names node fails, read by nothing
ERRED = {"boom": ("error: RuntimeError: the cleaner fell over", True),
         "halt": ("error: SystemExit: the cleaner quit: no such material", True),
         "bare": ("blocked: clean@bare: its input brief is missing", False)}  # (said, traceback in its report)


def test_a_drive_runs_every_line_to_its_end_and_a_node_that_does_not_stand_stops_only_its_readers(monkeypatch):
    """One drive of eight places under clean (a gathered word limit and no shouting), count, echo (reads only the
    brief), tally (reads clean and echo) and names (pier only, always fails); then hangar is put right, station's brief
    moves, and a second drive runs. A world whose limit is paid gathers it inside the runner's clearance.
    sound@square, 2026-10-20: one failed sound stopped every later row of the square's line, though none read it.
    Batch 1 try 4, 2026-10-25: twenty lines stopped on "has not run on its current inputs", nothing said why.
    surfaces-lists@lab, 2026-10-12: a SystemExit in a make ended its process with exit code 1 and nothing said; an
    error's line is its cause and its report, the traceback in its node's log, never one raised outside the log.
    2026-10-27: the folders of makes that failed stayed in store/cache/making and helped fill the conductor's disk.
    Break: score/graph/__init__.py: '                wanted = [] if did.startswith(("blocked", "broken", PAID_LEFT)) else self.gatherable(stage, place, self.ran)' -> '                wanted = []'
    Break: score/graph/__init__.py: '        if report.exists():\n            report.unlink()\n        return did, True' -> '        return did, True'
    Break: score/graph/__init__.py: '        if not cause.endswith(NOT_RUN):' -> '        if True:'
    Break: score/graph/__init__.py: '        return sorted(blocking) if blocking and blocking <= missing else []' -> '        return sorted(missing)'
    Break: score/graph/__init__.py: '            except (Exception, SystemExit) as error:  # noqa: BLE001 - a SystemExit too' -> '            except Exception as error:  # noqa: BLE001 - a SystemExit too'
    Break: score/graph/__init__.py: '        finally:\n            gone(out)' -> '        finally:\n            pass'
    Break: score/graph/__init__.py: '                    waits = [stopped[before] for before in earlier if before in stopped and before not in passes]' -> '                    waits = list(stopped.values())'
    Break: score/graph/__init__.py: '        with self.cleared(node_name(stage, place), euros) if euros else contextlib.nullcontext():' -> '        with contextlib.nullcontext():'"""
    monkeypatch.setattr(compute.ledger(), "entries", lambda: [])
    echo = graph.Stage("echo", "place", make_echo, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"})
    tally = graph.Stage("tally", "place", make_count, TEXT, PASSES, after={"clean": READS, "echo": READS})
    names = graph.Stage("names", "place", make_failing, TEXT, PASSES, applies=lambda place: place == "pier")
    runner = a_driven_runner(DRIVEN, more=(echo, tally, names))
    places = list(DRIVEN)
    found = runner.drive(places, say=quiet)
    stopped = "not run: its line stopped at clean@{}"
    for place in ("dock", "station", "pier"):
        assert found[f"clean@{place}"] == ("made: unknown; gathered words: judged again, output kept: pass, accepted "
                                           "automatically"), (place, found)
        assert found[f"count@{place}"] == found[f"echo@{place}"] == found[f"tally@{place}"] == ACCEPTED, (place, found)
    assert found["clean@hangar"].startswith("made: unknown; gathered words: judged again, output kept: fail"), found
    assert found["echo@hangar"] == ACCEPTED, found
    assert found["count@hangar"] == found["tally@hangar"] == stopped.format("hangar"), found
    assert found["clean@loud"].startswith(
        "made: fail; automatic free remake, attempt 2, after shout: made: fail;"), found
    assert found["names@pier"].startswith("error: RuntimeError: names failed"), found
    for place, (said, raised) in ERRED.items():  # a raise's line is exactly its cause; a missing input's names its path
        did, ending = found[f"clean@{place}"], f"; fault report {report_of(runner, f'clean@{place}')}"
        assert did == said + ending if raised else did.startswith(said) and did.endswith(ending), found
        assert found[f"count@{place}"] == stopped.format(place), found
    assert len(gathered(runner)) == 4  # dock, station, hangar and pier: loud's other gate fails, the rest never made
    faults = runner.store.cache.parent / "faults"
    assert {report.stem for report in faults.iterdir()} >= {f"clean@{place}" for place in ("hangar", "loud", *ERRED)}
    assert not any(report.stem.endswith(("@dock", "@station")) for report in faults.iterdir()), list(faults.iterdir())
    report = report_of(runner, "clean@hangar").read_text()
    assert "why its line stopped: clean@hangar answered fail: words: 8 words, limit 5" in report, report
    assert '  words: fail: 8 words, limit 5\n    measures: {"words": 8}\n    - 3 words too many' in report, report
    assert "cleaning" in report and "python -m score run toy --place hangar" in report, report
    assert "shout: fail: shouts" in report_of(runner, "clean@loud").read_text()
    for place, (said, traceback) in ERRED.items():
        report = report_of(runner, f"clean@{place}").read_text()
        assert said.split(": ", 2)[-1] in report and (not traceback or "Traceback" in report), report
    making = runner.store.cache / "making"
    assert not making.exists() or not list(making.iterdir()), list(making.iterdir())
    lines = runner.lines(places)
    assert lines["hangar"][0] == f"stopped at clean@hangar: fault report {report_of(runner, 'clean@hangar')}", lines
    assert lines["dock"][0] == lines["station"][0] == "done", lines

    brief(runner.world, "hangar", "a ship")
    brief(runner.world, "station", "a ship")
    cause = runner.standing(COUNT, "station")
    assert cause == "clean@station has not run on its current inputs", cause
    report = runner.fault_report(COUNT, "station", f"blocked: {cause}", cause).read_text()
    assert "what moved its key since its last record: brief changed" in report, report
    again = runner.drive(places, say=quiet)
    assert again["count@hangar"] == again["count@station"] == ACCEPTED, again
    assert not report_of(runner, "clean@hangar").exists()
    assert {again[f"{stage}@dock"] for stage in ("clean", "count", "echo", "tally")} == {"fresh"}, again
    assert len(gathered(runner)) == 4  # hangar and station now clean to dock's "A SHIP", whose limit stands

    paid = a_driven_runner({"dock": "a ship"}, euros=0.2)
    assert paid.drive(["dock"], say=quiet)["count@dock"] == ACCEPTED
    key = paid.key(paid.stages["clean"], "dock")["key"]
    assert [ticket for _, ticket in gathered(paid)] == [f"clean@dock {key}"]
    assert paid.store.clearances("clean@dock", key)[0]["euros"] == 0.2


# --- lines side by side ----------------------------------------------------------------------------------------------

MEETING_SECONDS = 15
def judge_met(output, inputs, evidence):
    return checks.Verdict("met", checks.PASS, "it ran")


MET = (checks.Check("met", judge_met),)


def meeting(data, me, others):
    """A make that says it started, then waits until every other named make started too: run one at a time, the
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


def made_once(data):
    def make(inputs, out, seed, params):
        with (data / "ground-made.txt").open("a") as made:
            made.write("made\n")
        (out / "ground.txt").write_text("ground")
    return make


def make_on_ground(inputs, out, seed, params):
    (out / "built.txt").write_text((inputs["ground"] / "ground.txt").read_text())


def a_world_of(places):
    world = a_world({place: None for place in places})
    return world.roots["data"], world


def meet_the_other_places(data):
    """A place's make meeting every other place's (its place is its declared input's folder name)."""
    def make(inputs, out, seed, params):
        place = inputs["place"].name
        meeting(data, place, [other for other in PLACES if other != place])(inputs, out, seed, params)
    return make


def test_a_drive_runs_what_reads_nothing_of_each_other_side_by_side_an_environment_node_once_and_only_what_is_read():
    """One world of two places. meet (each place's waits until the other place's started), first and second (hangar
    only, each waiting until the other started) are run one at a time only if the drive runs one node at a time; ground
    (the environment) is read by both places' build; sky (the environment, read by no place) and other (a place row
    the run leaves) wait for a make that never starts, so a drive that ran either would take MEETING_SECONDS and fail.
    Fault (owner, 2026-10-11: nothing waits for the slowest): the drive ran one node at a time.
    Break: score/graph/__init__.py: 'JOBS = 8' -> 'JOBS = 1'
    Break: score/graph/__init__.py: '        chosen = found if whole else' -> '        chosen = found if True else'"""
    data, world = a_world_of(PLACES)
    hangar_only = dict(applies=lambda place: place == "hangar")
    table = (graph.Stage("ground", "world", made_once(data), TEXT, MET),
             graph.Stage("sky", "world", meeting(data, "sky", ["never"]), TEXT, MET),
             graph.Stage("meet", "place", meet_the_other_places(data), TEXT, MET, files={"place": "{data}/{place}"}),
             graph.Stage("first", "place", meeting(data, "first", ["second"]), TEXT, MET, **hangar_only),
             graph.Stage("second", "place", meeting(data, "second", ["first"]), TEXT, MET, **hangar_only),
             graph.Stage("build", "place", make_on_ground, TEXT, MET, after={"ground": READS}),
             graph.Stage("other", "place", meeting(data, "other", ["never"]), TEXT, MET))
    runner = a_runner(world, a_store(), table)
    started = time.monotonic()
    found = runner.drive(PLACES, say=quiet, whole=False, only=["meet", "first", "second", "build"])
    assert time.monotonic() - started < MEETING_SECONDS
    assert set(found.values()) == {ACCEPTED}, found
    assert sorted(found) == sorted(["ground", "meet@hangar", "meet@station", "first@hangar", "second@hangar",
                                    "build@hangar", "build@station"]), found
    assert [node for node in found if node.startswith(("ground", "build"))] == ["ground", "build@hangar",
                                                                                "build@station"], found
    assert (data / "ground-made.txt").read_text() == "made\n"
    assert set(runner.lines(["hangar"], whole=False)) == {"world", "hangar"}
    assert list(runner.lines(["hangar"], whole=False)["world"][1]) == ["ground"]
    assert set(runner.lines(["hangar"], whole=False, only=["build"])["hangar"][1]) == {"build@hangar"}


def failing_with(code, times):
    """A make raising an HTTP `code` error on its first `times` tries in its process, then writing."""
    tries = []

    def make(inputs, out, seed, params):
        tries.append(1)
        if len(tries) <= times:
            raise urllib.error.HTTPError("https://images.example", code, "server", {}, None)
        (out / "made.txt").write_text(f"made on try {len(tries)}")
    return make


def make_leaving_a_thread(inputs, out, seed, params):
    threading.Thread(target=threading.Event().wait).start()  # never ends, and not a daemon
    (out / "made.txt").write_text("made")


def make_asking_its_stacks(inputs, out, seed, params):
    os.kill(os.getpid(), signal.SIGUSR1)  # as the agents' door's stack verb asks
    (out / "made.txt").write_text(str(os.getpid()))


def hung(signal_number, frame):
    raise RuntimeError("the drive did not end")  # not an OSError: a wait swallows those


@dataclasses.dataclass(frozen=True)
class Ended:
    """One drive of a one-node maps@hangar: its make, whether it is paid; what the drive ends with (ACCEPTED exactly,
    or the start of its error), words its log holds and never holds, how many transient errors it logs (None: not
    counted), and words its stacks file holds (None: no stacks asked)."""
    make: object
    outcome: str
    paid: bool = False
    logged: tuple = ()
    never_logged: tuple = ()
    transient_lines: int | None = None
    stacks: str | None = None


ENDED = {
    "a free node's two HTTP 500s are tried again, accepted on its third try":
        Ended(failing_with(500, 2), ACCEPTED, logged=("try 2 of 5 in 0 s", "try 3 of 5"), never_logged=("try 4 of 5",)),
    "a paid node's HTTP 500 is a gap, never tried again":
        Ended(failing_with(500, 1), "error: HTTPError: HTTP Error 500", paid=True, never_logged=("transient error",)),
    "a free node's 503 past every retry ends in its error":
        Ended(failing_with(503, graph.RETRIES + 1), "error: HTTPError: HTTP Error 503", transient_lines=graph.RETRIES),
    "a 404 is not transient, never tried again": Ended(failing_with(404, 1), "error: HTTPError: HTTP Error 404",
                                                       transient_lines=0),
    "a node leaving a thread running does not hold up the drive": Ended(make_leaving_a_thread, ACCEPTED),
    "a node asked for its stacks writes them and goes on": Ended(make_asking_its_stacks, ACCEPTED,
                                                                 stacks="make_asking_its_stacks"),
}
TRANSIENT = {"a timeout": (TimeoutError(), True), "a reset connection": (ConnectionResetError(), True),
             "a refused connection under a URLError": (urllib.error.URLError(ConnectionRefusedError()), True),
             "a ValueError": (ValueError(), False)}


def test_a_drive_ends_whatever_its_node_leaves_and_tries_a_free_node_again_only_on_a_transient_error(tmp_path,
                                                                                                    monkeypatch):
    """Eight places' maps on the image model's HTTP 500s, 2026-10-12; a paid node's failure is a gap (ADR-0005).
    Fault (2026-10-12): two `score run`s did all their work and never exited. And a node's process answers a SIGUSR1
    with its stacks in <home>/logs/stacks/<its pid>.txt, going on (2026-11-07: a forked node had no dump). Each row
    of ENDED is one drive under a 20 s alarm; TRANSIENT's rows are graph.transient's answers.
    Break: score/graph/__init__.py: '                if stage.paid or attempt == RETRIES or not transient(error):' -> '                if attempt == RETRIES or not transient(error):'
    Break: score/graph/__init__.py: '        sys.stderr.flush()\n        os._exit(0)' -> '        sys.stderr.flush()\n        sys.exit(0)'
    Break: score/graph/__init__.py: '        stacks_on_ask()\n        threading' -> '        threading'"""
    monkeypatch.setattr(graph, "RETRY_WAIT", 0)
    monkeypatch.setenv("PROPS_HOME", str(tmp_path))
    signal.signal(signal.SIGALRM, hung)
    for name, row in ENDED.items():
        runner = a_runner(a_world_of(["hangar"])[1], a_store(),
                          (graph.Stage("maps", "place", row.make, TEXT, MET, paid=row.paid, euros=0.1),))
        runner.cleared = lambda node, euros, forecast=None: contextlib.nullcontext()  # no clearance to buy here
        signal.alarm(20)
        try:
            did = runner.drive(["hangar"], say=quiet)
        finally:
            signal.alarm(0)
        log = runner.desk("logs", "maps@hangar", ".log").read_text()
        assert list(did) == ["maps@hangar"], (name, did)
        assert (did["maps@hangar"] == ACCEPTED if row.outcome == ACCEPTED
                else did["maps@hangar"].startswith(row.outcome)), (name, did)
        assert all(words in log for words in row.logged), (name, log)
        assert not any(words in log for words in row.never_logged), (name, log)
        assert row.transient_lines is None or log.count("transient error") == row.transient_lines, (name, log)
        if row.stacks:
            pid = accepted_text(runner.store, "maps@hangar", "made.txt")
            assert row.stacks in (tmp_path / "logs" / "stacks" / f"{pid}.txt").read_text(), name
    assert {name: graph.transient(error) for name, (error, _) in TRANSIENT.items()} == {
        name: expected for name, (_, expected) in TRANSIENT.items()}


CHILD_THREADS = "import os; print(os.environ['OMP_NUM_THREADS'], os.environ['NUMBA_NUM_THREADS'])"


def live_openblas_threads():
    """The pool size each OpenBLAS loaded in this process runs on now (not what its variable says)."""
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


def thread_note(jobs, monkeypatch, cores=24):
    """The thread note one node writes when `jobs` nodes share `cores`, numpy's and scipy's OpenBLAS loaded before the
    drive forks (as score.stages loads them); and the runner."""
    import numpy  # noqa: F401
    import scipy.linalg  # noqa: F401
    monkeypatch.delenv("OPENBLAS_NUM_THREADS", raising=False)  # the pool sized by the cap (one_openblas_thread_a_node)
    runner = a_runner(a_world_of(["hangar"])[1], a_store(), (graph.Stage("threads", "place", make_thread_note, TEXT,
                                                                         MET),))
    with monkeypatch.context() as patched:
        patched.setattr(os, "cpu_count", lambda: cores)
        did = runner.drive(["hangar"], say=quiet, jobs=jobs)["threads@hangar"]
    if did != ACCEPTED:
        return did, runner
    return accepted_text(runner.store, "threads@hangar", "threads.txt").splitlines(), runner


@contextlib.contextmanager
def full_disk(path):
    """graph.logged on a full disk (batch 1, 2026-10-26: the conductor's disk full)."""
    raise OSError(28, "No space left on device")
    yield


@dataclasses.dataclass(frozen=True)
class Threads:
    """One way a run is started on 24 cores: the owner's OMP_NUM_THREADS (None: unset), the run's arguments and what
    is broken in its node (BROKEN); then what it ends with, worked out by hand: the run's refusal (its exit and a
    part of what argparse printed), or its node's note (its own threads, its child's, its loaded OpenBLAS pools'
    size), or parts of what the node says and of its fault report."""
    omp: str | None
    argv: tuple
    broken: str | None = None
    refused: str | None = None
    printed: str = ""
    note: tuple | None = None
    said: tuple = ()
    report: tuple = ()


BROKEN = {"cap": ("OPENBLAS_SETTERS", ("no_such_setter",)), "log": ("logged", full_disk)}
OVER = "refused: 25 jobs of 1 thread(s) each ask for 25 threads on 24 cores; lower --jobs or pass --oversubscribe"
THREADS = {
    "24 cores over 6 jobs: 4 threads each, the OpenBLAS loaded before the fork too":
        Threads(None, ("--jobs", "6"), note=("4 4", "4 4", "4")),
    "the owner's smaller OMP_NUM_THREADS=1 stands": Threads("1", ("--jobs", "6"), note=("1 4", "1 4", "4")),
    "an empty OMP_NUM_THREADS is unset": Threads("", ("--jobs", "6"), note=("4 4", "4 4", "4")),
    "8 jobs: 3 threads each": Threads(None, ("--jobs", "8"), note=("3 3", "3 3", "3")),
    "24 jobs: one thread each": Threads(None, ("--jobs", "24"), note=("1 1", "1 1", "1")),
    "25 jobs run oversubscribed only when asked": Threads(None, ("--jobs", "25", "--oversubscribe"),
                                                          note=("1 1", "1 1", "1")),
    "25 jobs not asked to oversubscribe are refused": Threads(None, ("--jobs", "25"), refused=OVER),
    "--jobs 0 is refused by argparse": Threads(None, ("--jobs", "0"), refused="2", printed="at least 1"),
    "--jobs -2 is refused by argparse": Threads(None, ("--jobs", "-2"), refused="2", printed="at least 1"),
    **{f"OMP_NUM_THREADS={value!r} is refused before any node": Threads(
        value, ("--jobs", "6"), refused=f"refused: OMP_NUM_THREADS={value!r} is not a thread count (a whole number "
                                        "above 0); unset it or set one") for value in ("4,2", "auto", "0")},
    "a cap that fails says its cause in the node's fault report (review C11: raised before its log opened)":
        Threads(None, ("--jobs", "6"), broken="cap", said=("pool cannot be capped",),
                report=("RuntimeError", "  | ", "pool cannot be capped")),
    "a log that cannot be written still says why the node ended, through the pipe":
        Threads(None, ("--jobs", "6"), broken="log",
                said=("OSError: [Errno 28] No space left on device", "raised outside its log", "Traceback")),
}


@pytest.mark.parametrize("row", THREADS.values(), ids=THREADS.keys())
def test_each_node_and_its_children_share_the_cores_and_a_count_that_cannot_be_kept_is_said(row, monkeypatch):
    """C11, 2026-10-17: six local nodes each sized their pools to every core; review (C11): OMP_NUM_THREADS '4,2',
    'auto' and '0' crashed every node, --jobs 0 ended in a ZeroDivisionError, and a cap that raised before the node's
    log opened ended it 'without saying what it did'; batch 1, 2026-10-26: the conductor's disk full,
    surfaces-parts@engineroom ended 'without saying what it did' and an empty log. Each row (THREADS) is a run started
    through score run's own checks on 24 cores, its one node driven when the run is not refused.
    Break: score/graph/__init__.py: 'os.environ[variable] = str(threads if own is None else min(own, threads))' -> 'os.environ[variable] = str(threads)'
    Break: score/graph/__init__.py: '        with logged(log):\n            try:\n                cap_threads(threads)' -> '        cap_threads(threads)\n        with logged(log):\n            try:'
    Break: score/graph/__init__.py: '        except BaseException as error:  # noqa: BLE001 - raised where' -> '        except KeyError as error:  # noqa: BLE001 - raised where'
    Break: score/graph/__init__.py: '        if own and not (own.isdigit() and int(own) > 0):' -> '        if own and not own.isdigit():'"""
    from score import __main__ as command
    if row.omp is None:
        monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    else:
        monkeypatch.setenv("OMP_NUM_THREADS", row.omp)
    monkeypatch.setattr(os, "cpu_count", lambda: 24)
    printed, refused = io.StringIO(), None
    try:
        with contextlib.redirect_stderr(printed):
            options = command.parse(["run", "world1", *row.argv])
            command.checked_thread_variables()
            command.checked_threads(options)
    except SystemExit as refusal:
        refused = str(refusal.code)
    assert refused == row.refused and row.printed in printed.getvalue(), (refused, printed.getvalue())
    if refused:
        return
    if row.broken:
        monkeypatch.setattr(graph, *BROKEN[row.broken])
    outcome, runner = thread_note(options.jobs, monkeypatch)
    if row.note:
        assert outcome[:2] == list(row.note[:2]) and outcome[2].split(), outcome
        assert set(outcome[2].split()) == {row.note[2]}, outcome
    else:
        assert all(part in outcome for part in row.said) and "without saying" not in outcome, outcome
        report = runner.desk("faults", "threads@hangar", ".txt")
        assert all(part in report.read_text() for part in row.report), report


# --- runs side by side on one store ----------------------------------------------------------------------------------

def made_slowly(data, seconds=1):
    """A make counting its makes in a file and taking `seconds` (a second: two runs of it at once would overlap)."""
    def make(inputs, out, seed, params):
        with (data / "made.txt").open("a") as made:
            made.write("made\n")
        time.sleep(seconds)
        (out / "made.txt").write_text("made")
    return make


def run_in_a_process(runner, places):
    """`runner.run(places)` in a forked process; the process and the pipe its {node: what it did} comes down."""
    receiving, sending = graph.FORK.Pipe(duplex=False)
    process = graph.FORK.Process(target=lambda: sending.send(runner.run(places)))
    process.start()
    return process, receiving


def make_note(inputs, out, seed, params):
    (out / "note.txt").write_text(inputs["note"].read_text())


def make_writing_into_its_input(inputs, out, seed, params):
    (inputs["slow"] / "saved-over.txt").write_text("a save into the input")
    (out / "count.txt").write_text("counted")


# One place's nodes driven in turn by one runner: (row, note.txt's text, whether this checkout holds the accepted
# output's commit, the node, how its outcome starts, words it also says, whether the node's accepted output is the one
# it had before). None for holds: the real repository answers.
GUARDED = (
    ("note's first make is accepted", "new", None, "note", ACCEPTED, (), False),
    ("an older checkout's input under a commit it lacks: made, never accepted over the newer output", "old", False,
     "note", "made: pass, not accepted: key differs from the accepted one", ("pull main",), True),
    ("this checkout holds the accepted one's commit: its new key is accepted", "newest", None, "note", ACCEPTED, (),
     False),
    ("slow is made for writer to read", "newest", None, "slow", ACCEPTED, (), False),
    ("writer saves over its read-only input slow: it fails and stores nothing", "newest", None, "writer",
     "error: RuntimeError: writer@hangar: its make wrote into its read-only input slow", (), True),
)


def test_a_make_is_accepted_only_over_its_own_commits_output_and_only_when_it_left_its_inputs_as_they_were(
        monkeypatch):
    """A node's make is accepted only when it leaves its inputs untouched and no newer commit made the accepted output
    under another key. 2026-10-12: a runner in an older worktree accepted terrain's old output over the newer accepted
    one; light@camp's make saved over its read-only input. 2026-11-05: a commit this repository knows nothing of (a
    local commit rebased away before its push) never blocks a row for good; one only another branch holds still does
    (a newer main not pulled yet).
    Break: score/graph/__init__.py: '        if not records or any(record["key"] == key for record in records):' ->
    '        if True:' -> the older checkout's note is accepted;
    or score/graph/_code.py holds: drop `if known.returncode != 0: return True` (a rebased-away commit blocks for good).
    Break: score/graph/__init__.py: '        if changed:\n            raise RuntimeError(f"{node}: its make wrote' ->
    '        if False:\n            raise RuntimeError(f"{node}: its make wrote' -> writer is accepted."""
    data, world = a_world_of(["hangar"])
    note = graph.Stage("note", "place", make_note, TEXT, MET, files={"note": "{data}/{place}/note.txt"})
    slow = graph.Stage("slow", "place", made_slowly(data, 0), TEXT, MET)
    writer = graph.Stage("writer", "place", make_writing_into_its_input, TEXT, MET, after={"slow": READS})
    runner = a_runner(world, a_store(), (note, slow, writer))
    for row, text, holds, name, begins, words, kept in GUARDED:
        (data / "hangar" / "note.txt").write_text(text)
        before = runner.store.accepted(f"{name}@hangar")
        with monkeypatch.context() as patched:
            if holds is not None:
                patched.setattr(graph._code, "holds", lambda commit, holds=holds: holds)
            did = runner.drive(["hangar"], say=quiet, whole=False, only=[name])[f"{name}@hangar"]
        assert did.startswith(begins) and all(word in did for word in words), (row, did)
        assert (runner.store.accepted(f"{name}@hangar") == before) == kept, row
    assert runner.store.records("writer@hangar") == []
    assert graph._code.holds("f" * 40)
    ahead = subprocess.run(["git", "-C", str(REPO), "rev-parse", "origin/main"], capture_output=True, text=True)
    behind = subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", ahead.stdout.strip(), "HEAD"])
    if ahead.returncode == 0 and behind.returncode != 0:
        assert not graph._code.holds(ahead.stdout.strip())


def judge_gapped(output, inputs, evidence):
    return checks.Verdict(graph.GAPPED, checks.FAIL, "hangar: an accepted gap", findings=("hangar: no made model",))


def judge_brief_fault(output, inputs, evidence):
    faulty = "fault" in inputs["brief"].read_text()
    return checks.Verdict("other", checks.FAIL if faulty else checks.PASS, "a fault no gap names" if faulty else "ok")


def make_film(inputs, out, seed, params):
    (out / "film.txt").write_text((inputs["complete"] / "clean.txt").read_text())


def gapped_runner(text):
    """A completion gate failing its accepted gap (and an ungapped fault when the brief says so); a film reading it
    gapped, a count that does not."""
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "brief.txt").write_text(text)
    complete = graph.Stage("complete", "place", make_clean, TEXT,
                           (checks.Check(graph.GAPPED, judge_gapped), checks.Check("other", judge_brief_fault)),
                           files={"brief": "{data}/{place}/brief.txt"})
    film = graph.Stage("film", "place", make_film, TEXT, MET, after={"complete": READS}, gapped=("complete",))
    count = graph.Stage("count", "place", make_film, TEXT, MET, after={"complete": READS})
    return a_runner(world, a_store(), (complete, film, count))


def test_a_gapped_reader_runs_past_a_gate_failing_only_on_its_accepted_gaps_and_stops_on_any_other_fault():
    """The overseer, 2026-10-15: demo-film runs on a place whose complete fails only on its accepted gaps; the gate
    still fails by name, a reader not reading it gapped stops, and a fault no gap names stops both.
    Break: score/graph/__init__.py: '                    passes = {before for before in on_gaps if before.partition("@")[0] in stage.gapped}' -> '                    passes = set()'"""
    runner = gapped_runner("a ship")
    found = runner.drive(["hangar"], say=quiet)
    assert found["complete@hangar"].startswith("made: fail, accepted automatically; fault report"), found
    assert found["film@hangar"] == ACCEPTED, found
    assert found["count@hangar"] == "not run: its line stopped at complete@hangar", found
    assert runner.store.accepts("complete@hangar")[-1]["status"] == "complete apart from accepted gaps (1)"
    assert runner.status(["hangar"])["complete@hangar"] == "complete apart from accepted gaps (1), accepted"
    assert "stale" not in runner.status(["hangar"])["film@hangar"]
    runner = gapped_runner("a ship with a fault")
    assert runner.drive(["hangar"], say=quiet)["film@hangar"] == "not run: its line stopped at complete@hangar"
    assert runner.run_node(runner.stages["film"], "hangar").startswith("blocked: complete@hangar answered fail")
    assert runner.store.accepted("complete@hangar") is None


# --- memory: no node starts while this PC's memory is short --------------------------------------------------------
# Fault (owner, 2026-10-22): this PC (43 GB) has run out of memory before; the Buy batch goes from 8 jobs to 16.

FLOOR = graph.MEMORY_FLOOR
GIGA = 10**9


def faked(monkeypatch, readings):
    """graph.AVAILABLE replaced by `readings` in turn, its last one kept; the readings taken so far."""
    taken = []

    def reading():
        taken.append(readings[min(len(taken), len(readings) - 1)])
        return taken[-1]
    monkeypatch.setattr(graph, "AVAILABLE", reading)
    return taken


def a_machine(proc, cgroups, monkeypatch):
    """One PC in fake `proc` and `cgroups` folders, read by the real readers (graph.PROC, CGROUPS, docker's listing):
    a node 100 (1000 MB resident, 300 MB its share; VmHWM 10 GB) whose child 101 shares its pages (1000 MB, 200 MB
    its share) and exec'd tools/cloud/blender_cloud.py (VmHWM 3 GB), whose child 102 has no readable smaps_rollup
    (50 MB resident), whose grandchild 103 under 101 holds 100 MB by share, and whose worker 104 forked from it and
    never exec'd holds 1 GB by share though its VmHWM, inherited, says 2 GB; a node 200 (9000 MB, outside 100's tree)
    whose child 201 runs tools/cloud/gemini_judge.py; and three containers: the first SCORE one (score-this-pc: 30 GB
    cap, 10 GB anon; its sshd 10 runs paint_bake.py takes 20 (5 GB now, peaked 6) and 30 (1 GB, peaked 2), an idle
    ssh session 40 and an rsync session 50), a kind's own (score-this-pc-segment: 10 GB cap, 4 GB anon; its sshd 60
    runs a segment_worker.py take 70) and another program's (postgres: 50 GB cap, never read). The cgroup folders,
    by name (docker's listing of them: LISTED)."""
    page, megabyte = os.sysconf("SC_PAGE_SIZE"), 2**20
    pages = megabyte // page
    monkeypatch.setattr(graph, "PROC", str(proc))
    proc.mkdir()
    a_process(proc, 1, 0, 0)
    a_process(proc, 100, 1, 1000 * pages, 300 * 1024)
    a_process(proc, 101, 100, 1000 * pages, 200 * 1024)
    a_process(proc, 102, 100, 50 * pages)
    a_process(proc, 103, 101, 100 * pages, 100 * 1024)
    a_process(proc, 104, 100, 10, pss_kb=GIGA // 1024)
    a_process(proc, 200, 1, 9000 * pages, 9000 * 1024)
    a_process(proc, 201, 200, 10)
    for pid, (command, high) in {100: (b"python\0score\0run\0", 10 * GIGA),
                                 101: (b"python3\0tools/cloud/blender_cloud.py\0--detach\0", 3 * GIGA),
                                 104: (b"python\0score\0run\0", 2 * GIGA),
                                 201: (b"python3\0tools/cloud/gemini_judge.py\0", 0)}.items():
        (proc / str(pid) / "cmdline").write_bytes(command)
        (proc / str(pid) / "status").write_text(f"Name:\tnode\nVmHWM:\t{high // 1024} kB\n")
    for sshd in (10, 60):
        a_process(proc, sshd, 1, 1)
    a_container_job(proc, 10, 20, "paint_bake.py", 5, 6)
    a_container_job(proc, 10, 30, "paint_bake.py", 1, 2)
    for session in (40, 50):
        a_process(proc, session, 10, 1)
        (proc / str(session) / "cmdline").write_bytes(b"sshd: root@notty\0")
    a_process(proc, 51, 50, 1)
    (proc / "51" / "cmdline").write_bytes(b"rsync\0--server\0.\0")
    a_container_job(proc, 60, 70, "segment_worker.py", 3, 4)
    folders = {name: cgroups / identity for name, identity in (("first", "aaa"), ("segment", "bbb"), ("theirs", "ccc"))}
    for name, (room, anon, procs) in {"first": (30, 10, "10\n20\n21\n30\n31\n40\n50\n51\n"),
                                      "segment": (10, 4, "60\n70\n71\n"), "theirs": (50, 0, "")}.items():
        folders[name].mkdir(parents=True)
        (folders[name] / "cgroup.procs").write_text(procs)
        (folders[name] / "memory.max").write_text(f"{room * GIGA}\n")
        (folders[name] / "memory.stat").write_text(f"anon {anon * GIGA}\nfile 0\n")
    monkeypatch.setattr(graph, "CGROUPS", (str(cgroups / "{id}"),))
    return folders


LISTED = "aaa score-this-pc\nbbb score-this-pc-segment\nccc postgres\n"


def a_running(*nodes):
    """runner.coming's `running` of `nodes` ((stage name, pid, whether it is alive)), each at hangar."""
    return {number: (types.SimpleNamespace(name=stage, grain="place"), "hangar",
                     types.SimpleNamespace(pid=pid, is_alive=lambda alive=alive: alive))
            for number, (stage, pid, alive) in enumerate(nodes)}


TENTH = int(0.1 * FLOOR)
WAITING_BAKES = (("bake", 11, True), ("bake", 12, True), ("bake", 13, True), ("count", 14, True))
SETTLE = (("settle", 11, True),)
# What a new node has room for: (row, available, SCORE_MIN_FREE_GB, the running nodes' (peak, holds), the new
# node's expected peak, the floor that applies, whether it fits).
ROOM = (
    ("none running: one unmeasured node", 2.5 * FLOOR, "", [], FLOOR, FLOOR, True),
    ("beside one holding nothing yet: none", 2.5 * FLOOR, "", [(FLOOR, 0)], FLOOR, FLOOR, False),
    ("beside one holding its peak", 2.5 * FLOOR, "", [(FLOOR, FLOOR)], FLOOR, FLOOR, True),
    ("beside one holding more than its peak", 2.5 * FLOOR, "", [(FLOOR, 2 * FLOOR)], FLOOR, FLOOR, True),
    ("beside one at 1 of its 3-floor peak, it grows after its start", 2.5 * FLOOR, "", [(3 * FLOOR, FLOOR)],
     0.1 * FLOOR, FLOOR, False),
    ("a 4 GB floor named on 9 GB: room for one", 9 * 2**30, "4", [], 4 * 2**30, 4 * 2**30, True),
    ("a 4 GB floor named on 9 GB: none beside one starting", 9 * 2**30, "4", [(4 * 2**30, 0)], 4 * 2**30,
     4 * 2**30, False),
    ("the floor unnamed on 9 GB: none", 9 * 2**30, "", [], FLOOR, FLOOR, False),
    ("a second settle beside the first at its 8 GiB stage peak", 20 * 2**30, "", [(8 * 2**30, 0)], 8 * 2**30,
     FLOOR, False),
    ("one settle at its 12 GB tree on 30 GB", 30 * GIGA, "", [], 12 * GIGA, FLOOR, True),
)
# What each running node reserves (runner.coming), and whether a new node then fits: (row, the running nodes, this
# PC or not, what each tree holds now, the container's room (None: unread), the stage peaks, the client trees, the
# grown client stages, the reserves expected, available, the new node's expected peak, whether it fits).
COMING = (
    ("on this PC waiting bake clients reserve their kept trees beside the container counted once", WAITING_BAKES,
     True, TENTH, 1.5 * FLOOR, {"count": 2 * FLOOR}, {"bake": TENTH}, {"bake"},
     [(TENTH, TENTH)] * 3 + [(2 * FLOOR, TENTH), (int(1.5 * FLOOR), 0)], 5.5 * FLOOR, FLOOR, True),
    ("on this PC with the container unread each bake keeps the default", WAITING_BAKES, True, TENTH, None,
     {"count": 2 * FLOOR}, {"bake": TENTH}, {"bake"}, [(FLOOR, TENTH)] * 3 + [(2 * FLOOR, TENTH)], 5.5 * FLOOR,
     FLOOR, False),
    ("off this PC the container is never read and each bake keeps the default", WAITING_BAKES, False, TENTH, "never",
     {"count": 2 * FLOOR}, {"bake": TENTH}, {"bake"}, [(FLOOR, TENTH)] * 3 + [(2 * FLOOR, TENTH)], 5.5 * FLOOR,
     FLOOR, False),
    ("a running settle client keeps its tree's kept 12 GB, a second does not start beside it", SETTLE, True, 0, 0,
     {"settle": 8 * 2**30}, {"settle": 12 * GIGA}, set(), [(12 * GIGA, 0), (0, 0)], 30 * GIGA, 12 * GIGA, False),
    ("a client stage whose tree was never measured reserves the floor while it runs", SETTLE, True, 0, 0, {}, {},
     set(), [(FLOOR, 0), (0, 0)], 100 * FLOOR, FLOOR, True),
    ("an ended node holds nothing, a live one its stage's peak", (("clean", 11, False), ("count", 12, True)), False,
     0, "never", {"clean": 2 * FLOOR, "count": FLOOR}, {}, set(), [(FLOOR, 0)], 100 * FLOOR, FLOOR, True),
)
# What a client stage's node reserves for its own tree: (row, the stage peaks, the client trees, the grown client
# stages, client_peak, client_reserve).
CLIENT = (
    ("settle's 2.87 GB tree kept from a small early node: its 8 GiB stage peak until one grew",
     {"settle": 8 * 2**30}, {"settle": int(2.87 * GIGA)}, set(), int(2.87 * GIGA), 8 * 2**30),
    ("settle grown: its kept 2.87 GB", {"settle": 8 * 2**30}, {"settle": int(2.87 * GIGA)}, {"settle"},
     int(2.87 * GIGA), int(2.87 * GIGA)),
    ("settle's real 12 GB tree kept over its 8 GiB stage peak", {"settle": 8 * 2**30}, {"settle": 12 * GIGA}, set(),
     12 * GIGA, 12 * GIGA),
    ("never measured: the floor", {}, {}, set(), FLOOR, FLOOR),
)


def test_a_node_is_given_room_only_for_what_it_and_the_running_ones_may_still_take(tmp_path, monkeypatch):
    """A new node starts only while available memory, less what each running node may still grow by and less its own
    expected peak, stays at the floor (SCORE_MIN_FREE_GB, else MEMORY_FLOOR). A node's tree is read by each process's
    share of its pages (rss where that cannot be read) and by its VmHWM summed, a worker forked and never exec'd by its
    share; a tree that runs blender_cloud.py ran a container client. Every SCORE container on this PC is read (never
    another program's), its room summed and its takes counted; the container reserves what its takes may still grow to,
    each kind's kept take peaks deciding. On this PC a container client's node reserves its own tree, at least its
    stage peak until one of its nodes grew, and the container once beside its callers; off this PC, or with the
    container unread, each keeps its stage's default; an ended node holds nothing. Histories: round 23 (light passes'
    21 GB take paused before its peak was kept), 2026-10-28 (finish-route-views grew after its start; nodes ended but
    not reaped counted their peaks), 2026-10-29 (the cap's whole 16.5 GiB reserved beside three small takes), round 26
    and the coordinator, 2026-10-30 (settle's 12-13 GB never kept, two settles started together), 2026-10-31 (PRD #73:
    each kind in a container of its own), 2026-11-10 (a settle tree kept at 25.8 GB by inherited VmHWM).
    Break: score/graph/__init__.py: '    coming = sum(max(0, peak - holds) for peak, holds in running)' -> '    coming = 0'
    -> ROOM's "beside one holding nothing yet" fits.
    Break: score/graph/__init__.py:
    '            mine = process.pid in users and (reading is not None or process.pid not in calling)' ->
    '            mine = False' -> the bake clients keep the default beside the container: no room.
    Break: score/graph/__init__.py: 'return found if stage in grown else max(found, peaks.get(stage, memory_floor()))'
    -> 'return found' -> the ungrown settle reserves 2.87 GB.
    Break: score/graph/__init__.py: 'client_reserve(name, peaks, clients, grown) if mine' ->
    'held[process.pid] if mine' -> the running settle reserves what it holds, a second starts beside it.
    Break: score/graph/__init__.py: '                clients.update(self.keep_client_tree(stage.name, high))' ->
    '                pass' -> node 100's tree peak not kept while it runs.
    Break: score/graph/__init__.py: 'max(seen[node], highs.get(process.pid, 0))' -> 'seen[node]' -> nothing kept (its
    1.7 GB share is under the floor).
    Break: score/graph/__init__.py: 'if pid != root and forked_only(pid, parent)' -> 'if False' -> worker 104 counted
    at its inherited 2 GB VmHWM, not its 1 GB share.
    Break: score/graph/__init__.py: 'return bool(mine) and mine ==' -> 'return bool(mine) or mine ==' -> the exec'd
    child 101 counted by its share, not its 3 GB VmHWM.
    Break: score/graph/__init__.py: '                total += proportional_bytes(pid, table[pid][1])' ->
    '                total += table[pid][1]' -> 100's tree by its resident sum.
    Break: score/graph/__init__.py: '    return sum(room for room, _ in readings), jobs' ->
    '    return readings[0][0], container_jobs(readings[0][1])' -> 20 GB, the segment take missing; or
    'name == CONTAINER or name.startswith(f"{CONTAINER}-")' -> 'True' in container_cgroups -> postgres read.
    Break: score/graph/__init__.py: '    growth = sum(max(0, peak - holds) for peak, (_, holds, _) in zip(peaks, jobs.values()))'
    -> '    growth = room' -> the whole room again.
    Break: score/graph/__init__.py: '[kind, max(high, kept["open"].get(key, [kind, 0, None])[1]), None]' ->
    '[kind, 0, None]' -> each take's highest reading lost: the bake takes' kept peaks, the stopped take's 21 GB.
    Break: score/graph/__init__.py: 'TAKE_PEAK if len(measured) < TAKES_TRUSTED else 0' -> '0' -> one written take
    trusted: take 20 and the idle slot grow 1 + 6 GB, not 3.5 + 8.5; paint_bake.py's peak 1 GB from four takes.
    Break: score/graph/__init__.py: '    side = "written" if wrote else "unwritten"' -> '    side = "written"' -> a
    take that wrote nothing counted as written: the stopped light take's 21 GB, the failed bakes lowering it to 1 GB.
    Break: score/graph/__init__.py: 'take_mark(key).get("predicted", 0)' -> '0' -> 21 GB less 1, not 29 less 1.
    Break: score/graph/__init__.py: 'for stage, place, process in running.values() if process.is_alive()]' ->
    'for stage, place, process in running.values()]' -> the ended clean node charged its 2 floors.
    Break: score/graph/__init__.py: '        peak = max(peak, memory_floor()) if contained else peak' ->
    '        peak = peak' -> a node that ran a container client keeps its 0.1 floor."""
    monkeypatch.delenv(graph.FLOOR_VARIABLE, raising=False)
    marks = tmp_path / "marks"
    marks.mkdir()
    monkeypatch.setattr(graph, "TAKE_MARKS", marks)
    folders = a_machine(tmp_path / "proc", tmp_path / "cgroups", monkeypatch)
    page, megabyte = os.sysconf("SC_PAGE_SIZE"), 2**20

    # the machine as its readers see it
    share_100 = (300 + 200 + 50 + 100) * megabyte + GIGA // 1024 * 1024  # never the resident sum
    assert graph.trees_held([100, 999]) == {100: share_100, 999: 0}
    # 100's and its exec'd child's VmHWM, the forked worker by its share; 102 and 103 have no status
    high_100 = (10 * GIGA // 1024 + 3 * GIGA // 1024 + GIGA // 1024) * 1024
    assert graph.trees_high([100]) == {100: high_100}
    assert graph.ran_container_client(100) and not graph.ran_container_client(200)
    with monkeypatch.context() as docker:
        docker.setattr(graph.subprocess, "run", lambda *_, **__: subprocess.CompletedProcess([], 0, LISTED, ""))
        found = graph.container_cgroups()
    assert found == [folders["first"], folders["segment"]], found
    monkeypatch.setattr(graph, "CGROUPS_OF", lambda: found)
    room, jobs = graph.container_reading()
    assert room == 26 * GIGA and sorted(kind for kind, _, _ in jobs.values()) == [
        "paint_bake.py", "paint_bake.py", "segment_worker.py"], (room, jobs)
    take_20, take_30 = graph.take_key(["take-20"]), graph.take_key(["take-30"])
    high_20, high_30 = 6 * GIGA // 1024 * 1024, 2 * GIGA // 1024 * 1024
    bakes = graph.container_jobs(folders["first"])
    assert bakes == {take_20: ("paint_bake.py", 5 * GIGA // page * page, high_20),
                     take_30: ("paint_bake.py", 1 * GIGA // page * page, high_30)}, bakes
    assert graph.container_room(folders["first"]) == 20 * GIGA
    assert graph.take_key(["/a", "/b"]) == "148c32fbefbb40c1"  # tools/cloud/blender_cloud.py's test asserts the same

    for row, available, named, running, expected, floor, fits in ROOM:
        monkeypatch.setenv(graph.FLOOR_VARIABLE, named)
        monkeypatch.setattr(graph, "AVAILABLE", lambda available=available: available)
        assert graph.memory_floor() == floor, row
        assert graph.memory_room(running, expected) == fits, row
    monkeypatch.delenv(graph.FLOOR_VARIABLE)

    runner = a_driven_runner({"hangar": "a ship"})
    for row, nodes, this_pc, holds, container, peaks, clients, grown, reserves, available, expected, fits in COMING:
        monkeypatch.setenv(graph.THIS_PC[0], graph.THIS_PC[1] if this_pc else "scaleway")
        monkeypatch.setattr(graph, "HELD", lambda pids, holds=holds: dict.fromkeys(pids, holds))
        monkeypatch.setattr(graph, "HIGH", lambda pids: dict.fromkeys(pids, 0))
        monkeypatch.setattr(graph, "CONTAINED", lambda pid: pid < 14)
        monkeypatch.setattr(graph, "CONTAINER_READ", (lambda: pytest.fail(f"{row}: the container read")) if
                            container == "never" else lambda container=container: None if container is None else
                            (int(container), {}))  # no take seen yet: all its room
        monkeypatch.setattr(graph, "AVAILABLE", lambda available=available: available)
        coming = runner.coming(a_running(*nodes), peaks, {}, dict(clients), grown)
        assert coming == reserves, (row, coming)
        assert graph.memory_room(coming, expected) == fits, row

    for row, peaks, clients, grown, peak, reserve in CLIENT:
        assert graph.client_peak("settle", peaks, clients) == peak, row
        assert graph.client_reserve("settle", peaks, clients, grown) == reserve, row
    assert runner.client_grown() == set() and runner.keep_grown("settle") == runner.client_grown() == {"settle"}

    # node 100 runs a container client on this PC, read through the machine: its tree's peak is kept at once
    monkeypatch.setenv(*graph.THIS_PC)
    for name, reader in (("HELD", graph.trees_held), ("HIGH", graph.trees_high), ("CONTAINED",
                                                                                graph.ran_container_client)):
        monkeypatch.setattr(graph, name, reader)
    monkeypatch.setattr(graph, "CONTAINER_READ", lambda: (0, {}))
    clients, running = {}, a_running(("settle", 100, True))
    assert runner.coming(running, {}, {}, clients)[0] == (high_100, share_100)
    (tmp_path / "proc" / "100" / "status").write_text("Name:\tnode\nVmHWM:\t0 kB\n")  # a later, lower reading
    runner.coming(running, {}, {}, clients)
    assert clients == runner.client_trees() == {"settle": high_100}  # stopped now, no outcome read: still kept
    assert graph.client_peak("settle", runner.peaks(), runner.client_trees()) == high_100

    # a node's stage peak once it ended: one that ran a container client counts as the default at least
    clean = runner.stages["clean"]
    runner.keep_peak("clean", TENTH)
    assert runner.measured(clean, "made: pass", TENTH, False, runner.peaks()) == {"clean": TENTH}
    assert runner.measured(clean, "fresh", TENTH, True, runner.peaks()) == {"clean": FLOOR}
    assert runner.peaks() == {"clean": FLOOR}

    # the container's reserve from the first container's bake takes: none seen yet in any claim, its whole room; seen
    # once, each take TAKE_PEAK (8.5 GB, none of the kind wrote its outputs) less what it holds, each one's highest
    # reading kept under its key at once
    empty = {"written": {}, "unwritten": {}, "open": {}, "slots": 0}
    assert graph.container_reserve(20 * GIGA, bakes, empty) == 20 * GIGA
    bake_run = a_driven_runner({"hangar": "a ship"})
    near = functools.partial(pytest.approx, abs=2 * page)
    assert bake_run.container_growth((20 * GIGA, bakes)) == near(11 * GIGA)  # 3.5 + 7.5
    assert bake_run.container_takes() == {"written": {}, "unwritten": {}, "slots": 2, "open": {
        take_20: ["paint_bake.py", high_20, None], take_30: ["paint_bake.py", high_30, None]}}
    # take 30 ends, its mark saying it wrote its outputs: its 2 GB kept as written, its mark removed; fewer than
    # TAKES_TRUSTED written, so take 20 still grows 3.5 and the idle slot 8.5; never more than the room
    (marks / f"{take_30}.json").write_text(json.dumps({"kind": "paint_bake.py", "wrote": True}))
    alone = {take_20: bakes[take_20]}
    assert bake_run.container_growth((20 * GIGA, alone)) == near(3.5 * GIGA + 8.5 * GIGA)
    kept = bake_run.container_takes()
    assert kept["written"] == {"paint_bake.py": [high_30]} and list(kept["open"]) == [take_20], kept
    assert not (marks / f"{take_30}.json").exists()
    assert bake_run.container_growth((3 * GIGA, alone)) == 3 * GIGA

    # another run's desk: a light take read at 21 GB, then gone with no word (its runner stopped): kept at once, still
    # counted, and SETTLE_SECONDS later settled as a take that wrote nothing, its 21 GB the kind's peak
    take_run = a_driven_runner({"hangar": "a ship"})
    light = graph.take_key(["/base.usda", "/views.json", "/passes"])
    take_run.keep_takes({light: ("light_passes.py", 20 * GIGA, 21 * GIGA)}, 1000.0)
    kept = take_run.keep_takes({}, 1010.0)
    assert kept["open"] == {light: ["light_passes.py", 21 * GIGA, 1010.0]}, kept
    assert graph.take_peak(kept, "light_passes.py") == 21 * GIGA
    kept = take_run.keep_takes({}, 1010.0 + graph.SETTLE_SECONDS)
    assert kept["unwritten"] == {"light_passes.py": [21 * GIGA]} and not kept["open"], kept
    assert graph.take_peak(kept, "light_passes.py") == 21 * GIGA
    # paint_bake.py: six 1 GB takes that failed (wrote false) and four that wrote leave its peak at TAKE_PEAK; a
    # fifth written makes it 1 GB
    for name, wrote in [*((f"failed-{number}", False) for number in range(6)),
                        *((f"wrote-{number}", True) for number in range(5))]:
        key = graph.take_key([name])
        take_run.keep_takes({key: ("paint_bake.py", GIGA, GIGA)}, 2000.0)
        (marks / f"{key}.json").write_text(json.dumps({"kind": "paint_bake.py", "wrote": wrote}))
        kept = take_run.keep_takes({}, 2001.0)
        assert graph.take_peak(kept, "paint_bake.py") == (GIGA if name == "wrote-4" else graph.TAKE_PEAK), name
    # a running take whose mark predicts 29 GB from its inputs reserves 29 GB less the 1 GB it holds
    rendering = graph.take_key(["/garage.usda"])
    (marks / f"{rendering}.json").write_text(json.dumps({"kind": "light_passes.py", "predicted": 29 * GIGA}))
    assert graph.container_reserve(40 * GIGA, {rendering: ("light_passes.py", GIGA, GIGA)},
                                   take_run.container_takes()) == 28 * GIGA


def a_process(proc, pid, parent, resident_pages, pss_kb=None):
    """A process `pid` under `parent` in the fake `proc` folder: its stat line, and its smaps_rollup when `pss_kb`."""
    folder = proc / str(pid)
    folder.mkdir()
    fields = ["S", str(parent)] + ["0"] * 19 + [str(resident_pages)]  # field 22 of stat: resident pages
    (folder / "stat").write_text(f"{pid} (make node) {' '.join(fields)}\n")
    if pss_kb is not None:
        (folder / "smaps_rollup").write_text(f"00400000-ffffffff ---p 00000000 00:00 0  [rollup]\nRss: "
                                             f"{resident_pages * 4} kB\nPss: {pss_kb} kB\nShared_Clean: 0 kB\n")


SHIP_AND_HUB = {"hangar": "a ship", "station": "a hub"}
CLEAN_AND_COUNT = {"clean@hangar", "clean@station", "count@hangar", "count@station"}
ALL_MADE = dict.fromkeys(CLEAN_AND_COUNT, "made")  # made and accepted automatically, its words gathered or not
ALL_FRESH = dict.fromkeys(CLEAN_AND_COUNT, "fresh")

# Drives of clean and count on two places, in turn: a row with briefs drives a new runner on them, a row with None the
# runner before it again. Each row: its name; the briefs; the stage peaks kept before it drives; the memory desk files
# it leaves first ({name: peaks}, None removing one); graph.AVAILABLE's readings in turn (the last kept); what HELD
# reads in the drive's own process and in a node's; --jobs. Then what it pins: each node's outcome; the most nodes and
# the most clean nodes running at once (None where the timing decides); whether it waited for memory (a "memory: "
# line said and more readings taken than the short ones); the reading every node started on; each stage's peak kept
# after it.
MEMORY_DRIVES = (
    ("2 floors less a byte available three times: no node starts on it", SHIP_AND_HUB, {}, {},
     [2 * FLOOR - 1] * 3 + [100 * FLOOR], (0, 0), 4, ALL_MADE, (None, None), True, 100 * FLOOR, {}),
    ("--jobs 1: never two nodes at once", {"hangar": "a ship", "station": "a ship"}, {}, {}, [100 * FLOOR], (0, 0), 1,
     ALL_MADE, (1, 1), False, 100 * FLOOR, {}),
    ("clean's kept 1.5 floors, 0.1 held by each running node, 2.8 available: one clean node at a time", SHIP_AND_HUB,
     {"clean": int(1.5 * FLOOR)}, {}, [2.8 * FLOOR], (TENTH, TENTH), 4, ALL_MADE, (None, 1), True, 2.8 * FLOOR,
     {"clean": int(1.5 * FLOOR), "count": TENTH}),
    ("again, all fresh: each clean node only confirms its record, both at once", None, {}, {}, [2.8 * FLOOR],
     (TENTH, TENTH), 4, ALL_FRESH, (None, 2), False, 2.8 * FLOOR, {"clean": int(1.5 * FLOOR), "count": TENTH}),
    ("0.1 floor a node", SHIP_AND_HUB, {}, {}, [100 * FLOOR], (TENTH, TENTH), 4, ALL_MADE, (None, None), False,
     100 * FLOOR, {"clean": TENTH, "count": TENTH}),
    ("again, the peaks file gone: a node that made nothing keeps no peak", None, {}, {"peaks-made": None},
     [100 * FLOOR], (TENTH, TENTH), 4, ALL_FRESH, (None, None), False, 100 * FLOOR, {}),
    ("again, 2 floors a node: over the default, kept though it made nothing", None, {}, {}, [100 * FLOOR],
     (2 * FLOOR, 2 * FLOOR), 4, ALL_FRESH, (None, None), False, 100 * FLOOR, {"clean": 2 * FLOOR, "count": 2 * FLOOR}),
    ("the drive reads nothing, a node its own 0.2 floor; old RSS-sum and PSS peaks files left at 10 floors",
     SHIP_AND_HUB, {}, {"peaks": {"clean": 10 * FLOOR}, "peaks-pss": {"count": 10 * FLOOR}}, [100 * FLOOR],
     (0, int(0.2 * FLOOR)), 4, ALL_MADE, (None, None), False, 100 * FLOOR,
     {"clean": int(0.2 * FLOOR), "count": int(0.2 * FLOOR)}),
)

# A running clean node's room by its process's `making` flag: confirming its record, CHECK_PEAK; making, clean's peak.
CONFIRMING = ((0, graph.CHECK_PEAK), (1, int(1.5 * FLOOR)))


def test_a_node_starts_only_on_room_for_its_kept_peak_and_each_peak_is_its_own_trees_share(monkeypatch):
    """No node starts while available memory, less what each running node may still take, is short of its stage's kept
    peak beside the floor, and never more than --jobs at once; a node that only confirms its record fresh is expected at
    CHECK_PEAK (2026-11-11: 16 fresh checks held card rows back at their stages' make peaks). Each stage's peak is the
    node's own report of its tree's share, kept beside the store; a measured one never lowers it, a node that made
    nothing keeps none under the default (2026-10-28: quick finish-route-views nodes kept 0.1 GB, and 7 real ones
    started on 38.9 GB), and the old peaks.json (RSS sums) and peaks-pss.json are no longer read.
    Break: score/graph/__init__.py: '                        if not memory_room(coming, expected):' ->
    '                        if False:' -> the first row's nodes start on the short readings.
    Break: score/graph/__init__.py: 'else peaks.get(name, memory_floor()), held[process.pid]))' ->
    'else held[process.pid], held[process.pid]))' -> two clean nodes run at once.
    Break: 'expected = CHECK_PEAK if confirming else' -> 'expected = 0 * CHECK_PEAK if False else' -> the second fresh
    clean node waits; 'not making.value' -> 'False' -> the confirming node reserves its stage peak.
    Break: score/graph/__init__.py: '        if "made: " in did or peak > peaks.get(name, memory_floor()):' ->
    '        if True:' -> clean's and count's 0.1 floor are kept after the peaks file is gone.
    Break: score/graph/__init__.py: 'sending.send((did, max(high[0], HELD([os.getpid()])[os.getpid()]),' ->
    'sending.send((did, 0,' -> the own-report row keeps nothing.
    Break: score/graph/__init__.py: '        path = self.desk("memory", "peaks-made", ".json")\n        return' ->
    '        path = self.desk("memory", "peaks", ".json")\n        return', or -> '"peaks-pss"' -> the own-report row
    reads the old 10 floors."""
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    wait, drive_pid, runner = graph.FORK_WAIT, os.getpid(), None
    for row, briefs, kept, desk, available, (drive_holds, node_holds), jobs, outcomes, most, waited, lowest, peaks \
            in MEMORY_DRIVES:
        runner = a_driven_runner(briefs) if briefs else runner
        for stage, peak in kept.items():
            runner.keep_peak(stage, peak)
        for name, written in desk.items():
            path = runner.desk("memory", name, ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink() if written is None else path.write_text(json.dumps(written))
        taken = faked(monkeypatch, available)
        monkeypatch.setattr(graph, "HELD", lambda pids, drive=drive_holds, node=node_holds: dict.fromkeys(
            pids, drive if os.getpid() == drive_pid else node))
        running, seen, started, start = {}, [0, 0], [], runner.start

        def counted_start(stage, place, threads, given=None, priority=0, start=start):
            started.append(taken[-1] if taken else "nothing read")
            begun = start(stage, place, threads, given, priority)
            running.update(dict.fromkeys(begun, stage.name))
            seen[:] = max(seen[0], len(running)), max(seen[1], list(running.values()).count("clean"))
            return begun

        def counted_wait(connections, timeout=None):
            finished = wait(connections, timeout=timeout)
            for connection in finished:
                running.pop(connection)
            return finished
        runner.start = counted_start
        monkeypatch.setattr(graph, "FORK_WAIT", counted_wait)
        said = []
        found = runner.drive(PLACES, say=said.append, jobs=jobs)
        assert {node: "made" if did.startswith("made: ") and did.endswith(", accepted automatically") else did
                for node, did in found.items()} == outcomes, (row, found)
        assert [pinned if pinned is None else got for pinned, got in zip(most, seen)] == list(most), (row, seen)
        memory_lines = [line for line in said if line.startswith("memory: ")]
        assert (bool(memory_lines) and len(taken) >= len(available)) == waited, (row, said, len(taken))
        assert set(started) == {lowest}, (row, started)
        assert runner.peaks() == peaks, (row, runner.peaks())

    monkeypatch.setattr(graph, "HELD", lambda pids: dict.fromkeys(pids, TENTH))
    flag = types.SimpleNamespace(value=0)
    alive = {0: (types.SimpleNamespace(name="clean", grain="place"), "hangar",
                 types.SimpleNamespace(pid=11, is_alive=lambda: True, making=flag))}
    for making, expected in CONFIRMING:
        flag.value = making
        assert runner.coming(alive, {"clean": int(1.5 * FLOOR)}, {}, {}) == [(expected, TENTH)], making


def make_mark(inputs, out, seed, params):
    (out / "mark.txt").write_text("marked")


def make_late(inputs, out, seed, params):
    time.sleep(0.4)  # the big nodes wait many turns meanwhile
    (out / "mark.txt").write_text("marked")


def make_briefly(inputs, out, seed, params):
    time.sleep(0.2)  # the drive takes many turns meanwhile
    (out / "mark.txt").write_text("marked")


def make_queued(inputs, out, seed, params):
    """Its process's queue priority and place, as the drive handed them (Runner.node_process)."""
    (out / "clean.txt").write_text(f"{os.environ.get('SCORE_QUEUE_PRIORITY')} {os.environ.get('SCORE_QUEUE_PLACE')}")


# The drive's started nodes (a folder the drive's starts mark, the count of nodes it should hold at once), as a
# drive in cpus_beside sets them before it forks its nodes.
STARTED = [None, 0]


def make_slow(inputs, out, seed, params):
    """A remote node's jobs on the cluster: the cpu nodes start meanwhile. It holds until the drive has started every
    node it should hold at once, or for 3 s when the drive kept some out."""
    folder, every = STARTED
    deadline = time.monotonic() + 3
    while len(list(folder.iterdir())) < every and time.monotonic() < deadline:
        time.sleep(0.02)
    (out / "mark.txt").write_text("marked")


def make_big(inputs, out, seed, params):
    held = bytearray(BIG)  # zero-filled: every page touched, so its VmHWM counts it
    time.sleep(0.4)  # the drive reads it meanwhile, its next node waiting on the --jobs slot
    (out / "mark.txt").write_text(f"marked {len(held)}")


BIG = 300 * 2**20


def test_a_node_waiting_on_a_claim_holds_no_job_slot_and_its_stage_starts_no_other(
        monkeypatch, tmp_path):
    """2026-10-29: all 8 job slots held by surfaces-bake rows, 3 running a take and 5 waiting for one, about 60 ready
    rows of other stages kept out; then the slots the waiters freed went to yet more waiting bake rows. Two slow
    `late` nodes, every running one waiting on a claim, and two slow `other` nodes that claim nothing, at --jobs 1:
    a waiting late node holds no slot, so an other node runs beside it (two at once), and while it waits no second late
    node starts (one at once); off this PC the same, since a claim waiting on a warm pool machine marks itself too
    (2026-11-06, checkout 36 on the conductor: 15 of 16 slots held by bake clients waiting on 3 pool machines). A fresh
    mark of a process in a node's tree makes it a waiter, a stale one does not.
    Break: score/graph/__init__.py: 'if busy + len(ready) >= jobs or queued[stage.name] or (' ->
    'if busy + len(ready) >= jobs or (' -> two late nodes at once on this PC.
    #76, 2026-11-07: the slots were held by nodes whose jobs were on the cluster, no score pod Running. A node waiting
    on a cluster run (submitter.watch's mark in CLUSTER_WAITING) holds no slot either, up to REMOTE_EXCUSED (48) apart
    from the claims' five: at --jobs 16, 20 `remote` nodes all waiting on the cluster and 4 `cpu` nodes beside them run
    at once; 60 cluster waiters excuse 48; a waiter whose mark is gone (its run returned) holds its slot again.
    Break: score/graph/__init__.py: 'min(claim_waiting, WAITERS_EXCUSED) - min(cluster_waiting, remote_excused())' ->
    'min(claim_waiting + cluster_waiting, WAITERS_EXCUSED)' -> at most one cpu node beside the 20 remote ones.
    #76 build spec S8: under the box's queue up to IN_FLIGHT waiters hold no slot (20 remote nodes, REMOTE_EXCUSED
    scaled from 48 to 16, and 16 cpu nodes at once at --jobs 16); a node's queue priority is the count of waiting
    nodes that read it, through any others, handed to its process; the drive writes its expected work by image kind
    for the queue, and removes it at its end.
    Break: score/graph/__init__.py: 'min(cluster_waiting, remote_excused())' -> 'min(cluster_waiting, REMOTE_EXCUSED)'
    (pod waiters counted as slots past 16) -> 12 cpu nodes beside the 20. Break: 'order.get(node, 0)' -> '0'.
    Break: score/graph/__init__.py: 'pod_expect([stage for stage, _ in waiting])' -> 'pass'."""
    briefs = {"hangar": "a ship", "station": "a hub"}
    late = graph.Stage("late", "place", make_briefly, TEXT, PASSES)
    other = graph.Stage("other", "place", make_briefly, TEXT, PASSES)
    faked(monkeypatch, [100 * FLOOR])
    monkeypatch.setattr(graph, "HELD", lambda pids: dict.fromkeys(pids, 0))
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    stage_of = {}  # pid: the stage its node runs
    monkeypatch.setattr(graph, "CLAIM_WAITERS", lambda pids: {pid for pid in pids if stage_of[pid] == "late"})
    wait = graph.FORK_WAIT

    def most_at_once(runner):
        running, most, start = {}, [0, 0], runner.start

        def counted_start(stage, place, threads, given=None, priority=0):
            begun = start(stage, place, threads, given, priority)
            for pipe, (_, _, process) in begun.items():
                stage_of[process.pid], running[pipe] = stage.name, stage.name
            most[0] = max(most[0], len(running))
            most[1] = max(most[1], list(running.values()).count("late"))
            return begun

        def counted_wait(connections, timeout=None):
            finished = wait(connections, timeout=timeout)
            for connection in finished:
                running.pop(connection)
            return finished
        runner.start = counted_start
        monkeypatch.setattr(graph, "FORK_WAIT", counted_wait)
        found = runner.drive(tuple(briefs), say=quiet, jobs=1)
        assert set(found) == {f"{name}@{place}" for place in briefs for name in ("late", "other")}, found
        return tuple(most)
    monkeypatch.setenv(*graph.THIS_PC)
    assert most_at_once(a_runner(a_world(briefs), a_store(), (late, other))) == (2, 1)
    monkeypatch.setenv(graph.THIS_PC[0], "scaleway")  # off this PC the same: a warm pool's waiting claim marks too
    assert most_at_once(a_runner(a_world(briefs), a_store(), (late, other))) == (2, 1)
    monkeypatch.setattr(graph, "WAITING_CLAIMS", tmp_path)
    (tmp_path / str(os.getpid())).touch()
    assert graph.claim_waiters([os.getppid()]) == {os.getppid()}
    os.utime(tmp_path / str(os.getpid()), (0, time.time() - graph.WAIT_FRESH_SECONDS - 1))
    assert graph.claim_waiters([os.getppid()]) == set()

    # cluster waits: 20 remote nodes waiting on the cluster and 4 cpu nodes, --jobs 16
    remote = graph.Stage("remote", "place", make_slow, TEXT, PASSES)
    cpu = graph.Stage("cpu", "place", make_slow, TEXT, PASSES)
    monkeypatch.setattr(graph, "CLAIM_WAITERS", lambda pids: set())
    monkeypatch.setattr(graph, "CLUSTER_WAITERS", lambda pids: {pid for pid in pids if stage_of.get(pid) == "remote"})

    def cpus_beside(remotes, cpus):
        """How many cpu nodes ran beside `remotes` remote nodes all waiting on the cluster, at --jobs 16."""
        places = {f"place{number}": f"a place {number}" for number in range(remotes)}
        runner = a_runner(a_world(places), a_store(), (remote, cpu))
        beside, start, both = [0], runner.start, {}

        def counted_start(stage, place, threads, given=None, priority=0):
            begun = start(stage, place, threads, given, priority)
            for pipe, (_, _, process) in begun.items():
                stage_of[process.pid], both[pipe] = stage.name, stage.name
            if list(both.values()).count("remote") == len(places):
                beside[0] = max(beside[0], list(both.values()).count("cpu"))
            for _, _, process in begun.values():
                (STARTED[0] / str(process.pid)).touch()  # counted: its node may end
            return begun

        def counted_wait(connections, timeout=None):
            finished = wait(connections, timeout=timeout)
            for connection in finished:
                both.pop(connection)
            return finished
        runner.start = counted_start
        monkeypatch.setattr(graph, "FORK_WAIT", counted_wait)
        some = [f"cpu@{place}" for place in list(places)[:cpus]]
        STARTED[:] = [pathlib.Path(tempfile.mkdtemp()), remotes + cpus]
        found = runner.drive(tuple(places), say=quiet, jobs=16, whole=False, only=["remote", *some])
        assert set(found.values()) == {ACCEPTED} and len(found) == remotes + cpus, found
        return beside[0]
    assert cpus_beside(20, 4) == 4
    assert graph.slots_held(70, 0, 60) == 22 and graph.slots_held(70, 8, 60) == 17
    # #76 S8: under the box's queue (SCORE_K8S_QUEUE) it admits within the quota, so up to IN_FLIGHT (400) waiters,
    # pod makes among them, hold no slot: 20 remote nodes, past REMOTE_EXCUSED (48 scaled to 16: fewer nodes forked),
    # and 16 cpu nodes beside them.
    monkeypatch.setenv("SCORE_K8S_QUEUE", "1")
    with monkeypatch.context() as scaled:
        scaled.setattr(graph, "REMOTE_EXCUSED", 16)
        assert cpus_beside(20, 16) == 16
    assert graph.slots_held(216, 0, 200) == 16 and graph.slots_held(500, 0, 450) == 100
    monkeypatch.delenv("SCORE_K8S_QUEUE")
    # A node's queue priority is how many waiting nodes read it, through any number of others (pod.downstream), handed
    # to its process (SCORE_QUEUE_PRIORITY, SCORE_QUEUE_PLACE); the drive writes what it expects for the queue's
    # workers, {image kind: waiting nodes} (pod.expect), gone once it ends.
    from score.graph import pod
    reads = {"b@x": ["a@x"], "c@x": ["b@x"], "d@x": ["a@x", "b@x"], "e@y": ["z"]}
    assert pod.downstream(reads, ["a@x", "b@x", "z", "c@x"]) == {"a@x": 3, "b@x": 2, "z": 1, "c@x": 0}
    queued = graph.Stage("clean", "place", make_queued, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"})
    tail = graph.Stage("tail", "place", make_briefly, TEXT, PASSES, after={"count": READS})
    monkeypatch.setattr(graph, "pod_dispatching", lambda: True)
    monkeypatch.setattr(graph, "FORK_WAIT", wait)
    monkeypatch.setattr(pod, "IMAGE_OF", {"count": "runner"})
    monkeypatch.setattr(pod, "QUEUE_FOLDER", tmp_path / "queue")
    expected, real_expect = [], pod.expect
    monkeypatch.setattr(pod, "expect", lambda waiting: expected.append(
        json.loads(path.read_text()) if (path := real_expect(waiting)).exists() else None))
    store = a_store()
    found = a_runner(a_world({"hangar": "a ship", "station": "a hub"}), store, (queued, COUNT, tail)).drive(
        ("hangar", "station"), say=quiet, jobs=4)
    assert set(found.values()) == {ACCEPTED}, found
    assert accepted_text(store, "clean@hangar", "clean.txt") == "2 hangar", accepted_text(store, "clean@hangar", "clean.txt")
    assert expected[0] == {"runner": 2} and not list((tmp_path / "queue" / "expected").iterdir())
    monkeypatch.setattr(graph, "CLUSTER_WAITING", tmp_path / "cluster")
    (tmp_path / "cluster").mkdir()
    (tmp_path / "cluster" / str(os.getpid())).touch()
    assert graph.cluster_waiters([os.getppid()]) == {os.getppid()}
    (tmp_path / "cluster" / str(os.getpid())).unlink()  # its run returned: it holds its slot again
    assert graph.cluster_waiters([os.getppid()]) == set()


def test_a_ready_node_too_large_for_memory_waits_alone_and_the_ones_after_it_that_fit_start(monkeypatch):
    """2026-10-28: one ready node at the head that did not fit held 122 small ready nodes behind it, five of eight
    slots empty for 29 min; 2026-10-29: once it had waited ten turns it held every node behind it again (108 ready,
    2 running). big (kept peak 3 floors) comes before late (0.1 floor, 0.4 s a node) and small (0.1 floor, reads
    late), 2.5 floors available until both small nodes started (or 3 s): late starts first, small once late stands,
    though big has waited many turns by then, and big once the room is there.
    Break: score/graph/__init__.py: '                            continue\n                        waiting.remove'
    -> '                            break\n                        waiting.remove' -> big starts first.
    On a machine whose whole memory cannot hold big beside the floor (3.5 floors), big is refused at once with why
    and the run ends; late and small still run (2026-11-02: a plan row run waited ten hours on the idle conductor).
    Break: score/graph/__init__.py: '    if expected + memory_floor() <= TOTAL():' -> '    if True:' -> the run
    waits for ever (here: the 3 s deadline passes with big still waiting). A stage never measured on such a machine
    (its peak the floor's guess) is not refused: its nodes run one at a time, alone (2026-11-03: the conductor refused
    its 0.16 GB plan rows at the 6 GB guess). Break: score/graph/__init__.py: 'if refused and stage.name not in
    peaks:' -> 'if False:' -> the unmeasured nodes are refused."""
    monkeypatch.delenv(graph.FLOOR_VARIABLE, raising=False)
    monkeypatch.setattr(graph, "HELD", lambda pids: dict.fromkeys(pids, 0))
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    files = {"brief": "{data}/{place}/brief.txt"}
    big = graph.Stage("big", "place", make_mark, TEXT, PASSES, files=files)
    late = graph.Stage("late", "place", make_late, TEXT, PASSES, files=files)
    small = graph.Stage("small", "place", make_mark, TEXT, PASSES, after={"late": READS})
    runner = a_runner(a_world({"hangar": "a ship", "station": "a hub"}), a_store(), (big, late, small))
    for stage, peak in (("big", 3 * FLOOR), ("late", int(0.1 * FLOOR)), ("small", int(0.1 * FLOOR))):
        runner.keep_peak(stage, peak)
    started, start, until = [], runner.start, time.monotonic() + 3
    runner.start = lambda stage, place, threads, given=None, priority=0: started.append(stage.name) or start(stage, place, threads, given, priority)
    monkeypatch.setattr(graph, "AVAILABLE", lambda: 2.5 * FLOOR if started.count("small") < 2 and
                        time.monotonic() < until else 100 * FLOOR)
    found = runner.drive(PLACES, say=quiet, jobs=4)
    assert set(found.values()) == {ACCEPTED} and len(found) == 6, found
    assert started == ["late", "late", "small", "small", "big", "big"], started

    monkeypatch.setattr(graph, "TOTAL", lambda: 3.5 * FLOOR)
    deadline = time.monotonic() + 3  # past it room appears, so a waiting run ends and the timing check fails
    monkeypatch.setattr(graph, "AVAILABLE", lambda: 2.5 * FLOOR if time.monotonic() < deadline else 100 * FLOOR)
    small_machine = a_runner(a_world({"hangar": "a ship", "station": "a hub"}), a_store(), (big, late, small))
    for stage, peak in (("big", 3 * FLOOR), ("late", int(0.1 * FLOOR)), ("small", int(0.1 * FLOOR))):
        small_machine.keep_peak(stage, peak)
    said, began = [], time.monotonic()
    found = small_machine.drive(PLACES, say=said.append, jobs=4)
    assert time.monotonic() - began < 3, "a node that can never fit was waited for"
    refused = {node: line for node, line in found.items() if node.startswith("big@")}
    assert len(refused) == 2 and all("can never start here" in line and "21.0 GB in all" in line
                                     for line in refused.values()), refused
    assert all(found[node] == ACCEPTED for node in found if not node.startswith("big@")), found

    monkeypatch.setattr(graph, "TOTAL", lambda: 1.5 * FLOOR)  # the guess and the floor beside it pass the machine
    monkeypatch.setattr(graph, "AVAILABLE", lambda: 1.2 * FLOOR)
    fresh = graph.Stage("fresh", "place", make_mark, TEXT, PASSES, files=files)
    guessed = a_runner(a_world({"hangar": "a ship", "station": "a hub"}), a_store(), (fresh,))
    found = guessed.drive(PLACES, say=quiet, jobs=4)
    assert set(found.values()) == {ACCEPTED} and len(found) == 2, found


# Drives of a `client` stage on two places at --jobs 1, its kept stage peak 2 floors, 100 floors available until its
# first node starts and 2.5 floors after it until a 1.2 s deadline. Each row: its name; on this PC; whether its nodes'
# trees ran a container client when they ended (ran_container_client); the client tree kept before it drives (None:
# none); its make. Then what it pins: the second node started before the deadline; the least the kept client tree
# then is (None: none kept); the grown client stages kept.
CLIENT_DRIVES = (
    ("this PC, each node ran a client: the next is expected at the first's own tree, not the stage peak", True, True,
     None, make_briefly, True, 0, {"client"}),
    ("this PC, a stage that once ran a client (1 MB kept), its nodes holding 300 MB each and running none: their real "
     "trees are read while they run, the container never; grown by none, the next waits for its stage peak", True,
     False, 2**20, make_big, False, BIG + 1, set()),
    ("off this PC, each node ran a client: the next waits for its stage peak's room, no tree kept", False, True, None,
     make_briefly, False, None, set()),
)


@pytest.mark.parametrize("row", CLIENT_DRIVES, ids=[row[0] for row in CLIENT_DRIVES])
def test_on_this_pc_a_container_clients_node_is_expected_and_kept_at_its_own_read_tree(row, monkeypatch):
    """2026-10-29: two bakes ran with a Blender turn free and 37 GB available, and no third started: a new bake row
    was expected at its stage's 8 GB peak on top of the container's reserve, which already counts that idle turn. On
    this PC a client stage's next node is expected at what the first's own tree held, so it starts at once; off this
    PC, or before a node of the stage made its output (client_grown), it waits for its stage peak's room.
    Round 28, 2026-10-30: settle nodes held 12 and 8 GB in their own trees for minutes, client-trees.json kept 3.6
    GB: the drive took a node for a container client only while a blender_cloud.py ran under it, and settle's 12 GB
    is its own work outside its drop (a kept drop runs none). A stage whose nodes once ran a client: the drive's
    readings of the node's real tree raise the kept tree past 300 MB, and the container is never read for them (round
    29, 2026-10-30: such a settle node reserved the container's whole room beside its own tree).
    Break: score/graph/__init__.py: '    return clients[stage] if stage in clients else peaks.get(' ->
    '    return peaks.get(' -> the first row's second node waits for the deadline.
    Break: score/graph/__init__.py: 'clients = self.keep_client_tree(stage.name, tree)' ->
    'clients[stage.name] = tree' -> the first row keeps no tree for the next run.
    Break: score/graph/__init__.py: 'if on_this_pc() and (stage.name in clients or CONTAINED(process.pid))}' ->
    'if on_this_pc() and CONTAINED(process.pid)}' -> the second row keeps 1 MB.
    Break: score/graph/__init__.py: 'reading = CONTAINER_READ() if calling else None' ->
    'reading = CONTAINER_READ() if users else None' -> the container is read in the second row."""
    _, this_pc, ran_client, kept_before, make, soon, kept_over, grown = row
    monkeypatch.delenv(graph.FLOOR_VARIABLE, raising=False)
    monkeypatch.setenv(*graph.THIS_PC) if this_pc else monkeypatch.setenv(graph.THIS_PC[0], "scaleway")
    monkeypatch.setattr(graph, "HELD", lambda pids: dict.fromkeys(pids, 0))
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    monkeypatch.setattr(graph, "CONTAINED", lambda pid: False)  # no client runs now: the running ones charge peaks
    monkeypatch.setattr(graph, "ran_container_client", lambda root: ran_client)
    read = []
    monkeypatch.setattr(graph, "CONTAINER_READ", lambda: read.append(1))  # this PC's own container is never touched
    client = graph.Stage("client", "place", make, TEXT, PASSES)
    runner = a_runner(a_world({"hangar": "a ship", "station": "a hub"}), a_store(), (client,))
    runner.keep_peak("client", 2 * FLOOR)
    if kept_before is not None:
        runner.keep_client_tree("client", kept_before)
    started, start = [], runner.start  # the deadline 1.2 s after the first start: a slow first fork waits on none
    runner.start = lambda stage, place, threads, given=None, priority=0: started.append(time.monotonic()) or start(
        stage, place, threads, given, priority)
    monkeypatch.setattr(graph, "AVAILABLE", lambda: 100 * FLOOR if not started else
                        2.5 * FLOOR if time.monotonic() < started[0] + 1.2 else 100 * FLOOR)
    found = runner.drive(("hangar", "station"), say=quiet, jobs=1)
    assert set(found.values()) == {ACCEPTED} and len(started) == 2, found
    trees, until = runner.client_trees(), started[0] + 1.2
    assert (started[1] < until, trees.get("client", -1) >= kept_over if kept_over is not None else
            "client" not in trees, runner.client_grown(), read) == (soon, True, grown, []), (started, until, trees)


def a_container_job(proc, sshd, session, kind, resident_gb, high_gb):
    """A job in the fake `proc` folder: its ssh session `session` under the container's sshd (pid `sshd`), and one
    Blender running `kind` under it, `resident_gb` resident now and `high_gb` its VmHWM, its script's argument
    `take-<session>` (its take key: take_key(["take-<session>"]))."""
    page = os.sysconf("SC_PAGE_SIZE")
    a_process(proc, session, sshd, 0)
    (proc / str(session) / "cmdline").write_bytes(b"sshd: root@notty\0")
    (proc / str(session) / "status").write_text("Name:\tsshd\nVmHWM:\t0 kB\n")
    a_process(proc, session + 1, session, int(resident_gb * GIGA) // page)
    (proc / str(session + 1) / "cmdline").write_bytes(b"/root/blender/blender\0-b\0--python\0/r/%s\0--\0take-%d\0" %
                                                      (kind.encode(), session))
    (proc / str(session + 1) / "status").write_text(f"Name:\tblender\nVmHWM:\t{int(high_gb * GIGA) // 1024} kB\n")


def make_marked(name):
    """A stage `name` reading its place's brief, its make writing a mark (count reads it as clean's clean.txt)."""
    def make(inputs, out, seed, params):
        (out / "clean.txt").write_text("marked")
    return graph.Stage(name, "place", make, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"})


def test_an_input_is_hashed_again_once_it_changed_and_never_kept_while_it_just_changed(tmp_path, monkeypatch):
    """A settled file's hash is kept and read once; the same size rewritten is hashed anew; a file changed within
    SETTLED_NS is never kept. Break: score/graph/__init__.py: 'found.st_size, found.st_mtime_ns, found.st_ctime_ns)'
    -> 'found.st_size)' -> the rewritten file keeps its old hash."""
    monkeypatch.setattr(graph, "HASHED", {})
    read, hashed = [], graph.file_hash
    monkeypatch.setattr(graph, "file_hash", lambda path: read.append(path) or hashed(path))
    folder = tmp_path / "inputs"
    folder.mkdir()
    (folder / "a.json").write_text("aaaa")
    settled = time.time_ns() - 10 * graph.SETTLED_NS
    os.utime(folder / "a.json", ns=(settled, settled))
    later = time.time_ns() + 10 * graph.SETTLED_NS
    monkeypatch.setattr(graph.time, "time_ns", lambda: later)  # its ctime (now) settled too
    first = graph.source_hash(folder)
    assert graph.source_hash(folder) == first and len(read) == 1, read
    kept = os.stat(folder / "a.json").st_ctime_ns
    while os.stat(folder / "a.json").st_ctime_ns == kept:  # a file's times tick with the kernel's coarse clock: a
        time.sleep(0.001)  # rewrite in the same tick as the faked-settled write keeps its ctime (a real kept file
        (folder / "a.json").write_text("bbbb")  # settled SETTLED_NS before any rewrite)
        os.utime(folder / "a.json", ns=(settled, settled))  # the same size and mtime: only its ctime moved
    second = graph.source_hash(folder)
    assert second != first and second == graph.listing_hash({"a.json": hashed(folder / "a.json")})
    monkeypatch.undo()
    monkeypatch.setattr(graph, "HASHED", {})
    monkeypatch.setattr(graph, "file_hash", lambda path: read.append(path) or hashed(path))
    (folder / "a.json").write_text("cccc")  # changed just now: read every time, never kept
    graph.source_hash(folder), graph.source_hash(folder)
    assert len(read) == 4 and not graph.HASHED, read

# --- a run's end: one result line, every process it started ended, what it held released (score/__main__.py) -------

@contextlib.contextmanager
def logs_in_tmp():
    """A detached run's logs in a folder of the test's own, never $PROPS_HOME/logs; that folder."""
    kept, runs.LOGS = runs.LOGS, pathlib.Path(tempfile.mkdtemp())
    try:
        yield runs.LOGS
    finally:
        runs.LOGS = kept


def detached(argv):
    """`score run --detach` of a Python command: (what it printed, its log), once the log has its result line."""
    from score import __main__ as command
    printed = io.StringIO()
    started = time.time()
    with contextlib.redirect_stdout(printed), logs_in_tmp() as logs:
        command.detach(["-c", *argv, command.DETACH])
    assert time.time() - started < 2.5, time.time() - started  # returns at once
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    assert log.parent == logs and printed.getvalue().splitlines()[-1].startswith("detached: started pid="), log
    return printed.getvalue(), log


def wait_for(path, text, within=60):
    deadline = time.time() + within
    while text not in (path.read_text() if path.exists() else "") and time.time() < deadline:
        time.sleep(0.1)
    return path.read_text().splitlines() if path.exists() else []


def test_a_run_started_as_a_script_imports_the_tools_library():
    """Benchmark 2026-10-22: `python score/__main__.py` put score/ first on the path, so `import library` found
    score/library and earth-seed failed on it.
    Break: score/__main__.py: 'sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != REPO / "score"]' -> 'pass'"""
    done = ahead("test_a_run_started_as_a_script_imports_the_tools_library")
    assert done.stdout.strip().endswith("tools/props/library/library.py"), done.stdout + done.stderr[-2000:]


@run_ahead("test_a_run_started_as_a_script_imports_the_tools_library")
def a_script_run():
    """score/__main__.py run as a script, then `import library`: the process."""
    probe = ("import runpy, sys; runpy.run_path(sys.argv[1], run_name='probe'); import library; "
             "print(library.__file__)")
    return subprocess.run([sys.executable, "-c", probe, str(REPO / "score/__main__.py")], cwd=REPO / "score",
                          capture_output=True, text=True, timeout=110, env=ENVIRON)


# A run in miniature takes score/__main__ for its run machinery alone: score.stages stands as its bare package (its
# modules importable, its stage tables never loaded, 1.6 s of imports a process); no part of a run's stop reads them.
MAIN_ALONE = """
import pathlib, sys, types
sys.path.insert(0, sys.argv[1])
import score
score.stages = sys.modules["score.stages"] = types.ModuleType("score.stages")
score.stages.__path__ = [str(pathlib.Path(sys.argv[1]) / "score" / "stages")]
"""
# A `score run` in miniature: it becomes a run with score/__main__'s stop handling, forks a node that waits, and
# starts a batch that stops on SIGTERM and one that ignores it; it writes its run id and every pid.
STOPPED_RUN = MAIN_ALONE + """
import json, os, pathlib, signal, subprocess, sys, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command
from score.adapters import compute
folder = pathlib.Path(sys.argv[2])
command.STOP_GRACE_SECONDS = 1
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


def a_run_home(prefix):
    folder = pathlib.Path(tempfile.mkdtemp(prefix=prefix))
    return folder, {**ENVIRON, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}


# A cloud batch holding three machines, each deleted through batch.delete_machine taking argv[3] seconds; it writes
# "ready" once its stop handler is in.
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
# A `score run` in miniature whose one node runs SLOW_BATCH (argv[5]) from tools/cloud, its output piped to the node
# as a stage's subprocess.run does; the run's grace is argv[3] seconds, each delete argv[4]; with argv[6], the node's
# main thread runs no handler for that many seconds after the batch starts (long C code: its signals wait).
GROUP_RUN = MAIN_ALONE + """
import json, os, pathlib, signal, subprocess, sys, threading, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command, graph
from score.adapters import compute
folder, cloud = pathlib.Path(sys.argv[2]), str(pathlib.Path(sys.argv[1]) / "tools/cloud")
command.STOP_GRACE_SECONDS = float(sys.argv[3])
runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))


def drive():
    leader = os.getpid()
    (folder / "reservations.json").write_text(json.dumps({compute.graph.now(): {"euros": 2.0,
                                                                                 "run": os.environ[command.RUN_ID]}}))
    if os.fork() == 0:  # a node, as Runner.start forks one
        threading.Thread(target=graph.watch_runner, args=(leader, 0.2), daemon=True).start()
        batch = subprocess.Popen([sys.executable, "-c", sys.argv[5], cloud, str(folder), sys.argv[4]],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if len(sys.argv) > 6:
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


# A shell pipeline's later stage (`... | score run`) in a session of its own, a pseudo-terminal its controlling
# terminal: argv[2] "becomes" checks it holds the terminal as a run; "ends" checks a whole run gives it back.
PIPELINE_RUN = MAIN_ALONE + """
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
    if sys.argv[2] == "becomes":
        command.become_run()
        os._exit(0 if os.tcgetpgrp(terminal) == os.getpid() else 3)
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


THREE = ["machine-0", "machine-1", "machine-2"]
# How a run ends, as data: (row id, its world: STOPPED_RUN's mode, GROUP_RUN's grace, delete seconds and busy seconds,
# PIPELINE_RUN's case or a detached run's Python command, how it is stopped, what is seen). "said" must be in its output, "unsaid" not; "deleted" are the machines its
# batch deleted; "held" the runs whose reservations stand once it and its cloud tools ended.
STOP_CASES = [
    ("a run sent SIGTERM alone ends every process it started", ("stopped", "waits"), "alone",
     {"exit": 143, "said": ["score run: stopped by signal 15", "SIGKILL to 1 processes"], "alive at the stop": True,
      "alive after": [], "held": ["other"]}),
    ("a run whose drive raised releases only its reservations", ("stopped", "fails"), None,
     {"exit": 1, "said": ["the drive fell over"], "held": ["other"]}),
    ("SIGINT to its group gives its batch one stop", ("group", 30, 0.3), "group SIGINT", {"deleted": THREE}),
    ("SIGHUP to its group gives its batch one stop", ("group", 30, 0.3), "group SIGHUP", {"deleted": THREE}),
    ("SIGTERM to its group gives its batch one stop", ("group", 30, 0.3), "group SIGTERM", {"deleted": THREE}),
    ("SIGTERM to its group while its node's main thread is busy", ("group", 30, 0.8, "2"), "group SIGTERM busy",
     {"deleted": THREE}),
    # 1 s grace, 3 deletes of 1.2 s each (beside other tests: room for a slow start): the run ends first, holding its
    # reservation, and the batch it spared deletes on, never SIGKILLed
    ("SIGTERM to the run alone passes its stop on and holds its reservations until its cloud tools ended",
     ("group", 1, 1.2), "alone",
     {"unsaid": ["SIGKILL"], "still deleting as it ended": True, "held as it ended": 1, "deleted": THREE, "held": [],
      "runs": []}),
    ("a run late in a shell pipeline holds the terminal as a run", ("pipeline", "becomes"), None, {"exit": 0}),
    ("a run late in a shell pipeline gives the terminal back as it ends", ("pipeline", "ends"), None, {"exit": 0}),
    # detached runs (score run --detach of a Python command), started side by side in this process (they patch its
    # log folder): "result" is its log's last line up to its minutes
    ("a detached run that ends by itself ends its log with its result line",
     ("detached", "import time; time.sleep(0.2); print('the run went on')"), None,
     {"log first": "the run went on", "result": "detached: ok exit=0", "log named": True}),
    ("a detached run another run's registration refused ends with the refusal as its line",
     ("detached", "import sys; print('refused: run pid 7 holds the store', file=sys.stderr); "
                  f"sys.exit({stopped.REFUSED})"), None,
     {"said": ["may still be refused"], "result": f"detached: refused: run pid 7 holds the store exit={stopped.REFUSED}",
      "log named": True}),
    ("a detached run whose group was sent SIGTERM ends its log with its stop as its line",
     ("detached", "import time; print('working', flush=True); time.sleep(60)"), "group SIGTERM",
     {"result": "detached: stopped by signal 15 exit=143", "log named": True}),
]


def a_detached_run_ended(started, how):
    """A detached run `started` (detached: what it printed, its log), stopped `how` (None: it ends by itself), what
    its log showed once it had its result line."""
    printed, log = started
    if how:
        wait_for(log, "working", 30)
        os.killpg(int(printed.split("pid=")[1].split()[0]), getattr(signal, how.split()[1]))  # the session it started
    lines = wait_for(log, "detached:", 60 if how is None else 30)
    return {"output": printed, "log first": lines[0], "result": lines[-1].partition(" minutes=")[0],
            "log named": f"log={log}" in lines[-1]}


def a_run_stopped(world, how):
    """One STOP_CASES world started in a session of its own (a pipeline's in a pseudo-terminal too) and stopped `how` (None: it ends by itself), what was seen
    once it and its cloud tools ended (reservations released within 30 s, else as they stand)."""
    pids = []
    if world[0] == "stopped":
        folder, environment = a_run_home(world[1] + "-run-")
        run = subprocess.Popen([sys.executable, "-c", STOPPED_RUN, str(REPO), str(folder), world[1]], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        if how:
            wait_for(folder / "pids.json", "pids")
            pids = json.loads((folder / "pids.json").read_text())["pids"]
    elif world[0] == "pipeline":
        folder, environment = a_run_home("pipeline-")
        run = subprocess.Popen([sys.executable, "-c", PIPELINE_RUN, str(REPO), world[1]], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        seen = {"exit": run.wait(timeout=60)}  # it starts nothing and holds no reservation: its exit is its answer
        seen["output"], _ = run.communicate(timeout=60)
        return seen
    else:
        folder, environment = a_run_home("group-run-")
        run = subprocess.Popen([sys.executable, "-c", GROUP_RUN, str(REPO), str(folder), *map(str, world[1:3]),
                                SLOW_BATCH, *world[3:]], env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
        wait_for(folder / "ready", "ready")
        assert (folder / "ready").exists(), "the fake batch never started"
    seen = {"alive at the stop": all(map(alive, pids))}
    stopped_at = time.time()
    if how == "alone":
        run.send_signal(signal.SIGTERM)  # to the run's pid alone, not its group: it passes its stop on itself
    elif how:
        if how.endswith("busy"):
            time.sleep(0.5)  # the node's main thread is in its stretch now
        os.killpg(run.pid, getattr(signal, how.split()[1]))
    seen["exit"] = run.wait(timeout=60)  # its output's pipe stays open while a node it spared still runs
    reservations, deletes = folder / "reservations.json", folder / "deletes.txt"
    seen["deleted as it ended"] = len(deletes.read_text().split() if deletes.exists() else [])
    seen["held as it ended"] = len(json.loads(reservations.read_text()))
    seen["output"], _ = run.communicate(timeout=60)
    while any(map(alive, pids)) and time.time() < stopped_at + 35:
        time.sleep(0.2)
    seen["alive after"] = [pid for pid in pids if alive(pid)]
    if world[0] == "group":
        wait_for(folder / "batch.log", "", 60)
        deadline = time.time() + 30
        while time.time() < deadline and json.loads(reservations.read_text()):
            time.sleep(0.1)
    seen["deleted"] = deletes.read_text().split() if deletes.exists() else []
    seen["held"] = [held["run"] for held in json.loads(reservations.read_text()).values()]
    seen["runs"] = list(folder.rglob("runs/*"))
    seen["still deleting as it ended"] = seen["deleted as it ended"] < len(seen["deleted"])
    return seen


def test_a_run_ends_what_it_started_once_and_gives_back_its_reservations_and_terminal_only_after():
    """Fault (2026-10-17): runs stopped from outside left their nodes and batches running, renting on; review of C7:
    a drive that raised left its reservations held. The one process deaf to SIGTERM gets SIGKILL after the grace.
    Review of C7 (2026-10-17): Ctrl-C, a closed terminal or `kill -- -<pgid>` gives every batch the signal, and the
    run's own SIGTERM moments later, a batch's second signal, broke its delete loop (0 of 3 deleted); a node whose
    main thread was busy in long code showed no stop and got the second signal too; the SIGKILL after the grace cut a
    batch's deletes short; a stopped run released its reservations as it exited, while the cloud tools it spared were
    still deleting machines that billed. Review of C7 (2026-10-17): leading a group of its own took a pipeline's later
    stage out of the terminal's foreground group (Ctrl-C no longer reached it), and the terminal was never given back.
    Fault (2026-10-12): a detached run whose group was sent SIGTERM ended its log with no line; review of C10: a run
    another run's registration refused after detaching ends with the refusal as its line.
    Break: score/graph/stopped.py: '    if code != REFUSED:\n        return line' -> '    if True:\n        return line'
    Break: score/__main__.py: '        release_once_ended(runner, run_id, mark, pool_ticket[0] if pool_ticket else None)' -> '        pass'
    Break: score/__main__.py: '    spared = cloud_side(group)' -> '    spared = set()'
    Break: score/__main__.py: '    if not ending and not cloud_tool("park").parked_by(run_id):' -> '    if True:'
    Break: score/__main__.py: '    if held_before is not None:\n        hand_terminal(terminal, os.getpgrp())' -> '    if False:\n        hand_terminal(terminal, os.getpgrp())'"""
    started = {case: detached([world[1]]) for case, world, _, _ in STOP_CASES if world[0] == "detached"}
    seen_by_case = {**ahead("test_a_run_ends_what_it_started_once_and_gives_back_its_reservations_and_terminal_only_after"),
                    **{case: a_detached_run_ended(started[case], how) for case, _, how, _ in STOP_CASES
                       if case in started}}
    for case, _, _, expected in STOP_CASES:
        seen = seen_by_case[case]
        for said in expected.get("said", []):
            assert said in seen["output"], (case, said, seen["output"])
        for unsaid in expected.get("unsaid", []):
            assert unsaid not in seen["output"], (case, unsaid, seen["output"])
        for measure, value in expected.items():
            if measure not in ("said", "unsaid"):
                assert seen[measure] == value, (case, measure, seen[measure], seen["output"])


@run_ahead("test_a_run_ends_what_it_started_once_and_gives_back_its_reservations_and_terminal_only_after")
def stop_cases_stopped():
    """Every STOP_CASES row, each a run in a session and folder of its own, side by side (the file's time budget)."""
    with concurrent.futures.ThreadPoolExecutor(len(STOP_CASES)) as pool:
        futures = {case: pool.submit(a_run_stopped, world, how) for case, world, how, _ in STOP_CASES
                   if world[0] != "detached"}
        return {case: future.result() for case, future in futures.items()}


def slow_runner(seconds):
    """A one-node run whose make takes `seconds`."""
    def make_slowly(inputs, out, seed, params):
        time.sleep(seconds)
        (out / "made.txt").write_text("made")
    return a_runner(a_world_of(["hangar"])[1], a_store(), (graph.Stage("slow", "place", make_slowly, TEXT, MET),))


def run_options(**more):
    return argparse.Namespace(jobs=graph.JOBS, stage=None, command="run", **more)


def run_printing(runner, places, whole=False, **options):
    """score run's drive, closing status and exit line on `runner`; (its printed lines, the lines, the status)."""
    from score import __main__ as command
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        lines, status = command.run_with_exit_line(runner, places, whole, run_options(**options), ["run", "world1"],
                                                   runner.line_nodes(places, whole))
    return printed.getvalue().splitlines(), lines, status


@pytest.fixture
def run_registry(monkeypatch):
    """The run registry in a folder of the test's own."""
    folder = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(runs, "RUNS", folder)
    return folder


def a_runner_that_raises():
    """A one-node run whose closing states cannot be read: the store is unreadable."""
    runner = slow_runner(0.2)

    def broken(*arguments, **options):
        raise RuntimeError("the store is unreadable")
    runner.lines = broken
    return runner


@pytest.mark.parametrize("make, places, signalled, stall, hung, closing, tail, code", [
    (lambda: slow_runner(0.2), ["hangar"], None, 1.0, False, ["hangar: done"],
     ["hangar: done", "exit: ok, 1 of 1 lines done, 1 rows ran"], 0),
    (lambda: a_driven_runner({"hangar": "explode", "station": "a hub"}), list(PLACES), None, None, False,
     ["hangar: stopped at clean@hangar"], ["exit: stopped, 1 of 2 lines done, 1 stopped, 3 rows ran, 1 not run"], 0),
    (a_runner_that_raises, ["hangar"], None, None, False, [], ["exit: error: RuntimeError: the store is unreadable"],
     1),
    (lambda: slow_runner(5), ["hangar"], signal.SIGTERM, None, False, [],
     ["score run: stopped by signal 15", "exit: stopped by signal 15, exit 143"], 143),
    (lambda: slow_runner(5), ["hangar"], None, 0.5, True,
     ["score run: the drive has not moved", "score run: the pool's release did not end in 0.2 s"],
     ["exit: stopped by signal 15, exit 143"], 143),
], ids=["ends", "a-node-stops", "raises", "sigterm", "stalled-and-its-release-hangs"])
def test_a_run_ends_with_one_exit_line_after_its_line_states_whatever_ends_it(make, places, signalled, stall, hung,
                                                                               closing, tail, code, monkeypatch,
                                                                               run_registry):
    """Review (C8): the exit line came before the closing status; `exit: ok` was said for a run that ended with 1;
    a run that raised said none, nor one a SIGTERM stopped. Batch 1 (2026-10-25): a run past its last node never
    released its pool; the run releases it however it ends (once, unless a signal stopped it). Each run drives in a process of its own, as score run
    does; one node stopped of 2 lines, 3 rows ran, 1 not run; the SIGTERM comes once the run is registered and its
    node started, never at a guess.
    2026-10-24 (second Buy): the detached wrapper waited 40 s, the run spent 30 of them in its grace before its
    pool release and was SIGKILLed into it, and the pool rented cards at the stop: a stopped run closes its pool
    before it ends its group, and the wrapper's wait holds the release and the grace. Batch 1 (2026-10-25): a hung
    release kept the run from its exit line; its drive sat in one pass over an hour after its last heartbeat. The
    watchdog (its stall scaled to 0.5 s) stops a run whose 5 s node holds the drive still, and leaves one whose
    drive moves within its stall (1 s, the 0.2 s node); that run's pool release hangs 20 s and is left after 0.2 s,
    the group ending within 2 s of the release's start.
    Break: score/__main__.py: '        print(f"exit: {status}", flush=True)' -> '        pass'
    Break: score/__main__.py: '    release.join(POOL_RELEASE_SECONDS)' -> '    release.join()'
    Break: score/__main__.py: '    release_pool(os.environ.get(RUN_ID))\n    killed, spared = end_group()' -> '    killed, spared = end_group()\n    release_pool(os.environ.get(RUN_ID))'
    Break: score/__main__.py: '                os.kill(os.getpid(), signal.SIGTERM)\n                return' -> '                return'"""
    from score import __main__ as command
    assert command.POOL_RELEASE_SECONDS + command.STOP_GRACE_SECONDS < stopped.FORWARD_WAIT_SECONDS
    folder = pathlib.Path(tempfile.mkdtemp())
    released, at, ending_group = [], {}, command.end_group
    monkeypatch.setattr(command.cloud_tool("pool"), "release", lambda run_id: released.append(run_id) or at.setdefault(
        "released", time.monotonic()) and hung and time.sleep(20))
    monkeypatch.setattr(command, "end_group", lambda: released.append("group ended") or at.setdefault(
        "group ended", time.monotonic()) and ending_group())
    monkeypatch.setattr(command, "POOL_RELEASE_SECONDS", 0.2 if hung else command.POOL_RELEASE_SECONDS)
    monkeypatch.setattr(command, "DRIVE_STALL_SECONDS", stall or command.DRIVE_STALL_SECONDS)
    monkeypatch.setattr(command, "WATCH_SECONDS", 0.05 if stall else command.WATCH_SECONDS)

    def driving():
        sys.stdout = (folder / "said.txt").open("a", buffering=1)
        stopped.stop_on_signals(lambda number: print(f"score run: stopped by signal {number}", flush=True))
        runner = make()
        try:
            command.run_with_exit_line(runner, places, False, run_options(), ["run", "world1"],
                                       runner.line_nodes(places, False))
        finally:
            (folder / "released.json").write_text(json.dumps([released, os.environ.get(command.RUN_ID), at]))
    process = graph.FORK.Process(target=driving)
    process.start()
    deadline = time.monotonic() + 30
    while signalled and time.monotonic() < deadline and not (list(run_registry.glob("*.json")) and any(
            parent == process.pid for parent, _ in graph.process_table().values())):
        time.sleep(0.05)
    if signalled:
        os.kill(process.pid, signalled)
    process.join(30)
    lines = (folder / "said.txt").read_text().splitlines()
    assert process.exitcode == code and lines[-len(tail):] == tail, (process.exitcode, lines)
    assert all(any(line.startswith(state) for line in lines) for state in closing), lines
    pool, run_id, at = json.loads((folder / "released.json").read_text())
    assert not hung or at["group ended"] - at["released"] < 2, ("the hung release held the run past its 0.2 s", at)
    assert run_id and (pool == [run_id] if code != 143 else pool[:2] == [run_id, "group ended"] and set(pool) == {
        run_id, "group ended"}), (pool, run_id)


# A long node's drive: (id, its node's seconds, its gauges (None: a stage's own drive; "run": score run's gauges of
# this run's world), the least beats said before the node ends, the end of the first beat (None: no beat at all)).
BEATS = [
    ("this-runs-gauges", 0.5, "run", 3, ": rows done 0, running 1, queued 0; this run's rows: paid runs open 1, "
                                       "EUR 8.15 in the ledger since the run started (rows 2.50, pool 3.50, "
                                       "model calls 2.15)"),
    ("a-gauge-that-raises", 0.3, lambda: 1 / 0, 1, "; gauges unreadable: ZeroDivisionError: division by zero"),
    ("a-stages-own-drive", 0.2, None, 0, None),
]


def test_a_long_node_has_heartbeats_carrying_only_this_runs_gauges_and_a_gauge_that_fails_is_said(monkeypatch):
    """Fault (2026-10-16): runs failed or sat idle quietly. Review (C8): a gauge that raised ended the drive; a stage's
    own drive (no gauges) says no beat; the gauges summed every worktree's batches and every open paid run. Fault of
    2026-10-24: the heartbeat said EUR 2.31 while the pool and Pro close-ups cost ten times that; 2026-10-25: the
    gauges were made before the run took its id. The 2-minute beat and 3-minute node scaled to 0.1 s and 0.5 s. A
    beat of this run's gauges counts its rows 2.50 (k1; k3 is another worktree's, k4 before the run), its pool
    3.00 + 0.50 (a frozen copy's line of its pool), its calls 2.00 + the unfinished one's estimate 0.15, and one paid
    run open (other@far's is not this run's).
    Break: score/graph/__init__.py: '            beat_in = max(0.0, beat_at - time.monotonic()) if gauges else None' -> '            beat_in = None'
    Break: score/__main__.py: '        euros = spent_by_run(compute.ledger(), nodes, started, os.environ.get(RUN_ID))' -> '        euros = spent_by_run(compute.ledger(), nodes, started, None)'"""
    from score import __main__ as command
    monkeypatch.setattr(graph, "HEARTBEAT", 0.1)
    books = compute.ledger()
    runners = {case: slow_runner(seconds) for case, seconds, *_ in BEATS}
    runner = runners["this-runs-gauges"]
    here = books.origin()["worktree"]
    rows = [{"worktree": here, "ticket": "slow@hangar k1", "started": "2026-10-17T10:00:00Z", "euros": 2.5},
            {"worktree": here, "ticket": "other@far k2", "started": "2026-10-17T10:00:00Z", "euros": 7.0},
            {"worktree": "elsewhere", "ticket": "slow@hangar k3", "started": "2026-10-17T10:00:00Z", "euros": 9.0},
            {"worktree": here, "ticket": "slow@hangar k4", "started": "2026-10-17T08:00:00Z", "euros": 4.0},
            {"worktree": here, "ticket": "gpu-pool run-g", "started": "2026-10-17T10:01:00Z", "euros": 3.0,
             "run": "run-g", "kind": "pool-hold"},
            {"worktree": "frozen-other", "ticket": "gpu-pool run-g", "started": "2026-10-17T10:02:00Z", "euros": 0.5},
            {"worktree": here, "ticket": "gpu-pool other-run", "started": "2026-10-17T10:02:00Z", "euros": 9.0}]
    monkeypatch.setattr(books, "entries", lambda: rows)
    held = {graph.now(): {"node": "slow@hangar"}}
    held[graph.now()] = {"node": "other@far"}
    (runner.store.cache.parent / "reservations.json").write_text(json.dumps(held))
    google_spend = command.cloud_tool("google_spend")
    monkeypatch.setattr(google_spend, "write", google_spend.write)
    monkeypatch.setattr(books, "record", books.record)
    google_spend.LEDGER.unlink(missing_ok=True)  # the sandbox's
    google_spend.started("gemini-3-pro-image", "another run's")  # untagged: not this run's
    for name in (command.RUN_ID, command.LEDGER_TAG, "PYTHONPATH"):
        monkeypatch.delenv(name, raising=False)
    said = {}
    try:
        gauges = command.run_gauges(runner, runner.line_nodes(["hangar"], False), "2026-10-17T09:00:00Z")  # no id yet
        monkeypatch.setenv(command.RUN_ID, "run-g")
        command.tag_ledgers()
        assert os.environ[command.LEDGER_TAG] == "run-g" and "ledger_tag" in os.environ["PYTHONPATH"]
        google_spend.started("gemini-3-pro-image", "pro")  # never finished: its estimate, 0.15
        google_spend.record("gemini-3-pro-image", "pro", {"usageMetadata": {"promptTokenCount": 1000000}},
                            google_spend.started("gemini-3-pro-image", "pro"))  # EUR 2.00
        for case, _, given, _, _ in BEATS:
            said[case] = []
            options = {} if given is None else {"gauges": gauges if given == "run" else given}
            assert runners[case].drive(["hangar"], say=said[case].append, **options) == {"slow@hangar": ACCEPTED}, (
                case, said[case])
    finally:
        sys.meta_path[:] = [finder for finder in sys.meta_path if type(finder).__name__ != "Tagging"]
    for case, _, _, least, first in BEATS:
        lines = said[case][:said[case].index(f"slow@hangar: {ACCEPTED}")] if first else said[case]
        beats = [line for line in lines if line.startswith("heartbeat ")]
        if first is None:
            assert not [line for line in said[case] if line.startswith(("heartbeat ", "exit:"))], (case, said[case])
        else:
            assert len(beats) >= least and beats[0].endswith(first), (case, said[case])


def test_a_row_running_past_its_minutes_keeps_its_readers_off_the_pool(monkeypatch, tmp_path):
    """Batch 1 try 5 (2026-10-26): finish lists forecast at 3.7 min waited 18 to 43 min on Google's Batch API queue,
    and counted at their whole 3.7 min kept every bake reading them due: 13 machines parked idle 30 min. The list's
    likely 4 min, the bake's lead 8: started 1 min ago it has 3 left, the bake due; run 20 min it has overrun 16, as
    long again is past the lead, the bake not due; not started it counts its whole 4.
    Checkout 39 (2026-11-07): a running pooled row was due until it ended, its local work included, and the pool
    held 10 cards parked five hours (EUR 77). The bake running 2 min is due (its first claim is coming); 20 min with
    no use of the pool it is not; asked for a machine 1 min ago (pool.want, its ticket's node) it is; holding one now
    it is, whatever its last ask; given back 20 min ago it is not.
    Break: score/__main__.py: '    return abs(likely - ran)' -> '    return likely'
    Break: score/__main__.py: 'if began is None or now - max(began, used.get(node, 0.0)) <= leads[on] * 60:' -> 'if True:'"""
    from score import __main__ as command
    reads = {"list@a": [], "bake@a": ["list@a"]}
    runner = types.SimpleNamespace(
        store=types.SimpleNamespace(current_accept=lambda node: None),
        nodes_named=lambda names: iter([(name, None) for name in names]),
        earlier=lambda node, _place: reads[node],
        desk=lambda area, node, ending: pathlib.Path(tempfile.gettempdir()) / "no-such-fault" / f"{node}{ending}",
        began={})
    leads = {False: 8.0, True: 8.0}
    monkeypatch.setattr(command, "POOLED_ROWS", [("bake@a", "a", 1, False)])
    monkeypatch.setattr(command, "PAID_MINUTES", {"list@a": 4.0, "bake@a": 7.0})
    started = time.time() - 3600
    assert command.due_rows(runner, started, leads) == [("a", 1, False)]
    runner.began["list@a"] = time.time() - 60
    assert command.due_rows(runner, started, leads) == [("a", 1, False)]
    runner.began["list@a"] = time.time() - 20 * 60
    assert command.due_rows(runner, started, leads) == []
    standing = {"list@a": {"at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
    runner.store = types.SimpleNamespace(current_accept=standing.get)
    pool = command.cloud_tool("pool")
    monkeypatch.setattr(pool, "POOLS", tmp_path / "pools")
    monkeypatch.setattr(pool.preflight, "mark_waiting", lambda: None)  # the runaway watch's mark: not this test's
    run_id = "run-uses"
    pool.folder_of(run_id).mkdir(parents=True)
    runner.began["bake@a"] = time.time() - 2 * 60
    assert command.due_rows(runner, started, leads, pool.uses(run_id)) == [("a", 1, False)]
    runner.began["bake@a"] = time.time() - 20 * 60
    assert command.due_rows(runner, started, leads, pool.uses(run_id)) == []
    monkeypatch.setenv(pool.SPEND_TICKET, "bake@a key-1")
    pool.want(run_id, [], "blender", 100)  # no plan: nothing asked, the use still noted
    assert command.due_rows(runner, started, leads, pool.uses(run_id)) == [("a", 1, False)]
    ago = time.time() - 20 * 60
    os.utime(pool.folder_of(run_id) / pool.USES / "bake@a", (ago, ago))
    assert command.due_rows(runner, started, leads, pool.uses(run_id)) == []
    (pool.folder_of(run_id) / "cards").mkdir()
    (pool.folder_of(run_id) / "cards" / "card-1.json").write_text(json.dumps({"id": "card-1", "holder": None}))
    pool.held_by(run_id, "card-1", os.getpid())
    os.utime(pool.folder_of(run_id) / pool.USES / "bake@a", (ago, ago))
    assert command.due_rows(runner, started, leads, pool.uses(run_id)) == [("a", 1, False)]
    pool.held_by(run_id, "card-1", None)
    os.utime(pool.folder_of(run_id) / pool.USES / "bake@a", (ago, ago))
    assert command.due_rows(runner, started, leads, pool.uses(run_id)) == []


def test_the_pool_rents_each_machine_its_start_up_before_its_first_job_and_says_an_empty_one(monkeypatch):
    """Owner, 2026-10-25: "cant u just do the start up earlier then when u need them again" (Batch 1: machines idle an
    hour). Close-ups 150 min ahead: nothing due; ended: Pixal3D due now, the bake 30 min on (model 30) is not within
    its 8 min lead, at model 6 it is; the judge 40 min away (finish 40) waits, at finish 5 it is held; a row reading a
    stopped one is never due. Fault of 2026-10-26: rows waited an hour on a pool with no machine, said nowhere: said
    after 10 min, again only 10 min on, why it is empty, quiet once a machine is in.
    Break: score/__main__.py: '        if not ended_since(runner, node, started) and due(node) <= leads[on]:' -> '        if not ended_since(runner, node, started):'"""
    from score import __main__ as command
    reads = {"close@a": [], "model@a": ["close@a"], "bake@a": ["model@a"], "pixal@a": ["close@a"],
             "finish@a": ["pixal@a"], "judge@a": ["finish@a"]}
    started, standing = time.time() - 60, {}

    def ends(node):
        standing[node] = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    runner = types.SimpleNamespace(
        store=types.SimpleNamespace(current_accept=standing.get),
        nodes_named=lambda names: iter([(name, None) for name in names]),
        earlier=lambda node, _place: reads[node],
        desk=lambda area, node, ending: pathlib.Path(tempfile.gettempdir()) / "no-such-fault" / f"{node}{ending}",
        began={})
    leads = {False: 8.0, True: 8.0}
    monkeypatch.setattr(command, "POOLED_ROWS", [("bake@a", "a", 2, True), ("pixal@a", "a", 3, False),
                                                 ("judge@a", "j", 1, False)])
    monkeypatch.setattr(command, "PAID_MINUTES", {"close@a": 150.0, "model@a": 30.0, "bake@a": 20.0, "pixal@a": 60.0,
                                                  "finish@a": 40.0, "judge@a": 10.0})
    assert command.due_rows(runner, started, leads) == []
    ends("close@a")
    assert command.due_rows(runner, started, leads) == [("a", 3, False)]
    command.PAID_MINUTES["model@a"] = 6.0
    assert ("a", 2, True) in command.due_rows(runner, started, leads)
    for node in ("pixal@a", "model@a", "bake@a"):
        ends(node)
    assert command.due_rows(runner, started, leads) == []
    command.PAID_MINUTES["finish@a"] = 5.0
    assert command.due_rows(runner, started, leads) == [("j", 1, False)]
    chain_of = {"c": ["b"], "b": ["a"], "a": []}
    assert command.due_in("c", chain_of.get, lambda node: 10.0, lambda node: "stopped" if node == "a" else "todo",
                          {}) == float("inf")
    state = {"members": [], "plan": {"collector": os.getpid()}}
    pool = types.SimpleNamespace(members=lambda run_id: state["members"], current=lambda run_id: state["plan"],
                                 collector_alive=lambda plan: True,
                                 collector_said=lambda run_id: "[cloud] pool: 1 card(s) short, none in stock")
    step = command.POOL_EMPTY_SAY_SECONDS

    def said(now):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            command.said_empty_pool(pool, "run", [("a", 3, False)], now)
        return out.getvalue()
    monkeypatch.setattr(command, "POOL_EMPTY", {})
    assert said(1000.0) == "" and said(1000.0 + step - 1) == ""
    line = said(1000.0 + step)
    assert "no machine for 10 min while 1 row is due" in line and "none in stock" in line, line
    assert said(1000.0 + step + 60) == ""
    state["plan"] = None
    assert "it is closed" in said(1000.0 + 2 * step)
    state["members"] = [{"id": "card-1"}]
    assert said(1000.0 + 3 * step) == "" and command.POOL_EMPTY == {}


# --- the run registry: a run a reboot cut off is started again from its own code, and nothing else (C9) ------------

EARLIER_BOOT = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def no_live_store_sweep(monkeypatch):
    """C9 review: a resume with no `swept` deleted .partial files in the real store; a test passes swept=()."""
    def refused():
        raise AssertionError("a test swept the live store's .partial files: pass swept=()")
    monkeypatch.setattr(runs, "store_roots", refused)


def a_worktree(python=None):
    """A clean committed git worktree of the test's own (its .venv ignored), `python` as its .venv/bin/python when
    given; the folder and its commit."""
    worktree = pathlib.Path(tempfile.mkdtemp())
    (worktree / ".gitignore").write_text(".venv/\nstarts\n")
    if python is not None:
        (worktree / ".venv/bin").mkdir(parents=True)
        (worktree / ".venv/bin/python").write_text(python)
        (worktree / ".venv/bin/python").chmod(0o755)
    git = ["git", "-C", str(worktree), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "the run's code"]):
        subprocess.run([*git, *command], check=True)
    return worktree, runs.commit_of(worktree)


def an_entry(folder, name, **fields):
    entry = {"id": name, "argv": ["run", "world1", "--place", "hangar"], "commit": "c0ffee", "worktree": str(REPO),
             "pid": 1, "boot": EARLIER_BOOT, "started": "2026-10-17T08:00:00+00:00", "state": runs.RUNNING, **fields}
    (folder / f"{name}.json").write_text(json.dumps(entry))
    return entry


STARTS = '#!/bin/sh\necho "detached: started in $(pwd) with $*"; echo started >> "$PWD/starts"\n'


@run_ahead("test_resume_starts_only_a_run_an_earlier_boot_cut_off_from_its_own_unchanged_worktree")
def a_dry_resume():
    """`score resume --dry` in a home of its own over six runs' entries, two of a worktree of their own: the home,
    the worktree, its commit and the process."""
    home = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree()
    (home / "runs").mkdir()
    an_entry(home / "runs", "cut-off", worktree=str(worktree), commit=commit)
    an_entry(home / "runs", "other-commit", worktree=str(worktree), commit="c0ffee")
    an_entry(home / "runs", "finished", state=runs.ENDED)
    an_entry(home / "runs", "stopped-by-the-owner", state=runs.STOPPED)
    an_entry(home / "runs", "this-boot", boot=runs.boot_id())
    an_entry(home / "runs", "before-boots-were-kept", boot=None)
    done = subprocess.run([sys.executable, "-m", "score", "resume", "--dry"], cwd=REPO, capture_output=True,
                          text=True, env={**ENVIRON, "PROPS_HOME": str(home)})
    return home, worktree, commit, done


def test_resume_starts_only_a_run_an_earlier_boot_cut_off_from_its_own_unchanged_worktree(monkeypatch):
    """C9: PC reboots lost runs; review: resume ran whatever a worktree had checked out days later, a run the owner
    stopped, one OOM-killed long before. Listed by `score resume --dry` (marking none): the cut-off run; skipped: one
    whose worktree moved on. Started detached from its own worktree and marked resumed, never twice, even by two
    resumes at once; one moved on, changed, gone, silent over 12 h before the boot or whose restart fails is marked
    unresumable with why. The first resume also removes an earlier boot's partial write (C9 review: a write cut by a
    reboot leaves its .partial file, and nothing removed it) and keeps one of this boot (a write going on now).
    Break: score/graph/runs.py: '    if not entry.get("commit") or head != entry["commit"]:' -> '    if not entry.get("commit"):'
    Break: score/graph/runs.py: '    with locked(folder / ".resume.lock"):' -> '    with contextlib.nullcontext():'
    The conductor: a run asking for 16 jobs waits for the grow; a resume on 2 cores leaves it, one on 16 starts it and
    keeps the resumed run's pid and log on the entry, so the cockpit follows its launch to the resumed run's end.
    Break: score/graph/runs.py: '    if entry.get("state") == WAITING and entry.get("jobs", 0) > (os.cpu_count() or 1):' -> '    if False:'
    Break: score/graph/runs.py: '    started = STARTED.search(done.stdout)' -> '    started = None'
    On the cluster's home (#76) a run its drive pod's cut left `running` at this boot is started again once, a second
    cut from the same frozen copy is unresumable, a live one is left, and off the cluster's home none is taken.
    Break: in runs.cut_at_this_boot, drop `and not size.entry_alive(entry)` (a live drive started twice).
    Break: in runs.restart_cut, drop the `cut_before` refusal (a run cut by its memory resumed for ever)."""
    home, worktree, commit, done = ahead(
        "test_resume_starts_only_a_run_an_earlier_boot_cut_off_from_its_own_unchanged_worktree")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines() == [
        f"would resume cut-off: worktree={worktree} commit={commit[:12]} argv=run world1 --place hangar",
        f"would skip other-commit: worktree={worktree} commit=c0ffee argv=run world1 --place hangar: "
        f"its worktree is at {commit[:12]}, not the commit that registered it"], done.stdout
    assert {entry["state"] for entry in runs.entries(home / "runs").values()} == {runs.RUNNING, runs.ENDED,
                                                                                   runs.STOPPED}
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree(STARTS.replace("#!/bin/sh\n", "#!/bin/sh\nsleep 0.3; "))  # a race to win
    entry = an_entry(folder, "cut-off", worktree=str(worktree), commit=commit)
    assert runs.restart_command(entry) == [str(worktree / ".venv/bin/python"), "-m", "score", *entry["argv"],
                                           "--detach"]
    sizing, sizing_commit = a_worktree('#!/bin/sh\necho "detached: started pid=4242 log=/logs/$*"\n')
    an_entry(folder, "waiting", worktree=str(sizing), commit=sizing_commit, state=runs.WAITING, jobs=16,
             argv=["run", "world1", "--jobs", "16"])
    an_entry(folder, "waiting-this-boot", state=runs.WAITING, jobs=16, boot=runs.boot_id())
    assert set(runs.stranded(folder)) == {folder / "cut-off.json", folder / "waiting.json"}
    objects = pathlib.Path(tempfile.mkdtemp())
    old = partial_of(objects / "records/clean@hangar/k1.json")
    old.write_text("{")
    os.utime(old, (runs.boot_time() - 60, runs.boot_time() - 60))
    new = partial_of(objects / "records/clean@hangar/k2.json")
    new.write_text("{")
    said, found = [], []
    monkeypatch.setattr(os, "cpu_count", lambda: 2)
    both = [threading.Thread(target=lambda: found.append(runs.resume(False, said.append, folder=folder,
                                                                     swept=(objects,)))) for _ in range(2)]
    for each in both:
        each.start()
    for each in both:
        each.join()
    assert sorted(found) == [1, 2] and (worktree / "starts").read_text().splitlines() == ["started"], (found, said)
    assert [line for line in said if line.startswith("resumed cut-off")] == [
        line for line in said if f"started in {worktree} with -m score run" in line] and len(
        [line for line in said if line.startswith("resumed")]) == 1, said
    left = [line for line in said if line.startswith("left waiting")]
    assert len(left) == 2 and all("still waiting for size: it asks for 16 jobs" in line for line in left), said
    assert not old.exists() and new.exists() and any(str(old) in line for line in said), said
    assert runs.entries(folder)[folder / "cut-off.json"]["state"] == runs.RESUMED
    assert runs.entries(folder)[folder / "waiting.json"]["state"] == runs.WAITING
    assert list(runs.stranded(folder)) == [folder / "waiting.json"]
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    said.clear()
    runs.resume(False, said.append, folder=folder, swept=())
    assert said[0].startswith("resumed waiting") and "--jobs 16 --detach" in said[0], said
    resumed = runs.entries(folder)[folder / "waiting.json"]
    assert resumed["state"] == runs.RESUMED and resumed["jobs"] == 16, resumed
    assert resumed["resumed"] == {"pid": 4242, "log": "/logs/-m score run world1 --jobs 16 --detach"}, resumed
    assert [entry["id"] for entry in runs.waiting(folder).values()] == ["waiting-this-boot"]
    assert runs.stranded(folder) == {}
    (worktree / "starts").unlink()
    an_entry(folder, "moved-on", worktree=str(worktree), commit="c0ffee")
    an_entry(folder, "orphan", worktree=str(folder / "gone"))
    an_entry(folder, "killed-days-ago", worktree=str(worktree), commit=commit)
    silent = runs.boot_time() - runs.RESUME_WINDOW - 60
    os.utime(folder / "killed-days-ago.json", (silent, silent))
    runs.resume(False, said.append, folder=folder, swept=())
    (worktree / "stage.py").write_text("changed = True\n")
    an_entry(folder, "changed", worktree=str(worktree), commit=commit)
    runs.resume(False, said.append, folder=folder, swept=())
    refusing, refused_commit = a_worktree('#!/bin/sh\necho "refused: re-buys over EUR 5" >&2; exit 1\n')
    an_entry(folder, "refused", worktree=str(refusing), commit=refused_commit)
    runs.resume(False, said.append, folder=folder, swept=())
    assert not (worktree / "starts").exists(), said
    whys = {path.stem: entry.get("why", "") for path, entry in runs.entries(folder).items()
            if entry["state"] == runs.UNRESUMABLE}
    assert set(whys) == {"moved-on", "orphan", "killed-days-ago", "changed", "refused"}, whys
    for name, why in (("moved-on", "not the commit that registered it"), ("orphan", "worktree is gone"),
                      ("killed-days-ago", "last sign of life"), ("changed", "changes not committed"),
                      ("refused", "refused: re-buys")):
        assert why in whys[name], (name, whys[name])
    assert runs.stranded(folder) == {}  # never tried again
    assert sorted(line.split(":")[0] for line in runs.unresumable(folder)) == sorted(whys)
    from score.conductor import cluster
    cut_folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree(STARTS)
    gone = {"worktree": str(worktree), "commit": commit, "boot": runs.boot_id(), "pid": 2 ** 22 + 11}
    an_entry(cut_folder, "cut-on-the-vm", **gone)
    assert runs.resume(False, said.append, folder=cut_folder, swept=()) == 0  # off the cluster's home: never taken
    monkeypatch.setattr(cluster, "RECORD", cut_folder / "cluster.json")
    (cut_folder / "cluster.json").write_text('{"namespace": "score"}')
    (cut_folder / "cut-on-the-vm.json").unlink()
    an_entry(cut_folder, "cut-pod", **gone)
    an_entry(cut_folder, "live-pod", worktree=str(worktree), commit=commit, boot=runs.boot_id(), pid=os.getpid(),
             started=datetime.datetime.now(datetime.timezone.utc).isoformat())
    assert runs.resume(False, said.append, folder=cut_folder, swept=()) == 1
    states = {path.stem: entry for path, entry in runs.entries(cut_folder).items()}
    assert states["cut-pod"]["state"] == runs.RESUMED and states["cut-pod"]["cut"], said[-1]
    assert states["live-pod"]["state"] == runs.RUNNING and (worktree / "starts").read_text().count("started") == 1
    an_entry(cut_folder, "cut-again", **gone)
    runs.resume(False, said.append, folder=cut_folder, swept=())
    again = runs.entries(cut_folder)[cut_folder / "cut-again.json"]
    assert again["state"] == runs.UNRESUMABLE and "cut again" in again["why"], again
    assert (worktree / "starts").read_text().count("started") == 1


@dataclasses.dataclass(frozen=True)
class Ending:
    """How a registered run ends: registered running or waiting for a machine (`waiting`), stopped by `signal` (by
    stopped_by, or through score run's own `driven` when `drive` names where the signal arrives: as its entry is
    written, or while it drives), the machine shutting down or not, a resize the size timer asked for (None: none;
    0: just now; 60: a minute before the run registered; else seconds from now), and the state its entry is left in."""
    waiting: bool
    signal: int
    down: bool
    marked: object
    state: str
    drive: str = ""


ENDINGS = {
    "owner's Ctrl-C in a shutdown": Ending(False, signal.SIGINT, True, None, runs.STOPPED),
    "owner's hang-up in a shutdown": Ending(False, signal.SIGHUP, True, None, runs.STOPPED),
    "owner's kill": Ending(False, signal.SIGTERM, False, None, runs.STOPPED),
    "shutdown's kill": Ending(False, signal.SIGTERM, True, None, runs.RUNNING),
    "kill in the resize it waits for": Ending(True, signal.SIGTERM, False, 0, runs.WAITING),
    "kill after the resize's window": Ending(True, signal.SIGTERM, False, -conductor.RESIZE_WINDOW - 60, runs.STOPPED),
    "kill with no resize asked": Ending(True, signal.SIGTERM, False, None, runs.STOPPED),
    "kill in a resize asked before it registered": Ending(True, signal.SIGTERM, False, 60, runs.STOPPED),
    "score run's Ctrl-C while it drives": Ending(False, signal.SIGINT, False, None, runs.STOPPED, "driving"),
    "score run's Ctrl-C as it registers": Ending(False, signal.SIGINT, False, None, runs.STOPPED, "registering"),
}


class Driving:
    """A runner whose drive is stopped by a Ctrl-C."""
    def drive(self, *arguments, **options):
        os.kill(os.getpid(), signal.SIGINT)


def test_a_registered_run_says_it_lives_and_its_ending_leaves_it_stopped_unless_a_shutdown_or_resize_ended_it(
        monkeypatch, run_registry):
    """C9 review: Ctrl-C, a kill or a closed session left a run `running`, for resume to buy again what the owner
    stopped; and score run wrote its entry before the stopping signals were handled, so a Ctrl-C in between left it
    `running` too. A SIGTERM while the machine shuts down, or in a resize the size timer asked for, leaves it as it was;
    the owner's SIGTERM outside one, or to a run registered after the ask, stops it. While a run drives its entry is
    touched, so resume knows it was alive, and with its gauges says how many nodes the run runs and how many paid rows
    it would buy, which the conductor's checkout update reads (tools/cloud/conductor/update.py idle_copies).
    Break: score/graph/runs.py: '    if number == signal.SIGTERM and (shutting_down() or conductor.resizing(registered=registered_at(path))):' -> '    if shutting_down() or conductor.resizing(registered=registered_at(path)):'
    Break: score/__main__.py: '        if code > 128 and path.exists():' -> '        if False:'
    Break: score/graph/runs.py: '                noted(path, gauge)' -> '                pass'
    Break: score/graph/runs.py: '**(gauge() if gauge else {})}' -> '}' -> the entry never says what the run does."""
    from score import __main__ as command
    path = runs.register(["run", "world1", "--detach", "--jobs", "2"])
    entry = json.loads(path.read_text())
    assert entry["argv"] == ["run", "world1", "--jobs", "2"] and entry["pid"] == os.getpid()
    assert entry["worktree"] == str(REPO) and entry["commit"] == git_out("rev-parse", "HEAD")[0] and entry["state"] == runs.RUNNING
    assert entry["boot"] == runs.boot_id() and runs.stranded(run_registry) == {}
    monkeypatch.setattr(runs, "HEARTBEAT", 0.05)
    for gauge, says in ((None, {}), (lambda: {"running": 0, "buys": 0}, {"running": 0, "buys": 0})):
        os.utime(path, (1, 1))
        with runs.beating(path, gauge):
            time.sleep(0.3)
        entry = json.loads(path.read_text())
        assert path.stat().st_mtime > 1 and entry["argv"] == ["run", "world1", "--jobs", "2"], gauge
        assert {name: entry[name] for name in ("running", "buys") if name in entry} == says, gauge
    path.unlink()
    handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    written = runs.written

    def written_then_stopped(path, entry):
        written(path, entry)
        os.kill(os.getpid(), signal.SIGINT)
        return path
    monkeypatch.setattr(conductor, "RESIZING", pathlib.Path(tempfile.mkdtemp()) / "resizing.json")
    try:
        for name, ending in ENDINGS.items():
            monkeypatch.setattr(runs, "shutting_down", lambda: ending.down)
            monkeypatch.setattr(runs, "written", written_then_stopped if ending.drive == "registering" else written)
            if ending.drive:
                stopped.stop_on_signals(lambda number: None)  # as_run's handlers, installed before driven
                runner = Driving() if ending.drive == "driving" else object()
                with pytest.raises(SystemExit) as stop:
                    command.driven(runner, [], True, argparse.Namespace(jobs=1, stage=None), ["run", "world1"])
                assert stop.value.code == 128 + ending.signal, name
            else:
                argv = ["run", "world1", "--jobs", "16"]
                path = runs.register_waiting(argv, 16) if ending.waiting else runs.register(argv)
                if ending.marked is not None:
                    asked = runs.registered_at(path) - 60 if ending.marked == 60 else time.time() + ending.marked
                    conductor.RESIZING.write_text(json.dumps({"action": "grow", "at": asked}))
                runs.stopped_by(path, ending.signal)
            assert [entry["state"] for entry in runs.entries(run_registry).values()] == [ending.state], name
            conductor.RESIZING.unlink(missing_ok=True)
            for path in run_registry.glob("*.json"):
                path.unlink()
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)


# --- one commit per store (C10): a live run of another commit, or of the same commit making the same nodes, refuses

@pytest.fixture
def other():
    """A live process standing for another run (this test's own pid is the registering run's)."""
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield process
    process.kill()
    process.wait()


def a_dead_pid():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


OTHER_COMMIT = ("refused: run pid {other} from commit aaa111 in /work/one is live on this store; this run is at bbb222. "
                "Wait for it to end or stop it.")
SAME_NODE = "refused: run pid {other} at the same commit in /work/one would also make 1 of these nodes (terrain)"
# One store's claims, step by step: (what is done, by whom or for which place, at which commit, its nodes, what it
# answers). `run` is score run's own claim (__main__.claim, detached: it registers nothing) for a place of the toy
# table, its nodes those it would make; `claim` registers a pid ("other" a live process, "me" this test's, "dead" one
# that has ended) from /work/one (other, dead) or /work/two (me); `reused` gives other's pid another start time;
# `terrain` makes the environment node both places read.
CLAIMS = (
    ("claim", "other", "aaa111", ("terrain", "build@airlock"), None),
    ("run", "camp", "bbb222", ("terrain", "build@camp"), OTHER_COMMIT),
    ("claim", "me", "bbb222", ("build@camp",), OTHER_COMMIT),
    ("run", "camp", "aaa111", ("terrain", "build@camp"), SAME_NODE),  # every place reads terrain: it clashes
    ("claim", "me", "aaa111", ("build@camp",), None),
    ("unclaim", "me", None, (), None),
    ("claim", "me", "aaa111", ("terrain", "build@camp"), SAME_NODE),
    ("reused", "other", None, (), None),
    ("claim", "me", "bbb222", ("terrain",), None),  # other's pid now another process's: no run holds the store
    ("unclaim", "me", None, (), None),
    ("claim", "dead", "aaa111", ("terrain",), None),
    ("claim", "me", "bbb222", ("terrain",), None),  # a dead pid holds nothing
    ("unclaim", "me", None, (), None),
    ("claim", "other", "aaa111", ("terrain",), None),
    ("unclaim", "other", None, (), None),
    ("claim", "me", "bbb222", ("terrain",), None),  # a released run holds nothing
    ("unclaim", "me", None, (), None),
    ("terrain", None, None, (), None),
    ("claim", "other", "aaa111", ("build@airlock",), None),  # terrain stands: neither place would make it now
    ("run", "camp", "aaa111", ("build@camp",), None),
)


def test_a_run_claims_its_store_only_beside_live_runs_of_its_commit_that_make_other_nodes(other, monkeypatch):
    """Fault (2026-10-17): two runs at different code over one store re-made each other's rows for 6 hours. A dead
    pid, a reused one (another start time) or a released run frees the store; the claims are never read as a run.
    Review of C10: every place reads environment nodes (terrain), so comparing every planned node refused the second
    `score run --place` always; only nodes a run would make count. Fault (2026-10-28): the run's start listed its line
    nodes three times (claim, gauges, drive), each outside a still, and the claim worked out every key in a still of
    its own: 35 s of one core before the first node. The claim lists them once, inside the still its would_make works
    in, and the gauges take that list. A toy table: terrain read by each place's build.
    Break: score/graph/runs.py: '            if entry.get("started") is not None and start_time(int(pid)) == entry["started"]}' -> '            }'
    Break: score/graph/runs.py: '        return [node_name(stage, place) for stage, place in nodes if runner.standing(stage, place) is not None]' -> '        return [node_name(stage, place) for stage, place in nodes]'
    Break: score/__main__.py: '    with runner.still(), plans.one_moment():' -> '    with plans.one_moment():'"""
    from score import __main__ as command
    data, world = a_world_of(["airlock", "camp"])
    terrain = graph.Stage("terrain", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_seen, TEXT, MET, after={"terrain": READS})
    runner = a_runner(world, a_store(), (terrain, build))
    folder = pathlib.Path(tempfile.mkdtemp()) / "runs"
    pids = {"other": other.pid, "me": os.getpid(), "dead": a_dead_pid()}
    worktrees = {"other": "/work/one", "me": "/work/two", "dead": "/work/one"}
    listed, judged = [], []
    line_nodes, would_make, claim_refusal = runner.line_nodes, runs.would_make, runs.claim_refusal

    def listing(*arguments, **options):
        listed.append(runner.remembered is not None)
        return line_nodes(*arguments, **options)

    def making(*arguments):
        judged.append(runner.remembered is not None)
        return would_make(*arguments)
    monkeypatch.setattr(runner, "line_nodes", listing)
    monkeypatch.setattr(runs, "would_make", making)
    monkeypatch.setattr(runs, "claim_refusal", lambda commit, nodes: claim_refusal(commit, nodes, folder=folder))
    for step, (done, who, commit, nodes, answer) in enumerate(CLAIMS):
        expected = answer and answer.format(other=other.pid)
        if done == "claim":
            assert runs.claim(commit, list(nodes), pids[who], worktree=worktrees[who], folder=folder) == expected, step
            if expected:  # registering nothing, the check before detaching gives the same refusal
                assert claim_refusal(commit, list(nodes), folder=folder) == expected, step
        elif done == "unclaim":
            runs.unclaim(pids[who], folder=folder)
        elif done == "reused":
            entries = json.loads((folder / runs.ACTIVE).read_text())
            entries[str(pids[who])]["started"] = "1"
            (folder / runs.ACTIVE).write_text(json.dumps(entries))
        elif done == "terrain":
            airlock = runner.line_nodes(["airlock"], False)
            assert would_make(runner, airlock) == ["terrain", "build@airlock"], step
            assert runner.run_node(terrain, None) == ACCEPTED, step
            assert would_make(runner, airlock) == ["build@airlock"], step
        else:
            listed.clear(), judged.clear()
            monkeypatch.setattr(command, "run_commit", lambda *arguments, commit=commit: commit)
            said = io.StringIO()
            with contextlib.redirect_stderr(said):
                try:
                    chosen = command.claim(runner, [who], False, argparse.Namespace(stage=None, detach=True, free=True))
                    code = None
                except SystemExit as stop:
                    code = stop.code
            assert listed == [True] and judged == [True], (step, listed, judged)
            assert (code, said.getvalue()) == ((stopped.REFUSED, expected + "\n") if expected else (None, "")), step
            if not expected:
                assert [graph.node_name(*node) for node in chosen] == ["terrain", "build@camp"], chosen
            assert would_make(runner, line_nodes([who], False)) == list(nodes), step
    command.run_gauges(runner, chosen, "2026-10-28T09:00:00Z")
    assert runner.remembered is None  # the still is closed before the drive opens its own
    entry = an_entry(folder, "20261017T080000-1")
    assert (folder / runs.ACTIVE).exists() and list(runs.entries(folder).values()) == [entry]


# --- a run's frozen copy of the code and its design (#45) -----------------------------------------------------------

GIT_ENV = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test",
           "GIT_COMMITTER_EMAIL": "test@example.invalid"}


def a_repo():
    """A repository with one commit: a tracked stage.py and a .gitignore leaving out .venv."""
    repo = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "stage.py").write_text("SIZE = 1\n")
    (repo / ".gitignore").write_text(".venv\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "one"], check=True, env={**os.environ, **GIT_ENV})
    return repo


def a_home():
    """A home with a read-only design (one place's surface data, 58 takes), a store folder and the frozen folder its
    runs' copies (and their own homes) sit in, as PROPS_HOME holds them."""
    home = pathlib.Path(tempfile.mkdtemp())
    (home / "design" / "surfaces").mkdir(parents=True)
    (home / "design" / "surfaces" / "hangar.json").write_text('{"takes": 58}')
    (home / "store").mkdir()
    (home / "frozen").mkdir()
    for folder in (home / "design" / "surfaces", home / "design"):
        folder.chmod(0o555)
    return home


def sync_pass_rewrites(home):
    """A sync pass's prepare mid-run: the surface data rewritten in the real design, 62 takes."""
    folder = home / "design" / "surfaces"
    folder.chmod(0o755)
    (folder / "hangar.json").chmod(0o644)
    (folder / "hangar.json").write_text('{"takes": 62}')


def make_while_the_sync_pass_writes(inputs, out, seed, params):
    sync_pass_rewrites(pathlib.Path(params["home"]))
    (out / "palette.txt").write_text(inputs["surfaces"].read_text())


# (worktree has tracked changes, --uncommitted given, the run would buy paid rows) -> refused. An untracked scratch
# file is not a change, and a free run goes on as it is.
DIRTY = {
    "changes, a buy, no --uncommitted: refused": (True, False, True, True),
    "changes and --uncommitted: runs": (True, True, True, False),
    "changes but nothing to buy: runs": (True, False, False, False),
    "clean, buying: runs": (False, False, True, False),
}


def test_a_run_works_in_its_own_copy_and_home_as_they_started_and_only_its_owner_removes_them(monkeypatch):
    """One repository and one home (its design, its store, its frozen folder) and the copies of runs started from
    them, driven through the run's own life: refused or registered by its tracked changes, frozen, run, owned, resumed
    and removed.
    2026-10-20: earth-kit@airlock's 14 bake jobs thrown away when the main checkout was pulled under its run. A clean
    tree is frozen at HEAD; one with changes (an untracked file too) at one commit of the whole tree, HEAD its parent,
    neither index nor stash moved; the copy is clean, links the running venv, and is removed with its entry; a copy git
    cannot remove still goes (2026-10-26: disk full).
    Batch 1, 2026-10-25: prepare rewrote every place's surface data mid-run; finish-route-list@street had "an input
    changed while it ran". The run's home keeps 58 takes while the real design says 62; its store is the shared one;
    the node made mid-rewrite keeps its key, the next run's home reads 62; once closed, the run's design is a link to
    the real one and what it made at its top level is moved into the real home.
    2026-10-26: six processes of a stopped run worked on in its copy for an hour and held the checkout. A node or
    nested command is frozen but not the owner; the owner's mark is not inherited; after handing on it removes
    nothing; it removes once; one process deaf to SIGTERM in the copy gets SIGKILL, another copy's is left. A resumed
    run owns its copy and home again and keeps its launch's settings (2026-11-07: Launch 33 lost its cluster and caps
    at its grow's boot).
    Break: score/graph/runs.py: '    found = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],' -> '    found = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],'
    Break: score/graph/frozen.py: '    if not git(repo, "status", "--porcelain"):' -> '    if True:'
    Break: score/graph/frozen.py: '    end([pid for pid, name in users(path.parent).items() if name == path.name])' -> '    end([])'
    Break: score/graph/frozen.py: '            shutil.copytree(entry, own / "design", symlinks=True)' -> '            (own / entry.name).symlink_to(entry.resolve())'
    Break: in runs.restart, drop `entry.get("settings")`; or in runs.new_entry, drop "settings"; or in
    runs.LAUNCH_SETTINGS, drop "SCORE_POD_" (a resumed run's pod makes waited on processor classes no pool holds)"""
    for env, value in GIT_ENV.items():
        monkeypatch.setenv(env, value)
    for name, (dirty, uncommitted, paid, refused) in DIRTY.items():
        found = runs.dirty_refusal(dirty, uncommitted=uncommitted, paid=paid)
        assert found if refused else found is None, (name, found)
    assert runs.identity("aaa111", True, "/work/one") != runs.identity("aaa111", True, "/work/two") != "aaa111"
    assert runs.identity("aaa111", False, "/work/one") == "aaa111"
    repo, home = a_repo(), a_home()
    head = frozen.git(repo, "rev-parse", "HEAD")
    assert frozen.snapshot(repo) == (head, False) and not runs.tracked_changes(repo)
    copy = frozen.make(repo, head, home / "frozen")
    own = frozen.home_copy(copy, home)
    assert own == frozen.home_of(copy)

    # the run's node is made while a sync pass rewrites the real design; the run's home holds it as it started
    stage = graph.Stage("palette", "place", make_while_the_sync_pass_writes, TEXT, PASSES,
                        files={"surfaces": "{home}/design/surfaces/{place}.json"}, params={"home": str(home)})
    store = a_store()

    def runner(root):
        return graph.Runner((stage,), graph.Environment("toy", 7, {"home": str(root)}), store,
                            model_record=lambda kind: {"kind": kind})
    before = runner(own).key(stage, "hangar")["key"]
    assert runner(own).run(["hangar"])["palette@hangar"].startswith("made: pass")
    assert (own / "design/surfaces/hangar.json").read_text() == '{"takes": 58}'
    assert runner(own).key(stage, "hangar")["key"] == before != runner(home).key(stage, "hangar")["key"]
    (own / "store" / "record.json").write_text("{}")
    assert (home / "store" / "record.json").exists()
    (own / "made").mkdir()

    # the checkout moves on under the run: an untracked file is no tracked change, a staged new file and an edited
    # tracked one are; neither reaches the copy, and the next run is frozen at one commit of the whole tree
    (repo / "new.py").write_text("NEW = True\n")
    assert not runs.tracked_changes(repo)
    (repo / "kept.txt").write_text("a")
    frozen.git(repo, "add", "kept.txt")
    assert runs.tracked_changes(repo)
    frozen.git(repo, "rm", "-q", "--cached", "kept.txt")
    (repo / "stage.py").write_text("SIZE = 3\n")
    assert runs.tracked_changes(repo)
    assert (copy / "stage.py").read_text() == "SIZE = 1\n" and frozen.git(copy, "rev-parse", "HEAD") == head
    commit, changes = frozen.snapshot(repo)
    assert changes and commit != head and frozen.git(repo, "rev-parse", f"{commit}^") == head
    assert frozen.git(repo, "diff", "--cached", "--name-only") == "" and frozen.git(repo, "stash", "list") == ""
    later = frozen.make(repo, commit, tempfile.mkdtemp())
    assert (later / "stage.py").read_text() == "SIZE = 3\n" and (later / "new.py").exists()
    if sys.prefix != sys.base_prefix:
        assert (later / ".venv").resolve() == pathlib.Path(sys.prefix).resolve()
    assert frozen.git(later, "status", "--porcelain") == ""
    (later / ".git").write_text("gitdir: /nowhere\n")
    frozen.remove(later)
    assert not later.exists()

    # resume gives the copy and its home back to a new owner, with its launch's settings
    monkeypatch.setattr(frozen, "FOLDER", home / "frozen")
    assert frozen.resumed_env(copy)[frozen.FROZEN] == str(copy) and frozen.resumed_env(copy)[frozen.OWNER] == "1"
    assert frozen.resumed_env(copy)["PROPS_HOME"] == str(own)
    assert frozen.OWNER not in frozen.resumed_env(tempfile.mkdtemp())
    monkeypatch.setenv("SCORE_CLOUD_KINDS", "pixal,blender")
    monkeypatch.setenv("SCORE_POD_CLASSES", "gpu-24gb")
    monkeypatch.setenv("SCORE_SYNC_TOKEN", "not a setting")
    kept = runs.new_entry(["run", "world1"])["settings"]
    assert kept["SCORE_CLOUD_KINDS"] == "pixal,blender" and "SCORE_SYNC_TOKEN" not in kept
    assert kept["SCORE_POD_CLASSES"] == "gpu-24gb"
    monkeypatch.delenv("SCORE_CLOUD_KINDS")
    assert frozen.resumed_env(copy, kept)["SCORE_CLOUD_KINDS"] == "pixal,blender"

    # only the owner removes it: ending every process left in it, closing its home into the real one, once
    monkeypatch.setenv(frozen.FROZEN, str(copy))
    monkeypatch.setattr(frozen, "OWNED", {"path": None, "handed_on": False})
    monkeypatch.setattr(frozen, "END_GRACE_SECONDS", 0.5)
    assert frozen.inside() and frozen.claim() is None
    monkeypatch.setenv(frozen.OWNER, "1")
    assert frozen.claim() == copy and frozen.OWNER not in os.environ and frozen.owner_env()[frozen.OWNER] == "1"
    frozen.hand_on()
    frozen.remove_owned()
    assert copy.exists()
    other_copy = copy.parent / "another-run"
    other_copy.mkdir()
    sleep = [sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"]
    left, elsewhere = subprocess.Popen(sleep, cwd=copy), subprocess.Popen(sleep, cwd=other_copy)
    try:
        time.sleep(0.3)
        assert frozen.users(copy.parent) == {left.pid: copy.name, elsewhere.pid: other_copy.name}
        frozen.OWNED["handed_on"] = False
        frozen.remove_owned()
        assert left.wait(5) == -9 and not copy.exists() and elsewhere.poll() is None
        assert str(copy) not in frozen.git(repo, "worktree", "list")
        frozen.remove_owned()  # once only
    finally:
        elsewhere.kill()
        left.kill()
    assert (home / "made").is_dir() and (own / "made").is_symlink()
    assert (own / "design").is_symlink() and (own / "design/surfaces/hangar.json").read_text() == '{"takes": 62}'
    frozen.git(repo, "worktree", "prune")


# --- a free-only run: every free node runs, a paid one is left for the Buy, nothing is cleared ---------------------
# Fault (2026-10-25): the agents' door's free run refused as a whole at its start, so no free step was tried.

def make_paint(inputs, out, seed, params):
    raise AssertionError("a paid make ran in a free-only run")


def make_paint_here(inputs, out, seed, params):
    (out / "paint.txt").write_text(f"ticket {os.environ.get(compute.TICKET)}")


def make_paint_elsewhere(code):
    """A paint make whose cloud tool ends with exit `code` (compute.CLOUD_ONLY_EXIT: refused as too big for the card)."""
    def make(inputs, out, seed, params):
        raise subprocess.CalledProcessError(code, ["python", "tools/cloud/meshparts.py", "run", "--who", "x"])
    return make


def refused_clearance(*arguments, **options):
    raise AssertionError("a clearance was asked in a free-only run")


def free_runner(make=make_paint, free_only=True):
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "brief.txt").write_text("a ship")
    table = (graph.Stage("clean", "place", make_clean, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"}),
             graph.Stage("paint", "place", make, TEXT, PASSES, after={"clean": READS}, paid=True, euros=0.5),
             graph.Stage("count", "place", make_count, TEXT, PASSES, after={"paint": READS}))
    runner = a_runner(world, a_store(), table)
    runner.free_only = free_only
    return runner


WAITS_ON_PAINT = "not run: waits on paint@hangar, paid, left for the Buy"


@dataclasses.dataclass(frozen=True)
class Leaving:
    """One run of the clean -> paint (paid, EUR 0.50) -> count table: where it runs, what it may make, what each node
    ends as (a string exactly, a compiled pattern matched from its start), whether paint has a fault report, the
    place's first line, what paint's make wrote (ticket None: no clearance was asked) and whether the run's answer
    holds exactly the nodes named (whole) or at least them."""
    here: bool
    free_only: bool
    leave_out: str | None
    make: object
    found: dict
    reported: bool | None = False
    line: str | None = None
    painted: str | None = None
    whole: bool = False


LEAVING = {
    "free-only in the cloud leaves paint for the Buy": Leaving(
        False, True, None, make_paint,
        {"clean@hangar": ACCEPTED, "paint@hangar": graph.PAID_LEFT, "count@hangar": WAITS_ON_PAINT},
        line="waits at paint@hangar", whole=True),
    "a left-out stage is not made and its reader waits": Leaving(
        False, False, "paint", make_paint,
        {"clean@hangar": ACCEPTED, "paint@hangar": graph.LEFT_OUT,
         "count@hangar": "not run: reads paint@hangar, left out of this run"}, whole=True),
    "free-only on this PC's card makes paint with no ticket": Leaving(
        True, True, None, make_paint_here,
        {"clean@hangar": ACCEPTED, "paint@hangar": ACCEPTED},
        reported=None, painted="ticket None"),
    "free-only here, too big for the card: left for the Buy, priced": Leaving(
        True, True, None, make_paint_elsewhere(compute.CLOUD_ONLY_EXIT),
        {"clean@hangar": ACCEPTED, "paint@hangar": (f"{graph.PAID_LEFT} (about EUR 0.50: meshparts.py: a job too big "
                                                     "for this PC's card, a cloud job)"),
         "count@hangar": WAITS_ON_PAINT}),
    "free-only here, the tool crashing otherwise is an error with its report": Leaving(
        True, True, None, make_paint_elsewhere(1),
        {"clean@hangar": ACCEPTED, "paint@hangar": re.compile(r"error: CalledProcessError.*fault report", re.S)},
        reported=None),
}


def test_a_run_leaves_its_paid_or_left_out_nodes_for_the_buy_with_their_readers_waiting_and_makes_the_rest(
        monkeypatch, run_registry):
    """A free-only run makes its free nodes, leaves its paid ones for the Buy (their readers waiting) and ends ok with
    its list; a run's left-out stage (`score run --leave-out`, SCORE_LEAVE_OUT; 2026-11-10: env1's PC run must not
    start sim-body rows) is not made and its reader waits on it, and a stage the table does not hold is refused. On
    this PC's card a free-only run makes its paid nodes with no ticket; one too big for its card (2026-11-02, round 45:
    people-look-parts-astronaut_spacesuit-made's meshparts needed 24 GB of card on this PC's 16 GB, park.here refused
    it inside the cloud tool's own process and the row crashed with a fault report) is left for the Buy, priced at its
    estimate, no fault report, its reader waiting; the same tool crashing otherwise is still an error with its report.
    Break: score/graph/__init__.py: '        if not (self.free_only and stage.paid) or on_this_pc():\n            return False' -> '        if True:\n            return False'
    Break: score/graph/__init__.py: `        if stage.name not in self.left_out:` -> `        if True:`
    (paint is never left out: it runs and asks its refused clearance).
    Break: score/graph/__init__.py: '        if self.free_only and on_this_pc():\n            return contextlib.nullcontext()' -> '        if False:\n            return contextlib.nullcontext()'
    Break: score/graph/__init__.py: `        if refusal is None or not (self.free_only and stage.paid and on_this_pc()):`
        -> `        if True:`"""
    from score import __main__ as command
    monkeypatch.setattr(compute, "clearance", refused_clearance)
    monkeypatch.setattr(command, "opened_pool", refused_clearance)
    monkeypatch.delenv(compute.TICKET, raising=False)
    for name, row in LEAVING.items():
        if row.here:
            monkeypatch.setenv("SCORE_CLOUD", "local")
        else:
            monkeypatch.delenv("SCORE_CLOUD", raising=False)
        runner = free_runner(row.make, row.free_only)
        if row.leave_out:
            monkeypatch.setenv(command.LEAVE_OUT, row.leave_out)
        else:
            monkeypatch.delenv(command.LEAVE_OUT, raising=False)
        runner.left_out = command.left_out_stages(argparse.Namespace(leave_out=None), runner.stages)
        found = runner.drive(["hangar"], say=quiet)
        if row.whole:
            assert set(found) == set(row.found), (name, found)
        for node, expected in row.found.items():
            if isinstance(expected, re.Pattern):
                assert expected.match(found[node]), (name, node, found)
            else:
                assert found[node] == expected, (name, node, found)
        if row.reported is not None:
            assert report_of(runner, "paint@hangar").exists() == row.reported, name
        if row.line:
            assert runner.lines(["hangar"], whole=False)["hangar"][0] == row.line, (name, runner.lines(["hangar"]))
        if row.painted:
            painted = runner.store.checkout(runner.store.accepted("paint@hangar")) / "paint.txt"
            assert painted.read_text() == row.painted, name  # no clearance: a real paid point inside would refuse

    monkeypatch.delenv("SCORE_CLOUD", raising=False)
    monkeypatch.delenv(command.LEAVE_OUT, raising=False)
    with pytest.raises(graph.Blocked, match="left for the Buy"):
        free_runner().cleared("paint@hangar", 0.5)
    said, _, status = run_printing(free_runner(), ["hangar"], free=True)
    assert status.startswith("ok, free-only, 1 free rows stand, 0 failed, 1 paid rows left for the Buy"), said
    assert "  left for the Buy: paint@hangar" in said and "  waits on a paid row: count@hangar" in said, said
    stages = free_runner().stages
    assert command.left_out_stages(argparse.Namespace(leave_out="count"), stages) == {"count"}
    with pytest.raises(SystemExit, match="pain is no stage"):
        command.left_out_stages(argparse.Namespace(leave_out="pain"), stages)
    assert compute.cloud_only(RuntimeError("wrapped")) is None
    try:
        try:
            raise compute.CloudOnly("a meshparts job needs about 24 GB of card")
        except compute.CloudOnly as refusal:
            raise RuntimeError("its row") from refusal
    except RuntimeError as error:
        assert str(compute.cloud_only(error)) == "a meshparts job needs about 24 GB of card"


# --- an optional read the run makes: the people line a place's cast reads ------------------------------------------
# Fault (Buy of 2026-10-24): no Buy held a people-* node, since the cast read the dress rows only as optional and an
# optional read not usable now was left out of the run's line; the people were never made.

def make_look(inputs, out, seed, params):
    if "explode" in inputs["brief"].read_text():
        raise RuntimeError("the look fell over")
    (out / "look.txt").write_text(inputs["brief"].read_text())


def make_dress(inputs, out, seed, params):
    if "torn" in (inputs["look@people"] / "look.txt").read_text():
        raise SystemExit("no card for the dress answered")
    (out / "dress.txt").write_text((inputs["look@people"] / "look.txt").read_text())


def make_cast(inputs, out, seed, params):
    (out / "cast.txt").write_text("dressed" if "dress" in inputs else "undressed")


def people_runner(text, unread=None):
    """A look on the people line, a paid dress row of the environment reading it beside, a cast at each place reading
    the dress as optional (but at a place `unread` leaves it out)."""
    data, world = a_world_of(["people"])
    (data / "people" / "brief.txt").write_text(text)
    look = graph.Stage("look", "place", make_look, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"},
                       applies=lambda place: place == "people")
    dress = graph.Stage("dress", "world", make_dress, TEXT, PASSES, paid=True, euros=0.0, beside={"look": READS},
                        neighbours=lambda place: ["people"])
    cast = graph.Stage("cast", "place", make_cast, TEXT, PASSES, after={"dress": READS}, optional=("dress",),
                       applies=lambda place: place != "people", unread=unread)
    return a_runner(world, a_store(), (look, dress, cast))


def test_a_run_holds_prices_and_waits_on_the_optional_reads_it_makes_and_runs_without_one_that_stopped():
    """The people line's nodes are in the run whole or not, priced, and held for each place that reads them; the cast
    waits on its dress and takes it, and runs without it once its line stopped; a place whose cast leaves the dress
    unread (sim-body at a place whose cast wears no pilot: 2026-11-11) neither waits on it nor reads it; a dress
    that errored (no card answered) holds the cast, not run, rather than let it be made and keyed without it
    (2026-11-12: palette ran without an errored pixal and re-keyed a place's surfaces).
    Breaks (each applied once, seen red, reverted), in score/graph/__init__.py:
    'if before not in unread and (' -> 'if True and (';
    '    return [name for name in optional if name in line and name not in stood and name not in stopped]' -> '    return []'
    (the cast starts before its dress is settled and is made undressed);
    '    return [name for name in optional if done.get(name, "").startswith("error")]' -> '    return []'
    (the cast runs without its errored dress and is made undressed);
    '            for before in self.read_nodes(*reading.pop(), every=True):\n                if node_name(*before) not in names:\n                    names.add(node_name(*before))\n                    reading.append(before)\n        others' -> '            for before in self.read_nodes(*reading.pop(), every=False):\n                if node_name(*before) not in names:\n                    names.add(node_name(*before))\n                    reading.append(before)\n        others'"""
    runner = people_runner("a suit")
    for whole in (True, False):
        names = {graph.node_name(*node) for node in runner.line_nodes(PLACES, whole)}
        assert {"look@people", "dress", "cast@hangar", "cast@station"} <= names, (whole, names)
    assert [buy.node for buy in rebuy.buys(runner, runner.line_nodes(PLACES, False))] == ["dress"]
    held = rebuy.held_for(runner, runner.line_nodes(PLACES, True), set(PLACES))
    assert held["dress"] == held["look@people"] == set(PLACES) and held["cast@hangar"] == {"hangar"}, held
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"].startswith("made: pass"), found
    assert accepted_text(runner.store, "cast@hangar", "cast.txt") == "dressed"
    assert accepted_text(runner.store, "cast@station", "cast.txt") == "dressed"
    runner = people_runner("explode")
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"] == "not run: its line stopped at look@people", found
    assert accepted_text(runner.store, "cast@hangar", "cast.txt") == "undressed"
    runner = people_runner("a torn suit")
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"].startswith("error"), found
    assert found["cast@hangar"] == found["cast@station"] == "not run: waits on dress", found
    runner = people_runner("a suit", unread=lambda place: {"dress"} if place == "station" else ())
    assert runner.optional_nodes(runner.stages["cast"], "station") == [], "station's cast waits on the dress"
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"].startswith("made: pass"), found
    assert accepted_text(runner.store, "cast@hangar", "cast.txt") == "dressed"
    assert accepted_text(runner.store, "cast@station", "cast.txt") == "undressed"


def make_rung(inputs, out, seed, params):
    (out / "rung.txt").write_text(str(len(inputs)))


# Files laid in the driven ladder's store beside its own (none of its nodes is clean), and each prefix's keys as a
# store listing walking only the prefix's own folder gives them, worked out by hand: the .partial file left out.
LAID = ("accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json", "accepts/clean@station/1.json",
        "records/clean@hangar/k.json", "loose/ab", "top.json", "accepts/clean@hangar/3.json.9.partial")
PREFIX_KEYS = {"accepts/clean@hangar/": ["accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json"],
               "accepts/clean@": ["accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json",
                                  "accepts/clean@station/1.json"],
               "records/clean@hangar/k": ["records/clean@hangar/k.json"], "rejects/x/": [], "top": ["top.json"],
               "nothing/here/": []}

# A waiting pass's kept reads (graph.forget's `known`) and, by what ended, the nodes whose reads stay kept, worked out
# by hand: a node of an ended node's place or one reading it is dropped, all of them when an environment node ended.
KNOWN = {"count@hangar": {"earlier": ["clean@hangar"]}, "tally@hangar": {"earlier": []},
         "count@station": {"earlier": ["clean@station"]}, "meet@station": {"earlier": ["clean@hangar"]},
         "film": {"earlier": []}}
FORGOTTEN = ((frozenset({"clean@hangar"}), {"count@station"}), (frozenset({"film"}), set()))


def test_a_pass_lists_each_prefix_once_from_its_own_folder_and_works_out_each_key_once_and_only_the_runs_own_nodes(
        monkeypatch):
    """A pass of the store that writes nothing (a drive's pass, lines, status, a finished node's verdict) lists each
    prefix once, walking only the prefix's own folder, works out each key once and looks only at its run's own nodes.
    2026-10-14: the store's whole walk on each call held a run at one core for hours. A runner puts scoped_keys on
    every folder store, and it answers every prefix as the whole walk does, its .partial files left out (PREFIX_KEYS, and
    the driven store's "accepts/" and "").
    Break: score/graph/__init__.py: '             if path.is_file() and not path.name.endswith(".partial"))' ->
    '             if path.is_file())' -> "accepts/clean@hangar/" lists the .partial file.
    2026-10-12: `score status` walked the whole store for every lookup, over five minutes; 2026-10-16: then once a
    finished node, holding runs at their end. Batch 1 (2026-10-25): each pass worked out its waiting nodes' optional
    reads' keys outside a `still` pass, once a path through every node they read; passes took over an hour and the
    pool billed. One world: a ladder at two places (each rung reads the two below) read as optional by a top row. Its
    drive works out no key in the drive's process outside a pass, nor twice in one; then two passes (lines, status)
    list each prefix once each and work out each of the 16 keys once each; a finished node's verdict in a store of
    15,000 unrelated keys lists only its run's.
    Break: score/graph/__init__.py: '        self.store.objects.keys = listed_once(self.store.objects.keys)' -> '        self.store.objects.keys = self.store.objects.keys'
    Break: score/graph/__init__.py: '            with self.still():  # each key and plan worked out once a pass' ->
    '            with contextlib.nullcontext():  # each key and plan worked out once a pass'
    2026-10-28: the waiting pass read each plan's JSON again for every node asking (about 38k loads a pass) and
    worked out every waiting node's reads again every turn. The ladder's first rung applies by a plan: one still pass
    (lines) loads each place's plan once; its drive, held for memory for several turns, works out each first rung's
    reads once; a node's kept reads are dropped when a node of its place or one it reads ended, all of them when an
    environment node ended (KNOWN, FORGOTTEN).
    Break: score/graph/__init__.py: '            with plans.one_moment():\\n                yield' -> '            yield'
    Break: score/graph/__init__.py: '                    earlier = kept(known, node, "earlier", self.earlier, stage, place)'
    -> '                    earlier = self.earlier(stage, place)'
    Break: score/graph/__init__.py: '                 or node.partition("@")[2] in places' -> '                 or False'"""
    from score.review import plans
    loads = []
    data, world = a_world_of(PLACES)
    for place in PLACES:
        (data / place / "brief.txt").write_text("a rung")
    rungs = [graph.Stage("rung0", "place", make_look, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"},
                         applies=lambda place: plans.once("toy plan", None, place, lambda: loads.append(place) or True))]
    for number in range(1, 7):
        rungs.append(graph.Stage(f"rung{number}", "place", make_rung, TEXT, PASSES,
                                 after={f"rung{below}": READS for below in (number - 1, number - 2) if below >= 0}))
    top = graph.Stage("top", "place", make_cast, TEXT, PASSES, after={"rung6": READS}, optional=("rung6",))
    runner = a_runner(world, a_store(), (*rungs, top))
    nodes = {graph.node_name(stage, place) for stage in (*rungs, top) for place in PLACES}
    drive_pid, worked, passes, walks = os.getpid(), [], [], []
    work = runner.worked_out_key

    def counted(stage, place):
        if os.getpid() == drive_pid:
            if runner.remembered is not None and not any(seen is runner.remembered for seen in passes):
                passes.append(runner.remembered)
            worked.append((len(passes) if runner.remembered is not None else None, graph.node_name(stage, place)))
        return work(stage, place)
    runner.worked_out_key = counted
    monkeypatch.delenv(graph.FLOOR_VARIABLE, raising=False)
    taken = faked(monkeypatch, [0.5 * FLOOR] * 8 + [100 * FLOOR])  # the first rungs held for memory 8 turns
    monkeypatch.setattr(graph, "HELD", lambda pids: dict.fromkeys(pids, 0))
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    calls, earlier = [], graph.Runner.earlier
    monkeypatch.setattr(graph.Runner, "earlier", lambda self, stage, place: calls.append(
        graph.node_name(stage, place)) or earlier(self, stage, place))
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert all(found[f"top@{place}"].startswith("made: pass") for place in PLACES), found
    assert len(taken) > 8 and calls.count("rung0@hangar") == calls.count("rung0@station") == 1, (len(taken), calls)
    assert None not in {each for each, _ in worked}, worked
    assert len(worked) == len(set(worked)), sorted(worked)
    store_class, objects = type(runner.store.objects), runner.store.objects
    assert store_class.keys is graph.scoped_keys
    root = objects.root
    for key in LAID:
        (root / key).parent.mkdir(parents=True, exist_ok=True)
        (root / key).write_text("{}")
    for prefix, keys in PREFIX_KEYS.items():
        assert graph.scoped_keys(objects, prefix) == keys == graph.WHOLE_WALK(objects, prefix), prefix
    for prefix in ("accepts/", ""):
        assert graph.scoped_keys(objects, prefix) == graph.WHOLE_WALK(objects, prefix), prefix
    walk = store_class.keys
    monkeypatch.setattr(store_class, "keys", lambda self, prefix: walks.append(prefix) or walk(self, prefix))
    worked.clear()
    loads.clear()
    assert {state for state, _ in runner.lines(PLACES).values()} == {"done"}
    assert sorted(loads) == sorted(PLACES), loads
    assert "accepted" in runner.status(PLACES)["top@hangar"]
    assert walks and "" not in walks and len(walks) == 2 * len(set(walks)), walks
    assert None not in {each for each, _ in worked} and len(worked) == len(set(worked)), sorted(worked)
    assert sorted(node for _, node in worked) == sorted(2 * list(nodes)), sorted(worked)
    assert runner.remembered is None and "keys" not in vars(runner.store.objects)
    for area in ("records", "judgements", "accepts"):
        for folder in range(100):
            unrelated = root / area / f"elsewhere{folder}@far"
            unrelated.mkdir(parents=True)
            for index in range(50):
                (unrelated / f"{index}.json").write_text("{}")
    walks.clear()
    started = time.monotonic()
    assert runner.conclude(top, "hangar", "made") == ("made", True)
    assert time.monotonic() - started < 1.0
    assert walks and all(prefix.split("/")[1] in nodes for prefix in walks), walks
    for ended, staying in FORGOTTEN:
        known = json.loads(json.dumps(KNOWN))
        graph.forget(known, set(ended))
        assert set(known) == staying, (ended, known)


# --- a gap's chain: every node its place still needs, for pricing ---------------------------------------------------
#     draw -> shape -> gap <- part (its input missing)
#     gap -> finish -> complete -> film,  gap -> aside (an end: nothing reads it)
#     people (optional to complete, not made), alone (an end of its own)

def make_copy(inputs, out, seed, params):
    source = inputs.get("brief") or next(path for name, path in inputs.items() if name != "brief")
    found = source if source.is_file() else next(source.glob("*.txt"))
    (out / "text.txt").write_text(found.read_text())


def chain_stage(name, after=(), paid=False, **more):
    return graph.Stage(name, "place", make_copy, TEXT, PASSES, after={before: READS for before in after}, paid=paid,
                       euros=1.0 if paid else None, **more)


CHAIN_TABLE = [chain_stage("draw", files={"brief": "{data}/{place}.txt"}), chain_stage("shape", ("draw",)),
               chain_stage("part", paid=True, files={"brief": "{data}/{place}-part.txt"}),
               chain_stage("gap", ("shape", "part"), paid=True), chain_stage("finish", ("gap",), paid=True),
               chain_stage("aside", ("gap",), paid=True), chain_stage("people", paid=True),
               chain_stage("complete", ("finish", "people"), optional=("people",)),
               chain_stage("film", ("complete",), paid=True), chain_stage("alone", paid=True)]


def chain_runner():
    """The chain table with draw and shape made and standing at the hangar; part's input is missing."""
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = a_runner(graph.Environment("toy", 1, {"data": data}), a_store(), CHAIN_TABLE)
    for name in ("draw", "shape"):
        assert runner.run_node(runner.stages[name], "hangar").endswith("accepted automatically"), name
    return runner


def chained(runner, name):
    with runner.still():
        return chain.gap_chain(runner, runner.stages[name], "hangar", chain.readers(runner, ["hangar"]))


def test_a_gaps_chain_is_every_node_its_place_still_needs_up_to_its_lines_ends_and_no_pass_holds_it_over():
    """A node that stands is left out and ends its branch (draw, shape); one that cannot be keyed (part: no input) is
    in; later nodes are in up to the line's ends past the completion (film), an optional read too (people); an end not
    reading the gap's node (alone) is the line's, not the gap's. Once draw's input changes nothing stands, and the
    next pass walks through draw rather than holding the last pass's reading over.
    Break: score/graph/chain.py: '            if runner.standing(*before) is not None:' -> '            if True:'
    Break: score/graph/__init__.py: '            del self.store.objects.keys\n            self.remembered = None' ->
    '            del self.store.objects.keys'"""
    gap_line = {"aside@hangar": True, "complete@hangar": False, "film@hangar": True, "finish@hangar": True,
                "gap@hangar": True, "part@hangar": True, "people@hangar": True}
    runner = chain_runner()
    with runner.still():
        files = runner.files_of(runner.stages["draw"], "hangar")
        reading = chain.readers(runner, ["hangar"])
        ends = sorted(end.name for end, _ in chain.ends(runner, "hangar", reading))
        found = {"gap": chain.gap_chain(runner, runner.stages["gap"], "hangar", reading),
                 "line": chain.line_chain(runner, "hangar", reading)}
    assert files == {"brief": "{data}/{place}.txt"}
    assert ends == ["alone", "aside", "film"], ends
    assert found == {"gap": gap_line, "line": {**gap_line, "alone@hangar": True}}, found
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")  # draw's key moves: nothing stands
    moved = chained(runner, "gap")
    assert {"draw@hangar", "shape@hangar", "part@hangar"} <= set(moved) and moved["draw@hangar"] is False, moved


# --- what a run would buy, and the refusal of a dear re-buy without its reason --------------------------------------
# Fault (2026-10-12): one library change re-rendered every place and re-drew every view map, about EUR 50, unsaid.

DRAW = graph.Stage("draw", "place", make_copy, TEXT, PASSES, files={"brief": "{data}/{place}.txt"})
RENDER = graph.Stage("render", "place", make_copy, TEXT, PASSES, after={"draw": READS}, paid=True, euros=4.0)
BAKE = graph.Stage("bake", "place", make_copy, TEXT, PASSES, after={"render": READS}, paid=True, euros=3.0)


def make_missing_jobs(inputs, out, seed, params):
    raise FileNotFoundError("no jobs file at render-jobs.json")


def make_to_the_rent(inputs, out, seed, params):
    """A runner of its own that stops at its rent point as compute.require_cleared does under SCORE_FREE_ONLY=1."""
    subprocess.run([sys.executable, "-c", "import os, sys; sys.exit('a gpu-24gb in nowhere: refused, this process "
                    "runs free only (SCORE_FREE_ONLY=1)' if os.environ.get('SCORE_FREE_ONLY') == '1' else 0)"],
                   check=True)


def make_hashing(inputs, out, seed, params):
    time.sleep(60)


def make_through_the_client(inputs, out, seed, params):
    """Starts the renting client (graph.CONTAINER_CLIENTS) as surfaces-bake does: its paid point."""
    subprocess.run([sys.executable, "tools/cloud/blender_cloud.py", "run", "job.json"], check=True)


def a_hall_runner(stages):
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    return a_runner(graph.Environment("toy", 1, {"data": data}), a_store(), stages)


def a_buying_runner(render=RENDER):
    return a_hall_runner([DRAW, render, BAKE])


@pytest.fixture
def committed(monkeypatch):
    """Records made at a committed tree (same_requests reads their commit), the month's books open."""
    monkeypatch.setattr(_code, "git_commit", lambda: {"commit": "c0ffee", "uncommitted": False})
    monkeypatch.setattr(compute, "books_refusal", lambda: None)


def made(runner):
    for stage in runner.stages.values():
        assert runner.run_node(stage, "hangar").endswith("accepted automatically"), stage.name
    return runner


def judge_dropped(output, inputs, evidence):
    if evidence is None:
        return checks.Verdict("dropped", checks.UNKNOWN, "no drop run")
    return checks.Verdict("dropped", checks.PASS, "dropped")


def gather_drop(output, inputs, folder):
    (folder / "drop.txt").write_text("still")
    return folder / "drop.txt"


def make_with_rejects(inputs, out, seed, params):
    make_copy(inputs, out, seed, params)
    (out / rebuy.UNCACHED).write_text(json.dumps({"asks": 2, "euros": 0.134}))


def same_reads_of_the_draw(place):
    """A render's files rule saying the remade draw hands it what it read (carry.foreseen_same)."""
    return {}


same_reads_of_the_draw.same_reads = lambda runner, stage, place, moving: moving == ["draw@hangar"]

# The tables a run prices: each a hall's brief drawn, then paid rows reading it.
PRICED_TABLES = {
    "bought": [DRAW, RENDER, BAKE],
    "reads kept": [DRAW, dataclasses.replace(RENDER, files=same_reads_of_the_draw), BAKE],
    "rejected asks": [DRAW, dataclasses.replace(RENDER, make=make_with_rejects), BAKE],
    "optional look": [DRAW, RENDER, graph.Stage("look", "place", make_copy, TEXT, PASSES, after={"render": READS},
                                                optional=("render",), paid=True, euros=2.0)],
    "evidence": [DRAW, graph.Stage("place", "place", make_copy, TEXT,
                                   (checks.Check("dropped", judge_dropped, evidence="a drop run"),),
                                   after={"draw": READS}, gatherers={"dropped": (gather_drop, 1.5)})],
}
EVERY = "every"  # made: every row of the table, each accepted automatically


@dataclasses.dataclass(frozen=True)
class Priced:
    """One world a run prices, and the buys it lists, worked out by hand. `made` names the rows made before
    (EVERY: all of them, each accepted automatically); `changes` what moved after: the hall's brief, a row's code,
    the draw's code narrowed with a proof (a kept node), the drop run gathered. `cached_asks` is whether a request
    builder changed since, render asking Google from its cache; `asks_from` swaps render's make, `asks` what
    rebuy.asks_google says of it. `fields` are the buys' fields compared with `buys`; `refused` is None for no
    refusal, a text in it, or ... when not asked."""
    table: str
    buys: tuple
    made: object = ()
    changes: tuple = ()
    fields: tuple = ("node", "euros", "again")
    why_has: str = ""
    refused: object = ...
    reason: tuple = ()  # a reason given, then the ledger entry's kind, euros and estimate
    listed: str = ""
    kept_as: object = ...
    cached_asks: object = None
    asks_from: str = ""
    asks: object = None


FIRST_BUYS = (("render@hangar", 4.0, False), ("bake@hangar", 3.0, False))
PRICED = {
    "never made: each paid row a buy, no refusal": Priced("bought", FIRST_BUYS, refused=None),
    "made, nothing moved": Priced("bought", (), made=EVERY),
    "brief moved: both again, EUR 7 refused without a reason": Priced(
        "bought", (("render@hangar", 4.0, True), ("bake@hangar", 3.0, True)), made=EVERY, changes=("brief",),
        why_has="reads draw@hangar", refused="EUR 7.00", reason=("the owner changed the hall's brief", "rebuy", 0, 7.0)),
    "bake's code moved: bake alone, EUR 3 needs no reason": Priced(
        "bought", (("bake@hangar", 3.0),), made=EVERY, changes=("code bake",), fields=("node", "euros"),
        why_has="code changed", refused=None),
    "rows after a node kept by a proof still buys": Priced(
        "bought", (("render@hangar",), ("bake@hangar",)), made=("draw",), changes=("narrowed draw",),
        fields=("node",)),
    "an optional reader keys on the kept output": Priced(
        "optional look", (), made=EVERY, changes=("narrowed draw",), kept_as={}),
    "a read the rule foresees the same keeps its readers": Priced("reads kept", (), made=EVERY, changes=("brief",)),
    "a row to make buys its evidence's gather": Priced(
        "evidence", (("place@hangar", 1.5, "dropped"),), fields=("node", "euros", "evidence"),
        listed="buy place@hangar evidence dropped: EUR 1.50"),
    "an output waiting on that evidence alone buys it": Priced(
        "evidence", (("place@hangar", "evidence missing: dropped"),), made=("draw", "place"), fields=("node", "why")),
    "the evidence gathered buys nothing": Priced("evidence", (), made=("draw", "place"), changes=("gathered",)),
    "a route list's make asks Google": Priced(
        "bought", FIRST_BUYS, asks_from="score.stages.surfaces.route_list:make_list", asks=True),
    "a physics trial's make asks no model": Priced(
        "bought", FIRST_BUYS, asks_from="score.stages.physics:make_trial", asks=False),
    "the same Google ask is cached at EUR 0, moving nothing after it": Priced(
        "bought", (("render@hangar", 0.0),), made=EVERY, changes=("code render",), fields=("node", "euros"),
        why_has="cached", cached_asks=False),
    "a bake changed behind a cached ask is bought": Priced(
        "bought", (("render@hangar", 0.0), ("bake@hangar", 3.0)), made=EVERY, changes=("code render", "code bake"),
        fields=("node", "euros"), cached_asks=False),
    "its wording changed, both at their estimates": Priced(
        "bought", (("render@hangar", 4.0), ("bake@hangar", 3.0)), made=EVERY, changes=("code render",),
        fields=("node", "euros"), cached_asks=True),
    "answers the shape check dropped are priced as the output names": Priced(
        "rejected asks", (("render@hangar", 0.134), ("bake@hangar", 3.0)), made=EVERY, changes=("code render",),
        fields=("node", "euros"), cached_asks=False),
}


def moved(runner, change):
    """What moved after the rows were made (Priced.changes)."""
    if change == "brief":
        (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    elif change.startswith("code "):
        runner.code_versions[change.split()[1]] = f"{change} changed"
    elif change == "narrowed draw":
        runner.code_versions["draw"] = "only narrowed"
        runner.narrowing_proof = lambda stage, place, keyed: stage is DRAW
    else:
        runner.gather(runner.stages["place"], "hangar", ["dropped"])


@pytest.mark.parametrize("row", PRICED.values(), ids=PRICED.keys())
def test_a_run_buys_each_paid_key_it_would_make_at_its_price(row, committed, monkeypatch):
    """A run lists as a buy each paid row it would make: rows never made at their estimates; a moved brief or code
    as re-buys, over EUR 5 refused without a reason and a given one in the ledger. Rows after a node kept by a proof
    are still buys (fault 2026-10-24: the greenhouse's kept plan hid its prop route); a row reading a kept node
    optionally keys on its kept output, never as run without it (fault 2026-11-07: a plan kept by its remake dropped
    pixal from 27 palettes' keys, EUR 106 of surfaces re-buys listed); a row whose content rule says the remade read
    hands it what it read is kept, as are its readers (the square's plan redrawn without surplus items, 2026-11-07).
    A free row's paid evidence gather is a buy at its estimate (EUR 1.50) until gathered (Buy of 2026-10-24: the
    likeness's DINOv2 and the assembly's drop run were spent at run time in no price). The re-buy check knows a row
    of cached model asks (fault 2026-10-28: asks_google looked for google_spend.py among a row's source files, where
    a framework file never is). A render asking Google what it asked before is EUR 0 and moves nothing after it; a
    bake changed behind it is still bought; its wording changed, both are bought at their estimates; a close-up the
    shape check rejected leaves Google's cache, so the re-ask is priced at what the output names (owner, 2026-10-24).
    Break: score/graph/rebuy.py: '    if again > LIMIT and not (reason or "").strip():' -> '    if again > 2 * LIMIT and not (reason or "").strip():'
    Break: score/graph/__init__.py: '        if node in self.kept_as:' -> '        if node in ():'
    Break: score/graph/rebuy.py: 'stage.files.same_reads(runner, stage, place, moving))' -> 'False)'
    Break: score/graph/rebuy.py: '    paid = {name: euros for name, (_, euros) in stage.gatherers.items() if euros}' -> '    paid = {}'
    Break: score/graph/rebuy.py: '    return asks_cached(stage)' -> '    return False'
    Break: score/graph/rebuy.py: '            cached = stage.paid and same_requests(runner, stage, node, parts)' -> '            cached = False'"""
    stages = list(PRICED_TABLES[row.table])
    if row.asks_from:
        module, name = row.asks_from.split(":")
        stages[1] = dataclasses.replace(stages[1], make=getattr(importlib.import_module(module), name))
        _code.search_folders.cache_clear()  # its folders on the path, as a run's table import puts them before any key
        assert rebuy.asks_google(stages[1]) is row.asks
    runner = a_hall_runner(stages)
    if row.made == EVERY:
        made(runner)
    for name in () if row.made == EVERY else row.made:
        runner.run_node(runner.stages[name], "hangar")
    if row.cached_asks is not None:
        monkeypatch.setattr(rebuy, "asks_google", lambda stage: stage.name == "render")
        monkeypatch.setattr(rebuy, "builders_changed", lambda commit: row.cached_asks)
    for change in row.changes:
        moved(runner, change)
    found = rebuy.buys(runner, list(runner.nodes(["hangar"])))
    assert [tuple(getattr(buy, field) for field in row.fields) for buy in found] == list(row.buys), found
    assert row.why_has in (found[0].why if row.why_has else ""), found
    refusal = rebuy.refusal(found, None)
    assert row.refused is ... or (refusal is None if row.refused is None else row.refused in refusal), refusal
    if row.reason:
        reason, *entry = row.reason
        assert rebuy.refusal(found, reason) is None
        logged = rebuy.ledger_entry(found, reason)
        assert [logged["kind"], logged["euros"], logged["estimate"]] == entry, logged
    assert row.listed in rebuy.listing(found)
    assert row.kept_as is ... or runner.kept_as == row.kept_as, runner.kept_as


def test_every_file_that_words_a_google_request_is_a_request_builder():
    """Audit (2026-10-22): the finish route's list, recheck, palette and library wordings were left out, so an edit
    there was priced as a cached ask at EUR 0 while the run paid again. A code walk, not a shape test of an output: a
    file that builds a request body (`def ..._body(`) and reaches Google through google_spend, google_batch or
    finish_ask is a builder, and so is the batch client.
    Break: score/graph/rebuy.py: '                    "score/stages/surfaces/body_faces.py")' -> '                    )'"""
    reaches = re.compile(r"^\s*(import|from)\s+(\S+\.)?(google_spend|google_batch|finish_ask)\b", re.MULTILINE)
    wording = re.compile(r"^\s*def \w+_body\(", re.MULTILINE)
    found = set()
    for path in [*(_code.REPO / "score/stages").rglob("*.py"), *(_code.REPO / "tools/props").rglob("*.py")]:
        text = path.read_text(errors="replace")
        if not path.name.endswith("_test.py") and not path.name.startswith("test_") and wording.search(text) and \
                reaches.search(text):
            found.add(str(path.relative_to(_code.REPO)))
    assert found and found <= set(rebuy.REQUEST_BUILDERS), sorted(found - set(rebuy.REQUEST_BUILDERS))
    assert "tools/cloud/google_batch.py" in rebuy.REQUEST_BUILDERS
    assert all((_code.REPO / builder).is_file() for builder in rebuy.REQUEST_BUILDERS)


def test_score_run_refuses_before_it_starts_records_a_given_reason_and_plans_on_the_runners_numbers(committed,
                                                                                                   monkeypatch):
    """`score run` lists and refuses a EUR 7 re-buy with no reason, writing nothing; given one, the ledger holds it.
    `score plan --json` keeps each estimate as the guess when unmeasured; with every row's minutes measured, the run's
    time is its longest row or its minutes over --jobs, whichever is longer (C3): 10+20+30 over 2 jobs is 30, over 1
    is 60. `score preflight` (a phase's free check before it is queued, owner 2026-11-06) is clean on this plan, its
    stages' modules importing in fresh processes and its pool fitting with its class in stock; a missing input, a
    module that does not import, a pool that does not fit (the month's books unknown) and a class out of stock each
    fail by name, and it exits 1 with them. Each paid stage it buys has a node dry-run, its make run free only up to
    its paid point: one whose make reaches its rent (a runner of its own stopping there) passes; one whose make raises
    first, one whose make finishes (its paid work would run on this machine) and one past its time box each fail by
    the node's name and the cause.
    Break: score/__main__.py: '    refused = rebuy.refusal(bought, options.rebuy_reason)' -> '    refused = None'
    Break: score/__main__.py: '    failed = plan_failed + import_failed + dry_failed + pool_failed + stock_failed' -> '    failed = plan_failed + import_failed + pool_failed + stock_failed'
    Break: score/__main__.py: '    if time.monotonic() < deadline:' -> '    if True:'"""
    from score import __main__ as command
    books = compute.ledger()
    monkeypatch.setattr(books, "LEDGER", pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl")
    runner = made(a_buying_runner())
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    options = argparse.Namespace(stage=None, rebuy_reason=None, detach=False, jobs=2)
    with contextlib.redirect_stdout(io.StringIO()) as printed, pytest.raises(SystemExit) as refusal:
        command.checked_buys(runner, ["hangar"], True, options)
    assert "refused" in str(refusal.value.code) and "re-buy render@hangar: EUR 4.00" in printed.getvalue()
    assert not books.LEDGER.exists()
    planned = command.plan_json(runner, ["hangar"], True, options)
    assert [(buy["node"], buy["euros"], buy["price"]["likely_euros"], buy["price"]["guess_euros"])
            for buy in planned["buys"]] == [("render@hangar", 4.0, None, 4.0), ("bake@hangar", 3.0, None, 3.0)]
    assert planned["price"] == {"likely_euros": 0.0, "high_euros": 0.0, "guessed_euros": 7.0, "guessed": 2,
                                "likely_minutes": None, "high_minutes": None, "measured": 0, "rows": 2, "jobs": 2}
    options.rebuy_reason = "the owner changed the hall's brief"
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        command.checked_buys(runner, ["hangar"], True, options)
    assert "re-buy reason: the owner changed the hall's brief" in printed.getvalue()
    line = json.loads(books.LEDGER.read_text())
    assert line["reason"] == options.rebuy_reason and line["rebuys"] == {"render@hangar": 4.0, "bake@hangar": 3.0}
    # the run's start works its buys out in one still pass, each node's files and key once (2026-11-06: outside one a
    # detached run's start listed a node's files again per path, a git subprocess per take each time). Break: in
    # __main__.checked_buys, drop `with runner.still():`
    stilled, real_buys = [], command.rebuy.buys
    with monkeypatch.context() as patch, contextlib.redirect_stdout(io.StringIO()):
        patch.setattr(command.rebuy, "buys", lambda runner, nodes: stilled.append(runner.remembered is not None)
                      or real_buys(runner, nodes))
        command.checked_buys(runner, ["hangar"], True, argparse.Namespace(**{**vars(options), "detach": True}))
    assert stilled == [True], stilled
    timed = [{"likely_euros": 1.0, "high_euros": 2.0, "likely_minutes": minutes, "high_minutes": 2 * minutes,
              "runs": 3} for minutes in (10.0, 20.0, 30.0)]
    assert command.plan_price(timed, 2) == {"likely_euros": 3.0, "high_euros": 6.0, "guessed_euros": 0, "guessed": 0,
                                            "likely_minutes": 30.0, "high_minutes": 60.0, "measured": 3, "rows": 3,
                                            "jobs": 2}
    assert command.plan_price(timed, 1)["likely_minutes"] == 60.0
    monkeypatch.setattr(books, "books_refusal", lambda: None)
    offers = [types.SimpleNamespace(machine_class="gpu-24gb", stock_word="available")]
    tools = {"provider": types.SimpleNamespace(on_cluster=lambda: False,
                                               cloud=types.SimpleNamespace(offers=lambda classes: offers)),
             "pool": types.SimpleNamespace(shrinking=lambda sizes, hours: [(sizes, 3.6)])}
    monkeypatch.setattr(command, "cloud_tool", tools.get)
    monkeypatch.setattr(command, "card_rows", lambda *args: [("render@hangar", "hangar", 1, False)])
    monkeypatch.setattr(command, "pool_sizes", lambda rows, jobs: {"gpu-24gb": len(rows)})
    options.stage = ["render"]
    assert command.phase_modules(runner, ["render"]) == ["score.graph._toys", __name__]  # its check, its make
    assert command.preflight(runner, ["hangar"], True, argparse.Namespace(stage=["render", "concept"]))[1] == [
        "no such stage: concept"]
    summary, failed = command.preflight(runner, ["hangar"], True, options)
    assert failed == [] and "clean" in summary and "guesses only: render@hangar" in summary, (summary, failed)
    assert "2 of 2 modules import" in summary and "warm pool of {'gpu-24gb': 1} fits" in summary, summary
    (runner.world.roots["data"] / "hangar.txt").unlink()
    monkeypatch.setattr(command, "phase_modules", lambda runner, names: ["json", "score.no_such_module"])
    monkeypatch.setattr(books, "books_refusal", lambda: "the month's books are not known")
    offers[0].stock_word = "shortage"
    with contextlib.redirect_stdout(io.StringIO()) as printed, pytest.raises(SystemExit) as stopped:
        command.preflight_command(runner, ["hangar"], True, argparse.Namespace(**vars(options), phase=None))
    lines = printed.getvalue().splitlines()
    assert stopped.value.code == 1 and "4 failing" in lines[0] and "1 of 2 modules import" in lines[0], lines
    assert lines[1].startswith("missing input: draw@hangar: brief (") and "hangar.txt" in lines[1], lines
    assert lines[2].startswith("does not import: score.no_such_module: ModuleNotFoundError"), lines
    assert lines[3:] == ["pool: no warm pool fits: the month's books are not known", "out of stock: gpu-24gb"], lines
    # a node blocked by an output that answered fail is named; one waiting on a row not made yet is not (2026-11-06:
    # env1's three blockers went unnamed). Break: in __main__.preflight_plan, drop the `ANSWERED` failures
    planned = {"missing": [], "refusal": None, "buys": [], "price": {"likely_euros": 0.0, "high_euros": 0.0},
               "blocked": {"plan@square": "plan@square answered fail: held: the stairwell's doors",
                           "pixal@base": "blocked: closeup@base has not run on its current inputs"}}
    assert command.preflight_plan(planned)[1] == [
        "failing: plan@square: plan@square answered fail: held: the stairwell's doors"]
    # a re-buy is said, never failed: a Buy names its reason (2026-11-06: surfaces and people failed on it). Break:
    # in __main__.preflight_plan, put back `failed.append(planned["refusal"])`
    planned = {"missing": [], "refusal": "refused: this run would buy accepted outputs again for about EUR 47.00",
               "buys": [{"node": "bake@base", "euros": 47.0, "again": True,
                         "price": {"likely_euros": 40.0, "high_euros": 47.0}}],
               "price": {"likely_euros": 40.0, "high_euros": 47.0}, "blocked": {}}
    said, failed = command.preflight_plan(planned)
    assert failed == [] and "bought again about EUR 47.00" in said, (said, failed)
    # a bare name its package put on sys.path is imported through that package (route_views met its own circular
    # import alone). Break: in __main__.import_failure, pass `module` for `dotted_name(module)`
    from score.stages.surfaces import route_views  # noqa: F401 - loads the bare `route_views` too
    assert command.dotted_name("route_views") == "score.stages.surfaces.route_views"
    assert command.dotted_name("json") == "json" and command.import_failure("route_views") is None
    # lock-phase with no --stage locks the phase table's stages of that phase (2026-11-06: the door locks a phase by
    # name). Break: in __main__.phase_locked_line, drop the `phases.stages_of` line
    table = {name: types.SimpleNamespace(name=name, grain="place") for name in ("pixal", "brief")}
    locked = {}
    fake = types.SimpleNamespace(stages=table, nodes=lambda places: [(stage, "hangar") for stage in table.values()],
                                 lock_phase=lambda phase, nodes: locked.update(phase=phase, nodes=nodes) or {
                                     "phase": phase, "n": 1, "at": "now", "nodes": {}, "not standing": []})
    command.phase_locked_line(fake, ["hangar"], argparse.Namespace(phase="models", stage=None, node=None))
    assert locked == {"phase": "models", "nodes": [(table["pixal"], "hangar")]}, locked
    monkeypatch.setattr(command, "phase_modules", lambda runner, names: [])
    monkeypatch.setattr(books, "books_refusal", lambda: None)
    monkeypatch.setattr(command, "DRY_SECONDS", 1)
    offers[0].stock_word = "available"
    found = {}
    for make in (make_missing_jobs, make_copy, make_to_the_rent, make_hashing, make_through_the_client):
        runner = a_buying_runner(dataclasses.replace(RENDER, make=make))
        assert runner.run_node(runner.stages["draw"], "hangar").endswith("accepted automatically")
        found[make.__name__] = command.preflight(runner, ["hangar"], True, options)
    summary, failed = found["make_to_the_rent"]
    assert failed == [] and "1 of 1 paid nodes dry-run to their paid point" in summary, (summary, failed)
    assert found["make_copy"][1] == [], found  # finished with nothing to rent (its jobs kept): no failure
    # the renting client is its paid point, not Blender here (2026-11-06: surfaces-bake@airlock). Break: in
    # __main__.DryPopen, drop the `client_named` lines
    assert found["make_through_the_client"][1] == [], found
    assert [failed[0].split(" (its log ")[0] for _, failed in [found["make_missing_jobs"], found["make_hashing"]]] == [
        "dry run: render@hangar: FileNotFoundError: no jobs file at render-jobs.json",
        "dry run: render@hangar: its dry run passed its 1 s box before reaching a paid point"], found
