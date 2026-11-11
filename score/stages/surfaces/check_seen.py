"""surfaces-check's make with a ship place's view distance: route_check.make_check, given a kit laid from its own
scene record. bake_check.seen_degrees sizes a model from the kit it reads, and the old kits were retired on
2026-10-21, so every ship model's view distance was none and the one-look check named it unknown (shiplock's sliding
door, 2026-11-11: "no view distance"). The kit laid here is each scene-record object that names its bake, at its spot,
sized as its bake made it (baked.json). Its own module, set on the row in the table (stages.bake_checked), so no row
reading bake_check.py (the people's, the crops') moves for it.
"""
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import route_check  # noqa: E402


def make_check(inputs, out, seed, params):
    """route_check.make_check, with `kit` (laid_kit) beside a scene record its inputs carry."""
    scene = inputs.get("scene record")
    if scene is None or not pathlib.Path(scene).is_file() or "kit" in inputs:
        return route_check.make_check(inputs, out, seed, params)
    baked = json.loads((pathlib.Path(inputs["surfaces-bake"]) / "baked.json").read_text())
    with tempfile.TemporaryDirectory() as temporary:
        kit = pathlib.Path(temporary) / "kit.json"
        kit.write_text(json.dumps(laid_kit(json.loads(pathlib.Path(scene).read_text()), baked)))
        return route_check.make_check(dict(inputs, kit=kit), out, seed, params)


def laid_kit(record, baked):
    """A kit of the scene record's objects (bake_check.seen_degrees' `pieces`): each top-level object whose bake the
    bake made, at its spot, in its baked size."""
    return {"pieces": [{"model": entry["bake"], "at": entry["at"], "size": baked[entry["bake"]]["size"]}
                       for entry in record.get("objects", [])
                       if entry.get("bake") in baked and isinstance(entry.get("at"), list) and len(entry["at"]) == 3
                       and "size" in baked[entry["bake"]]]}
