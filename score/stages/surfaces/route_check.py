"""The finish route's check, `surfaces-check` (free): bake_check.py's check, each baked surface held against the spec
the bake baked (its specs.json, route_bake.py): a part with the finish list's settings bakes its variant in the list's
token, roughness and metal under its settings name (route_settings), which the library alone does not know, and a
finish with its own wear level is held against its surface worn to that level, not the scene's
(`own_wear_checked`); the scene's wear, dirt and surfaces are its scene palette's (palette_library.py, read from its
design), never place.json's.
A model a gate fails is a batch gap of it and its take (route_paint.item_gaps: the batch rule, its bake ran once in
the batch), named in batch-gaps.json with the gaps the inputs carry; the table moves the fault (stages.BATCH_GATES)
and complete fails it by name, so one model's fault no longer stops the place's line.
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


ROW = "surfaces-check"


def make_check(inputs, out, seed, params):
    """The check run in the prop environment, then each model a gate fails named a batch gap."""
    prop_env.handover(__file__, "check", inputs, out)
    import route_paint
    takes = take_of(inputs)
    route_paint.write_gaps(inputs, out, ROW, check_gates(), "checks.json", lambda found: found,
                           json.loads((out / "checks.json").read_text()),
                           lambda model: (model, takes.get(model)),
                           "the model's paint and bake ran once in the batch and failed this gate")


def check_gates():
    """Every gate the row holds as the table sets it (stages.bake_checked), guarded as the row's."""
    from surface_gates import guarded
    return tuple(guarded(name, judge) for name, judge in (
        ("baked matches its surfaces", bake_check.judge_lit), ("triangles within budget", bake_check.judge_triangles),
        ("stands level", bake_check.judge_stance)))


def take_of(inputs):
    """{model: its take} of the bake's entries (<surfaces-bake>/entries/<take>.json)."""
    return {model: path.stem for path in sorted((pathlib.Path(inputs["surfaces-bake"]) / "entries").glob("*.json"))
            for model in json.loads(path.read_text())}


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
