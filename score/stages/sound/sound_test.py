"""The sound stage's make and gates on places whose sounds are all picked already (no take is made, nothing rented):
the hub and the airlock pass every gate; a new scene's objects and people sound from its design alone (its inventory
rows' kinds, its cast); a silent moving thing fails `events` and people with no voice
fail `voices`; a sound with no file fails `sources`, as does an object sound at a row
the place does not hold; a file made too loud fails `level`; a MOSS sound under the CLAP floor fails `likeness`; a
Freesound recording the owner did not choose fails `no freesound`.

Run: .venv/bin/python -m pytest score/stages/sound/sound_test.py   (reads the sounds' bytes from the library; a
test that plays them is skipped where no library is configured: SCORE_LIB_*, or no score_lib checkout beside score)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages import sound  # noqa: E402
from score.stages.sound import beds, gates  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


def inputs_for(place, folder, changes=None):
    """The place's inputs, with each changed record ({input name: document}) written into `folder`."""
    inputs = {name: pathlib.Path(pattern.format(place=place, data=str(REPO / "data"), home=str(beds.DESIGN.parent)))
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


def verdicts(out, inputs):
    return {check.name: check.judge(out, inputs, None) for check in sound.CHECKS}


def read(name):
    return json.loads((REPO / f"data/sound/{name}.json").read_text())


def test_picked_places_pass():
    """The hub passes every gate; so does the airlock, its people left out so their voice (crew_talk, still to make)
    is not, and nothing is rented."""
    for place, changes, failing in (("hub", None, set()), ("airlock", {"cast": {"people": []}}, set())):
        with tempfile.TemporaryDirectory() as folder:
            inputs, out = made(place, folder, changes)
            found = verdicts(out, inputs)
        assert {name for name, verdict in found.items() if verdict.answer != checks.PASS} == failing, {
            name: (verdict.reason, verdict.findings[:5]) for name, verdict in found.items()}


def recorded(place, folder, drop_on=()):
    """A sound record of the place's uses (sound.uses_of, nothing made), every sound with a file, the uses at any of
    `drop_on` left out; its inputs and output folder."""
    inputs = inputs_for(place, folder)
    uses = [use for use in sound.uses_of(place, inputs) if use["on"] not in drop_on]
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    (out / gates.RECORD).write_text(json.dumps({"place": place, "uses": uses,
                                                "sounds": {use["sound"]: {"files": ["files/x.wav"]} for use in uses}}))
    return inputs, out


def test_a_silent_moving_thing_fails_events_and_people_with_no_voice_fail_voices():
    """#29: the lab's hatch (leaf, wheel and window moving as one) and its crew's voice; the hatch's leaf silent fails
    events, Nev's voice left out fails voices."""
    with tempfile.TemporaryDirectory() as folder:
        inputs, out = recorded("lab", folder)
        assert gates.judge_events(out, inputs, None).answer == checks.PASS
        assert gates.judge_voices(out, inputs, None).answer == checks.PASS
    with tempfile.TemporaryDirectory() as folder:
        inputs, out = recorded("lab", folder, ("/lab/Objects/hatch_leaf_1", "nev"))
        events, voices = gates.judge_events(out, inputs, None), gates.judge_voices(out, inputs, None)
    assert events.answer == checks.FAIL and any("hatch_door_leaf_1" in line for line in events.findings), events
    assert voices.answer == checks.FAIL, voices


def test_needs_name_what_the_library_does_not_answer():
    """#29: free, from the place's records: the lab's hatches are answered from the library, its crew's voice is a
    brief the sound row makes (a gap naming sound@lab); the workshop's robot turntable has no sound named (a gap
    with its work); a hatch's wheel and window ride its leaf (one event)."""
    from score.stages.sound import needs
    lab = {(need["kind"], need["item"]): need["state"] for need in needs.needs("lab", REPO / "data")}
    assert lab[("event", "hatch_door_leaf_1")] == needs.LIBRARY and ("event", "hatch_door_wheel_1") not in lab, lab
    assert lab[("voice", "people")] == needs.MAKE, lab
    gaps = {gap["id"]: gap for gap in needs.gaps("lab", REPO / "data")}
    assert gaps["sound:voice:people"]["node"] == "sound@lab", gaps
    workshop = {gap["id"]: gap for gap in needs.gaps("workshop", REPO / "data")}
    assert workshop["sound:event:robot_turntable"]["node"] is None, workshop
    assert "data/sound/moving.json" in workshop["sound:event:robot_turntable"]["work"], workshop


def test_a_missing_sound_and_a_lost_row_fail_sources():
    with tempfile.TemporaryDirectory() as folder:
        inputs, out = made("hub", folder)
        record = gates.record_of(out)
        record["uses"] += [{"sound": "no_such_sound", "role": "object", "on": read_json_rows("hub")[0]["id"],
                            "from": "the test"},
                           {"sound": "base_hum", "role": "object", "on": "no_such_row", "from": "the test"}]
        (out / gates.RECORD).write_text(json.dumps(record))
        verdict = gates.judge_sources(out, inputs, None)
    assert verdict.answer == checks.FAIL and len(verdict.findings) == 2, verdict


def read_json_rows(place):
    return json.loads(sound.stage_inputs.inventory_path(place).read_text())["rows"]


def test_a_loud_file_fails_level():
    with tempfile.TemporaryDirectory() as folder:
        inputs, out = made("hub", folder)
        record = gates.record_of(out)
        path = out / record["sounds"]["habitat"]["files"][0]
        louder = path.with_name("louder.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-af", "volume=18dB", str(louder)], check=True)
        shutil.move(louder, path)
        verdict = gates.judge_level(out, inputs, None)
    assert verdict.answer == checks.FAIL and any("habitat" in line for line in verdict.findings), verdict


def test_a_low_match_fails_likeness_and_a_fetched_pick_fails_no_freesound():
    with tempfile.TemporaryDirectory() as folder:
        inputs, out = made("hub", folder)
        record = gates.record_of(out)
        record["sounds"]["habitat"]["clap"] = gates.CLAP_FLOOR - 0.01
        stepped = next(name for name, entry in record["sounds"].items() if entry["chosen_by"] == "owner")
        record["sounds"][stepped]["chosen_by"] = "scoring"
        (out / gates.RECORD).write_text(json.dumps(record))
        inputs = dict(inputs, licences=pathlib.Path(folder) / "licences.json")  # its CC0 row gone
        inputs["licences"].write_text("[]")
        assert gates.judge_likeness(out, inputs, None).answer == checks.FAIL
        assert gates.judge_no_freesound(out, inputs, None).answer == checks.FAIL


def test_a_cc0_freesound_file_passes_with_its_licence_row_and_fails_without_or_under_another_licence():
    """The owner's exception (2026-10-20, #29): a Freesound recording under CC0 with its row in
    data/sound/licences.json passes `no freesound`; with no row, or a row of another licence, it fails."""
    row = next(row for row in read("licences") if gates.FREESOUND in row["source"])
    record = {"place": "toy", "uses": [], "sounds": {"roar": {"credits": [row], "chosen_by": "scoring"}}}
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / gates.RECORD).write_text(json.dumps(record))
        licences = folder / "licences.json"

        def answer(rows):
            licences.write_text(json.dumps(rows))
            return gates.judge_no_freesound(folder, {"licences": licences}, None).answer
        assert answer([row]) == checks.PASS
        assert answer([]) == checks.FAIL
        assert answer([dict(row, licence="CC BY 4.0")]) == checks.FAIL


def test_a_brief_several_places_play_is_one_take_on_one_card_and_counted_once():
    """#29: crew_talk, played in several places, is one take of the environment's plan, counted once by the price's
    forecast rule; two places' lines side by side make it on one card, the second waiting and reading it."""
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

    try:
        takes.TAKES, takes.on_card = kept_folder / "takes", on_card
        plan = sound.environment_takes(REPO / "data", sound.moss_weights())
        shared = [places for job, places in plan.values() if job["sound"] == "crew_talk"]
        assert len(shared) == 1 and len(shared[0]) > 1, shared
        places = beds.places(REPO / "data")
        assert sum(price.rule_units("sound_takes", [], REPO / "data", place) for place in places) == len(plan)
        brief = sound.brief_of("crew_talk", {"sounds": REPO / "data/sound/sounds.json"})
        lines = [threading.Thread(target=takes.made, args=(takes.jobs_for("crew_talk", brief, "rev"),
                                                            kept_folder / f"work-{place}")) for place in shared[0][:2]]
        for line in lines:
            line.start()
        for line in lines:
            line.join()
    finally:
        takes.TAKES, takes.on_card = real_takes, real_on_card
        shutil.rmtree(kept_folder)
    assert asked == ["crew_talk"], asked


def test_a_shared_take_that_fails_is_a_gap_on_every_place_and_never_asked_again():
    """#29: two places' lines wait on one take whose card job fails: one card asked for, both lines get the gap."""
    import threading
    from score.stages.sound import takes
    kept_folder = pathlib.Path(tempfile.mkdtemp())
    real_takes, real_on_card = takes.TAKES, takes.on_card
    asked, scored = [], {}

    def on_card(plan):  # the job fails on its card: nothing comes back
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


def test_moving_things_sound_off_their_own_moves():
    """A hatch's latch plays as it starts to open (the lab's; the hub's stand shut, so make no sound) and its bolts as it is shut tight (its swing's angle over its speed
    later), in the stage's seconds, once for the leaf, wheel and window moving as one; the rover's drive loops over its
    drive; and moving.py's rounds are the assembly's (tools/usd/sound.rounds_of)."""
    lab = sound.uses_of("lab", inputs_for("lab", None))
    hatch = [(use["sound"], use["at"]) for use in lab if use["on"] == "/lab/Objects/hatch_leaf_1"]
    assert hatch == [("hatch_open", 4.0), ("airlock_hatch_seal_clunk", 18.0)], hatch
    assert not [use for use in lab if "wheel" in str(use["on"]) or "window" in str(use["on"])], "the wheel and window ride the leaf"
    hub = sound.uses_of("hub", inputs_for("hub", None))
    assert not [use for use in hub if "hatch" in str(use.get("on"))], "the hub's hatches stand shut, so stay silent"
    garage = sound.uses_of("garage", inputs_for("garage", None))
    drive = [(use["at"], use["loops_until"]) for use in garage if use["sound"] == "rover_motor"]
    assert drive == [(1.0, 7.5)], drive
    sys.path.insert(0, str(REPO / "tools/usd"))
    import sound as layer  # noqa: E402  (tools/usd: the assembly's rounds, which moving.py repeats)
    from score.stages.sound import moving
    for motion in ({"start": 1.0}, {"start": 0.0, "length": 14.0, "loop": True},
                   {"start": 0.0, "length": 86.0, "loop": True}):
        assert moving.rounds_of(motion) == layer.rounds_of(motion), motion
    assert moving.SOUND_SPAN_SECONDS == layer.SOUND_SPAN_SECONDS


def test_a_new_scene_sounds_from_its_design_alone():
    """A scene no sound table names (its plan, scene inventory and cast only, read from a new concept): each row whose
    kind sounds plays its kind's library sound at that row (a console its hum, a duct the vent's air, a rover its idle,
    a ceiling light its buzz; a lantern, a noun its kind leaves silent, nothing), its first person the people's voice;
    every target stands in its design, and its voice need reads the same records."""
    from score.stages.sound import needs
    rows = [{"id": "main_desk", "name": "main desk", "noun": "console"}, {"id": "roof_duct", "noun": "duct"},
            {"id": "buggy", "noun": "rover"}, {"id": "panel_light", "noun": "light"},
            {"id": "paper_lantern", "noun": "lantern"}, {"id": "table", "noun": "table"},
            {"id": "pilot", "noun": "person"}]
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inputs = {name: path for name, path in inputs_for("hub", folder).items() if name not in ("motion", "moves")}
        inputs.update({"plan": folder / "new_scene.json", "scene inventory": folder / "inventory.json",
                       "cast": folder / "cast.json"})
        inputs["plan"].write_text(json.dumps({"leads": {}, "rows": {"DESK": ["main_desk"]}}))
        inputs["scene inventory"].write_text(json.dumps({"rows": rows}))
        inputs["cast"].write_text(json.dumps({"people": [{"name": "pilot"}, {"name": "officer"}]}))
        assert sound.place_of(inputs) == "new_scene"
        uses = sound.uses_of("new_scene", inputs)
        heard = sorted((use["sound"], use["on"]) for use in uses if use["role"] == "object")
        assert heard == [("console_hum", "main_desk"), ("crew_talk", "pilot"), ("lamp_buzz", "panel_light"),
                         ("rover_idle", "buggy"), ("vent_air", "roof_duct")], heard
        assert {use["on"] for use in uses if use["role"] == "object"} <= gates.standing(inputs)
        data = folder / "data"
        (data / "sound").mkdir(parents=True)
        for name in ("sounds", "catalogue", "voices"):
            shutil.copyfile(REPO / f"data/sound/{name}.json", data / f"sound/{name}.json")
        (data / "characters").mkdir()
        shutil.copyfile(inputs["cast"], data / "characters/new_scene.json")
        (data / "checks").mkdir()
        shutil.copyfile(REPO / "data/checks/row-kinds.json", data / "checks/row-kinds.json")
        voice = next(need for need in needs.needs("new_scene", data) if need["kind"] == "voice")
    assert (voice["sounds"], voice["state"], voice["prim"]) == (
        ["crew_talk"], needs.MAKE, "/new_scene/Characters/pilot"), voice


def test_a_moving_thing_sounds_by_its_row_kind_and_move_never_its_name():
    """A place written here, its names unlike any place's: a gate row (a door) sliding in a game motion plays the
    library's door slide in its round's seconds; a cart row (a vehicle) on a path plays its drive; a thing whose record
    names only its motion kind (a hatch) swings as a door; a boom row, no kind, plays nothing and is a gap with its
    work. The same table answers any place."""
    from score.stages import row_kinds
    from score.stages.sound import moving, needs
    kinds, table = row_kinds.table(REPO / "data/checks/row-kinds.json"), read("moving")
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
    assert found["porthole"] == [("hatch_open", "/toy/Objects/porthole_1", 4.0, None),
                                 ("airlock_hatch_seal_clunk", "/toy/Objects/porthole_1", 15.0, None)], found
    assert found["spray_run"] == [], found
    assert needs.event_sounds(needs.events([], moves[2:], {})[0], rows, kinds, table) == []
    assert "data/checks/row-kinds.json" in needs.WORK["event"], needs.WORK
    # Two gates of one row, swung alike each about its own side (as the motion stage writes a row's objects), are two
    # events, each sounding at its own prim; a gate's bar turning about that gate's named hinge rides it, one event.
    swing = {"about": {"side": [-1.0, 0.0, 0.0]}, "angle": 90.0, "speed": 30.0, "moves": [[4.0, "open"], [12.0, "shut"]]}
    alike = [{"name": f"yard_gate_{number}", "prim": f"/toy/Objects/yard_gate_{number}", "row": "yard_gate",
              "start": 0.0, "length": 20.0, "loop": False, "swing": swing} for number in (1, 2)]
    hinged = dict(swing, about="Objects/gate_hinge_1")
    riding = [{"name": name, "prim": f"/toy/Objects/{name}", "row": "yard_gate", "start": 0.0, "length": 20.0,
               "loop": False, "swing": hinged} for name in ("yard_gate_3", "yard_gate_3_bar")]
    sounded = [sorted({use["on"] for use in moving.event_uses(event, rows, kinds, table, {})})
               for event in needs.events([], alike + riding, {})]
    assert sounded == [["/toy/Objects/yard_gate_1"], ["/toy/Objects/yard_gate_2"], ["/toy/Objects/yard_gate_3"]], sounded


def test_a_brief_is_one_batch_of_its_takes_and_a_lost_take_is_a_gap():
    """#21, #29: one take a sound, its brief's first prompt at seed 1, made once; the card's deadline is its takes'
    minutes, not twice them; a take that did not come back is left out of the scores (its sound a gap), never asked
    again."""
    from score.stages.sound import takes
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


def test_no_card_in_stock_is_a_gap_asked_once():
    """#21: the card is asked for once; none in stock blocks the row at once (its takes gaps), never waited out."""
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
            raise AssertionError("no card in stock was not a gap")
        except graph.Blocked as blocked:
            assert "in stock" in str(blocked), blocked
    finally:
        takes.prove_tool = real_tool
        if real_provider is None:
            sys.modules.pop("provider", None)
        else:
            sys.modules["provider"] = real_provider
    assert len(attempts) == 1, attempts


def test_a_take_the_batch_brought_under_the_floor_or_not_at_all_is_a_gap_and_likeness_moves_it():
    """sound@square, 2026-10-20: two MOSS takes of the batch came back under the CLAP floor (square_pa 0.12,
    leader_speech 0.26) and failed `likeness`, stopping the line though the batch rule makes each a gap. Each take made
    here under the floor, or not back, is a named batch gap; the table's likeness moves the first; a picked sound under
    the floor is no take of this batch and still fails."""
    from score import stages
    from score.stages import batch_gaps
    likeness = next(check for row in stages.STAGES if row.name == "sound" for check in row.checks
                    if check.name == "likeness")
    uses = [{"sound": "square_pa", "role": "object", "on": "pa", "from": "places.json objects"},
            {"sound": "lost_take", "role": "room", "on": None, "from": "places.json"}]
    sounds = {"square_pa": {"made_by": "moss", "clap": 0.1248, "files": []},
              "base_hum": {"made_by": "moss", "clap": 0.45, "files": []}}
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder)
        (out / gates.RECORD).write_text(json.dumps({"place": "toy", "sounds": sounds, "uses": uses[:1]}))
        batch_gaps.write(out, sound.take_gaps(["square_pa", "lost_take"], sounds, uses))
        found = {entry["name"]: entry for entry in batch_gaps.read([out])}
        assert set(found) == {"square_pa: MOSS take under the CLAP floor", "lost_take: no MOSS take came back"}, found
        assert found["lost_take: no MOSS take came back"]["faults"] == ["lost_take: no sound (room, places.json)"]
        assert gates.judge_likeness(out, {}, None).answer == checks.FAIL  # the gate's own answer stands
        moved = likeness.judge(out, {}, None)
        assert moved.answer == checks.PASS and "moved to complete as accepted gaps: square_pa" in moved.reason, moved
        sounds["base_hum"]["clap"] = 0.2
        (out / gates.RECORD).write_text(json.dumps({"place": "toy", "sounds": sounds, "uses": uses[:1]}))
        assert likeness.judge(out, {}, None).answer == checks.FAIL


def test_a_take_that_did_not_come_back_leaves_its_uses_out_with_its_gap_and_sources_passes():
    """The garage's rover_idle is made here; its batch brings nothing back: the record leaves its use out, names it a
    gap, and `sources` passes on what the place plays (nothing rented: the take step answers nothing)."""
    from score.stages import batch_gaps
    with tempfile.TemporaryDirectory() as folder:
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
        assert not any(use["sound"] in made_here for use in record["uses"]), record["uses"]
        assert gates.judge_sources(out, inputs, None).answer == checks.PASS


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            try:
                test()
            except pytest.skip.Exception as skipped:
                print(f"skipped {name}: {skipped.msg}")
                continue
            print(f"ok {name}")
