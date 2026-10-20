"""The sound stage's make and gates on places whose sounds are all picked already (no take is made, nothing rented):
the hub and the airlock pass all four gates; a sound with no file fails `sources`, as does an object sound at a row
the place does not hold; a file made too loud fails `level`; a MOSS sound under the CLAP floor fails `likeness`; a
Freesound recording the owner did not choose fails `no freesound`.

Run: .venv/bin/python -m pytest score/stages/sound/sound_test.py   (reads the sounds' bytes from the library; a
test that plays them is skipped where no library is configured, SCORE_LIB_* or $PROPS_HOME/library.env)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages import sound  # noqa: E402
from score.stages.sound import gates  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


def inputs_for(place, folder, changes=None):
    """The place's inputs, with each changed record ({input name: document}) written into `folder`."""
    inputs = {name: pathlib.Path(pattern.format(place=place, data=str(REPO / "data")))
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
    for place in ("hub", "airlock"):
        with tempfile.TemporaryDirectory() as folder:
            inputs, out = made(place, folder)
            found = verdicts(out, inputs)
        assert all(verdict.answer == checks.PASS for verdict in found.values()), {
            name: (verdict.reason, verdict.findings[:5]) for name, verdict in found.items()}


def test_a_missing_sound_and_a_lost_row_fail_sources():
    places = read("places")
    places["places"]["hub"]["loops"].append("no_such_sound")
    places["places"]["hub"]["objects"] = [{"sound": "base_hum", "on": "no_such_row"}]
    with tempfile.TemporaryDirectory() as folder:
        inputs, out = made("hub", folder, {"places": places})
        verdict = gates.judge_sources(out, inputs, None)
    assert verdict.answer == checks.FAIL and len(verdict.findings) == 2, verdict


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
        assert gates.judge_likeness(out, inputs, None).answer == checks.FAIL
        assert gates.judge_no_freesound(out, inputs, None).answer == checks.FAIL


def test_moving_things_sound_off_their_own_moves():
    """A hatch's latch plays as it starts to open (the lab's; the hub's stand shut, so make no sound) and its bolts as it is shut tight (its swing's angle over its speed
    later), in the stage's seconds; the garage's big doors, silent in the game's record, start and stop in their own
    round, at the leaves the place renamed them to, round by round; the rover's drive loops over its drive; the ship
    rooms hear their own machines; and movers.py's rounds are the assembly's (tools/usd/sound.rounds_of)."""
    lab = sound.uses_of("lab", inputs_for("lab", None))
    hatch = [(use["sound"], use["at"]) for use in lab if use["on"] == "/lab/Objects/hatch_leaf_1"]
    assert hatch == [("hatch_open", 4.0), ("airlock_hatch_seal_clunk", 18.0)], hatch
    hub = sound.uses_of("hub", inputs_for("hub", None))
    assert not [use for use in hub if "hatch" in str(use.get("on"))], "the hub's hatches stand shut, so stay silent"
    garage = sound.uses_of("garage", inputs_for("garage", None))
    door = sorted((use["sound"], use["at"]) for use in garage if use["on"] == "/garage/Places/south_door_leaf_1")
    assert door[:4] == [("lift_start", 1.0), ("lift_start", 5.0), ("lift_start", 18.0), ("lift_start", 22.0)], door
    drive = [(use["at"], use["loops_until"]) for use in garage if use["sound"] == "rover_motor"]
    assert drive == [(1.0, 7.5)], drive
    sys.path.insert(0, str(REPO / "tools/usd"))
    import sound as layer  # noqa: E402  (tools/usd: the assembly's rounds, which movers.py repeats)
    from score.stages.sound import movers
    for motion in ({"start": 1.0}, {"start": 0.0, "length": 14.0, "loop": True},
                   {"start": 0.0, "length": 86.0, "loop": True}):
        assert movers.rounds_of(motion) == layer.rounds_of(motion), motion
    assert movers.SOUND_SPAN_SECONDS == layer.SOUND_SPAN_SECONDS
    rooms = {place: sorted(use["sound"] for use in sound.uses_of(place, inputs_for(place, None))
                           if use["role"] in ("room", "object"))
             for place in ("cockpit", "galley", "engineroom", "quarters")}
    assert len({tuple(found) for found in rooms.values()}) == len(rooms), rooms


def test_a_brief_is_one_batch_of_one_take_a_prompt_and_a_lost_take_is_a_hole():
    """#21: each prompt once at takes.SEED whatever the brief's `seeds`; the card's deadline is its takes' minutes, not
    twice them; a take that did not come back is left out of the scores (its sound a hole), never asked again."""
    from score.stages.sound import takes
    jobs = takes.jobs_for("pump", {"prompts": ["a pump", "a pump, closer"], "seeds": 4, "seconds": 6}, "rev")
    assert [(job["prompt"], job["seed"]) for job in jobs] == [("a pump", 1), ("a pump, closer", 1)], jobs
    kept_folder = pathlib.Path(tempfile.mkdtemp())
    real_takes, real_on_card = takes.TAKES, takes.on_card
    asked = []

    def on_card(plan):
        asked.append(plan["minutes"])
        back = pathlib.Path(plan["runs"][0]["jobs"][0]["outputs"][0]["to"])
        (back / jobs[0]["file"]).write_bytes(b"RIFF")
        (back / "scores-0.json").write_text(json.dumps({jobs[0]["file"]: 0.41}))

    try:
        takes.TAKES, takes.on_card = kept_folder / "takes", on_card
        scored = takes.made(jobs, kept_folder / "work")
    finally:
        takes.TAKES, takes.on_card = real_takes, real_on_card
        shutil.rmtree(kept_folder)
    assert asked == [round(takes.FIRST_RESULT_MINUTES + takes.MINUTES_A_TAKE * 2)], asked
    assert scored == {jobs[0]["file"]: 0.41}, scored
    assert len(sound.candidates("pump", jobs, scored, "rev")) == 1


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
