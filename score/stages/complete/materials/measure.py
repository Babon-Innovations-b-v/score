"""A place's evidence for the materials checks, from the store (read only), written to a folder the judges read:

    <folder>/evidence.json   {"place", "outputs": {node: output read}, "objects": [{prim, model, row, kind, made,
                             near, px_per_m}], "models": [{prim, model, near, parts: [{part, border_m, smooth_m,
                             ragged}]}], "kit": [{model, prims, route, baked_by, known_by}], "bake_code": {route:
                             [{commit, at, subject}]}}

`objects` feeds texel.py, `models` (each model with two finishes or more, once) borders.py, `kit` and `bake_code`
kit_age.py. The place's accepted assembly is linked (assets.linked) under <cache>/<output>, where the pictures read it.
"""
import json
import pathlib

from score.stages.complete.materials import assets, borders, kit_age, meshes, texel

EVIDENCE = "evidence.json"


def read_outputs(store, place):
    """{node: accepted output} of the place's assembly and film (the film's cameras count as seen)."""
    found = {}
    for node in (f"assembly@{place}", f"demo-film@{place}"):
        output = store.accepted(node)
        if output:
            found[node] = output
    return found


def json_file(folder, name):
    """A JSON file of an output folder, or None."""
    path = pathlib.Path(folder) / name
    return json.loads(path.read_text()) if path.exists() else None


def place_cameras(store, outputs, folder, place):
    """The cameras of the place's start views and of its film's frames."""
    film = outputs.get(f"demo-film@{place}")
    return assets.cameras(json_file(folder, "scene.json"), store.read_file(film, "views.json") if film else None)


def described(objects, rows, eyes):
    """Each laid object with its inventory row's kind and made, and its nearest camera."""
    return [dict(entry, kind=rows.get(entry["row"], {}).get("kind"), made=rows.get(entry["row"], {}).get("made"),
                 near=assets.nearest(entry["box"], eyes)) for entry in objects]


def drawn_models(folder, objects):
    """{model: its drawn meshes} of every model the place lays that has an asset file."""
    found = {}
    for entry in objects:
        if entry["model"] not in found:
            asset = assets.asset_file(folder, entry["model"])
            found[entry["model"]] = meshes.drawn(asset) if asset else []
    return found


def with_density(objects, drawn):
    """Each object with its model's texture pixels a metre at its laid scale."""
    return [dict(entry, px_per_m=texel.density(drawn[entry["model"]], entry["scale"] ** 2)) for entry in objects]


def nearest_of(objects, model):
    """The model's object nearest a camera (any of them when none is seen)."""
    laid = [entry for entry in objects if entry["model"] == model]
    seen = [entry for entry in laid if entry["near"] is not None]
    return min(seen, key=lambda entry: entry["near"]) if seen else laid[0]


def border_models(objects, drawn):
    """Each model with two finishes or more, once, measured at its nearest object's scale."""
    found = []
    for model, meshes_of in drawn.items():
        if not any(len(mesh.finishes) >= 2 for mesh in meshes_of):
            continue
        entry = nearest_of(objects, model)
        found.append({"prim": entry["prim"], "model": model, "near": entry["near"],
                      "parts": borders.measured_parts(meshes_of, entry["scale"])})
    return found


def kept(entry):
    """An object as the evidence keeps it (its box left out)."""
    return {name: value for name, value in entry.items() if name not in ("box", "group")}


def gather(store, place, folder, cache):
    """Measure a place into its evidence folder; the evidence file's path, or None when it has no accepted assembly."""
    outputs = read_outputs(store, place)
    output = outputs.get(f"assembly@{place}")
    if output is None:
        return None
    linked = assets.linked(store, output, pathlib.Path(cache) / output)
    rows = assets.inventory_rows(place)
    objects = described(assets.laid_objects(assets.opened(linked, place), place), rows,
                        place_cameras(store, outputs, linked, place))
    drawn = drawn_models(linked, objects)
    objects = with_density(objects, drawn)
    seed = (json_file(linked, "inputs.json") or {}).get("models", {})
    evidence = {"place": place, "outputs": outputs, "linked": str(linked),
                "objects": [kept(entry) for entry in objects],
                "models": border_models(objects, drawn), "kit": kit_age.kit_models(objects, rows, seed),
                "bake_code": {route: kit_age.code_commits(route) for route in kit_age.ROUTES}}
    path = pathlib.Path(folder) / EVIDENCE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=1))
    return path
