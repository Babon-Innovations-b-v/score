"""Check the framework's own shaders (tools/usd/shaders.py, earth.py) without Blender: the Earth's picture is the real
planet (ocean, land and cloud, no flat palette) and the same every bake; a ball painted earth_face
is bound to the baked look with its picture in the stage; without a folder it keeps the library's flat surface; a
shell surface with a library tile is drawn with it, repeated along its metres; the
sun's disc hangs along the sky's sun as wide as the game draws it and not along a named light; and the game's
missing materials are library surfaces.

Run: .venv/bin/python tools/usd/shaders_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Sdf, Usd, UsdGeom, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import builders  # noqa: E402
import earth  # noqa: E402
import scene  # noqa: E402
import shaders  # noqa: E402

PLACE = "wreck"


def check_the_picture():
    first = earth.picture(512)
    assert first.shape == (256, 512, 3) and np.array_equal(first, earth.picture(512))
    red, green, blue = (first[..., index].astype(int) for index in range(3))
    cloud = np.minimum(np.minimum(red, green), blue) > 170
    sea = (blue >= red) & (blue >= green) & ~cloud
    land = (red > blue + 10) & ~cloud
    codes = (first.astype(np.int64) // 8) @ np.array([1024, 32, 1])
    flat = np.sort(np.bincount(codes.ravel()))[::-1][:8].sum() / codes.size
    # The ink_earth cartoon's eight commonest colours covered 0.88 of it (measured 2026-10-11); the planet's 0.41, most
    # of that its dark open ocean.
    assert 0.2 < cloud.mean() < 0.7 and sea.mean() > 0.2 and land.mean() > 0.05 and flat < 0.5, \
        (cloud.mean(), sea.mean(), land.mean(), flat)


def stage_with_library():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    for name in ("earth_face", "sun_disc"):
        UsdShade.Material.Define(stage, f"/{PLACE}/Library/{name}")
    return stage


def check_the_earth_look(folder):
    stage = stage_with_library()
    ball = scene.mesh_prim(stage, f"/{PLACE}/Structure/earth", builders.sphere([0.0, 0.0, 0.0], 220.0, "earth_face"))
    shaders.EARTH_WIDTH = 64
    scene.bind_surface(stage, ball, PLACE, "earth_face", folder)
    bound = UsdShade.MaterialBindingAPI(ball.GetPrim()).GetDirectBinding().GetMaterialPath()
    assert bound == Sdf.Path(f"/{PLACE}/Looks/earth_face"), bound
    assert (folder / "assets/textures" / shaders.EARTH_PICTURE).exists()
    assert ball.GetPrim().GetAttribute("score:surface").Get() == "earth_face"
    flat = scene.mesh_prim(stage, f"/{PLACE}/Structure/flat", builders.sphere([0.0, 0.0, 0.0], 1.0, "earth_face"))
    scene.bind_surface(stage, flat, PLACE, "earth_face")
    assert UsdShade.MaterialBindingAPI(flat.GetPrim()).GetDirectBinding().GetMaterialPath() == \
        Sdf.Path(f"/{PLACE}/Library/earth_face")


def check_the_sun_disc():
    stage = stage_with_library()
    lights = [{"type": "sun", "energy": 1.25, "toward": [0.6, -0.8, 0.0]},
              {"type": "sun", "name": "earthshine", "energy": 0.1, "toward": [0.0, -1.0, 0.0]}]
    count = shaders.sun_discs(stage, PLACE, lights, lambda path, centre, radius: scene.sun_ball(stage, PLACE, path,
                                                                                                 centre, radius))
    assert count == 1
    points = np.array(UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Sky/sun_disc_0")).GetPointsAttr().Get())
    middle = (points.min(axis=0) + points.max(axis=0)) / 2
    assert np.allclose(middle / np.linalg.norm(middle), [-0.6, 0.8, 0.0], atol=1e-3)
    across = math.degrees(2 * math.asin((points.max(axis=0) - points.min(axis=0)).max() / 2 / np.linalg.norm(middle)))
    assert abs(across - shaders.SUN_ACROSS_DEGREES) < 0.05, across


def check_the_missing_materials_are_library_surfaces():
    families = json.loads((REPO / "data/library/materials.json").read_text())["families"]
    variants = {name: about for family in families.values() for name, about in family["variants"].items()}
    for name in ("warning_lamp", "grow_light", "indicator_amber", "screen_teal", "sun_disc", "earth_face"):
        assert name in variants, name
    games = {about.get("game") for about in variants.values()}
    assert {"hull_trim", "roof"} <= games


def tiles_folder(folder, surface="deck", metres=2.0):
    """A surface-tiles output as make_tiles.py writes it: one surface's three pictures and tiles.json."""
    from PIL import Image
    tiles = folder / "tiles"
    tiles.mkdir()
    for role in shaders.TILE_ROLES:
        Image.new("RGB", (8, 8), (90, 90, 90)).save(tiles / f"{surface}_{role}.png")
    (tiles / "tiles.json").write_text(json.dumps({surface: {"metres": metres, "side": 8}}))
    return tiles


def check_the_tile_look(folder):
    """A shell mesh whose surface has a tile is bound to /<place>/Looks/<surface>, its pictures copied into the stage's
    textures and repeated every tile's side along the mesh's metre uvs; a surface the tiles lack keeps the library's."""
    stage = stage_with_library()
    for name in ("deck", "bare_steel"):
        UsdShade.Material.Define(stage, f"/{PLACE}/Library/{name}")
    tiles = tiles_folder(folder)
    deck = scene.mesh_prim(stage, f"/{PLACE}/Structure/deck", builders.box([0.0, 0.0, 0.0], [4.0, 0.1, 4.0], "deck"))
    scene.bind_surface(stage, deck, PLACE, "deck", folder, tiles)
    bound = UsdShade.MaterialBindingAPI(deck.GetPrim()).GetDirectBinding().GetMaterialPath()
    assert bound == Sdf.Path(f"/{PLACE}/Looks/deck"), bound
    assert deck.GetPrim().GetAttribute("score:surface").Get() == "deck"
    for role in shaders.TILE_ROLES:
        assert (folder / "assets/textures" / f"tile_{PLACE}_deck_{role}.png").exists(), role
    repeat = UsdShade.Shader(stage.GetPrimAtPath(f"/{PLACE}/Looks/deck/repeat"))
    assert tuple(repeat.GetInput("scale").Get()) == (0.5, 0.5)
    steel = scene.mesh_prim(stage, f"/{PLACE}/Structure/steel",
                            builders.box([0.0, 0.0, 0.0], [1.0, 1.0, 1.0], "bare_steel"))
    scene.bind_surface(stage, steel, PLACE, "bare_steel", folder, tiles)
    assert UsdShade.MaterialBindingAPI(steel.GetPrim()).GetDirectBinding().GetMaterialPath() == \
        Sdf.Path(f"/{PLACE}/Library/bare_steel")


def main():
    check_the_picture()
    with tempfile.TemporaryDirectory() as folder:
        check_the_earth_look(pathlib.Path(folder))
    with tempfile.TemporaryDirectory() as folder:
        check_the_tile_look(pathlib.Path(folder))
    check_the_sun_disc()
    check_the_missing_materials_are_library_surfaces()
    print("shaders_test: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
