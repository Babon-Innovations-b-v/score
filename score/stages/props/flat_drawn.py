"""The likeness row's drawn size of a flat row's model laid as the bake lays it: by its face, its depth held apart.

The bake lays a flat row's model (the model gate's shape class "flat") by its face, its depth at most 3 times its
row's (score/stages/surfaces/flat_fit.py, #10, 2026-11-12). likeness_row.drawn_size fitted the baked model as one
within its row (bake_job.fit_within), so on a flat row its depth bound again: quarters' picture frame, baked 0.15 by
0.178 by 0.06 m for its 0.15 by 0.2 by 0.02 m row, was drawn 0.052 by 0.02 by 0.06 and its wall read 1.7 mm ("thin
and in proportion" failed), 5.4 mm at the size it was baked. Held, a flat row's model is drawn through
flat_fit.face_fit, at the size the bake lays it; every other row (a person, a chunky or slender one) is drawn by
likeness_row's own drawn_size, as before.

A sheet row is judged a sheet by its row, its wall held to its row's read thickness (`model_checks`). Drawn by its
face, a curled sheet keeps its curl as its depth: habitat's paper note, a solid slab 9.5 to 11 mm through its face on
its 0.2 by 0.01 by 0.3 m row (every ray through it two hits), its curl 2.7 cm deep, was drawn 0.2 by 0.027 by 0.287,
no longer under flat_sheet.SHEET_SHARE of its longest, so likeness_row.sheet refused it and its wall was read along
its rim's tilted normals, 1.8 mm, and "thin and in proportion" failed (Buy 97, 2026-11-13). A drawn size carries its
row's size (`Drawn`); a row that is a sheet by its own size (likeness_row.sheet), drawn thicker than its row, has its
wall read straight through its face, a ray crossing the mesh more than once reading 0 (`solid`), and held to the model
gate's least wall at its row's thinnest side: a hollow shell, a one-sided plane or a sheet far thinner than its row
still fails. Quarters' paper, poster and sticky note (their stored takes, 1 mm rows drawn 6 mm deep) read 5.5 to 5.8
mm and pass, as they did.

Apart from likeness_row.py so that only the likeness row takes it into its key: it declares it as a file of its own
(FILES, added in the framework's table, score/stages/__init__.py, which imports it and so installs it in every
process that runs a row); likeness_row is read by other rows through the prop route's table, and the table's make
wrappers keep a row's code version as it was. Importing this module puts `drawn_size` and `model_checks` in
likeness_row's place (`install`), once a process.
"""
import functools

import numpy as np

import score.stages.props.likeness_row as likeness_row
import score.stages.props.prop_data as prop_data

# The row that draws a baked model at its row's size, and the files it declares so its key takes this module and the
# bake's flat fit in.
ROWS = ("likeness",)
FILES = {"flat drawn": "{repo}/score/stages/props/flat_drawn.py",
         "flat fit": "{repo}/score/stages/surfaces/flat_fit.py"}
UNFLAT = likeness_row.drawn_size  # likeness_row's own: every row fitted as one within its row
UNSHEETED = likeness_row.model_checks  # likeness_row's own: a sheet by its drawn size alone


class Drawn(list):
    """A drawn size (wide, deep, tall) carrying its row's own size (`row`), so model_checks judges a sheet by its
    row."""

    def __init__(self, sides, row):
        super().__init__(sides)
        self.row = [float(side) for side in row]


@functools.cache
def flat_fit():
    """score/stages/surfaces/flat_fit.py, loaded by its path with the prop tools it imports (as bake_job_module)."""
    import importlib.util
    import sys
    surfaces = str(prop_data.REPO / "score/stages/surfaces")
    if surfaces not in sys.path:
        sys.path.append(surfaces)
    with prop_data.tools("props/library", "props"):
        spec = importlib.util.spec_from_file_location("flat_fit", prop_data.REPO / "score/stages/surfaces/flat_fit.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def drawn_size(row, model, rows, inputs, person=False):
    """likeness_row.drawn_size, a flat row's model (not a person's) drawn through flat_fit.face_fit: its baked
    `model`'s face within its row's face, its ground sides on the row's longer to longer, its depth at most
    flat_fit.depth_bound of the row's."""
    import score.stages.surfaces.tumble as tumble
    fit = flat_fit()
    if person or tumble.person(row) or not fit.flat(row["size"]):
        return UNFLAT(row, model, rows, inputs, person)
    points, _ = likeness_row.likeness.gltf_mesh(model)
    extents = points.max(0) - points.min(0)
    wide, deep, tall = (float(side) for side in row["size"])
    ground = sorted((wide, deep), reverse=extents[0] >= extents[2])
    across, tall, along = fit.face_fit(extents, [ground[0], tall, ground[1]])
    return Drawn([across, along, tall], row["size"])


def model_checks(path, size, kind, square, thin=False):
    """likeness_row.model_checks, a model drawn for a row that is a sheet by its own size (`size` a `Drawn`,
    likeness_row.sheet) and drawn thicker than its row held as a sheet at its row's thickness: its wall read straight
    through its face (`solid`) and at least the model gate's least wall at the thinner of its drawn and its row's
    thinnest side. A sheet drawn no thicker than its row is judged as likeness_row judges it."""
    found = UNSHEETED(path, size, kind, square, thin)
    row = getattr(size, "row", None)
    drawn = min(float(side) for side in size)
    if row is None or not likeness_row.sheet(kind, row) or min(row) >= drawn:
        return found
    import trimesh
    with prop_data.tools("props/gates", "props/library", "props"):
        import model as model_gate
    points, triangles = likeness_row.likeness.gltf_mesh(path)
    mesh = trimesh.Trimesh(points, triangles, process=True)
    wall = round(solid(mesh, laid_on(mesh, size), model_gate.SAMPLES), 4)
    checked = found["model_check"]
    checked.update(thinnest=wall, sheet=True, **{"pass": checked["spread"] <= model_gate.SPREAD_LIMIT
                                                 and wall >= model_gate.least_wall([min(row)])})
    return found


def solid(mesh, laid, samples):
    """A sheet's 5th-percentile wall straight through its face once fitted to `laid`, as likeness_row.through reads
    it (its rim band skipped), but a ray that meets the mesh again past its first stretch reads 0: drawn thicker than
    its row, a curled solid sheet is crossed once (habitat's paper note: every ray two hits), a hollow shell twice
    (its outer wall alone would read as thick as a thin row's sheet)."""
    fitted = mesh.copy()
    fitted.vertices = (fitted.vertices - fitted.bounds[0]) / np.maximum(fitted.extents, 1e-6) * np.array(laid)
    across = int(np.argmin(laid))
    rim = min(float(mesh.extents[across]), 0.25 * min(laid[side] for side in range(3) if side != across))
    starts = rim + np.random.default_rng(0).uniform(0, 1, (samples, 3)) * (np.array(laid) - 2 * rim)
    starts[:, across] = laid[across] + 0.01
    down = np.zeros((samples, 3))
    down[:, across] = -1
    where, index, _ = fitted.ray.intersects_location(starts, down, multiple_hits=True)
    walls = []
    for ray in np.unique(index):
        heights = np.unique(np.round(where[index == ray, across], 7))[::-1]  # a hit on a shared edge counted once
        walls.append(heights[0] - heights[1] if len(heights) == 2 else 0.0)
    return float(np.percentile(walls, 5)) if walls else 0.0


def laid_on(mesh, size):
    """`size` (wide, deep, tall) on the model's own axes as likeness_row.model_checks lays it: its ground sides on the
    model's longer to longer, y tall; a slender row's as one scale, its longest side the row's."""
    wide, deep, tall = (float(side) for side in size)
    ground = sorted((wide, deep), reverse=mesh.extents[0] >= mesh.extents[2])
    laid = [ground[0], tall, ground[1]]
    if likeness_row.thin_straight.slender(size):
        laid = (mesh.extents * max(laid) / mesh.extents.max()).tolist()
    return laid


def install():
    """`drawn_size` and `model_checks` in likeness_row's place (its object_record calls both by name)."""
    likeness_row.drawn_size = drawn_size
    likeness_row.model_checks = model_checks


install()
