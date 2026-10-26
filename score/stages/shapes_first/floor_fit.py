"""props-inputs@<place>'s gate `fits the plan` (#41): every row the place's plan stands on its floor fits the floor the
rough model was registered to, turned or not; how many fit no footprint of the aligned rough model is measured.

Held to the floor are the rows the place stands on it. Counted, never held: a row of a layer that lies round the
floor (align.ROUND: a terrain detail area), the rows the kept plan names its `structure` (its own shell, floors,
roofs, ground: laid as the plan's walls, levels and roofs, never as an item at the row's metres) and its `beyond`
(seen through a window or past its edge: they stand in another place, plan_writing.py), a row marked `far` (laid far
off by the scene record alone, never at a plan item: prepare's groups.far_made), and a row standing on the ground that
the plan lays only against its edge (`past_edge`: a building round a square, its face the plan's item, its body on the
ground past the place's edge; 2026-10-26, the square's 30 by 30 m buildings on its 29.86 m floor). Rows of a layer no
place owns (align.NO_PLACE) are held to no plan. Unknown without a registration: the loop splits a place's parts only once its
rough model stands in its plan.

The kept plan is the file the plan row reads (`{home}/design/plans/<place>.json`), declared on the split as KEPT_PLAN
by the table (stages.boxed_split); a place with none holds every row to the floor.
"""
import json
import pathlib

from score import checks
import score.stages.shapes_first.align as align
from score.stages.surfaces.surface_gates import unknown, verdict

KEPT_PLAN = "kept plan"
NOT_ON_FLOOR = ("structure", "beyond")  # the kept plan's lists of rows it never stands on its floor
# A row's metres are rounded to 3 decimals (prepare/groups.plan_sizes) and the plan's floor to 4 (scene_record/plan
# box_of), so a row laid as wide as the floor can read up to this much wider.
ROUNDING = 0.001


def fits(size, wide, deep):
    """Whether a row's footprint (its size's wide and deep) fits a floor of `wide` by `deep`, turned or not."""
    wide, deep = wide + ROUNDING, deep + ROUNDING
    return (size[0] <= wide and size[1] <= deep) or (size[0] <= deep and size[1] <= wide)


def kept_plan(inputs):
    """The kept plan the split declares (KEPT_PLAN), {} without one."""
    path = inputs.get(KEPT_PLAN)
    return json.loads(pathlib.Path(path).read_text()) if path else {}


def off_floor(plan):
    """{list name: set of row ids} the kept plan never stands on its floor (NOT_ON_FLOOR)."""
    return {name: set(plan.get(name) or []) for name in NOT_ON_FLOOR}


def at_edge(item, wide, deep):
    """Whether a plan item [name, x, y, across, along, ...] touches the edge of the plan's `wide` by `deep` box."""
    x, y, across, along = (float(value) for value in item[1:5])
    return min(x, y) <= ROUNDING or x + across >= wide - ROUNDING or y + along >= deep - ROUNDING


def past_edge(plan, inventory):
    """The ids of the inventory's rows standing on the ground (the ground runs on past the place, its floor does not)
    whose every plan item, laid for that row, touches the plan's edge: the plan lays only its face, its body stands on
    the ground round the place."""
    if not plan.get("w") or not plan.get("d"):
        return set()
    tied, laid = plan.get("rows") or {}, {}
    for item in plan.get("items") or []:
        if len(item) > 6 and item[6] == "item" and tied.get(item[0]):
            laid.setdefault(tied[item[0]][0], []).append(item)
    return {row["id"] for row in inventory.get("rows", []) if row.get("anchor") == "ground" and laid.get(row["id"])
            and all(at_edge(item, plan["w"], plan["d"]) for item in laid[row["id"]])}


def judge_rows_fit(output, inputs, evidence):
    """The parts split held to the registered floor (module docstring)."""
    split = [row for row in json.loads((output / "rows.json").read_text())["rows"]
             if row.get("layer") not in align.NO_PLACE]
    if not split:
        return checks.Verdict("fits the plan", checks.PASS, "no row on a place's plan: models no place owns")
    if "rough-align" not in inputs:
        return unknown("fits the plan", "no registered rough model: the place has no plan to register one to")
    found = json.loads((pathlib.Path(inputs["rough-align"]) / align.REGISTRATION).read_text())
    if found["unregistrable"]:
        return unknown("fits the plan", "the rough model was not registered: " + "; ".join(found["unregistrable"]))
    plan = kept_plan(inputs)
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text()) if inputs.get("inventory") else {}
    lists = {"rows round the floor": {row["id"] for row in split if row.get("layer") in align.ROUND},
             **{f"rows of the plan's {name}": ids for name, ids in off_floor(plan).items()},
             "rows laid far off": {row["id"] for row in split if row.get("far")},
             "rows past the plan's edge": past_edge(plan, inventory)}
    apart, counted = {}, set()
    for name, ids in lists.items():  # a row in two lists counted in the first
        apart[name] = {row["id"] for row in split} & ids - counted
        counted |= apart[name]
    rows = [row for row in split if row["id"] not in counted]
    floor, aligned = found["plan"], found["aligned"]
    failing = [f"{row['id']}: {row['size'][0]} by {row['size'][1]} m fits no way on the {floor['wide']:.2f} by "
               f"{floor['deep']:.2f} m floor" for row in rows if not fits(row["size"], floor["wide"], floor["deep"])]
    past = sum(not fits(row["size"], aligned["wide"], aligned["deep"]) for row in rows)
    return verdict("fits the plan", failing, len(rows), "rows",
                   {"rows past the rough model": past, **{name: len(ids) for name, ids in apart.items()}})
