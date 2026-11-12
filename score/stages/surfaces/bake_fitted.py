"""surfaces-bake made with each take's card job running inside/paint_fit.py in place of inside/paint_bake.py: the same
paint and bake, its last step through inside/layout_fit.py, so a model's texture layout that surfaces-check's
"texture layout sound" would fail is laid again before it bakes (#118). Set on the row in the stage table
(stages.layout_fitted), as recheck_picks is, so no row reading route_bake.py moves: every row whose code reaches it
(the surfaces package's readers) declares the scripts route_bake.py starts.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import route_bake  # noqa: E402

SCRIPT = "score/stages/surfaces/inside/paint_fit.py"


def make_bake(inputs, out, seed, params):
    """route_bake.make_bake, its card jobs' script SCRIPT (route_bake.card_job reads route_bake.SCRIPT)."""
    route_bake.SCRIPT = SCRIPT
    return route_bake.make_bake(inputs, out, seed, params)
