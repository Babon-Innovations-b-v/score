"""The finish route's environment data: each take's model and close-up, and the environment files each of its rows
declares (Stage.files, a function of the place). Kept apart from the rows' code, as surface_data.py is.

A take's model is its raw Pixal3D take (`{home}/work/pixal/<take>.glb`) while that file is there, else the made model
the environment's release holds for it (the place's bake names the model, `models/<model>/<model>.glb` in
data/assets/world1.json), else none: the views row names that take in its gate's fail. Its close-up is the take's own
(`<take>.svviews/input.png`) while it is there, else a stand-in, the model's own texture rendered from the front
(`route_cast`), named a stand-in in every output and verdict that reads it.
"""
import json
import pathlib
import sys

import surface_data as data

REPO = pathlib.Path(__file__).resolve().parents[3]
ASSETS = REPO / "tools/assets"
if str(ASSETS) not in sys.path:
    sys.path.append(str(ASSETS))

import world as world_assets  # noqa: E402

STAND_IN = "stand-in: the model's own texture from the front, not a close-up"


def pixal_folder():
    import prop_env
    return prop_env.PROPS_HOME / "work/pixal"


def released(place, take):
    """The release's made model of a take (the place's bake names it), as its manifest name, or None."""
    models = data.record(place).get("bake", {}).get("models", {})
    names = [f"models/{model}/{model}.glb" for model, named in sorted(models.items()) if named == take]
    files = world_assets.manifest()["files"]
    return next((name for name in names if name in files), None)


def model_path(place, take):
    """The file a take's model is read from: its raw take, else its released model, else None."""
    raw = pixal_folder() / f"{take}.glb"
    if raw.exists():
        return raw
    name = released(place, take)
    return world_assets.local_folder(world_assets.manifest()) / name if name else None


def close_up_path(take):
    """The take's own close-up, or None when it has none here (the route renders a stand-in)."""
    found = pixal_folder() / f"{take}.svviews" / "input.png"
    return found if found.exists() else None


def model_files(place):
    """{name: path} of every take's model and own close-up that is there; a take with neither model is left out and
    named by the views row."""
    found = {}
    for take in data.takes(place):
        model = model_path(place, take)
        if model is not None:
            found[f"model {take}"] = str(model)
        close_up = close_up_path(take)
        if close_up is not None:
            found[f"close-up {take}"] = str(close_up)
    return found


def shape_files(place):
    """The views and parts rows' files: the place's data, its takes' models and close-ups, the release's manifest."""
    return {"surfaces": data.pattern(place), "assets": "{data}/assets/world1.json", **model_files(place)}


def library_files(place):
    """The rows that read the library (list, fill, recheck): shape_files, the library, the places and the palette."""
    return {**shape_files(place), "library": "{data}/library", "places": "{data}/definitions/place.json",
            "tokens": "{repo}/design/tokens/tokens.json"}


def takes(inputs, params):
    """The place and {take: entry} the row works on: every take of the place's data (its input `surfaces`), or
    those the runner's object filter keeps."""
    found = json.loads(pathlib.Path(inputs["surfaces"]).read_text())
    kept = params.get("objects")
    return found["place"], {take: entry for take, entry in found.get("takes", {}).items()
                            if kept is None or take in kept}


def takes_written(out, inputs, params):
    """takes.json in the output: the place and the takes the row worked on (later rows read it); those takes."""
    place, found = takes(inputs, params)
    (out / "takes.json").write_text(json.dumps({"place": place, "takes": found}, indent=1))
    return found


def takes_read(folder):
    """{take: entry} an earlier row of the route wrote."""
    return json.loads((pathlib.Path(folder) / "takes.json").read_text())["takes"]
