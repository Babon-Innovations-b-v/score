"""Check what a place's scene record adds to its stage (tools/usd/scene.py), on records made here: the code builders'
shapes (a room's walls with a doorway cut, a deck with a pit's hole, a dome closing at its top, a turned rocket), a
structure piece painted with its library surface and carrying its roof layer, the game's lights in the stage's units
with the game's own numbers kept, a kit room's lamps hung where HubKit hangs them, a walkway tube laid bay by bay
along its length, a kit piece the game moves shifted by its node, the Moon drawn as the game's sky draws it, a kit
light's night glow kept to its picture's bright parts, and every real record in data/scene naming only builders,
surfaces and fields that exist.

Run: .venv/bin/python tools/usd/scene_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Usd, UsdGeom, UsdLux, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/props/library"))
import builders  # noqa: E402
import export  # noqa: E402
import library  # noqa: E402
import scene  # noqa: E402

PLACE = "hub"


def check_builders():
    walls = builders.room_walls(6.0, 6.0, 1.6, 2.8, "x", [{"side": "south", "wide": 2.2, "tall": 2.6}])
    middles = walls["points"][walls["triangles"]].mean(axis=1)
    in_doorway = (np.abs(middles[:, 0]) < 1.0) & (middles[:, 2] > 2.9) & (middles[:, 1] < 2.5)
    assert not in_doorway.any(), "the south doorway is not cut"
    assert np.isclose(walls["points"][:, 1].max(), 2.8)
    deck = builders.room_deck(6.0, 6.0, 1.6, -0.02, "x", holes=[(0.0, 0.0, 1.0)])
    deck_middles = deck["points"][deck["triangles"]].mean(axis=1)
    assert np.hypot(deck_middles[:, 0], deck_middles[:, 2]).min() > 1.0, "the pit's hole is not left out of the deck"
    roof = builders.dome_roof(6.0, 6.0, 1.6, 2.8, 1.0, 1.2, "x")
    assert np.isclose(roof["points"][:, 1].max(), 3.8) and np.isclose(roof["points"][:, 1].min(), 2.8)
    rocket = builders.lathe([[0.0, 3.0, 2.8, 1.5], [50.0, 60.0, 3.6, 0.0]], [-270.0, 0.0, -60.0], "x")
    assert np.isclose(rocket["points"][:, 1].max(), 60.0)
    assert np.isclose(np.hypot(rocket["points"][:, 0] + 270.0, rocket["points"][:, 2] + 60.0).max(), 3.6)
    facets = builders.walls(12, 4.5, 0.0, 3.1, "x", 15.0, [(0.0, 2.2, 2.6)])
    assert np.isclose(np.hypot(facets["points"][:, 0], facets["points"][:, 2]).min(), 4.5 / math.cos(math.pi / 12),
                      atol=1.2), "a facet's corners stand out on its corner radius"


def check_lights_and_structure(folder):
    """A record with one built wall, a roof on layer 2, an omni, a spot and a sun, written into a stage."""
    record = {
        "structure": [{"name": "walls", "builder": "room_walls", "wide": 4.0, "deep": 5.0, "corner": 0.6, "high": 2.8,
                       "surface": "roof_steel_paint", "doors": []},
                      {"name": "roof", "builder": "dome_roof", "wide": 4.0, "deep": 5.0, "corner": 0.6, "eave": 2.8,
                       "rise": 0.6, "run": 1.1, "surface": "roof_steel_paint", "layer": 2}],
        "water": [{"name": "harbour", "builder": "grid", "low": [-10, -10], "high": [10, 10], "height": 0.0,
                   "step": 5.0, "surface": "harbour_water"}],
        "lights": [{"type": "omni", "at": [0.0, 2.5, 0.0], "colour": "#ffd29a", "energy": 1.92, "range": 6.0,
                    "attenuation": 2.2, "shadows": True},
                   {"type": "spot", "at": [0.0, 2.0, 0.0], "aim": [0.0, 0.0, -5.0], "colour": "#ffffff", "energy": 3.0,
                    "range": 90.0, "angle": 42.0},
                   {"type": "sun", "toward": [0.0, -1.0, 0.0], "colour": "#fff5e6", "energy": 1.25}],
        "environment": {"background": "#030409", "ambient": {"colour": "#9fb8e6", "energy": 0.1}, "exposure": 0.85,
                        "inside": True},
    }
    path = folder / "base.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    export.library_materials(stage, PLACE, f"/{PLACE}")
    scene.write(stage, PLACE, record, folder)
    walls = stage.GetPrimAtPath(f"/{PLACE}/Structure/walls")
    bound = UsdShade.MaterialBindingAPI(walls).ComputeBoundMaterial()[0]
    assert bound.GetPath().name == "roof_steel_paint", bound.GetPath()
    assert stage.GetPrimAtPath(f"/{PLACE}/Structure/roof").GetAttribute("score:layer").Get() == "2"
    assert stage.GetPrimAtPath(f"/{PLACE}/Water/harbour").IsValid()
    omni = UsdLux.SphereLight(stage.GetPrimAtPath(f"/{PLACE}/Lights/light_1"))
    watts = omni.GetIntensityAttr().Get() * scene.SPHERE_WATTS_PER_INTENSITY
    assert math.isclose(watts, scene.OMNI_PER_ENERGY * 1.92 * 3.0 ** -0.2, rel_tol=1e-6), watts  # matched at 3 m
    assert omni.GetPrim().GetAttribute("score:game:energy").Get() == np.float32(1.92)
    assert math.isclose(omni.GetColorAttr().Get()[0], 1.0, rel_tol=1e-6)  # #ffd29a's red is full
    spot = stage.GetPrimAtPath(f"/{PLACE}/Lights/light_2")
    assert spot.HasAPI(UsdLux.ShapingAPI) and UsdLux.ShapingAPI(spot).GetShapingConeAngleAttr().Get() == 42.0
    assert UsdLux.ShapingAPI(spot).GetShapingConeSoftnessAttr().Get() == 1.0  # dimmed across its whole cone, as Godot
    shine = UsdGeom.Xformable(spot).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).TransformDir((0, 0, -1))
    expected = np.array([0.0, -2.0, -5.0]) / math.sqrt(29.0)
    assert np.allclose(np.asarray(shine) / np.linalg.norm(shine), expected, atol=1e-5), shine
    sun = UsdLux.DistantLight(stage.GetPrimAtPath(f"/{PLACE}/Lights/sun_1"))
    strength = sun.GetIntensityAttr().Get() * scene.DISTANT_STRENGTH_PER_INTENSITY
    assert math.isclose(strength, scene.SUN_PER_ENERGY * 1.25, rel_tol=1e-6)
    down = UsdGeom.Xformable(sun).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).TransformDir((0, 0, -1))
    assert np.allclose(np.asarray(down), [0.0, -1.0, 0.0], atol=1e-5), down
    sky = stage.GetPrimAtPath(f"/{PLACE}/Environment")
    assert sky.IsA(UsdLux.DomeLight) and math.isclose(sky.GetAttribute("score:exposure").Get(), 0.85, rel_tol=1e-6)


def check_kit_lamps():
    """A lamp kind hangs its light where HubKit does: at its kind's `high` and a little in front of the piece."""
    kit = {"kinds": {"hub_wall_cage_lamp": {"light": {"strength": 0.05, "reach": 3.5, "high": 0.5}}}}
    laid = {"kind": "hub_wall_cage_lamp", "at": [1.0, 2.0, 3.0], "x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1],
            "size": [0.2, 0.4, 0.1]}
    lights = scene.kit_lights(kit, [laid, dict(laid, part="glow")])
    assert len(lights) == 1, lights
    assert np.allclose(lights[0]["at"], [1.0, 2.2, 3.0 - 0.1]), lights[0]["at"]
    assert math.isclose(lights[0]["energy"], 0.6) and lights[0]["range"] == 3.5 and not lights[0]["shadows"]


def check_tube():
    """A walkway tube's bay piece goes on every bay stretched to fill the way, an `every` one on the middle bay of
    each run, an end piece at the start and turned round at the end (TubeKit)."""
    bay = export.tube_spots({"tube_part": "bay"}, 4.35, 1.3)
    assert [round(spot[2, 3], 3) for spot in bay] == [0.0, 1.45, 2.9]
    assert math.isclose(bay[0][2, 2], 4.35 / 3.9)
    assert len(export.tube_spots({"tube_part": "bay", "every": 3}, 4.35, 1.3)) == 1
    ends = export.tube_spots({"tube_part": "end"}, 4.35, 1.3)
    assert len(ends) == 2 and ends[1][0, 0] == -1.0 and ends[1][2, 3] == 4.35


def check_moved():
    """A piece the game moves (the flat's balcony door) is shifted by its node, its transform with it; others stay."""
    door = {"kind": "flat_sliding_glass_leaf", "node": "BalconyDoor", "at": [-2.94, 0.02, -3.5],
            "matrix": np.eye(4).tolist()}
    wall = {"kind": "flat_render_wall", "at": [0.0, 0.0, 0.0]}
    moved = scene.moved_pieces([door, wall], [{"node": "BalconyDoor", "by": [0.0, 0.0, 1.4]}])
    assert np.allclose(moved[0]["at"], [-2.94, 0.02, -2.1]) and np.isclose(moved[0]["matrix"][2][3], 1.4)
    assert moved[1] is wall and door["at"][2] == -3.5
    try:
        scene.moved_pieces([wall], [{"node": "BalconyDoor", "by": [0.0, 0.0, 1.4]}])
    except ValueError:
        return
    raise AssertionError("a move naming no piece of the kit went unnoticed")


def check_moon(folder):
    """The Moon's face covers its 4.4 degrees and no more, its halo falls off from its way, and both stand square to
    the way far out from the eye."""
    entry = {"way": [-0.90042, 0.39071, -0.1913], "eye": [-4.0, 9.0, -3.5], "across": 4.4, "colour": "#e6ebf2",
             "brightness": 1.2, "seas": 0.4, "halo": 0.35, "halo_fall": 0.09, "distance": 1800.0}
    face, half = scene.moon_face_picture(entry, pixels=200)
    assert face[100, 100, 3] == 255 and face[0, 0, 3] == 0 and face[100, 2, 3] == 0
    covered = (face[100, :, 3] > 127).sum() / 200 * 2 * math.tan(half)
    assert math.isclose(covered, 2 * math.tan(math.radians(2.2)), rel_tol=0.03), covered
    halo, _ = scene.moon_halo_picture(entry, pixels=101)
    assert math.isclose(halo[50, 50, 3] / 255, 0.35, abs_tol=0.01) and halo[50, 0, 3] < 2
    stage = Usd.Stage.CreateNew(str(folder / "moon.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    scene.write_moon(stage, PLACE, entry, folder)
    points = np.asarray(UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Sky/moon")).GetPointsAttr().Get())
    middle = points.mean(axis=0) - np.array(entry["eye"])
    assert math.isclose(np.linalg.norm(middle), 1800.0, rel_tol=1e-4)
    assert np.allclose(middle / 1800.0, np.array(entry["way"]) / np.linalg.norm(entry["way"]), atol=1e-4)


def check_night_glow(folder):
    """A kit light's glow map: its picture times the night's strength where it is bright, nothing where it is dark;
    only the kinds a kit marks glow, and only with the record's kit_glow."""
    from PIL import Image
    picture = np.zeros((2, 2, 3), dtype=np.uint8)
    picture[0, 0] = 255
    picture[1, 1] = 60
    Image.fromarray(picture).save(folder / "sign.png")
    export.night_glow_map(folder / "sign.png", {"strength": 0.9, "from": 0.5, "ramp": 0.15}, folder / "glow.png")
    glow = np.asarray(Image.open(folder / "glow.png"))
    assert glow[0, 0, 0] == round((1.055 * 0.9 ** (1 / 2.4) - 0.055) * 255) and glow[1, 1].max() == 0
    kit = {"kinds": {"street_shop_sign": {"night_glow": 0.5}, "street_kerb_stone": {}},
           "pieces": [{"kind": "street_shop_sign", "model": "shop_sign_1"}, {"kind": "street_kerb_stone",
                                                                             "model": "kerb_stone_1"}]}
    assert export.night_glows(kit, None) == {}
    assert export.night_glows(kit, {"strength": 0.9, "ramp": 0.15}) == {
        "shop_sign_1": {"strength": 0.9, "ramp": 0.15, "from": 0.5}}


def check_stretched_fixture(folder):
    """A gameplay object the game presses to other proportions (the street's car) is scaled by its stretch."""
    import trimesh
    world = folder / "world"
    world.mkdir()
    trimesh.creation.box(extents=(2.0, 2.0, 4.0)).export(world / "car.glb")
    (folder / "layers").mkdir(exist_ok=True)
    stage = Usd.Stage.CreateNew(str(folder / "layers/car.usda"))  # beside the assets, as a base layer stands
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    scene.write_objects(stage, PLACE, [{"name": "car", "model": "car.glb", "at": [10.0, 0.0, 4.0], "yaw": 180.0,
                                        "stretch": [0.72, 0.72, 1.0]}], folder, world)
    box = UsdGeom.Imageable(stage.GetPrimAtPath(f"/{PLACE}/Fixtures/car")).ComputeWorldBound(
        Usd.TimeCode.Default(), "default").ComputeAlignedRange()
    assert np.allclose(np.asarray(box.GetSize()), [1.44, 1.44, 4.0], atol=1e-4), box


def check_records():
    """Every record names builders that exist with their own arguments, library surfaces that exist, and views
    with an eye, an aim and a field of view."""
    surfaces = set(library.variants(library.theme_library()))
    for path in sorted(scene.SCENES.glob("*.json")):
        record = json.loads(path.read_text())
        for key in ("structure", "ground", "water"):
            for entry in record.get(key, []):
                assert entry["builder"] in scene.BUILDERS, (path.name, entry["builder"])
                assert entry["surface"] in surfaces, (path.name, entry["surface"])
                scene.built_meshes(entry)
        for entry in record.get("lights", []):
            assert entry["type"] in ("omni", "spot", "sun"), (path.name, entry)
        assert record.get("views"), path.name
        for view in record["views"]:
            assert len(view["eye"]) == 3 and len(view["aim"]) == 3 and view["fov"] > 0, (path.name, view)
        if record.get("inside"):
            assert "floor" in record, path.name


def main():
    check_builders()
    with tempfile.TemporaryDirectory() as folder:
        check_lights_and_structure(pathlib.Path(folder))
        check_moon(pathlib.Path(folder))
        check_night_glow(pathlib.Path(folder))
        check_stretched_fixture(pathlib.Path(folder))
    check_kit_lamps()
    check_tube()
    check_moved()
    check_records()
    print("scene_test: ok")


if __name__ == "__main__":
    main()
