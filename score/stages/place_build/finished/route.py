"""A made model's finish route in its place (#213): the surfaces finish route's rows (views, list, split, parts: the
prop benchmark's branch B, tools/props/bench/run/finish.py `finished`) run on a laid TRELLIS.2 model with the place's
own palette as its surface library, and its texel masks and decals written as the bench look's job (`look_job`)
under the place's `made/<entry>/finish/`, where the scene package's bake reads them (scene_package.finish_of): so the
place's bake draws the model as its bench look draws it, not as `refinish`'s palette parts.

    finish(folder, name, source) -> answer     the route run on the laid object `name`, from `source`'s picture

`source` names the picture the model was made from, as `make` takes it (take/<take>, concept/<n> or a picture's
path); it is refused unless its sha256 is the one the model's record keeps (maker's `picture`), so the masks and
decals are read through the picture the model's paint came from. The list's ask goes to Claude (EUR 0 on the
subscription, as the place line asks); views render on this PC's card.
"""
import json
import pathlib
import shutil
import sys

from score.stages import place_build

FINISH = "finish"  # under made/<entry>/: the route's rows, and its look job in `look/` (LOOK)
LOOK = "look/look.json"
FINAL = "-final.glb"  # a TRELLIS.2 entry's model file (maker: <entry>-final.glb)


def bench_finish():
    """tools/props/bench/run/finish.py, the route's runner on one made model."""
    folder = str(place_build.REPO / "tools/props/bench/run")
    if folder not in sys.path:
        sys.path.append(folder)
    import finish
    return finish


def route_library(folder):
    """The route's surface library from the place's palette (<folder>/palette.json, `palette`): (its materials.json
    content, its palette.json content {tokens, wear: the library's wear level nearest the place's wear, the place's
    dirt in the palette's dirt token}, no addresses, nothing left out), finish.library_written's form."""
    path = pathlib.Path(folder) / place_build.PALETTE
    if not path.is_file():
        raise place_build.Refused("no palette: lay the place's surface library first (palette <folder> <materials.json>)")
    taken = json.loads(path.read_text())
    worn = taken.pop("place_wear")
    method = json.loads((place_build.REPO / "data/library/materials.json").read_text())
    own = taken.get("recipes", {})  # a setting the place's copy lacks is the method's, as palette_spec reads it
    taken["recipes"] = {name: {**recipe, **own.get(name, {})} for name, recipe in method["recipes"].items()}
    for key in ("wear_levels", "colour_settings"):
        taken.setdefault(key, method.get(key, {}))
    taken.setdefault("kinds", {})
    taken.setdefault("pictures", {})
    level = min(taken["wear_levels"], key=lambda name: abs(float(taken["wear_levels"][name]) - worn["wear"]))
    dirt_token = taken.get("dirt") or min(taken["tokens"])
    palette = {"tokens": taken["tokens"], "wear": {"level": level, "dirt": worn["dirt"], "dirt_token": dirt_token}}
    return taken, palette, {}, {}


def made_model(folder, prim):
    """(the entry's id, its model file in the place's assets, its make record) of a laid TRELLIS.2 model; Refused for
    any other object."""
    from score.stages.place_build import finished
    address = finished.text(prim, "score:library")
    if not address or "@" not in address:
        raise place_build.Refused(f"{prim.GetName()} lays no library entry")
    _, record, copied = place_build.fetch(folder, address)
    models = [name for name in copied if name.endswith(FINAL)]
    if record.get("kind") != "model" or len(models) != 1:
        raise place_build.Refused(f"{address}: not a made model (one {FINAL} file): its finish is its entry's own")
    entry = models[0][:-len(FINAL)]
    made = pathlib.Path(copied.get(f"{entry}.json", ""))
    if not made.is_file() or "picture" not in json.loads(made.read_text()):
        raise place_build.Refused(f"{address}: its record keeps no picture it was made from (maker's `picture`)")
    return entry, pathlib.Path(copied[models[0]]), json.loads(made.read_text())


def held_picture(folder, source, made, work):
    """The cut-out picture `source` names (maker.picture_of), refused unless it is the one the model was made from."""
    from score.stages.place_build import maker
    picture, said = maker.picture_of(folder, source, None, work)
    if maker.sha256(picture) != made["picture"]["sha256"]:
        raise place_build.Refused(f"{source}: not the picture the model was made from ({made['picture']['source']})")
    return picture, said


def row_of(entry, made):
    """The route's row of the model: its id, its words (the name `make` was given) and its size (wide, deep, tall:
    the record's glTF box, x, z and y)."""
    wide, tall, deep = made["size_m"]
    return {"id": entry, "words": entry.rsplit("_trellis.", 1)[0].replace("_", " "), "size": [wide, deep, tall]}


def finish(folder, name, source):
    """The finish route run on the laid TRELLIS.2 model `name` from `source`'s picture (module docstring), its rows
    and look job written under made/<entry>/finish/ (made again from nothing each time); what it laid."""
    folder = pathlib.Path(folder)
    stage, place = place_build.opened(folder)
    prim = place_build.object_prim(stage, place, name)
    entry, model, made = made_model(folder, prim)
    out = folder / "made" / entry / FINISH
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    picture, said = held_picture(folder, source, made, out)
    row = row_of(entry, made)
    finish_tools = bench_finish()
    try:
        finish_tools.finished(model, picture, row, route_library(folder), out)
        look = out / pathlib.Path(LOOK).parent
        look.mkdir()
        job = json.loads(finish_tools.look_job(out, entry, model, finish_tools.look_view(None, out), look).read_text())
    except RuntimeError as why:  # the route's own named stops: no parts, no texels, texels of several pictures
        raise place_build.Refused(f"{name}: {why}") from why
    return {"name": name, "entry": entry, "picture": said, "look": str(out / LOOK),
            "slots": [mask["slot"] for mask in job["masks"]],
            "decals": sum(len(mask["spec"].get("decals") or []) for mask in job["masks"]),
            "hardware": len(job.get("hardware") or [])}
