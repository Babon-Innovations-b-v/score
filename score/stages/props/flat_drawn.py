"""The likeness row's drawn size of a flat row's model laid as the bake lays it: by its face, its depth held apart.

The bake lays a flat row's model (the model gate's shape class "flat") by its face, its depth at most 3 times its
row's (score/stages/surfaces/flat_fit.py, #10, 2026-11-12). likeness_row.drawn_size fitted the baked model as one
within its row (bake_job.fit_within), so on a flat row its depth bound again: quarters' picture frame, baked 0.15 by
0.178 by 0.06 m for its 0.15 by 0.2 by 0.02 m row, was drawn 0.052 by 0.02 by 0.06 and its wall read 1.7 mm ("thin
and in proportion" failed), 5.4 mm at the size it was baked. Held, a flat row's model is drawn through
flat_fit.face_fit, at the size the bake lays it; every other row (a person, a chunky or slender one) is drawn by
likeness_row's own drawn_size, as before.

Apart from likeness_row.py so that only the likeness row takes it into its key: it declares it as a file of its own
(FILES, added in the framework's table, score/stages/__init__.py, which imports it and so installs it in every
process that runs a row); likeness_row is read by other rows through the prop route's table, and the table's make
wrappers keep a row's code version as it was. Importing this module puts `drawn_size` in likeness_row's place
(`install`), once a process.
"""
import functools

import score.stages.props.likeness_row as likeness_row
import score.stages.props.prop_data as prop_data

# The row that draws a baked model at its row's size, and the files it declares so its key takes this module and the
# bake's flat fit in.
ROWS = ("likeness",)
FILES = {"flat drawn": "{repo}/score/stages/props/flat_drawn.py",
         "flat fit": "{repo}/score/stages/surfaces/flat_fit.py"}
UNFLAT = likeness_row.drawn_size  # likeness_row's own: every row fitted as one within its row


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
    return [across, along, tall]


def install():
    """`drawn_size` in likeness_row's place (its record_of calls drawn_size by name)."""
    likeness_row.drawn_size = drawn_size


install()
