"""Check the framework's own shaders (tools/usd/shaders.py, earth.py) without Blender: the Earth's picture is mostly
ocean with land, desert, ice and cloud in the palette's own colours and the same every bake; a ball painted earth_face
is bound to the baked look with its picture in the stage; without a folder it keeps the library's flat surface; the
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
    first = earth.picture(256)
    assert first.shape == (128, 256, 3) and np.array_equal(first, earth.picture(256))
    ocean = np.array([int(earth.token_value("earth-ocean")[index:index + 2], 16) for index in (1, 3, 5)])
    land = np.array([int(earth.token_value("earth-land")[index:index + 2], 16) for index in (1, 3, 5)])
    near = lambda colour: np.mean(np.abs(first.astype(int) - colour).sum(axis=-1) < 12)  # noqa: E731
    cloud = np.array([int(earth.token_value("earth-cloud")[index:index + 2], 16) for index in (1, 3, 5)])
    shares = (near(ocean), near(land), near(cloud))
    assert shares[0] > 0.25 and shares[1] > 0.03 and shares[2] > 0.1, shares


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


def main():
    check_the_picture()
    with tempfile.TemporaryDirectory() as folder:
        check_the_earth_look(pathlib.Path(folder))
    check_the_sun_disc()
    check_the_missing_materials_are_library_surfaces()
    print("shaders_test: ok")


if __name__ == "__main__":
    main()
