"""A thing with moving parts is built in code with its parts apart, each on its pivot (#19, 2026-11-05): env1's kinds of
rows (a garage's "square double door", a docking airlock's "floor hatch", a "lunar rover", a "black police car") take
their parted rule, and a single hinged door, a "tracked rover", a drone and a cabinet take none; the double door's two
leaves hinge on its outer edges about the upright, the left the positive way and the right the negative, the hatch's
lid on its level edge, the rover's four wheels spin about their axles at their own middles, each part a node of its
own whose name the motion layer reads its joint from (from_design.PART) and whose origin is its pivot, every part
finished with a recipe of the library (data/library/materials.json), the object at its row's size centred over its
floor; its model and record are written, the model's nodes by their part names.

Breaks (each applied once, seen red, reverted), in score/stages/props/moving_parts/__init__.py:
    `return "double door" if "double" in said else None` -> `return "double door"` (a single door is parted)
    `(0.0, 0.0, inner), "hinge", "y", -1)` -> `(0.0, 0.0, inner), "hinge", "y", 1)` (both leaves open apart)
    `if kind in VEHICLES and not said & set(TRACKED) and "drone" not in said:` -> `if kind in VEHICLES:`
    `transform=trimesh.transformations.translation_matrix(pivot))` -> `transform=np.eye(4))` (no pivot at the origin)
    a wheel's `"rubber"` -> `"tyre"` (a finish no library recipe names)

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/props/moving_parts/
"""
import json
import pathlib

import numpy as np
import trimesh

from score.stages import row_kinds
from score.stages.motion import from_design
from score.stages.props import moving_parts

REPO = pathlib.Path(__file__).resolve().parents[4]
ROWS = {"square_door": ({"id": "square_door", "name": "square double door", "noun": "door",
                         "size": [2.5, 0.2, 2.5]}, "double door"),
        "floor_hatch": ({"id": "floor_hatch", "name": "floor hatch", "noun": "hatch", "size": [0.6, 0.6, 0.1]},
                        "hatch"),
        "rover": ({"id": "rover", "name": "lunar rover", "noun": "rover", "size": [4.5, 2.5, 2.5]}, "wheeled"),
        "police_car": ({"id": "police_car", "name": "black police car", "noun": "police car",
                        "size": [1.9, 4.8, 1.5]}, "wheeled"),
        "door": ({"id": "door", "name": "door", "noun": "door", "size": [1.0, 0.1, 2.1]}, None),
        "tracked_rover": ({"id": "tracked_rover", "name": "tracked rover", "noun": "rover",
                           "size": [2.5, 1.8, 1.5]}, None),
        "drone": ({"id": "drone", "name": "drone", "noun": "drone", "size": [0.5, 0.5, 0.2]}, None),
        "cabinet": ({"id": "cabinet", "name": "cabinet", "noun": "cabinet", "size": [0.8, 0.6, 1.8]}, None)}


def joints(record):
    return {entry["name"]: (entry["joint"], entry["axis"], entry["sign"]) for entry in record["parts"]}


def test_a_moving_thing_is_built_with_its_parts_on_their_pivots(tmp_path):
    kinds = row_kinds.table()
    assert {name: moving_parts.parted(row, kinds) for name, (row, _) in ROWS.items()} == \
        {name: rule for name, (_, rule) in ROWS.items()}
    recipes = set(json.loads((REPO / moving_parts.RECIPES).read_text())["recipes"])
    built = {name: moving_parts.build(row, kinds) for name, (row, rule) in ROWS.items() if rule}
    door, hatch, rover = (built[name][1] for name in ("square_door", "floor_hatch", "rover"))
    assert joints(door) == {"frame": (None, None, 1), "leaf_left__hinge_y": ("hinge", "y", 1),
                            "leaf_right__hinge_yn": ("hinge", "y", -1)}
    pivots = {entry["name"]: entry["pivot"] for entry in door["parts"]}
    assert pivots["leaf_left__hinge_y"][2] == -pivots["leaf_right__hinge_yn"][2] == -1.1  # the jambs' inner faces
    assert joints(hatch) == {"frame": (None, None, 1), "lid__hinge_xn": ("hinge", "x", -1)}
    wheels = {name: joint for name, joint in joints(rover).items() if name.startswith("wheel")}
    assert len(wheels) == 4 and set(wheels.values()) == {("spin", "x", 1)}
    for name, (scene, record) in built.items():
        assert {entry["finish"] for entry in record["parts"]} <= recipes, (name, record["parts"])
        size = moving_parts.frame_size(ROWS[name][0])
        low, high = scene.bounds
        assert np.allclose(high - low, size, atol=1e-6) and np.allclose([low[0] + high[0], low[1], low[2] + high[2]],
                                                                         0.0, atol=1e-6), (name, scene.bounds)
        for entry in record["parts"]:
            placed, _ = scene.graph[entry["name"]]
            assert np.allclose(placed[:3, 3], entry["pivot"], atol=1e-5), (name, entry["name"])
            named = from_design.PART.match(entry["name"])
            assert (named["joint"], named["axis"]) == (entry["joint"], entry["axis"]) if entry["joint"] else not named
    wheel = next(entry for entry in rover["parts"] if entry["name"] == "wheel_1__spin_x")
    hub = built["rover"][0].geometry["wheel_1__spin_x"].bounds.mean(axis=0)
    assert np.allclose(hub, 0.0, atol=1e-6), (wheel, hub)  # it spins at its own middle
    written = moving_parts.write(ROWS["square_door"][0], kinds, tmp_path)
    loaded = trimesh.load(tmp_path / "model.glb")
    assert written == json.loads((tmp_path / "parts.json").read_text())
    assert {"frame", "leaf_left__hinge_y", "leaf_right__hinge_yn"} <= set(loaded.graph.nodes_geometry)
