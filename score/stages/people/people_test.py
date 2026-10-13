"""The people stage's checks on made-up records (no cloud, no models): the surface rows' renamed inputs, the body
gates, the dress's glTF round trip and the clips' clearance easing."""
import json
import pathlib
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/characters/maker"))

from score.stages.people import bodies, clips, dress, far, renamed  # noqa: E402
import clearance  # noqa: E402


def test_renamed_inputs():
    found = renamed.as_surfaces({"people-parts": "a", "surfaces": "b", "people-body-x": "c"})
    assert found == {"surfaces-parts": "a", "surfaces": "b", "surfaces-body-x": "c"}, found


def write_checks(folder, deep, bind_deep, tuck_over=0):
    """A body's records with two clips: walking with the given counts, standing clean."""
    checks = folder / "checks"
    checks.mkdir(parents=True)
    (checks / "bodycloth.json").write_text(json.dumps({
        "margin_mm": 3.0, "bind": {"deep_by_part": {"boot_r": bind_deep}},
        "clips": {"walking": {"deep_by_part": {"boot_r": deep}, "deepest_mm": 9.0},
                  "standing": {"deep_by_part": {"boot_r": bind_deep}, "deepest_mm": 2.0}}}))
    clip = {"worst_tuck_out_mm": 2.0, "frames_tuck_over": 0, "rigid_stretch": 1.0, "most_crossings": 10}
    (checks / "pokes.json").write_text(json.dumps({"rest_crossings": 10, "clips": {
        "walking": dict(clip, worst_tuck_out_mm=2.0 + tuck_over, frames_tuck_over=tuck_over), "standing": clip}}))
    (checks / "pokes_shipped.json").write_text(json.dumps({"rest_crossings": 10, "clips": {
        "walking": {"most_crossings": 20}, "standing": {"most_crossings": 20}}}))


def test_a_body_is_judged_clip_by_clip():
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        write_checks(folder, deep=13, bind_deep=13)
        assert clips.usable(folder) == (["standing", "walking"], {})
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        write_checks(folder, deep=50, bind_deep=13, tuck_over=3)
        passing, failing = clips.usable(folder)
        assert passing == ["standing"] and len(failing["walking"]) == 2, failing
        verdict = bodies.judge_clips(folder, {}, {})
        assert verdict.answer == "pass" and verdict.measures["failing"] == 1 and "walking" in verdict.findings[0]


def test_a_far_only_look_is_judged_on_its_far_body():
    with tempfile.TemporaryDirectory() as held:
        checks = pathlib.Path(held) / "checks"
        checks.mkdir()
        (checks / "build.json").write_text(json.dumps({"levels": {"far": {"triangles": 1220},
                                                                  "coat": {"triangles": 34159}}}))
        (checks / "shell.json").write_text(json.dumps({"offset_most_m": 0.09}))
        assert far.judge_far_triangles(pathlib.Path(held), {}, {}).answer == "pass"
        recorded = far.judge_near_recorded(pathlib.Path(held), {}, {})
        assert recorded.answer == "pass" and recorded.measures == {"near_triangles": 34159, "shell_most_m": 0.09}


def test_a_cast_doing_a_failing_clip_fails():
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        (folder / "casts").mkdir()
        (folder / "casts" / "lab.json").write_text(json.dumps({"place": "lab", "people": [
            {"name": "a", "look": "bram_work", "doing": "walking"}, {"name": "b", "look": "bram_work",
                                                                      "doing": "standing"}]}))
        (folder / "cut.json").write_text(json.dumps({"cast_names": {}}))
        (folder / "usable.json").write_text(json.dumps({"bram-work": {"usable": ["standing"],
                                                                     "failing": {"walking": ["tucks: 5.1 mm"]}}}))
        verdict = clips.judge_casts(folder, {"casts": folder / "casts", "cut": folder / "cut.json"}, {})
        assert verdict.answer == "fail" and verdict.measures == {"failing": 1, "judged": 2}, verdict


def shell_verdict(soft_tail):
    """judge_shell on a look of 1,000 soft points, `soft_tail` of them 8 cm off, and a hand and a boot 12 cm off."""
    with tempfile.TemporaryDirectory() as held:
        checks = pathlib.Path(held) / "checks"
        checks.mkdir()
        near, far = [0] * 21, [0] * 81
        near[20], far[80] = 1000 - soft_tail, soft_tail
        rigid = [0] * 121
        rigid[120] = 50
        (checks / "shell.json").write_text(json.dumps({"scale": 1.0, "parts": {
            "1": {"most_m": 0.02, "offsets_mm": near}, "2": {"most_m": 0.08, "offsets_mm": far},
            "3": {"most_m": 0.12, "offsets_mm": rigid}, "4": {"most_m": 0.12, "offsets_mm": rigid}}}))
        (checks / "parts.json").write_text(json.dumps({"parts": [
            {"part": 1, "role": "garment", "name": "cloth"}, {"part": 2, "role": "garment", "name": "cloth"},
            {"part": 3, "role": "hard", "name": "boot"}, {"part": 4, "role": "skin", "name": "skin_hands"}]}))
        return bodies.judge_shell(pathlib.Path(held), {}, {})


def test_the_shell_holds_most_soft_points_and_leaves_rigid_parts_out():
    passing, failing = shell_verdict(9), shell_verdict(20)
    assert passing.answer == "pass" and passing.measures["offset_share_m"] == 0.02, passing
    assert passing.measures["offset_most_m"] == 0.08 and "part 2" in passing.reason, passing
    assert failing.answer == "fail" and failing.measures["offset_share_m"] == 0.08, failing


def test_missing_record_is_unknown():
    with tempfile.TemporaryDirectory() as held:
        joins = dict((check.name, check) for check in bodies.checks())["joins"]
        assert joins.judge(pathlib.Path(held), {}, {}).answer == "unknown"


def test_dress_keeps_the_binary_chunk():
    with tempfile.TemporaryDirectory() as held:
        path = pathlib.Path(held) / "a.glb"
        blob = np.arange(9, dtype=np.float32).tobytes()
        document = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(blob)}],
                    "bufferViews": [{"buffer": 0, "byteLength": len(blob)}],
                    "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}]}
        rest = len(blob).to_bytes(4, "little") + b"BIN\x00" + blob
        dress.write_glb(path, document, rest)
        read, kept = dress.read_glb(path)
        assert kept == rest and read["asset"] == document["asset"]
        assert np.allclose(dress.positions(read, kept, 0).ravel(), np.arange(9))


def test_clearance_eases_out_and_back():
    angles = np.zeros(20)
    angles[10] = 0.3
    eased = clearance.spread(angles)
    assert eased[10] >= 0.3 and eased[8] > 0 and eased[0] == 0 and eased[19] == 0, eased


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("people stage checks pass")
