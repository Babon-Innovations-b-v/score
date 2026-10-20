"""The finish route's check, `surfaces-check` (free): bake_check.py's check, each baked surface held against the spec
the bake baked (its specs.json, route_bake.py): a part with the finish list's settings bakes its variant in the list's
token, roughness and metal under its settings name (route_settings), which the library alone does not know. Its own
module, so bake_check.py, in the crops', people's and finish-map lines' code versions, stays unedited.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import bake_check  # noqa: E402
import prop_env  # noqa: E402


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def check_step(inputs, out):
    """bake_check.check_step with the bake's specs over the place's library surfaces (library.by_library, which it
    reads them from), in this step's own process."""
    import library
    baked = json.loads((inputs["bake"] / "specs.json").read_text())
    by_library = library.by_library
    library.by_library = lambda name: {**by_library(name), **baked}
    bake_check.check_step(inputs, out)


STEPS = {"check": check_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
