"""A place is heard as its design says, and its sound row is held to it, nothing rented. Its bed comes from its design
alone (beds.py, on toy scenes over the environment's own briefs, reference bodies and row kinds): a room in a Moon base
hears the base's tone over its hum; a greenhouse, a garage, a tube, a craft's room and a shelter alone in the open
each their own tone; outside on the Moon and Mars only the suit, on Earth the open air and its crowd; what the design
lacks is named, never guessed, and the `bed` gate fails on it. Its objects and people sound from its design (its rows'
kinds, the people it stands); a moving thing sounds off its own moves by its row kind, never its name. Its gates: a
silent moving thing fails `events`, people with no voice `voices`, a sound with no file or a lost row `sources`, a
file too loud `level`, a MOSS take under the CLAP floor `likeness`, a Freesound recording the owner did not choose
`no freesound`. Its takes: one a brief, one card a batch, a shared take made once, a lost take a gap on every place
that plays it, never asked again.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once, seen red and
reverted.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/sound/test_a_place_is_heard_as_its_design_says.py
    (reads the sounds' bytes from the library; the one test that plays them is skipped where no library is
    configured: SCORE_LIB_*, or no score_lib checkout beside score)
"""
import contextlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages import sound  # noqa: E402
from score.stages.sound import beds, gates, needs  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


# --- the bed, from the design alone (beds.py) -------------------------------------------------------------------------

SETTING = {"bodies": [{"body": "moon", "reference": "moon"}, {"body": "mars", "reference": "mars"},
                      {"body": "earth", "reference": "earth"}, {"body": "rock", "name": "Rock", "radius_km": 10.0,
                                                                "mass_kg": 1e15}],
           "plots": [], "sites": [{"place": "base", "on": "moon"}, {"place": "crater", "on": "moon"},
                                  {"place": "dunes", "on": "mars"}, {"place": "plaza", "on": "earth"},
                                  {"place": "cave", "on": "rock"}]}
HOLDERS = {"within": {name: {"within": "base"} for name in ("room", "farm", "bay", "link", "cabin")} |
           {"hut": {"within": "dunes"}, "flatlet": {"within": "plaza"}},
           "parts": {"pier": {"of": "plaza"}}, "merged": {}}
PLANS = {"base": {"shell": "kit", "holds": [{"place": "dock"}]}, "dock": {"ground_free": "in the ship"}, "room": {},
         "farm": {}, "bay": {}, "link": {"shape": "tube"}, "cabin": {"ground_free": "in the ship"},
         "hut": {"shell": "outdoor", "inside": True}, "crater": {"shell": "outdoor"}, "dunes": {"shell": "outdoor"},
         "plaza": {"shell": "kit", "inside": False}, "pier": {"shell": "kit", "inside": False},
         "flatlet": {"shell": "kit", "inside": True}, "cave": {"shell": "outdoor"}, "lost": {}}
ROWS = {"farm": ["planter", "lamp"], "bay": ["rover", "workbench"], "plaza": ["crowd", "the stage's speaker"],
        "pier": ["the launch pad's concrete apron"], "room": ["plant", "chair"]}


@pytest.fixture(scope="module")
def toy():
    """A data folder (the environment's sounds, bodies and row kinds; the toy setting and holders) and a
    design folder holding the toy scenes' plans and inventories."""
    folder = pathlib.Path(tempfile.mkdtemp())
    data, design = folder / "data", folder / "design"
    for name in ("sound/sounds.json", "physics/bodies.json", "checks/row-kinds.json"):
        (data / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "data" / name, data / name)
    (data / "physics/setting.json").write_text(json.dumps(SETTING))
    (data / "places").mkdir()
    (data / "places/within.json").write_text(json.dumps(HOLDERS))
    (design / "plans").mkdir(parents=True)
    for place, plan in PLANS.items():
        (design / "plans" / f"{place}.json").write_text(json.dumps(plan))
    (design / "inventory").mkdir(parents=True)
    for place, nouns in ROWS.items():
        rows = [{"id": f"{noun.split()[-1]}_{at}", "noun": noun} for at, noun in enumerate(nouns)]
        (design / "inventory" / f"{place}.json").write_text(json.dumps({"rows": rows}))
    yield data, design
    shutil.rmtree(folder)


SUIT = ["suit_fans", "suit_breathing_calm"]
# (place, how it is heard, its bed's sounds, what its design lacks, whether its design is kept: a sound row of its own)
BEDS = [
    ("room", "room", ["habitat", "base_hum"], [], True),  # one potted plant makes no greenhouse
    ("farm", "room", ["greenhouse", "base_hum"], [], True),
    ("bay", "room", ["garage", "base_hum"], [], True),
    ("link", "room", ["link_tube", "base_hum"], [], False),
    ("cabin", "room", ["ship_inside"], [], False),  # a craft's room: no base hum through its hull
    ("dock", "room", ["ship_inside"], [], False),  # added in the app: within.json lacks it, the base's plan holds it
    ("hut", "room", ["camp_room"], [], False),  # a shelter alone in the open on Mars, a plan alone
    ("flatlet", "room", ["earth_flat"], [], False),  # a room where the air outside is breathed
    ("crater", "suit", SUIT, [], False),  # the Moon's vacuum, under the Armstrong limit
    ("dunes", "suit", SUIT, [], False),  # Mars's 0.636 kPa, under the Armstrong limit
    ("base", "suit", SUIT, [], False),  # a top scene round its rooms stands on its site: outside, though a kit
    ("plaza", "open", ["street_night", "prologue_crowd", "square_pa"], [], True),
    ("pier", "open", ["launch_pad"], [], True),  # a part of the plaza, its site the plaza's
    ("cave", None, [], ["rock has no surface pressure"], False),
    ("lost", None, [], ["no site in the setting holds it"], False),
]




# --- the sound row's make, gates and takes ----------------------------------------------------------------------------


def inputs_for(place, folder, changes=None):
    """The place's inputs, with each changed record ({input name: document}) written into `folder`."""
    inputs = {name: pathlib.Path((pattern[0] if isinstance(pattern, tuple) else pattern).format(
        place=place, data=str(REPO / "data"), home=str(beds.DESIGN.parent)))
        for name, pattern in sound.files(place).items()}
    for name, document in (changes or {}).items():
        inputs[name] = pathlib.Path(folder) / f"{name}.json"
        inputs[name].write_text(json.dumps(document))
    return inputs


def made(place, folder, changes=None):
    if not sound.library_files.settings().get("SCORE_LIB_ROOT"):
        pytest.skip("no library configured here: the picked sounds' bytes are the library's")
    inputs = inputs_for(place, folder, changes)
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    sound.make(inputs, out, 0, {})
    assert sound.layer_faults(out) == [], sound.layer_faults(out)
    return inputs, out


DOOR = {"about": {"side": [-1.0, 0.0, 0.0]}, "angle": 90.0, "speed": 30.0, "starts": "shut",
        "moves": [[2.0, "open"], [10.0, "shut"]]}
TABLE = {"kinds": {"door": {"swing": {"sounds": [{"name": "door_open", "part": "start", "when": "open"},
                                                 {"name": "door_shut", "part": "end", "when": "shut"}],
                                      "from": "a test's door"}}}}


def toy_design(folder):
    """A scene written here: a door row the motion row swings (its moves.json, as from_design writes it) and a person
    its design stands (data/people/rows.json's form), a moving sounds table and a voice naming sounds (the rules);
    {input name: path} over the hub's other inputs."""
    folder = pathlib.Path(folder)
    inputs = inputs_for("hub", folder)
    inputs.update({"plan": folder / "toy.json", "scene inventory": folder / "inventory.json",
                   "people": folder / "rows.json", "motion": folder / "motion",
                   "moving sounds": folder / "moving.json", "voices": folder / "voices.json"})
    inputs["plan"].write_text(json.dumps({"leads": {}, "rows": {}}))
    inputs["scene inventory"].write_text(json.dumps({"rows": [{"id": "hatch", "noun": "door"},
                                                              {"id": "pilot", "noun": "person"}]}))
    inputs["people"].write_text(json.dumps({"places": {"toy": {"rows": {"pilot": {"looks": ["pilot-drawn"]}}}}}))
    inputs["motion"].mkdir()
    (inputs["motion"] / "moves.json").write_text(json.dumps({"moves": [
        {"name": "hatch_1", "prim": "/toy/Objects/hatch_1", "row": "hatch", "start": 0.0, "length": 20.0,
         "loop": True, "swing": DOOR}]}))
    inputs["moving sounds"].write_text(json.dumps(TABLE))
    inputs["voices"].write_text(json.dumps({"people": "crew_talk"}))
    return inputs


FETCHED = {"file": "sound/roar@1/roar.ogg", "source": "https://freesound.org/people/someone/sounds/1/",
           "author": "someone", "licence": "CC0 1.0"}
ROAR = {"roar": {"files": [], "made_by": "recording", "credits": [FETCHED], "chosen_by": "scoring"}}
FLOORED = {"square_pa": {"made_by": "moss", "clap": 0.1248, "files": []},
           "base_hum": {"made_by": "moss", "clap": 0.45, "files": []}}
CALLED = [{"sound": "square_pa", "role": "object", "on": "pa", "from": "places.json objects"},
          {"sound": "lost_take", "role": "room", "on": None, "from": "places.json"}]
LOST_DOOR_AND_VOICE = {"door_open", "door_shut", "crew_talk"}
DOOR_PRIM = "/toy/Objects/hatch_1"
CREW_TALK = {"sound": "crew_talk", "role": "object", "on": "pilot"}
MOVED = "moved to complete as accepted gaps"

# The sound row's records and how its gates judge them. Each row a world: the toy design (a door the motion row swings,
# a person it stands) heard where `where` stands it (None: the hub's room; "moon": outside on the Moon, through the
# suit; "earth": a room on Earth's breathable air), or none (`design` false: only `uses` and `sounds`); its record as
# the make writes it (sound.all_uses, each design sound with a file), the uses on or of `silent` left out, `uses`
# added, `sounds` over its sounds, `lost` the batch's takes that did not come back (sound.take_gaps). `gates` are judged
# (a name: gates.judge_<name>; "table <name>": the stage table's check, which moves a lost take's faults to its gap),
# each to `answer`, its findings fullmatching `findings` in order and its reason holding `reason`, where given; the
# record plays `voiced` ({row: its sounds}) and names `unheard`, and the batch's gaps are `gaps` ({name: its faults}).
VERDICTS = [
    # #29, the audit of 2026-11-04: objects, doors and every person's crew_talk played as if through air where the bed
    # played the suit, and a sealed module's crew talk in a Hong Kong flat.
    {"id": "outside on the Moon the door is unheard and the voice the helmet radio's", "where": "moon",
     "gates": ("events", "voices", "heard", "suits"), "answer": checks.PASS,
     "voiced": {"pilot": ["helmet_radio_talk"]}, "unheard": {(DOOR_PRIM, "door_open"), (DOOR_PRIM, "door_shut")}},
    {"id": "the door's latch and crew talk written back on the Moon fail heard", "where": "moon",
     "hear_unheard": True, "uses": [CREW_TALK], "gates": ("heard",), "answer": checks.FAIL,
     "findings": [f"{DOOR_PRIM}:.*", "pilot:.*"]},
    {"id": "in a room on Earth's air the voice is room talk", "where": "earth", "gates": ("suits",),
     "answer": checks.PASS, "voiced": {"pilot": ["room_talk"]}},
    {"id": "crew talk written into a room on Earth's air fails suits", "where": "earth", "uses": [CREW_TALK],
     "gates": ("suits",), "answer": checks.FAIL,
     "findings": [re.escape("pilot: crew_talk heard here as air breathable (written for sealed)")]},
    {"id": "the door and the person sounding pass events and voices", "gates": ("events", "voices"),
     "answer": checks.PASS},
    {"id": "a silent moving thing fails events", "silent": {DOOR_PRIM, "pilot"}, "gates": ("events",),
     "answer": checks.FAIL, "findings": [".*hatch_1.*"]},
    {"id": "people with no voice fail voices", "silent": {DOOR_PRIM, "pilot"}, "gates": ("voices",),
     "answer": checks.FAIL},
    # cockpit (2026-11-11): its pilot a bodies gap, no voice wanted
    {"id": "a person a bodies gap leaves unlaid wants no voice", "silent": {DOOR_PRIM, "pilot"},
     "gapped": ["pilot"], "gates": ("voices",), "answer": checks.PASS},
    {"id": "with no voice named none plays", "voices": {"people": None}, "gates": (), "voiced": {"pilot": []}},
    {"id": "a sound the record lacks and a lost row fail sources", "gates": ("sources",), "answer": checks.FAIL,
     "uses": [{"sound": "no_such_sound", "role": "object", "on": "hatch", "from": "the test"},
              {"sound": "door_open", "role": "object", "on": "no_such_row", "from": "the test"}],
     "findings": [".*no_such_sound.*", ".*no_such_row.*"]},
    # a room tone made 18 dB too loud: a full-scale sine of its brief's length
    {"id": "a loud file fails level", "design": False, "loud": "tone.wav", "gates": ("level",),
     "answer": checks.FAIL,
     "findings": ["tone: tone.wav peaks at .* dBTP", "tone: tone.wav at .* LUFS, off its room target .*"],
     "sounds": {"tone": {"files": ["files/tone.wav"], "category": "room", "brief_seconds": 5, "made_by": "moss",
                         "credits": []}}},
    {"id": "a MOSS take a hundredth under the CLAP floor fails likeness", "design": False, "gates": ("likeness",),
     "answer": checks.FAIL, "sounds": {"hum": {"files": [], "made_by": "moss", "clap": gates.CLAP_FLOOR - 0.01,
                                               "credits": [], "chosen_by": "scoring"}}},
    # the owner's exception (2026-10-20, #29): a CC0 Freesound recording with its row in data/sound/licences.json
    {"id": "a CC0 Freesound recording with its licence row passes no freesound", "design": False, "sounds": ROAR,
     "licences": [FETCHED], "gates": ("no_freesound",), "answer": checks.PASS},
    {"id": "a Freesound recording chosen by scoring with no licence row fails no freesound", "design": False,
     "sounds": ROAR, "licences": [], "gates": ("no_freesound",), "answer": checks.FAIL},
    {"id": "a Freesound recording under another licence fails no freesound", "design": False, "sounds": ROAR,
     "licences": [dict(FETCHED, licence="CC BY 4.0")], "gates": ("no_freesound",), "answer": checks.FAIL},
    # sound@square, 2026-10-20: two takes back under the CLAP floor failed likeness and stopped the line, though the
    # batch rule makes each a gap
    {"id": "a take under the floor or not back is a batch gap, likeness's own answer standing", "design": False,
     "uses": CALLED, "silent": {"lost_take"}, "sounds": FLOORED, "lost": ["square_pa", "lost_take"],
     "gates": ("likeness",), "answer": checks.FAIL,
     "gaps": {"square_pa: MOSS take under the CLAP floor": None,
              "lost_take: no MOSS take came back": ["lost_take: no sound (room, places.json)"]}},
    {"id": "the table's likeness moves a take under the floor to its gap", "design": False, "uses": CALLED,
     "silent": {"lost_take"}, "sounds": FLOORED, "lost": ["square_pa", "lost_take"], "gates": ("table likeness",),
     "answer": checks.PASS, "reason": f"{MOVED}: square_pa"},
    {"id": "a picked sound under the floor is no take of this batch and still fails", "design": False,
     "uses": CALLED, "silent": {"lost_take"}, "sounds": {**FLOORED, "base_hum": dict(FLOORED["base_hum"], clap=0.2)},
     "lost": ["square_pa", "lost_take"], "gates": ("table likeness",), "answer": checks.FAIL},
    # try 4, 2026-10-25: moving.json and voices.json named no sound, so every place with motion or people stopped its
    # line; now a take not back leaves its door and person silent, a gap naming each
    {"id": "a door and a voice silent by lost takes fail their own gates", "silent": LOST_DOOR_AND_VOICE,
     "lost": sorted(LOST_DOOR_AND_VOICE), "gates": ("events", "voices"), "answer": checks.FAIL},
    {"id": "the table's events and voices move a lost take's silence to its gap", "silent": LOST_DOOR_AND_VOICE,
     "lost": sorted(LOST_DOOR_AND_VOICE), "gates": ("table events", "table voices"), "answer": checks.PASS,
     "reason": MOVED},
    {"id": "a door silent with no take lost still fails the table's events", "silent": LOST_DOOR_AND_VOICE,
     "gates": ("table events",), "answer": checks.FAIL},
]


def standing_where(inputs, folder, where):
    """The toy design's inputs as `where` stands it: outside on the Moon (an outdoor plan on a site of the Moon), or in a
    room on Earth's breathable air; the house's voices table (by hearing)."""
    inputs["setting"] = pathlib.Path(folder) / "setting.json"
    inputs["setting"].write_text(json.dumps({"bodies": [{"body": where, "reference": where}], "plots": [],
                                             "sites": [{"place": "toy", "on": where}]}))
    plan = {"shell": "outdoor"} if where == "moon" else {"shell": "kit", "inside": True}
    inputs["plan"].write_text(json.dumps({**plan, "leads": {}, "rows": {}}))
    inputs["voices"] = REPO / "data/sound/voices.json"


def world_of(row, folder):
    """`row`'s world (VERDICTS): its inputs, its output folder with the record and the batch's gaps written."""
    from score.stages import batch_gaps
    folder = pathlib.Path(folder)
    inputs = toy_design(folder)
    if row.get("where"):
        standing_where(inputs, folder, row["where"])
    if "voices" in row:
        inputs["voices"].write_text(json.dumps(row["voices"]))
    designed, unheard = sound.all_uses("toy", inputs) if row.get("design", True) else ([], [])
    written_back = [dict(unheard[0])] if row.get("hear_unheard") else []
    played = [use for use in designed + written_back + row.get("uses", [])
              if use["on"] not in row.get("silent", ()) and use["sound"] not in row.get("silent", ())]
    sounds = {use["sound"]: {"files": ["files/x.wav"]} for use in designed if use in played}
    sounds.update(row.get("sounds", {}))
    out = folder / "out"
    (out / "files").mkdir(parents=True)
    (out / gates.RECORD).write_text(json.dumps({"place": "toy", "uses": played, "unheard": unheard,
                                                "sounds": sounds}))
    if row.get("loud"):
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=5",
                        "-af", "volume=18dB", str(out / "files" / row["loud"])], check=True)
    if row.get("lost"):
        batch_gaps.write(out, sound.take_gaps(row["lost"], sounds, designed + row.get("uses", [])))
    if "licences" in row:
        inputs["licences"] = folder / "licences.json"
        inputs["licences"].write_text(json.dumps(row["licences"]))
    if row.get("gapped"):
        inputs["gaps"] = str(folder / "gaps.json")
        (folder / "gaps.json").write_text(json.dumps({"gaps": [{"row": "characters-layer", "check": "bodies",
                                                                "objects": row["gapped"]}]}))
    return inputs, out


def judge_of(gate):
    """The judge `gate` names (VERDICTS): gates.judge_<name>, or the stage table's check of "table <name>"."""
    from score import stages
    if gate.startswith("table "):
        return next(check for table in stages.STAGES if table.name == "sound" for check in table.checks
                    if check.name == gate.removeprefix("table ")).judge
    return getattr(gates, f"judge_{gate}")


def test_a_place_is_heard_as_its_design_says(toy):
    """A place's bed comes from its design alone (BEDS): how it is heard, the tones it plays, and what its design lacks,
    named, never guessed. The `bed` gate passes a decided bed and fails an undecided one naming what lacks; its bed gap
    says what lacks, or that a decided bed is still to make, the sound row's to make only where the design is kept
    (the plaza), else naming the work, never a node the table lacks (the hut). Its record plays and its gates judge
    each world of VERDICTS as that row says.
    Break: score/stages/sound/beds.py: `found["shape"] = plan.get("shape")` -> `found["shape"] = None`
    Break: score/stages/sound/beds.py: `found["grounded"] = not plan.get("ground_free")` -> `found["grounded"] =
        True`
    Break: score/stages/sound/beds.py: `None if kpa is None else "suit" if kpa < ARMSTRONG_KPA else "open")`
        -> `None if kpa is None else "open")`
    Break: score/stages/sound/beds.py: `found["missing"].append(f"{ground} has no surface pressure")` -> `pass`
    Break: score/stages/sound/beds.py: `found["missing"].append("no site in the setting holds it")` -> `pass`
    Break: score/stages/sound/gates.py: `    if bed["sounds"]:` -> `    if True:`
    Break: score/stages/sound/needs.py: `"node": f"sound@{place}" if made_here else None,` -> `"node":
        f"sound@{place}",`
    Break: score/stages/sound/gates.py: `if not sounding & set(event["prims"])]` -> `if False]`
    Break: score/stages/sound/__init__.py: `if not people or not voice:` -> `if not people:`
    Break: score/stages/sound/__init__.py: `if bed["facts"].get("heard") == "suit":` -> `if False:`
    Break: score/stages/sound/gates.py: `if facts.get(key) not in values]` -> `if False]`
    Break: score/stages/sound/__init__.py: `for entry in voices.get("by_hearing", []):` -> `for entry in []:`
    Break: score/stages/sound/gates.py: people_of's `if name not in gapped]` -> `]` (cockpit's gapped pilot wanted a
        voice)
    Break: score/stages/sound/gates.py: `if not record["sounds"].get(use["sound"], {}).get("files")]` -> `if False]`
    Break: score/stages/sound/gates.py: `            faults += found` -> `            pass`
    Break: score/stages/sound/gates.py: `if sound.get("clap") is not None and sound["clap"] < CLAP_FLOOR]` -> `if
        False]`
    Break: score/stages/sound/gates.py: `    if left:` -> `    if False:`
    Break: score/stages/sound/gates.py:
        `if FREESOUND in row.get("source", "") and row.get("licence", "").startswith("CC0")}`
        -> `if FREESOUND in row.get("source", "")}`
    Break: score/stages/sound/gates.py:
        `all(credit["file"] in rows for credit in sound["credits"] if FREESOUND in credit.get("source", ""))}`
        -> `True}`
    Break: score/stages/sound/__init__.py:
        `elif sounds[name].get("clap") is not None and sounds[name]["clap"] < gates.CLAP_FLOOR:` -> `elif False:`
    Break: score/stages/sound/__init__.py: `return [use.get("event") if use["role"] == "motion" else use["on"] for use
        in uses`
        -> `return [use["on"] for use in uses`"""
    data, design = toy
    for place, heard, sounds, missing, kept in BEDS:
        found = beds.of_place(place, beds.paths(place, data, design))
        assert (found["facts"].get("heard"), found["sounds"], found["facts"]["missing"]) == (heard, sounds, missing), (
            place, found)
        verdict = gates.judge_bed(None, beds.paths(place, data, design), None)
        assert (verdict.answer, verdict.findings) == (checks.PASS if sounds else checks.FAIL, tuple(missing)), (
            place, verdict)
        gap = {gap["id"]: gap for gap in needs.gaps(place, data, design)}["sound:bed:room"]
        assert place in beds.places(design) and needs.sounded(place, design) == kept, place
        if missing:
            assert all(lack in gap["work"] for lack in missing) and gap["node"] is None, (place, gap)
        else:
            assert "still to make" in gap["sentence"], (place, gap)
            if kept:
                assert gap["node"] == f"sound@{place}" and gap["work"] is None, (place, gap)
            else:
                assert gap["node"] is None and gap["work"], (place, gap)
    from score.stages import batch_gaps
    for row in VERDICTS:
        with tempfile.TemporaryDirectory() as folder:
            inputs, out = world_of(row, folder)
            record = gates.record_of(out)
            for on, voiced in row.get("voiced", {}).items():
                assert [use["sound"] for use in record["uses"] if use["on"] == on] == voiced, (row["id"], record)
            if "unheard" in row:
                assert {(use["on"], use["sound"]) for use in record["unheard"]} == row["unheard"], (row["id"], record)
            if "gaps" in row:
                found = {entry["name"]: entry for entry in batch_gaps.read([out])}
                assert set(found) == set(row["gaps"]), (row["id"], found)
                assert all(faults is None or found[name]["faults"] == faults
                           for name, faults in row["gaps"].items()), (row["id"], found)
            for gate in row["gates"]:
                verdict = judge_of(gate)(out, inputs, None)
                assert verdict.answer == row["answer"], (row["id"], gate, verdict.reason, verdict.findings)
                if "findings" in row:
                    assert len(verdict.findings) == len(row["findings"]) and all(
                        re.fullmatch(wanted, line) for wanted, line in zip(row["findings"], verdict.findings)), (
                        row["id"], gate, verdict.findings)
                assert row.get("reason", "") in verdict.reason, (row["id"], gate, verdict.reason)


def needs_of_toy(folder, named):
    """The toy design's needs and gaps (needs.needs, needs.gaps) over the environment's tables, or (`named` false)
    over tables that name no sound: a moving sounds table whose parts name none and no voice."""
    from score.stages.sound import needs
    data = pathlib.Path(folder)
    for part in ("sound", "checks", "people", "inventory"):
        (data / part).mkdir()
    for name in ("sounds", "catalogue", "voices", "moving"):
        shutil.copyfile(REPO / f"data/sound/{name}.json", data / f"sound/{name}.json")
    if not named:
        table = json.loads((data / "sound/moving.json").read_text())
        worded = [entry for entries in table["words"].values() for entry in entries]
        for moves in [*table["kinds"].values(), *worded]:
            for move in [value for key, value in moves.items() if key != "words"]:
                move["sounds"] = [{key: value for key, value in part.items() if key != "name"}
                                  for part in move["sounds"]]
        (data / "sound/moving.json").write_text(json.dumps(table))
        (data / "sound/voices.json").write_text(json.dumps({"people": None}))
    shutil.copyfile(REPO / "data/checks/row-kinds.json", data / "checks/row-kinds.json")
    (data / "people/rows.json").write_text(json.dumps({"places": {"toy": {"rows": {"pilot": {"looks": ["p-d"]}}}}}))
    design = data / "design"
    (design / "inventory").mkdir(parents=True)
    (design / "inventory/toy.json").write_text(json.dumps({"rows": [{"id": "hatch", "noun": "door"},
                                                                     {"id": "pilot", "noun": "person"}]}))
    found = {(need["kind"], need["item"]): need for need in needs.needs("toy", data, design)}
    return found, {gap["id"]: gap for gap in needs.gaps("toy", data, design)}


def test_needs_name_what_the_library_does_not_answer():
    """#29: free, from the design: a door row the design moves, with no sound named for its kind's move, and the
    people it stands, with no voice named, are each a gap naming its work; the environment's own tables name a brief
    for each, which the sound row's batch makes.
    Break: score/stages/sound/needs.py: `if not names or any(not has_file(name) and not briefed(name) for name in
        names):`
        -> `if any(not has_file(name) and not briefed(name) for name in names):`"""
    from score.stages.sound import needs
    with tempfile.TemporaryDirectory() as folder:
        found, gaps = needs_of_toy(folder, named=False)
    assert found[("event", "hatch")]["state"] == needs.NONE and found[("event", "hatch")]["prim"] == "/toy/hatch", found
    assert found[("voice", "people")]["state"] == needs.NONE, found
    assert "data/sound/moving.json" in gaps["sound:event:hatch"]["work"], gaps
    assert "data/sound/voices.json" in gaps["sound:voice:people"]["work"], gaps
    with tempfile.TemporaryDirectory() as folder:
        found, gaps = needs_of_toy(folder, named=True)
    assert found[("event", "hatch")]["state"] == needs.MAKE and found[("voice", "people")]["state"] == needs.MAKE, found



@contextlib.contextmanager
def kept_designs(designs):
    """Small kept designs in the sandbox home ({place: its scene inventory rows}): each a plan and a scene inventory,
    removed after."""
    written = []
    for place, rows in designs.items():
        for folder, record in (("plans", {"leads": {}, "rows": {}}), ("inventory", {"rows": rows})):
            path = beds.DESIGN / folder / f"{place}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record))
            written.append(path)
    try:
        yield
    finally:
        for path in written:
            path.unlink()


def voiced_data(folder):
    """The environment's data folder (links into data/) with its voices table naming crew_talk, still to make, as the
    people's voice: the rule with a voice named."""
    data = pathlib.Path(folder) / "data"
    (data / "sound").mkdir(parents=True)
    for path in (REPO / "data").iterdir():
        if path.name != "sound":
            (data / path.name).symlink_to(path)
    for path in (REPO / "data/sound").iterdir():
        if path.name != "voices.json":
            (data / "sound" / path.name).symlink_to(path)
    (data / "sound/voices.json").write_text(json.dumps({"people": "crew_talk"}))
    return data


def test_a_brief_several_places_play_is_one_take_on_one_card_and_counted_once():
    """#29: crew_talk, played in several places (the voice of every place whose design stands people), is one take of
    the environment's plan, counted once by the price's forecast rule; two places' lines side by side make it on one
    card, the second waiting for it and reading its score.
    Break: score/stages/sound/takes.py: `for name in sorted({job["file"] for job in jobs}):` -> `for name in []:`"""
    import threading
    from score.stages.complete.gaps import price
    from score.stages.sound import takes
    kept_folder = pathlib.Path(tempfile.mkdtemp())
    real_takes, real_on_card = takes.TAKES, takes.on_card
    asked = []

    def on_card(plan):
        wanted = json.loads(pathlib.Path(plan["runs"][0]["inputs"][0]["from"]).read_text())
        asked.extend(job["sound"] for job in wanted)
        time.sleep(0.3)  # the card at work while the other line asks
        back = pathlib.Path(plan["runs"][0]["jobs"][0]["outputs"][0]["to"])
        for job in wanted:
            (back / job["file"]).write_bytes(b"RIFF")
        (back / "scores-0.json").write_text(json.dumps({job["file"]: 0.4 for job in wanted}))

    with kept_designs({"airlock": [], "cockpit": []}):  # two places data/people/rows.json stands people in
        try:
            takes.TAKES, takes.on_card = kept_folder / "takes", on_card
            data = voiced_data(kept_folder)
            plan = sound.environment_takes(data, sound.moss_weights())
            shared = [places for job, places in plan.values() if job["sound"] == "crew_talk"]
            assert len(shared) == 1 and len(shared[0]) > 1, shared
            places = beds.places()
            assert sum(price.rule_units("sound_takes", [], data, place) for place in places) == len(plan)
            brief = sound.brief_of("crew_talk", {"sounds": REPO / "data/sound/sounds.json"})
            heard = {}

            def line_of(place):
                heard[place] = takes.made(takes.jobs_for("crew_talk", brief, "rev"), kept_folder / f"work-{place}")
            lines = [threading.Thread(target=line_of, args=(place,)) for place in shared[0][:2]]
            for line in lines:
                line.start()
            for line in lines:
                line.join()
        finally:
            takes.TAKES, takes.on_card = real_takes, real_on_card
            shutil.rmtree(kept_folder)
    assert asked == ["crew_talk"], asked
    assert [list(scored.values()) for scored in heard.values()] == [[0.4], [0.4]], heard  # the second read it


def test_a_shared_take_that_fails_is_a_gap_on_every_place_and_never_asked_again():
    """#29: two places' lines wait on one take whose card job fails: one card asked for, both lines get the gap.
    Break: score/stages/sound/takes.py: `lost_before = [job for job in wanted if asked_here(job)]` -> `lost_before =
        []`"""
    import threading
    from score.stages.sound import takes
    kept_folder = pathlib.Path(tempfile.mkdtemp())
    real_takes, real_on_card = takes.TAKES, takes.on_card
    asked, scored = [], {}

    def on_card(plan):  # the job works on its card but brings nothing back
        asked.append(json.loads(pathlib.Path(plan["runs"][0]["inputs"][0]["from"]).read_text()))
        time.sleep(0.3)

    def line(place):
        scored[place] = takes.made(takes.jobs_for("crew_talk", {"prompts": ["crew talk"]}, "rev"),
                                   kept_folder / f"work-{place}")

    try:
        takes.TAKES, takes.on_card = kept_folder / "takes", on_card
        lines = [threading.Thread(target=line, args=(place,)) for place in ("hub", "airlock")]
        for each in lines:
            each.start()
        for each in lines:
            each.join()
    finally:
        takes.TAKES, takes.on_card = real_takes, real_on_card
        shutil.rmtree(kept_folder)
    assert len(asked) == 1, asked
    assert scored == {"hub": {}, "airlock": {}}, scored



def test_a_job_that_failed_as_a_job_with_no_take_back_fails_the_row_on_every_place_never_a_gap():
    """A generator that never ran (this PC's moss job, "moss_generate.py: command not found" for days, 13e63538) is the
    framework's fault, not a gap: two places' lines wait on one take whose job exits non-zero with nothing back, one
    card asked for, both lines fail. A failed job that still brought a take back leaves only its missing takes as gaps.
    Break: score/stages/sound/takes.py: `if failed and not came_back:` -> `if False:`
    Break: score/stages/sound/takes.py: `        if failed:\n            raise JobFailed` -> `        if False:\n
        raise JobFailed`"""
    import threading
    from score.stages.sound import takes
    kept_folder = pathlib.Path(tempfile.mkdtemp())
    real_takes, real_on_card = takes.TAKES, takes.on_card
    asked, failed = [], {}

    def on_card(plan):  # the share exits 127: nothing comes back
        asked.append(json.loads(pathlib.Path(plan["runs"][0]["inputs"][0]["from"]).read_text()))
        time.sleep(0.3)
        return "the moss job failed on this PC's card: share 0"

    def line(place):
        try:
            takes.made(takes.jobs_for("crew_talk", {"prompts": ["crew talk"]}, "rev"), kept_folder / f"work-{place}")
        except takes.JobFailed as error:
            failed[place] = str(error)

    def half_back(plan):  # the job exits non-zero after one of its two takes came back
        back = pathlib.Path(plan["runs"][0]["jobs"][0]["outputs"][0]["to"])
        first = json.loads(pathlib.Path(plan["runs"][0]["inputs"][0]["from"]).read_text())[0]
        (back / first["file"]).write_bytes(b"RIFF")
        (back / "scores-0.json").write_text(json.dumps({first["file"]: 0.4}))
        return "the moss job failed on this PC's card: share 0"

    try:
        takes.TAKES, takes.on_card = kept_folder / "takes", on_card
        lines = [threading.Thread(target=line, args=(place,)) for place in ("hub", "airlock")]
        for each in lines:
            each.start()
        for each in lines:
            each.join()
        takes.on_card = half_back
        jobs = [job for name in ("pump", "fan") for job in takes.jobs_for(name, {"prompts": [f"a {name}"]}, "rev")]
        scored = takes.made(jobs, kept_folder / "work-garage")
    finally:
        takes.TAKES, takes.on_card = real_takes, real_on_card
        shutil.rmtree(kept_folder)
    assert len(asked) == 1, asked
    assert sorted(failed) == ["airlock", "hub"] and all("share 0" in text for text in failed.values()), failed
    assert scored == {jobs[0]["file"]: 0.4}, scored  # the fan's take, not back, is a gap

def test_moving_things_sound_off_their_own_moves():
    """A door the motion row swings plays its latch as it starts to open and its bolts as it is shut tight (its
    swing's angle over its speed later), in the stage's seconds, round after round; and moving.py's rounds are the
    assembly's (tools/usd/sound.rounds_of). The door opens at 2 s and shuts at 10 s, its 90 degrees at 30 a second
    taking 3 s: latch at 2, bolts at 13, and the next 20 s round's latch at 22.
    Break: score/stages/sound/moving.py: `return [(end, None) for _, end in moves_of(motion, entry["when"])]`
        -> `return [(start, None) for start, _ in moves_of(motion, entry["when"])]`
    Break: score/stages/sound/moving.py:
        `return [start + length * number for number in range(max(1, math.ceil(SOUND_SPAN_SECONDS / length)))]`
        -> `return [start]`"""
    with tempfile.TemporaryDirectory() as folder:
        uses = sound.uses_of("toy", toy_design(folder))
    door = [(use["sound"], use["at"]) for use in uses if use["on"] == "/toy/Objects/hatch_1"]
    assert door[:2] == [("door_open", 2.0), ("door_shut", 13.0)], door
    assert ("door_open", 22.0) in door, "the next round's"
    sys.path.insert(0, str(REPO / "tools/usd"))
    import sound as layer  # noqa: E402  (tools/usd: the assembly's rounds, which moving.py repeats)
    from score.stages.sound import moving
    for motion in ({"start": 1.0}, {"start": 0.0, "length": 14.0, "loop": True},
                   {"start": 0.0, "length": 86.0, "loop": True}):
        assert moving.rounds_of(motion) == layer.rounds_of(motion), motion
    assert moving.SOUND_SPAN_SECONDS == layer.SOUND_SPAN_SECONDS


def test_a_new_scene_sounds_from_its_design_alone():
    """A scene no sound table names (its plan, scene inventory and people only, read from a new concept): each row whose
    kind sounds plays its kind's library sound at that row (a console its hum, a duct the vent's air, a rover its idle,
    a ceiling light its buzz; a lantern, a noun its kind leaves silent, nothing), its first person the people's voice;
    every target stands in its design, and its voice need reads the same records.
    Break: score/stages/sound/__init__.py: `return [{"sound": voice, "role": "object", "on": people[0],`
        -> `return [{"sound": voice, "role": "object", "on": people[-1],`
    Break: score/stages/sound/__init__.py: object_uses' `if row["id"] in beyond: continue` -> `if False: continue`,
        or voice_uses' `if name not in gapped]` -> `]`"""
    from score.stages.sound import needs
    rows = [{"id": "main_desk", "name": "main desk", "noun": "console"}, {"id": "roof_duct", "noun": "duct"},
            {"id": "buggy", "noun": "rover"}, {"id": "panel_light", "noun": "light"},
            {"id": "paper_lantern", "noun": "lantern"}, {"id": "table", "noun": "table"},
            {"id": "pilot", "noun": "person"}]
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inputs = inputs_for("hub", folder)
        inputs.update({"plan": folder / "new_scene.json", "scene inventory": folder / "inventory.json",
                       "people": folder / "rows.json", "voices": folder / "voices.json"})
        inputs["plan"].write_text(json.dumps({"leads": {}, "rows": {"DESK": ["main_desk"]}}))
        inputs["scene inventory"].write_text(json.dumps({"rows": rows}))
        inputs["people"].write_text(json.dumps({"places": {"new_scene": {"rows": {
            "pilot": {"looks": ["pilot-drawn"]}, "officer": {"looks": ["officer-drawn"]}}}}}))
        inputs["voices"].write_text(json.dumps({"people": "crew_talk"}))  # the rule, a voice named
        assert sound.place_of(inputs) == "new_scene"
        uses = sound.uses_of("new_scene", inputs)
        heard = sorted((use["sound"], use["on"]) for use in uses if use["role"] == "object")
        assert heard == [("console_hum", "main_desk"), ("crew_talk", "officer"), ("lamp_buzz", "panel_light"),
                         ("rover_idle", "buggy"), ("vent_air", "roof_duct")], heard
        assert {use["on"] for use in uses if use["role"] == "object"} <= gates.standing(inputs)
        # street and stairwell (2026-11-11): a row the plan sees beyond the place (the street's distant floodlight)
        # and a person an accepted bodies gap leaves unlaid (the stairwell's man) were played at nothing
        inputs["plan"].write_text(json.dumps({"leads": {}, "rows": {"DESK": ["main_desk"]}, "beyond": ["buggy"]}))
        (folder / "gaps.json").write_text(json.dumps({"gaps": [{"row": "characters-layer", "check": "bodies",
                                                               "objects": ["officer"]}]}))
        gapped = sorted((use["sound"], use["on"]) for use in sound.uses_of("new_scene", {**inputs, "gaps": str(
            folder / "gaps.json")}) if use["role"] == "object")
        assert gapped == [("console_hum", "main_desk"), ("crew_talk", "pilot"), ("lamp_buzz", "panel_light"),
                          ("vent_air", "roof_duct")], gapped
        inputs["plan"].write_text(json.dumps({"leads": {}, "rows": {"DESK": ["main_desk"]}}))
        data = folder / "data"
        (data / "sound").mkdir(parents=True)
        for name in ("sounds", "catalogue"):
            shutil.copyfile(REPO / f"data/sound/{name}.json", data / f"sound/{name}.json")
        shutil.copyfile(inputs["voices"], data / "sound/voices.json")
        (data / "people").mkdir()
        shutil.copyfile(inputs["people"], data / "people/rows.json")
        (data / "checks").mkdir()
        shutil.copyfile(REPO / "data/checks/row-kinds.json", data / "checks/row-kinds.json")
        voice = next(need for need in needs.needs("new_scene", data) if need["kind"] == "voice")
    assert (voice["sounds"], voice["state"], voice["prim"]) == (
        ["crew_talk"], needs.MAKE, "/new_scene/Characters/officer"), voice


def test_a_moving_thing_sounds_by_its_row_kind_and_move_never_its_name():
    """A place written here, its names unlike any place's: a gate row (a door) sliding in a game motion plays the
    library's door slide in its round's seconds; a cart row (a vehicle) on a path plays its drive; a thing whose record
    names only its motion kind (a hatch) swings as a door; a boom row, no kind, plays nothing and is a gap with its
    work. The same table answers any place.
    Break: score/stages/sound/moving.py:
        `return next((kind for kind, rule in kinds.items() if rule.get("motion", {}).get("kind") == entry["kind"]),
        None)`
        -> `return None`
    Break: score/stages/sound/needs.py: `return pivots[0] if pivots else entry["prim"]` -> `return entry["prim"]`
    Break: score/stages/sound/moving.py: `found = next((worded[move] for worded in table.get("words", {}).get(kind,
        []) if said & set(worded["words"]) and move in worded), None) or` -> `found =`"""
    from score.stages import row_kinds
    from score.stages.sound import moving, needs
    kinds = row_kinds.table(REPO / "data/checks/row-kinds.json")
    table = {"kinds": {"door": {"slide": {"sounds": [{"name": "door_slide_open", "part": "start", "when": "open"},
                                                     {"name": "door_slide_close", "part": "start", "when": "shut"}],
                                          "from": "a test's slide"}, **TABLE["kinds"]["door"]},
                       "vehicle": {"path": {"sounds": [{"name": "rover_motor", "part": "drive"},
                                                       {"name": "rover_wheels_gravel", "part": "drive"}],
                                            "from": "a test's drive"}}}}  # the rule, sounds named
    rows = [{"id": "yard_gate", "noun": "gate"}, {"id": "cart", "noun": "cart"}, {"id": "boom", "noun": "boom"}]
    motions = [{"name": "west_entry", "prim": "/toy/Objects/yard_gate_1", "start": 0.0, "length": 10.0, "loop": True,
                "slide": {"by": [2.0, 0.0, 0.0], "speed": 1.0, "moves": [[1.0, "open"], [5.0, "shut"]]}, "sounds": []}]
    moves = [{"name": "loop_a", "prim": "/toy/Objects/cart_1", "start": 2.0, "length": 8.0, "loop": False,
              "path": {"points": [[0, 0, 0], [5, 0, 0]]}},
             {"name": "porthole", "prim": "/toy/Objects/porthole_1", "kind": "hatch", "start": 0.0, "length": 20.0,
              "loop": False, "swing": {"angle": 90.0, "speed": 30.0, "moves": [[4.0, "open"], [12.0, "shut"]]}},
             {"name": "spray_run", "prim": "/toy/Objects/boom_1", "start": 0.0, "length": 8.0, "loop": False,
              "slide": {"by": [0.0, 0.0, 4.0], "speed": 0.5, "moves": [[0.0, "open"]]}}]
    found = {event["name"]: [(use["sound"], use["on"], use["at"], use["loops_until"])
                             for use in moving.event_uses(event, rows, kinds, table, {})]
             for event in needs.events(motions, moves, {})}
    assert found["west_entry"] == [("door_slide_open", "/toy/Objects/yard_gate_1", 1.0, None),
                                   ("door_slide_close", "/toy/Objects/yard_gate_1", 5.0, None)], found
    assert found["loop_a"] == [("rover_motor", "/toy/Objects/cart_1", 2.0, 10.0),
                               ("rover_wheels_gravel", "/toy/Objects/cart_1", 2.0, 10.0)], found
    assert found["porthole"] == [("door_open", "/toy/Objects/porthole_1", 4.0, None),
                                 ("door_shut", "/toy/Objects/porthole_1", 15.0, None)], found
    assert found["spray_run"] == [], found
    assert needs.event_sounds(needs.events([], moves[2:], {})[0], rows, kinds, table) == []
    assert "data/checks/row-kinds.json" in needs.WORK["event"], needs.WORK
    # Two gates of one row, swung alike each about its own side (as the motion stage writes a row's objects), are two
    # events, each sounding at its own prim; a gate's bar turning about that gate's named hinge rides it, one event.
    swing = {"about": {"side": [-1.0, 0.0, 0.0]}, "angle": 90.0, "speed": 30.0,
             "moves": [[4.0, "open"], [12.0, "shut"]]}
    alike = [{"name": f"yard_gate_{number}", "prim": f"/toy/Objects/yard_gate_{number}", "row": "yard_gate",
              "start": 0.0, "length": 20.0, "loop": False, "swing": swing} for number in (1, 2)]
    hinged = dict(swing, about="Objects/gate_hinge_1")
    riding = [{"name": name, "prim": f"/toy/Objects/{name}", "row": "yard_gate", "start": 0.0, "length": 20.0,
               "loop": False, "swing": hinged} for name in ("yard_gate_3", "yard_gate_3_bar")]
    sounded = [sorted({use["on"] for use in moving.event_uses(event, rows, kinds, table, {})})
               for event in needs.events([], alike + riding, {})]
    assert sounded == [[f"/toy/Objects/yard_gate_{number}"] for number in (1, 2, 3)], sounded
    # Fault (the audit of 2026-11-04): every door played a spacecraft hatch's latch and airlock bolts, Hong Kong's
    # too. By the house table, a wooden door plays an ordinary latch, a metal hatch the hatch's, a garage door its
    # opener: the row's own words.
    house = json.loads((REPO / "data/sound/moving.json").read_text())
    worded = [{"id": "front", "name": "wooden door", "noun": "door"}, {"id": "lock", "name": "metal hatch",
                                                                       "noun": "hatch"},
              {"id": "bay", "name": "large garage door", "noun": "door"}]
    swung = [{"name": f"{row}_1", "prim": f"/toy/Objects/{row}_1", "row": row, "start": 0.0, "length": 20.0,
              "loop": False, "swing": swing} for row in ("front", "lock")]
    rising = [{"name": "bay_1", "prim": "/toy/Objects/bay_1", "row": "bay", "start": 0.0, "length": 40.0,
               "loop": False, "slide": {"by": [0.0, 8.0, 0.0], "speed": 0.235, "moves": [[0.0, "open"]]}}]
    heard = {event["name"]: [use["sound"] for use in moving.event_uses(event, worded, kinds, house, {})]
             for event in needs.events([], swung + rising, {})}
    assert heard == {"front_1": ["door_latch_open", "door_close_thud"],
                     "lock_1": ["hatch_open", "airlock_hatch_seal_clunk"], "bay_1": ["garage_door_run"]}, heard


def test_a_brief_is_one_batch_of_its_takes_and_a_lost_take_is_a_gap():
    """#21, #29: one take a sound, its brief's first prompt at seed 1, made once; the card's deadline is its takes'
    minutes, not twice them; a take that did not come back is left out of the scores (its sound a gap), never asked
    again.
    Break: score/stages/sound/takes.py: `round(FIRST_RESULT_MINUTES + MINUTES_A_TAKE * len(wanted))`
        -> `round(FIRST_RESULT_MINUTES + MINUTES_A_TAKE * len(wanted) * 2)`
    Break: score/stages/sound/takes.py:
        `shutil.copy2(back / "timings-0.json", TAKES / TIMINGS / f"{time.strftime('%Y%m%dT%H%M%S')}.json")` -> `pass`
    A loop brief's take is made long enough that its loop keeps what the level gate asks (workshop's 6 s
    robot_arm_servo, made at 6 s, looped to 3.28 s under 3.6 s, 2026-11-10); a one-shot and a loop that already
    keeps it are made at their brief's length.
    Break: score/stages/sound/takes.py: `while picker_takes.looped_seconds(seconds) < least:` -> `while False:`"""
    from score.stages.sound import takes
    servo = {"prompts": ["a servo"], "seconds": 6, "category": "loop"}
    made_at = takes.asked_seconds(servo)
    kept_share = takes.choose.KEPT_SHARE["loop"] * 6
    assert takes.picker_takes.looped_seconds(6) < kept_share <= takes.picker_takes.looped_seconds(made_at), made_at
    heard = {"category": "loop", "brief_seconds": 6}
    assert gates.length_fault(heard, takes.picker_takes.looped_seconds(made_at), 1) is None, made_at
    assert gates.length_fault(heard, takes.picker_takes.looped_seconds(6), 1) is not None
    assert made_at == 7 and takes.jobs_for("servo", servo, "rev")[0]["seconds"] == 7
    assert takes.asked_seconds({"seconds": 6, "category": "shot"}) == 6
    assert takes.asked_seconds({"seconds": 15, "category": "room"}) == 15
    jobs = [job for name in ("pump", "fan") for job in
            takes.jobs_for(name, {"prompts": [f"a {name}", f"a {name}, closer"], "seconds": 6, "seeds": 4}, "rev")]
    assert [(job["prompt"], job["seed"]) for job in jobs] == [("a pump", 1), ("a fan", 1)], jobs
    kept_folder = pathlib.Path(tempfile.mkdtemp())
    real_takes, real_on_card = takes.TAKES, takes.on_card
    asked = []

    def on_card(plan):
        asked.append(plan["minutes"])
        back = pathlib.Path(plan["runs"][0]["jobs"][0]["outputs"][0]["to"])
        (back / jobs[0]["file"]).write_bytes(b"RIFF")
        (back / "scores-0.json").write_text(json.dumps({jobs[0]["file"]: 0.41}))
        (back / "timings-0.json").write_text(json.dumps({"runs": {jobs[0]["file"]: 27.5}}))

    try:
        takes.TAKES, takes.on_card = kept_folder / "takes", on_card
        scored = takes.made(jobs, kept_folder / "work")
        kept = [json.loads(path.read_text()) for path in (kept_folder / "takes" / takes.TIMINGS).iterdir()]
        assert kept == [{"runs": {jobs[0]["file"]: 27.5}}], kept  # the take's work seconds outlive the batch
    finally:
        takes.TAKES, takes.on_card = real_takes, real_on_card
        shutil.rmtree(kept_folder)
    assert asked == [round(takes.FIRST_RESULT_MINUTES + takes.MINUTES_A_TAKE * 2)], asked
    assert scored == {jobs[0]["file"]: 0.41}, scored
    assert len(sound.candidates("pump", jobs, scored, "rev")) == 1


def test_the_moss_job_runs_the_repos_run_script_and_every_path_it_names_is_sent():
    """The image's baked moss-run named a moved script and every take failed (Batch 1, 2026-10-24): the job runs the
    repo's run script, and every repo path the script names is sent with the code.
    Break: score/stages/sound/takes.py: `"command": ["bash", f"/work/repo/{RUN_SCRIPT}", f"{REMOTE}/jobs-0.json", "0"],`
        -> `"command": ["moss-run", f"{REMOTE}/jobs-0.json", "0"],`
    Break: score/stages/sound/takes.py: `"code": ["tools/cloud/moss_generate.py", RUN_SCRIPT],` -> `"code":
        [RUN_SCRIPT],`"""
    from score.stages.sound import takes
    plan = takes.plan_for(pathlib.Path("jobs.json"), pathlib.Path("back"), 10, 1)
    run = plan["runs"][0]
    command = run["jobs"][0]["command"]
    assert command[:2] == ["bash", f"/work/repo/{takes.RUN_SCRIPT}"] and takes.RUN_SCRIPT in run["code"], plan
    script = (takes.REPO / takes.RUN_SCRIPT).read_text()
    for named in re.findall(r"/work/repo/(\S+\.py)", script):
        assert (takes.REPO / named).is_file() and named in run["code"], named


def test_no_card_had_by_the_deadline_is_a_gap_asked_once():
    """#21: the card is asked for once (its claim waits for a pool card or stock up to its deadline); none had blocks
    the row (its takes gaps), never asked again.
    Break: score/stages/sound/takes.py: `if not prove.one_attempt(plan, account, registry, store_spec, WHO, results):`
        -> `if False:`"""
    import types
    from score import graph
    from score.stages.sound import takes
    attempts = []
    batch = types.SimpleNamespace(sweep=lambda account: None, ssh_key=lambda: "key")
    prove = types.SimpleNamespace(batch=batch, one_attempt=lambda *args: attempts.append(args) or False)
    cloud = types.SimpleNamespace(account=lambda: "account", allow_key=lambda *args: None, registry=lambda: None,
                                  object_store=lambda: None)
    real_tool, real_provider = takes.prove_tool, sys.modules.get("provider")
    try:
        takes.prove_tool = lambda: prove
        sys.modules["provider"] = types.SimpleNamespace(cloud=cloud)
        try:
            takes.on_card({"classes": ["L4-1-24G"]})
            raise AssertionError("no card had was not a gap")
        except graph.Blocked as blocked:
            assert "before the deadline" in str(blocked) and len(attempts) == 1, blocked
    finally:
        takes.prove_tool = real_tool
        if real_provider is None:
            sys.modules.pop("provider", None)
        else:
            sys.modules["provider"] = real_provider
    assert len(attempts) == 1, attempts




def test_a_take_that_did_not_come_back_leaves_its_uses_out_with_its_gap():
    """Every sound the garage plays is made here (no old pick is left, 2026-10-21); its batch brings nothing back: the
    record leaves every use out, names each a gap, and `sources` has nothing to judge (nothing rented: the take step
    answers nothing).
    Break: score/stages/sound/__init__.py:
        `kept = [use for use in uses if use["sound"] in sounds or use["sound"] not in made_here]` -> `kept = uses`"""
    from score.stages import batch_gaps
    with tempfile.TemporaryDirectory() as folder, kept_designs({"garage": [{"id": "tracked_rover", "noun": "rover"}]}):
        inputs = inputs_for("garage", folder)
        made_here = sound.to_make(list(dict.fromkeys(use["sound"] for use in sound.uses_of("garage", inputs))), inputs)
        assert "rover_idle" in made_here, made_here
        nothing_back, sound.moss_takes.made = sound.moss_takes.made, lambda jobs, work: {}
        try:
            inputs, out = made("garage", folder)
        finally:
            sound.moss_takes.made = nothing_back
        record = gates.record_of(out)
        names = {entry["name"] for entry in batch_gaps.read([out])}
        assert "rover_idle: no MOSS take came back" in names, names
        assert not record["uses"], record["uses"]
        assert gates.judge_sources(out, inputs, None).answer == checks.UNKNOWN




def test_the_environment_names_a_brief_for_every_moving_part_it_plays_and_for_the_voice():
    """Every sound moving.json and voices.json name is a library brief the batch can make (data/sound/sounds.json,
    with prompts): a name with no brief would be silent with no take to ask. A check of the environment's data.
    Break: data/sound/voices.json: `"people": "crew_talk"` -> `"people": "no_such_brief"`
    Break: data/sound/moving.json: a `words` entry's `"name": "garage_door_run"` -> `"name": "no_such_brief"`"""
    briefs = json.loads((REPO / "data/sound/sounds.json").read_text())["sounds"]
    table = json.loads((REPO / "data/sound/moving.json").read_text())
    worded = [{key: value for key, value in entry.items() if key != "words"}
              for entries in table["words"].values() for entry in entries]
    named = [part["name"] for moves in [*table["kinds"].values(), *worded] for move in moves.values()
             for part in move["sounds"] if part.get("name")]
    voices = json.loads((REPO / "data/sound/voices.json").read_text())
    named += [voices["people"], *(entry["sound"] for entry in voices["by_hearing"])]
    assert all(briefs.get(name, {}).get("pick", {}).get("prompts") for name in named), named
    assert all(any(part.get("name") for part in move["sounds"]) for moves in table["kinds"].values()
               for move in moves.values()), "a kind's move with no sound named fails events wherever it moves"
