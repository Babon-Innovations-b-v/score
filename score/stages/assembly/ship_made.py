"""A ship place's made pieces laid on its kit-built base (2026-10-15: complete@quarters failed "no object of this row
on the stage" for its bunks, lockers, console, screens, vents and door frame).

A ship place's base (usd-ship/<place>, exported from its installed kit) holds the code pieces only: the ship-kit stage
keeps those (ship_kits.code_only), a prop-route row's model being its own take, made later. An old room's seed laid
every row, so its bake only swaps the assets under objects already laid; a ship place has no object to swap into.
The table runs this for the ship places only (score.stages.ship_assembled), so no other place's assembly moves; the
ship places declare this file, the plan and the kit layout's tools, so a change here moves their keys.

    owners   each prop-route row's painting place: the place whose surface data lists a take of the row's `thing`
             (each take is painted by one place only), the place's own or another's (the quarters' lockers are the
             shiplock's)
    pieces   each prop-route row's pieces where the ship kit lays them (tools/props/scene/ship_kit.layout on the plan
             and inventory, as the ship-kit stage lays them before it keeps the code pieces), each with the model its
             owner's bake makes it from
    lay      every piece of a row the base lays no object of: an object referencing the baked model's asset (another
             place's bake taken in as the assembly takes a claimed one), its frame a kit piece's
             (package.kit_matrix); a row no bake made stays unlaid, and the completion gate's rows check names it
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
SURFACES = REPO / "data/surfaces"
# The world files a ship place's made pieces are laid from, beside the inventory folder and the place's own surface
# data the assembly declares.
FILES = {"plan": "{data}/plans/{place}.json", "ship made": "{repo}/score/stages/assembly/ship_made.py",
         "ship kit": "{repo}/tools/props/scene/ship_kit.py", "room kit": "{repo}/tools/props/scene/room_kit.py",
         "hub kit": "{repo}/tools/props/scene/hub_kit.py", "sorter": "{repo}/tools/props/library/sorter.py",
         "pipeline failures": "{repo}/data/library/pipeline_failures.json"}


def made_rows(inventory):
    """The inventory's prop-route rows, the ones the sorter sends to the shared loop (sorter.row_route `model`, whatever
    the row's own kind): {row: the take kind its `thing` names}."""
    import score.stages.props.prop_data as prop_data
    with prop_data.tools("props/library"):
        import sorter
    return {row["id"]: row["thing"].split(":", 1)[1] for row in inventory["rows"]
            if sorter.row_route(inventory["scene"], row) == "model"}


def take_kinds(surfaces):
    """{take kind: model} a place's surface data bakes."""
    takes = {take: entry["kind"] for take, entry in surfaces.get("takes", {}).items()}
    return {takes[take]: model for model, take in surfaces.get("bake", {}).get("models", {}).items() if take in takes}


def owners(place):
    """{row: the place whose surface line paints it} for each prop-route row of the place's inventory a surface data
    of the world paints."""
    kinds = made_rows(json.loads((REPO / "data/inventory" / f"{place}.json").read_text()))
    painted = {kind: path.stem for path in sorted(SURFACES.glob("*.json"))
               for kind in take_kinds(json.loads(path.read_text()))}
    return {row: painted[kind] for row, kind in kinds.items() if kind in painted}


def neighbours(place):
    """The other places whose bake a ship place's made pieces come from, read beside."""
    return sorted(set(owners(place).values()) - {place})


def files(place):
    """FILES, and the surface data of every other place a made piece comes from."""
    return {**{name: pattern.replace("{place}", place) for name, pattern in FILES.items()},
            **{f"surfaces {other}": "{data}/surfaces/" + f"{other}.json" for other in neighbours(place)}}


def row_models(inventory, surfaces):
    """{row: (owner, model)} of each prop-route row a bake makes, `surfaces` {place: its surface data path}."""
    baked = {kind: (owner, model) for owner, path in surfaces.items()
             for kind, model in take_kinds(json.loads(pathlib.Path(path).read_text())).items()}
    return {row: baked[kind] for row, kind in made_rows(inventory).items() if kind in baked}


def pieces(place, plan, inventory, models):
    """Each prop-route piece the ship kit lays, as the kit lays it, with its row and model (`models`: {row: model});
    a glowing part (a route-written lens) left out."""
    import score.stages.props.prop_data as prop_data
    with prop_data.tools("props/scene"):
        import ship_kit
        layout = ship_kit.layout(place, plan, inventory)
    found = []
    for piece in layout["pieces"]:
        row = piece["kind"].removeprefix(f"{layout['room']}_")
        if row in models and "part" not in piece:
            found.append(dict(piece, row=row, model=models[row]))
    return found


def surfaces_of(inputs, place, owners_needed):
    """{owner: its surface data path} from the node's inputs: the place's own `surfaces`, the others' `surfaces
    <owner>`."""
    return {owner: inputs["surfaces"] if owner == place else inputs[f"surfaces {owner}"] for owner in owners_needed}


def lay(inputs, out, place):
    """Every made piece of a row the base lays no object of, laid in the base layer; {row: model} laid, and the
    prop-route rows left unlaid (no bake makes them)."""
    import export
    import stage_inputs
    from pxr import Sdf, Usd
    from score.stages.assembly import BASE_LAYER, take_bake
    inventory = json.loads((pathlib.Path(inputs["inventories"]) / f"{place}.json").read_text())
    named = {place, *(name.split(" ", 1)[1] for name in inputs if name.startswith("surfaces "))}
    models = row_models(inventory, surfaces_of(inputs, place, named))
    layer = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    stage = Usd.Stage.Open(layer)
    laid = {prim.GetAttribute("score:row").Get() for prim in stage.Traverse() if prim.HasAttribute("score:row")}
    wanted = {row: entry for row, entry in models.items() if row not in laid}
    for owner, model in sorted(set(wanted.values())):
        if owner != place:
            take_bake(pathlib.Path(inputs[f"surfaces-bake@{owner}"]), pathlib.Path(inputs[f"surfaces-paint@{owner}"]),
                      out, {model: model})
    rows = {row["id"]: row for row in inventory["rows"]}
    found = pieces(place, json.loads(pathlib.Path(inputs["plan"]).read_text()), inventory,
                   {row: model for row, (_, model) in wanted.items()})
    stage = Usd.Stage.Open(Sdf.Layer.FindOrOpen(str(out / BASE_LAYER)))  # take_bake saved the base under us
    for name, piece in zip(export.object_names(found), found):
        owner = wanted[piece["row"]][0]
        bake = pathlib.Path(inputs["surfaces-bake" if owner == place else f"surfaces-bake@{owner}"])
        gltf = bake / "made" / f"{piece['model']}.gltf"
        matrix, _ = export.package.kit_matrix(piece, *export.package.model_box(gltf))
        export.laid_object(stage, f"/{place}/Objects/{name}", dict(piece, matrix=matrix.tolist()),
                           rows[piece["row"]], f"../assets/{piece['model']}.usdc", None,
                           sha256=stage_inputs.model_hash(gltf))
    stage.GetRootLayer().Save()
    unlaid = sorted(set(made_rows(inventory)) - laid - set(wanted))
    return {row: model for row, (_, model) in sorted(wanted.items())}, unlaid
