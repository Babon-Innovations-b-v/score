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
                       ISLAND_LEAST of the area, joined to the rest or loose, taken into the nearest larger island in
                       space, its finish with it (merged_islands): the aft section's ~9,600 loose bits were parts
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
    of the area, joined to the rest or loose, is taken into the larger island nearest it in space (the nearest face
    middle; a loose bit shares no edge, so without_crumbs never reaches it). With no larger island, the largest
    island takes the rest."""
    import numpy as np
    from scipy.spatial import cKDTree
    import patchy
    island = np.unique(patchy.islands(face_label, mesh.face_adjacency), return_inverse=True)[1]
    area = np.bincount(island, weights=mesh.area_faces)
    large = area >= ISLAND_LEAST * mesh.area
    if not large.any():
        large[area.argmax()] = True
    kept = large[island]
    host = np.flatnonzero(kept)
    part_of, label = island.copy(), face_label.copy()
    if (~kept).any():
        nearest = host[cKDTree(mesh.triangles_center[host]).query(mesh.triangles_center[~kept])[1]]
        part_of[~kept], label[~kept] = island[nearest], face_label[nearest]
    return np.unique(part_of, return_inverse=True)[1], label


def laid(mesh, take, inputs, count):
    """One take's maps laid: (part per face, finish per face, the maps' labels per face)."""
    import numpy as np
    per_map = map_labels(mesh, take, inputs)
    votes = voted(per_map, count)
    own = np.where(votes.sum(1) > 0, votes.argmax(1), -1)
    from_parts = segvigen_labels(mesh, segvigen_split(mesh, inputs["segvigen"] / take), votes)
    walked_label = walked(mesh, own)
    face_label = np.where(own >= 0, own, np.where(from_parts >= 0, from_parts, walked_label))
    part_of, face_label = merged_islands(mesh, cleaned(mesh, face_label, count))
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
    import library
    every = library.resolved(entry["library_places"][0])
    return {name: np.clip(labels.srgb(np.array(every[name]["colour"], dtype=float)) * 255, 0, 255).astype(np.uint8)
            for name in names}


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


def parts_take(inputs, take, entry, out):
    """One take's parts, its arrays and pictures under <out>/<take>/; its parts.json record."""
    import numpy as np
    import split_compare
    import turntable_views as views
    finishes = json.loads((inputs["maps"] / take / "map.json").read_text())["finishes"]
    mesh = split_compare.raw_model(take)
    part_of, face_label, per_map = laid(mesh, take, inputs, len(finishes))
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
    return {"method": "finish-map", "parts": rows, "judge_unknown": [], "measures": measures}


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
        "parts": sum(record["measures"]["parts"] for record in found.values())})


STEPS = {"inputs": inputs_step, "parts": parts_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
