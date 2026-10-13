"""The framework's half of a place's surface line, after the method's parts (PARTS in __init__.py: per model its
parts, each with the library surface the method named for it): every part painted from its surface alone, baked and
checked. Never a picture's colours: a part the method named nothing for takes the surface of the part it borders
most, else it stays unnamed and the gate fails. A new library surface the method proposed for a part goes into the
finish registry (registry.py) as proposed, for the owner; until he accepts it, the part keeps the nearest library
surface the method named.

Rows (place grain, surfaces-<step>@<place>):
    paint   (free)  per part its surface (the method's, else the bordering part's), the labelled folder written
                    (labels.write_parts) and its gate: one surface a part
    bake    (paid)  the labelled folders baked onto the place's made models (library_bake.py make_chunky), each by
                    the entry the place's data names (data/surfaces/<place>.json `bake`); the models the place lays
                    that another place claims (its data's `elsewhere`) named in elsewhere.json, read from that place's
                    bake: each model is painted once world-wide
    check   (free)  the baked models: every part's baked base colour lies on its library surface (CIE76 under
                    BAKE_DELTA_E, no near-black blotch), every map there, triangles within the job's budget
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", PROPS / "cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import surface_gates as gates  # noqa: E402
import prop_env  # noqa: E402

# A baked part lies on its surface when its median base colour is within BAKE_DELTA_E (CIE76) of the surface's
# colour: the bake's wear and dirt (0.4 each) move a surface's colour, a wrong surface moves it far more. A part
# whose surface is not dark (L* over DARK_SURFACE) fails with over BLOTCH_SHARE of its area under BLOTCH_L (the
# black blotches of round six). Parts under PART_LEAST of the model are not judged.
BAKE_DELTA_E = 20.0
DARK_SURFACE, BLOTCH_L, BLOTCH_SHARE = 35.0, 12.0, 0.05
PART_LEAST = 0.01
PART_POINTS = 60000  # labelled points kept per model to name each baked triangle (export.PART_POINTS)
CLASSES = "gpu-24gb,gpu-48gb,gpu-80gb"
BAKE_EUROS = 2.0
# Two neighbouring parts of one surface join only when their colours lie within this (Lab) (MaPa's merge: same class
# and same unlit colour, its CIE threshold 2 on albedo is too fine for a picture's).
MERGE_COLOUR = 12.0
# A take's feet in its own frame (feet.py), levelled only when a row lays it loose on the floor or held
# (stands_on_feet): found within FOOT_BAND of its height over its lowest point, points within FOOT_LINK of its
# footprint's diagonal one foot. In shares of its size (its height or its footprint's diagonal, the larger: a pallet's
# feet are measured against its width, not its few centimetres of height), a foot may stand FOOT_TOLERANCE over the
# lowest and count as down (a hundredth: 2.3 cm on the water tank, inside the resting check's 3 cm), and a short leg
# is stretched down FOOT_MOST at most (a tenth: the water tank's shortest leg ends 6.4% of its size up); a foot further
# up is a missing leg, a fault of the model, and fails the gate "feet in one plane" by name.
FOOT_BAND, FOOT_TOLERANCE, FOOT_MOST, FOOT_LINK = 0.15, 0.01, 0.1, 0.03
# A base that slopes as one piece (flattened_base): its bottom BASE_BAND of height, each footprint quadrant brought
# down level when over FOOT_TOLERANCE of its size up, refused over BASE_MOST (the rack's legs: 7.4% of its size).
BASE_BAND, BASE_MOST = 0.25, 0.15
# The paint runs on processor machines, a job a take of about PAINT_MINUTES (campgrounds, 2026-10-12: twelve takes,
# eight machines of 3.3 to 4.7 min each for EUR 5.83 at 5; a job about 1.5 min, crane-r1 alone 34.8 GB at its peak); the
# keys of a take's listing besides the make's inputs (prop_env.short reads each as a path: the take is its name); the
# repository folders its code and data come from.
PAINT_CLASSES = "cpu-32c-128gb,cpu-32c-64gb,cpu-32c-256gb,cpu-16c-64gb"
PAINT_MINUTES, PAINT_EUROS = 2, 0.5
TAKE, RECORDS, HOME, CODE = "paint take", "paint records", "props home", "paint repo"
PAINT_REPO = ("score", "tools/props", "data/library", "data/definitions", "design/tokens", "data/checks",
              "data/inventory")


def data_of(inputs):
    return json.loads(inputs["surfaces"].read_text())


# --- paint ---------------------------------------------------------------------------------------------------------

def method_surfaces(take, place, rows, registry):
    """Each part's record with the surface the method named for it; a new library surface the method proposed for a
    part goes into the registry as proposed (the standing proposal of its name is recorded on the part), the part
    keeping the method's nearest library surface meanwhile."""
    found = []
    for row in rows:
        record = dict(row)
        if row["judge"]:
            record.update(surface=row["judge"], by="the method")
        if row.get("proposed"):
            spec = {**row["proposed"], "status": "proposed", "stands_in": row["judge"]}
            standing = registry.propose_surface(row["proposed"]["name"], spec,
                                                {"line": place, "take": take, "part": row["part"]})
            record["proposed"] = standing["spec"]
        found.append(record)
    return found


def bordered(mesh, part_of, records, names):
    """Each part's index into `names` (appended to as needed), a part with no surface taking the one of the part it
    borders most; -1 where none does."""
    import numpy as np
    import labels
    chosen = np.full(len(records), -1)
    for record in records:
        if record.get("surface"):
            if record["surface"] not in names:
                names.append(record["surface"])
            chosen[record["part"]] = names.index(record["surface"])
    shared = labels.borders(mesh, part_of, len(records))
    for part in np.nonzero(chosen < 0)[0]:
        known = np.nonzero(chosen >= 0)[0]
        if len(known) and shared[part, known].max() > 0:
            chosen[part] = chosen[known[np.argmax(shared[part, known])]]
            records[part].update(surface=names[chosen[part]], by="the part it borders most")
    return chosen


def colour_joined_parts(mesh, part_of, chosen, colours):
    """labels.joined_parts with MaPa's second condition: neighbouring parts join where one surface is named for both
    and their colours (labels.part_colour, Lab) lie within MERGE_COLOUR; parts with too few seen faces for a colour
    (every part of a method that measures none) join on the surface alone."""
    import numpy as np
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    import labels
    count = len(chosen)
    seen = ~np.isnan(colours[:, 0])
    part_colours = np.full((count, 3), np.nan)
    for part in range(count):
        members = (part_of == part) & seen
        if members.sum() >= labels.SEEN_LEAST:
            part_colours[part] = labels.part_colour(colours[members])
    pairs = mesh.face_adjacency
    first, second = part_of[pairs[:, 0]], part_of[pairs[:, 1]]
    gap = np.linalg.norm(part_colours[first] - part_colours[second], axis=1)
    near = np.isnan(gap) | (gap <= MERGE_COLOUR)
    same = (first != second) & (chosen[first] == chosen[second]) & near
    links = sparse.coo_matrix((np.ones(same.sum()), (first[same], second[same])), shape=(count, count))
    return connected_components(links + links.T, directed=False)[1][part_of]


def finished_frame(mesh, take):
    """The raw model laid on its finished model (labels.onto_finished, seeded as labels.py seeds it); the matrix,
    the median gap and the finished model's bounds."""
    import numpy as np
    import trimesh
    import labels
    np.random.seed(0)
    final = trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh")
    matrix, gap = labels.onto_finished(mesh.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                       labels.finish_turn(take))
    return matrix, gap, final.bounds


def stands_on_feet(entry, inventory, rules_file):
    """Whether a row of the take's own place lays its kind loose on the floor or held on another row, as the resting
    triage reads the same data (data/checks/resting.json): not fixed, not on a wall or ceiling, not hanging by its
    words, not of a class that may bed in (cable, cloth, debris). Only such a take has feet to level: a glove that
    hangs, a wall panel or a fragment thrown on the ground is left as made."""
    rules = json.loads(pathlib.Path(rules_file).read_text())
    rows = json.loads(pathlib.Path(inventory).read_text())["rows"] if inventory and pathlib.Path(inventory).exists() \
        else []
    loose_words = set(rules["hanging"]) | {word for bedding in rules["may_bed"] for word in bedding["words"]}
    return any(row.get("thing") == f"prop:{entry['kind']}" and not row.get("fixed")
               and row.get("support") in (None, "floor", "held")
               and (row.get("anchor", "") in ("floor", "ground", "") or row.get("anchor", "").startswith("on:"))
               and not row_words(row) & loose_words for row in rows)


def row_words(row):
    """A row's id and name as a set of lower-case words (as tools/usd/triage.py words_of reads them)."""
    text = f"{row.get('id', '')} {row.get('name', '')}".lower().replace("_", " ")
    return set("".join(letter if letter.isalnum() else " " for letter in text).split())


def levelled_feet(vertices, faces):
    """A take's vertices on its finished model (+y up, its own frame) with its feet brought onto one level plane
    (feet.level: FOOT_BAND of its height, FOOT_LINK of its footprint, FOOT_TOLERANCE and FOOT_MOST of its size), and
    what was done, each gap as a share of its size."""
    import feet
    height, diagonal = feet.model_scale(vertices)
    size = max(height, diagonal)
    points, record = feet.level(vertices, faces, FOOT_BAND * height, FOOT_LINK * diagonal, FOOT_TOLERANCE * size,
                                FOOT_MOST * size)
    points, base = flattened_base(points, BASE_BAND * height, FOOT_TOLERANCE * size, BASE_MOST * size)
    record["refused"] = record["refused"] + base["refused"]
    shares = {key: [round(gap / size, 4) for gap in record[key]] for key in ("gaps", "levelled", "refused")}
    return points, {"feet": record["feet"], **shares,
                    "base": [round(gap / size, 4) for gap in base["quadrants"]],
                    "flattened": [round(gap / size, 4) for gap in base["flattened"]]}


def flattened_base(points, band, tolerance, most):
    """A take's vertices with its base brought down level where it slopes as one piece (the hangar's parts rack stood
    on a middle part, its legs 22 cm up; the shelving's one side 10 cm short; the paint's legs check found one foot
    and passed them): each footprint quadrant of the bottom `band` whose lowest point lies over `tolerance` above the
    lowest is brought down, the drop spread over the footprint by inverse squared distance from the quadrants' lowest
    points (each of them comes down its whole gap) and faded over the band (one at the band's top moves none). Never by tipping the model. A quadrant over
    `most` up is a fault of the model: nothing moves and its gap comes back refused. Returns (vertices, {"quadrants":
    each quadrant's gap, "flattened": the gaps brought down, "refused": ...})."""
    import numpy as np
    points = np.array(points, dtype=np.float64)
    low = points[:, 1].min()
    base = points[points[:, 1] <= low + band]
    middle = (base.min(axis=0) + base.max(axis=0)) / 2
    gaps, places = np.zeros(4), np.zeros((4, 2))
    sides = [(x_side, z_side) for x_side in (base[:, 0] < middle[0], base[:, 0] >= middle[0])
             for z_side in (base[:, 2] < middle[2], base[:, 2] >= middle[2])]
    for number, (x_side, z_side) in enumerate(sides):
        chosen = base[x_side & z_side]
        lowest = chosen[chosen[:, 1].argmin()] if len(chosen) else np.array([middle[0], low, middle[2]])
        gaps[number], places[number] = lowest[1] - low, lowest[[0, 2]]
    record = {"quadrants": [float(gap) for gap in gaps], "flattened": [], "refused": []}
    if gaps.max() <= tolerance:
        return points, record
    if gaps.max() > most:
        record["refused"] = [float(gap) for gap in gaps if gap > most]
        return points, record
    drops = np.where(gaps > tolerance, gaps, 0.0)
    distance = ((points[:, None, [0, 2]] - places[None]) ** 2).sum(axis=2)
    weights = 1.0 / np.maximum(distance, 1e-12)
    drop = (weights * drops).sum(axis=1) / weights.sum(axis=1)
    fade = np.clip((low + band - points[:, 1]) / np.maximum(band - drop, 1e-9), 0.0, 1.0)  # a quadrant's low: all
    points[:, 1] -= drop * fade
    record["flattened"] = [float(gap) for gap in drops if gap > 0]
    return points, record


def paint_take(inputs, out, take, record, records):
    """One take painted from its part records (method_surfaces): each part's surface, the labelled folder and
    faces.npz, its report."""
    import numpy as np
    import labels
    import patchy
    import split_compare
    import stored_parts
    entry = data_of(inputs)["takes"][take]
    part_of = np.load(inputs["parts"] / take / "parts.npy").astype(int)
    colours = np.load(inputs["parts"] / take / "colours.npy")
    mesh = split_compare.raw_model(take)
    names = list(labels.allowed_materials(entry["library_places"][0], entry["kind"], []))
    chosen = bordered(mesh, part_of, records, names)
    unnamed = [part for part in range(len(records)) if chosen[part] < 0]
    safe = np.where(chosen < 0, 0, chosen)
    painted_parts = colour_joined_parts(mesh, part_of, safe, colours)
    painted = safe[part_of]
    folder = out / "labelled" / take
    folder.mkdir(parents=True)
    np.savez_compressed(folder / "faces.npz", surface=painted.astype(np.int16), part=part_of.astype(np.int32),
                        painted_part=painted_parts.astype(np.int32), names=np.array(names))
    matrix, gap, bounds = finished_frame(mesh, take)
    order = sorted({names[index] for index in np.unique(painted)})
    face_labels = np.array([order.index(name) if name in order else -1 for name in names])[painted]
    moved = mesh.copy()
    moved.apply_transform(matrix)
    levelled = {"skipped": "no floor or held row of its place lays its kind"}
    if stands_on_feet(entry, inputs.get(f"inventory {entry['place']}"), inputs["resting rules"]):
        moved.vertices, levelled = levelled_feet(moved.vertices, moved.faces)
    shares, _ = labels.write_parts(moved, face_labels, order, part_of, painted_parts, bounds, folder)
    kept, kept_labels, _, kept_parts = patchy.labelled_parts(folder)
    report = {"take": take, "method": record["method"], "kind": entry["kind"], "parts": records, "shares": shares,
              "judge_unknown": record["judge_unknown"], "unnamed_parts": unnamed,
              "finishes": record.get("finishes", []),
              "unnamed_share": round(sum(row["share"] for row in records if row["part"] in unnamed), 4),
              "painted_parts": int(painted_parts.max()) + 1, "upright_gap": round(gap, 4), "feet": levelled,
              "patchy": patchy.score(kept, kept_labels, kept_parts, patchy.labelled_regions(folder, kept))}
    stored_parts.write(folder, take, target=folder)
    (folder / "labels.json").write_text(json.dumps(report, indent=1))
    return report


def make_paint(inputs, out, seed, params):
    """Every take painted on rented processor machines, one job a take spread over them (blender_cloud.py,
    inside/paint_take.py: most takes peak at 1.5 to 3.4 GB, campgrounds' crane-r1 at 34.8 GB, past the PC's 14 GB cap,
    2026-10-12; heavy steps run in the cloud); the method's proposals go into the finish
    registry here first. painted.json (with the takes the method left out)."""
    from registry import Registry
    from score.store import Store
    short = prop_env.short(inputs)
    data = data_of(short)
    method = json.loads((short["parts"] / "parts.json").read_text())
    registry = Registry(Store.default())
    jobs = [paint_job(inputs, short, out, take,
                      method_surfaces(take, data["takes"][take]["place"], record["parts"], registry))
            for take, record in method["takes"].items()]
    done = subprocess.run([str(prop_env.PROPS_PYTHON), str(PROPS / "cloud/blender_cloud.py"), *map(str, jobs), "--who",
                           f"surfaces-paint-{data['place']}", "--classes", PAINT_CLASSES], cwd=REPO,
                          capture_output=True, text=True)
    (out / "paint.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py paint failed: {done.stderr[-3000:]}")
    for path in out.glob(".paint-*"):
        path.unlink()
    found = {take: json.loads((out / "labelled" / take / "labels.json").read_text()) for take in method["takes"]}
    (out / "painted.json").write_text(json.dumps({"takes": found, "left_out": method["left_out"]}, indent=1))


def paint_job(inputs, short, out, take, records):
    """One take's cloud job file: its listing (the make's inputs, the take, its part records, PROPS_HOME) and every
    file the paint reads at its own path (the repository's code and data it imports and reads, the take's raw,
    finished and turned models, its parts); its labelled folder comes back."""
    listing, kept = out / f".paint-{take}.json", out / f".paint-{take}-records.json"
    kept.write_text(json.dumps(records))
    listing.write_text(json.dumps({**{name: str(path) for name, path in inputs.items()}, TAKE: take,
                                   RECORDS: str(kept), HOME: str(prop_env.PROPS_HOME), CODE: str(REPO)}))
    pixal = prop_env.PROPS_HOME / "work/pixal"
    models = sorted({pixal / f"{take}.glb", pixal / f"{take}-final.glb", *pixal.glob(f"{take}-[0-9]*.glb")})
    inventories = [path for name, path in short.items() if name.startswith("inventory ")]
    read = [listing, kept, short["surfaces"], short["parts"] / "parts.json", short["parts"] / take,
            short["resting rules"], *inventories, *models, *(REPO / folder for folder in PAINT_REPO)]
    job = out / f".paint-{take}-job.json"
    job.write_text(json.dumps({"script": "score/stages/surfaces/inside/paint_take.py", "args": [str(listing)],
                               "inputs": [str(path) for path in read], "outputs": [str(out / "labelled" / take)],
                               "minutes": PAINT_MINUTES}, indent=1))
    return job


def paint_take_step(inputs, out):
    """On the rented machine (inside/paint_take.py hands it here): one take painted (paint_take) from its listing's
    take and part records."""
    import heavy
    heavy.refuse_here("the surface stage's paint")
    take = inputs[TAKE].name
    record = json.loads((inputs["parts"] / "parts.json").read_text())["takes"][take]
    paint_take(inputs, out, take, record, json.loads(inputs[RECORDS].read_text()))


def paint_faults(folder):
    return [] if (folder / "painted.json").exists() else ["no painted.json"]


def judge_one_surface(output, inputs, evidence):
    """Every part of every painted model has exactly one library surface (the method's or its bordering part's)."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    failing = [f"{take}: parts {report['unnamed_parts']} unnamed ({report['unnamed_share']:.1%})"
               for take, report in found.items() if report["unnamed_parts"]]
    return gates.verdict("one surface a part", failing, len(found), "models with a part no surface names")


def judge_feet(output, inputs, evidence):
    """Every painted take's feet lie in one plane in its own frame: short legs were stretched down (levelled_feet), a
    foot over FOOT_MOST of its height above the lowest fails by name."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    failing = [f"{take}: {len(report['feet']['refused'])} of {report['feet']['feet']} feet end "
               f"{', '.join(f'{gap:.1%}' for gap in report['feet']['refused'])} of its size over its lowest "
               f"(over {FOOT_MOST:.0%}: a missing leg, not a short one)"
               for take, report in found.items() if report.get("feet", {}).get("refused")]
    levelled = sum(bool(report.get("feet", {}).get("levelled")) for report in found.values())
    return gates.verdict("feet in one plane", failing, len(found), "models with a foot off the plane",
                         {"levelled": levelled})


def judge_concept_colour(output, inputs, evidence):
    """Every finish's library surface lies near its colour in the close-up (the method's `finishes`, each with the
    measured colour and its surface's distance from it): a finish no library surface fits by colour is named, its
    proposed tinted surface in the registry for the owner."""
    found = json.loads((output / "painted.json").read_text())["takes"]
    failing = [f"{take}: {finish['finish']} measured L*a*b* {finish['measured_lab']}, {finish['surface']} dE "
               f"{finish['delta_e']} (proposed: {finish['new_surface']['name']})"
               for take, report in found.items() for finish in report.get("finishes", [])
               if finish.get("by") == "off its colour"]
    swapped = sum(finish.get("by") == "nearest of its family by colour" for report in found.values()
                  for finish in report.get("finishes", []))
    finishes = sum(len(report.get("finishes", [])) for report in found.values())
    return gates.verdict("colour against the close-up", failing, finishes, "finishes no surface fits by colour",
                         {"swapped": swapped})


# --- bake ----------------------------------------------------------------------------------------------------------

def bake_entries(inputs, labelled):
    """The place's bake job and its make_chunky entries for the labelled takes ({take: folder}): each model the data
    names, by its entry in the job, in another job the data names, or written out in the data."""
    bake = data_of(inputs)["bake"]
    job = json.loads(inputs["bake job"].read_text())
    entries = {entry["name"]: entry for entry in job["chunky"]}
    for name, entry in bake.get("entries", {}).items():
        if isinstance(entry, str):
            entry = next(found for found in json.loads(inputs[f"bake job {name}"].read_text())["chunky"]
                         if found["name"] == name)
        entries[name] = entry
    # regions: an old job's boxes that forced a variant over the paint (the water tank's top as glass): the method paints
    chunky = [dict(entries[name], name=name, parts=str(labelled[take]), regions=[])
              for name, take in bake["models"].items() if take in labelled]
    return job, chunky


def baking_specs(library_name, specs, labelled):
    """The bake job's specs with every surface today's library knows, painted or the job's own (its decals, screens),
    taken from today's library in the place's palette tokens (library.by_library, the place's own names by
    library.resolved): a job's stored spec can name a picture at a path long gone (the greenhouse's screen and camp's
    locker label, from another checkout, 2026-10-12), and a surface of another library place the take may take from
    is not in it. A spec left naming a picture that is not there stops the bake before anything is rented."""
    import library
    painted = {path.stem for folder in labelled for path in folder.glob("*.ply")}
    every = {**library.by_library(library_name), **library.resolved(library_name)}
    unknown = sorted(painted - set(every) - set(specs))
    if unknown:
        raise RuntimeError(f"surfaces in no library: {unknown}")
    found = {**specs, **{name: every[name] for name in painted | set(specs) if name in every}}
    missing = sorted(name for name, spec in found.items()
                     if "image" in spec and not pathlib.Path(spec["image"]).exists())
    if missing:
        raise RuntimeError(f"specs whose picture is not there: {missing}")
    return found


def measured_dirt(finishes, specs, most):
    """The dirt one model bakes with, from its close-up: for each finish on a painted surface (not glass, screen,
    light or print) with a measured colour, how far that colour lies from the surface's clean colour toward its dirt
    colour, as a share of the way; the median, within 0 and the place's dirt (`most`). A fixed 0.6 in regolith baked
    the wreck's and old_station's whites to L* 69 where their close-ups show them near 90 (2026-10-13)."""
    import numpy as np
    import labels
    shares = []
    for finish in finishes:
        spec = specs.get(finish.get("surface"), {})
        if finish.get("measured_lab") is None or "colour" not in spec or "dirt_colour" not in spec \
                or spec.get("family") in ("glass", "screen", "light", "print"):
            continue
        clean = labels.lab(labels.srgb(np.array(spec["colour"], dtype=float))[None])[0]
        toward = labels.lab(labels.srgb(np.array(spec["dirt_colour"], dtype=float))[None])[0] - clean
        reach = float(np.dot(toward, toward))
        if reach > 1.0:
            shares.append(float(np.clip(np.dot(np.array(finish["measured_lab"]) - clean, toward) / reach, 0.0, 1.0)))
    return round(min(float(np.median(shares)), most), 3) if shares else most


def make_bake(inputs, out, seed, params):
    """The labelled folders baked on rented cards (library_bake.py make_chunky), one job per model."""
    inputs = prop_env.short(inputs)
    data = data_of(inputs)
    painted = inputs["paint"]
    takes = json.loads((painted / "painted.json").read_text())["takes"]
    labelled = {take: painted / "labelled" / take for take in takes}
    job, chunky = bake_entries(inputs, labelled)
    job["specs"] = baking_specs(data["library"], job["specs"], list(labelled.values()))
    jobs = []
    for entry in chunky:
        report = json.loads((pathlib.Path(entry["parts"]) / "labels.json").read_text())
        one = dict(job, chunky=[entry], out=str(out / "made"), report=f"report-{entry['name']}.json",
                   dirt=measured_dirt(report.get("finishes", []), job["specs"], job["dirt"]))
        for key in ("kit", "pieces", "code", "was"):
            one.pop(key, None)
        path = out / f".job-{entry['name']}.json"
        path.write_text(json.dumps(one, indent=1))
        jobs.append(str(path))
    done = subprocess.run([str(prop_env.PROPS_PYTHON), str(PROPS / "cloud/library_bake.py"), *jobs, "--who",
                           f"surfaces-{data['place']}", "--classes", CLASSES], cwd=REPO, capture_output=True,
                          text=True)
    (out / "bake.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode:
        raise RuntimeError(f"library_bake.py failed: {done.stderr[-2000:]}")
    (out / "baked.json").write_text(json.dumps({entry["name"]: dict(entry, parts=pathlib.Path(entry["parts"]).name)
                                                for entry in chunky}, indent=1))
    (out / "elsewhere.json").write_text(json.dumps(claims(inputs), indent=1))
    for path in jobs:
        pathlib.Path(path).unlink()


def claims(inputs):
    """The models the place lays that another place claims (its data's `elsewhere`), each read from that place's
    bake: {model: {take, place, node (that place's bake row), baked_as (the model that place bakes the take as, None
    when it bakes none)}}."""
    found = {}
    for model, claim in data_of(inputs).get("elsewhere", {}).items():
        other = json.loads(inputs[f"claimed {claim['place']}"].read_text())
        baked_as = sorted(name for name, take in other.get("bake", {}).get("models", {}).items()
                          if take == claim["take"] and claim["take"] in other["takes"])
        found[model] = dict(claim, node=f"surfaces-bake@{claim['place']}", baked_as=baked_as[0] if baked_as else None)
    return found


def bake_faults(folder):
    if not (folder / "baked.json").exists():
        return ["no baked.json"]
    missing = [name for name in json.loads((folder / "baked.json").read_text())
               if not (folder / "made" / f"{name}.gltf").exists()]
    return [f"no baked model for {missing}"] if missing else []


def judge_baked(output, inputs, evidence):
    """Every painted model came back baked, and every model the place lays that another place claims is baked by
    that place (its claim names a take that place lists and bakes); a model no place bakes fails."""
    baked = json.loads((output / "baked.json").read_text())
    painted = json.loads((prop_env.short(inputs)["paint"] / "painted.json").read_text())["takes"]
    failing = [f"{take}: not baked (no model of the place's data takes it)" for take in painted
               if take not in {entry["parts"] for entry in baked.values()}]
    claimed = json.loads((output / "elsewhere.json").read_text())
    failing += [f"{model}: claimed by {claim['place']}, which does not bake {claim['take']}"
                for model, claim in claimed.items() if claim["baked_as"] is None]
    return gates.verdict("baked", failing, len(painted) + len(claimed), "models not baked here or by their claim")


# --- check ---------------------------------------------------------------------------------------------------------

def gltf_model(gltf):
    """A baked .gltf's one primitive (positions, texture coordinates in glTF's own convention, triangles) and its
    maps by role, read as tools/usd/export.py reads them but without OpenUSD (the prop environment has none)."""
    import glb_file
    document = json.loads(gltf.read_text())
    blob = (gltf.parent / document["buffers"][0]["uri"]).read_bytes()
    views = [blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
             for view in document["bufferViews"]]
    primitive = document["meshes"][0]["primitives"][0]
    geometry = {"positions": glb_file.accessor_array(document, views, primitive["attributes"]["POSITION"]),
                "uvs": glb_file.accessor_array(document, views, primitive["attributes"]["TEXCOORD_0"]),
                "triangles": glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3)}
    material = document["materials"][primitive["material"]]
    references = {"base_color": material["pbrMetallicRoughness"].get("baseColorTexture"),
                  "metal_roughness": material["pbrMetallicRoughness"].get("metallicRoughnessTexture"),
                  "normal": material.get("normalTexture")}
    maps = {role: gltf.parent / document["images"][document["textures"][reference["index"]]["source"]]["uri"]
            for role, reference in references.items() if reference is not None}
    return geometry, maps


def baked_surfaces(geometry, labelled, entry):
    """Each baked triangle's surface (the labelled part, one .ply per surface, whose nearest point lies under the
    triangle's middle, the parts laid into the kit frame as make_chunky lays them, stored_parts.kit_frame) and
    whether it lies inside its part (all three corners' nearest points on it too)."""
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
    import stored_parts
    points, names = [], []
    for path in sorted(labelled.glob("*.ply")):
        vertices = np.asarray(trimesh.load(path, process=False).vertices)
        vertices = vertices[::max(1, len(vertices) // PART_POINTS)]
        points.append(vertices)
        names += [path.stem] * len(vertices)
    laid = stored_parts.kit_frame(np.vstack(points), np.array(entry["base"]).reshape(3, 3), entry["size"])
    tree, names = cKDTree(laid), np.array(names)
    middles = geometry["positions"][geometry["triangles"]].mean(axis=1)
    surface = names[tree.query(middles)[1]]
    corners = names[tree.query(geometry["positions"])[1]][geometry["triangles"]]
    return surface, (corners == surface[:, None]).all(axis=1)


def check_model(name, entry, labelled, made, materials):
    """One baked model measured: per surface its parts' baked base colour (area-weighted median over its triangles'
    texture at their middles' coordinates; glTF's v runs down the picture) against the surface's colour, its
    near-black share, its maps and its triangles against the job's budget."""
    import numpy as np
    from PIL import Image
    import labels
    geometry, maps = gltf_model(made / f"{name}.gltf")
    record = {"triangles": int(len(geometry["triangles"])), "budget": int(entry["faces"]),
              "maps": sorted(maps), "surfaces": {}}
    record["missing_maps"] = [role for role in ("base_color", "metal_roughness", "normal") if role not in maps]
    if "base_color" in record["missing_maps"]:
        return record
    picture = np.asarray(Image.open(maps["base_color"]).convert("RGB"), dtype=np.float64) / 255
    height, width = picture.shape[:2]
    uv = geometry["uvs"][geometry["triangles"]].mean(axis=1) % 1.0
    columns = np.clip((uv[:, 0] * width).astype(int), 0, width - 1)
    rows = np.clip((uv[:, 1] * height).astype(int), 0, height - 1)
    colour = labels.lab(picture[rows, columns])
    corners = geometry["positions"][geometry["triangles"]]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    surface, interior = baked_surfaces(geometry, labelled, entry)
    for name_of in sorted(set(surface.tolist())):
        chosen = surface == name_of
        order = np.argsort(colour[chosen, 0])
        weights = np.cumsum(areas[chosen][order])
        middle = colour[chosen][order][np.searchsorted(weights, weights[-1] / 2)]
        token = labels.lab(labels.srgb(np.array(materials[name_of]["colour"]))[None])[0] \
            if name_of in materials else None
        inside = chosen & interior  # a triangle across a border bakes its neighbour's colour (a paper label on black)
        blotch = float(areas[inside & (colour[:, 0] < BLOTCH_L)].sum() / max(areas[inside].sum(), 1e-12))
        record["surfaces"][name_of] = {
            "share": round(float(areas[chosen].sum() / areas.sum()), 4),
            "baked_lab": [round(float(value), 1) for value in middle],
            "surface_lab": None if token is None else [round(float(value), 1) for value in token],
            "delta_e": None if token is None else round(float(np.linalg.norm(middle - token)), 1),
            "near_black": round(blotch, 4)}
    return record


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def check_step(inputs, out):
    """The prop environment's side: every baked model measured (checks.json)."""
    import library
    name = data_of(inputs)["library"]
    materials = {**library.by_library(name), **library.resolved(name)}
    found = {model: check_model(model, entry, inputs["paint"] / "labelled" / entry["parts"], inputs["bake"] / "made",
                                materials)
             for model, entry in json.loads((inputs["bake"] / "baked.json").read_text()).items()}
    (out / "checks.json").write_text(json.dumps(found, indent=1))


def check_faults(folder):
    return [] if (folder / "checks.json").exists() else ["no checks.json"]


def surface_faults(name, record):
    """A baked model's faults against its surfaces: parts off their surface's colour, near-black blotches, a
    surface not in the place's library."""
    faults = []
    for surface, entry in record["surfaces"].items():
        if entry["share"] < PART_LEAST:
            continue
        if entry["delta_e"] is None:
            faults.append(f"{name}: {surface} is not in the place's library")
        elif entry["delta_e"] > BAKE_DELTA_E:
            faults.append(f"{name}: {surface} baked {entry['baked_lab']} against {entry['surface_lab']} "
                          f"(dE {entry['delta_e']})")
        if entry["surface_lab"] and entry["surface_lab"][0] > DARK_SURFACE and entry["near_black"] > BLOTCH_SHARE:
            faults.append(f"{name}: {surface} {entry['near_black']:.1%} near black")
    return faults


def judge_lit(output, inputs, evidence):
    """The baked model matches its surfaces: every part's baked colour on its surface, no blotch, every map."""
    found = json.loads((output / "checks.json").read_text())
    failing = []
    for name, record in found.items():
        failing += [f"{name}: no {role} map" for role in record["missing_maps"]] + surface_faults(name, record)
    return gates.verdict("baked matches its surfaces", failing, len(found), "faults over the models")


def judge_triangles(output, inputs, evidence):
    """Triangles within the bake job's budget per model."""
    found = json.loads((output / "checks.json").read_text())
    failing = [f"{name}: {record['triangles']} triangles over {record['budget']}" for name, record in found.items()
               if record["triangles"] > record["budget"]]
    return gates.verdict("triangles within budget", failing, len(found), "models",
                         {"triangles": sum(record["triangles"] for record in found.values())})


STEPS = {"paint-take": paint_take_step, "check": check_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
