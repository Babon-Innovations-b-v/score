"""The surface-tiles stage: a place's room shell (its scene record's code-built walls, decks and roofs) drawn with its
library surfaces, not a flat colour (the materials audit, 2026-10-18: "the room shell is a flat colour with no
texture"). Each library surface the shell names is baked once, flat, as a repeating tile (tools/props/library/inside/
make_tiles.py, on a rented card through tools/props/cloud/library_bake.py), in the place's own tokens, wear and dirt;
the assembly writes the shell with it (tools/usd/shaders.py tile_look), every TILE_METRES along the mesh's own uvs.

    make    the place's tile job, baked: <out>/<surface>_{base_color,metal_roughness,normal}.png and tiles.json
    gates   tiles  every surface the shell names that has a recipe to bake came back with its three pictures

A surface seen through (glass) or giving light keeps the library's flat surface: a tile carries no opacity or glow.
"""
import json
import os
import pathlib
import subprocess
import sys

from score import checks, contracts, graph
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
LIBRARY_BAKE = REPO / "tools/props/cloud/library_bake.py"
# The tile's side and its normal map's texels a metre: the room kit's density (route.FAR, place_route's code jobs), so
# the shell holds the kit's detail; colour and metal-roughness at half, as every bake (a 1024 normal map a tile).
TILE_METRES = 2.0
DENSITY = 512
SEED = 3
# Library families a tile cannot draw: see-through, glowing or printed surfaces keep the flat surface.
UNTILED_FAMILIES = ("glass", "light", "screen", "print")
ROLES = ("base_color", "metal_roughness", "normal")
# One card for a few flat bakes (a code-built piece is 0.3 card minutes, library_bake.MINUTES_EACH): its set-up rounds
# it up, as late_bake's.
EUROS = 1.0


def scene_path(place):
    return REPO / "data/scene" / f"{place}.json"


def library_place(place):
    """The place's library place in data/definitions/place.json: its surface data's `library`, else its kit's
    `place`, else its own name (as tools/usd/export.py's library_materials takes it)."""
    surfaces = REPO / "data/surfaces" / f"{place}.json"
    if surfaces.exists() and "library" in json.loads(surfaces.read_text()):
        return json.loads(surfaces.read_text())["library"]
    kit = REPO / "data/kit" / f"{place}.json"
    return json.loads(kit.read_text()).get("place", place) if kit.exists() else place


def shell_surfaces(place):
    """The library surfaces the place's seed scene record's shell (`structure`) names, sorted."""
    path = scene_path(place)
    if not path.exists():
        return []
    return sorted({entry.get("surface") for entry in json.loads(path.read_text()).get("structure", [])
                   if entry.get("surface")})


def tiled(place, specs):
    """The shell's surfaces a tile is baked for: those the library holds with a recipe a flat bake draws."""
    return [surface for surface in shell_surfaces(place)
            if surface in specs and specs[surface].get("family") not in UNTILED_FAMILIES]


def place_specs(place):
    """Every library variant as the place paints it (library.by_library on its library place)."""
    sys.path.insert(0, str(REPO / "tools/props/library"))
    import library
    return library.by_library(library_place(place))


def applies(place):
    return bool(tiled(place, place_specs(place))) if scene_path(place).exists() else False


def files(place):
    """The place's seed scene record, what names its library place (its surface data or kit, where it has them), the
    library and its tokens, and the bake's code."""
    named = {f"{name} data": "{data}/" + folder + "/" + place + ".json" for name, folder in (("surface", "surfaces"),
                                                                                              ("kit", "kit"))
             if (REPO / "data" / folder / f"{place}.json").exists()}
    return {"scene": "{data}/scene/" + place + ".json", **named, "library": "{data}/library",
            "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json",
            "tile script": "{repo}/tools/props/library/inside/make_tiles.py",
            "bake": "{repo}/tools/props/library/inside/bake.py", "recipes": "{repo}/tools/props/library/recipes.py",
            "runtime": "{repo}/tools/props/library/inside/runtime.py",
            "scene setup": "{repo}/tools/props/library/inside/scene_setup.py",
            "library bake": "{repo}/tools/props/cloud/library_bake.py"}


def tile_job(place, out):
    """The place's make_tiles.py job: its shell's surfaces in its own tokens, wear and dirt."""
    sys.path.insert(0, str(REPO / "tools/props/library"))
    import library
    specs = place_specs(place)
    wear, dirt = library.wear_of(library_place(place))
    surfaces = tiled(place, specs)
    return {"script": "make_tiles.py", "out": str(out), "density": DENSITY, "metres": TILE_METRES, "wear": wear,
            "dirt": dirt, "seed": SEED, "specs": {surface: specs[surface] for surface in surfaces},
            "tiles": surfaces}


def make(inputs, out, seed, params):
    """The place's tiles baked on a rented card into `out`."""
    place = pathlib.Path(inputs["scene"]).stem
    job = out / ".job-tiles.json"
    job.write_text(json.dumps(tile_job(place, out), indent=1))
    subprocess.run([str(PROPS_PYTHON), str(LIBRARY_BAKE), str(job), "--who", f"surface-tiles@{place} (seed {seed})"],
                   check=True, env=dict(os.environ), cwd=REPO)
    job.unlink()


def tile_faults(folder):
    """Why a folder is not a tiles output, or [] when it is."""
    if not (folder / "tiles.json").exists():
        return ["no tiles.json"]
    return [f"no {surface}_{role}.png" for surface in json.loads((folder / "tiles.json").read_text())
            for role in ROLES if not (folder / f"{surface}_{role}.png").exists()]


TILES = contracts.Contract("surface-tiles", 1, tile_faults, {"length": "metre"})


def judge_tiles(output, inputs, evidence):
    """Every surface the shell names that a tile draws came back as a tile."""
    place = pathlib.Path(inputs["scene"]).stem
    wanted = tiled(place, place_specs(place))
    made = json.loads((output / "tiles.json").read_text())
    missing = [surface for surface in wanted if surface not in made]
    answer = checks.FAIL if missing else checks.PASS
    reason = f"{len(wanted) - len(missing)} of {len(wanted)} shell surfaces tiled" + (
        f"; missing {', '.join(missing)}" if missing else "")
    return checks.Verdict("tiles", answer, reason, {"wanted": len(wanted), "missing": len(missing)},
                          {"missing": "lower"}, tuple(missing))


STAGE = graph.Stage("surface-tiles", "place", make, TILES, (checks.Check("tiles", judge_tiles),), files=files,
                    paid=True, euros=EUROS, applies=applies)
