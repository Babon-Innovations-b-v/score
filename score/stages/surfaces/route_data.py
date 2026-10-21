"""The finish route's environment data: each take's model and close-up, and the environment files each of its rows
declares (Stage.files, a function of the place). Kept apart from the rows' code, as surface_data.py is.

A take's model is its raw Pixal3D take (`{home}/work/pixal/<take>.glb`), the one the paint lays on its finished
model; a take whose raw take is not here has none, and the views row names it in its gate's fail before anything is
asked. Its close-up is the take's own (`<take>.svviews/input.png`) while it is there, else a stand-in, the model's
own texture rendered from the front (`route_cast`), named a stand-in in every output and verdict that reads it.
"""
import json
import pathlib

import surface_data as data

STAND_IN = "stand-in: the model's own texture from the front, not a close-up"


def pixal_folder():
    import prop_env
    return prop_env.PROPS_HOME / "work/pixal"


def model_path(take):
    """The take's raw model, or None when it is not here."""
    found = pixal_folder() / f"{take}.glb"
    return found if found.exists() else None


def close_up_path(take):
    """The take's own close-up, or None when it has none here (the route renders a stand-in)."""
    found = pixal_folder() / f"{take}.svviews" / "input.png"
    return found if found.exists() else None


def model_files(place):
    """{name: path} of every take's model and own close-up that is there (of the takes the runner's object filter
    keeps, graph.selected); a take with no model here is left out and named by the views row."""
    from score import graph
    objects = graph.selected()
    found = {}
    for take in data.takes(place):
        if objects is not None and take not in objects:
            continue
        model = model_path(take)
        if model is not None:
            found[f"model {take}"] = str(model)
        close_up = close_up_path(take)
        if close_up is not None:
            found[f"close-up {take}"] = str(close_up)
    return found


def shape_files(place):
    """The views and split rows' files: the place's data, its takes' raw models and close-ups."""
    return {"surfaces": data.pattern(place), **model_files(place)}


def library_files(place):
    """The rows that read the library (list, parts, recheck): shape_files and the method's library (the scene's
    surfaces, tokens and wear are its surface-library's and scene palette's, inputs, never place.json)."""
    return {**shape_files(place), "library": "{data}/library"}


def parts_files(place):
    """The parts row's files: library_files and the place's kit with the code its kit surfaces are read from
    (surface_data.parts_files' kit entries), so a finish takes the room's own kit surface."""
    kit = {name: pattern for name, pattern in data.parts_files(place).items() if name.startswith("kit")}
    return {**library_files(place), **kit}


def takes(inputs, params):
    """The place and {take: entry} the row works on: every take of the place's data (its input `surfaces`), or
    those the runner's object filter keeps."""
    found = json.loads(pathlib.Path(inputs["surfaces"]).read_text())
    kept = params.get("objects")
    return found["place"], {take: entry for take, entry in found.get("takes", {}).items()
                            if kept is None or take in kept}


def takes_written(out, inputs, params):
    """takes.json in the output: the place and the takes the row worked on; the place and those takes."""
    place, found = takes(inputs, params)
    (out / "takes.json").write_text(json.dumps({"place": place, "takes": found}, indent=1))
    return place, found

