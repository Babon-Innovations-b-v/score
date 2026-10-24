"""props-inputs@<place>'s gate `fits the plan` (#41): every row the place's plan stands on its floor fits the floor the
rough model was registered to, turned or not; how many fit no footprint of the aligned rough model is measured.

Held to the floor are the rows the place stands on it. Counted, never held: a row of a layer that lies round the
floor (align.ROUND: a terrain detail area), the rows the kept plan names its `structure` (its own shell, floors,
roofs, ground: laid as the plan's walls, levels and roofs, never as an item at the row's metres) and its `beyond`
(seen through a window or past its edge: they stand in another place, plan_writing.py). Rows of a layer no place owns
(align.NO_PLACE) are held to no plan. Unknown without a registration: the loop splits a place's parts only once its
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


def off_floor(inputs):
    """{list name: set of row ids} the kept plan never stands on its floor (NOT_ON_FLOOR); empty lists without one."""
    path = inputs.get(KEPT_PLAN)
    plan = json.loads(pathlib.Path(path).read_text()) if path else {}
    return {name: set(plan.get(name) or []) for name in NOT_ON_FLOOR}


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
    lists = {"rows round the floor": {row["id"] for row in split if row.get("layer") in align.ROUND},
             **{f"rows of the plan's {name}": ids for name, ids in off_floor(inputs).items()}}
    apart, counted = {}, set()
    for name, ids in lists.items():  # a row in two lists counted in the first
        apart[name] = {row["id"] for row in split} & ids - counted
        counted |= apart[name]
    rows = [row for row in split if row["id"] not in counted]
    plan, aligned = found["plan"], found["aligned"]
    failing = [f"{row['id']}: {row['size'][0]} by {row['size'][1]} m fits no way on the {plan['wide']:.2f} by "
               f"{plan['deep']:.2f} m floor" for row in rows if not fits(row["size"], plan["wide"], plan["deep"])]
    past = sum(not fits(row["size"], aligned["wide"], aligned["deep"]) for row in rows)
    return verdict("fits the plan", failing, len(rows), "rows",
                   {"rows past the rough model": past, **{name: len(ids) for name, ids in apart.items()}})
