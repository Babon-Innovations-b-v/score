"""The earth seed (#27): each place's base stage made again from git, its design and the rows' own outputs, in place
of the round-three folders (`usd-r3/<place>`, the ship's `usd-ship/<place>`) the old disk took (2026-10-19). Every
row that read those folders reads this row's output instead (the table's `earth_seeded`), so the runner can plan and
price everything after it. Its places are every place with a kit laid and every designed scene (the plan the creator
locked, kept under {home}/design/plans: the ship's rooms, a scene he added in the app), the earth's and the ship's
alike (the owner, 2026-10-21: every designed scene's base from its own design).

A place's kit is its base's only when no design is locked for it (kit_is_base): a place with no locked plan has
only its kit. A designed scene's base is always its design's (data/kit was laid by per-place scripts from the filed
plans, the old concepts' rooms, whatever their size; the hangar's matched its locked plan's 32 x 64 m and was still
the old room, 2026-10-21): no kit piece, its room shell
from its locked plan (design_shell.py), its inventory the design's, its style its own place.json entry's, else that
of the scene holding it (style_of); nothing here bakes or lays a kit laid for another room. A place with no style
(styled: a top scene place.json does not name) has no base row until it has one.

    earth-kit@<place>   paid   (a place whose kit is its base's) the kit's named code fallbacks only (#41: the shared
                               loop makes every kit piece, code only where a record names why): of the place's
                               installed kit (data/kit/<place>.json, less its prop-route pieces and the glowing
                               parts make_kit splits off), the pieces of each row not handed to the loop (its
                               hand-in record, data/props/<place>.json, `"layer": "kit"`); fallbacks.json names
                               every kit row not handed, with its route (`code`, baked here, or `stored take`, a
                               picture-made model of the old prop route that earth-seed lays from data/parts) and
                               why (NOT_HANDED); a handed row is the loop's alone, and a model it makes none of is a
                               gap, not a code bake (the batch rule). Planned by route.py's
                               late-plan into make_kit jobs and baked once with the material library on rented cards
                               (tools/props/cloud/library_bake.py), as the ship-kit and late-bake stages do; gates
                               `made` and `surfaces` are theirs
    earth-seed@<place>  free   tools/usd/export.py on the place's kit, inventory, stored labelled takes, ground record
                               and old scene record, each model read from the earth-kit's made folder, the place's
                               own surfaces-bake and the bakes of the places that paint its claimed models (read
                               beside); the stage under <place>/ in the output, as the old folder held it (a loop-made
                               kit model is its bake's, named as the kit names it). A place whose kit is not its
                               base's: the export on no piece (kit.json in the output says why), in its design's
                               inventory and style, and its room shell from its locked plan (design_shell.py; an
                               inside room whose kit holds its walls only: a domed or outdoor shell is its scene
                               record's, an open place has none); its made ground is the terrain row's, which the
                               assembly takes
             gates      laid    every kit piece's model was made by a row; a piece whose model no row made is left out
                                and named (gaps.json `models`), never a stand-in
                        picks   every row the owner picked a model for shows that model (pick_lock.py), its faults
                                named (gaps.json `picks`) instead of stopping the export

A piece whose model is missing is a gap of this row: the kit's code pieces are earth-kit's, a generated piece is its
place's surface line's. The 7 screen parts route.py's `layout` drew from pictures are among them until a row draws them.
"""
import json
import pathlib
import shutil
import subprocess
import sys

from score import checks, contracts
from score.stages.earth_seed import design_shell
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
DESIGN = PROPS_HOME / "design"  # the locked designs, where the plan stage reads them (score/review/plans.KEPT's folder)
KIT_FILE = "kit.json"  # a design base's kit: no piece, and why (make_design_seed)
ROUTE = REPO / "tools/props/library/route.py"
GAPS = "gaps.json"
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
             "pipeline failures": "{repo}/data/library/pipeline_failures.json",
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


# --- the base's kit ------------------------------------------------------------------------------------------------

def read(path):
    return json.loads(pathlib.Path(path).read_text())


def locked_plan(place):
    """The plan the creator locked for the place (DESIGN/plans), or None."""
    path = DESIGN / "plans" / f"{place}.json"
    return read(path) if path.is_file() else None


def kit_is_base(place):
    """Whether the place's kit (data/kit) is its base's: laid, and no design locked for the place. A designed scene's
    base is always its design's (the owner, 2026-10-21: no hand-written per-scene list decides what a scene gets): a
    kit laid by a per-place script from a filed plan is the old concept's room, whatever its size."""
    return (REPO / "data/kit" / f"{place}.json").exists() and locked_plan(place) is None


def holder_of(name, plans):
    """The scene whose plan (`plans`: {scene: its plan}) holds `name` (its `holds`), else None."""
    return next((holder for holder, plan in plans.items()
                 if any(hold.get("place") == name for hold in plan.get("holds", []))), None)


def known_as(place, surfaces=None):
    """The name the library and data/definitions/place.json know a place by: its surface data's `library` (`surfaces`,
    data/surfaces/<place>.json where it has one: the camp's expedition_camp, the street's prologue_street), else its
    own (prepare's handin.library_of rule)."""
    return read(surfaces).get("library", place) if surfaces is not None else place


def holders(place):
    """{scene: its locked plan's path pattern} of the scenes up from the place to the first one
    data/definitions/place.json knows (known_as), nearest first, each the one whose plan holds the one under it; none
    for a place place.json knows; None for one with no such scene above it (no style: a top scene place.json does not
    name, the base's outside, has no base row until it has one)."""
    surfaces = REPO / "data/surfaces" / f"{place}.json"
    named, found = read(REPO / "data/definitions/place.json"), {}
    if known_as(place, surfaces if surfaces.is_file() else None) in named:
        return found
    plans, name = {path.stem: read(path) for path in sorted((DESIGN / "plans").glob("*.json"))}, place
    while True:
        holder = holder_of(name, plans)
        if holder is None or holder in found or holder == place:
            return None
        found[holder] = "{home}/design/plans/" + f"{holder}.json"
        if holder in named:
            return found
        name = holder


def styled(place):
    """Whether the place has a style its base can be made in (holders)."""
    return holders(place) is not None


def style_of(place, inputs):
    """The place.json entry whose style the place takes: its own (known_as, its `surfaces` input where declared), else
    the nearest scene holding it that place.json names (its holders' plans declared as `holder <scene>`)."""
    named, own = read(inputs["places"]), known_as(place, inputs.get("surfaces"))
    if own in named:
        return own
    plans, name = {key.split(" ", 1)[1]: read(path) for key, path in inputs.items() if key.startswith("holder ")}, place
    while name not in named or name == place:
        held = holder_of(name, plans)
        if held is None or held == place:
            raise ValueError(f"{place}: no scene holding it in its declared holder plans is in place.json "
                             f"(stopped at {name}): it has no style")
        name = held
    return name


# --- earth-seed ------------------------------------------------------------------------------------------------------

def seed_files(place):
    """What the export reads: the kit (where it is not the base's, the design's files instead: design_files), the
    inventories, the stored takes, the grounds, the library and sounds, the place definitions and composites, and the
    place's old scene record where it has one."""
    found = {"kit": "{data}/kit/" + f"{place}.json", "inventories": "{data}/inventory", "parts": "{data}/parts",
             "grounds": "{data}/ground", "library": "{data}/library", "sounds": "{data}/sound/surfaces.json",
             "places": "{data}/definitions/place.json", "export": "{repo}/tools/usd/export.py"}
    if not kit_is_base(place):
        found = {**{name: path for name, path in found.items() if name != "kit"}, **design_files(place)}
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


def design_files(place):
    """A design base's own inputs: the locked plan, its inventory, and the plans of the scenes holding it up to one
    with a style (holders)."""
    return {"design plan": "{home}/design/plans/" + f"{place}.json",
            "design inventory": "{home}/design/inventory/" + f"{place}.json",
            **{f"holder {holder}": path for holder, path in (holders(place) or {}).items()}}


def make_design_seed(inputs, out):
    """A place whose kit is not its base's: its stage under out/<place> exported on no kit piece, in its design's
    inventory and style, its room shell laid from its locked plan (an inside room whose kit holds its walls:
    design_shell.laid_for); kit.json says what was laid and why, gaps.json its picks' faults."""
    export, _ = export_tools()
    plan_path = pathlib.Path(inputs["design plan"])
    place, plan = plan_path.stem, read(plan_path)
    kit_path = out / KIT_FILE
    kit = {"room": place, "place": style_of(place, inputs), "pieces": [],
           "why": "no kit laid for this design: its base is its locked plan's room shell and what the rows make "
                  "(data/kit's, where there is one, was laid for another room)"}
    kit_path.write_text(json.dumps(kit, indent=1))
    gaps = []
    export.export(place, [], out / place, kit_path=kit_path, inventory_path=pathlib.Path(inputs["design inventory"]),
                  gaps=gaps)
    shell = design_shell.lay(out / place / "layers/base.usda", place, plan, export.scene_record) \
        if design_shell.laid_for(plan) else []
    kit_path.write_text(json.dumps({**kit, "shell": shell}, indent=1))
    (out / GAPS).write_text(json.dumps({"models": [], "picks": [gap for gap in gaps if "row" in gap]}, indent=1))


def make_seed(inputs, out, seed, params):
    """The place's base stage under out/<place> (export.py), every model a row made; gaps.json names the rest. A
    place whose kit is not its base's is its design's (make_design_seed)."""
    if "kit" not in inputs:
        return make_design_seed(inputs, out)
    export, _ = export_tools()
    kit_path = pathlib.Path(inputs["kit"])
    place = kit_path.stem
    kit = json.loads(kit_path.read_text())
    gaps, scratch = [], out / SCRATCH
    try:
        export.export(place, model_folders(inputs, scratch), out / place, kit_path=kit_path,
                      ground=export.grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0])),
                      scene=export.scene_record.record(place), gaps=gaps)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    found = {"models": sorted({gap["model"] for gap in gaps if "model" in gap}),
             "picks": [gap for gap in gaps if "row" in gap]}
    (out / GAPS).write_text(json.dumps(found, indent=1))


def seed_faults(folder):
    """Why a folder is not an earth seed: one place's stage under its own name, and its gaps."""
    stages = [path for path in folder.iterdir() if path.is_dir() and (path / f"{path.name}.usda").exists()]
    faults = [] if len(stages) == 1 else [f"{len(stages)} place stages, not one"]
    return faults + ([] if (folder / GAPS).exists() else [f"no {GAPS}"])


def gaps_of(output):
    return json.loads((pathlib.Path(output) / GAPS).read_text())


def judge_laid(output, inputs, evidence):
    """Every kit piece's model was made by a row."""
    missing = gaps_of(output)["models"]
    reason = "every kit piece's model made" if not missing else \
        f"{len(missing)} models no row made, their pieces left out: " + ", ".join(missing[:8])
    return checks.Verdict("laid", checks.FAIL if missing else checks.PASS, reason, {"missing": len(missing)},
                          {"missing": "lower"}, tuple(missing))


def judge_picks(output, inputs, evidence):
    """Every row the owner picked a model for shows that model."""
    broken = gaps_of(output)["picks"]
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
