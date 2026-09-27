"""Straighten a made prop part by part, and give each part one real finish.

    bash tools/props/run.sh --straighten crate-1
    bash tools/props/run.sh --straighten drone-6 --finish 0=solar 1=yellow

A generated mesh is one welded lump with washed-out, blotchy colour baked from the picture's light.
This is the step after it, and the runner does it to every take:

  1. scraps that float off the body are dropped, and the surface is ironed flat without rounding
     its edges (denoise.py);
  2. the faces are sorted into a few groups by their own colour, and each group is named as the
     nearest real finish: silver foil, gold foil, white paint, solar cells and so on;
  3. the lump is cut into parts (parts.py); every part takes one finish, stray blobs take their
     neighbours', and parts of one finish that fill a straight shell together are joined;
  4. each part is replaced by its convex hull, the tightest straight-sided shell round it, painted
     flat in its finish.

It writes `<name>-straight.glb` beside the mesh it started from, and a report the review page reads,
so a straightened take shows beside its lump. The groups and the names they got are printed; if a
name is wrong, run it again with `--finish group=name` for that group.

What it costs: a hollow cannot survive in a convex part, so recesses fill in. Measured on the three
craft (#55): 57 to 90 parts cut, about 15 seconds each, and the owner's word was "a massive
improvement".
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paths import MESHES  # noqa: E402

import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402

from denoise import denoise  # noqa: E402
from finish import take_out_ripples  # noqa: E402
from parts import adopt, choose, cut, finish_shares, join, piece_of_each_face, thinned  # noqa: E402

# The finishes a part can take, as the colour each is painted. The look draws them matte with ink
# lines; the names stay in the report so a finish can be mapped to a token later.
FINISHES = {
    "silver": (204, 209, 214),
    "gold": (219, 163, 61),
    "copper": (199, 110, 56),
    "white": (232, 234, 232),
    "black": (26, 26, 28),
    "solar": (18, 23, 46),
    "metal": (179, 184, 191),
    "grey": (120, 128, 135),
    "yellow": (242, 194, 26),
}
GROUPS = 7
# A floating piece smaller than this share of the faces, and this short, is a scrap.
SCRAP_SHARE = 0.004
SCRAP_REACH = 0.06


def lab(rgb):
    """Colours in 0..1 into a rough perceptual space, so nearest means what the eye means."""
    linear = np.clip(rgb, 0, 1) ** 2.2
    xyz = linear @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192],
                             [0.1805, 0.0722, 0.9505]])
    xyz = xyz / np.array([0.9505, 1.0, 1.089])
    root = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * root[:, 1] - 16, 500 * (root[:, 0] - root[:, 1]),
                     200 * (root[:, 1] - root[:, 2])], axis=1)


def welded(mesh):
    """The same surface with its seams closed, so pieces and neighbours mean what they look like."""
    copy = trimesh.Trimesh(mesh.vertices.copy(), mesh.faces.copy(), process=False)
    copy.merge_vertices(merge_tex=True, merge_norm=True)
    return copy


def without_scraps(mesh, colours):
    """The welded mesh and its face colours, minus pieces that are both few faces and short."""
    joined = welded(mesh)
    adjacency = joined.face_adjacency
    size = len(joined.faces)
    count, label = connected_components(
        coo_matrix((np.ones(len(adjacency)), (adjacency[:, 0], adjacency[:, 1])), shape=(size, size)),
        directed=False)
    sizes = np.bincount(label, minlength=count)
    corners = joined.vertices[joined.faces].reshape(-1, 3)
    low = np.full((count, 3), np.inf)
    high = np.full((count, 3), -np.inf)
    np.minimum.at(low, np.repeat(label, 3), corners)
    np.maximum.at(high, np.repeat(label, 3), corners)
    reach = np.linalg.norm(high - low, axis=1)
    scrap = (sizes < SCRAP_SHARE * size) & (reach < SCRAP_REACH * np.linalg.norm(joined.extents))
    keep = ~scrap[label]
    kept = trimesh.Trimesh(joined.vertices, joined.faces[keep], process=False)
    kept.remove_unreferenced_vertices()
    return kept, colours[keep]


def face_colours(mesh):
    """Each face's generated colour, lifted so its brightest panels are bright."""
    colour = np.asarray(mesh.visual.vertex_colors)[:, :3][mesh.faces].mean(1) / 255
    return np.clip(colour / max(np.percentile(colour.max(1), 97), 1e-3), 0, 1)


def ironed(mesh, strength):
    """The surface ironed flat between its edges, then the last ripples taken out."""
    return take_out_ripples(denoise(mesh, strength=strength), 6, 35)


def colour_groups(mesh, colours, rounds=12):
    """Sort faces into a few groups by colour, then let each face side with its neighbours.
    Colour counts double against brightness, because brightness is mostly the picture's shading."""
    points = lab(colours)
    points[:, 1:] *= 2.0
    generator = np.random.default_rng(4)
    centres = points[generator.choice(len(points), GROUPS, replace=False)]
    for _ in range(50):
        group = np.argmin(((points[:, None] - centres[None]) ** 2).sum(-1), axis=1)
        centres = np.array([points[group == index].mean(0) if (group == index).any() else centres[index]
                            for index in range(GROUPS)])
    adjacency = mesh.face_adjacency
    for _ in range(rounds):
        votes = np.zeros((len(group), GROUPS))
        np.add.at(votes, (adjacency[:, 0], group[adjacency[:, 1]]), 1)
        np.add.at(votes, (adjacency[:, 1], group[adjacency[:, 0]]), 1)
        np.add.at(votes, (np.arange(len(group)), group), 1.2)
        group = votes.argmax(1)
    return group


def named(colours, group, overrides):
    """Each group's finish: what the run was told, else the finish nearest its colour."""
    targets = lab(np.array(list(FINISHES.values()), dtype=float) / 255)
    names = {}
    for index in np.unique(group):
        if index in overrides:
            names[index] = overrides[index]
            continue
        centre = lab(colours[group == index].mean(0)[None])[0]
        # the generated colour usually comes out greyed, so it is matched as it is and with its
        # colour strengthened, whichever lands nearer; hue counts for more than how light it is
        distance = np.minimum.reduce([(0.5 * (targets[:, 0] - centre[0])) ** 2 + ((targets[:, 1:] - boost * centre[1:]) ** 2).sum(1)
                       for boost in (1.0, 1.6)])
        names[index] = list(FINISHES)[int(np.argmin(distance))]
    return names


def painted(hulls, chosen):
    """All parts in one mesh, each face painted flat in its part's finish."""
    pieces = []
    for hull, finish in zip(hulls, chosen):
        corners = hull.vertices[hull.faces].reshape(-1, 3)
        piece = trimesh.Trimesh(corners, np.arange(len(corners)).reshape(-1, 3), process=False)
        piece.visual = trimesh.visual.ColorVisuals(
            piece, vertex_colors=np.tile(list(FINISHES[finish]) + [255], (len(corners), 1)).astype(np.uint8))
        pieces.append(piece)
    return trimesh.util.concatenate(pieces)


def straighten(name, overrides, threshold, strength):
    """Straighten MESHES/<name>.glb into MESHES/<name>-straight.glb, and write its report."""
    source = trimesh.load(MESHES / f"{name}.glb", force="mesh", process=False)
    mesh, colours = without_scraps(source, face_colours(source))
    mesh = ironed(mesh, strength)
    group = colour_groups(mesh, colours)
    names = named(colours, group, overrides)
    hulls = cut(mesh, threshold)
    ranked = finish_shares(mesh, np.array([names[index] for index in group], dtype=object),
                           piece_of_each_face(mesh, hulls), len(hulls))
    cut_count = len(hulls)
    hulls, chosen = join(hulls, adopt(hulls, choose(ranked)))
    out = painted([thinned(hull) for hull in hulls], chosen)
    target = MESHES / f"{name}-straight.glb"
    out.export(target)
    report = json.loads((MESHES / f"{name}-report.json").read_text())
    report.update({
        "name": f"{name}-straight",
        "faces_final": int(len(out.faces)),
        "vertices_final": int(len(out.vertices)),
        "size_kb": round(target.stat().st_size / 1000, 1),
        "parts": {"cut": cut_count, "after_joining": len(hulls)},
        "groups": {str(index): {"finish": names[index],
                                "colour": [round(float(value) * 255) for value in colours[group == index].mean(0)]}
                   for index in names},
        "colour": "one finish per straightened part",
    })
    (MESHES / f"{name}-straight-report.json").write_text(json.dumps(report, indent=1))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="a take already made, e.g. crate-1")
    parser.add_argument("--finish", nargs="*", default=[], metavar="GROUP=FINISH",
                        help=f"name a colour group's finish by hand; finishes: {', '.join(FINISHES)}")
    parser.add_argument("--pieces", type=float, default=0.05,
                        help="how tightly to cut: lower gives more, tighter parts")
    parser.add_argument("--strength", type=float, default=1.2, help="how hard to iron the surface")
    args = parser.parse_args()
    overrides = {}
    for pair in args.finish:
        group, finish = pair.split("=")
        if finish not in FINISHES:
            raise SystemExit(f"no finish called {finish}; there are {', '.join(FINISHES)}")
        overrides[int(group)] = finish
    report = straighten(args.name, overrides, args.pieces, args.strength)
    for group, facts in report["groups"].items():
        print(f"  group {group}: colour {facts['colour']} -> {facts['finish']}")
    print(f"{report['name']}: {report['parts']['cut']} parts cut, {report['parts']['after_joining']} "
          f"after joining, {report['faces_final']:,} triangles")


if __name__ == "__main__":
    main()
