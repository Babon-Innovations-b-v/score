"""What rough-model@<place> reads off plan@<place>: the plan's place name alone (__init__.py's make and gates read
`plan.json`'s `place`; the concept and inventory it is made from are its own declared files). The carry's content
rule for its plan input (score/stages/surfaces/carry.py): a plan written again (8b4011f0, #72) keeps the rough model.
What rough-align@<place> reads off it (ALIGN_RULES): its place and its floor, the floor's height and the walls' height
(shapes_first/align.py plan_box): the square's plan redrawn without 16 surplus items (2026-11-07) moves neither.
Framework (score/graph/_code.py FRAMEWORK): no row reads it, so no key moves by it.
"""


def plan_place(store, record):
    """The content of the plan output `record` made, as rough-model reads it: its place."""
    plan = store.read_file(record["output"], "plan.json")
    if plan is None:
        raise ValueError(f"output {record['output'][:12]} has no plan.json")
    return {"place": plan["place"]}


# {input stage: its content rule}.
RULES = {"plan": plan_place}


def plan_floor(store, record):
    """The content of the plan output `record` made, as rough-align reads it: its place, floor, floor height and walls'
    height (align.plan_box)."""
    plan = store.read_file(record["output"], "plan.json")
    if plan is None:
        raise ValueError(f"output {record['output'][:12]} has no plan.json")
    return {"place": plan["place"], "floor": plan["floor"], "floor_height": plan["floor_height"],
            "walls high": (plan.get("walls") or {}).get("high")}


# rough-align's {input stage: its content rule}; the rough model it reads is carried whole or made again.
ALIGN_RULES = {"plan": plan_floor}
