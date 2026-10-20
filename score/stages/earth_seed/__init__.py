"""The earth seed (#27): each earth place's base stage made again from git and the rows' own outputs, in place
of the round-three folder `usd-r3/<place>` the old disk took (2026-10-19). Every row that read that folder reads
this row's output instead (the table's `earth_seeded`), so the runner can plan and price everything after it.

    earth-kit@<place>   paid   the kit's named code fallbacks only (#41: the shared loop makes every kit piece, code
                               only where a record names why): of the place's installed kit (data/kit/<place>.json,
                               less its prop-route pieces and the glowing parts make_kit splits off), the pieces of
                               each row not handed to the loop (its hand-in record, data/props/<place>.json,
                               `"layer": "kit"`); fallbacks.json names every kit row not handed, with its route
                               (`code`, baked here, or `stored take`, a picture-made model of the old prop route that
                               earth-seed lays from data/parts) and why (NOT_HANDED); a handed row is the loop's
                               alone, and a model it makes none of is a gap, not a code bake (the batch rule).
                               Planned by route.py's
                               late-plan into make_kit jobs and baked once with the material library on rented cards
                               (tools/props/cloud/library_bake.py), as the ship-kit and late-bake stages do; gates
                               `made` and `surfaces` are theirs
    earth-seed@<place>  free   tools/usd/export.py on the place's kit, inventory, stored labelled takes, ground record
                               and old scene record, each model read from the earth-kit's made folder, the place's
                               own surfaces-bake and the bakes of the places that paint its claimed models (read
                               beside); the stage under <place>/ in the output, as the old folder held it (a loop-made
                               kit model is its bake's, named as the kit names it)
             gates      laid    every kit piece's model was made by a row; a piece whose model no row made is left out
                                and named (holes.json `models`), never a stand-in
                        picks   every row the owner picked a model for shows that model (pick_lock.py), its faults
                                named (holes.json `picks`) instead of stopping the export

A piece whose model is missing is a hole of this row: the kit's code pieces are earth-kit's, a generated piece is its
place's surface line's. The 7 screen parts route.py's `layout` drew from pictures are among them until a row draws them.
"""
import json
import pathlib
import shutil
import subprocess
import sys

from score import checks, contracts
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
ROUTE = REPO / "tools/props/library/route.py"
HOLES = "holes.json"
FALLBACKS = "fallbacks.json"
KIT_LAYER = "kit"  # the Earth kit's layer at the shared loop's seam (shapes_first.KIT)
# Why a kit row is not handed to the shared loop yet (#41), so earth-kit still bakes its code build: the finish route's
# bake lays a kit take only at its turn into the kit's frame (data/library/details.json `turn`), which no loop row
# measures, and a handed row the loop makes no model for fails likeness, which stops the place's line, not a gap.
NOT_HANDED = ("not handed to the shared loop yet: no loop row measures a kit take's turn into the kit frame, which its "
              "bake needs (details.json turn), and a row the loop makes no model for stops the line at likeness")
SCRATCH = "scratch"  # claimed models renamed, in the output's own folder while the make runs, then removed
UPRIGHT = [0.0, 1.0, 0.0]  # a piece laid without axes (an open place's: `at` and `facing`) stands upright
# One card at most an hour for a place's make_kit jobs (the ship's kits took EUR 0.09 to 0.14 a place, 2026-10-15);
# the clearance's estimate only, never shown as a price (data/costs/per-unit.json has none measured).
EUROS = 1.0
KIT_TOOLS = {"route": "{repo}/tools/props/library/route.py", "sorter": "{repo}/tools/props/library/sorter.py",
             "make_kit": "{repo}/tools/props/library/inside/make_kit.py",
             "pieces": "{repo}/tools/props/library/inside/pieces.py",
             "library bake": "{repo}/tools/props/cloud/library_bake.py",
             "library": "{repo}/data/library/materials.json", "pictures": "{repo}/data/library/pictures"}


# --- earth-kit -------------------------------------------------------------------------------------------------------

def piece_row(piece, kit, place):
    """A kit piece's inventory row: the row it names, else its kind without its room's or its place's name (as
    tools/usd/export.py's kind_row)."""
    if "row" in piece:
        return piece["row"]
    kind = piece["kind"]
    prefix = next((f"{name}_" for name in (kit.get("room", ""), place) if name and kind.startswith(f"{name}_")), "")
    return kind.removeprefix(prefix)


def code_built(piece, kit):
    """Whether a kit piece is code-built (route `code` in its models; a glowing or screen part is its host's model's,
    split off by make_kit)."""
    return "part" not in piece and kit.get("models", {}).get(piece["model"], {}).get("route") == "code"


def handed_in(objects):
    """The rows a hand-in record's objects ({row: entry}) hand the shared loop on the kit layer, by the loop's own rule
    (closeup_row.layer_of, as shapes_first.handed reads it)."""
    import score.stages.props.closeup_row as closeup_row  # by its full name, as made.py: the table stays out
    return {row for row, entry in objects.items() if closeup_row.layer_of(entry) == KIT_LAYER}


def handed_rows(place):
    """The rows the place handed the shared loop on the kit layer (its hand-in record, prop_data's); none for a place
    with no record."""
    import score.stages.props.prop_data as prop_data
    return handed_in(prop_data.objects(place))


def piece_route(piece, kit):
    """How earth-seed lays a kit piece the loop was not handed: its code build (earth-kit's bake), or a stored take
    (a picture-made model of the old prop route, data/parts)."""
    return "code" if code_built(piece, kit) else "stored take"


def fallbacks(kit, place, handed):
    """{row: {"route", "why"}} of every kit row not in `handed` (the rows the loop has on the kit layer), each laid by
    its code build or its stored take and named NOT_HANDED; a glowing or screen part is its host's. A handed row is the
    loop's alone: a model it makes none of is a gap (the batch rule), never baked or laid here."""
    routes = {}
    for piece in kit["pieces"]:
        if "part" not in piece:
            routes.setdefault(piece_row(piece, kit, place), set()).add(piece_route(piece, kit))
    return {row: {"route": " and ".join(sorted(routes[row])), "why": NOT_HANDED}
            for row in sorted(routes.keys() - handed)}


def code_layout(kit, place, fallback_rows):
    """The installed kit with the code-built pieces of its named fallback rows only, each with an up axis where it was
    laid without one, as late-plan reads."""
    pieces = [{"y": UPRIGHT, **piece} for piece in kit["pieces"]
              if code_built(piece, kit) and piece_row(piece, kit, place) in fallback_rows]
    return dict(kit, pieces=pieces)


def kit_jobs(place):
    """How many make_kit jobs the place's earth-kit sends (route.py late-plan's picture sets of its fallbacks), counted
    free from its installed kit and hand-in record; the forecast of the stage's units (tools/costs/per_unit.py
    `kit_jobs`). The path is put back as it was after (route.py puts its folders on it), so no code version takes in
    the route's folders."""
    kit = json.loads((REPO / "data/kit" / f"{place}.json").read_text())
    kept = list(sys.path)
    sys.path.insert(0, str(ROUTE.parent))
    try:
        import route
        planned = route.late_plan(code_layout(kit, place, fallbacks(kit, place, handed_rows(place))))
        return len(route.shared_sets(planned, {}))
    finally:
        sys.path[:] = kept


def kit_files(place):
    """The place's installed kit and its hand-in record where it has one, the library and place definitions the route
    plans from (its details, wear and surfaces), and the route's and bake's files."""
    found = {"kit": "{data}/kit/" + f"{place}.json", "library folder": "{data}/library",
             "places": "{data}/definitions/place.json", **KIT_TOOLS}
    import score.stages.props.prop_data as prop_data
    if prop_data.applies(place):
        found["props"] = prop_data.pattern(place)
    return found


def bake_jobs(out):
    """Every make_kit job late-plan wrote into `out`, each pointed at out/made."""
    jobs = sorted(out.glob("job-*.json"))
    for job in jobs:
        spec = json.loads(job.read_text())
        spec["out"] = str(out / "made")
        job.write_text(json.dumps(spec, indent=1))
    return jobs


def make_kit(inputs, out, seed, params):
    """Plan the kit's named fallbacks (fallbacks.json) and bake their code builds once on rented cards; the models into
    out/made. The handed rows are read from the hand-in record the row declares (`props`), none without one."""
    import score.stages.props.prop_data as prop_data
    kit_path = pathlib.Path(inputs["kit"])
    kit = json.loads(kit_path.read_text())
    handed = handed_in(prop_data.record_at(inputs["props"])["objects"]) if "props" in inputs else set()
    named = fallbacks(kit, kit_path.stem, handed)
    (out / FALLBACKS).write_text(json.dumps(named, indent=1))
    layout = out / "layout.json"
    layout.write_text(json.dumps(code_layout(kit, kit_path.stem, named), indent=1))
    subprocess.run([str(PROPS_PYTHON), str(inputs["route"]), "late-plan", str(layout), str(out)], check=True)
    jobs = bake_jobs(out)
    if jobs:
        subprocess.run([str(PROPS_PYTHON), str(inputs["library bake"]), *map(str, jobs), "--who",
                        f"score earth_kit stage ({pathlib.Path(inputs['kit']).stem}, seed {seed})"], check=True)
    (out / "made").mkdir(exist_ok=True)


# --- earth-seed ------------------------------------------------------------------------------------------------------

def seed_files(place):
    """What the export reads: the kit, the inventories, the stored takes, the grounds, the library and sounds, the
    place definitions and composites, and the place's old scene record where it has one."""
    found = {"kit": "{data}/kit/" + f"{place}.json", "inventories": "{data}/inventory", "parts": "{data}/parts",
             "grounds": "{data}/ground", "library": "{data}/library", "sounds": "{data}/sound/surfaces.json",
             "places": "{data}/definitions/place.json", "export": "{repo}/tools/usd/export.py"}
    if (REPO / "data/scene" / f"{place}.json").exists():
        found["scene"] = "{data}/scene/" + f"{place}.json"
    if (REPO / "data/surfaces" / f"{place}.json").exists():
        found["surfaces"] = "{data}/surfaces/" + f"{place}.json"
    return found


def export_tools():
    """tools/usd/export.py and the assembly's bake helpers, imported where the assembly imports them."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import export
    from score.stages.assembly import baked
    return export, baked


def model_folders(inputs, scratch):
    """The folders the place's models are read from: earth-kit's made models, its own bake's, and each claimed model
    of another place's bake under the name this place lays it (assembly.baked.renamed_model, in `scratch`)."""
    export, baked = export_tools()
    folders = [pathlib.Path(inputs["earth-kit"]) / "made"]
    if "surfaces-bake" not in inputs:
        return folders
    folders.append(pathlib.Path(inputs["surfaces-bake"]) / "made")
    for bake, _, _, models in baked.claimed_bakes(inputs, scratch):
        folders += [baked.renamed_model(bake / "made", baked_as, model, scratch / "renamed")
                    for model, baked_as in models.items()]
    return folders


def make_seed(inputs, out, seed, params):
    """The place's base stage under out/<place> (export.py), every model a row made; holes.json names the rest."""
    export, _ = export_tools()
    kit_path = pathlib.Path(inputs["kit"])
    place = kit_path.stem
    kit = json.loads(kit_path.read_text())
    holes, scratch = [], out / SCRATCH
    try:
        export.export(place, model_folders(inputs, scratch), out / place, kit_path=kit_path,
                      ground=export.grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0])),
                      scene=export.scene_record.record(place), holes=holes)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    found = {"models": sorted({hole["model"] for hole in holes if "model" in hole}),
             "picks": [hole for hole in holes if "row" in hole]}
    (out / HOLES).write_text(json.dumps(found, indent=1))


def seed_faults(folder):
    """Why a folder is not an earth seed: one place's stage under its own name, and its holes."""
    stages = [path for path in folder.iterdir() if path.is_dir() and (path / f"{path.name}.usda").exists()]
    faults = [] if len(stages) == 1 else [f"{len(stages)} place stages, not one"]
    return faults + ([] if (folder / HOLES).exists() else [f"no {HOLES}"])


def holes_of(output):
    return json.loads((pathlib.Path(output) / HOLES).read_text())


def judge_laid(output, inputs, evidence):
    """Every kit piece's model was made by a row."""
    missing = holes_of(output)["models"]
    reason = "every kit piece's model made" if not missing else \
        f"{len(missing)} models no row made, their pieces left out: " + ", ".join(missing[:8])
    return checks.Verdict("laid", checks.FAIL if missing else checks.PASS, reason, {"missing": len(missing)},
                          {"missing": "lower"}, tuple(missing))


def judge_picks(output, inputs, evidence):
    """Every row the owner picked a model for shows that model."""
    broken = holes_of(output)["picks"]
    findings = tuple(f"{fault['row']}: {fault['why']}" for fault in broken)
    reason = "every owner's pick shown" if not broken else f"{len(broken)} picks not shown: " + "; ".join(findings[:3])
    return checks.Verdict("picks", checks.FAIL if broken else checks.PASS, reason, {"broken": len(broken)},
                          {"broken": "lower"}, findings)


def place_in(output):
    """The place an earth seed's output holds (its one stage folder)."""
    return next(path for path in pathlib.Path(output).iterdir() if path.is_dir())


EARTH_KIT = contracts.Contract("earth-kit", 2, lambda folder: [f"no {name}" for name in ("layout.json", "made",
                                                                                        FALLBACKS)
                                                              if not (folder / name).exists()],
                               {"length": "metre", "up axis": "Y"})
EARTH_SEED = contracts.Contract("earth-seed", 1, seed_faults, {"length": "metre", "up axis": "Y"})
SEED_CHECKS = (checks.Check("laid", judge_laid), checks.Check("picks", judge_picks))
