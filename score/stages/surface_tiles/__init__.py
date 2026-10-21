"""The surface-tiles stage: a place's shell (the walls, decks, roofs and stairs its scene record lays from its locked
plan, scene_record.writer `structure`) drawn with its library surfaces, not a flat colour (the materials audit,
2026-10-18: "the room shell is a flat colour with no texture"). Each surface the shell takes from the scene's own
surface library (surface-library@<place>, design_shell.PART_KINDS) is baked once, flat, as a repeating tile
(tools/props/library/inside/make_tiles.py, on a rented card through tools/props/cloud/library_bake.py), in the scene
palette's tokens, wear and dirt (finish-route-palette@<place>); the assembly writes the shell with it
(tools/usd/shaders.py tile_look), every TILE_METRES along the mesh's own uvs.

    make    the place's tile job, baked: <out>/<surface>_{base_color,metal_roughness,normal}.png and tiles.json
    gates   tiles  every surface the shell takes that has a recipe to bake came back with its three pictures

A surface seen through (glass) or giving light keeps the library's flat surface: a tile carries no opacity or glow. The
design alone says which parts the record lays (`shell_kinds`); the scene library says which surface each part takes.
"""
import json
import os
import pathlib
import subprocess

from score import checks, contracts, graph
from score.stages.earth_seed import design_shell
import score.stages.surfaces.palette_library as palette_library  # the module alone in the key, not the surface line
import score.stages.surfaces.surface_data as surface_data
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
LIBRARY_BAKE = REPO / "tools/props/cloud/library_bake.py"
DESIGN = PROPS_HOME / "design"  # the locked designs (score/review/plans.KEPT's folder)
# The tile's side and its normal map's texels a metre: a shell's far density, so the shell holds a wall's detail;
# colour and metal-roughness at half, as every bake (a 1024 normal map a tile).
TILE_METRES = 2.0
DENSITY = 512
SEED = 3
# Library families a tile cannot draw: see-through, glowing or printed surfaces keep the flat surface.
UNTILED_FAMILIES = ("glass", "light", "screen", "print")
ROLES = ("base_color", "metal_roughness", "normal")
# One card for a few flat bakes (a tile is 0.3 card minutes, library_bake.MINUTES_EACH): its set-up rounds it up.
EUROS = 1.0
# The rows whose outputs the tiles read: the scene's surface library and its palette.
LIBRARY_ROW = palette_library.ROW
PALETTE_ROW = "finish-route-palette"


def design_path(place):
    return DESIGN / "plans" / f"{place}.json"


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def shell_kinds(design):
    """The part kinds of the shell the scene record lays from the locked plan `design` (scene_record.writer
    `structure`), sorted: an enclosed place's deck, walls and roof where its base does not lay them
    (design_shell.laid_for), and `stair` for the plan's flights."""
    kinds = {design_shell.part_kind(name) for name, _, _ in design_shell.pieces(design)} \
        if design_shell.encloses(design) and not design_shell.laid_for(design) else set()
    if any(len(entry.get("points") or []) >= 3 for entry in design.get("stairs") or []):
        kinds.add("stair")
    return sorted(kinds)


def tiled(design, library, specs):
    """The surfaces a tile is baked for: each the scene library (`library`, its materials.json content) gives a part of
    the shell, which `specs` holds with a recipe a flat bake draws; sorted."""
    named = {surface for kind in shell_kinds(design)
             if (surface := palette_library.shell_surface(kind, library)) is not None}
    return sorted(surface for surface in named
                  if surface in specs and specs[surface].get("family") not in UNTILED_FAMILIES)


def scene_specs(palette):
    """Every scene library variant in its own token, dirtied in the scene's dirt token (palette_library.specs)."""
    return palette_library.specs(palette)


def wanted(inputs):
    """(the surfaces the place's tiles are baked for, the scene palette, its specs) from a row's inputs."""
    palette = palette_library.read(inputs)
    specs = scene_specs(palette)
    return tiled(read(inputs["design"]), palette_library.library_of(palette), specs), palette, specs


def applies(place):
    """Whether the place has the row: its locked plan lays a shell the scene record draws, and its finish line makes
    a surface library (surface_data.paints)."""
    path = design_path(place)
    return path.is_file() and bool(shell_kinds(read(path))) and surface_data.paints(place)


def files(place):
    """The place's locked plan, the library's method and the bake's code."""
    return {"design": "{home}/design/plans/{place}.json", "library": "{data}/library",
            "tile script": "{repo}/tools/props/library/inside/make_tiles.py",
            "bake": "{repo}/tools/props/library/inside/bake.py", "recipes": "{repo}/tools/props/library/recipes.py",
            "runtime": "{repo}/tools/props/library/inside/runtime.py",
            "scene setup": "{repo}/tools/props/library/inside/scene_setup.py",
            "library bake": "{repo}/tools/props/cloud/library_bake.py"}


def tile_job(inputs, out):
    """The place's make_tiles.py job: its shell's surfaces in the scene palette's tokens, wear and dirt."""
    surfaces, palette, specs = wanted(inputs)
    wear, dirt = palette_library.wear(palette)
    return {"script": "make_tiles.py", "out": str(out), "density": DENSITY, "metres": TILE_METRES, "wear": wear,
            "dirt": dirt, "seed": SEED, "specs": {surface: specs[surface] for surface in surfaces},
            "tiles": surfaces}


def make(inputs, out, seed, params):
    """The place's tiles baked on a rented card into `out`."""
    place = pathlib.Path(inputs["design"]).stem
    job = out / ".job-tiles.json"
    job.write_text(json.dumps(tile_job(inputs, out), indent=1))
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
    """Every surface the shell takes that a tile draws came back as a tile."""
    surfaces = wanted(inputs)[0]
    made = json.loads((output / "tiles.json").read_text())
    missing = [surface for surface in surfaces if surface not in made]
    answer = checks.FAIL if missing else checks.PASS
    reason = f"{len(surfaces) - len(missing)} of {len(surfaces)} shell surfaces tiled" + (
        f"; missing {', '.join(missing)}" if missing else "")
    return checks.Verdict("tiles", answer, reason, {"wanted": len(surfaces), "missing": len(missing)},
                          {"missing": "lower"}, tuple(missing))


STAGE = graph.Stage("surface-tiles", "place", make, TILES, (checks.Check("tiles", judge_tiles),), files=files,
                    after={LIBRARY_ROW: ("surface-library", 1), PALETTE_ROW: (PALETTE_ROW, 1)}, paid=True,
                    euros=EUROS, applies=applies)
