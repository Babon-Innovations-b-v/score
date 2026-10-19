"""A place's bake job written from git, inside the bake's make: no job file to keep or to lose (2026-10-19: the 30 job
files under the work folder went with the old disk, and every surface bake blocked on them).

    job_head(library_name, outside)               the job's top-level fields: script, density, wear, dirt, seed,
                                                  faces, specs, as the place's route writes them
    entry_of(place, model, inline, kit, inventory, labelled)  one model's make_chunky entry

A model's entry is the one its surface data writes out, else the route's own entry for it, written by the route's own
code over the place's data: an outside place's (tools/props/library/place_route.py `chunky_entry`, its kit record has
an `on_seat`: package.py's) sized by `place_route.made_size` over its labelled take and its inventory row, a kit
room's (tools/props/library/route.py `jobs`) at its laid size in data/kit/<place>.json. A model with neither fails the
make, by name: a hole, never a guessed size.

The world files it reads are the bake row's (surface_data.job_files). Kept small and apart from place_line.py on
purpose: the paid bake row's code version hashes it.
"""
import json

import library
import place_route
import route


class NoEntry(RuntimeError):
    """A model the place bakes whose entry nothing in git gives."""


def outside(kit):
    """Whether a kit record is an outside place's (place_route's package: it says where it sits on its seat)."""
    return "on_seat" in kit


def specs_of(library_name):
    """Every library surface the place's route bakes with: each variant by its own name and the place's own names
    (library.by_library, library.resolved), as both routes' `jobs` write them."""
    return dict(library.by_library(library_name), **library.resolved(library_name))


def job_head(library_name, is_outside):
    """The job's top-level fields, as the place's route writes its make_chunky job (place_route.chunky_jobs or
    route.jobs); its out and report are the bake's own."""
    wear, dirt = library.wear_of(library_name)
    density, faces = (place_route.DENSITY, 19000) if is_outside else (route.NEAR, route.CHUNKY_FACES)
    return {"script": "make_chunky.py", "density": density, "wear": wear, "dirt": dirt, "seed": 3, "faces": faces,
            "specs": specs_of(library_name)}


def details_of(kind, model):
    found = json.loads(place_route.DETAILS.read_text()).get(kind)
    if not found or "turn" not in found:
        raise NoEntry(f"no entry for {model}: kind {kind} has no details (data/library/details.json turn)")
    return found


def outside_entry(place, model, inventory, labelled):
    """place_route's entry for an outside place's model (one inventory row, named by its id), sized over its
    labelled take."""
    row = next((row for row in inventory.get("rows", []) if row["id"] == model), None)
    if row is None or labelled is None:
        raise NoEntry(f"no entry for {model}: no inventory row of that id, or no labelled take")
    own = details_of(f"{place}_{model}", model)
    size = place_route.made_size(labelled, place_route.kit_size(row["size"]), place_route.yaw_of(own["turn"]))
    planned = {"size": size, "faces": place_route.faces_for(model, row["size"])}
    return place_route.chunky_entry(model, planned, own, labelled.parent, labelled.name)


def laid_foot(piece):
    """How high a laid piece's foot stands over its floor (route.foot_of), its own `foot` where it says one."""
    return piece.get("foot", route.foot_of(piece["at"][1]))


def laid_near(piece):
    """Whether a laid piece comes within the player's reach (route: its middle under REACH_HIGH)."""
    up = piece["y"][1] if "y" in piece else 1.0
    return piece.get("near", piece["at"][1] + up * piece["size"][1] / 2 < route.REACH_HIGH)


def furniture_foot(model, inventory):
    """route.furniture's foot of a furniture model (`<row>_1`): its row's lowest spot, 0 with none."""
    row = next((row for row in inventory.get("rows", []) if f"{row['id']}_1" == model), None)
    if row is None:
        raise NoEntry(f"no entry for {model}: not laid in the kit and no inventory row <row>_1")
    return min((route.foot_of(spot["y"]) for spot in row.get("at", [])), default=0.0)


def child_of(model, kit, inventory):
    """route.children's kind and foot of a composite's child model (the hub's telephone on its comms desk): the kind
    of its parent's composite child (data/library/composites.json) of its name and size, standing on its parent's
    foot at its height there."""
    models = kit.get("models", {})
    parent = models[models[model]["child_of"]]
    composites = json.loads(route.COMPOSITES.read_text())
    kinds = [child["kind"] for child in composites.get(parent.get("prop"), {}).get("children", [])
             if f"{route.own_name(child['kind'])}_" in f"{model.rsplit('_', 1)[0]}_"
             and route.made_size(child["size"]) == route.made_size(models[model]["size"])]
    spots = [child["at"][1] for child in parent.get("children", []) if child["model"] == model]
    if not kinds or not spots:
        raise NoEntry(f"no entry for {model}: its parent's composite names no child of its name and size")
    return kinds[0], round(furniture_foot(models[model]["child_of"], inventory) + min(spots), 3)


def room_entry(model, kit, inventory):
    """route.jobs' entry for a kit room's model: at its laid size (its first piece's in the kit, or the furniture or
    composite child model's own), its kind's details."""
    laid = [piece for piece in kit.get("pieces", []) if piece.get("model") == model]
    own_model = kit.get("models", {}).get(model, {})
    if laid:
        kind, size = laid[0]["kind"], laid[0]["size"]
        near, foot = any(map(laid_near, laid)), min(map(laid_foot, laid))
    elif own_model.get("child_of") and own_model.get("size"):
        (kind, foot), size, near = child_of(model, kit, inventory), own_model["size"], True
    elif own_model.get("prop") and own_model.get("size"):
        kind, size, near, foot = own_model["prop"], own_model["size"], True, furniture_foot(model, inventory)
    else:
        raise NoEntry(f"no entry for {model}: not laid in the kit, no furniture or composite child size")
    own = details_of(kind, model)
    planned = {"kind": kind, "near": near}
    return {"name": model, "base": own["turn"], "size": [float(side) for side in size],
            "screens": own.get("screens", []), "cuts": own.get("cuts", []), "density": route.density_of(planned),
            "decals": own.get("decals", []), "foot": foot, "faces": route.faces_for(size),
            "regions": own.get("regions", []), "wall": own.get("wall", route.ROOM_WALL)}


def entry_of(place, model, inline, kit, inventory, labelled):
    """One model's make_chunky entry: `inline` (the surface data's own) when given, else its route's (module
    docstring). `kit`, `inventory`: the place's records ({} when it has none); `labelled`: its labelled take."""
    if isinstance(inline, str):
        raise NoEntry(f"no entry for {model}: the data names a job file ({inline}); write its entry out or drop it")
    if inline is not None:
        return dict(inline, name=model)
    if not kit:
        raise NoEntry(f"no entry for {model}: the data writes none and the place has no kit")
    if outside(kit):
        return outside_entry(place, model, inventory, labelled)
    return room_entry(model, kit, inventory)
