"""Check the motion stage on stages made here: every motion record's prim is one its place's scene record writes (or
one the motion adds beside such a prim), the samples stand where the game's timing puts them (a door's travel at the
game's speed, the airlock's light lit while the pump runs, a rocket's climb at its push less Earth's pull), the layer
sits between the edit layer and the base, and an edit to a moving prim still wins.

Run: .venv/bin/python tools/usd/motion_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import sys
import tempfile

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import motion  # noqa: E402
import scene as scene_record  # noqa: E402

RATE = 24.0


def base_of(place, out):
    """A stage of the place holding the prims its scene record writes where motions can reach them: each structure
    entry as a mesh with no transform, each object as a fixture's translate, turn and scale, each light as the record
    writes it."""
    record = scene_record.record(place)
    (out / "layers").mkdir(parents=True)
    layer = Sdf.Layer.CreateNew(str(out / "layers/base.usda"))
    stage = Usd.Stage.Open(layer)
    for entry in record.get("structure", []):
        UsdGeom.Mesh.Define(stage, f"/{place}/Structure/{entry['name']}")
    for entry in record.get("objects", []):
        fixture = UsdGeom.Xform.Define(stage, f"/{place}/Fixtures/{entry['name']}")
        fixture.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
        fixture.AddRotateYOp().Set(float(entry.get("yaw", 0.0)))
        fixture.AddScaleOp().Set(Gf.Vec3f(1.0))
    scene_record.write_lights(stage, place, record.get("lights", []))
    layer.Save()
    Sdf.Layer.CreateNew(str(out / "layers/edit.usda")).Save()
    export.write_root(place, out)


def at(stage, path, seconds):
    return UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(seconds * RATE).ExtractTranslation()


def lit(stage, path, seconds):
    return UsdLux.SphereLight(stage.GetPrimAtPath(path)).GetIntensityAttr().Get(seconds * RATE)


def close(found, wanted, what):
    assert abs(found - wanted) < 1e-6, f"{what}: {found} where {wanted} was wanted"


def check_every_record_reaches_its_place(work):
    """Every record's prim is one its scene record writes, or one the motion adds beside a prim it writes."""
    for path in sorted(motion.MOTIONS.glob("*.json")):
        place = path.stem
        records = json.loads(path.read_text())
        assert records["place"] == place, f"{path.name} names place {records['place']}"
        out = work / place
        base_of(place, out)
        result = motion.write_layer(place, records, out)
        stage = Usd.Stage.Open(str(out / f"{place}.usda"))
        for entry in records["motions"]:
            assert entry.get("from"), f"{place} {entry['name']} says nowhere where its numbers came from"
            assert stage.GetPrimAtPath(entry["prim"]), f"{place} {entry['name']}: no prim {entry['prim']}"
            for sound in entry.get("sounds", []):
                assert sound.get("from") and "name" in sound and "at" in sound, f"{place} {entry['name']}: {sound}"
        assert result["moved"] == [entry["name"] for entry in records["motions"]]
        print(f"ok  {place}: {len(records['motions'])} motions on prims its scene record writes")


def check_the_airlock_cycles_as_the_game_does(work):
    stage = Usd.Stage.Open(str(work / "airlock/airlock.usda"))
    travel = 2.8 / 3.0  # the game's OPEN_DROP over its DOOR_SPEED
    inner, outer, light = "/airlock/Fixtures/inner_door", "/airlock/Fixtures/outer_door", "/airlock/Lights/cycle_light"
    close(at(stage, inner, 0.0)[1], -2.8, "the inner door sunk open with air in the chamber")
    close(at(stage, inner, 1.0 + travel / 2)[1], -1.4, "the inner door half way up at the game's speed")
    close(at(stage, inner, 1.0 + travel)[1], 0.0, "the inner door shut")
    close(at(stage, inner, 0.0)[2], -2.5, "the inner door where the game stands it")
    close(at(stage, outer, 6.0 + travel)[1], -2.8, "the outer door open once the chamber is empty")
    close(at(stage, outer, 9.0)[1], 0.0, "the outer door shut again")
    close(at(stage, inner, 14.0 + 2.0)[1], 0.0, "the second round as the first")
    full = float(UsdLux.SphereLight(stage.GetPrimAtPath(light)).GetIntensityAttr().Get())
    assert full > 0.0
    close(lit(stage, light, 0.5), 0.0, "the light dark with air in the chamber")
    close(lit(stage, light, 3.0), full, "the light lit while the pump runs")
    close(lit(stage, light, 7.0), 0.0, "the light dark with the chamber empty")
    close(lit(stage, light, 10.0), full, "the light lit while the tanks fill")
    close(lit(stage, light, 6.0 - 0.01), full, "a switch, not a fade")
    print("ok  the airlock: doors at 2.8 m in 0.93 s, the light lit for the pump's and the tanks' 5 s each")


def check_the_bay_doors(work):
    garage = Usd.Stage.Open(str(work / "garage/garage.usda"))
    close(at(garage, "/garage/Structure/big_door_west", 1.0 + 1.04)[0], -2.6, "the west leaf open, 2.6 m at 2.5 m/s")
    close(at(garage, "/garage/Structure/big_door_east", 1.0 + 0.52)[0], 1.3, "the east leaf half way")
    close(at(garage, "/garage/Structure/big_door_west", 7.0)[0], 0.0, "the leaves shut before the tanks fill")
    beacon = "/garage/Lights/big_door_beacon"
    assert lit(garage, beacon, 3.0) > 0.0 and lit(garage, beacon, 11.5) == 0.0, "the beacon dark only with air"
    hangar = Usd.Stage.Open(str(work / "hangar/hangar.usda"))
    close(at(hangar, "/hangar/Structure/roof_leaf_east", 1.0 + 11.2 / 3.0)[0], 11.2, "the roof leaf open at 3 m/s")
    print("ok  the garage's leaves and beacon, the hangar's roof leaves")


def check_the_launch_climbs(work):
    stage = Usd.Stage.Open(str(work / "launch/launch.usda"))
    rest = at(stage, "/launch/Fixtures/rocket", 0.0)
    close(at(stage, "/launch/Fixtures/rocket", 3.9)[1], rest[1], "standing through the engines' rumble")
    close(at(stage, "/launch/Fixtures/rocket", 6.0)[1] - rest[1], 0.5 * (24.0 - 9.81) * 2.0 ** 2,
          "two seconds into the climb at its push less Earth's pull")
    print("ok  the launch: 3 s of rumble from 1 s, then the climb")


def check_the_layer_order_and_the_edit(work):
    root = Sdf.Layer.FindOrOpen(str(work / "airlock/airlock.usda"))
    assert list(root.subLayerPaths) == ["./layers/edit.usda", "./layers/motion.usda", "./layers/base.usda"], \
        list(root.subLayerPaths)
    edit = Sdf.Layer.FindOrOpen(str(work / "airlock/layers/edit.usda"))
    editing = Usd.Stage.Open(edit)
    over = editing.OverridePrim("/airlock/Fixtures/outer_door")
    over.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(0.5, 0.0, 2.5))
    edit.Save()
    stage = Usd.Stage.Open(str(work / "airlock/airlock.usda"))
    assert at(stage, "/airlock/Fixtures/outer_door", 7.0) == Gf.Vec3d(0.5, 0.0, 2.5), "the creator's edit wins"
    print("ok  the motion layer between the edit layer and the base; an edit to a moving prim wins")


def check_bad_rounds_are_refused():
    try:
        motion.slide_keys({"by": [0, -2.8, 0], "speed": 3.0, "starts": "shut", "moves": [[1.0, "open"], [1.5, "shut"]]})
    except ValueError:
        pass
    else:
        raise AssertionError("a move before the last one ended was accepted")
    keys = motion.slide_keys({"by": [0, -2.8, 0], "speed": 3.0, "starts": "shut", "moves": [[1.0, "open"]]})
    try:
        motion.rounds(keys, {"name": "door", "length": 4.0, "loop": True}, 20.0)
    except ValueError:
        pass
    else:
        raise AssertionError("a looping round that ends open was accepted")
    switches = motion.light_switches({"name": "beacon", "length": 4.0, "loop": True, "light": {"on": [[0.0, 1.0],
                                                                                                    [3.0, 4.0]]}}, 8.0)
    assert switches == [(0.0, 1.0), (1.0, 0.0), (3.0, 1.0), (5.0, 0.0), (7.0, 1.0), (8.0, 0.0)], switches
    assert math.isclose(motion.climb_height({"lift": 3.0, "push": 24.0, "pull": 9.81}, 2.0), 0.0)
    print("ok  overlapping moves, an unjoined loop refused; a light's spans across rounds joined")


def main():
    with tempfile.TemporaryDirectory() as folder:
        work = pathlib.Path(folder)
        check_every_record_reaches_its_place(work)
        check_the_airlock_cycles_as_the_game_does(work)
        check_the_bay_doors(work)
        check_the_launch_climbs(work)
        check_the_layer_order_and_the_edit(work)
    check_bad_rounds_are_refused()


if __name__ == "__main__":
    main()
