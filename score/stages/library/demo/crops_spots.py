"""Crops on beds: the greenhouse's beds, shared out between its crops, each crop's measured spacing, then the plants
laid on them by `score.stages.crops.layer` (the recorded laying at the measured spacing; the slider lays them again
with the same code at other spacings)."""
import json

from score.stages.crops import layer

ALGORITHM = "crops_spots"
PLACE = "greenhouse"
SCALES = (0.6, 0.8, 1.0, 1.3, 1.6)  # the slider: times the measured spacing; 1.0 is the recorded laying


def plan_point(east, south):
    return [round(east, 2), round(-south, 2)]


def bed_outline(bed):
    (east, _, south), (wide, _, deep) = bed["centre"], bed["size"]
    return [plan_point(east + dx * wide / 2, south + dz * deep / 2) for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def plants(spots, widths, tones):
    """One dots shape a crop: each plant a dot its model's width."""
    found = []
    for kind, tone in tones.items():
        own = [plan_point(spot["at"][0], spot["at"][2]) for spot in spots if spot["kind"] == kind]
        found.append({"kind": "dots", "points": own, "r": round(widths[kind], 3), "tone": tone,
                      "label": f"{kind}: {len(own)} plants"})
    return found


def made(inputs):
    laid = inputs.json(f"layer/crops.{PLACE}@1", "spots.json")
    record = json.loads((inputs.repo / "data/crops" / f"{PLACE}.json").read_text())
    scene = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())
    beds = layer.beds_of(scene, record["beds"])
    tones = {kind: f"c{rank + 1}" for rank, kind in enumerate(laid["beds"])}
    tone_of_bed = {name: tones[kind] for kind, names in laid["beds"].items() for name in names}
    kind_of_bed = {name: kind for kind, names in laid["beds"].items() for name in names}
    corners = [point for bed in beds for point in bed_outline(bed)]
    xs, ys = [point[0] for point in corners], [point[1] for point in corners]
    variants = [laid["spots"] if scale == 1.0 else layer.laid_spots(
        beds, laid["beds"], {kind: spacing * scale for kind, spacing in laid["spacings"].items()}, 0)
        for scale in SCALES]
    first_bed = {kind: next(bed for bed in beds if bed["name"] == names[0]) for kind, names in laid["beds"].items()}
    return {
        "example": f"the {PLACE}'s {len(beds)} beds",
        "view": "plan", "bounds": [min(xs) - 0.6, min(ys) - 0.6, max(xs) + 0.6, max(ys) + 0.6],
        "steps": [
            {"label": "The beds, from the place's plan",
             "shapes": [{"kind": "area", "points": bed_outline(bed), "tone": "ground", "id": bed["name"],
                         "label": bed["name"]} for bed in beds]},
            {"label": "Each crop gets whole beds, by its share of the concept's plot",
             "shapes": [{"kind": "area", "points": bed_outline(bed), "tone": tone_of_bed[bed["name"]],
                         "id": bed["name"], "label": kind_of_bed[bed["name"]]} for bed in beds]},
            {"label": "Each crop's spacing, measured off the concept",
             "shapes": [{"kind": "text", "points": [plan_point(bed["centre"][0], bed["centre"][2] - 0.45)],
                         "tone": tones[kind], "label": f"{kind} {laid['spacings'][kind]:.2f} m apart"}
                        for kind, bed in first_bed.items()]},
            {"label": "Plants laid on a grid of each bed, moved a little within their cells",
             "shapes": plants(laid["spots"], laid["widths"], tones)}],
        "slider": {"label": "spacing", "unit": "x measured", "values": list(SCALES), "at": SCALES.index(1.0),
                   "shapes": [plants(spots, laid["widths"], tones) for spots in variants]},
        "numbers": [{"label": "plants", "value": len(laid["spots"]), "unit": "", "tip": "plants laid at the "
                     "measured spacing"},
                    {"label": "beds", "value": len(beds), "unit": "", "tip": "the place's beds"}]}
