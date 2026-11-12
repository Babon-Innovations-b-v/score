"""A place's seed as the assembly lays it, in a folder of its own: its accepted scene record written in, each kit
piece at its kit spot, the surface line's bakes over its models and the place on its made ground. The settle drops
it and the motion models layer lays its models on it (2026-10-15: the motion models layer, then named machines, laid the hangar's ship on the
seed, whose structure still held the game's old ship, which the scene record no longer lays, and the hull stood 48
cm up on it in the assembly).
"""
import json
import os
import pathlib
import shutil

from score.stages.assembly import face_down, level_spot, on_ground, parting, roof_tops, tops_levelled

# The seed's own files copied beside its root (its assets are copied or linked apart).
SEED_PARTS = ("layers", "inputs.json")


def grounded_seed(inputs, folder):
    """The seed's stage in `folder` with its accepted scene record written in and each kit piece at its kit spot, on
    the place's made ground (the assembly's take_record and take_ground, so the settle starts from what the assembly
    lays: the airlock's alcove, moved off its wall, met the seed's old hanging suit) with the surface line's bakes over
    its models (take_bakes): its root and layers copied, its assets copied (linked, read and never written, where
    there is no bake). The root's path."""
    import score.stages.assembly.record as record  # this form: the code version hashes record.py alone
    seed = pathlib.Path(inputs["seed"])
    folder.mkdir(parents=True, exist_ok=True)
    root = folder / f"{seed.name}.usda"
    # copied as plain files (copyfile): the store's seed is read-only and a copy keeping its modes refused the
    # record's save over the copied base (Batch 1, 2026-10-25)
    shutil.copyfile(seed / root.name, root)
    for part in SEED_PARTS:
        source = seed / part
        if source.is_dir():
            shutil.copytree(source, folder / part, copy_function=shutil.copyfile)
        elif source.exists():
            shutil.copyfile(source, folder / part)
    # copied where the bakes are written over them (a write through a link would change the seed's file); a seed
    # laying no kit piece has none, and the store keeps no empty folder (Batch 1, 2026-10-25: every settle)
    if (seed / "assets").is_dir():
        shutil.copytree(seed / "assets", folder / "assets",
                        copy_function=shutil.copyfile if "surfaces-bake" in inputs else linked)
    else:
        (folder / "assets").mkdir()
    record.take_record({key: inputs[key] for key in ("kit", "scene", "scene-record") if key in inputs}, folder,
                       seed.name)
    take_bakes(inputs, folder, seed.name)
    parting.parted(folder, seed.name)  # as the assembly's make parts them (wired.make)
    record.take_ground(inputs["terrain"], seed.name, root)
    level_spot.slid(folder, seed.name)  # to a level spot of its made ground, as wired.make
    on_ground.stood(folder, seed.name)  # on its made ground, as the assembly's make stands them (wired.make)
    tops_levelled.laid(folder, seed.name)  # a thing on its holder's curved top laid again on its levelled model
    roof_tops.let_down(folder, seed.name, inventory_rows(inputs))  # a roof piece onto the holder it roofs
    # a face thing of a row its inventory leaves standing onto what is under it, as wired.make (tube's wall lamps on
    # its ribs are mounted, so left)
    face_down.let_down(folder, seed.name, inventory_rows(inputs))
    return root


def inventory_rows(inputs):
    """The rows of the settle's inventory (`inventory`, the file the settle judges by); None without one."""
    path = pathlib.Path(inputs["inventory"]) if inputs.get("inventory") else None
    return json.loads(path.read_text())["rows"] if path is not None and path.is_file() else None


def take_bakes(inputs, folder, place):
    """The surface line's bakes over the seed's models, as the assembly lays them (baked.py: the place's own bake, a
    waiting entry its bake made, each model another place bakes for it), so the drop rests the very models the
    assembly lays: the seed's, rested and laid under the repainted bakes, tilted the hangar's control desk 2 degrees
    and left its keyboards on its sloping front (2026-10-15). The assets are copied, not linked, for it. Each floor
    thing's model then stands on every foot by the resting check's measure (even_feet: campgrounds' domes,
    2026-11-11)."""
    import score.stages.assembly.baked as baked
    import score.stages.assembly.even_feet as even_feet
    from score.stages.assembly import made_waiting
    from score.stages.assembly.record import BASE_LAYER
    if "surfaces-bake" not in inputs:
        return
    bake = pathlib.Path(inputs["surfaces-bake"])
    baked.take_bake(bake, pathlib.Path(inputs["surfaces-paint"]), folder)
    for row in made_waiting.lay(folder, place, bake, made_waiting.joined_rows(inputs)):
        baked.stamp_baked_hash(folder / BASE_LAYER, row, bake / "made" / f"{row}.gltf")
    for claimed in baked.claimed_bakes(inputs, folder):
        baked.take_bake(*claimed)
    even_feet.evened(folder, place)  # every foot down by the resting check's own measure, as the assembly lays it


def linked(source, target):
    """A file linked where it can be (one disk), else copied."""
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)
