"""Check what a place's scene record adds to its stage (tools/usd/scene.py), on records made here: the code builders'
shapes (a room's walls with a doorway cut, a deck with a pit's hole, a dome closing at its top, a turned rocket, a
flattened ring, the ship's hull with its windows lying flat on it), a structure piece painted with its library
surface and carrying its roof layer and the plain thing a primitive says it is, a piece built in its own frame and
placed, a place shown turned and stretched, the game's lights in the stage's units with the game's own numbers kept,
a kit room's lamps hung where HubKit hangs them, a walkway tube laid bay by bay along its length, a kit piece the
game moves shifted by its node, the Moon drawn as the game's sky draws it, a kit light's night glow kept to its
picture's bright parts, the engine's seeded random numbers, the planned rocks lying as the game lays them, the ground
shader's detail baked with a decal, the stars turned at the record's minute, a water's lit columns, the night's glow, a
column of light and a shown place's left-out piece, and every real record in data/scene naming only builders,
surfaces, plain kinds and fields that exist.

Run: .venv/bin/python tools/usd/scene_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image
from pxr import Sdf, Usd, UsdGeom, UsdLux, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/props/library"))
import builders  # noqa: E402
import export  # noqa: E402
import ground  # noqa: E402
import ground_detail  # noqa: E402
import library  # noqa: E402
import orbits  # noqa: E402
import placeholders  # noqa: E402
import rocks  # noqa: E402
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
    ship = builders.ship_hull([0.0, 0.5, 0.0], "hull", "nose", "band", "stripe", "seam", "steel", "glass")
    ship_points = np.vstack([part["points"] for part in ship])
    assert np.isclose(ship_points[:, 1].max(), 0.5 + 7.8) and np.isclose(ship_points[:, 1].min(), 0.5 + 0.8)
    assert {part["surface"] for part in ship} == {"hull", "nose", "band", "stripe", "seam", "steel", "glass"}
    window = next(part for part in ship if part["surface"] == "glass")["points"]
    reach = np.hypot(window[:, 0], window[:, 2])
    assert reach.min() > 1.6 - 1e-6 and reach.max() < 1.6 + 0.05, "a service window does not lie flat on the hull"
    legs, feet = builders.ship_legs([0.0, 0.5, 0.0], "steel", "trim")
    assert np.isclose(feet["points"][:, 1].min(), 0.0), "the ship's feet do not reach the ground it stands half a metre over"
    assert np.isclose(legs["points"][:, 1].max(), 0.5 + 0.9) and np.isclose(np.abs(legs["points"][:, 0]).max(), 1.99)
    facets = builders.walls(12, 4.5, 0.0, 3.1, "x", 15.0, [(0.0, 2.2, 2.6)])
    assert np.isclose(np.hypot(facets["points"][:, 0], facets["points"][:, 2]).min(), 4.5 / math.cos(math.pi / 12),
                      atol=1.2), "a facet's corners stand out on its corner radius"


def check_lights_and_structure(folder):
    """A record with one built wall, a roof on layer 2, a slab that is an inventory row's, an omni, a spot and a sun,
    written into a stage."""
    record = {
        "structure": [{"name": "walls", "builder": "room_walls", "wide": 4.0, "deep": 5.0, "corner": 0.6, "high": 2.8,
                       "surface": "roof_steel_paint", "doors": []},
                      {"name": "roof", "builder": "dome_roof", "wide": 4.0, "deep": 5.0, "corner": 0.6, "eave": 2.8,
                       "rise": 0.6, "run": 1.1, "surface": "roof_steel_paint", "layer": 2},
                      {"name": "slab", "builder": "box", "centre": [0.0, 0.05, 0.0], "size": [2.0, 0.1, 2.0],
                       "surface": "roof_steel_paint", "plain": "plate", "row": "ramp"}],
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
    assert stage.GetPrimAtPath(f"/{PLACE}/Structure/slab").GetAttribute("score:plain").Get() == "plate"
    assert stage.GetPrimAtPath(f"/{PLACE}/Structure/slab").GetAttribute("score:row").Get() == "ramp"
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


def check_sky_builders():
    """The star field is the game's (Godot's RandomNumberGenerator of seed 9, as this port of random_pcg.h draws it:
    its first draws pinned so a change to the port shows, not checked against a running Godot; 1800 stars as wide
    seen from the middle wherever they hang), and a haze shell closes round its body in each of the game's FogVolume
    shapes."""
    assert [round(float(value), 6) for value in builders.pcg32_floats(9, 3)] == [0.896333, 0.085484, 0.925146]
    near = builders.stars(1800, 9, 700.0, 700.0, 0.7, 0.4, 1.3, None)
    far = builders.stars(1800, 9, 700.0, 1900.0, 0.7, 0.4, 1.3, None)
    assert len(near["points"]) == 1800 * 6 and len(near["triangles"]) == 1800 * 8
    middles = far["points"].reshape(1800, 6, 3).mean(axis=1)
    assert np.allclose(np.linalg.norm(middles, axis=1), 1900.0)
    widths = np.ptp(far["points"].reshape(1800, 6, 3), axis=1).max(axis=1) / 1900.0
    assert np.allclose(widths, np.ptp(near["points"].reshape(1800, 6, 3), axis=1).max(axis=1) / 700.0)
    assert 2 * 0.7 * 0.4 / 700 - 1e-9 <= widths.min() and widths.max() <= 2 * 0.7 * 1.3 / 700 + 1e-9
    first = middles[0] / 1900.0
    way = np.array([0.896333 * 2 - 1, 0.085484 * 2 - 1, 0.925146 * 2 - 1])
    assert np.allclose(first, way / np.linalg.norm(way), atol=1e-5), first
    for shape in ("box", "cylinder", "ellipsoid"):
        shell = builders.haze_volume(shape, [1.0, 2.0, 3.0], [4.0, 2.0, 6.0], None)
        assert np.allclose(shell["points"].min(axis=0), [-1.0, 1.0, 0.0], atol=1e-6), shape
        assert np.allclose(shell["points"].max(axis=0), [3.0, 3.0, 6.0], atol=1e-6), shape


def check_sky(folder):
    """A record's stars, haze body, Earth haze ring and water mirror written onto its stage, with the game's numbers
    kept where a renderer reads them; a place shown from another leaves its sky to the one showing it."""
    ring = json.loads((scene.SCENES / "launch.json").read_text())["environment"]["haze"]
    record = {
        "water": [{"name": "harbour", "builder": "grid", "low": [-10, -10], "high": [10, 10], "height": 0.0,
                   "step": 5.0, "surface": "harbour_water",
                   "mirror": {"along": 0.65, "down": 0.2, "ripple_tip": 0.03, "ripple_size": 0.2}}],
        "environment": {"background": "#030409", "ambient": {"colour": "#9fb8e6", "energy": 0.1}, "exposure": 0.85,
                        "stars": {"count": 10, "seed": 9, "sky_distance": 700.0, "distance": 1900.0, "radius": 0.7,
                                  "size": [0.4, 1.3], "colour": "#eef2ff"},
                        "haze": {"shape": "box", "centre": [0.0, 1.4, 0.0], "size": [6.0, 2.8, 6.0],
                                 "colour": "#ece8e0", "density": 0.025, "forward": 0.3, "reach": 24.0}}}
    stage = Usd.Stage.CreateNew(str(folder / "sky.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    export.library_materials(stage, PLACE, f"/{PLACE}")
    scene.write(stage, PLACE, record, folder)
    haze = stage.GetPrimAtPath(f"/{PLACE}/Sky/Haze")
    assert haze.GetAttribute("score:kind").Get() == "haze"
    assert math.isclose(haze.GetAttribute("score:haze_density").Get(), 0.025, rel_tol=1e-6)
    assert math.isclose(haze.GetAttribute("score:haze_forward").Get(), 0.3, rel_tol=1e-6)
    assert np.allclose(haze.GetAttribute("score:haze_colour").Get(), scene.colour("#ece8e0"), atol=1e-6)
    stars = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Sky/Stars"))
    assert len(stars.GetPointsAttr().Get()) == 60
    water = stage.GetPrimAtPath(f"/{PLACE}/Water/harbour")
    assert math.isclose(water.GetAttribute("score:mirror_along").Get(), 0.65, rel_tol=1e-6)
    assert math.isclose(water.GetAttribute("score:mirror_ripple_size").Get(), 0.2, rel_tol=1e-6)
    record["environment"]["haze"] = ring
    stage = Usd.Stage.CreateNew(str(folder / "ring.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    export.library_materials(stage, PLACE, f"/{PLACE}")
    scene.write(stage, PLACE, record, folder)
    ring_prim = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Sky/HazeRing"))
    points = np.asarray(ring_prim.GetPointsAttr().Get())
    assert np.allclose(np.hypot(points[:, 0], points[:, 2]), 297.0, atol=1e-3)
    assert np.isclose(points[:, 1].min(), 0.0) and np.isclose(points[:, 1].max(), 150.0)
    from PIL import Image
    alpha = np.asarray(Image.open(folder / "assets/textures/haze_ring.png"))[::-1, :, 3] / 255.0
    over_pictures = alpha[:, int(180 / 360 * alpha.shape[1])]  # bearing 180 (south, +z): angle 90, on the pictures
    in_gap = alpha[:, int(90 / 360 * alpha.shape[1])]  # bearing 90 (+x): angle 0, inside the gap
    def at(height):
        return int(height / 150.0 * alpha.shape[0])

    assert abs(over_pictures[at(10)] - 0.15) < 0.02 and abs(over_pictures[at(84)] - 0.35) < 0.02, over_pictures
    assert over_pictures[at(149)] < 0.02 and in_gap[at(1)] > 0.9
    shown = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(shown, "/flat")
    scene.write_places(shown, "flat", [{"name": "hub", "stage": "hub", "at": [0, 0, 0]}])
    assert not shown.GetPrimAtPath("/flat/Places/hub/Sky").IsActive()


def check_light_pieces(folder):
    """The stars turned as the game turns them at the record's minute, a water's lit columns, the sky's glow and a
    column of light written where a renderer reads them, and a shown place's piece the game does not draw here left
    out."""
    stars = {"count": 10, "seed": 9, "sky_distance": 700.0, "distance": 1900.0, "radius": 0.7, "size": [0.4, 1.3],
             "colour": "#eef2ff", "turn": {"minute": 60.0, "axes": "site"}}
    lit = {"name": "rocket", "at": [-270.0, -60.0], "low": 0.0, "high": 60.0, "half_width": 9.48, "colour": "#f3f1ea",
           "strength": 1.6}
    record = {
        "water": [{"name": "harbour", "builder": "grid", "low": [-10, -10], "high": [10, 10], "height": 0.0,
                   "step": 5.0, "surface": "harbour_water",
                   "mirror": {"along": 0.65, "down": 0.2, "ripple_tip": 0.03, "ripple_size": 0.2, "lit": [lit],
                              "column_smear": 0.35, "column_soft": 0.6}}],
        "environment": {"background": "#030409", "ambient": {"colour": "#9fb8e6", "energy": 0.1}, "exposure": 0.85,
                        "stars": stars,
                        "glow": {"threshold": 0.85, "intensity": 0.8, "hdr_scale": 2.0, "levels": [3, 5]},
                        "beams": [{"name": "beam", "foot": [1.0, 0.0, 2.0], "way": [0.0, 1.0, 0.1], "low": 12.0,
                                   "high": 100.0, "radius": 0.8, "sides": 8, "least_half_angle": 0.0035,
                                   "colour": "#74b9ea", "glow": 0.6}]}}
    stage = Usd.Stage.CreateNew(str(folder / "light.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    export.library_materials(stage, PLACE, f"/{PLACE}")
    scene.write(stage, PLACE, record, folder)
    points = np.asarray(UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Sky/Stars")).GetPointsAttr().Get())
    unturned = builders.stars(10, 9, 700.0, 1900.0, 0.7, 0.4, 1.3, None)["points"]
    assert np.allclose(points, unturned @ orbits.stars_turn(60.0, np.eye(3)).T, atol=1e-2)
    assert not np.allclose(points, unturned, atol=1.0)
    water = stage.GetPrimAtPath(f"/{PLACE}/Water/harbour")
    assert np.allclose(water.GetAttribute("score:mirror_lit_columns").Get()[0], [-270.0, -60.0, 0.0, 60.0])
    assert np.allclose(water.GetAttribute("score:mirror_lit_lights").Get()[0],
                       [channel * 1.6 for channel in scene.colour("#f3f1ea")], atol=1e-6)
    sky = stage.GetPrimAtPath(f"/{PLACE}/Environment")
    assert math.isclose(sky.GetAttribute("score:glow_threshold").Get(), 0.85, rel_tol=1e-6)
    assert list(sky.GetAttribute("score:glow_levels").Get()) == [3, 5]
    beam = stage.GetPrimAtPath(f"/{PLACE}/Sky/beam")
    beam_points = np.asarray(UsdGeom.Mesh(beam).GetPointsAttr().Get())
    way = np.array([0.0, 1.0, 0.1]) / np.linalg.norm([0.0, 1.0, 0.1])
    along = (beam_points - [1.0, 0.0, 2.0]) @ way
    aside = np.linalg.norm(beam_points - [1.0, 0.0, 2.0] - np.outer(along, way), axis=1)
    assert np.isclose(along.min(), 12.0, atol=1e-3) and np.isclose(along.max(), 100.0, atol=1e-3)
    assert np.allclose(aside, 0.8, atol=1e-3) and beam.GetAttribute("score:kind").Get() == "beam"
    assert placeholders.plain_fault(beam) is None
    shown = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(shown, "/camp")
    scene.write_places(shown, "camp", [{"name": "lock", "stage": "airlock", "at": [0, 0, 0],
                                        "leave_out": [{"prim": "Structure/outer_ramp", "why": "made in the test"}]}])
    assert not shown.GetPrimAtPath("/camp/Places/lock/Structure/outer_ramp").IsActive()


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


def check_ring_and_placing(folder):
    """A flattened ring keeps its hole and outside and its squashed height; a piece built in its own frame is turned and
    moved by its placing; a place is shown turned by its whole rotation and stretched along its run."""
    ring = builders.torus(13.6, 14.2, 0.2, "x", flatten=0.2)
    across = np.hypot(ring["points"][:, 0], ring["points"][:, 2])
    assert np.isclose(across.min(), 13.6) and np.isclose(across.max(), 14.2)
    assert np.isclose(ring["points"][:, 1].max(), 0.2 + 0.3 * 0.2)
    half_turn = [0.0, math.sin(math.pi / 4), 0.0, math.cos(math.pi / 4)]  # 90 degrees about up
    entry = {"name": "pad", "builder": "box", "centre": [1.0, 0.0, 0.0], "size": [0.2, 0.2, 0.2], "surface": "deck",
             "placed_at": [10.0, 2.0, 0.0], "placed_turn": half_turn}
    middle = scene.built_meshes(entry)[0]["points"].mean(axis=0)
    assert np.allclose(middle, [10.0, 2.0, -1.0], atol=1e-6), middle  # +x turned 90 degrees about up is -z
    stage = Usd.Stage.CreateNew(str(folder / "placed.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    scene.write_places(stage, PLACE, [{"name": "tube", "stage": "tube", "at": [1.0, 0.0, 0.0], "rotation": half_turn,
                                       "scale": [1.0, 1.0, 0.5]}])
    matrix = UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Places/tube")).ComputeLocalToWorldTransform(
        Usd.TimeCode.Default())
    assert np.allclose(np.asarray(matrix.Transform((0.0, 0.0, 2.0))), [2.0, 0.0, 0.0], atol=1e-6)
    check_shown_in_itself(folder)


def check_shown_in_itself(folder):
    """A place shown in itself (the tube's twin past the hub) is its own base layer referenced: it composes with no
    cycle, where the place's frame puts it, and the copy's own Places stay off."""
    (folder / "self/layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "self/layers/base.usda"))
    UsdGeom.Xform.Define(base, "/tube")
    UsdGeom.Cube.Define(base, "/tube/Structure/hull")
    scene.write_places(base, "tube", [{"name": "twin", "stage": "tube", "at": [0.0, 0.0, 5.0]}])
    base.GetRootLayer().Save()
    root = Sdf.Layer.CreateNew(str(folder / "self/tube.usda"))
    root.subLayerPaths.append("./layers/base.usda")
    root.Save()
    stage = Usd.Stage.Open(str(folder / "self/tube.usda"))
    twin = stage.GetPrimAtPath("/tube/Places/twin/Structure/hull")
    assert twin.IsValid(), "the place's twin is not composed"
    matrix = UsdGeom.Xformable(twin).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    assert np.allclose(np.asarray(matrix.ExtractTranslation()), [0.0, 0.0, 5.0])
    assert not stage.GetPrimAtPath("/tube/Places/twin/Places").IsActive()


def flat_ground(folder, skin=(128, 128, 128)):
    """A ground record for a flat plan, its seat straight out from the plan's middle."""
    size = 65
    code = np.full((size, size), round(20.0 / 40.0 * 65535), dtype=np.int64)
    pixels = np.stack([code >> 8, code & 255, np.zeros_like(code)], axis=-1).astype(np.uint8)
    Image.fromarray(pixels).save(folder / "heights.png")
    Image.new("RGB", (64, 64), skin).save(folder / "skin.jpg")
    record = {"heights": "heights.png", "skin": "skin.jpg", "side": 260.0, "low": 20.0, "span": 40.0,
              "radius": 220.0, "plan_out": [0.0, 1.0, 0.0], "folder": str(folder)}
    return ground.Ground(record, {"out": [0.0, 1.0, 0.0], "heading": 0.0}, [0.0, 0.0])


def check_planned_rocks(folder):
    """On flat ground a planned rock lies sunk by its share of its size, as long as its size, the same way every time;
    a pebble past where pebbles are seen and a rock off the plan's square are left out; laid Mars's way (no sinking
    for its tip) it stands higher by the tip's lift alone."""
    flat = flat_ground(folder)
    (folder / "game").mkdir()
    trimesh.creation.box(extents=(1.0, 0.5, 0.8)).export(folder / "game/rock.glb")
    layout = {"rocks": [{"x": 2.0, "z": 3.0, "size": 1.2, "kind": 0}, {"x": 60.0, "z": 0.0, "size": 0.2, "kind": 0},
                        {"x": 120.0, "z": 0.0, "size": 2.0, "kind": 0}]}
    (folder / "game/plan.json").write_text(json.dumps(layout))
    entry = {"plan": "game/plan.json", "boulders": ["game/rock.glb"], "stones": ["game/rock.glb"], "seed": 41,
             "sunk": 0.12, "tip": 0.25, "crest_reach": 1.0, "pebble": 0.45, "pebbles_seen": 40.0, "plan_reach": 116.0,
             "reach": 130.0}
    laid = rocks.laid_rocks(entry, folder, flat)
    assert len(laid) == 1, laid
    rock = laid[0]
    assert np.allclose(rock["at"][[0, 2]], [2.0, 3.0], atol=0.5), rock["at"]
    assert np.isclose(rock["stretch"].max() / rock["stretch"].min() < 1.6, True)
    assert 1.2 * 0.85 - 1e-6 <= rock["stretch"][0] <= 1.2 * 1.15 + 1e-6
    assert np.allclose(rock["turn"] @ rock["turn"].T, np.eye(3), atol=1e-9)
    assert np.allclose(rocks.laid_rocks(entry, folder, flat)[0]["turn"], rock["turn"])
    # Mars's way: sunk by its share of its height alone, so it stands higher by the tip's half size, and turned alike.
    mars = {key: value for key, value in entry.items() if key != "crest_reach"}
    mars["tip_sinks"] = False
    on_mars = rocks.laid_rocks(mars, folder, flat)[0]
    tip = rocks.Draws(41, 5)
    tip.randf_range(0.0, 1.0)
    lifted = 0.5 * 1.2 * abs(np.sin(tip.randf_range(-0.25, 0.25)))
    assert np.allclose(on_mars["turn"], rock["turn"])
    assert np.isclose(np.linalg.norm(on_mars["at"] - rock["at"]), lifted, atol=1e-3), (on_mars["at"], rock["at"], lifted)


def check_ground_detail(folder):
    """The baked ground is the rock colour shaded by the skin, darker where a decal lies, and faces mostly up."""
    flat = flat_ground(folder, skin=(107, 107, 107))  # the skin's red at its middle grey (0.42): no shade from it
    for name in ("shade", "bumps"):
        Image.new("RGB", (32, 32), (128, 128, 255) if name == "bumps" else (128, 128, 128)).save(folder / f"{name}.png")
    Image.new("RGB", (32, 32), (128, 128, 128)).save(folder / "relief.png")
    detail = {"flat_colour": [0.5, 0.5, 0.5], "ink_colour": [0.0, 0.0, 0.0], "relief": "relief.png",
              "scans": {"wide_shade": "shade.png", "close_shade": "shade.png", "wide_bumps": "bumps.png",
                        "close_bumps": "bumps.png"}}
    decal = {"centre": [2.0, 0.0, 0.0], "radius": 1.0, "solid": 0.35, "rays": 13, "ray_reach": 0.55, "seed": 23,
             "colour": [0.1, 0.1, 0.1]}
    baked = ground_detail.bake(flat, detail, [decal], folder, np.array([-3.0, -1.0]), np.array([3.0, 1.0]),
                               folder / "out", texel=0.02)
    colour = np.asarray(Image.open(baked["colour"]), dtype=np.float64)
    facing = np.asarray(Image.open(baked["facing"]), dtype=np.float64) / 255.0 * 2.0 - 1.0
    assert colour.shape == (100, 300, 3)
    burnt = colour[45:55, 245:255].mean()
    assert burnt < 40 and np.median(colour[:, :100]) > 100, (burnt, np.median(colour[:, :100]))
    assert np.median(facing[..., 2]) > 0.9


def check_dust(folder):
    """The wind's grains hang over their square round the place, none under the ground or over their height, the same
    every time; each is a speck of six points and eight triangles."""
    flat = flat_ground(folder)
    entry = {"count": 500, "side": 70.0, "high": 0.4, "seed": 116}
    points = scene.dust_points(entry, flat)
    assert points.shape == (500, 3)
    assert np.abs(points[:, [0, 2]]).max() <= 35.1, np.abs(points[:, [0, 2]]).max()
    lift = np.linalg.norm((points + [0.0, flat.drop, 0.0]) @ flat.frame + flat.origin, axis=1) - flat.radius
    assert lift.min() >= -1e-6 and lift.max() <= 0.4 + 1e-6, (lift.min(), lift.max())
    assert np.allclose(scene.dust_points(entry, flat), points)
    built = builders.specks(points[:3], 0.03, None)
    assert built["points"].shape == (18, 3) and built["triangles"].shape == (24, 3)
    assert np.isclose(np.ptp(built["points"][:6, 0]), 0.03)


def check_shared_paint(folder):
    """A game model whose surfaces are named after the game's shared materials is drawn in them (a hull surface in
    hull's flat colour), its children too; a surface named nothing shared keeps its own look."""
    import trimesh
    world = folder / "world"
    (world / "models").mkdir(parents=True)
    hull = trimesh.creation.box((0.2, 0.2, 0.2))
    hull.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(name="hull"))
    own = trimesh.creation.box((0.1, 0.1, 0.1))
    own.apply_translation((0.0, 0.3, 0.0))
    own.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="decal", baseColorFactor=[255, 0, 0, 255]))
    trimesh.Scene({"hull": hull, "own": own}).export(world / "models/robot.glb")
    record = {"objects": [{"name": "robot", "model": "models/robot.glb", "at": [0.0, 0.0, 0.0], "shared_paint": True,
                           "children": [{"model": "models/robot.glb", "at": [1.0, 0.0, 0.0]}]}]}
    (folder / "layers").mkdir()
    stage = Usd.Stage.CreateNew(str(folder / "layers/paint.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    scene.write(stage, PLACE, record, folder, world=world)
    hull_colour = json.loads(scene.SHARED_PAINT.read_text())["paints"]["hull"]["colour"]
    looks = {}
    for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{PLACE}/Fixtures/robot")):
        if prim.IsA(UsdGeom.Mesh):
            bound = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
            colour = UsdShade.Shader(stage.GetPrimAtPath(f"{bound.GetPath()}/surface")).GetInput("diffuseColor").Get()
            looks.setdefault(round(float(colour[0]), 3), []).append(str(prim.GetPath()))
    painted = round(hull_colour[0] ** 2.2, 3)
    assert len(looks.get(painted, [])) == 2 and len(looks.get(1.0, [])) == 2, looks


def check_labels_and_glow(folder):
    """A gameplay object worn in the glow the game paints over it, and a label on it (a Label3D's words drawn in the
    world's font, as large as its pixel size makes them), written into a stage."""
    world = folder / "world"
    (world / "models").mkdir(parents=True)
    import trimesh
    trimesh.creation.box((0.06, 0.06, 0.06)).export(world / "models/lamp.glb")
    font = HERE.parents[1] / "data/fonts/barlow_condensed/BarlowCondensed-Bold.ttf"
    record = {"objects": [{"name": "desk_lamp", "model": "models/lamp.glb", "at": [1.0, 0.8, 0.0],
                           "glow": {"colour": "#ff3a22", "strength": 4.0},
                           "children": [{"label": ["Lab desk", "Nothing yet"], "font": str(font), "font_size": 48,
                                         "pixel_size": 0.003, "outline_size": 10, "colour": "#a79c8b",
                                         "at": [0.0, 1.6, 0.0], "yaw": 180.0}]}]}
    (folder / "layers").mkdir()
    stage = Usd.Stage.CreateNew(str(folder / "layers/labels.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    scene.write(stage, PLACE, record, folder, world=world)
    lamp = stage.GetPrimAtPath(f"/{PLACE}/Fixtures/desk_lamp")
    mesh = next(prim for prim in Usd.PrimRange(lamp) if prim.IsA(UsdGeom.Mesh) and "label" not in str(prim.GetPath()))
    bound = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial()[0]
    assert bound.GetPath().name == "desk_lamp_glow", bound.GetPath()
    glow = UsdShade.Shader(stage.GetPrimAtPath(f"{bound.GetPath()}/surface")).GetInput("emissiveColor").Get()
    assert math.isclose(glow[0], 4.0, rel_tol=1e-6), glow
    label = stage.GetPrimAtPath(f"/{PLACE}/Fixtures/desk_lamp/label_1")
    assert label.GetAttribute("score:label").Get() == "Lab desk\nNothing yet"
    text = stage.GetPrimAtPath(f"{label.GetPath()}/text")
    assert UsdShade.MaterialBindingAPI(text).ComputeBoundMaterial()[0].GetPath().name == "look"
    points = np.asarray(UsdGeom.Mesh(text).GetPointsAttr().Get())
    tall = points[:, 1].max() - points[:, 1].min()
    assert 0.2 < tall < 0.5, tall  # two lines of a 48 pixel font at 3 mm a pixel


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
                assert entry.get("plain", "plate") in placeholders.PLAIN_KINDS, (path.name, entry["name"])
                scene.built_meshes(entry)
        assert "backdrop" not in record, path.name  # no picture of a place on a ring: the far city is built in 3D
        for entry in record.get("lights", []):
            assert entry["type"] in ("omni", "spot", "sun"), (path.name, entry)
        assert record.get("views"), path.name
        for view in record["views"]:
            assert len(view["eye"]) == 3 and len(view["aim"]) == 3 and view["fov"] > 0, (path.name, view)
        if record.get("inside"):
            assert "floor" in record, path.name
        environment = record.get("environment", {})
        haze = environment.get("haze")
        if haze:
            assert haze["shape"] in ("box", "cylinder", "ellipsoid", "ring") and haze.get("from"), path.name
            assert haze["centre"] != "ball" or record.get("planned_ground"), path.name
            if haze["shape"] != "ring":
                builders.haze_volume(haze["shape"], [0.0, 0.0, 0.0], haze["size"], None)
        if environment.get("stars"):
            assert environment["stars"].get("from") and environment["stars"]["distance"] < 2000.0, path.name
            turn = environment["stars"].get("turn")
            assert turn is None or (turn["axes"] in ("site", "seat") and turn.get("from")), path.name
            assert turn is None or turn["axes"] != "seat" or record.get("planned_ground"), path.name
        for beam in environment.get("beams", []):
            assert beam.get("from") and beam["high"] > beam["low"] and beam["radius"] > 0.0, (path.name, beam)
        assert not environment.get("glow") or environment["glow"].get("from"), path.name
        for entry in record.get("water", []):
            for lit in entry.get("mirror", {}).get("lit", []):
                assert lit.get("from") and lit["high"] > lit["low"] and lit["half_width"] > 0.0, (path.name, lit)
        for entry in record.get("places", []):
            for left in entry.get("leave_out", []):
                assert left["prim"] and left.get("why"), (path.name, entry["name"])


def check_rejected():
    """A record that holds again a thing its owner_rejected names is refused, and so are a kit piece's row and an
    effect of that name; an owner_rejected entry in words alone names nothing."""
    rejected = {"place": "here", "owner_rejected": ["the market, in words", {"what": "the pad", "names": ["pad"],
                                                                              "date": "2026-10-04", "why": "owner"}]}
    assert scene.rejected_names(rejected) == {"pad"}
    scene.refuse_rejected(rejected, ["deck", "the market, in words"], "the kit")
    try:
        scene.refuse_rejected(rejected, ["deck", "pad"], "the kit")
    except ValueError as error:
        assert "['pad']" in str(error) and "the kit" in str(error), error
    else:
        raise AssertionError("a rejected name came back unrefused")
    for path in sorted(scene.SCENES.glob("*.json")):
        scene.record(path.stem)  # every real record keeps out what its owner rejected


def main():
    check_builders()
    check_sky_builders()
    with tempfile.TemporaryDirectory() as folder:
        check_lights_and_structure(pathlib.Path(folder))
        check_moon(pathlib.Path(folder))
        check_night_glow(pathlib.Path(folder))
        check_stretched_fixture(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_sky(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_light_pieces(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_labels_and_glow(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_shared_paint(pathlib.Path(folder))
    check_kit_lamps()
    check_tube()
    check_moved()
    with tempfile.TemporaryDirectory() as folder:
        check_ring_and_placing(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_planned_rocks(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_ground_detail(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_dust(pathlib.Path(folder))
    check_records()
    check_rejected()
    print("scene_test: ok")


if __name__ == "__main__":
    main()
