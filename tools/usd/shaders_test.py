"""Check the framework's own shaders (tools/usd/shaders.py) without Blender: a shell surface with a library tile is
drawn with it, repeated along its metres; one the tiles lack keeps the library's flat surface.

Run: .venv/bin/python tools/usd/shaders_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

from pxr import Sdf, Usd, UsdGeom, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import builders  # noqa: E402
import scene  # noqa: E402
import shaders  # noqa: E402

PLACE = "wreck"


def stage_with_library():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, f"/{PLACE}")
    return stage


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
    with tempfile.TemporaryDirectory() as folder:
        check_the_tile_look(pathlib.Path(folder))
    print("shaders_test: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
