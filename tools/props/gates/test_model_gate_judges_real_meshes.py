"""The model gate (G5, model.py) passes a real mesh in the proportions it is laid at and fails one that is not: a
cube laid as a panel, a hollow shell laid thinner than its walls; and room.py places every laid piece's own model as
HubKit does (fitted into a unit box on its foot, then scaled, turned and moved by the piece), never its box.

One room is laid from a folder of real models, one piece a case row; the gate runs once through model.main on it and
room.placed places it once, and every row's answer (its class, spread, wall floor, pass, where it stands) is worked
out by hand from its sizes (in each row's comment).

Breaks that turn the test red (each applied once and seen red, 2026-11-13):
- room.unit_fit's `foot` made the box's centre (`(low + high) / 2`).
- room.piece_matrix's `* np.array(laid["size"])` dropped.
- model.check's `found["spread"] <= SPREAD_LIMIT and` dropped.
- model.least_wall returns THINNEST_LIMIT always; and, apart, `return SOLID_SHARE * thinnest_side - RAY_START` made
  `return 0.0`.
- shape_class's `if middle / largest < SLENDER_SHARE: return "slender"` made `"chunky"`.
"""
import json
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model  # noqa: E402
import room  # noqa: E402

NOTE = (0.129, 0.001, 0.281)


def box(extents):
    return trimesh.creation.box(extents=extents)


def hollow_note():
    """A sticky note's shell: the inner box faces in, so its walls are 0.2 mm."""
    shell = trimesh.util.concatenate([box(NOTE), box((0.12, 0.0006, 0.27))])
    shell.faces[12:] = shell.faces[12:, ::-1]
    return shell


# (model name, kind, its mesh or None for no file, laid size, at x, class, spread, least wall, thinnest (value, tol)
#  or None, pass, placed bounds or None for left out). A piece stands at (x, 0, 0) unturned: it spans x +- wide / 2,
#  y 0..tall, z +- deep / 2.
CASES = [
    # A 2 x 4 x 1 model laid 1 x 2 x 3: chunky (1/3 not flat, 2/3 not slender), judged on all three sides; model
    # 0.5 : 1 : 0.25 against laid 0.33 : 0.67 : 1, the worst ratio 1 / 0.25 = 4, spread 3.
    ("crate", "crate", box((2.0, 4.0, 1.0)), (1.0, 2.0, 3.0), 5.0, "chunky", 3.0, 0.003, None, False,
     [[4.5, 0.0, -1.5], [5.5, 2.0, 1.5]]),
    # A panel laid 1.2 x 2.0 x 0.06 is flat (0.06 / 2.0 thin, 1.2 / 2.0 wide): judged on its face, 1.2 : 2.0.
    ("panel", "hub_wall_upper_plain", box((1.2, 2.0, 0.06)), (1.2, 2.0, 0.06), 10.0, "flat", 0.0, 0.003,
     (0.06, 0.005), True, [[9.4, 0.0, -0.03], [10.6, 2.0, 0.03]]),
    # A cube laid as that panel: its face is 1 : 1, so its error is (2.0 / 1.2) - 1 = 0.67, over the 20% rule.
    ("cube", "hub_wall_upper_plain", box((1.0, 1.0, 1.0)), (1.2, 2.0, 0.06), 15.0, "flat", 2.0 / 1.2 - 1, 0.003,
     None, False, [[14.4, 0.0, -0.03], [15.6, 2.0, 0.03]]),
    # A rib 0.12 / 4.6 is under a quarter: slender, its proportions not judged.
    ("rib", "hub_lattice_hip_rib", box((0.12, 4.6, 0.12)), (0.12, 4.6, 0.12), 20.0, "slender", 0.0, 0.003, None,
     True, [[19.94, 0.0, -0.06], [20.06, 4.6, 0.06]]),
    # Its name says it is an opening, whatever its box; its face 1.2 : 1.2 matches.
    ("porthole", "hub_porthole_panel", box((1.2, 1.2, 0.1)), (1.2, 1.2, 0.1), 25.0, "opening", 0.0, 0.003, None,
     True, [[24.4, 0.0, -0.05], [25.6, 1.2, 0.05]]),
    # A 1 mm sticky note can never have a 3 mm wall: held instead to being solid through its own thickness,
    # 0.9 * 1 mm - 0.1 mm = 0.8 mm. A solid one is.
    ("note", "note", box(NOTE), NOTE, 30.0, "flat", 0.0, 0.0008, None, True,
     [[29.9355, 0.0, -0.1405], [30.0645, 0.001, 0.1405]]),
    # A shell with 0.2 mm walls laid 1 mm fails the 0.8 mm floor.
    ("note_hollow", "note", hollow_note(), NOTE, 35.0, "flat", 0.0, 0.0008, None, False,
     [[34.9355, 0.0, -0.1405], [35.0645, 0.001, 0.1405]]),
    # Laid 10 mm, its walls are then 2 mm: under the 3 mm wall (2026-10-26).
    ("note_hollow_thick", "note", hollow_note(), (0.129, 0.01, 0.281), 40.0, "flat", 0.0, 0.003, None, False,
     [[39.9355, 0.0, -0.1405], [40.0645, 0.01, 0.1405]]),
    # A piece whose model is in no folder is reported missing and left out of the room.
    ("missing", "missing", None, (1.0, 1.0, 1.0), 0.0, None, None, None, None, None, None),
]


def test_the_model_gate_judges_each_laid_piece_by_its_real_mesh(tmp_path, monkeypatch):
    folder = tmp_path / "models"
    folder.mkdir()
    layout = {"kinds": {}, "models": {}, "pieces": []}
    for name, kind, mesh, laid, at_x, *_ in CASES:
        if mesh is not None:
            (folder / f"{name}.glb").write_bytes(mesh.export(file_type="glb"))
        layout["kinds"][kind] = {}
        layout["models"][name] = {}
        layout["pieces"].append({"kind": kind, "model": name, "at": [at_x, 0.0, 0.0], "size": list(laid),
                                 "x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]})
    (tmp_path / "layout.json").write_text(json.dumps(layout))
    monkeypatch.setattr(sys, "argv", ["model.py", str(tmp_path / "layout.json"), "--models", str(folder),
                                      "--report", str(tmp_path / "report.json")])
    model.main()
    report = json.loads((tmp_path / "report.json").read_text())
    resolve = room.models_in(folder)
    placed = {index: mesh for index, _, mesh in room.placed(layout, resolve)}

    # A model is fitted into a unit box standing on its foot's middle.
    assert np.allclose(resolve("crate", {}).bounds, [[-0.5, 0.0, -0.5], [0.5, 1.0, 0.5]])
    for index, (name, kind, mesh, laid, _, shape, spread, wall, thinnest, passes, bounds) in enumerate(CASES):
        found = report[name]
        if mesh is None:
            assert found == {"missing": True, "pass": None}, name
            assert index not in placed, name
            continue
        assert found["class"] == shape, (name, found)
        assert abs(found["spread"] - spread) < 0.01, (name, found)
        assert found["watertight"], (name, found)
        assert model.least_wall(laid) == wall, name
        if thinnest is not None:
            assert abs(found["thinnest"] - thinnest[0]) < thinnest[1], (name, found)
        assert found["pass"] is passes, (name, found)
        assert np.allclose(placed[index].bounds, bounds), (name, placed[index].bounds)
