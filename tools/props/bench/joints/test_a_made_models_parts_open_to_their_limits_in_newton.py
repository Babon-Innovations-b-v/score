"""A made model's parts open to their limits in Newton (tools/props/bench/joints, #177): a cabinet cut as maker/parts.py
cuts it (its door on a hinge about its own y, its negative way, 0 to 100 degrees; its drawer on a slide along its own
z, 0 to 0.3 m) is staged as a place of its own with its part nodes kept, joined with each part driven toward its far
limit, and measured: a part passes only when it travels REACHED of its range and goes no more than PAST_SLACK past
it, a spin when it turns SPIN_DEGREES, and a part the trial measured no joint for fails by name. Where this box has
the trial's Python built (tools/usd/drop.LOCAL_ENV) the trial runs in Newton with MuJoCo's solver and both parts
pass; elsewhere (make tests' sandbox home) that run is skipped and said so.

Breaks (each seen red 2026-11-25):
- measured's `* (1 if part["sign"] > 0 else -1)` dropped -> the door opening its negative way reads as never opened.
- measured's `past <= PAST_SLACK[part["joint"]]` made `True` -> the drawer 0.05 m past its limit passes.
- staged without `gltf.converted` (the GLB referenced as it is) -> no part node to join: write_parted raises.
"""
import json
import pathlib
import sys

import numpy as np
import trimesh

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from tools.props.bench import joints  # noqa: E402

DOOR = {"node": "door_01__hinge_yn", "joint": "hinge", "axis": "y", "sign": -1, "limits": [0.0, 100.0], "kg": 4.0,
        "pivot": [-0.24, 0.54, 0.205]}
DRAWER = {"node": "drawer_01__slide_z", "joint": "slide", "axis": "z", "sign": 1, "limits": [0.0, 0.3], "kg": 2.0,
          "pivot": [0.0, 0.15, 0.215]}
KNOB = {"node": "knob_01__spin_z", "joint": "spin", "axis": "z", "sign": 1, "limits": None, "kg": 0.1}


def cabinet(path):
    """The cabinet's parted GLB: its carcass a body node, its door and drawer slabs under their part nodes at their
    pivots (maker/parts.written's form)."""
    scene = trimesh.Scene()
    scene.add_geometry(trimesh.creation.box((0.5, 0.8, 0.4)).apply_translation((0, 0.4, 0)), node_name="body_0",
                       geom_name="body_0")
    for part, extents, middle in ((DOOR, (0.48, 0.48, 0.02), (0.0, 0.54, 0.215)),
                                  (DRAWER, (0.48, 0.26, 0.02), (0.0, 0.15, 0.215))):
        scene.graph.update(frame_to=part["node"], frame_from=scene.graph.base_frame,
                           matrix=trimesh.transformations.translation_matrix(part["pivot"]))
        slab = trimesh.creation.box(extents).apply_translation(np.subtract(middle, part["pivot"]))
        scene.add_geometry(slab, node_name=f"{part['node']}_0", geom_name=f"{part['node']}_0",
                           parent_node_name=part["node"])
    scene.export(str(path))
    return path


def test_a_made_models_parts_open_to_their_limits_in_newton(tmp_path):
    record = {"parts": [DOOR, DRAWER]}
    trial = joints.trial_record(record)
    assert [part["drive"]["speed"] for part in trial["parted"][0]["parts"]] == [50.0, 0.15], trial
    # measured: the door its negative way to -99.5 degrees, the drawer 0.05 m past its 0.3 m, a knob that turned 30
    # degrees, a part the trial has no joint for
    out = {"hinges": {"model/door_01__hinge_yn": {"angles": [0.0, -50.0, -99.5]},
                      "model/knob_01__spin_z": {"angles": [0.0, 30.0]}},
           "slides": {"model/drawer_01__slide_z": {"metres": [0.0, 0.2, 0.35]}}}
    lost = {**DOOR, "node": "lid_01__hinge_x"}
    found = joints.measured(out, {"parts": [DOOR, DRAWER, KNOB, lost]})
    assert {node: entry["passes"] for node, entry in found.items()} == {
        "door_01__hinge_yn": True, "drawer_01__slide_z": False, "knob_01__spin_z": False, "lid_01__hinge_x": False}
    assert found["drawer_01__slide_z"]["past"] == 0.05 and found["lid_01__hinge_x"]["why"].startswith("the trial")
    # staged and joined: the part nodes laid under the object, each joined by its own joint
    folder = joints.staged(cabinet(tmp_path / "parted.glb"), record, tmp_path / "place")
    written = joints.physics.write(folder, trial, joints.MATERIALS)
    assert not written.get("faults"), written
    stage = joints.physics.opened(folder)[0]
    names = {prim.GetName() for prim in stage.Traverse() if prim.GetTypeName() in ("PhysicsRevoluteJoint",
                                                                                   "PhysicsPrismaticJoint")}
    assert names == {"model_door_01__hinge_yn", "model_drawer_01__slide_z"}, names
    if not list(joints.LOCAL_ENV.glob(".built-*")):
        print(f"skipped: the Newton run: no trial Python built at {joints.LOCAL_ENV}")
        return
    ran = joints.trialled(cabinet(tmp_path / "again.glb"), record, tmp_path / "run")
    assert all(entry["passes"] for entry in ran.values()), ran
