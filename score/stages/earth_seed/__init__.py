"""The earth seed (#27): each designed scene's base stage made from its design and the rows' own outputs, in place of
the round-three folders (`usd-r3/<place>`, the ship's `usd-ship/<place>`) the old disk took (2026-10-19). Every row
that read those folders reads this row's output instead (the table's `earth_seeded`), and every row that read a
place's old kit (data/kit, retired with the old concepts on 2026-10-21) reads its design's kit here, `kit.json`
(the table's `earth_seeded`). Its places are every designed scene (the plan the creator locked, kept under
{home}/design/plans: the Earth's, the ship's rooms, a scene he added in the app) with a style (its own, its holder's,
else its top scene's; the owner, 2026-10-21: every scene builds from its own design alone, everything old retired).

    earth-seed@<place>  free   tools/usd/export.py on no kit piece, in the design's inventory and the place's style
                               (its own place.json entry, else that of the scene holding it, else its top scene's:
                               style_of), its shell laid from its locked plan (design_shell.py: a room whose kit holds
                               its walls its deck, walls and roof, an open place its raised levels, each painted from
                               the scene's surface library, surface-library@<place>, read where the place has one;
                               every other shell and every stair is the scene record's, from the same plan); the
                               stage under <place>/ in the output, and kit.json: the design's kit, no piece, its
                               style, the shell parts laid and the plan's box in the place's frame (`footprint`),
                               which the readers of the old kit read. Its made ground is the terrain row's and its models the surface line's bake,
                               which the assembly takes.
             gates      laid    every kit piece's model was made by a row (the design's kit lays none)
                        picks   every row the owner picked a model for shows that model (pick_lock.py), its faults
                                named (gaps.json `picks`) instead of stopping the export
"""
import json
import pathlib
import sys

from score import checks, contracts
from score.stages.earth_seed import design_shell
import score.stages.surfaces.surface_data as surface_data  # the module alone in the key, not the surface line
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
DESIGN = PROPS_HOME / "design"  # the locked designs, where the plan stage reads them (score/review/plans.KEPT's folder)
KIT_FILE = "kit.json"  # a design base's kit: no piece, and why (make_seed)
GAPS = "gaps.json"
KIT_LAYER = "kit"  # the kit's layer at the shared loop's seam (shapes_first.KIT): its shell pieces as inventory rows
LIBRARY_ROW = "surface-library"  # the scene's surface library (score/stages/surfaces/scene_library.py), its shell's
LIBRARY_FILE = "materials.json"


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def locked_plan(place):
    """The plan the creator locked for the place (DESIGN/plans), or None."""
    path = DESIGN / "plans" / f"{place}.json"
    return read(path) if path.is_file() else None


def holder_of(name, plans):
    """The scene whose plan (`plans`: {scene: its plan}) holds `name` (its `holds`), else None."""
    return next((holder for holder, plan in plans.items()
                 if any(hold.get("place") == name for hold in plan.get("holds", []))), None)


def known_as(place, surfaces=None):
    """The name the library and data/definitions/place.json know a place by: its surface data's `library` (`surfaces`,
    surface_data.path's where it has one, its design's where designed: the camp's expedition_camp, the street's
    prologue_street), else its own (prepare's handin.library_of rule)."""
    return read(surfaces).get("library", place) if surfaces is not None else place


def holders(place):
    """{scene: its locked plan's path pattern} of the scenes up from the place to the first one
    data/definitions/place.json knows (known_as), else to its top scene (the one no plan holds, whose style is the
    environment concept's: the Base), nearest first, each the one whose plan holds the one under it; none for a place
    place.json knows or a top scene itself; None for plans that hold each other round in a ring."""
    surfaces = surface_data.path(place)
    named, found = read(REPO / "data/definitions/place.json"), {}
    if known_as(place, surfaces if surfaces.is_file() else None) in named:
        return found
    plans, name = {path.stem: read(path) for path in sorted((DESIGN / "plans").glob("*.json"))}, place
    while True:
        holder = holder_of(name, plans)
        if holder is None:
            return found
        if holder in found or holder == place:
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
    the nearest scene holding it that place.json names (its holders' plans declared as `holder <scene>`), else its top
    scene's own name (a top scene place.json does not name, the Base: its style is the environment concept's, its
    library entries its own)."""
    named, own = read(inputs["places"]), known_as(place, inputs.get("surfaces"))
    if own in named:
        return own
    plans, name = {key.split(" ", 1)[1]: read(path) for key, path in inputs.items() if key.startswith("holder ")}, place
    while name not in named or name == place:
        held = holder_of(name, plans)
        if held is None:
            return own if name == place else name
        if held == place:
            raise ValueError(f"{place}: the plans holding it hold each other round in a ring (stopped at {name}): it "
                             "has no style")
        name = held
    return name


# --- earth-seed ------------------------------------------------------------------------------------------------------

def seed_files(place):
    """What the export reads: the design's files (design_files), the inventories (no ground: the made ground is the
    terrain row's), the library and sounds, the place definitions, the export, and the place's surface data where it
    has one (surface_data.pattern: its design's, which its finish route paints)."""
    found = {"inventories": "{data}/inventory", "library": "{data}/library", "sounds": "{data}/sound/surfaces.json",
             "places": "{data}/definitions/place.json", "export": "{repo}/tools/usd/export.py", **design_files(place)}
    if surface_data.path(place).exists():
        found["surfaces"] = surface_data.pattern(place)
    return found


def claiming_places(place):
    """The places whose surface line paints models this place lays (its surface data's `elsewhere`, surface_data's:
    its design's where designed), read beside."""
    return sorted({claim["place"] for claim in surface_data.record(place).get("elsewhere", {}).values()})


def export_tools():
    """tools/usd/export.py, imported where the assembly imports it."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import export
    return export


def design_files(place):
    """A design base's own inputs: the locked plan, its inventory, and the plans of the scenes holding it up to one
    with a style (holders)."""
    return {"design plan": "{home}/design/plans/" + f"{place}.json",
            "design inventory": "{home}/design/inventory/" + f"{place}.json",
            **{f"holder {holder}": path for holder, path in (holders(place) or {}).items()}}


def library_path(inputs):
    """The scene's surface library (its surface-library output's materials.json), else None: the place has no such
    row, so its shell's surfaces are named missing."""
    return pathlib.Path(inputs[LIBRARY_ROW]) / LIBRARY_FILE if LIBRARY_ROW in inputs else None


def make_seed(inputs, out, seed, params):
    """The place's base stage under out/<place> exported on no kit piece, in its design's inventory and style, its
    shell laid from its locked plan with its scene library's surfaces (design_shell); kit.json is the design's kit
    (what was laid and why, the plan's box), gaps.json its picks' faults."""
    export = export_tools()
    plan_path = pathlib.Path(inputs["design plan"])
    place, plan = plan_path.stem, read(plan_path)
    kit_path = out / KIT_FILE
    # a place with no ground of its own (its plan writes no terrain spots, as the scene record reads it) stands in its
    # own frame, its floor y = 0 (a kit room's `room`, as settle and the export read it)
    own_frame = {} if (plan.get("terrain") or {}).get("spots") else {"room": place}
    kit = {**own_frame, "place": style_of(place, inputs), "pieces": [], "footprint": design_shell.footprint(plan),
           "why": "the design lays no kit piece: its base is its locked plan's shell and what the rows make (the "
                  "old kits, data/kit, were retired with the old concepts, 2026-10-21)"}
    kit_path.write_text(json.dumps(kit, indent=1))
    gaps = []
    export.export(place, [], out / place, kit_path=kit_path, inventory_path=pathlib.Path(inputs["design inventory"]),
                  gaps=gaps)
    shell = design_shell.lay(out / place / "layers/base.usda", place, plan, export, library_path(inputs))
    kit_path.write_text(json.dumps({**kit, "shell": shell}, indent=1))
    (out / GAPS).write_text(json.dumps({"models": [], "picks": [gap for gap in gaps if "row" in gap]}, indent=1))


def seed_faults(folder):
    """Why a folder is not an earth seed: one place's stage under its own name, its kit and its gaps."""
    stages = [path for path in folder.iterdir() if path.is_dir() and (path / f"{path.name}.usda").exists()]
    faults = [] if len(stages) == 1 else [f"{len(stages)} place stages, not one"]
    return faults + [f"no {name}" for name in (GAPS, KIT_FILE) if not (folder / name).exists()]


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


def kit_in(output):
    """The design's kit an earth seed's output holds (kit.json)."""
    return pathlib.Path(output) / KIT_FILE


EARTH_SEED = contracts.Contract("earth-seed", 2, seed_faults, {"length": "metre", "up axis": "Y"})
SEED_CHECKS = (checks.Check("laid", judge_laid), checks.Check("picks", judge_picks))
