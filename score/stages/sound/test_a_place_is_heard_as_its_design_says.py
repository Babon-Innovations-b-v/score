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

The test names the breaks that turn it red (`Break: <file>: `old` -> `new``); each was applied once, seen red and
reverted.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/sound/test_a_place_is_heard_as_its_design_says.py
    (reads the sounds' bytes from the library; the made record's world, which plays them, is left out where no
    library is configured: SCORE_LIB_*, or no score_lib checkout beside score)
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
import warnings

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
    # a door the motion row swings plays its latch as it starts to open and its bolts as it is shut tight (its swing's
    # angle over its speed later), round after round: opens at 2 s, shuts at 10 s, 90 degrees at 30 a second taking
    # 3 s: latch at 2, bolts at 13, the next 20 s round's latch at 22
    {"id": "the door and the person sounding pass events and voices", "gates": ("events", "voices"),
     "answer": checks.PASS, "times": {DOOR_PRIM: [("door_open", 2.0), ("door_shut", 13.0), ("door_open", 22.0)]}},
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


# --- moving things' events, by row kind and move (moving.py) ----------------------------------------------------------

SWING = {"about": {"side": [-1.0, 0.0, 0.0]}, "angle": 90.0, "speed": 30.0, "moves": [[4.0, "open"], [12.0, "shut"]]}
SLIDING = {"kinds": {"door": {"slide": {"sounds": [{"name": "door_slide_open", "part": "start", "when": "open"},
                                                   {"name": "door_slide_close", "part": "start", "when": "shut"}],
                                        "from": "a test's slide"}, **TABLE["kinds"]["door"]},
                     "vehicle": {"path": {"sounds": [{"name": "rover_motor", "part": "drive"},
                                                     {"name": "rover_wheels_gravel", "part": "drive"}],
                                          "from": "a test's drive"}}}}  # the rule, sounds named
YARD = [{"id": "yard_gate", "noun": "gate"}, {"id": "cart", "noun": "cart"}, {"id": "boom", "noun": "boom"}]
WORDED = [{"id": "front", "name": "wooden door", "noun": "door"},
          {"id": "lock", "name": "metal hatch", "noun": "hatch"},
          {"id": "bay", "name": "large garage door", "noun": "door"}]


def gate_move(name, swing=SWING):
    return {"name": name, "prim": f"/toy/Objects/{name}", "row": "yard_gate", "start": 0.0, "length": 20.0,
            "loop": False, "swing": swing}


# A place written here, its names unlike any place's (its rows, the game's motions and the motion row's moves, its
# moving sounds table: a test's, or None for the house's data/sound/moving.json); each event it makes plays these
# (sound, prim, at, loops until). The same table answers any place.
EVENTS = [
    # a gate (a door) sliding in a game motion plays the door slide in its round's seconds; a cart (a vehicle) on a
    # path its drive; a thing whose record names only its motion kind (a hatch) swings as a door; a boom, no kind,
    # nothing (a gap with its work)
    {"id": "each moving thing sounds by its row kind and move, never its name", "rows": YARD, "table": SLIDING,
     "motions": [{"name": "west_entry", "prim": "/toy/Objects/yard_gate_1", "start": 0.0, "length": 10.0,
                  "loop": True, "sounds": [],
                  "slide": {"by": [2.0, 0.0, 0.0], "speed": 1.0, "moves": [[1.0, "open"], [5.0, "shut"]]}}],
     "moves": [{"name": "loop_a", "prim": "/toy/Objects/cart_1", "start": 2.0, "length": 8.0, "loop": False,
                "path": {"points": [[0, 0, 0], [5, 0, 0]]}},
               {"name": "porthole", "prim": "/toy/Objects/porthole_1", "kind": "hatch", "start": 0.0,
                "length": 20.0, "loop": False,
                "swing": {"angle": 90.0, "speed": 30.0, "moves": [[4.0, "open"], [12.0, "shut"]]}},
               {"name": "spray_run", "prim": "/toy/Objects/boom_1", "start": 0.0, "length": 8.0, "loop": False,
                "slide": {"by": [0.0, 0.0, 4.0], "speed": 0.5, "moves": [[0.0, "open"]]}}],
     "heard": {"west_entry": [("door_slide_open", "/toy/Objects/yard_gate_1", 1.0, None),
                              ("door_slide_close", "/toy/Objects/yard_gate_1", 5.0, None)],
               "loop_a": [("rover_motor", "/toy/Objects/cart_1", 2.0, 10.0),
                          ("rover_wheels_gravel", "/toy/Objects/cart_1", 2.0, 10.0)],
               "porthole": [("door_open", "/toy/Objects/porthole_1", 4.0, None),
                            ("door_shut", "/toy/Objects/porthole_1", 15.0, None)],
               "spray_run": []}},
    # two gates of one row, swung alike each about its own side (as the motion stage writes a row's objects), are two
    # events, each at its own prim; a gate's bar turning about that gate's named hinge rides it, one event
    {"id": "gates swung alike are an event each, a bar on a gate's hinge rides it", "rows": YARD, "table": SLIDING,
     "motions": [],
     "moves": [gate_move("yard_gate_1"), gate_move("yard_gate_2"),
               *(gate_move(name, dict(SWING, about="Objects/gate_hinge_1"))
                 for name in ("yard_gate_3", "yard_gate_3_bar"))],
     "heard": {f"yard_gate_{number}": [("door_open", f"/toy/Objects/yard_gate_{number}", 4.0, None),
                                       ("door_shut", f"/toy/Objects/yard_gate_{number}", 15.0, None)]
               for number in (1, 2, 3)}},
    # the audit of 2026-11-04: every door played a spacecraft hatch's latch and airlock bolts, Hong Kong's too; by the
    # house table a wooden door plays an ordinary latch, a metal hatch the hatch's, a garage door its opener
    {"id": "by the house table a door sounds by its row's own words", "rows": WORDED, "table": None, "motions": [],
     "moves": [{**gate_move(f"{row}_1"), "row": row} for row in ("front", "lock")] + [
         {"name": "bay_1", "prim": "/toy/Objects/bay_1", "row": "bay", "start": 0.0, "length": 40.0, "loop": False,
          "slide": {"by": [0.0, 8.0, 0.0], "speed": 0.235, "moves": [[0.0, "open"]]}}],
     "heard": {"front_1": [("door_latch_open", "/toy/Objects/front_1", 4.0, None),
                           ("door_close_thud", "/toy/Objects/front_1", 15.0, None)],
               "lock_1": [("hatch_open", "/toy/Objects/lock_1", 4.0, None),
                          ("airlock_hatch_seal_clunk", "/toy/Objects/lock_1", 15.0, None)],
               "bay_1": [("garage_door_run", "/toy/Objects/bay_1", 0.0, 34.0426)]}},
]
# moving.py's rounds are the assembly's (tools/usd/sound.rounds_of): one, a short loop's, a long loop's
ROUNDS = [{"start": 1.0}, {"start": 0.0, "length": 14.0, "loop": True}, {"start": 0.0, "length": 86.0, "loop": True}]


# --- a scene's uses and needs from its design alone (uses_of, needs.py) -----------------------------------------------

NEW_ROWS = [{"id": "main_desk", "name": "main desk", "noun": "console"}, {"id": "roof_duct", "noun": "duct"},
            {"id": "buggy", "noun": "rover"}, {"id": "panel_light", "noun": "light"},
            {"id": "paper_lantern", "noun": "lantern"}, {"id": "table", "noun": "table"},
            {"id": "pilot", "noun": "person"}]
NEW_PEOPLE = {"pilot": {"looks": ["pilot-drawn"]}, "officer": {"looks": ["officer-drawn"]}}
TOY_ROWS = [{"id": "hatch", "noun": "door"}, {"id": "pilot", "noun": "person"}]
# A scene no sound table names (its plan, scene inventory and people only, read from a new concept) over the
# environment's tables, or (`named` false) tables naming no sound (a moving sounds table whose parts name none, no
# voice). Its object uses are `heard` (sound, row) where given; its needs ({(kind, item): {field: value}}) and its gaps'
# work ({gap id: what the work names}) as given; `beyond` the rows the plan sees beyond the place, `gapped` the people
# an accepted bodies gap leaves unlaid.
SCENES = [
    # each row whose kind sounds plays its kind's library sound (a console its hum, a duct the vent's air, a rover its
    # idle, a ceiling light its buzz; a lantern, a noun its kind leaves silent, nothing), its first person the voice
    {"id": "a new scene sounds from its design alone", "scene": "new_scene", "rows": NEW_ROWS, "people": NEW_PEOPLE,
     "named": True,
     "heard": [("console_hum", "main_desk"), ("crew_talk", "officer"), ("lamp_buzz", "panel_light"),
               ("rover_idle", "buggy"), ("vent_air", "roof_duct")],
     "needs": {("voice", "people"): {"sounds": ["crew_talk"], "state": needs.MAKE,
                                     "prim": "/new_scene/Characters/officer"}}},
    # street and stairwell (2026-11-11): a row the plan sees beyond the place (the street's distant floodlight) and a
    # person an accepted bodies gap leaves unlaid (the stairwell's man) were played at nothing
    {"id": "a row seen beyond the place and a person a bodies gap leaves unlaid play nothing", "scene": "new_scene",
     "rows": NEW_ROWS, "people": NEW_PEOPLE, "named": True, "beyond": ["buggy"], "gapped": ["officer"],
     "heard": [("console_hum", "main_desk"), ("crew_talk", "pilot"), ("lamp_buzz", "panel_light"),
               ("vent_air", "roof_duct")]},
    # #29: a door row the design moves with no sound named for its kind's move, and the people it stands with no voice
    # named, are each a gap naming its work
    {"id": "what the library does not answer is a need naming its work", "scene": "toy", "rows": TOY_ROWS,
     "people": {"pilot": {"looks": ["p-d"]}}, "named": False,
     "needs": {("event", "hatch"): {"state": needs.NONE, "prim": "/toy/hatch"},
               ("voice", "people"): {"state": needs.NONE}},
     "work": {"sound:event:hatch": "data/sound/moving.json", "sound:voice:people": "data/sound/voices.json"}},
    # the environment's own tables name a brief for each, which the sound row's batch makes
    {"id": "the environment's tables name a brief the batch makes", "scene": "toy", "rows": TOY_ROWS,
     "people": {"pilot": {"looks": ["p-d"]}}, "named": True,
     "needs": {("event", "hatch"): {"state": needs.MAKE}, ("voice", "people"): {"state": needs.MAKE}}},
]


def unnamed(table):
    """The moving sounds table with no part naming its sound."""
    worded = [entry for entries in table["words"].values() for entry in entries]
    for moves in [*table["kinds"].values(), *worded]:
        for move in [value for key, value in moves.items() if key != "words"]:
            move["sounds"] = [{key: value for key, value in part.items() if key != "name"} for part in move["sounds"]]
    return table


def scene_world(row, folder):
    """`row`'s scene (SCENES): a data folder (the environment's sound tables, or unnamed ones; row kinds; its people)
    and a design folder (its scene inventory), and the place's inputs over them (its plan, with `beyond`; its gaps)."""
    data = pathlib.Path(folder) / "data"
    for part in ("sound", "checks", "people"):
        (data / part).mkdir(parents=True)
    for name in ("sounds", "catalogue", "voices", "moving"):
        shutil.copyfile(REPO / f"data/sound/{name}.json", data / f"sound/{name}.json")
    if not row["named"]:
        table = unnamed(json.loads((data / "sound/moving.json").read_text()))
        (data / "sound/moving.json").write_text(json.dumps(table))
        (data / "sound/voices.json").write_text(json.dumps({"people": None}))
    shutil.copyfile(REPO / "data/checks/row-kinds.json", data / "checks/row-kinds.json")
    (data / "people/rows.json").write_text(json.dumps({"places": {row["scene"]: {"rows": row["people"]}}}))
    design = pathlib.Path(folder) / "design"
    (design / "inventory").mkdir(parents=True)
    (design / "inventory" / f"{row['scene']}.json").write_text(json.dumps({"rows": row["rows"]}))
    inputs = inputs_for("hub", folder)
    inputs.update({"plan": pathlib.Path(folder) / f"{row['scene']}.json",
                   "scene inventory": design / "inventory" / f"{row['scene']}.json",
                   "people": data / "people/rows.json", "voices": data / "sound/voices.json"})
    inputs["plan"].write_text(json.dumps({"leads": {}, "rows": {"DESK": ["main_desk"]},
                                          **({"beyond": row["beyond"]} if "beyond" in row else {})}))
    if row.get("gapped"):
        inputs["gaps"] = str(pathlib.Path(folder) / "gaps.json")
        pathlib.Path(inputs["gaps"]).write_text(json.dumps({"gaps": [{"row": "characters-layer", "check": "bodies",
                                                                      "objects": row["gapped"]}]}))
    return data, design, inputs


# --- the takes: one a brief, one card a batch (takes.py) --------------------------------------------------------------

SHARE_FAILED = "the moss job failed on this PC's card: share 0"
# A batch's lines side by side (`lines`, each a place's line making the same jobs: each sound's brief, None the
# library's), the card bringing back the takes `back` names (by job) at `score`, with its timings (`timings`, a take's
# work seconds) and its job's failure (`fails`), or (`card` None) no card had by the deadline. The card is asked for
# `asked` (each time, its takes' sounds); each line hears `heard` ({job: CLAP score}, or "<error>: <what it says>").
TAKES = [
    # #29: crew_talk, played in several places, made on one card, the second line waiting for it and reading its score
    {"id": "a brief several places play is one take on one card, the second line reading it",
     "lines": ("airlock", "cockpit"), "jobs": [("crew_talk", None)], "back": [0], "score": 0.4,
     "asked": [["crew_talk"]], "heard": {0: 0.4}},
    {"id": "a shared take that does not come back is a gap on every line, never asked again",
     "lines": ("hub", "airlock"), "jobs": [("crew_talk", {"prompts": ["crew talk"]})], "back": [],
     "asked": [["crew_talk"]], "heard": {}},
    # a generator that never ran (this PC's moss job, "moss_generate.py: command not found" for days, 13e63538) is the
    # framework's fault, not a gap
    {"id": "a job that failed as a job with no take back fails the row on every line, never a gap",
     "lines": ("hub", "airlock"), "jobs": [("crew_talk", {"prompts": ["crew talk"]})], "back": [],
     "fails": SHARE_FAILED, "asked": [["crew_talk"]], "heard": "JobFailed: share 0"},
    {"id": "a failed job that brought a take back leaves only its missing takes as gaps", "lines": ("garage",),
     "jobs": [("pump", {"prompts": ["a pump"]}), ("fan", {"prompts": ["a fan"]})], "back": [0], "score": 0.4,
     "fails": SHARE_FAILED, "asked": [["pump", "fan"]], "heard": {0: 0.4}},
    # #21: one take a sound, its brief's first prompt at seed 1; the take's work seconds outlive the batch
    {"id": "a brief is one take, its lost take a gap, its timings kept", "lines": ("hub",),
     "jobs": [(name, {"prompts": [f"a {name}", f"a {name}, closer"], "seconds": 6, "seeds": 4})
              for name in ("pump", "fan")],
     "back": [0], "score": 0.41, "timings": 27.5, "asked": [["pump", "fan"]], "heard": {0: 0.41}},
    # #21: the claim waits for a pool card or stock up to its deadline; none had blocks the row
    {"id": "no card had by the deadline blocks the row, asked once", "lines": ("hub",),
     "jobs": [("crew_talk", {"prompts": ["crew talk"]})], "card": None, "asked": [["crew_talk"]],
     "heard": "Blocked: before the deadline"},
]
# A brief's take is made at its length; a loop's long enough that its loop keeps what the level gate asks (workshop's
# 6 s robot_arm_servo, made at 6 s, looped to 3.28 s under 3.6 s, 2026-11-10). (brief, the seconds it is made at)
LENGTHS = [({"prompts": ["a servo"], "seconds": 6, "category": "loop"}, 7),
           ({"seconds": 6, "category": "shot"}, 6), ({"seconds": 15, "category": "room"}, 15)]


@contextlib.contextmanager
def swapped(module, **values):
    """`module`'s names set to `values`, put back after."""
    real = {name: getattr(module, name) for name in values}
    for name, value in values.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in real.items():
            setattr(module, name, value)


def asked_with(plan):
    """(the plan, the sounds of the takes it carries), read while the card is asked."""
    return plan, [job["sound"] for job in json.loads(pathlib.Path(plan["runs"][0]["inputs"][0]["from"]).read_text())]


@contextlib.contextmanager
def no_card_had(seen):
    """prove.py and the cloud provider as a claim that gets no card by its deadline, each plan tried kept in `seen`."""
    import types
    from score.stages.sound import takes
    batch = types.SimpleNamespace(sweep=lambda account: None, ssh_key=lambda: "key")
    prove = types.SimpleNamespace(batch=batch, one_attempt=lambda plan, *rest: seen.append(asked_with(plan)) and False)
    cloud = types.SimpleNamespace(account=lambda: "account", allow_key=lambda *args: None, registry=lambda: None,
                                  object_store=lambda: None)
    real_provider = sys.modules.get("provider")
    sys.modules["provider"] = types.SimpleNamespace(cloud=cloud)
    try:
        with swapped(takes, prove_tool=lambda: prove):
            yield
    finally:
        if real_provider is None:
            sys.modules.pop("provider", None)
        else:
            sys.modules["provider"] = real_provider


def card_of(row, seen):
    """`row`'s card (TAKES): it brings back the takes `back` names, their scores and timings, and its job's failure."""
    def on_card(plan):
        seen.append(asked_with(plan))
        if len(row["lines"]) > 1:
            time.sleep(0.3)  # the card at work while the other line asks
        back = pathlib.Path(plan["runs"][0]["jobs"][0]["outputs"][0]["to"])
        wanted = json.loads(pathlib.Path(plan["runs"][0]["inputs"][0]["from"]).read_text())
        files = [wanted[index]["file"] for index in row["back"]]
        for name in files:
            (back / name).write_bytes(b"RIFF")
        if files:
            (back / "scores-0.json").write_text(json.dumps({name: row["score"] for name in files}))
        if "timings" in row:
            (back / "timings-0.json").write_text(json.dumps({"runs": {name: row["timings"] for name in files}}))
        return row.get("fails")
    return on_card


def batch_of(row, folder, jobs):
    """`row`'s batch (TAKES): its lines run side by side on `jobs` against its card; (each (plan, its takes' sounds)
    the card was asked with, what each line heard, the timings kept)."""
    import threading
    from score import graph
    from score.stages.sound import takes
    folder = pathlib.Path(folder)
    seen, heard = [], {}

    def line(place):
        try:
            heard[place] = takes.made(jobs, folder / f"work-{place}")
        except (takes.JobFailed, graph.Blocked) as error:
            heard[place] = f"{type(error).__name__}: {error}"

    card = no_card_had(seen) if row.get("card", True) is None else swapped(takes, on_card=card_of(row, seen))
    with swapped(takes, TAKES=folder / "takes"), card:
        lines = [threading.Thread(target=line, args=(place,)) for place in row["lines"]]
        for each in lines:
            each.start()
        for each in lines:
            each.join()
        timings = folder / "takes" / takes.TIMINGS
        kept = [json.loads(path.read_text()) for path in timings.iterdir()] if timings.is_dir() else []
    return seen, heard, kept


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


def named_in(data):
    """Every sound the data folder's moving sounds and voices tables name (each a brief the batch must make)."""
    table = json.loads((data / "sound/moving.json").read_text())
    worded = [{key: value for key, value in entry.items() if key != "words"}
              for entries in table["words"].values() for entry in entries]
    named = [part["name"] for moves in [*table["kinds"].values(), *worded] for move in moves.values()
             for part in move["sounds"] if part.get("name")]
    voices = json.loads((data / "sound/voices.json").read_text())
    return named + [name for name in [voices["people"], *(entry["sound"] for entry in voices.get("by_hearing", []))]
                    if name]

def test_a_place_is_heard_as_its_design_says(toy):
    """A place's bed comes from its design alone (BEDS): how it is heard, the tones it plays, and what its design lacks,
    named, never guessed. The `bed` gate passes a decided bed and fails an undecided one naming what lacks; its bed gap
    says what lacks, or that a decided bed is still to make, the sound row's to make only where the design is kept
    (the plaza), else naming the work, never a node the table lacks (the hut). Its record plays and its gates judge
    each world of VERDICTS as that row says, its door sounding off its own moves round after round. Each moving thing
    of EVENTS sounds by its row kind and move, and moving.py's rounds are the assembly's; each scene of SCENES plays and
    needs from its design alone, and the environment's tables name a brief for every sound they play. The takes of
    TAKES are one a brief, one card a batch: a shared take made once, a lost one a gap on every line and never asked
    again, a job failed as a job the row's failure, no card had a block; each plan runs the repo's run script with every
    path it names sent, its deadline its takes' minutes. A take that did not come back leaves its uses out.
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
        -> `return [use["on"] for use in uses`
    Break: score/stages/sound/moving.py: `return [(end, None) for _, end in moves_of(motion, entry["when"])]`
        -> `return [(start, None) for start, _ in moves_of(motion, entry["when"])]`
    Break: score/stages/sound/moving.py:
        `return [start + length * number for number in range(max(1, math.ceil(SOUND_SPAN_SECONDS / length)))]`
        -> `return [start]`
    Break: score/stages/sound/moving.py:
        `return next((kind for kind, rule in kinds.items() if rule.get("motion", {}).get("kind") == entry["kind"]),
        None)`
        -> `return None`
    Break: score/stages/sound/needs.py: `return pivots[0] if pivots else entry["prim"]` -> `return entry["prim"]`
    Break: score/stages/sound/moving.py: `found = next((worded[move] for worded in table.get("words", {}).get(kind,
        []) if said & set(worded["words"]) and move in worded), None) or` -> `found =`
    Break: score/stages/sound/__init__.py: `return [{"sound": voice, "role": "object", "on": people[0],`
        -> `return [{"sound": voice, "role": "object", "on": people[-1],`
    Break: score/stages/sound/__init__.py: object_uses' `if row["id"] in beyond: continue` -> `if False: continue`,
        or voice_uses' `if name not in gapped]` -> `]`
    Break: score/stages/sound/needs.py: `if not names or any(not has_file(name) and not briefed(name) for name in
        names):`
        -> `if any(not has_file(name) and not briefed(name) for name in names):`
    Break: data/sound/voices.json: `"people": "crew_talk"` -> `"people": "no_such_brief"`
    Break: data/sound/moving.json: a `words` entry's `"name": "garage_door_run"` -> `"name": "no_such_brief"`
    Break: score/stages/sound/takes.py: `for name in sorted({job["file"] for job in jobs}):` -> `for name in []:`
    Break: score/stages/sound/takes.py: `lost_before = [job for job in wanted if asked_here(job)]` -> `lost_before =
        []`
    Break: score/stages/sound/takes.py: `if failed and not came_back:` -> `if False:`
    Break: score/stages/sound/takes.py: `        if failed:\n            raise JobFailed` -> `        if False:\n
        raise JobFailed`
    Break: score/stages/sound/takes.py: `round(FIRST_RESULT_MINUTES + MINUTES_A_TAKE * len(wanted))`
        -> `round(FIRST_RESULT_MINUTES + MINUTES_A_TAKE * len(wanted) * 2)`
    Break: score/stages/sound/takes.py:
        `shutil.copy2(back / "timings-0.json", TAKES / TIMINGS / f"{time.strftime('%Y%m%dT%H%M%S')}.json")` -> `pass`
    Break: score/stages/sound/takes.py: `while picker_takes.looped_seconds(seconds) < least:` -> `while False:`
    Break: score/stages/sound/takes.py: `"command": ["bash", f"/work/repo/{RUN_SCRIPT}", f"{REMOTE}/jobs-0.json", "0"],`
        -> `"command": ["moss-run", f"{REMOTE}/jobs-0.json", "0"],`
    Break: score/stages/sound/takes.py: `"code": ["tools/cloud/moss_generate.py", RUN_SCRIPT],` -> `"code":
        [RUN_SCRIPT],`
    Break: score/stages/sound/takes.py: `if not prove.one_attempt(plan, account, registry, store_spec, WHO, results):`
        -> `if False:`
    Break: score/stages/sound/__init__.py:
        `kept = [use for use in uses if use["sound"] in sounds or use["sound"] not in made_here]` -> `kept = uses`"""
    from score.stages import batch_gaps, row_kinds
    from score.stages.complete.gaps import price
    from score.stages.sound import moving, takes
    sys.path.insert(0, str(REPO / "tools/usd"))
    import sound as layer  # noqa: E402  (tools/usd: the assembly's rounds, which moving.py repeats)
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
    for row in VERDICTS:
        with tempfile.TemporaryDirectory() as folder:
            inputs, out = world_of(row, folder)
            record = gates.record_of(out)
            for on, voiced in row.get("voiced", {}).items():
                assert [use["sound"] for use in record["uses"] if use["on"] == on] == voiced, (row["id"], record)
            for on, times in row.get("times", {}).items():
                played = [(use["sound"], use["at"]) for use in record["uses"] if use["on"] == on]
                assert played[:len(times)] == times, (row["id"], played)
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
    kinds = row_kinds.table(REPO / "data/checks/row-kinds.json")
    house = json.loads((REPO / "data/sound/moving.json").read_text())
    for row in EVENTS:
        table = row["table"] or house
        events = needs.events(row["motions"], row["moves"], {})
        found = {event["name"]: [(use["sound"], use["on"], use["at"], use["loops_until"])
                                 for use in moving.event_uses(event, row["rows"], kinds, table, {})]
                 for event in events}
        assert found == row["heard"], (row["id"], found)
        assert all(needs.event_sounds(event, row["rows"], kinds, table) == list(dict.fromkeys(
            heard[0] for heard in row["heard"][event["name"]])) for event in events), row["id"]
    assert "data/checks/row-kinds.json" in needs.WORK["event"], needs.WORK  # a silent kind's gap names its table
    assert [moving.rounds_of(motion) for motion in ROUNDS] == [layer.rounds_of(motion) for motion in ROUNDS]
    assert moving.SOUND_SPAN_SECONDS == layer.SOUND_SPAN_SECONDS
    for row in SCENES:
        with tempfile.TemporaryDirectory() as folder:
            data, design, inputs = scene_world(row, folder)
            assert sound.place_of(inputs) == row["scene"], row["id"]
            uses = [use for use in sound.uses_of(row["scene"], inputs) if use["role"] == "object"]
            if "heard" in row:
                assert sorted((use["sound"], use["on"]) for use in uses) == row["heard"], (row["id"], uses)
                assert {use["on"] for use in uses} <= gates.standing(inputs), (row["id"], uses)
            found = {(need["kind"], need["item"]): need for need in needs.needs(row["scene"], data, design)}
            assert all(found[key][field] == value for key, wanted in row.get("needs", {}).items()
                       for field, value in wanted.items()), (row["id"], found)
            gaps = {gap["id"]: gap for gap in needs.gaps(row["scene"], data, design)}
            assert all(named in gaps[gap]["work"] for gap, named in row.get("work", {}).items()), (row["id"], gaps)
            # every sound the tables name is a library brief the batch can make: a name with no brief would be silent
            # with no take to ask; a kind's move with no sound named fails events wherever it moves
            briefs = json.loads((data / "sound/sounds.json").read_text())["sounds"]
            named = named_in(data)
            assert bool(named) == row["named"], (row["id"], named)
            assert all(briefs.get(name, {}).get("pick", {}).get("prompts") for name in named), (row["id"], named)
            moves = [move for moves in json.loads((data / "sound/moving.json").read_text())["kinds"].values()
                     for move in moves.values()]
            assert all(any(part.get("name") for part in move["sounds"]) for move in moves) == row["named"], row["id"]
    # crew_talk, the voice of every place whose design stands people, is one take of the environment's plan, counted
    # once by the price's forecast rule
    with tempfile.TemporaryDirectory() as folder, kept_designs({"airlock": [], "cockpit": []}), swapped(
            takes, TAKES=pathlib.Path(folder) / "takes"):
        voiced = voiced_data(folder)
        plan = sound.environment_takes(voiced, sound.moss_weights())
        shared = [places for job, places in plan.values() if job["sound"] == "crew_talk"]
        assert len(shared) == 1 and len(shared[0]) > 1, shared
        assert sum(price.rule_units("sound_takes", [], voiced, place) for place in beds.places()) == len(plan)
    script = (takes.REPO / takes.RUN_SCRIPT).read_text()
    for row in TAKES:
        jobs = [job for name, brief in row["jobs"] for job in takes.jobs_for(
            name, brief or sound.brief_of(name, {"sounds": REPO / "data/sound/sounds.json"}), "rev")]
        assert [(job["prompt"], job["seed"]) for job in jobs] == [
            ((brief or sound.brief_of(name, {"sounds": REPO / "data/sound/sounds.json"}))["prompts"][0], 1)
            for name, brief in row["jobs"]], (row["id"], jobs)
        with tempfile.TemporaryDirectory() as folder:
            asked, heard, timings = batch_of(row, folder, jobs)
        assert [sounds for _, sounds in asked] == row["asked"], (row["id"], asked)
        for plan, sounds in asked:  # the image's baked moss-run named a moved script, Batch 1, 2026-10-24
            run = plan["runs"][0]
            assert plan["minutes"] == round(takes.FIRST_RESULT_MINUTES + takes.MINUTES_A_TAKE * len(sounds)), plan
            assert run["jobs"][0]["command"][:2] == ["bash", f"/work/repo/{takes.RUN_SCRIPT}"], plan
            assert all((takes.REPO / named).is_file() and named in run["code"]
                       for named in [takes.RUN_SCRIPT, *re.findall(r"/work/repo/(\S+\.py)", script)]), run["code"]
        if isinstance(row["heard"], str):
            error, says = row["heard"].split(": ", 1)
            assert all(text.startswith(f"{error}: ") and says in text for text in heard.values()), (row["id"], heard)
            assert sorted(heard) == sorted(row["lines"]), (row["id"], heard)
        else:
            wanted = {jobs[index]["file"]: score for index, score in row["heard"].items()}
            assert heard == {place: wanted for place in row["lines"]}, (row["id"], heard)
            assert [len(sound.candidates(job["sound"], [job], wanted, "rev")) for job in jobs] == [
                int(job["file"] in wanted) for job in jobs], row["id"]
        assert timings == ([{"runs": {jobs[index]["file"]: row["timings"] for index in row["back"]}}]
                           if "timings" in row else []), (row["id"], timings)
    for brief, seconds in LENGTHS:
        made_at = takes.asked_seconds(brief)
        assert made_at == seconds and takes.jobs_for("take", dict(brief, prompts=["a take"]), "rev")[0][
            "seconds"] == seconds, (brief, made_at)
        heard = {"category": brief["category"], "brief_seconds": brief["seconds"]}
        kept = takes.picker_takes.looped_seconds if brief["category"] in takes.picker_takes.LOOPED else float
        assert gates.length_fault(heard, kept(made_at), 1) is None, (brief, made_at)
        assert made_at == brief["seconds"] or gates.length_fault(heard, kept(brief["seconds"]), 1) is not None, brief
        assert made_at == brief["seconds"] or (kept(brief["seconds"]) < takes.choose.KEPT_SHARE[brief["category"]] *
                                               brief["seconds"] <= kept(made_at)), brief
    # every sound the garage plays is made here (no old pick is left, 2026-10-21); its batch brings nothing back: the
    # record leaves every use out, names each a gap, and `sources` has nothing to judge (the take step answers nothing)
    library = sound.library_files.settings().get("SCORE_LIB_ROOT")  # the picked sounds' bytes are the library's
    with tempfile.TemporaryDirectory() as folder, kept_designs({"garage": [{"id": "tracked_rover", "noun": "rover"}]}):
        inputs = inputs_for("garage", folder)
        made_here = sound.to_make(list(dict.fromkeys(use["sound"] for use in sound.uses_of("garage", inputs))), inputs)
        assert "rover_idle" in made_here, made_here
        if library:
            with swapped(sound.moss_takes, made=lambda jobs, work: {}):
                out = pathlib.Path(folder) / "out"
                out.mkdir()
                sound.make(inputs, out, 0, {})
            assert sound.layer_faults(out) == [], sound.layer_faults(out)
            record = gates.record_of(out)
            names = {entry["name"] for entry in batch_gaps.read([out])}
            assert "rover_idle: no MOSS take came back" in names, names
            assert not record["uses"], record["uses"]
            assert gates.judge_sources(out, inputs, None).answer == checks.UNKNOWN
    if not library:  # every other check above ran; only the garage's make was left out, and the run says so (a
        # pytest.skip here would mark the whole one test as not run: the sandbox always empties SCORE_LIB_ROOT)
        warnings.warn("no library configured here (SCORE_LIB_ROOT empty): the garage's make, its gap and its record "
                      "were not checked; every other check ran")
