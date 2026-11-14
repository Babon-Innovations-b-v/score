"""The library rows' invariant: everything an environment holds is handed to the creator's library by its own command,
and every mismatch between the handover, the library and the store is named, never passed.

At the runner's seams, with a fake library command over a toy table (one environment row, one place row, one showcase
render that never passes) and a store of its own; the machine's score_lib checkout and the cloud are fakes:

    no library configured     library@garage says so, `configured` fails, the place is not complete
    library-free environment  the same environment named in library-free.json passes and is complete
    a configured library      the fake command runs once with the template's words; a second run reuses the record
    every accept handed       off by default; a run's automatic accept and the owner's start the handover (handed.py);
                              a failing command keeps the accept, writes failed.json and status counts what waits; the
                              retry covers it; an accept during a handover is taken by a second loop; an unpushed
                              report is not handed (owner, 2026-11-02, #40)
    the route                 on the toy runner, a route stage's code moves it, another stage's does not
    coverage                  an output the handover misses fails `handed` by name; a written exception covers it; an
                              output no entry holds is held through what it was made into
    copies                    a missing 3D copy is unknown, never a pass
    traced                    unknown with no library, pass on the good fixture, fail naming the photo on the bad one
    the report's shape        the shared example, as the library writes it, is on the contract field for field
                              (both repositories read it), and every report the node stores is; a covered row without
                              its keys leaves the node broken
    a slow library            a run past its timeout is a transient error, tried again by the runner (a row of the
                              runner's seams)
    no frozen copy named      a row of the runner's seams inside a run's frozen copy: the library's command (a library
                              row's, the handover process's) and handed.spawn's process name no copy in words or
                              environment; in every row a child the command left running ends with its row
                              (2026-11-05: on the conductor they kept the copy busy, so every carry, clean-cache and
                              clean-frozen refused)
    a run's stop              a row of the runner's seams: a SIGTERM while the place's handover runs reaches the
                              command in its own session, then is handled as before
    the defaults              the environment wins over the defaults, a library the defaults alone name is found; the
                              cloud's store only when no blob folder is set (rows of the runner's seams)
    the gate                  on the runner's toy table and the real one the two library rows read every row of their
                              grain (on the real table, but straight-masks), the showcase renders optional, both free,
                              and no row reads them (owner, 2026-10-22: no paid preview); on the toy table (a list baked
                              into a bake, a seed from the world's terrain, an assembly laying the library-finish
                              check's fixture) what each library node reads is held through what it was made into, and
                              the assembly's every finish traced (rows of the runner's seams)
    pictures and demos        after each run at the runner's seams, from the library folder the handover left: every
                              picture (each handed entry's too), viewer file and demo made into the one library cache;
                              a lost picture never stops the others; a 404 is not asked again (by the pictures or a
                              demo reading it) until the bytes change; a demo off the shape says what; one whose
                              example is lost or that fails is missing with why; no library, no pictures, said so
    the invariant             after each run at the runner's seams, the sweep's chain over its store and the library
                              folder the handover left: each mismatch (not handed, not in library, moved on, shown
                              nowhere, not pushed) gives exactly its problem, an agreeing library none; the library
                              folder read into rows, a library-free decision (dated, its own environment) standing for
                              a library as the node reads it too, the cockpit's findings with the entry's picture

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- checks.uncovered: an output not in the handover left out of the findings (coverage).
- backend.settings: the defaults over the environment (the defaults).
- library.route: hash every stage, not only the route's (the route).
- handover.row_faults: skip the covered rows (the report's shape: the keyless report stored, 2026-11-13).
- invariant: `if now == row["output"]` -> `if True` (moved on never found).
- invariant.newest: keep the oldest version, not the newest (history is not counted).
- sweep.library_free: take a decision with no date (library free).
- pictures.held_or_why: ask a file marked lost again (pictures and demos).
- demos.shape_problem: accept any shape kind (pictures and demos).
- library.rows: the place row reads straight-masks too (the gate, the real table).
- checks.held_through: always False (the gate: the list held through its bake fails, 2026-11-14).
- checks.judge_traced: no untraced finish ever found (the gate: the bad fixture's photo passes, 2026-11-14).
- graph.Runner conclude: drop `self.hand_accepted()` after an automatic accept; hand_on_accept True by default;
  handed.hand_waiting: no record_failure; handed.drain: hand once (`while` -> `if` and no second look after the
  lock, together); handed.covered: count an unpushed report; web.hand_accept: say started without starting (every
  accept handed, 2026-11-02).
- backend.run: words or environment not through `outside`/`outside_frozen`; no `ended(process.pid)` after the command;
  handed.spawn: the environment only its SCORE_FROZEN marks dropped (the run's PYTHONPATH kept) (no frozen copy
  named, 2026-11-05).
- backend.passed_on: its `os.killpg(group, number)` dropped, or `return {}` always (a run's stop never reaches the command in
  its own session: review of 2026-11-05).
- backend.run: a run past TIMEOUT raises RuntimeError, not TimeoutError (a slow library is never tried again,
  2026-11-14).
"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

import pytest

from score import checks, contracts, graph
from score.conductor import disk
from score.stages import library
from score.review import web
from score.stages.library import backend, demos, handed, handover, invariant, pictures, sweep, traced
from score.store import Store

REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
FAKE_STORE = {"endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
              "secret_key": "SK"}
PLACE, WORLD = "garage", "toyworld"
TOY = contracts.Contract("toy-text", 1, lambda folder: [] if any(folder.glob("*.txt")) else ["no text file"])

# The fake library: writes handover.json from reads.json as its mode file says, and writes down each call's words and
# the blob store its environment names.
FAKE = '''import json, os, pathlib, signal, subprocess, sys, time
words = sys.argv[1:]
here = pathlib.Path(__file__).parent
seen = {name: os.environ.get(name) for name in ("SCORE_LIB_BLOBS_DIR", "SCORE_LIB_S3_BUCKET", "SCORE_LIB_S3_PREFIX",
                                               "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")}
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])  # left running for its row to end
with (here / "calls.txt").open("a") as calls:
    said = {"words": words, "environment": seen, "all": dict(os.environ), "child": child.pid}
    calls.write(json.dumps(said) + "\\n")
value = lambda option: words[words.index(option) + 1] if option in words else None
out = pathlib.Path(value("--out"))
mode = (here / "mode.txt").read_text().strip()
if mode == "slow" and not (here / "slowed").exists():  # the first call runs past the timeout, once
    (here / "slowed").touch()
    time.sleep(30)
if mode == "stop" and "--place" in words:  # the run is stopped while the place's handover runs
    os.kill(os.getppid(), signal.SIGTERM)
    time.sleep(30)
reads = json.loads((out / "reads.json").read_text())
covered = [{"node": row["node"], "output": row["output"], "entries": [f"layer/{row['node']}@1"], "exception": None,
            "why": ""} for row in reads]
if mode == "miss-one":
    covered = [row for row in covered if not row["node"].startswith("made@")]
if mode.startswith("bare:"):  # these rows' outputs hold no entry of their own
    bare = mode.split(":")[1].split(",")
    covered = [dict(row, entries=[], why="no exporter takes it") if row["node"].split("@")[0] in bare else row
               for row in covered]
if mode == "exception":
    covered = [dict(row, entries=[], exception="E1") for row in covered]
copy = None if mode == "no-copy" else {"sha256": "0" * 64, "role": "gltf"}
named = json.loads((here / "named.json").read_text())  # the place's handover names these entries; pushed or not
entries = [{"address": address, "kind": address.split("/")[0], "state": "draft", "status": "new",
            "node": "made@garage", "output": "1" * 64, "source": "", "copy": copy,
            "copy_why": "no copies command in this library yet", "quality": {"score": 0.8, "measures": {}},
            "quality_why": ""} for address in (named["addresses"] if "--place" in words else [])]
saved = {"committed": "c" * 40, "pushed": named["pushed"], "why": "" if named["pushed"] else "no remote"}
report = {"schema": "library-handover", "version": 1, "backend": "command", "library": "fake", "world": value("--world"),
          "place": value("--place"), "commit": value("--commit"), "command": words, "covered": covered,
          "entries": entries, "refused": [], "saved": saved}
if mode == "example":  # the shared example as the library writes it, only this run's own words put in
    report = dict(json.loads((here / "example.json").read_text()), world=value("--world"), place=value("--place"),
                  commit=value("--commit"), command=words)
if mode == "keyless":
    report["covered"] = [{"node": "x"}]
(out / "handover.json").write_text(json.dumps(report, indent=1, sort_keys=True))
'''


@pytest.fixture(autouse=True)
def no_real_library(monkeypatch):
    """No score_lib checkout beside score's, no library setting, and a cloud backend whose store is a fixed dict."""
    for variable in backend.VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(backend.library_files, "defaults", lambda: {})
    provider = type(sys)("provider")
    provider.cloud = type("Cloud", (), {"object_store": staticmethod(lambda: FAKE_STORE)})
    monkeypatch.setitem(sys.modules, "provider", provider)


# --- the toy table --------------------------------------------------------------------------------------------------

def make_text(inputs, out, seed, params):
    (out / "made.txt").write_text(pathlib.Path(inputs["brief"]).read_text())


def make_assembly(inputs, out, seed, params):
    """The place's assembled stage: the library-finish check's fixture its brief names (data/checks/library)."""
    fixture = REPO / "data/checks/library" / pathlib.Path(inputs["brief"]).read_text()
    (out / "fixture.usda").write_text(fixture.read_text())


def judge_always(output, inputs, evidence):
    return checks.Verdict("ok", checks.PASS, "always")


def judge_never(output, inputs, evidence):
    return checks.Verdict("ok", checks.FAIL, "a showcase render that never passes here")


PASSING = (checks.Check("ok", judge_always),)
GROUND = graph.Stage("surfaces-ground", "world", make_text, TOY, PASSING, files={"brief": "{data}/briefs/ground.txt"})
TERRAIN = graph.Stage("terrain", "world", make_text, TOY, PASSING, files={"brief": "{data}/briefs/terrain.txt"})
MADE = graph.Stage("made", "place", make_text, TOY, PASSING, files={"brief": "{data}/briefs/{place}.txt"})
FILM = graph.Stage("demo-film", "place", make_text, TOY, (checks.Check("ok", judge_never),),
                   files={"brief": "{data}/briefs/{place}.txt"}, after={"made": ("toy-text", 1)})
# a list baked into a bake, a seed made from the world's terrain, the place's assembled stage
LIST = graph.Stage("list", "place", make_text, TOY, PASSING, files={"brief": "{data}/briefs/list.txt"})
BAKE = graph.Stage("bake", "place", make_text, TOY, PASSING, files={"brief": "{data}/briefs/bake.txt"},
                   after={"list": ("toy-text", 1)})
SEED = graph.Stage("seed", "place", make_text, TOY, PASSING, files={"brief": "{data}/briefs/seed.txt"},
                   after={"terrain": ("toy-text", 1)})
ASSEMBLY = graph.Stage("assembly", "place", make_assembly, contracts.Contract("toy-usd", 1, lambda folder: []),
                       PASSING, files={"brief": "{data}/briefs/assembly.txt"})
PLACE_MADE = (MADE, LIST, BAKE, SEED, ASSEMBLY)  # the place rows that pass
TABLE = (GROUND, TERRAIN, FILM, *PLACE_MADE)


def world_data(root, free=(), exceptions=None, fixture="good.usda"):
    """The toy environment's data folder: its record, the briefs (the assembly's the fixture it lays), the
    library-free decisions `free`; and beside it the home with its one place's kept plan."""
    data = root / "data"
    (root / "home/design/plans").mkdir(parents=True, exist_ok=True)
    (root / f"home/design/plans/{PLACE}.json").write_text(json.dumps({"leads": {}}))
    for path, content in {"definitions/world.json": {"name": WORLD, "seed": 7},
                          "checks/library-free.json": {"worlds": list(free)}}.items():
        (data / path).parent.mkdir(parents=True, exist_ok=True)
        (data / path).write_text(json.dumps(content))
    if exceptions is not None:
        (data / "checks/library-exceptions.json").write_text(json.dumps({"exceptions": exceptions}))
    (data / "briefs").mkdir()
    (data / "briefs/ground.txt").write_text("the ground")
    (data / f"briefs/{PLACE}.txt").write_text("the garage")
    for name in ("terrain", "list", "bake", "seed"):
        (data / f"briefs/{name}.txt").write_text(f"the {name}")
    (data / "briefs/assembly.txt").write_text(fixture)
    return data


def toy_runner(root, free=(), exceptions=None, store=None, fixture="good.usda"):
    """A runner over the toy table and its library rows, in a folder of its own, its store the home's (or `store`)."""
    data = world_data(root, free, exceptions, fixture)
    return graph.Runner((*TABLE, *library.rows(TABLE, data)),
                        graph.Environment(WORLD, 7, {"data": str(data), "home": str(root / "home")}),
                        Store.in_folder(store or root / "home/store"))


def frozen_run(home, monkeypatch):
    """A run's frozen copy and its home as graph/frozen.py lays them out (the copy's home's store a link to the real
    one), this process's environment and the library's repository naming them (the copy a repository of its own, as
    the run reads its commit there); the store folder as the run names it."""
    copy = home / "frozen/run-1"
    copy.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(copy)], check=True)
    subprocess.run(["git", "-C", str(copy), "-c", "user.name=run", "-c", "user.email=run@copy", "commit", "-q",
                    "--allow-empty", "-m", "the run's commit"], check=True)
    monkeypatch.setattr(library, "REPO", copy)
    (home / "store").mkdir(parents=True)
    pathlib.Path(f"{copy}.home").mkdir()
    pathlib.Path(f"{copy}.home/store").symlink_to(home / "store")
    monkeypatch.setenv("SCORE_FROZEN", str(copy))
    monkeypatch.setenv("PROPS_HOME", f"{copy}.home")
    monkeypatch.setenv("PYTHONPATH", f"{copy}/score/stages/props/ledger_tag{os.pathsep}/elsewhere")
    return pathlib.Path(f"{copy}.home/store")


def fixture_library(root):
    """The library folder `root` holding the entries the good fixture names (the library-finish check's own test's)."""
    for kind, entry_id in (("surface", "bare_steel"), ("surface", "deck"), ("model", "crate_1"), ("kit", "fixture"),
                           ("light", "lamp"), ("sound", "hum")):
        folder = root / "entries" / kind / entry_id / "1"
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1",
                                                       "kind": kind, "id": entry_id, "version": 1, "state": "draft",
                                                       "files": {}, "provenance": {}}))
    return root


def fake_library(root, monkeypatch, mode="full", found="environment", blobs=False, named=(), pushed=True):
    """The fake library's folder under `root`, its folder and command set where `found` says: in the environment over
    defaults naming another library, or in the defaults alone; with `blobs` a blob folder in the environment over a
    default one; the addresses its place handover names and whether it pushes. Its calls file."""
    folder = root / "library"
    folder.mkdir(parents=True)
    (folder / "handover.py").write_text(FAKE)
    (folder / "mode.txt").write_text(mode)
    (folder / "named.json").write_text(json.dumps({"addresses": list(named), "pushed": pushed}))
    (folder / "example.json").write_text((HERE / "handover_example.json").read_text())
    fixture_library(folder)
    ours = {"SCORE_LIB_ROOT": str(folder), "SCORE_LIB_COMMAND": f"{sys.executable} {folder / 'handover.py'}"}
    defaults = ours if found == "defaults" else {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"}
    if found == "environment":
        for name, value in ours.items():
            monkeypatch.setenv(name, value)
    if blobs:
        defaults = {**defaults, "SCORE_LIB_BLOBS_DIR": "/the/default/blobs"}
        monkeypatch.setenv("SCORE_LIB_BLOBS_DIR", str(root / "blobs"))
    monkeypatch.setattr(backend.library_files, "defaults", lambda: defaults)
    return folder / "calls.txt"


def driven(runner):
    """Each node of the garage run as the drive runs it (Runner.run_retrying: a transient error tried again); {node:
    what it did, a raised error's words as the drive gives them}."""
    did = {}
    for stage, place in runner.nodes([PLACE]):
        try:
            did[graph.node_name(stage, place)] = runner.run_retrying(stage, place)
        except Exception as error:  # noqa: BLE001 - the drive's own words for a node that raised (drive_node)
            did[graph.node_name(stage, place)] = f"error: {type(error).__name__}: {error}"
    return did


def library_output(runner, place=PLACE):
    """The library node's newest output folder and its judgement's verdicts."""
    stage = runner.stages[library.WORLD_ROW if place is None else library.PLACE_ROW]
    record = runner.store.record(graph.node_name(stage, place), runner.key(stage, place)["key"])
    judgement = runner.store.judgements(record["node"], record["key"])[-1]
    return runner.store.checkout(record["output"]), judgement["verdicts"]


# --- the rows at the runner's seams ---------------------------------------------------------------------------------

EXCEPTION_E1 = {"id": "E1", "place": PLACE, "prim": "/garage/*", "what": "a toy", "why": "a test",
                "allowed_by": "@owner", "allowed_on": "2026-10-18"}
DATED = {"world": WORLD, "why": "a toy", "who": "@owner", "when": "2026-10-18"}
NO_LIBRARY = {"configured": (checks.FAIL, "is", "no library configured"),
              "handed": (checks.FAIL, "has", f"made@{PLACE}"), "traced": (checks.UNKNOWN, "has", "SCORE_LIB_ROOT"),
              "saved": (checks.FAIL, "has", "no library configured")}
NEITHER_HANDED = {"world": ["not handed"], PLACE: ["not handed"]}
NOT_CONFIGURED_SAID = ((PLACE, 0, "sentence", "has", "no library is configured"),)
MADE_OUTPUT = "made"  # an entry's output: the one made@garage stands accepted with
PICTURE, PICTURE_SHA = b"\x89PNG fake picture bytes", "ab" + "0" * 62
LIBRARY = ({"address": "model/rover@1"}, {"address": "model/rover@2"})  # the garage's one entry, two versions
NAMED = ("model/rover@2",)


def row(address, made, node=f"made@{PLACE}", output=MADE_OUTPUT, state="draft", place=PLACE, world=WORLD):
    """One library row as the invariant reads it (sweep.entry_row's shape, its picture left out); `made` the output
    MADE_OUTPUT stands for."""
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    return {"address": address, "kind": kind, "id": entry_id, "version": int(version), "state": state,
            "world": world, "place": place, "node": node, "output": made if output == MADE_OUTPUT else output}


def write_entry(root, blobs, spec, made):
    """One library entry's folder from a row spec, its picture's bytes in the blob folder."""
    entry = row(**spec, made=made)
    (blobs / "blobs" / PICTURE_SHA[:2]).mkdir(parents=True, exist_ok=True)
    (blobs / "blobs" / PICTURE_SHA[:2] / PICTURE_SHA).write_bytes(PICTURE)
    folder = root / "entries" / entry["kind"] / entry["id"] / str(entry["version"])
    folder.mkdir(parents=True)
    (folder / "entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": entry["address"], "kind": entry["kind"], "id": entry["id"],
        "version": entry["version"], "state": entry["state"], "picture": {"file": "picture.png"},
        "files": {"picture.png": {"sha256": PICTURE_SHA}},
        "provenance": {key: entry[key] for key in ("world", "place", "node", "output")}}))


def seam(name, mode=None, free=(), exceptions=None, verdicts=None, accepted=True, calls=2, found="environment",
         blobs=False, broken=None, frozen=False, timeout=None, stopped=None, fixture="good.usda", library=LIBRARY,
         named=NAMED, pushed=True, hangar=False, problems=None, said=()):
    """One toy environment at the runner's seams: the fake library's mode (None: no library command), a library-free
    decision, the written exceptions; the library node's verdicts that do not pass (check: (answer, "is"/"has",
    reason text[, the nodes its findings name]), every other verdict passes), whether its library nodes are accepted
    automatically, and how often the library's command ran (each node once; a failed output is made once more, an unknown one is not, a timed-out
    run is tried again); where the library's settings are found (fake_library) and whether a blob folder is set;
    `broken`: why a report off the contract leaves both library nodes broken, with no output; `frozen`: the run in a
    frozen copy (frozen_run); `timeout`: the handover's TIMEOUT; `stopped`: the place node's error when the run is
    stopped (SIGTERM) while its handover runs; `fixture`: the library-finish check's fixture the assembly lays.
    The sweep after the run: `library` the entries the library folder holds once handed (row specs; none without a
    library), `named` the addresses the place's handover names and `pushed` whether it pushed, `hangar` a second
    place with no library node; the invariant's rules found where (`problems`, empty places left out) and what they
    say (`said`: (where, index, field, "is"/"has", text))."""
    swept = {"library": library if mode else (), "hangar": hangar, "problems": problems or {}, "said": said}
    return pytest.param(mode, free, exceptions, verdicts or {}, accepted, calls, found, blobs, broken, frozen, timeout,
                        stopped, fixture, named, pushed, swept, id=name)


@pytest.mark.parametrize(
    "mode, free, exceptions, verdicts, accepted, calls, found, blobs, broken, frozen, timeout, stopped, fixture, "
    "named, pushed, swept", (
        seam("no library configured", verdicts=NO_LIBRARY, accepted=False, problems=NEITHER_HANDED,
             said=NOT_CONFIGURED_SAID),
        seam("an undated library-free decision is no decision", free=({**DATED, "when": ""},), verdicts=NO_LIBRARY,
             accepted=False, problems=NEITHER_HANDED, said=NOT_CONFIGURED_SAID),
        seam("another environment's library-free decision", free=({**DATED, "world": "world2"},), verdicts=NO_LIBRARY,
             accepted=False, problems=NEITHER_HANDED, said=NOT_CONFIGURED_SAID),
        seam("a library-free environment", free=(DATED,)),
        seam("a configured library, a place with no library node and a handover that did not push", mode="full",
             hangar=True, pushed=False,
             problems={"hangar": ["not handed"], PLACE: ["not pushed"], "world": ["not pushed"]},
             said=(("hangar", 0, "sentence", "is",
                    "The hangar is not handed to the library yet (library@hangar: nothing stands accepted)."),
                   (PLACE, 0, "sentence", "is",
                    "The library's last handover of the garage did not push: no remote."))),
        seam("a library found by its defaults, the environment's blob folder over theirs; history and a repo-made "
             "entry never move", mode="full", found="defaults", blobs=True,
             library=({"address": "model/rover@1", "output": "out-0"}, {"address": "model/rover@2"},
                      {"address": "surface/steel@1", "node": None, "output": None}),
             named=("model/rover@2", "surface/steel@1")),
        seam("an output the handover misses", mode="miss-one",
             verdicts={"handed": (checks.FAIL, "has", f"made@{PLACE}", {f"made@{PLACE}"})}, accepted=False, calls=3,
             problems={PLACE: ["not handed"]}),
        seam("a list no entry holds is held through the bake made from it; an entry whose output moved on",
             mode="bare:list", verdicts={"handed": (checks.PASS, "has", "(1 held through")},
             library=(*LIBRARY[:1], {"address": "model/rover@2", "output": "out-old"}), problems={PLACE: ["moved on"]},
             said=((PLACE, 0, "sentence", "is",
                    "model/rover@2 was made from an output the garage no longer holds (made@garage)."),)),
        seam("an output made into nothing held fails, and a finish from a photo is named", mode="bare:list,bake,made",
             fixture="bad.usda", verdicts={"handed": (checks.FAIL, "has", "holds no entry: no exporter takes it",
                                                      {f"list@{PLACE}", f"bake@{PLACE}", f"made@{PLACE}"}),
                                          "traced": (checks.FAIL, "has", "photo_of_a_crate.png")},
             accepted=False, calls=3, problems={PLACE: ["not handed"]}),
        seam("a written exception covers it; an address the library lacks or holds withdrawn", mode="exception",
             exceptions=[EXCEPTION_E1], library=(*LIBRARY, {"address": "model/cart@1", "state": "withdrawn"}),
             named=("model/rover@2", "model/crate@1", "model/cart@1"),
             problems={PLACE: ["not in library", "not in library"]},
             said=((PLACE, 0, "address", "is", "model/crate@1"), (PLACE, 1, "address", "is", "model/cart@1"),
                   (PLACE, 1, "sentence", "has", "withdrawn"))),
        seam("an exception the data does not write covers nothing", mode="exception",
             verdicts={"handed": (checks.FAIL, "has", "E1")}, accepted=False, calls=4, problems=NEITHER_HANDED),
        seam("a missing copy is unknown, never a pass", mode="no-copy",
             verdicts={"copies": (checks.UNKNOWN, "has", "model/rover@2")}, accepted=False,
             problems={PLACE: ["not handed"]}),
        seam("the shared example report is on the contract", mode="example",
             verdicts={"handed": (checks.FAIL, "has", f"made@{PLACE}"),
                       "refused": (checks.FAIL, "has", "model old_crate from pixal@garage: no take file in the output"),
                       "quality": (checks.UNKNOWN, "has", "surface/brushed_steel@1")}, accepted=False, calls=4,
             problems=NEITHER_HANDED),
        seam("a covered row without its keys is off the contract", mode="keyless",
             broken="covered row 1 lacks entries, exception, output, why", problems=NEITHER_HANDED),
        seam("inside a run's frozen copy, nothing the library runs names it; a newest entry no handover names",
             mode="full", frozen=True,
             library=(*LIBRARY, {"address": "model/old_crate@1"}, {"address": "model/tank@1", "world": "world2"},
                      {"address": "model/hut@1", "place": "hangar"}),
             problems={PLACE: ["shown nowhere"], "world": ["shown nowhere"]},
             said=((PLACE, 0, "address", "is", "model/old_crate@1"),  # the hangar has no library node: shown on the
                   ("world", 0, "address", "is", "model/hut@1"))),  # environment
        seam("a slow library is a transient error, tried again; an entry whose node no longer has an accepted output",
             mode="slow", calls=3, timeout=2,
             library=(*LIBRARY[:1], {"address": "model/rover@2", "node": f"demo-film@{PLACE}"}),
             problems={PLACE: ["moved on"]}, said=((PLACE, 0, "sentence", "has", "no longer has accepted"),)),
        seam("a run's stop reaches the command in its own session", mode="stop", timeout=3,
             stopped="the library's handover command exited -15", problems={PLACE: ["not handed"]}),
    ))
def test_the_library_node_hands_everything_by_the_librarys_command_once_and_names_what_it_misses(
        tmp_path, monkeypatch, mode, free, exceptions, verdicts, accepted, calls, found, blobs, broken, frozen,
        timeout, stopped, fixture, named, pushed, swept):
    home = tmp_path / "home"
    called = fake_library(tmp_path, monkeypatch, mode, found, blobs, named, pushed) if mode else None
    runner = toy_runner(tmp_path, free=free, exceptions=exceptions,
                        store=frozen_run(home, monkeypatch) if frozen else None, fixture=fixture)
    monkeypatch.setattr(traced, "KEPT_PLANS", home / "design/plans")  # every place's bakes: the toy home's places
    fetches = []  # the files the cockpit's pictures and demos ask the library for

    def fetched(address, named):
        """The cache's path of every file but the ground's picture and the crate's web copy, which the store lost."""
        fetches.append((address, named))
        if (address, named) in (("ground/lost@1", "b.png"), ("model/crate@1", "web3d/light.glb")):
            raise backend.library_files.LibraryUnreachable(LOST)
        return pathlib.Path(named)

    monkeypatch.setattr(pictures, "fetched", fetched)
    monkeypatch.setattr(backend.library_files, "cache_folder", lambda: tmp_path / "cache")
    from score import stages
    # the library rows read every row of their grain (on the real table, but straight-masks: only prepare's prediction
    # reads it, score/stages/__init__.py), the showcase renders optional, the environment's film never holds the world
    # row up, both free, and no row reads them
    for table, unread, optional, world_optional in ((tuple(runner.stages.values()), set(), {FILM.name}, ()),
                                                    (stages.STAGES, {"straight-masks"}, set(library.SHOWCASE),
                                                     ("environment-film",))):
        rows = {row.name: row for row in table}
        place, world = rows[library.PLACE_ROW], rows[library.WORLD_ROW]
        assert not place.paid and not world.paid
        assert set(place.after) == {row.name for row in table if row.grain == "place"} - {library.PLACE_ROW, *unread}
        assert set(world.after) == {row.name for row in table if row.grain == "world"} - {library.WORLD_ROW}
        assert set(place.optional) | set(world.optional) == optional and world.optional == world_optional
        assert not [row.name for row in table if library.PLACE_ROW in row.after or library.WORLD_ROW in row.after]
    monkeypatch.setattr(graph, "RETRY_WAIT", 0)
    if timeout:
        monkeypatch.setattr(backend, "TIMEOUT", timeout)
    asked = []  # the handover processes handed.spawn starts: their words and environment
    monkeypatch.setattr(handed, "subprocess", type(sys)("subprocess"))
    handed.subprocess.DEVNULL, handed.subprocess.STDOUT = subprocess.DEVNULL, subprocess.STDOUT
    handed.subprocess.Popen = lambda words, **given: asked.append((words, given["env"]))
    heard = []
    before = signal.signal(signal.SIGTERM, lambda number, frame: heard.append(number))
    try:
        did = driven(runner)
    finally:
        signal.signal(signal.SIGTERM, before)
    assert asked == [] and not (home / "store" / handed.FOLDER).exists()  # handing accepts is off unless asked
    assert heard == ([signal.SIGTERM] if stopped else []), heard  # the stop handled as before, once passed on
    said = [json.loads(line) for line in called.read_text().splitlines()] if mode else []
    deadline = time.monotonic() + 5
    while any(running(call["child"]) for call in said) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not [call["child"] for call in said if running(call["child"])], "a child of the handover outlived its row"
    # neither the command's words nor its environment name a frozen copy; a copy's path moved to the main checkout's,
    # the copy home's to the real home
    assert all(copies_named(home, call["words"], call["all"]) == [] for call in said), said
    assert all("SCORE_FROZEN" not in call["all"] for call in said), said
    if frozen:
        assert all(call["all"]["PROPS_HOME"] == str(home) for call in said), said
        assert all(call["all"]["PYTHONPATH"] == f"{backend.main_checkout()}/score/stages/props/ledger_tag"
                   f"{os.pathsep}/elsewhere" for call in said), said
        # the copy named as the library's repository moved to the main checkout, in its words and its environment
        assert all(call["words"][call["words"].index("--repo") + 1] == str(backend.main_checkout())
                   and call["all"]["SCORE_REPO"] == str(backend.main_checkout()) for call in said), said
        assert disk.working(home / "frozen") == {}  # the conductor's own count: nothing works in the copy
    # the sweep's chain on the same environment: the library folder (its entries as the handover left them) read into
    # rows, the library-free decision, the invariant's problems, each place's findings.json with the entry's picture
    library_root, blob_root, swept_out = tmp_path / "library", tmp_path / "blobs", tmp_path / "swept"
    made = runner.store.accepted(f"made@{PLACE}")
    for spec in swept["library"]:
        write_entry(library_root, blob_root, spec, made)
    rows = sweep.library_rows(str(library_root) if mode else "")
    ordered = sorted(swept["library"], key=lambda spec: spec["address"].replace("@", "/"))
    assert [line for line in rows if line["world"]] == [dict(row(**spec, made=made), picture=PICTURE_SHA)
                                                        for spec in ordered], rows
    configured = (backend.kind(backend.settings()) != backend.NONE
                  or sweep.library_free(WORLD, tmp_path / "data/checks/library-free.json"))
    held = sweep.handed_of(runner.store, [PLACE, *(["hangar"] if swept["hangar"] else [])])
    problems = invariant.problems(WORLD, held, rows, {line["node"]: runner.store.accepted(line["node"])
                                                      for line in rows if line["node"]}, configured)
    assert {where: [item["rule"] for item in items] for where, items in problems.items() if items} == (
        swept["problems"]), problems
    assert set(problems) == set(held), problems
    for where, index, field, how, text in swept["said"]:
        told = problems[where][index][field]
        assert (told == text if how == "is" else text in told), (where, index, field, told)
    for where, node in held.items():
        sweep.written(where, node, problems[where], rows, str(blob_root), swept_out / where)
        on_disk = json.loads((swept_out / where / "findings.json").read_text())
        rules = swept["problems"].get(where, [])
        stands = runner.store.accepted(node["node"])
        assert on_disk["answer"] == ("fail" if rules else "pass"), on_disk
        assert on_disk["outputs"] == ({node["node"]: stands} if stands else {}), on_disk
        assert [finding["rule"] for finding in on_disk["findings"]] == rules, on_disk
        for finding in on_disk["findings"]:
            assert set(finding) == {"rule", "prim", "name", "sentence", "picture"}, finding
            if finding["name"] in {line["address"] for line in rows if line["world"]}:  # its picture beside it
                assert (swept_out / where / finding["picture"]).read_bytes() == PICTURE, finding
            else:
                assert finding["picture"] is None, finding
    # the cockpit's files from the same library folder: the pictures and the item pages' viewer files of every kind
    # fetched into the library cache, a lost one never stopping the others; every demo made from that cache; a file
    # lost before never asked again, by the pictures or a demo, until its entry names new bytes
    if not mode:
        assert pictures.run() == ("library pictures: no library folder (SCORE_LIB_ROOT, or the score_lib checkout "
                                  "beside score)")
    else:
        for address in ("model/crate@1", "surface/brass@1", "sound/drone@1", "effect/smoke@1"):
            picture_entry(library_root, address, VIEWER)
        picture_entry(library_root, "place/flat@1", {"a.png": "picture", "web3d/light.glb": "web3d"}, picture="a.png")
        picture_entry(library_root, "ground/lost@1", {"b.png": "picture"}, picture="b.png")
        # what an item page's viewer plays of each kind: the light web copy, then a model's close-up, a surface's
        # material and print, a sound's first four takes, an effect's settings; a place's only its web copy
        viewed = [("effect/smoke@1", "web3d/light.glb"), ("effect/smoke@1", "settings.json"),
                  ("model/crate@1", "web3d/light.glb"), ("model/crate@1", "closeup.png"),
                  ("place/flat@1", "web3d/light.glb"),
                  *[("sound/drone@1", named) for named in ("web3d/light.glb", "a.ogg", "b.ogg", "c.ogg", "d.ogg")],
                  *[("surface/brass@1", named) for named in ("web3d/light.glb", "material.usda", "print.png")]]
        assert pictures.viewed(library_root, None) == viewed
        shown = len(swept["library"])  # every handed entry's own picture beside the two here
        assert pictures.run() == (f"library pictures (every kind) in the cache: {shown + 1} of {shown + 2} (1 not "
                                  f"fetched, first: ground/lost@1: {LOST}); viewer files: 12 of 13 (1 not fetched, "
                                  f"first: model/crate@1: {LOST})")
        assert sorted(fetches) == sorted([*((spec["address"], "picture.png") for spec in swept["library"]),
                                          ("ground/lost@1", "b.png"), ("place/flat@1", "a.png"), *viewed]), fetches
        fetches.clear()
        assert pictures.run() == (f"library pictures (every kind) in the cache: {shown + 1} of {shown + 2} (1 not "
                                  "fetched, first: ground/lost@1: b.png lost (404 before)); viewer files: 12 of 13 (1 "
                                  "not fetched, first: model/crate@1: web3d/light.glb lost (404 before))")
        # every demo made from the same cache: the real modules found by their algorithm, a fake one an algorithm here
        real = demos.modules()
        assert "surface_recipes" in real and all(module.ALGORITHM == name for name, module in real.items())
        fakes = {}
        for name, (made_by, _) in DEMO_CASES.items():
            fakes[name] = type(sys)(name)
            fakes[name].made = made_by
        monkeypatch.setattr(demos, "modules", lambda: fakes)
        line = demos.run()
        assert line.startswith(f"library demos: 1 of 5 made into {demos.path()} (not made: "), line
        assert all(f"{name}: {expected['missing'][:120]}" in line
                   for name, (_, expected) in DEMO_CASES.items() if "missing" in expected), line
        assert json.loads(demos.path().read_text()) == {name: expected for name, (_, expected) in DEMO_CASES.items()}
        assert ("ground/lost@1", "b.png") not in fetches and ("model/crate@1", "web3d/light.glb") not in fetches
        picture_entry(library_root, "model/crate@1", VIEWER, sha="b" * 64)  # new bytes: asked again
        fetches.clear()
        pictures.run()
        assert ("model/crate@1", "web3d/light.glb") in fetches and ("ground/lost@1", "b.png") not in fetches, fetches
    if broken:
        stage = runner.stages[library.PLACE_ROW]
        assert runner.store.record(graph.node_name(stage, PLACE), runner.key(stage, PLACE)["key"]) is None
        assert did[f"library@{PLACE}"] == did["library-world"] == (
            f"broken: off its contract library-handover v1: {broken}"), did
        return
    if stopped:
        assert stopped in did[f"library@{PLACE}"] and len(said) == calls, (did, said)
        return
    output, found = library_output(runner)
    # what each read was made into, read here (the showcase render that never passed read without) and beyond
    assert {read["node"]: (read["into"], read["beyond"]) for read in handover.handed(output)} == {
        f"made@{PLACE}": (["demo-film"], []), f"list@{PLACE}": (["bake"], []), f"bake@{PLACE}": ([], []),
        f"seed@{PLACE}": ([], []), f"assembly@{PLACE}": ([], [])}, handover.handed(output)
    world_reads = handover.handed(library_output(runner, None)[0])
    assert {read["node"]: (read["into"], read["beyond"]) for read in world_reads} == {
        GROUND.name: ([], []), TERRAIN.name: ([], ["seed"])}, world_reads
    shared = handover.report(output)  # the library's report or score's own, on the contract field for field
    assert shared["backend"] == ("command" if mode else "none")
    assert sorted(shared) == sorted(handover.KEYS) and sorted(shared["saved"]) == sorted(handover.SAVED_KEYS), shared
    assert all(sorted(line) == sorted(keys) for area, keys in handover.ROWS.items() for line in shared[area]), shared
    assert set(verdicts) <= set(found), found
    for check, verdict in found.items():
        answer, how, text, *nodes = verdicts.get(check, (checks.PASS, "has", ""))
        told = verdict["reason"]
        assert verdict["answer"] == answer and (told == text if how == "is" else text in told), (check, verdict)
        assert not nodes or {finding.split(" ")[0] for finding in verdict["findings"]} == nodes[0], (check, verdict)
    waiting = dict(library.world_completion(runner, [PLACE]))
    if accepted:
        assert did[f"library@{PLACE}"].endswith("accepted automatically"), did
        assert did["library-world"].endswith("accepted automatically"), did
        assert waiting == {}, waiting
    else:
        assert "accepted" not in did[f"library@{PLACE}"], did
        assert f"library@{PLACE}" in waiting, waiting
        assert "not complete" in library.completion_line(WORLD, list(waiting.items()))
    if mode is None:
        assert ("library-world" in waiting) is not configured, waiting  # the node and the sweep read one decision
        return
    # the library's own command with the template's words, for the place's node and for the environment's
    words = [call["words"] for call in said]
    assert len(words) == calls, words
    place_words = next(said for said in words if "--place" in said)
    world_words = next(said for said in words if "--place" not in said)
    # the cloud's blob store only when no blob folder is set, and the environment's folder over the defaults'
    store = {"SCORE_LIB_BLOBS_DIR": str(tmp_path / "blobs"), "SCORE_LIB_S3_BUCKET": None, "SCORE_LIB_S3_PREFIX": None,
             "AWS_ACCESS_KEY_ID": None, "AWS_SECRET_ACCESS_KEY": None} if blobs else {
        "SCORE_LIB_BLOBS_DIR": None, "SCORE_LIB_S3_BUCKET": "a-bucket", "SCORE_LIB_S3_PREFIX": "score_lib",
        "AWS_ACCESS_KEY_ID": "AK", "AWS_SECRET_ACCESS_KEY": "SK"}
    assert all(call["environment"] == store for call in said), said

    def after(option):
        return place_words[place_words.index(option) + 1]
    assert after("--world") == WORLD and after("--place") == PLACE and after("--seed") == "7"
    route = library.runner_route(runner)
    assert after("--route") == route == world_words[world_words.index("--route") + 1]

    def moved(name):
        """The runner's route with row `name`'s code version moved."""
        return library.route(lambda stage: runner.code(stage) + ("-moved" if stage.name == name else ""),
                             runner.stages.values())
    assert moved(MADE.name) == route, "a stage off the route moved the route"
    assert moved(GROUND.name) != route, "a route stage's code did not move it"
    assert runner.key(runner.stages[library.PLACE_ROW], PLACE)["params"]["route"] == route  # in the key
    assert after("--store") == str((home / "store/objects").resolve())
    assert place_words[:3] == ["--root", str(tmp_path / "library"), "handover"], place_words  # the setting's own root
    assert "--world" in world_words, world_words
    again = runner.run([PLACE])
    assert again[f"library@{PLACE}"] == "fresh", again
    assert len(called.read_text().splitlines()) == calls, "a second run called the library again"
    if not accepted:
        return
    # every accept handed the moment it is made: the run's automatic accept and the owner's start the handover; a
    # failing handover keeps the accept and the next one covers it
    store, nodes = runner.store, lambda: handed.nodes_of(runner.stages.values(), [PLACE])
    (tmp_path / f"data/briefs/{PLACE}.txt").write_text("the garage, again")
    (tmp_path / "library/named.json").write_text(json.dumps({"addresses": list(named), "pushed": True}))  # remote back
    runner.hand_on_accept = True
    assert runner.run([PLACE])[f"made@{PLACE}"].endswith("accepted automatically")
    made = store.accepted(f"made@{PLACE}")
    spawned = [dict(zip(words[3::2], words[4::2])) for words, _ in asked]  # --world, --commit, --route
    assert asked and {job["--route"] for job in spawned} == {route}, asked  # the run's accepts started the handover
    # the detached handover process names no frozen copy either, its home the real one
    assert all(copies_named(home, words, environment) == [] for words, environment in asked), asked
    assert all(environment["PROPS_HOME"] == str(home.resolve()) for _, environment in asked), asked
    every = {None: [(row.name, store.accepted(row.name)) for row in (GROUND, TERRAIN)],
             PLACE: [(node, store.accepted(node)) for node in (f"{row.name}@{PLACE}" for row in PLACE_MADE)]}
    assert handed.waiting(store, WORLD, nodes()) == every
    job = {"world": WORLD, "seed": 7, "commit": spawned[0]["--commit"], "route": route, "repo": str(library.REPO)}
    library_command = backend.settings()["SCORE_LIB_COMMAND"]
    monkeypatch.setenv("SCORE_LIB_COMMAND", f"{sys.executable} -c 'import sys; sys.exit(3)'")
    handed.drain(store, WORLD, lambda: job, nodes, say=lambda line: None)
    assert store.accepted(f"made@{PLACE}") == made  # a failed handover never loses the accept
    assert "exited 3" in handed.failure(store, WORLD, PLACE)["error"]
    line = handed.status_line(store, WORLD, nodes())
    assert "7 accepted outputs not in the library yet (world 2, garage 5); failing: " in line, line
    monkeypatch.setenv("SCORE_LIB_COMMAND", library_command)
    loops, hand_waiting = [], handed.hand_waiting
    monkeypatch.setattr(handed, "hand_waiting", lambda *given: loops.append(
        "" if loops else handed.start(store, WORLD)) or hand_waiting(*given))  # an accept lands during the handover
    started = len(asked)
    assert web.hand_accept(store, WORLD) == "handover started" and len(asked) == started + 1  # the owner's accept
    handed.drain(store, WORLD, lambda: job, nodes, say=lambda line: None)
    assert loops == ["a handover is running: it hands this next", ""], loops  # taken by a second loop
    assert handed.failure(store, WORLD, PLACE) is None and handed.waiting(store, WORLD, nodes()) == {}
    assert handed.status_line(store, WORLD, nodes()).endswith("every accepted output is in the library")
    report = json.loads((handed.place_folder(store, WORLD, PLACE) / handover.REPORT).read_text())
    report["saved"]["pushed"] = False
    handover.write(handed.place_folder(store, WORLD, PLACE) / handover.REPORT, report)
    assert handed.waiting(store, WORLD, nodes()) == {PLACE: every[PLACE]}  # not pushed: not handed


def copies_named(home, words, environment):
    """The words and variables (NAME=value) that name a copy under `home`/frozen, as the conductor reads them
    (disk.working: a whole word, a variable's value, each path of a path list)."""
    found = []
    for word in words + [f"{name}={value}" for name, value in environment.items()]:
        value = word.partition("=")[2] if "=" in word and not word.startswith("/") else word
        if any(disk.copy_named(home / "frozen", part) for part in value.split(os.pathsep) if part):
            found.append(word)
    return found


def running(pid):
    """Whether the process `pid` still runs (a zombie waiting to be reaped has ended)."""
    stat = pathlib.Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().rsplit(") ", 1)[1][0] != "Z"
    except FileNotFoundError:
        return False


# --- the cockpit's files from the library ----------------------------------------------------------------------

LOST = "HeadObject: An error occurred (404) when calling it"
VIEWER = {"web3d/light.glb": "web3d", "web3d/full.glb": "web3d", "material.usda": "usd", "print.png": "texture",
          "settings.json": "record", "a.ogg": "audio", "b.ogg": "audio", "c.ogg": "audio", "d.ogg": "audio",
          "e.ogg": "audio", "sky.usda": "usd", "closeup.png": "closeup"}


def picture_entry(root, address, files, picture=None, sha="f" * 64):
    """One library entry's record: its files (name: role) all of bytes `sha`, its picture, a web copy when it has
    one."""
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    record = {"schema": "score-lib-entry/1", "address": address, "kind": kind, "id": entry_id,
              "version": int(version), "state": "draft", "provenance": {},
              "files": {name: {"role": role, "sha256": sha} for name, role in files.items()}}
    if picture:
        record["picture"] = {"file": picture}
    if "web3d/light.glb" in files:
        record["web3d"] = {"file": "web3d/full.glb", "light": "web3d/light.glb"}
    folder = root / "entries" / kind / entry_id / version
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "entry.json").write_text(json.dumps(record))


GOOD = {"example": "the greenhouse's beds", "view": "plan", "bounds": [0, 0, 1, 1],
        "steps": [{"label": "The beds", "shapes": [{"kind": "area", "points": [[0, 0], [1, 0], [1, 1]], "tone": "c1"}]}]}
OFF = {**GOOD, "view": "film", "steps": [{"label": "x", "shapes": [{"kind": "blob", "points": [[0, 0]]},
                                                                 {"kind": "dots", "points": [], "tone": "pink"}]}]}


def raises(error):
    """A module's `made` that raises `error`."""
    def made(inputs):
        raise error
    return made


# Each algorithm's demo as its module makes it from the library cache, and what demos.json holds for it: a demo whose
# example file the store lost is missing with the cache's own why, and never asks the store again.
DEMO_CASES = {
    "on the shape": (lambda inputs: inputs.library("place/flat@1", "a.png") and GOOD, GOOD),
    "off the shape": (lambda inputs: OFF,
                      {"missing": "its demo is off the shape: view 'film'; shape kind 'blob'; tone 'pink'"}),
    "relief": (lambda inputs: {**GOOD, "view": "relief"},
               {"missing": "its demo is off the shape: relief without heights"}),
    "no example": (lambda inputs: inputs.library("ground/lost@1", "b.png") and GOOD,
                   {"missing": "ground/lost@1: b.png lost (404 before)"}),
    "fails": (raises(KeyError("beds")), {"missing": "its demo failed: KeyError: 'beds'"}),
}
