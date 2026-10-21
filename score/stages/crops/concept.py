"""crops-concept@<place>: how each crop kind grows on the concept (its patches and its spacing in plant widths),
measured with SAM 3 on one rented card.

SAM 3 (tools/props/scene/box_masks.py through tools/props/cloud/box_masks_cloud.py)
is asked for the plot on the whole concept view, and for every noun of every kind on TILES tiles of it, each tile
OVERLAP wider than its share and drawn UPSCALE times larger (small plants and plants that touch are found on the
close tiles; on the whole picture SAM 3 merged the bushes into a few boxes), each row keeping up to KEEP_PLANTS
instances. Free measures here, kept in concept.json:

    plot       the plot instance with the largest mask: its pixel box and its mask's area (`fills` of a row boxed
               over the whole picture is the mask's share of the picture)
    plants     every tile's instances mapped back onto the picture, centred in the plot's box, each the kind of its
               noun; where boxes overlap over SAME_PLANT (one plant found twice: on two tiles, or by two kinds'
               nouns) the earlier kind in the record's order keeps it (the more specific nouns first), within a
               kind the surest
    kinds      per kind: its patches (plants linked within LINK median spacings, at least PATCH_LEAST; strays left
               out and counted), their share of the plot (each patch's hull of centres widened by one spacing), and
               its spacing in plant widths: the median distance from a plant to its nearest neighbour over the
               median plant's width (its box's); a box over MERGED median widths is several plants SAM 3 merged
               into one mass, left out

The spacing is scale-free: the concept draws its plants larger than the plan's 12 m plot would hold them, so a
density in plants a square metre read off the plan's metres would lay them metres apart. The view looks down on the
floor at a slant, so distances across the picture's height are short by the plot's height over its width (a square
plot turned a quarter seen from above at a slant); centres are stretched back by that before measuring.
The gate `measured`: the plot found and every kind at least FOUND_LEAST plants in patches; else unknown, naming what
SAM 3 did not find (a kind's nouns are its inventory row's words; never typed as a count).
"""
import json
import math
import statistics

from score import checks
import score.stages.crops.crop_data as crop_data

KEEP_PLANTS = 400
KEEP_PLOT = 4
SAME_PLANT = 0.5
SAME_INSIDE = 0.7
SAME_CENTRE = 0.5
# A box over this many times its kind's median width is several plants SAM 3 merged into one mass.
MERGED = 2.5
FOUND_LEAST = 5
# A patch: plants linked within LINK times their kind's median nearest-neighbour distance, at least PATCH_LEAST.
LINK = 2.0
PATCH_LEAST = 4
# The tiles the plants are counted on: columns x rows, each this share wider than its part, drawn this many times
# larger.
TILES = (3, 2)
OVERLAP = 0.15
UPSCALE = 2
# SAM 3 on one L4: EUR 0.04 for 7 pictures in the ledger on 2026-10-12 (a minute to set up), rounded up.
EUROS = 0.5


def tile_boxes(size):
    """The tiles' boxes on the picture: TILES columns and rows, each widened by OVERLAP of its part, inside it."""
    columns, rows = TILES
    wide, tall = size[0] / columns, size[1] / rows
    found = []
    for row in range(rows):
        for column in range(columns):
            left, top = column * wide - OVERLAP * wide / 2, row * tall - OVERLAP * tall / 2
            found.append([max(0, round(left)), max(0, round(top)), min(size[0], round(left + wide * (1 + OVERLAP))),
                          min(size[1], round(top + tall * (1 + OVERLAP)))])
    return found


def plant_rows(record, size):
    """One row a noun of every kind, boxed over a whole tile of `size`."""
    return [{"key": f"{kind}:{noun}", "nouns": [noun], "box": [0, 0, *size], "keep": KEEP_PLANTS}
            for kind, entry in record["kinds"].items() for noun in entry["nouns"]]


def write_tiles(picture, out):
    """Each tile of the picture drawn UPSCALE times larger into out/tiles; [(path, box)]."""
    from PIL import Image
    image = Image.open(picture).convert("RGB")
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    found = []
    for number, box in enumerate(tile_boxes(image.size)):
        tile = image.crop(box)
        path = out / "tiles" / f"tile-{number}.png"
        tile.resize((tile.width * UPSCALE, tile.height * UPSCALE), Image.LANCZOS).save(path)
        found.append((path, box))
    return found


def jobs_of(record, picture, size, tiles):
    """box_masks.py's jobs: the plot's nouns on the whole picture (rows keyed plot:<noun>), then every kind's nouns
    on each tile (rows keyed <tile>/<kind>:<noun>)."""
    jobs = [{"picture": str(picture), "rows": [{"key": f"plot:{noun}", "nouns": [noun], "box": [0, 0, *size],
                                                "keep": KEEP_PLOT}
                                               for noun in record["concept"]["plot"]["nouns"]]}]
    for number, (path, box) in enumerate(tiles):
        tile_size = [(box[2] - box[0]) * UPSCALE, (box[3] - box[1]) * UPSCALE]
        jobs.append({"picture": str(path), "rows": [dict(row, key=f"{number}/{row['key']}")
                                                    for row in plant_rows(record, tile_size)]})
    return jobs


def on_picture(instances, tiles):
    """Every tile's plant instances with their boxes mapped back onto the whole picture, keyed <kind>:<noun>; the
    plot's rows as they are."""
    found = {key: list(listed) for key, listed in instances.items() if key.startswith("plot:")}
    for key, listed in instances.items():
        if "/" not in key:
            continue
        number, row = key.split("/", 1)
        left, top = tiles[int(number)][:2]
        found.setdefault(row, []).extend(
            dict(instance, box=[left + instance["box"][0] / UPSCALE, top + instance["box"][1] / UPSCALE,
                                left + instance["box"][2] / UPSCALE, top + instance["box"][3] / UPSCALE])
            for instance in listed)
    return found


def centre(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def overlap(first, second):
    """Two boxes' shared area over their union."""
    wide = min(first[2], second[2]) - max(first[0], second[0])
    tall = min(first[3], second[3]) - max(first[1], second[1])
    if wide <= 0 or tall <= 0:
        return 0.0
    shared = wide * tall
    area = (first[2] - first[0]) * (first[3] - first[1]) + (second[2] - second[0]) * (second[3] - second[1])
    return shared / (area - shared)


def inside(point, box):
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def the_plot(instances, size):
    """The plot: the plot rows' instance with the largest mask, with its area in pixels; None when none was found."""
    found = [dict(instance, area=instance["fills"] * size[0] * size[1])
             for key, listed in instances.items() if key.startswith("plot:") for instance in listed]
    return max(found, key=lambda instance: instance["area"]) if found else None


def within(first, second):
    """The share of the smaller box inside the other."""
    wide = min(first[2], second[2]) - max(first[0], second[0])
    tall = min(first[3], second[3]) - max(first[1], second[1])
    if wide <= 0 or tall <= 0:
        return 0.0
    smaller = min((box[2] - box[0]) * (box[3] - box[1]) for box in (first, second))
    return wide * tall / smaller


def same_plant(first, second):
    """Two boxes of one kind are one plant found twice: they share over SAME_PLANT of their union, the smaller lies
    over SAME_INSIDE inside the other (a plant cut by a tile's edge, found whole on the next tile), or their centres
    lie within SAME_CENTRE of the narrower's width (one plant boxed a little differently on two tiles)."""
    return (overlap(first, second) > SAME_PLANT or within(first, second) > SAME_INSIDE
            or math.dist(centre(first), centre(second)) < SAME_CENTRE * min(width(first), width(second)))


def width(box):
    return box[2] - box[0]


def merged(instance, found):
    """Whether an instance is several plants SAM 3 merged into one mass: over MERGED times its kind's median width."""
    return width(instance["box"]) > MERGED * statistics.median(width(other["box"]) for other in found)


def kept_kind(found):
    """A kind's instances without its merged masses."""
    return [instance for instance in found if not merged(instance, found)]


def plants_in(instances, plot_box, kinds):
    """Every kind's instances centred in the plot's box, each with its kind and noun, kind by kind in the crop data's
    order, surest first, its merged masses left out (`kept_kind`); one dropped
    where it is a plant of its kind kept before it (`same_plant`), or shares over SAME_PLANT with any plant kept
    before it (so a plant two kinds' nouns find is the earlier kind's)."""
    kept = []
    for kind in kinds:
        found = [{**instance, "kind": kind, "noun": key.split(":", 1)[1]}
                 for key, listed in instances.items() if key.split(":", 1)[0] == kind for instance in listed
                 if inside(centre(instance["box"]), plot_box)]
        found = sorted(kept_kind(found), key=lambda instance: -instance["score"])
        for instance in found:
            if not any(same_plant(instance["box"], other["box"]) if other["kind"] == kind
                       else overlap(instance["box"], other["box"]) > SAME_PLANT for other in kept):
                kept.append(instance)
    return kept


def nearest_distances(points):
    """Each point's distance to its nearest neighbour."""
    return [min(math.dist(point, other) for number, other in enumerate(points) if number != index)
            for index, point in enumerate(points)]


def patches(points):
    """The patches a kind's plants make: groups linked by centres within LINK times the kind's median distance to a
    nearest neighbour, each of at least PATCH_LEAST plants; lone plants and small groups (strays) are left out."""
    if len(points) < 2:
        return []
    reach = LINK * statistics.median(nearest_distances(points))
    groups, unseen = [], list(range(len(points)))
    while unseen:
        group, todo = [], [unseen.pop(0)]
        while todo:
            index = todo.pop()
            group.append(points[index])
            linked = [other for other in unseen if math.dist(points[index], points[other]) <= reach]
            unseen = [other for other in unseen if other not in linked]
            todo += linked
        groups.append(group)
    return [group for group in groups if len(group) >= PATCH_LEAST]


def hull_area(points):
    """The area of the convex hull of points (monotone chain), 0 for fewer than three."""
    points = sorted(set(points))
    if len(points) < 3:
        return 0.0

    def turn(origin, first, second):
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (second[0] - origin[0])

    def half(ordered):
        chain = []
        for point in ordered:
            while len(chain) >= 2 and turn(chain[-2], chain[-1], point) <= 0:
                chain.pop()
            chain.append(point)
        return chain[:-1]
    hull = half(points) + half(points[::-1])
    return abs(sum(hull[index][0] * hull[(index + 1) % len(hull)][1] - hull[(index + 1) % len(hull)][0] *
                   hull[index][1] for index in range(len(hull)))) / 2.0


def patch_area(points):
    """A patch's area from its plants' centres: the hull widened by one spacing, half a spacing round each edge plant
    (a square patch of n plants has sqrt(n) - 1 spacings across its hull); 0 for fewer than four plants."""
    hull = hull_area(points)
    if len(points) < 4 or hull <= 0:
        return 0.0
    across = math.sqrt(len(points))
    return hull * (across / (across - 1)) ** 2


def kind_measures(plants, kinds, plot):
    """{kind: plants in its patches, patches, strays, the patches' share of the plot, its spacing in plant widths
    (None when not measurable)}."""
    slant = (plot["box"][3] - plot["box"][1]) / (plot["box"][2] - plot["box"][0])
    found = {}
    for kind in kinds:
        own = [plant for plant in plants if plant["kind"] == kind]
        floor = [(centre(plant["box"])[0], centre(plant["box"])[1] / slant) for plant in own]
        grouped = patches(floor)
        members = [point for group in grouped for point in group]
        widths = [plant["box"][2] - plant["box"][0] for plant, point in zip(own, floor) if point in members]
        share = sum(patch_area(group) for group in grouped) * slant / plot["area"]
        spacing = (statistics.median(nearest_distances(members)) / statistics.median(widths)
                   if len(members) >= PATCH_LEAST else None)
        found[kind] = {"count": len(members), "patches": len(grouped), "strays": len(own) - len(members),
                       "share": round(share, 4), "spacing": round(spacing, 3) if spacing else None,
                       "width_px": round(statistics.median(widths), 1) if widths else None}
    return found


def measures(record, instances, size):
    """concept.json's content from SAM 3's instances (on the whole picture)."""
    plot = the_plot(instances, size)
    if plot is None:
        return {"plot": None, "plants": [], "kinds": {}}
    plants = plants_in(instances, plot["box"], record["kinds"])
    return {"plot": plot, "plants": plants, "kinds": kind_measures(plants, record["kinds"], plot)}


def make_concept(inputs, out, seed, params):
    """SAM 3 on the concept view and its tiles on one rented card; concept.json with the plot and every kind's
    patches and spacing."""
    from PIL import Image
    record = crop_data.read(inputs)
    size = list(Image.open(inputs["concept"]).size)
    tiles = write_tiles(inputs["concept"], out)
    jobs = jobs_of(record, inputs["concept"], size, tiles)
    (out / "jobs.json").write_text(json.dumps(jobs, indent=1))
    with crop_data.tools("props/cloud", "props"):
        import box_masks_cloud
        box_masks_cloud.mask(out / "jobs.json", out / "instances.json")
    instances = on_picture(json.loads((out / "instances.json").read_text()), [box for _, box in tiles])
    found = measures(record, instances, size)
    (out / "concept.json").write_text(json.dumps(dict(found, size=size), indent=1))


def concept_faults(folder):
    return [] if (folder / "concept.json").exists() else ["no concept.json"]


def judge_measured(output, inputs, evidence):
    """The plot was found and every kind has at least FOUND_LEAST plants in patches on it and a spacing."""
    found = json.loads((output / "concept.json").read_text())
    kinds = crop_data.read(inputs)["kinds"]
    if found["plot"] is None:
        return checks.Verdict("measured", checks.UNKNOWN, "SAM 3 found no plot on the concept")
    short = [f"{kind}: {found['kinds'][kind]['count']} plants in patches" for kind in kinds
             if found["kinds"][kind]["count"] < FOUND_LEAST or found["kinds"][kind]["spacing"] is None]
    spacings = {f"{kind} spacing": found["kinds"][kind]["spacing"] or 0.0 for kind in kinds}
    reason = (f"{len(short)} of {len(kinds)} kinds under {FOUND_LEAST} plants: {', '.join(short)}" if short
              else f"{len(found['plants'])} plants of {len(kinds)} kinds on the plot")
    return checks.Verdict("measured", checks.UNKNOWN if short else checks.PASS, reason,
                          {"plants": len(found["plants"]), **spacings}, findings=tuple(short))


CHECKS = (checks.Check("measured", judge_measured),)
