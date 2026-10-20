"""The placeholder check: nothing visible on a place's OpenUSD stage stands in for a made piece.

    .venv/bin/python tools/usd/placeholders.py <stage.usda> [<stage.usda> ...] [--out <placeholders.json>]

The owner's rule (2026-10-07, held again after the demo of 2026-10-09: "I saw a ton of placeholder assets still"):
code may build only plain plates, pipes and trims; everything with detail is a made piece, the game's own model
placed, a code piece that passes the parts check, or a model from the prop pipeline. The stage is read as composed,
and every prim drawn (not a guide, not made invisible) is judged by four rules:

    plain     a mesh the scene record's code drew (score:builder, in any group) must say which plain thing it
              is: its record entry's `plain`, written as score:plain, or a record group's own kind when that is plain
              (the ground's and the water's), one of PLAIN_KINDS. One that does not stands for a thing with detail
              (a door leaf, a ship, a car, a rocket) and fails, whatever its builder: a box or a lathe, or a builder
              that puts a thing together from many (the hangar's ship_hull and ship_legs, which this rule passed by
              default until 2026-10-11 because it judged only a list of primitives). Only the shell builders
              (SHELL_BUILDERS: room walls, decks and roofs, stairs, a tube's arcs, a heightfield's ground, the stars,
              specks, the haze and a light's beam) draw the place's own shell and pass without saying; a new builder
              is judged until it is put on that list.
    sorter    a kit piece (/<place>/Objects) whose model the place's kit built in code (`route` code in
              data/kit/<place>.json) must be a kind the sorter sends to code (tools/props/library/sorter.py: one
              the pipeline-failure record, data/library/pipeline_failures.json, names; #19).
    material  a mesh with no material, or with a surface that has no colour of its own (a UsdPreviewSurface whose
              diffuseColor is neither set nor connected: the reader's default grey), fails.
    proxy     a prim drawn for the proxy purpose, or named as a proxy, a placeholder or a debug mesh, fails.

Not judged here: other places' stages shown from this one (/<place>/Places: each is checked as its own stage), the
characters (the cast check, tools/characters/), and nothing hidden. The game's own models placed as fixtures are the
game's, placed and never remade, so only the material and proxy rules reach them. Prints one line a fault and exits
1 when there is any.
"""
import argparse
import json
import pathlib
import sys

from pxr import Usd, UsdGeom, UsdShade

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/props/library"))
import sorter  # noqa: E402

KITS = REPO / "data/kit"
# The scene record's builders that draw the place's own shell and nothing else (scene.BUILDERS, and the sky's beams):
# every other builder, a primitive or one that puts a thing together, must say which plain thing it drew.
SHELL_BUILDERS = frozenset(("room_walls", "room_deck", "dome_roof", "walls", "wall_strip", "pyramid_roof", "stairs",
                            "tube_arc", "heightfield", "stars", "specks", "haze_volume", "beam"))
# What a primitive may be (the owner's sorter rule, 2026-10-07: plain plates, pipes and trims; and what is not a thing
# at all: a room's shell, the ground, a field's soil, water and the sky).
PLAIN_KINDS = frozenset(("plate", "pipe", "trim", "shell", "ground", "soil", "water", "sky"))
# Top-level groups of a stage not judged here, and why: other places are checked as their own stages, the cast by its
# own check.
NOT_JUDGED = ("Places", "Characters")
PROXY_WORDS = ("proxy", "placeholder", "debug")


def attribute(prim, name):
    """A score:* attribute's value on a prim, or None when it has none."""
    found = prim.GetAttribute(name)
    return found.Get() if found and found.HasValue() else None


def judged_prims(stage):
    """Every prim of the place drawn on the stage and judged here: under the default prim, not in a group left to its
    own check, drawn for render or by default, and not made invisible."""
    root = stage.GetDefaultPrim()
    left_out = {root.GetPath().AppendChild(name) for name in NOT_JUDGED}
    prims = iter(Usd.PrimRange(root, Usd.TraverseInstanceProxies()))
    for prim in prims:
        if prim.GetPath() in left_out:
            prims.PruneChildren()
            continue
        imageable = UsdGeom.Imageable(prim)
        if not imageable:
            continue
        if imageable.ComputePurpose() == UsdGeom.Tokens.guide:
            prims.PruneChildren()
            continue
        if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
            prims.PruneChildren()
            continue
        yield prim


def plain_fault(prim):
    """Why a mesh the scene record's code drew fails the plain rule, or None when it passes (or no builder drew it)."""
    builder = attribute(prim, "score:builder")
    if builder is None or builder in SHELL_BUILDERS:
        return None
    plain = attribute(prim, "score:plain") or plain_group_kind(prim)
    if plain is None:
        return (f"drawn by the record's {builder} builder without saying which plain thing it is "
                "(a made piece's stand-in)")
    if plain not in PLAIN_KINDS:
        return (f"a {builder} called '{plain}', which is not a plain plate, pipe, trim, shell, ground, soil, water "
                "or sky")
    return None


def plain_group_kind(prim):
    """The plain thing a record group's kind says its meshes are (the ground's `ground`, the water's `water`), or None
    when the kind is not plain (the structure's `structure`)."""
    kind = attribute(prim, "score:kind")
    return kind if kind in PLAIN_KINDS else None


def kit_routes(place, kits=KITS):
    """{model: route} of the place's kit (data/kit/<place>.json), empty when the place has no kit."""
    path = pathlib.Path(kits) / f"{place}.json"
    if not path.exists():
        return {}
    return {name: entry.get("route") for name, entry in json.loads(path.read_text()).get("models", {}).items()}


def sorter_fault(prim, routes):
    """Why a kit piece fails the sorter rule, or None when it passes."""
    model, kind = attribute(prim, "score:model"), attribute(prim, "score:kind")
    if model is None or kind is None or routes.get(model) != "code":
        return None
    if sorter.route(kind) == "code":
        return None
    return f"{kind} built in code, but the sorter sends it to the prop pipeline (no pipeline failure named for it)"


def default_grey(material):
    """Whether a material's surface has no colour of its own: a UsdPreviewSurface whose diffuseColor is neither set
    nor connected draws in the reader's default grey. A surface drawn wholly clear (opacity 0: the haze's shell, which
    a renderer fills as a volume) shows no colour at all and is not grey."""
    shader = material.ComputeSurfaceSource()[0]
    if not shader or shader.GetIdAttr().Get() != "UsdPreviewSurface":
        return False
    opacity = shader.GetInput("opacity")
    if opacity and opacity.GetAttr().HasAuthoredValue() and not opacity.HasConnectedSource() and opacity.Get() == 0:
        return False
    colour = shader.GetInput("diffuseColor")
    return not colour or not (colour.HasConnectedSource() or colour.GetAttr().HasAuthoredValue())


def bound_materials(prim):
    """The materials a mesh is drawn with: its own binding, else its subsets' (one None for a part left bare)."""
    material = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
    if material:
        return [material]
    subsets = UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(prim))
    return [UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()[0] or None for subset in subsets] or [None]


def material_fault(prim):
    """Why a drawn mesh fails the material rule, or None when it passes."""
    if not prim.IsA(UsdGeom.Gprim):
        return None
    materials = bound_materials(prim)
    if any(material is None for material in materials):
        return "a mesh drawn with no material"
    greys = [str(material.GetPath()) for material in materials if default_grey(material)]
    return f"a mesh in the default grey ({', '.join(greys)} has no colour)" if greys else None


def proxy_fault(prim):
    """Why a prim fails the proxy rule, or None when it passes."""
    if UsdGeom.Imageable(prim).ComputePurpose() == UsdGeom.Tokens.proxy:
        return "drawn for the proxy purpose"
    name = prim.GetName().lower()
    word = next((word for word in PROXY_WORDS if word in name), None)
    return f"named as a {word}" if word else None


def faults_of(prim, routes):
    """Every rule one prim fails, as (rule, why)."""
    found = [("proxy", proxy_fault(prim)), ("material", material_fault(prim)), ("plain", plain_fault(prim))]
    group = prim.GetPath().pathElementCount > 1 and prim.GetPath().GetPrefixes()[1].name
    if group == "Objects":
        found.append(("sorter", sorter_fault(prim, routes)))
    return [(rule, why) for rule, why in found if why]


def check(stage_path, kits=KITS):
    """Every fault on the stage: [{"prim", "rule", "why"}], empty when nothing stands in for a made piece."""
    stage = Usd.Stage.Open(str(stage_path))
    routes = kit_routes(stage.GetDefaultPrim().GetName(), kits)
    return [{"prim": str(prim.GetPath()), "rule": rule, "why": why}
            for prim in judged_prims(stage) for rule, why in faults_of(prim, routes)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stages", type=pathlib.Path, nargs="+")
    parser.add_argument("--out", type=pathlib.Path, help="write every stage's faults here as JSON")
    options = parser.parse_args()
    found = {str(path): check(path) for path in options.stages}
    for path, faults in found.items():
        for fault in faults:
            print(f"{path}: {fault['prim']}: {fault['rule']}: {fault['why']}")
        print(f"{path}: {'no placeholder' if not faults else f'{len(faults)} placeholders'}")
    if options.out:
        options.out.write_text(json.dumps(found, indent=1))
    sys.exit(1 if any(found.values()) else 0)


if __name__ == "__main__":
    main()
