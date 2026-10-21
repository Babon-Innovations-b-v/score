"""The finish route's check, `surfaces-check` (free): bake_check.py's check, each baked surface held against the spec
the bake baked (its specs.json, route_bake.py): a part with the finish list's settings bakes its variant in the list's
token, roughness and metal under its settings name (route_settings), which the library alone does not know, and a
finish with its own wear level is held against its surface worn to that level, not the scene's
(`own_wear_checked`); the scene's wear, dirt and surfaces are its scene palette's (palette_library.py, read from its
design), never place.json's.
Its own module, so bake_check.py, in the crops', people's and finish-map lines' code versions, stays unedited.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import bake_check  # noqa: E402
import palette_library  # noqa: E402
import prop_env  # noqa: E402


def make_check(inputs, out, seed, params):
    prop_env.handover(__file__, "check", inputs, out)


def own_wear_checked(check_model):
    """bake_check.check_model with each surface whose spec carries its own wear (route_settings) measured again at
    that wear: the model is measured once at the place's wear, then once a distinct own wear, each such surface's
    record taken from its own."""
    def checked(name, entry, labelled, made, materials, dirt=0.0, wear=0.0):
        record = check_model(name, entry, labelled, made, materials, dirt, wear)
        own = {surface: materials[surface]["wear"] for surface in record["surfaces"]
               if "wear" in materials.get(surface, {})}
        for level in sorted(set(own.values())):
            again = check_model(name, entry, labelled, made, materials, dirt, level)
            record["surfaces"].update({surface: again["surfaces"][surface] for surface, its in own.items()
                                       if its == level})
        return record
    return checked


def check_step(inputs, out):
    """bake_check.check_step with the scene palette in place of data/definitions/place.json, in this step's own
    process: its surfaces the library's as the scene palette gives them (palette_library.specs) under the bake's
    specs, its wear and dirt the scene palette's (read from its design), each finish's own wear honoured."""
    import library
    palette = palette_library.read(inputs)
    baked = json.loads((inputs["bake"] / "specs.json").read_text())
    library.by_library = lambda name: {**palette_library.specs(palette), **baked}
    library.resolved = lambda name: {}
    library.wear_of = lambda name: palette_library.wear(palette)
    bake_check.check_model = own_wear_checked(bake_check.check_model)
    bake_check.check_step(inputs, out)


STEPS = {"check": check_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
