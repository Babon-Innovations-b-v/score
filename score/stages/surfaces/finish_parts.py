"""The finish-map method's free steps, run in the prop environment (trimesh) through this module's command line
(prop_env.py): its inputs, and its parts, the method's interface (PARTS in __init__.py). No model runs here.

Rows (place grain, surfaces-<step>@<place>):
    inputs  (free)  flat/takes.json from the place's data (each take's place, kind, object and library places) and the
                    turntable's cameras (turntable_views.cameras)
    parts   (free)  every take whose close-up map settled, its finish maps laid onto the raw Pixal3D model (its
                    geometry kept), every face one finish:
                    1. each map votes on the faces its view sees (the close-up's FRONT_VOTE, each turntable view's 1)
                    2. each part of SegviGen's guided split takes its voted faces' finish when they hold SEEN_LEAST of
                       its area and are pure (the second finish under MIX_SHARE of them): SegviGen merged the
                       lander's gold and silver foil into one part, so a mixed part names nothing
                    3. a voted face keeps its own vote; any other face its SegviGen part's finish, else the finish of
                       the nearest voted face along the surface (walked)
                    4. smoothed over the surface and its crumbs joined (cleaned), then every island under
                       ISLAND_LEAST of the area, joined to the rest or loose, taken into the nearest larger island of
                       its own finish, its finish's crumbs one part when it has none and they reach ISLAND_LEAST
                       together, else the nearest larger island with its finish (merged_islands): the aft section's
                       ~9,600 loose bits were parts
                    5. measured against the maps: per map the share of the faces it sees painted its finish, the
                       parts whose voted faces mix two finishes (MIX_SHARE), the parts; front and back pictures
                    parts.json per take: each part's share, its finish's library surface (`judge`) and words, the new
                    surface Gemini proposed for it (`proposed`); `finish` null: nothing is measured from the texture.
                    <take>/parts.npy, <take>/colours.npy (NaN: no colour measured, neighbours of one surface join on
                    the surface alone), <take>/front.png and back.png (each part in its surface's colour).
                    Gate: no part mixes two finishes by the maps (a take that does is named and stops the line).
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", PROPS / "cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import prop_env  # noqa: E402
import surface_gates as gates  # noqa: E402

FRONT_VOTE = 2.0  # the close-up's map is the one the owner checked (2026-10-12: "finish map seed 1 looks great")
SEEN_LEAST = 0.05  # a SegviGen part names itself from its voted faces when they hold this share of its area
MIX_SHARE = 0.2  # a part mixes finishes when its second finish holds this share of its voted area
PART_LEAST = 0.01  # parts under this share of the model are not judged for mixing
ISLAND_LEAST = 0.002  # split_compare.CRUMB: an island under this share of the area joins the nearest larger one
BORDER = (0, 0, 0)
# A finish's library surface must lie within this (CIE76) of its colour in the close-up. A photo's light, dirt and
# muted saturation move a right surface far: on round 4's six models the right ones lay up to dE 29.7 from it (the
# lander's light paint, its gold foil 29.5, black rubber 29.4), the wrong ones 33.2 to 44.9 (the power unit's grey
# steel as near-black dark_panel 44.9, the lab chair's grey vinyl as navy vinyl_seat 37.8, the power unit's silver
# tape as dark galvanized_dull 33.2; 2026-10-12). At the bake check's 20 the gold foil turned silver.
COLOUR_DELTA_E = 32.0


def takes_of(inputs):
    return json.loads((inputs["inputs"] / "flat" / "takes.json").read_text())


def passed(inputs):
    import segvigen_row
    return segvigen_row.passed(inputs)


# --- inputs --------------------------------------------------------------------------------------------------------

def make_inputs(inputs, out, seed, params):
    prop_env.handover(__file__, "inputs", inputs, out)


def inputs_step(inputs, out):
    """The prop environment's side: flat/takes.json and multiview/job.json."""
    import turntable_views as views
    takes = json.loads(inputs["surfaces"].read_text())["takes"]
    (out / "flat").mkdir(parents=True)
    (out / "flat" / "takes.json").write_text(json.dumps(takes, indent=1))
    views.cameras(out, sorted(takes))


def inputs_faults(folder):
    present = (folder / "flat" / "takes.json").exists() and (folder / "multiview" / "job.json").exists()
    return [] if present else ["no flat/takes.json or multiview/job.json"]


def judge_inputs(output, inputs, evidence):
    """Every take has its row and its cameras."""
    takes = json.loads((output / "flat" / "takes.json").read_text())
    job = json.loads((output / "multiview" / "job.json").read_text())
    named = {entry["take"] for entry in job["takes"]}
    return gates.verdict("inputs", [take for take in takes if take not in named], len(takes), "takes without cameras")


# --- the maps on the model -----------------------------------------------------------------------------------------

def map_labels(mesh, take, inputs):
    """{map name: label per face, -1 where its view does not see the face or the map has no label}: the close-up's
    ("front") and each settled view map's."""
    import numpy as np
    import labels
    import turntable_views as views
    folder = inputs["maps"] / take
    _, seen, row, column = labels.picture_view(mesh, take)
    front = np.load(folder / "front.npy").astype(int)
    found = {"front": np.where(seen, front[row, column], -1)}
    job = json.loads((inputs["inputs"] / "multiview" / "job.json").read_text())
    renders = inputs["turntable"] / "renders" / take
    for view in views.MAP_VIEWS:
        if not (folder / f"{view}.npy").exists():
            continue
        drawn = np.load(folder / f"{view}.npy").astype(int)
        seen, row, column = views.seen_in_view(renders, views.camera_of(job, take, view), mesh,
                                               views.face_map(renders, view, mesh))
        found[view] = np.where(seen, drawn[row, column], -1)
    return found


def voted(per_map, count):
    """Each face's votes per finish over the maps that see it (the close-up's FRONT_VOTE, a view's 1)."""
    import numpy as np
    faces = len(next(iter(per_map.values())))
    votes = np.zeros((faces, count))
    for name, label in per_map.items():
        seen = label >= 0
        votes[np.flatnonzero(seen), label[seen]] += FRONT_VOTE if name == "front" else 1.0
    return votes


def walked(mesh, face_label):
    """Every unlabelled face given the label of the nearest labelled face along the surface (face middles joined
    across shared edges, weighed by their distance); faces no walk reaches take the nearest labelled face in space."""
    import numpy as np
    from scipy import sparse
    from scipy.sparse.csgraph import dijkstra
    from scipy.spatial import cKDTree
    pairs = mesh.face_adjacency
    middles = mesh.triangles_center
    length = np.linalg.norm(middles[pairs[:, 0]] - middles[pairs[:, 1]], axis=1) + 1e-9
    count = len(mesh.faces)
    graph = sparse.coo_matrix((np.r_[length, length], (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                              shape=(count, count)).tocsr()
    sources = np.flatnonzero(face_label >= 0)
    distance, _, source = dijkstra(graph, directed=False, indices=sources, min_only=True, return_predecessors=True)
    found = face_label.copy()
    reached = np.isfinite(distance) & (source >= 0)
    found[reached] = face_label[source[reached]]
    lost = found < 0
    if lost.any():
        found[lost] = face_label[sources[cKDTree(middles[sources]).query(middles[lost])[1]]]
    return found


def segvigen_split(mesh, take_folder):
    """SegviGen's guided split on the faces (its voxels laid on the model turned half round, as it was given),
    cleaned as the parts test cleaned it (split_compare)."""
    import trimesh
    import labels
    import split_compare
    turned = trimesh.Trimesh(mesh.vertices @ labels.VIEW_TURN.T, mesh.faces, process=False)
    return split_compare.cleaned(mesh, split_compare.segvigen_parts(turned, take_folder, "guided"))


def segvigen_labels(mesh, part_of, votes):
    """Each SegviGen part's finish per face: its voted faces' (area-weighted) when they hold SEEN_LEAST of its area
    and its second finish stays under MIX_SHARE of them; -1 for a part that names nothing."""
    import numpy as np
    areas = mesh.area_faces
    weighted = votes * areas[:, None]
    parts = int(part_of.max()) + 1
    by_part = np.zeros((parts, votes.shape[1]))
    np.add.at(by_part, part_of, weighted)
    seen_area = np.bincount(part_of, weights=areas * (votes.sum(1) > 0), minlength=parts)
    size = np.bincount(part_of, weights=areas, minlength=parts)
    ordered = np.sort(by_part, axis=1)
    second = ordered[:, -2] if by_part.shape[1] > 1 else np.zeros(parts)
    pure = second < MIX_SHARE * np.maximum(by_part.sum(1), 1e-12)
    chosen = np.where((seen_area >= SEEN_LEAST * size) & pure, by_part.argmax(1), -1)
    return chosen[part_of]


def cleaned(mesh, face_label, count):
    """The labels smoothed over the surface (labels.smoothed_parts, hardly across a crease) and every island under
    ISLAND_LEAST of the area that borders others joined to the label it borders most."""
    import numpy as np
    import labels
    votes = np.zeros((len(face_label), count))
    votes[np.arange(len(face_label)), face_label] = 1.0
    smoothed = labels.smoothed_parts(votes, labels.neighbour_matrix(mesh))
    saved = labels.PART_CRUMB
    labels.PART_CRUMB = ISLAND_LEAST
    try:
        return labels.without_crumbs(mesh, smoothed)
    finally:
        labels.PART_CRUMB = saved


def merged_islands(mesh, face_label):
    """Each face's part and finish once every island (one finish's faces joined by shared edges) under ISLAND_LEAST
    of the area, joined to the rest or loose (a loose bit shares no edge, so without_crumbs never reaches it), is
    taken in by its finish: into the larger island of its own finish nearest it in space; when its finish has no
    larger island, its finish's small islands together are one part if they reach ISLAND_LEAST; else into the larger
    island of any finish nearest it, its finish with it. Taken in by space alone, the crane trolley's black warning
    stripes (each band a crumb) and the cut's yellow and rope crumbs went into its forged steel, the black finish
    vanished and that part mixed (2026-10-12). With no larger island, the largest island takes the rest."""
    import numpy as np
    from scipy.spatial import cKDTree
    import patchy
    island = np.unique(patchy.islands(face_label, mesh.face_adjacency), return_inverse=True)[1]
    area = np.bincount(island, weights=mesh.area_faces)
    large = area >= ISLAND_LEAST * mesh.area
    if not large.any():
        large[area.argmax()] = True
    kept = large[island]
    part_of, label = island.copy(), face_label.copy()
    middles = mesh.triangles_center
    hosts = kept.copy()
    for finish in np.unique(face_label[~kept]):
        lost = np.flatnonzero(~kept & (face_label == finish))
        host = np.flatnonzero(hosts & (face_label == finish))
        if not len(host) and mesh.area_faces[lost].sum() >= ISLAND_LEAST * mesh.area:
            part_of[lost] = island[lost[0]]
            continue
        if not len(host):
            host = np.flatnonzero(hosts)
        nearest = host[cKDTree(middles[host]).query(middles[lost])[1]]
        part_of[lost], label[lost] = part_of[nearest], face_label[nearest]
    return np.unique(part_of, return_inverse=True)[1], label


def laid(mesh, take, inputs, count, within):
    """One take's maps laid, each finish seen within a cover laid as its cover (`within`: seen_within): (part per face,
    finish per face, the maps' labels per face)."""
    import numpy as np
    per_map = {name: taken_in(label, within) for name, label in map_labels(mesh, take, inputs).items()}
    votes = voted(per_map, count)
    own = np.where(votes.sum(1) > 0, votes.argmax(1), -1)
    from_parts = segvigen_labels(mesh, segvigen_split(mesh, inputs["segvigen"] / take), votes)
    walked_label = walked(mesh, own)
    face_label = np.where(own >= 0, own, np.where(from_parts >= 0, from_parts, walked_label))
    part_of, face_label = merged_islands(mesh, cleaned(mesh, face_label, count))
    mixed = [part for part, _ in mixing_parts(mesh, part_of, face_label, per_map, count)]
    if mixed:  # the smoothing ran a part across the votes (the seed tray, 2026-10-12): cut it along them
        inside = np.isin(part_of, mixed)
        face_label = np.where(inside, np.where(own >= 0, own, walked_label), face_label)
        part_of, face_label = merged_islands(mesh, face_label)
    return part_of, face_label, per_map


# --- measures and pictures -----------------------------------------------------------------------------------------

def agreement(mesh, face_label, per_map):
    """Per map, the area share of the faces it labels that are painted its finish."""
    areas = mesh.area_faces
    found = {}
    for name, label in per_map.items():
        seen = label >= 0
        found[name] = round(float(areas[seen & (face_label == label)].sum() / max(areas[seen].sum(), 1e-12)), 3)
    return found


def mixing_parts(mesh, part_of, face_label, per_map, count):
    """The parts over PART_LEAST of the area whose voted faces give another finish than the part's on MIX_SHARE of
    their area: [(part, share of the other finish)]."""
    import numpy as np
    votes = voted(per_map, count)
    own = np.where(votes.sum(1) > 0, votes.argmax(1), -1)
    areas = mesh.area_faces
    found = []
    for part in range(int(part_of.max()) + 1):
        members = part_of == part
        if areas[members].sum() < PART_LEAST * mesh.area:
            continue
        seen = members & (own >= 0)
        total = areas[seen].sum()
        other = areas[seen & (own != face_label)].sum()
        if total > 0 and other >= MIX_SHARE * total:
            found.append((part, round(float(other / total), 3)))
    return found


def part_picture(mesh, renders, view, part_of, colours):
    """A turntable view of the painted model: each pixel its part's surface colour (sRGB 0-255), part borders black,
    off the model clear (RGBA)."""
    import numpy as np
    from PIL import Image
    import turntable_views as views
    faces = views.face_map(renders, view, mesh)
    inside = faces >= 0
    part = np.where(inside, part_of[np.maximum(faces, 0)], -1)
    painted = np.zeros((*faces.shape, 4), dtype=np.uint8)
    painted[inside, :3] = colours[part[inside]]
    painted[inside, 3] = 255
    edge = np.zeros(faces.shape, dtype=bool)
    edge[:-1] |= part[:-1] != part[1:]
    edge[:, :-1] |= part[:, :-1] != part[:, 1:]
    painted[edge & inside, :3] = BORDER
    return Image.fromarray(painted)


def surface_colours(entry, names):
    """Each surface's library colour, sRGB 0-255."""
    import numpy as np
    import labels
    every = take_surfaces(entry)
    return {name: np.clip(labels.srgb(np.array(every[name]["colour"], dtype=float)) * 255, 0, 255).astype(np.uint8)
            for name in names}


# --- each finish's surface against the close-up's colour -----------------------------------------------------------

# A finish whose library surface is darker than this (L*) is measured on its darker pixels (finish_colour).
DARK_L = 35.0


def measured_colours(take, front, surfaces):
    """Each finish's colour in the close-up (CIELAB) over its label's pixels in the close-up's map (`surfaces`: each
    finish's library spec, or None), None for a finish with no pixel (finish_colour)."""
    import labels
    import split_compare
    lab = labels.picture_lab(split_compare.picture(take))
    return [finish_colour(lab[front == label], spec) for label, spec in enumerate(surfaces)]


def finish_colour(pixels, spec):
    """One finish's colour from its label's pixels (CIELAB): the median of the brighter half by L* (the shaded half
    left out); for a finish whose library surface lies under DARK_L, the median of all its pixels: the close-up's light
    lifts a black finish's brighter half to L* 40 to 45 (old_station's black rubber, garage's tyres), and its darker
    quarter is shadow (launch's dark wood at L* 2, flat's soil at 3; 2026-10-12). None with no pixel."""
    import numpy as np
    if not len(pixels):
        return None
    if spec and "colour" in spec and library_lab(spec)[0] < DARK_L:
        return np.median(pixels, axis=0)
    return np.median(pixels[pixels[:, 0] >= np.median(pixels[:, 0])], axis=0)


def library_lab(spec):
    import labels
    import numpy as np
    return labels.lab(labels.srgb(np.array(spec["colour"], dtype=float))[None])[0]


def take_surfaces(entry):
    """Every library surface a take may take: each of its library places' (no surface an object never is), its
    kind's own list on top."""
    import labels
    every = {}
    for place in entry["library_places"]:
        every.update({name: spec for name, spec in labels.allowed_materials(place, None, []).items()
                      if name not in every})
    every.update(labels.allowed_materials(entry["library_places"][0], entry["kind"], []))
    return every


# The material words a finish list uses, by class, and the classes each library family is: a finish whose words name
# a class its surface's family is not (black rubber named bare_steel) is named again.
CLASS_WORDS = {"rubber": ("rubber",), "plastic": ("plastic", "vinyl", "bakelite", "leather"),
               "paper": ("paper", "card", "label"), "glass": ("glass", "lens", "screen"), "water": ("water",),
               "wood": ("wood", "timber", "plank"), "fabric": ("fabric", "canvas", "cloth", "textile"),
               "foil": ("foil",), "soil": ("soil", "seed", "potting"), "plant": ("plant", "leaf", "seedling"),
               "metal": ("steel", "metal", "aluminium", "aluminum", "iron", "chrome", "tin"),
               "paint": ("paint",)}
FAMILY_CLASSES = {"painted": ("paint", "metal"), "steel": ("metal",), "aluminium": ("metal",), "rusted": ("metal",),
                  "rubber": ("rubber",), "plastic": ("plastic", "rubber"), "cable": ("rubber", "plastic"),
                  "fabric": ("fabric",), "composite": ("plastic",), "glass": ("glass", "water"),
                  "screen": ("glass",), "light": ("glass",), "print": ("paper",), "paper": ("paper",),
                  "wood": ("wood",), "foil": ("foil", "metal"), "growing": ("soil", "plant"), "ground": ("soil",),
                  "water": ("water",)}


def contradicts(words, family):
    """Whether a finish's words name a material class and none of them is one its surface's family is."""
    import re
    named = {name for name, keys in CLASS_WORDS.items()
             if any(re.search(rf"\b{key}", words.lower()) for key in keys)}
    return bool(named) and family in FAMILY_CLASSES and not named & set(FAMILY_CLASSES[family])


# Not paint (owner, #8, 2026-10-12): glass, screen glow, lamp light and print are judged by their own colour, so one
# off the close-up's lit colour keeps its surface. A finish the close-up shows over ORDER_L lighter than another must
# not lie over ORDER_LIBRARY darker in the library (bake_check's ORDER_L and ORDER_BAKED, before the bake).
# A finish seen through (see_through): its surface's family, or these words in its finish or parts. A see-through
# part's pixels cover what lies behind it, grown by COVER_GROW pixels (face middles land a pixel or two apart).
SEEN_THROUGH_FAMILIES = ("glass", "screen", "light")
SEEN_THROUGH_WORDS = ("transparent", "translucent")
COVER_GROW = 2
# An opaque finish whose outline in the close-up's map (OUTLINE pixels round it) is at least SEEN_WITHIN one
# see-through finish is seen through it (seen_within): the garage beacon's reflector, 97.6% its red dome.
OUTLINE, SEEN_WITHIN = 3, 0.9
OWN_COLOUR = ("glass", "screen", "light", "print")
ORDER_L, ORDER_LIBRARY = 10.0, 3.0


def checked_finishes(entry, finishes, measured):
    """Each finish with its surface checked against the close-up's colour: the listed surface when it lies within
    COLOUR_DELTA_E of the measured colour, else the nearest surface of the same family (library `family`) the take's
    library places allow, when within it; else the listed one kept, a new surface tinted to the measured colour
    proposed, and the finish marked off its colour (the paint's gate fails it). A see-through finish of a surface
    that is not glass, glow or light keeps its surface (coloured_cover)."""
    import numpy as np
    every = take_surfaces(entry)
    found = []
    for finish, colour in zip(finishes, measured):
        record = dict(finish, listed_surface=finish.get("listed_surface", finish["surface"]), measured_lab=None,
                      delta_e=None, by=finish.get("by", "the list"))
        if colour is None or finish["surface"] not in every:
            found.append(record)
            continue
        listed = every[finish["surface"]]
        apart = float(np.linalg.norm(library_lab(listed) - colour))
        record.update(measured_lab=[round(float(value), 1) for value in colour], delta_e=round(apart, 1))
        if apart > COLOUR_DELTA_E and coloured_cover(finish, every):
            record.update(by="its own colour", cover=True)
        elif apart > COLOUR_DELTA_E:
            family = [(float(np.linalg.norm(library_lab(spec) - colour)), name) for name, spec in every.items()
                      if spec.get("family") == listed.get("family") and "colour" in spec]
            nearest_apart, nearest = min(family) if family else (float("inf"), None)
            if nearest_apart <= COLOUR_DELTA_E:
                record.update(surface=nearest, delta_e=round(nearest_apart, 1), by="nearest of its family by colour")
            elif listed.get("family") in OWN_COLOUR:
                record.update(by="its own colour")
            else:
                record.update(by="off its colour", fits=False, new_surface={
                    "name": f"{finish['finish']} ({take_words(entry)})",
                    "description": f"{finish['finish']}, measured in the close-up at L*a*b* "
                                   f"{[round(float(value), 1) for value in colour]}",
                    "why": f"no {listed.get('family')} surface lies within dE {COLOUR_DELTA_E:.0f} of the close-up's "
                           f"colour (nearest {nearest}, dE {nearest_apart:.1f})",
                    "lab": [round(float(value), 1) for value in colour]})
        found.append(record)
    return in_close_up_order(entry, found, every)


def coloured_cover(finish, every):
    """True for a see-through finish whose surface is not glass, glow or light (the garage beacon's red transparent
    dome as red_plastic): its close-up pixels are its highlights and what lies behind it, not its colour, so like
    glass (owner, #8) it is judged by its own colour. Its pale highlights took the dome to plastic_grey (2026-10-13)."""
    return see_through(finish, every) and every.get(finish["surface"], {}).get("family") not in OWN_COLOUR


def opaque_lightness(every):
    """{surface: its library L*} of the take's surfaces that are paint (not OWN_COLOUR) and have a colour."""
    return {name: float(library_lab(spec)[0]) for name, spec in every.items()
            if "colour" in spec and spec.get("family") not in OWN_COLOUR}


def out_of_order(lighter, darker, lightness):
    """True when the close-up shows `lighter` over ORDER_L lighter than `darker` while its surface lies over
    ORDER_LIBRARY darker in the library (`lightness`: opaque_lightness)."""
    return (lighter.get("measured_lab") is not None and darker.get("measured_lab") is not None
            and lighter["surface"] in lightness and darker["surface"] in lightness
            and lighter["measured_lab"][0] - darker["measured_lab"][0] > ORDER_L
            and lightness[lighter["surface"]] < lightness[darker["surface"]] - ORDER_LIBRARY)


def in_close_up_order(entry, found, every):
    """The finishes with their opaque surfaces in the close-up's lightness order: where the close-up shows a finish
    over ORDER_L lighter than another whose surface lies over ORDER_LIBRARY lighter in the library (painted_panel L* 61.6
    under bare_steel 66.3 on the greenhouse's water tank, the panel 13 lighter in its close-up; the bake keeps the
    library's order), the lighter finish takes the nearest surface of its family by colour, within COLOUR_DELTA_E,
    that keeps the order; else it is marked off its colour by its order (the paint's gate fails it). Glass, glow, lamp
    light and print (OWN_COLOUR) and a finish judged by its own colour are left out; a take with no such pair comes back
    as it was."""
    import numpy as np
    lightness = opaque_lightness(every)
    for lighter in found:
        for darker in found:
            if (lighter.get("by") == "off its colour" or "its own colour" in (lighter.get("by"), darker.get("by"))
                    or not out_of_order(lighter, darker, lightness)):
                continue
            seen = lighter["measured_lab"][0] - darker["measured_lab"][0]
            floor = lightness[darker["surface"]] - ORDER_LIBRARY
            colour = np.array(lighter["measured_lab"])
            family = every[lighter["surface"]].get("family")
            fits = sorted((float(np.linalg.norm(library_lab(every[name]) - colour)), name) for name in lightness
                          if every[name].get("family") == family and lightness[name] >= floor)
            if fits and fits[0][0] <= COLOUR_DELTA_E:
                lighter.update(surface=fits[0][1], delta_e=round(fits[0][0], 1), by="nearest of its family in order")
                continue
            lighter.update(by="off its colour", fits=False, new_surface={
                "name": f"{lighter['finish']} ({take_words(entry)})",
                "description": f"{lighter['finish']}, measured in the close-up at L*a*b* {lighter['measured_lab']}",
                "why": f"{seen:.1f} L* lighter than {darker['surface']} in the close-up, but no {family} surface within "
                       f"dE {COLOUR_DELTA_E:.0f} lies lighter in the library",
                "lab": lighter["measured_lab"]})
    return found


def take_words(entry):
    return entry["object"][:40]


# --- parts: the method's interface ---------------------------------------------------------------------------------

def part_rows(mesh, part_of, face_label, finishes):
    """parts.json's rows: per part its share, its finish's library surface and words, the proposed new surface."""
    import numpy as np
    areas = mesh.area_faces
    rows = []
    for part in range(int(part_of.max()) + 1):
        members = part_of == part
        finish = finishes[int(np.bincount(face_label[members], weights=areas[members]).argmax())]
        rows.append({"part": part, "share": round(float(areas[members].sum() / areas.sum()), 4), "finish": None,
                     "judge": finish["surface"], "words": finish["finish"], "set_aside": False,
                     "proposed": None if finish["fits"] else finish.get("new_surface")})
    return rows


def see_through(finish, every):
    """True for a finish one sees through or that gives its own light: its surface glass, a screen or a light (or its
    words a transparent or translucent material)."""
    words = f"{finish['finish']} {finish['parts']}".lower()
    return (every.get(finish["surface"], {}).get("family") in SEEN_THROUGH_FAMILIES
            or any(word in words for word in SEEN_THROUGH_WORDS))


def see_through_cover(mesh, take, face_label, listed, every):
    """The close-up's pixels whose first face from its camera belongs to a see-through finish (see_through): each seen
    face of such a finish marks the pixel its middle lands on, grown by COVER_GROW pixels to close the gaps between
    face middles."""
    import numpy as np
    from scipy import ndimage
    import labels
    picture, seen, row, column = labels.picture_view(mesh, take)
    through = [number for number, finish in enumerate(listed) if see_through(finish, every)]
    cover = np.zeros((picture.size[1], picture.size[0]), dtype=bool)
    if through:
        faces = seen & np.isin(face_label, through)
        cover[row[faces], column[faces]] = True
        cover = ndimage.binary_dilation(cover, iterations=COVER_GROW)
    return cover


def seen_within(front, listed, every):
    """{finish: the see-through finish round it} for each opaque finish whose outline in the close-up's map (OUTLINE
    pixels round it, off the object counted) is at least SEEN_WITHIN that one see-through finish: the model is the
    cover's shell with nothing inside it, so the maps drew what lies behind the cover on the cover's own faces (the
    garage beacon's reflector on its red dome's front, measured red and painted cast_steel, 2026-10-13)."""
    import numpy as np
    from scipy import ndimage
    found = {}
    for number, finish in enumerate(listed):
        here = front == number
        if see_through(finish, every) or not here.any():
            continue
        outline = front[ndimage.binary_dilation(here, iterations=OUTLINE) & ~here]
        covers, counts = np.unique(outline[outline >= 0], return_counts=True)
        for cover, count in zip(covers, counts):
            if see_through(listed[cover], every) and count >= SEEN_WITHIN * len(outline):
                found[number] = int(cover)
    return found


def taken_in(label, within):
    """The labels (a map's pixels or faces) with each finish seen within a cover given its cover's (seen_within)."""
    found = label.copy()
    for finish, cover in within.items():
        found[label == finish] = cover
    return found


def behind_left_out(front, cover, listed, every):
    """The close-up map with each opaque finish's pixels under a see-through part (`cover`) left out of its measure:
    its colour there is the cover's (the garage beacon's reflector measured its red dome's colour, 2026-10-13). A
    finish with every pixel behind the cover is left unmeasured; one with none behind comes back as it was."""
    import numpy as np
    found = front.copy()
    for number, finish in enumerate(listed):
        if not see_through(finish, every):
            found[(front == number) & cover] = -1
    return found


def parts_take(inputs, take, entry, out):
    """One take's parts, its arrays and pictures under <out>/<take>/; its parts.json record."""
    import numpy as np
    import split_compare
    import turntable_views as views
    listed = json.loads((inputs["names"] / f"{take}.json").read_text())["finishes"]
    front = np.load(inputs["maps"] / take / "front.npy").astype(int)
    every = take_surfaces(entry)
    mesh = split_compare.raw_model(take)
    within = seen_within(front, listed, every)
    part_of, face_label, per_map = laid(mesh, take, inputs, len(listed), within)
    front = behind_left_out(taken_in(front, within), see_through_cover(mesh, take, face_label, listed, every), listed,
                            every)
    finishes = checked_finishes(entry, listed,
                                measured_colours(take, front, [every.get(finish["surface"]) for finish in listed]))
    for number, cover in within.items():
        finishes[number]["seen_within"] = listed[cover]["finish"]
    rows = part_rows(mesh, part_of, face_label, finishes)
    folder = out / take
    folder.mkdir(parents=True)
    np.save(folder / "parts.npy", part_of.astype(np.int32))
    np.save(folder / "colours.npy", np.full((len(mesh.faces), 3), np.nan, dtype=np.float32))
    colours = surface_colours(entry, {row["judge"] for row in rows})
    by_part = np.array([colours[row["judge"]] for row in rows])
    renders = inputs["turntable"] / "renders" / take
    for name, view in (("front", views.FRONT), ("back", views.BACK)):
        if (renders / f"{view}-id.npz").exists():
            part_picture(mesh, renders, view, part_of, by_part).save(folder / f"{name}.png")
    measures = {"agreement": agreement(mesh, face_label, per_map),
                "mixing_parts": mixing_parts(mesh, part_of, face_label, per_map, len(finishes)),
                "parts": len(rows), "maps": sorted(per_map)}
    return {"method": "finish-map", "parts": rows, "judge_unknown": [], "measures": measures, "finishes": finishes}


def make_parts(inputs, out, seed, params):
    prop_env.handover(__file__, "parts", inputs, out)


def parts_step(inputs, out):
    """The prop environment's side: every take whose map settled, its parts (parts.json and its arrays); a take
    without one is listed as left out."""
    takes = takes_of(inputs)
    painted = passed(inputs)
    found = {take: parts_take(inputs, take, takes[take], out) for take in painted}
    left = {take: "no finish map settled" for take in takes if take not in painted}
    (out / "parts.json").write_text(json.dumps({"takes": found, "left_out": left}, indent=1))


def parts_faults(folder):
    if not (folder / "parts.json").exists():
        return ["no parts.json"]
    missing = [take for take in json.loads((folder / "parts.json").read_text())["takes"]
               if not (folder / take / "parts.npy").exists()]
    return [f"no parts.npy for {missing}"] if missing else []


def judge_parts(output, inputs, evidence):
    """Every take whose map settled has its parts, and none has a part mixing two finishes by the maps; the maps'
    agreement and the parts as measures."""
    found = json.loads((output / "parts.json").read_text())["takes"]
    takes = passed(prop_env.short(inputs))
    failing = [f"{take}: no parts" for take in takes if take not in found]
    failing += [f"{take}: parts {record['measures']['mixing_parts']} mix two finishes (part, other share)"
                for take, record in found.items() if record["measures"]["mixing_parts"]]
    front = [record["measures"]["agreement"].get("front", 0.0) for record in found.values()]
    return gates.verdict("parts", failing, len(takes), "models", {
        "front agreement least": min(front, default=0.0),
        "parts": sum(record["measures"]["parts"] for record in found.values()),
        "off colour": sum(finish["by"] == "off its colour" for record in found.values()
                          for finish in record.get("finishes", []))})


STEPS = {"inputs": inputs_step, "parts": parts_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
