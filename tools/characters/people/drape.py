"""Read a drape GarmentCode simulated: the cloth as it hangs on the body, and what each point is.

GarmentCode (MIT) turns a sewing pattern into cloth and drops it onto the body in NVIDIA Warp; it
runs outside the repo, once, and leaves a folder with the cloth (`*_sim.obj`, centimetres) and a
line per point naming the pattern panel it was cut from (`*_sim_segmentation.txt`). A point on a
seam is labelled `stitch` rather than a panel, and takes the commonest label round it.
"""
import numpy as np
import trimesh

CENTIMETRES = 0.01
# How many rounds a seam point's label is voted in from its neighbours before it gives up.
VOTING_ROUNDS = 10


def read_cloth(folder):
    """The cloth's points in metres, its triangles, and the raw label of every point.

    The positions and faces are read straight from the file: trimesh would split points along
    the file's texture seams, and then the labels, one a point, would no longer line up.
    """
    points, faces = [], []
    for line in next(folder.glob("*_sim.obj")).read_text().splitlines():
        if line.startswith("v "):
            points.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            corners = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            for index in range(1, len(corners) - 1):
                faces.append([corners[0], corners[index], corners[index + 1]])
    labels = [line.strip() for line in
              next(folder.glob("*_sim_segmentation.txt")).read_text().split("\n") if line.strip()]
    if len(labels) != len(points):
        raise ValueError(f"{len(labels)} labels for {len(points)} points in {folder}")
    return np.array(points) * CENTIMETRES, np.array(faces), labels


def limb_of(panel):
    """Which limb a panel dresses, or the torso: a sleeve follows its own arm, a trouser leg its
    own leg, and nothing else may take their weights."""
    if panel.startswith("pant_"):
        return "left_leg" if ("_l_" in panel or panel.endswith("_l")) else "right_leg"
    if "sleeve" in panel or "cuff" in panel:
        return "left_arm" if "left" in panel else "right_arm"
    return "torso"


def settled(labels, faces, fallback):
    """Every point's label, a missing one (None) voted in from the labelled points round it,
    round by round, so a seam point takes its label from points that already have one."""
    labels = np.array(labels, dtype=object)
    neighbours = trimesh.Trimesh(np.zeros((len(labels), 3)), faces, process=False).vertex_neighbors
    for _ in range(VOTING_ROUNDS):
        missing = [index for index, label in enumerate(labels) if label is None]
        if not missing:
            break
        for index in missing:
            around = [labels[other] for other in neighbours[index] if labels[other] is not None]
            if around:
                # A tie goes to the label that sorts last, the same way on every run (python
                # does not keep a set of strings in one order from run to run): so a seam
                # between a limb and the torso is the torso's, and a band round the torso closes.
                labels[index] = max(sorted(set(around), reverse=True), key=around.count)
    labels[labels == None] = fallback  # noqa: E711
    return labels.astype(str)


def panel_labels(labels):
    """Each point's panel, None on a seam."""
    return [None if label.startswith("stitch") else label.split(",")[0] for label in labels]


def work_suit_cloth(folder):
    """The work suit's cloth with GarmentCode's own collar taken off (a stiff stand collar
    replaces it): points, faces, each point's panel and its limb.

    The panels are settled first and the limbs read off them. A seam point on the collar's seam
    stays, so the cloth keeps its neckline."""
    points, faces, labels = read_cloth(folder)
    panels = settled(panel_labels(labels), faces, "torso")
    on_a_seam = np.array([label.startswith("stitch") for label in labels])
    dropped = (np.char.find(panels, "collar") >= 0) & ~on_a_seam
    kept_faces = faces[~dropped[faces].any(axis=1)]
    used, renumbered = np.unique(kept_faces, return_inverse=True)
    panels = panels[used]
    limbs = np.array([limb_of(panel) for panel in panels])
    return points[used], renumbered.reshape(-1, 3), panels, limbs


def space_suit_cloth(folder):
    """The space suit's coverall whole: points, faces and each point's limb, the limbs settled
    on the seams directly."""
    points, faces, labels = read_cloth(folder)
    limbs = [None if label.startswith("stitch") else limb_of(label.split(",")[0]) for label in labels]
    return points, faces, settled(limbs, faces, "torso")
