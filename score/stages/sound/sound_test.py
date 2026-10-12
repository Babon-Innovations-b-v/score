"""The sound stage's make and gates on places whose sounds are all picked already (no take is made, nothing rented):
the hub and the airlock pass all four gates; a sound with no file fails `sources`, as does an object sound at a row
the place does not hold; a file made too loud fails `level`; a MOSS sound under the CLAP floor fails `likeness`; a
Freesound recording the owner did not choose fails `no freesound`.

Run: .venv/bin/python score/stages/sound/sound_test.py   (reads the world's release, fetched once)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")
