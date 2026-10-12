"""A made ground written as the ground record tools/usd/ground.py reads (`ground.json` beside its pictures), with its
surfaces by zone and its rocks:

    <ground>/ground.json   side, low, span, radius, plan_out, places (each place's seat), dug, heights, skin, zones,
                           surfaces (each zone's library surface and its colour), rocks, the chosen picture
    <ground>/heights.png   sixteen bits in red and green: height = code / 65535 * span - low, metres
    <ground>/zones.png     each point's zone (an index into `surfaces`)
    <ground>/skin.png      each zone in its library surface's colour (the design token's), never a picture's colour
    <ground>/rocks.json    the rocks the plan's rule lays (rocks.py)

Every zone takes exactly one library surface: the plan's `zones` rules, first match wins, read on the plan's held
flats, paths, landforms, crater floors, water and slope.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

from score.stages.terrain import landforms, plan

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import ground as grounds  # noqa: E402


def heights_code(heights, low, span):
    """Heights as the record's sixteen-bit picture (red the high byte, green the low)."""
    code = np.clip(np.round((heights + low) / span * 65535), 0, 65535).astype(np.int64)
    pixels = np.zeros((*heights.shape, 3), dtype=np.uint8)
    pixels[..., 0], pixels[..., 1] = code >> 8, code & 255
    return Image.fromarray(pixels)


def decoded(path, low, span):
    """A record's heights picture back in metres."""
    pixels = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    return (pixels[..., 0] * 256 + pixels[..., 1]) / 65535.0 * span - low


def levelled(heights, record):
    """The plan's levelled yards (a box held at one height, eased back over its blend) laid on the heights; a yard
    with no height is held at the ground's mean height over its box; a yard `on_seat` is held `height` under the
    floor of the place it is for, its seat's flat plane (a room too long to stand on the ball's curve: the hangar)."""
    for level in record.get("levels", []):
        box = level["box"]
        height = level["height"]
        if level.get("on_seat"):
            height = seat_plane(record, record["seats"][level["for"]], heights.shape[0]) + height
        elif height is None:
            grid = landforms.Grid(record["side"], heights.shape[0])
            inside = (grid.x >= box[0]) & (grid.x <= box[2]) & (grid.z >= box[1]) & (grid.z <= box[3])
            height = float(heights[inside].mean())
        heights = grounds.levelled(heights, record["side"], np.array(box[:2]), np.array(box[2:]), height,
                                   level["blend"])
    return heights


def seat_plane(record, seat, points):
    """The height over the ball of a seat's flat plane (its tangent plane, where a room laid flat on it has its
    floor) at every point of the plan's grid."""
    grid = landforms.Grid(record["side"], points)
    plan = grounds.seat_frame(record["plan_out"], 0.0)
    toward = plan[1] * record["radius"] + grid.x[..., None] * plan[0] + grid.z[..., None] * plan[2]
    toward /= np.linalg.norm(toward, axis=-1, keepdims=True)
    out = np.asarray(seat["out"], dtype=float) / np.linalg.norm(seat["out"])
    return record["radius"] / (toward @ out) - record["radius"]


def dented(heights, record, folder, kits):
    """The plan's dents under thrown pieces, each made where the place's seat puts its spot on the plan."""
    for place, dents in record.get("dents", {}).items():
        on_seat = json.loads((pathlib.Path(kits) / f"{place}.json").read_text()).get("on_seat", [0.0, 0.0])
        laid = grounds.Ground(ground_fields(record, folder), record["seats"][place], on_seat)
        for dent in dents.values():
            heights = grounds.dented(laid, heights, dent["at"][0], dent["at"][1], dent["radius"], dent["depth"])
    return heights


def ground_fields(record, folder):
    """The fields tools/usd/ground.Ground reads, for this made ground in `folder`."""
    return {"radius": record["radius"], "side": record["side"], "low": record["low"], "span": record["span"],
            "folder": str(folder), "heights": "heights.png", "skin": "skin.png", "plan_out": record["plan_out"],
            **({"dug": record["dug"]} if record.get("dug") else {})}


def crater_floors(grid, craters):
    """Where a named crater's floor lies: within 0.3 of its diameter of its middle."""
    floor = np.zeros(grid.x.shape, dtype=bool)
    for crater in craters:
        if crater["kind"] == "small":
            continue
        stretch = crater.get("stretch", 1.0)
        floor |= np.hypot(grid.x - crater["x"], grid.z - crater["z"]) < 0.3 * crater["d"] * stretch
    return floor


def zone_masks(shaped, heights):
    """The masks the zone rules read, at the shaped plan's grid."""
    return {"held": shaped.held > 0.5, "path": shaped.on_path > 0.5,
            "water": shaped.land < 0 if shaped.land is not None else np.zeros(heights.shape, dtype=bool),
            "crater floor": crater_floors(shaped.grid, shaped.craters),
            "slope": plan.slopes(heights, shaped.grid.cell)}


def zones(shaped, record, heights):
    """Each point's zone index and the zones' surfaces in order: the plan's rules, first match wins."""
    masks = zone_masks(shaped, heights)
    surfaces = []
    found = np.full(heights.shape, -1, dtype=np.int64)
    for rule in record["zones"]:
        when = rule["when"]
        if when == "slope":
            hit = masks["slope"] > rule["over"]
        elif when == "landform":
            hit = shaped.masks[rule["name"]] > rule["over"]
        elif when == "else":
            hit = np.ones(heights.shape, dtype=bool)
        else:
            hit = masks[when]
        if rule["surface"] not in surfaces:
            surfaces.append(rule["surface"])
        found[(found < 0) & hit] = surfaces.index(rule["surface"])
    return found, surfaces


def named_surfaces(value):
    """Every library surface a plan names (each `surface` value, at any depth)."""
    if isinstance(value, dict):
        return {found for key, item in value.items()
                for found in ([item] if key == "surface" and isinstance(item, str) else named_surfaces(item))}
    if isinstance(value, list):
        return {found for item in value for found in named_surfaces(item)}
    return set()


def ground_surfaces(library):
    """The part of the library the grounds read, as text: each surface the plans (data/ground/plan, beside the
    library's folder) name, with its variant. Terrain's key hashes this, not the whole library, so a surface added
    for a model moves no ground."""
    plans = pathlib.Path(library).parents[1] / "ground" / "plan"
    named = set().union(*(named_surfaces(json.loads(path.read_text())) for path in sorted(plans.glob("*.json"))))
    variants = {name: variant for family in json.loads(pathlib.Path(library).read_text())["families"].values()
                for name, variant in family["variants"].items()}
    return json.dumps({name: variants.get(name) for name in sorted(named)}, sort_keys=True)


def surface_colours(surfaces, library, tokens):
    """Each library surface's colour, '#rrggbb', from its design token."""
    variants = {name: variant for family in json.loads(pathlib.Path(library).read_text())["families"].values()
                for name, variant in family["variants"].items()}
    colours = {entry["name"]: entry["value"]["ops"] if isinstance(entry["value"], dict) else entry["value"]
               for entry in json.loads(pathlib.Path(tokens).read_text())["color"]["tokens"]}
    missing = [surface for surface in surfaces if surface not in variants]
    if missing:
        raise ValueError(f"the library has no surface {', '.join(missing)}")
    return {surface: colours[variants[surface]["token"]][:7] for surface in surfaces}


def skin(found, surfaces, colours):
    """The zones painted each in its surface's colour."""
    palette = np.array([[int(colours[surface][index:index + 2], 16) for index in (1, 3, 5)] for surface in surfaces],
                       dtype=np.uint8)
    return Image.fromarray(palette[found])


def write(folder, record, shaped, heights, laid_rocks, picture, inputs):
    """The made ground's record and pictures into `folder`; the record."""
    folder.mkdir(parents=True, exist_ok=True)
    points = record["heights_points"]
    small = ndimage.zoom(heights, points / heights.shape[0], order=1) if points != heights.shape[0] else heights
    small = levelled(small, record)
    heights_code(small, record["low"], record["span"]).save(folder / "heights.png")
    if record.get("dents"):
        small = dented(small, record, folder, inputs["kits"])
        heights_code(small, record["low"], record["span"]).save(folder / "heights.png")
    found, surfaces = zones(shaped, record, heights)
    found = ndimage.zoom(found, points / found.shape[0], order=0) if points != found.shape[0] else found
    water = record.get("water")
    colours = surface_colours(surfaces + ([water["surface"]] if water else []), inputs["library"], inputs["tokens"])
    Image.fromarray(found.astype(np.uint8)).save(folder / "zones.png")
    skin(found, surfaces, colours).save(folder / "skin.png")
    (folder / "rocks.json").write_text(json.dumps(laid_rocks))
    written = {**ground_fields(record, "."), "ground": record["ground"], "zones": "zones.png",
               "surfaces": [{"surface": surface, "colour": colours[surface]} for surface in surfaces],
               "rocks": "rocks.json", "places": record["seats"], "picture": picture,
               "water": {**water, "colour": colours[water["surface"]]} if water else None}
    written.pop("folder")
    (folder / "ground.json").write_text(json.dumps(written, indent=1))
    return written


def read(folder):
    """A made ground's record, with its folder, as tools/usd/ground.Ground reads it."""
    return {**json.loads((pathlib.Path(folder) / "ground.json").read_text()), "folder": str(folder)}
