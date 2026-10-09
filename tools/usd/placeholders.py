"""The placeholder check: nothing visible on a place's OpenUSD stage stands in for a made piece.

    .venv/bin/python tools/usd/placeholders.py <stage.usda> [<stage.usda> ...] [--out <placeholders.json>]

The owner's rule (2026-10-07, held again after the demo of 2026-10-09: "I saw a ton of placeholder assets still"):
code may build only plain plates, pipes and trims; everything with detail is a made piece, the game's own model
placed, a code piece that passes the parts check, or a model from the prop pipeline. The stage is read as composed,
and every prim drawn (not a guide, not made invisible) is judged by four rules:

    plain     a structure mesh (/<place>/Structure) built by a primitive builder (PRIMITIVES: a box, a quad, a
              disc, a round wall, a lathe, a sphere or a torus) must say which plain thing it is: its record entry's
              `plain`, written as score:plain, one of PLAIN_KINDS. One that does not stands for a thing with detail
              (a door leaf, a ship, a car, a rocket) and fails. The shell builders (room walls, decks and roofs,
              stairs, a tube's arcs, the ground, the stars and the haze) draw the place's own shell and pass.
    sorter    a kit piece (/<place>/Objects) whose model the place's kit built in code (`route` code in
              data/kit/<place>.json) must be a kind the sorter sends to code (tools/props/library/sorter.py: a
              plain plate, pipe or trim, or a fitting whose code build shows every part of its close-up).
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
# The scene record's builders that draw one plain primitive: each such entry must say which plain thing it is.
PRIMITIVES = frozenset(("box", "quad", "disc", "cylinder_wall", "lathe", "sphere", "torus"))
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
    """Why a structure mesh fails the plain rule, or None when it passes."""
    builder = attribute(prim, "score:builder")
    if builder not in PRIMITIVES:
        return None
    plain = attribute(prim, "score:plain")
    if plain is None:
        return f"a {builder} that does not say which plain thing it is (a made piece's stand-in)"
    if plain not in PLAIN_KINDS:
        return f"a {builder} called '{plain}', which is not a plain plate, pipe, trim, shell, ground, soil, water or sky"
    return None


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
    return f"{kind} built in code, but the sorter sends it to the prop pipeline (it has parts its code build lacks)"


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
    found = [("proxy", proxy_fault(prim)), ("material", material_fault(prim))]
    group = prim.GetPath().pathElementCount > 1 and prim.GetPath().GetPrefixes()[1].name
    if group == "Structure":
        found.append(("plain", plain_fault(prim)))
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
