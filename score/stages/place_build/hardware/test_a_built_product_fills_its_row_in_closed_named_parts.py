"""A built product fills its row's box as the maker lays a model (y up, front +z, stood on y = 0, centred), every part
a closed solid under its own name, its GLB keeps those parts and their hard edges, and its record and take-in listing
carry its mass and its maker (never TRELLIS.2).

Breaks that turn this red (each applied once and seen red, then reverted):
- hardware.parts: the centring shift dropped -> the knob stands off y = 0 and off its centre
- hardware.bent: its caps dropped -> the pull handle's bar is open at its feet, no closed solid
- hardware.edged: smooth_shade's split dropped (one vertex a corner) -> the read GLB's plate corner has one normal
- hardware.written: a material's name not the part's -> the read GLB names its parts part_<n>
- hardware.socket: the dish's floor laid under the raised face (as first built) -> its pin holes sit inside the face
- hardware.made: the record's physics not the maker's shape -> the scene package finds no `physics.mass_kg`
- hardware.listing: tagged trellis2 -> the entry claims a picture-made maker
"""
import json

import numpy as np
import pytest
import trimesh

from score.stages.place_build import gltf, hardware

# kind, size (wide, deep, tall), options, the parts it must hold, whether it is made whole (hulls and mass) here
ROWS = [
    ("knob", (0.055, 0.065, 0.09), {}, {"plate", "knob", "screw"}, True),
    ("lever", (0.12, 0.06, 0.05), {}, {"rose", "lever"}, False),
    ("pull", (0.02, 0.03, 0.12), {}, {"handle", "foot"}, False),
    ("nail", (0.014, 0.02, 0.028), {}, {"nail", "wire"}, False),
    ("switch", (0.08, 0.02, 0.08), {"surround": False, "screws": 2}, {"plate", "rocker", "screw"}, False),
    ("socket", (0.08, 0.03, 0.08), {}, {"plate", "face", "hole"}, False),
    ("junction", (0.36, 0.15, 0.42), {}, {"box", "lid", "screw", "gland"}, False),
    ("meter", (0.2, 0.14, 0.42), {}, {"box", "door", "window", "dial", "hinge", "cable"}, False),
    ("split_ac", (0.8, 0.3, 0.55), {"fan": "right"}, {"case", "guard", "fan", "grille", "cover", "bracket"}, False),
    ("window_ac", (0.6, 0.5, 0.4), {"brace": False}, {"case", "louvre", "grille"}, False),
    ("grate", (0.5, 0.3, 0.05), {}, {"frame", "bars", "gully"}, False),
    ("intercom", (0.2, 0.05, 0.35), {}, {"body", "faceplate", "screen", "speaker", "keys"}, False),
]


@pytest.mark.parametrize("kind, size, options, names, whole", ROWS, ids=[row[0] for row in ROWS])
def test_a_built_product_fills_its_row_in_closed_named_parts(kind, size, options, names, whole, tmp_path):
    built = hardware.parts(kind, size, **options)
    assert set(built) == names
    assert all(hardware.closed(built).values()), hardware.closed(built)
    joined = trimesh.util.concatenate(list(built.values()))
    low, high = joined.bounds
    assert abs(low[1]) < 1e-9 and abs(low[0] + high[0]) < 1e-9 and abs(low[2] + high[2]) < 1e-9
    wide, deep, tall = size
    laid = [high[0] - low[0], high[2] - low[2], high[1] - low[1]]
    assert np.allclose(laid, [wide, deep, tall], rtol=0.12), laid
    if kind == "socket":  # the pin holes stand proud of the raised face's front (0.75 of the depth), never inside it
        assert built["hole"].bounds[1][2] - low[2] > 0.75 * deep, "pin holes buried under the face"
    path = hardware.written(built, tmp_path / f"{kind}-final.glb")
    read = {found[0]: (found[2], found[3]) for found in gltf.meshes(path)[0]}
    assert set(read) == names
    if kind == "switch":  # the plate's back corner keeps a hard edge: three normals at one point
        points, normals = read["plate"]
        corner = np.argmin(points[:, 0] + points[:, 1] + points[:, 2])
        same = np.linalg.norm(points - points[corner], axis=1) < 1e-6
        assert len({tuple(np.round(normal, 3)) for normal in normals[same]}) >= 2
    if not whole:
        return
    answer = json.dumps({"whole_kg": 0.2, "reason": "test", "parts": [{"part": number, "kg": 0.2 / len(names)}
                                                                      for number in range(len(names))]})
    record = hardware.made(kind, size, tmp_path / "made", f"{kind}.test", kind, "metal", options=options,
                           weigh=lambda body: answer)
    assert {path.name for path in record["files"].values()} == {f"{kind}.test-final.glb", f"{kind}.test-hulls.glb",
                                                                 f"{kind}.test.json"}
    kept = json.loads((tmp_path / "made" / f"{kind}.test.json").read_text())
    assert kept["physics"]["mass_kg"] == pytest.approx(0.2) and kept["physics"]["hulls"] >= 1
    listed = hardware.listing([(f"{kind}.test", record, "Knob (built, test)", tmp_path / "made")], "0" * 40)
    entry = listed["entries"][0]
    assert entry["tags"] == {"maker": ["score_hardware"]} and "trellis" not in json.dumps(listed).lower()
