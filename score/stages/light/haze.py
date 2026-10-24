"""Which of a place's lamps light a shaft of haze (`shafted_kinds`: a glowing row its plan aims, the library's aimed
lamp), whose heads the light row measures. The paid light-haze row that rendered the place with its shafts off was
retired on 2026-10-22: it applied nowhere, since a design lays no kit piece.
"""
import json
import pathlib

import score.stages.light.passes as passes  # this form: the code version then leaves __init__ out

LAMPS = passes.REPO / "data/library/lamps.json"


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def glowing(inventory_path):
    """The ids of an inventory's rows whose row kind glows (score/stages/row_kinds.py): its lamps."""
    import score.stages.row_kinds as row_kinds  # by its package name: score/stages on sys.path would shadow tools
    return {row["id"] for row in row_kinds.rows_that(read(inventory_path), "glows", row_kinds.table())}


def shafted_rows(place):
    """The rows of the place whose lamps light a shaft of haze (its floodlights): each inventory row whose row kind
    glows that the place's plan aims (`aims`), the library's aimed lamp, when that lamp has a shaft
    (data/library/lamps.json), as the scene-record row lights them (scene_record/kit_shell)."""
    plan = passes.plan_of(place)
    inventory = passes.KEPT / "inventory" / f"{place}.json"  # the design's scene inventory
    if not plan or not plan.get("aims") or not inventory.is_file() or not read(LAMPS)["aimed"].get("shaft"):
        return set()
    return glowing(inventory) & set(plan["aims"])


def shafted_kinds(place, kit):
    """The kit kinds `kit` lays (the place's design kit, earth_seed's kit.json) of its shafted rows, each laid as
    `<room>_<row>`."""
    kinds = {f"{kit.get('room', place)}_{row}" for row in shafted_rows(place)}
    return kinds & {laid["kind"] for laid in kit["pieces"]}
