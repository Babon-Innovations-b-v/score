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

from score.stages.people import bodies, dress, renamed  # noqa: E402
import clearance  # noqa: E402


def test_renamed_inputs():
    found = renamed.as_surfaces({"people-parts": "a", "surfaces": "b", "people-body-x": "c"})
    assert found == {"surfaces-parts": "a", "surfaces": "b", "surfaces-body-x": "c"}, found


def write_checks(folder, deep, bind_deep, tuck_over=0):
    checks = folder / "checks"
    checks.mkdir(parents=True)
    (checks / "bodycloth.json").write_text(json.dumps({
        "margin_mm": 3.0, "bind": {"deep_by_part": {"boot_r": bind_deep}},
        "clips": {"walking": {"deep_by_part": {"boot_r": deep}, "deepest_mm": 9.0}}}))
    (checks / "pokes.json").write_text(json.dumps({
        "verdict": {"tucks": tuck_over == 0, "rigid": True, "cloth_through_cloth": True},
        "clips": {"walking": {"worst_tuck_out_mm": 2.0 + tuck_over, "frames_tuck_over": tuck_over,
                              "rigid_stretch": 1.0}}}))


def test_body_through_cloth_holds_the_bind():
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        write_checks(folder, deep=13, bind_deep=13)
        assert bodies.judge_body_through_cloth(folder, {}, {}).answer == "pass"
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        write_checks(folder, deep=50, bind_deep=13, tuck_over=3)
        assert bodies.judge_body_through_cloth(folder, {}, {}).answer == "fail"
        tucks = dict((check.name, check) for check in bodies.checks())["tucks"]
        assert tucks.judge(folder, {}, {}).answer == "fail"


def test_the_shell_leaves_rigid_parts_out():
    with tempfile.TemporaryDirectory() as held:
        checks = pathlib.Path(held) / "checks"
        checks.mkdir()
        (checks / "shell.json").write_text(json.dumps({"scale": 1.0, "parts": {
            "1": {"most_m": 0.02}, "2": {"most_m": 0.09}, "3": {"most_m": 0.08}}}))
        (checks / "parts.json").write_text(json.dumps({"parts": [{"part": 1, "role": "garment"},
                                                                 {"part": 2, "role": "hard"},
                                                                 {"part": 3, "role": "skin"}]}))
        found = bodies.judge_shell(pathlib.Path(held), {}, {})
        assert found.answer == "fail" and len(found.findings) == 1 and "part 3" in found.findings[0], found


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
