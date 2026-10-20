"""The cast stage's make and gates on a one-person cast on the hub's seed: the person stands and keeps clear; the record
holds 1 where a concept showing 3 fails `counted` and one showing 1 passes; a person lifted off the floor fails
`standing`, one stood in a thing fails `clear`; a look with no usable dress row is not made (an accepted gap, the gate passing), one whose dress row
the runner gave is; a crowd's lattice keeps two body widths apart; KEEP is box_masks.py's.

Run: .venv/bin/python score/stages/cast/cast_test.py   (needs the hub's round-three seed in the work folder)
"""
import json
import pathlib
import re
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages import cast  # noqa: E402
from score.stages.cast import measure, spread  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402


def hub_inputs(folder, record, concept_people):
    """The hub's inputs with its record and concept count swapped for the given ones, written into `folder`."""
    inputs = {name: pathlib.Path((pattern[0] if isinstance(pattern, tuple) else pattern).format(
        place="hub", data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"), repo=str(REPO)))
        for name, pattern in cast.files("hub").items()}
    inputs["record"] = folder / "record.json"
    inputs["record"].write_text(json.dumps(record))
    inputs["concept_people"] = folder / "concept"
    inputs["concept_people"].mkdir(exist_ok=True)
    instances = [{"judged": "person"}] * concept_people
    (inputs["concept_people"] / "people.json").write_text(json.dumps(
        {"hub": {"v1": {"people": concept_people, "instances": instances}}}))
    return inputs


def answers(record, concept_people):
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inputs = hub_inputs(folder, record, concept_people)
        out = folder / "out"
        out.mkdir()
        cast.make(inputs, out, 0, {})
        assert cast.cast_faults(out) == []
        return {check.name: check.judge(out, inputs, None) for check in cast.CHECKS}


def hub_record():
    """A one-person cast on the hub's seed (the hub's own cast holds nobody: its concept's figure is a chair)."""
    return {"place": "hub", "people": [{"name": "bram", "character": "bram", "look": "bram_work", "doing": "bench",
                                        "at": [-0.535, -0.407, 0.9], "facing_to": [-0.606, -0.407, 1.517],
                                        "why": "at the operations console in the pit"}]}


def test_the_hub():
    found = answers(hub_record(), 3)
    assert found["standing"].answer == checks.PASS, found["standing"].reason
    assert found["clear"].answer == checks.PASS, found["clear"].reason
    assert found["counted"].answer == checks.FAIL and found["counted"].measures["cast"] == 1
    # a look with no dressed body is an accepted gap carried down, never a stop (complete's people check fails it)
    assert found["made"].answer == checks.PASS and found["made"].measures["missing"] >= 1
    assert all("no accepted dressed body" in finding for finding in found["made"].findings)
    assert "drapes" not in found
    assert answers(hub_record(), 1)["counted"].answer == checks.PASS


def test_a_person_off_the_floor_or_in_a_thing():
    lifted = hub_record()
    lifted["people"][0]["at"][1] += 0.3
    assert answers(lifted, 1)["standing"].answer == checks.FAIL
    inside = hub_record()
    nev = inside["people"][0]
    nev["at"] = list(nev["facing_to"])  # where he faces: the console
    found = answers(inside, 1)["clear"]
    assert found.answer == checks.FAIL and "runs into" in found.reason, found.reason


def test_a_look_is_made_by_its_usable_dress_row():
    look = cast.look_of({"character": "bram", "look": "bram_work"})
    assert look == ("bram", "work")
    assert cast.made_row(look, "hub", {"people-dress-bram-work": "accepted"}) == "people-dress-bram-work"
    assert cast.made_row(look, "hub", {}) is None
    assert cast.made_row(look, "camp", {"people-dress-bram-work": "accepted"}) is None  # the camp's is coloured
    assert cast.made_row(look, "camp", {"people-dress-bram-work-in-camp": "a"}) == "people-dress-bram-work-in-camp"
    assert cast.made_row(None, "hub", {}) is None
    assert cast.look_of({"character": "kit_m_avg", "worn": ["plain_coat_grey", "head_f1"]}) == ("kit_m_avg", "coat-grey")


def test_a_crowd_lattice_keeps_bodies_apart():
    crowd = {"spread": [0.0, 0.0, 6.0, 6.0], "seed": 3, "count": 10, "facing_to": [0.0, 0.0, -10.0],
             "turn_jitter": 0.1, "height_jitter": 0.0, "doing": ["standing"], "shares": [1.0], "phases": 1,
             "palettes": [[0, 0, 0]], "palette_shares": [1.0]}
    spots = [copy["at"] for copy in spread.lattice(crowd, [])]
    nearest = min(((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 for number, a in enumerate(spots)
                  for b in spots[number + 1:])
    assert len(spots) > 100 and nearest >= 2 * measure.BODY_RADIUS, (len(spots), nearest)


def test_a_crowd_keeps_clear_of_each_view():
    view = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -10.0], "fov": 70}
    near, far, behind = {"at": [0.0, 0.0, -4.0]}, {"at": [0.0, 0.0, -20.0]}, {"at": [0.0, 0.0, 4.0]}
    assert spread.frame_share(view, near["at"]) > spread.FAR_SHARE > spread.frame_share(view, far["at"])
    assert spread.far_enough([near, far, behind], [view]) == [far, behind]


def test_a_group_wears_only_its_kit():
    cast_rules, _ = measure.characters()
    kit = {"builds": ["m_avg", "w_slim"], "plain": ["uniform_olive"]}
    mixes = [cast_rules.kit_mix(seed, kit) for seed in range(200)]
    assert {mix["character"] for mix in mixes} == {"kit_m_avg", "kit_w_slim"}
    assert {mix["worn"]["plain"][0] for mix in mixes} == {"plain_uniform_olive"}


def test_copied_constants_agree():
    cast_rules, cast_check = measure.characters()
    assert (measure.BODY_RADIUS, measure.KNEE, measure.HEAD) == (cast_check.BODY_RADIUS, cast_check.KNEE,
                                                                 cast_check.HEAD)


def test_keep_is_box_masks():
    text = (REPO / "tools/props/scene/box_masks.py").read_text()
    assert int(re.search(r"^KEEP = (\d+)", text, re.M).group(1)) == cast.KEEP


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
