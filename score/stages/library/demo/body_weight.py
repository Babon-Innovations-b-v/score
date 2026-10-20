"""A body's weight and material at work in the habitat: the trial's bodies where they stand, each weighed as
`tools/usd/physics.write_masses` weighs it (its drawn surface's area times its material's sheet times its density:
props are hollow shells), with its material's friction and bounce. Each body's area is its recorded mass over the
recorded sheet and density; the slider weighs the same surfaces at another sheet thickness."""
import json

from score.stages.library.demo import _trial

ALGORITHM = "body_weight"
SHEETS_MM = (1.0, 1.5, 2.0, 3.0)  # the slider's sheets; the materials record's own is among them
DOT = 0.12  # a body's dot, metres wide a kilogram to the third
NEAR = 1.5  # metres east or west: a body this close to one listed before it has its words a line lower
LINE = 0.45  # metres between those lines
BELOW = 0.6  # metres from a dot's middle down to its words: clear of the heaviest dot


def ranks(starts):
    """{body: how many bodies listed before it stand within NEAR}, so their words do not overlap."""
    names = list(starts)
    return {name: sum(abs(starts[name][0] - starts[other][0]) < NEAR
                      for other in names[:index]) for index, name in enumerate(names)}


def weighed(name, point, kilograms, rank):
    """The body's dot sized by its weight, and its weight in words beside it."""
    east, north = _trial.plan_point(point[0], point[2])
    wide = round(DOT * kilograms ** (1 / 3), 2)
    return [{"kind": "dots", "points": [[east, north]], "r": wide, "tone": "c1",
             "id": name, "label": f"{_trial.said(name)}, {kilograms:.1f} kg"},
            {"kind": "text", "points": [[east, round(north - BELOW - LINE * rank, 2)]], "tone": "c1",
             "id": f"{name}-kg", "label": f"{_trial.said(name).rstrip(' 0123456789')} {kilograms:.1f} kg"}]


def made(inputs):
    ran, the_record, the_scene = _trial.trial(inputs), _trial.record(inputs), _trial.scene(inputs)
    material = json.loads((inputs.repo / "data/physics/materials.json").read_text())["materials"][the_record["material"]]
    starts = {name: _trial.track(body)[0] for name, body in ran["bodies"].items()}
    rank = ranks(starts)
    areas = {name: body["mass"] / (material["sheet"] * material["density"]) for name, body in ran["bodies"].items()}
    sheets = [sheet / 1000 for sheet in SHEETS_MM]
    at = min(range(len(sheets)), key=lambda index: abs(sheets[index] - material["sheet"]))
    return {
        "example": f"the {_trial.PLACE}'s trial bodies, all {the_record['material']}",
        "view": "plan", "bounds": _trial.plan_bounds(the_scene),
        "steps": [
            {"label": "The bodies the trial moves, where they stand",
             "shapes": [_trial.floor(the_scene),
                        *[{"kind": "dots", "points": [_trial.plan_point(point[0], point[2])], "r": 0.15,
                           "tone": "base", "id": name, "label": f"{_trial.said(name)}, {areas[name]:.2f} m² of surface"}
                          for name, point in starts.items()]]},
            {"label": f"Each weighed: its surface times a {material['sheet'] * 1000:g} mm sheet of "
                      f"{the_record['material']} at {material['density']:g} kg/m³",
             "shapes": [shape for name, point in starts.items()
                        for shape in weighed(name, point, ran["bodies"][name]["mass"], rank[name])]}],
        "slider": {"label": "sheet", "unit": "mm", "values": list(SHEETS_MM), "at": at,
                   "shapes": [[shape for name, point in starts.items()
                               for shape in weighed(name, point, areas[name] * sheet * material["density"], rank[name])]
                              for sheet in sheets]},
        "numbers": [
            {"label": "density", "value": round(material["density"]), "unit": "kg/m³", "tip": "its material's density"},
            {"label": "sheet", "value": material["sheet"] * 1000, "unit": "mm",
             "tip": "the sheet a made thing of it is formed from (an assumption, not measured)"},
            {"label": "friction", "value": material["static"], "unit": "",
             "tip": f"static against itself; sliding {material['dynamic']}"},
            {"label": "bounce", "value": material["restitution"], "unit": "", "tip": "restitution"}]}
