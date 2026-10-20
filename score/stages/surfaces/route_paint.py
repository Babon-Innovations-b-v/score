"""The finish route's paint, `surfaces-paint` (free, here, after the bake): the paint runs in the bake's job on the
rented card (route_bake.py, #18, 2026-10-20: this PC's 14 GB cap failed heavy takes, crane-r1 peaked at 34.8 GB), so
this row takes the bake's painted takes over as its own output, which every reader of the paint reads (the check, the
assembly, the machines, the prop makers), and holds its gates: one surface a part, colour against the close-up (a
accepted gap's gate) and, set in the table, feet in one plane. The parts row's "off colour" measure names the colour
faults before the bake; the gates fail them here, after it.

Output as the rented paint's: painted.json (with the takes the parts left out), labelled/<take>/.
"""
import pathlib
import shutil


def make_paint(inputs, out, seed, params):
    """The bake's painted.json and labelled folders copied into this output (as plain files: the input's checkout is
    read-only)."""
    baked = pathlib.Path(inputs["surfaces-bake"])
    for path in [baked / "painted.json", *(baked / "labelled").rglob("*")]:
        if path.is_file():
            target = out / path.relative_to(baked)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
