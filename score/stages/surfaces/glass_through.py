"""finish-route-split with what each glass shows through it (#201, owner's choice of 2026-11-25): tc5r's fridge showed
its white interior through its clear glass door, and the faces behind the glass (TRELLIS.2's wire shelves) took the
body's stainless steel from the texture's labels. The list now names, for a see-through finish, the finish the
close-up shows through it (route_list.THROUGH, its finishes' `through`); here every face first met behind such a
glass by the close-up's own camera takes that finish alone, once the split has filled and smoothed every face: forced
on the votes, those faces were fill sources for the faces no view sees, and tc6's fridge's 1802 hidden inner faces
behind its pane (NVIDIA's glass shelves) took the liner, see-through 1.0 to 0.734 (r202).

Behind the glass: the close-up's pixels cast through its camera (route_cast.close_up_camera, sampled as
route_cast.close_up_cast samples them) with every hit along each ray; a ray whose first face the laid close-up labels
a see-through finish with a `through` gives that finish to the first face it meets over PANE_DEPTH (of the model's
largest side) behind that first face, past the pane's own back. A take whose close-up was not laid (no own close-up,
camera or fit: route_views.laid_close_up) or that lists no `through` is split as before.

Set on the split row in the table (stages.glass_split), with the views row's files (each own close-up's camera,
route_views.files), so no row reading route_split.py moves. Output: route_split's; split.json's record of a take
names its `behind_glass` faces by finish where any were given.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_parts  # noqa: E402
import route_cast as cast  # noqa: E402
import route_split  # noqa: E402
import route_views  # noqa: E402

PANE_DEPTH = 0.02  # a glass pane's own back lies within this share of the model's largest side behind its front
SPLIT_TAKE, VOTED_FINISHES = route_split.split_take, route_split.voted_finishes  # route_split's own


def glasses(finishes):
    """{glass finish: the finish shown through it} (0-based) of the listed finishes: a see-through one (a glass
    family, or transparent or translucent words; never a lit one, which shows its own light) naming another."""
    found = {}
    for number, finish in enumerate(finishes):
        words = f"{finish.get('finish', '')} {finish.get('parts', '')}".lower()
        clear = (finish.get("family") in finish_parts.SEEN_THROUGH_FAMILIES
                 or any(word in words for word in finish_parts.SEEN_THROUGH_WORDS))
        if clear and finish.get("family") not in finish_parts.LIT_FAMILIES and finish.get("through") is not None:
            found[number] = int(finish["through"])
    return found


def behind_faces(hits, laid, shown, face_count):
    """Each face's finish seen through a glass, -1 where none: `hits` (face, ray, distance from the eye) of every
    hit along the close-up's rays, `laid` the laid close-up's finish per face (-1 none), `shown` {glass: finish}. A
    ray's first face laid as a glass gives its finish to the first face over PANE_DEPTH behind it."""
    faces, rays, distances = (np.asarray(column) for column in hits)
    found = np.full(face_count, -1)
    if not len(faces) or not shown:
        return found
    order = np.lexsort((distances, rays))
    faces, rays, distances = faces[order], rays[order], distances[order]
    starts = np.flatnonzero(np.r_[True, rays[1:] != rays[:-1]])
    first = np.repeat(starts, np.diff(np.r_[starts, len(rays)]))
    glass = laid[faces[first]]
    through = np.array([shown.get(int(finish), -1) for finish in glass])
    behind = np.flatnonzero((through >= 0) & (distances > distances[first] + PANE_DEPTH))
    chosen = behind[np.unique(rays[behind], return_index=True)[1]]  # each ray's nearest: sorted by distance in it
    found[faces[chosen]] = through[chosen]
    return found


def close_up_hits(model, camera_file, close_up):
    """(face, ray, distance) of every hit along the close-up's sampled pixels' rays through its camera, in the
    normalised model's frame (route_cast.close_up_cast's grid)."""
    from PIL import Image
    width, height = Image.open(close_up).size
    step = max(1, -(-max(width, height) // cast.CLOSE_UP_SIDE))
    columns, rows = np.meshgrid(np.arange(0, width, step), np.arange(0, height, step))
    camera = cast.close_up_camera(camera_file)
    ways = cast.pixel_ways(camera, (width, height), np.c_[columns.ravel() + 0.5, rows.ravel() + 0.5])
    middle, side = model.frame
    eye = (camera[0] - middle) / side
    faces, rays, points = model.mesh.ray.intersects_id(np.repeat(eye[None], len(ways), axis=0), ways,
                                                       multiple_hits=True, return_locations=True)
    return faces, rays, np.linalg.norm(np.asarray(points).reshape(-1, 3) - eye, axis=1)


def through_votes(inputs, take, listed, views):
    """Each face's finish seen through a glass (behind_faces), or None where the take has none to give."""
    shown = glasses(listed["finishes"])
    files = [inputs.get(f"{name} {take}") for name in ("model", "camera", "close-up")]
    if not shown or None in files or not (views / take / "close-up.npz").exists():
        return None
    model = cast.loaded(files[0])
    laid = route_split.per_view(views / take, listed["labels"], len(json.loads(
        (views / "views.json").read_text())[take]["regions"]), len(model.mesh.faces))[route_views.CLOSE_UP]
    return behind_faces(close_up_hits(model, files[1], files[2]), laid, shown, len(model.mesh.faces))


def forced(found, behind):
    """(part per face, finish per face) `found` with each face behind a glass given the finish it shows through it,
    each part parted where it now holds two finishes."""
    part_of, finish_of = found
    chosen = np.flatnonzero(behind >= 0)
    if not len(chosen):
        return found
    finish_of = finish_of.copy()
    finish_of[chosen] = behind[chosen]
    return np.unique(np.c_[part_of, finish_of], axis=0, return_inverse=True)[1].ravel(), finish_of


CURRENT = {}  # the make running: its inputs and views, and the take being split's faces behind a glass


def voted_finishes(mesh, votes, count):
    """route_split.voted_finishes, then the faces behind a glass of the take being split forced (forced): after
    the unseen faces took the finish nearest them, so a face no view sees never takes what shows through a glass."""
    found = VOTED_FINISHES(mesh, votes, count)
    behind = CURRENT.get("behind")
    return found if behind is None else forced(found, behind)


def split_take(folders, listed, record):
    """route_split.split_take with its faces behind a glass forced (through_votes, voted_finishes); its record names
    them by finish (`behind_glass`). The table answers it per take through kept.call (stages.PER_TAKE)."""
    take = folders["views"].name
    behind = through_votes(CURRENT["inputs"], take, listed, CURRENT["views"])
    CURRENT["behind"] = behind
    try:
        found = SPLIT_TAKE(folders, listed, record)
    finally:
        CURRENT.pop("behind")
    if behind is not None and (behind >= 0).any():
        found["behind_glass"] = {str(finish): int((behind == finish).sum())
                                 for finish in np.unique(behind[behind >= 0])}
    return found


def make_split(inputs, out, seed, params):
    """route_split.make_split with each take split by this module's split_take (looked up at each call, so the
    table's per-take keeping answers it) and voted_finishes."""
    CURRENT.update(inputs=inputs, views=pathlib.Path(inputs["finish-route-views"]))
    route_split.split_take = lambda *arguments: split_take(*arguments)
    route_split.voted_finishes = voted_finishes
    try:
        route_split.make_split(inputs, out, seed, params)
    finally:
        route_split.split_take, route_split.voted_finishes = SPLIT_TAKE, VOTED_FINISHES
        CURRENT.clear()
