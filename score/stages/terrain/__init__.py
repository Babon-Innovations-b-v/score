"""The terrain stage (the paper's Methods, "Terrain"): every ground of the environment from its design alone, one
environment node for all of them (the owner, 2026-10-21: everything old is retired, the batch makes everything fresh
from the design; the game's ground plans and copied grounds went with it). Free and local.

Terrain is a model layer (CONTEXT.md "layer adapter", the owner, 2026-10-20): its detail (craters, tracks, outcrops:
the scene inventory's terrain rows) comes from close-ups made into models through the prop pipeline, joined into the
ground by ground-join@<place> (join.py). This row is the code fallback under them, and every ground's measures.json
says so (`made_by`, MADE_BY): the ground the design gives, standing wherever no piece was made.

    make     for each body or plot a top scene stands on (design.layout: its kept sky's site, the setting's body at its
             true radius or the plot's plane), the ground under every scene standing on it (the top scene and each
             scene its plan holds) raised by the relief of each kept plan's terrain spots and by its far landforms (the
             far hills its places' plans mark beyond, design.far_reliefs), lowered under its bodies of water and
             their water laid over it (design.waters: the square's sea); for every such scene the
             layer that draws the ground in its frame (outside.py); the ground's record (ground.json) and measures
    gates    spots      the ground drawn passes through every terrain spot of the plans standing on it
             curve      the ground falls away with its body's true radius (level on a plot)
             The ground under each place's objects, its continuity and its openings are judged on the place's
             assembly, which stands on this ground (ground-fit@<place>, fit.py).

The output (contract `grounds` v2: v1 was the game's plans, pictures and rocks) holds a folder per ground: ground.json
(design.layout's ground with its row), measures.json, and places/<place>.usdc, the layer a place's stage takes over
its old ground (the ground only: the places it shows are its own stage's and the neighbours row's).
"""
import json
import pathlib

from pxr import Sdf, Usd

from score import contracts
from score.stages import natural_grounds
from score.stages.terrain import design, gates, outside

FILES = {"plans": "{home}/design/plans", "skies": "{home}/design/sky", "inventories": "{home}/design/inventory",
         "reference": "{data}/physics/bodies.json"}
CHECKS = gates.CHECKS
# What made every ground here (#27): the code fallback, named; the terrain adapter's pieces join over it.
MADE_BY = {"made_by": "code fallback: the design's ground (design.py: the body's true sphere or the plot's plane, "
                      "the plans' terrain spots)",
           "why": "the terrain adapter's detail pieces (the prop pipeline's models of the inventory's terrain rows) "
                  "are joined over it by ground-join@<place> (join.py); where none was made this ground stands (#27)"}


def ground_row(ground, inventories, plans):
    """The row the ground is: of its first top scene's plan `structure` rows its scene inventory marks terrain, the
    one a level of its plan at the floor's height is named for (the square's plaza, not its sea), else the first;
    None when it has none."""
    for top in sorted(ground["tops"]):
        path = pathlib.Path(inventories) / f"{top}.json"
        rows = {row["id"]: row for row in json.loads(path.read_text())["rows"]} if path.is_file() else {}
        found = [row for row in plans[top].get("structure") or [] if (rows.get(row) or {}).get("terrain")]
        floors = {str(level.get("name", "")).lower() for level in plans[top].get("levels") or []
                  if abs(float(level.get("height") or 0.0)) < 1e-6}
        if found:
            return next((row for row in found if row.replace("_", " ") in floors), found[0])
    return None


def row_of(ground, row, inventories):
    """The ground row's entry in its top scenes' inventories ({"id"} alone when none holds it)."""
    for top in sorted(ground["tops"]):
        path = pathlib.Path(inventories) / f"{top}.json"
        found = [entry for entry in json.loads(path.read_text())["rows"] if entry["id"] == row] \
            if path.is_file() else []
        if found:
            return found[0]
    return {"id": row}


def recipe_of(ground, row, inventories, skies, table):
    """[the natural ground recipe the ground is made with, why] by rule (natural_grounds.of_row: its row's words,
    else its body's physics, the setting of its first top scene's kept sky with the reference `table`; a plot's
    none)."""
    bodies = skies[sorted(ground["tops"])[0]]["setting"].get("bodies") or []
    body = next((body for body in bodies if body["body"] == ground["on"]), None) \
        if ground["kind"] == "body" else None
    entry = row_of(ground, row, inventories) if row else {"id": None}
    return list(natural_grounds.of_row(entry, body, bodies, table))


def own_water_row(place, inventories, fallback):
    """The place's own water row (design.water_row) of its inventory, so its rows check counts the water it sees
    (the stairwell's water is the square's sea), else `fallback`."""
    path = pathlib.Path(inventories) / f"{place}.json"
    rows = json.loads(path.read_text())["rows"] if path.is_file() else []
    return next((row for row in rows if design.water_row(row)), fallback)


def sheet_of(ground, place, found, sheets, inventories):
    """The place's water layer entry (outside.write's `sheet`): its water's points and triangles, its row and the
    natural ground recipe its row's words name; None with no water showing."""
    shown = outside.water(ground, place, found, sheets)
    if shown is None:
        return None
    row = own_water_row(place, inventories, sheets[0][3])
    return (*shown, row["id"], list(natural_grounds.of_row(row, None, [], {})))


def write_layer(folder, place, found, row, recipe, sheet=None):
    """The layer that draws the ground in the place's frame, a whole asset (whole_layer): places/<place>.usdc."""
    path = folder / "places" / f"{place}.usdc"
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    stage = Usd.Stage.Open(layer)
    stage.DefinePrim(f"/{place}")
    outside.write(stage, place, found, row, recipe, sheet)
    outside.whole_layer.stamped(layer, place).Save()


def make_ground(name, ground, row, recipe, out, plans, inventories):
    """One ground's place layers, record and measures into out/<name>, its natural ground recipe (`recipe`,
    [recipe, why]) on its record and meshes, the far landforms of its places' inventories (design.far_reliefs) raised
    on it and listed in its record (`far`)."""
    folder = out / name
    folder.mkdir(parents=True)
    far, raised = design.far_reliefs(ground, plans, inventories, outside.reach(ground))
    sheets, waters = design.waters(ground, plans, inventories, outside.reach(ground))
    shaped = design.reliefs(ground) + far + [(source, relief) for source, relief, _, _ in sheets]
    laid = {place: outside.meshes(ground, place, shaped) for place in ground["places"]}
    for place, found in laid.items():
        write_layer(folder, place, found, row, recipe, sheet_of(ground, place, found, sheets, inventories))
    (folder / "ground.json").write_text(json.dumps({**ground, "ground": name, "row": row, "recipe": recipe[0],
                                                    "recipe_by": recipe[1], "far": raised, "water": waters},
                                                   indent=1))
    (folder / "measures.json").write_text(json.dumps({**MADE_BY, **gates.measured(ground, laid)}, indent=1))


def make(inputs, out, seed, params):
    """Make every ground of the design."""
    plans, skies = design.kept(inputs["plans"]), design.kept(inputs["skies"])
    table = json.loads(pathlib.Path(inputs["reference"]).read_text())
    for name, ground in design.layout(plans, skies).items():
        row = ground_row(ground, inputs["inventories"], plans)
        make_ground(name, ground, row, recipe_of(ground, row, inputs["inventories"], skies, table), out, plans,
                    inputs["inventories"])


def grounds_faults(folder):
    """The output against its contract: at least one ground, each with its record, measures and place layers."""
    made = [path for path in pathlib.Path(folder).iterdir() if (path / "ground.json").exists()]
    if not made:
        return ["no ground made"]
    return [f"{ground.name} lacks {name}" for ground in made for name in ("measures.json", "places")
            if not (ground / name).exists()]


GROUNDS = contracts.Contract("grounds", 2, grounds_faults, {"length": "metre", "up axis": "Y"})
