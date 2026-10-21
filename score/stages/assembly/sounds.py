"""The sound layer the assembly writes from the place's accepted sound output (score/stages/sound: sound.json and its
files), in tools/usd/sound.py's layout and with its prim writer (audio_prim), in place of the seed's sound layer:

    room     each room tone (role room): /<place>/Sound/Room/<name>, non-spatial, looping from the stage's start
    object   each object sound (role object, `on` a row id or a record entry's name): <prim>/Sound on every prim of
             that row (score:row) or of that name, spatial, looping
    motion   each motion's sound (role motion, `on` the moving prim): <prim>/Sound_<n>, from its start time code (the
             sound record gives one use a round of its moving thing, in the stage's seconds: sound/moving.py)
    bank     each surface's footstep, impact and scrape (role bank): /<place>/Sound/Bank/<name>, every library surface
             of the stage pointing at its own (score:sound:<happening>)

Each sound's files are copied into assets/ under their world names, over the seed's files of the same names; its
level, bus, loop, reach and ground thud are the record's. A use the stage has no prim for, or a sound with no file,
is returned in words: the assembly's `layers` gate fails on it.
"""
import json
import pathlib
import shutil

LAYER = "layers/sound.usda"
FILES = "files/"
NOTE = "The place's sounds, written by the assembly from its accepted sound output (score/stages/sound)."


def entry_of(sound):
    """A record's sound as tools/usd/sound.py's entry: its files by world name, its level and how it plays."""
    return {"file": [path.removeprefix(FILES) for path in sound["files"]], "volume_db": sound["volume_db"],
            "bus": sound.get("bus", ""), "loops": sound.get("loops", False), "reach": sound.get("reach", 0.0),
            "ground_thud": sound.get("ground_thud", False)}


def copy_files(made, record, out):
    """Every file of the record into the stage's assets/ under its world name."""
    for sound in record["sounds"].values():
        for path in sound["files"]:
            target = out / "assets" / path.removeprefix(FILES)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(made / path, target)


def prims_by_name(stage, place):
    """{row id or prim name: [prims]} over the place, so an object sound finds where it plays."""
    from pxr import Usd
    found = {}
    for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{place}")):
        row = prim.GetAttribute("score:row")
        names = {prim.GetName(), *([row.Get()] if row and row.Get() else [])}
        for name in names:
            found.setdefault(name, []).append(prim)
    return found


def take(made, root, inputs):
    """The place's sound layer written from its accepted sound output over the seed's; the uses placed nowhere."""
    from pxr import Sdf, Usd
    from score.stages.assembly.record import hold
    record = json.loads((made / "sound.json").read_text())
    copy_files(made, record, root.parent)
    path = root.parent / LAYER
    layer = Sdf.Layer.FindOrOpen(str(path)) or Sdf.Layer.CreateNew(str(path))
    layer.Clear()
    layer.documentation = NOTE
    layer.Save()
    hold(root, f"./{LAYER}")
    stage = Usd.Stage.Open(str(root))
    stage.SetEditTarget(Usd.EditTarget(layer))
    place = stage.GetDefaultPrim().GetName()
    entries = {name: entry_of(sound) for name, sound in record["sounds"].items()}
    uses = {role: [use for use in record["uses"] if use["role"] == role] for role in ("room", "object", "motion", "bank")}
    unplaced = room_tones(stage, place, uses["room"], entries, root.parent)
    unplaced += object_sounds(stage, place, uses["object"], entries, root.parent)
    unplaced += motion_sounds(stage, uses["motion"], entries, root.parent)
    unplaced += bank_sounds(stage, place, {use["sound"] for use in uses["bank"]}, entries, root.parent, inputs["sounds"])
    layer.Save()
    return unplaced


def room_tones(stage, place, uses, entries, out):
    """The room tones (and what the suit lets through outside), non-spatial loops from the stage's start."""
    import sound as tool
    from pxr import UsdGeom, UsdMedia
    UsdGeom.Scope.Define(stage, f"/{place}/Sound/Room")
    return [f"{use['sound']} (room): no file" for use in uses
            if not tool.audio_prim(stage, f"/{place}/Sound/Room/{use['sound']}", use["sound"], entries[use["sound"]],
                                   out, aural=UsdMedia.Tokens.nonSpatial, playback=UsdMedia.Tokens.loopFromStage,
                                   source=use["from"])]


def object_sounds(stage, place, uses, entries, out):
    """Each object sound, a spatial loop at every prim of its row or name."""
    import sound as tool
    from pxr import UsdMedia
    found = prims_by_name(stage, place) if uses else {}
    unplaced = []
    for use in uses:
        prims = found.get(use["on"], [])
        if not prims:
            unplaced.append(f"{use['sound']} (object): no prim of the row or name {use['on']} on the stage")
        for prim in prims:
            if not tool.audio_prim(stage, prim.GetPath().AppendChild("Sound"), use["sound"],
                                   dict(entries[use["sound"]], loops=True), out, aural=UsdMedia.Tokens.spatial,
                                   playback=UsdMedia.Tokens.loopFromStage, source=use["from"]):
                unplaced.append(f"{use['sound']} (object): no file")
    return unplaced


def motion_sounds(stage, uses, entries, out):
    """Each motion's sound, spatial at the moving prim from its start (each use one round's, in the stage's
    seconds); a looping one plays until its end."""
    import sound as tool
    from pxr import UsdMedia
    rate = stage.GetTimeCodesPerSecond()
    unplaced, counted = [], {}
    for use in uses:
        target = stage.GetPrimAtPath(use["on"]) if use["on"] else None
        if not target:
            unplaced.append(f"{use['sound']} (motion): no moving prim {use['on']} on the stage")
            continue
        number = counted[use["on"]] = counted.get(use["on"], -1) + 1
        until = use.get("loops_until")
        end = None if until is None else float(until) * rate
        if not tool.audio_prim(stage, target.GetPath().AppendChild(f"Sound_{number}"), use["sound"],
                               entries[use["sound"]], out, aural=UsdMedia.Tokens.spatial, start=float(use["at"]) * rate,
                               end=end, source=use["from"],
                               playback=UsdMedia.Tokens.loopFromStartToEnd if end is not None
                               else UsdMedia.Tokens.onceFromStart):
            unplaced.append(f"{use['sound']} (motion): no file")
    return unplaced


def bank_sounds(stage, place, banked, entries, out, surfaces):
    """Every library surface's footstep, impact and scrape as bank sounds, each surface pointing at its own."""
    import export
    import library
    import sound as tool
    from pxr import Sdf, UsdGeom, UsdMedia
    library_root = stage.GetPrimAtPath(f"/{place}/Library")
    if not library_root:
        return []
    sounds = json.loads(pathlib.Path(surfaces).read_text())
    variants = library.variants(library.theme_library())
    UsdGeom.Scope.Define(stage, f"/{place}/Sound/Bank")
    written, unplaced = set(), []
    for material in library_root.GetChildren():
        sound = export.sound_of(material.GetName(), variants, sounds)
        if sound is None:
            continue
        for happening in tool.HAPPENINGS:
            name = sound.get(happening)
            if not name:
                continue
            bank = f"/{place}/Sound/Bank/{name}"
            if name not in written:
                if name not in banked or not tool.audio_prim(
                        stage, bank, name, dict(entries.get(name, {}), loops=False), out,
                        playback=UsdMedia.Tokens.onceFromStart, source=f"data/sound/surfaces.json, the surface "
                                                                        f"{sound['surface']}"):
                    unplaced.append(f"{name} ({sound['surface']} {happening}): not in the place's sound output")
                    continue
                written.add(name)
            material.CreateRelationship(f"score:sound:{happening}").SetTargets([Sdf.Path(bank)])
        material.CreateAttribute("score:sound:absorbs", Sdf.ValueTypeNames.Float).Set(float(sound.get("absorbs", 0.0)))
    return unplaced
