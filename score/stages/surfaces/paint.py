"""The g-texture method's naming of a split's parts (g_texture.py): each part asked of the judge, outlined on the
close-up's picture for the parts it shows and on the raw model's own texture drawn unlit round a turntable
(multiview.py) for every other part, each on the view that shows most of it; the judge's answers read back by
majority (part_judge.vote); each face's seen colour; neighbouring parts of one surface joined where their colours
agree (colour_joined_parts, MaPa's merge); and the raw model laid on its finished model (finished_frame). No model
runs here.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PROPS = HERE.parents[2] / "tools/props"  # the prop tool chain this stage reads (labels, the judge, the cloud)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROPS))
sys.path.insert(0, str(PROPS / "library"))
import labels  # noqa: E402
import multiview  # noqa: E402
import part_judge  # noqa: E402

# Two neighbouring parts named one surface join only when their colours lie within this (Lab)
# (MaPa's merge: same class and same unlit colour, its CIE threshold 2 on albedo is too fine for a picture's).
MERGE_COLOUR = 12.0


def raw_mesh(take):
    import trimesh
    return labels.welded(trimesh.load(labels.PIXAL / f"{take}.glb", force="mesh", process=False))


def view_of(mesh, take, picture_path):
    """(picture, seen, row, column) as labels.picture_view gives it, for any picture in the close-up's frame."""
    picture = Image.open(picture_path).convert("RGBA")
    rgba = np.asarray(picture, dtype=np.float64) / 255
    camera = json.loads((labels.PIXAL / f"{take}.svviews" / "transforms.json").read_text())
    seen, row, column = labels.seen_faces(mesh, camera, rgba.shape[:2])
    return picture, seen & (rgba[row, column, 3] > 0.5), row, column


def views(mesh, arguments):
    """The front view and, with --turntable, every turntable view of the raw model's own texture ({name: view})."""
    front = view_of(mesh, arguments.take, arguments.front)
    if not arguments.turntable:
        return front, {}
    return front, {view: multiview.turntable_view(arguments.work, arguments.take, view, mesh)
                   for view in multiview.view_names(arguments.work, arguments.take)}


def seen_colours(mesh, front, others):
    """Each face's colour (Lab): from the front where the front sees it, else the mean over the turntable views that
    see it, NaN where none does."""
    colours = labels.face_colours(mesh, front[:4])
    if others:
        stacked = np.stack([labels.face_colours(mesh, view[:4]) for view in others.values()])
        seen = ~np.isnan(stacked[..., 0])
        behind = np.where(seen.any(0)[:, None], np.nansum(stacked, axis=0) / np.maximum(seen.sum(0), 1)[:, None],
                          np.nan)
        missing = np.isnan(colours[:, 0])
        colours[missing] = behind[missing]
    return colours


def asked_parts(part_of, front, others):
    """{view name: parts asked on it}: on the front ("") each part it shows on SEEN_LEAST faces; every other part on the
    turntable view that draws most of its pixels, when that is SEEN_LEAST or more (pixels drawn, not faces seen: a
    shell just inside another passes the depth test and shows nothing to outline)."""
    count = int(part_of.max()) + 1
    drawn = [np.bincount(pixel_parts(part_of, view)[pixel_parts(part_of, view) >= 0], minlength=count)
             for view in others.values()]
    shown = np.stack([np.bincount(part_of[front[1]], minlength=count), *drawn])
    asked = {"": [part for part in range(count) if shown[0, part] >= labels.SEEN_LEAST]}
    names = list(others)
    for part in range(count):
        if part in asked[""] or not names:
            continue
        best = int(shown[1:, part].argmax())
        if shown[1 + best, part] >= labels.SEEN_LEAST:
            asked.setdefault(names[best], []).append(part)
    return asked


def judge_name(arm, take, view):
    """The judge's take name for the questions asked on one view (the front's is "<arm>~<take>")."""
    return f"{arm}~{take}" if not view else f"{arm}@{view}~{take}"


def pixel_parts(part_of, view):
    """Each pixel's part: from the view's face map where it has one (a turntable view), else its seen faces' pixels."""
    if len(view) > 4:
        faces = view[4]
        return np.where(faces >= 0, part_of[np.maximum(faces, 0)], -1)
    picture, seen, row, column = view[:4]
    return part_judge.part_pixels(part_of, seen, row, column, np.asarray(picture).shape[:2])


def ask(arguments, mesh, part_of, materials):
    """Each asked part's outlined picture and question, on the view it is asked on; the question names."""
    front, others = views(mesh, arguments)
    asked = []
    for view, parts in asked_parts(part_of, front, others).items():
        shown = others[view] if view else front
        asked += part_judge.write_questions(arguments.questions, judge_name(arguments.arm, arguments.take, view),
                                            shown[0], pixel_parts(part_of, shown), parts, arguments.object, materials)
    return asked


def judged_parts(arguments, part_of, materials, front, others):
    """{part: (surface, what the judge called it)} from every view's answers (a majority of its asks,
    part_judge.vote), a strongly coloured pick on a part the picture shows colourless set aside
    (labels.paint_by_own_parts' rule); the set-aside parts; and the asked parts no surface won (unknown)."""
    count = int(part_of.max()) + 1
    names, anchors = labels.anchors_of(materials)
    found, set_aside, undecided = {}, [], []
    for view, asked in asked_parts(part_of, front, others).items():
        shown = others[view] if view else front
        asked_as = judge_name(arguments.arm, arguments.take, view)
        answers = part_judge.judged(arguments.answers, asked_as, count, list(materials))
        undecided += [part for part in part_judge.unknown(arguments.answers, asked_as, count, list(materials))
                      if part in asked]
        vivid = labels.part_vividness(pixel_parts(part_of, shown), labels.picture_lab(shown[0]), count)
        for part in asked:
            if part not in answers:
                continue
            surface = answers[part][0]
            if np.hypot(*anchors[names.index(surface)][1:]) > labels.SATURATED and vivid[part] < labels.NEUTRAL:
                set_aside.append(part)
            else:
                found[part] = answers[part]
    return found, set_aside, sorted(undecided)


def colour_joined_parts(mesh, part_of, chosen, colours):
    """labels.joined_parts with MaPa's second condition (EXPERIMENTAL): neighbouring parts join where the judge named
    one surface for both and their colours (labels.part_colour, Lab) lie within MERGE_COLOUR; parts with too few seen
    faces for a colour join on the surface alone."""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
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
    import trimesh
    np.random.seed(0)
    final = trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh")
    matrix, gap = labels.onto_finished(mesh.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                       labels.finish_turn(take))
    return matrix, gap, final.bounds
