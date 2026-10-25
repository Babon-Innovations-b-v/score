"""A place's seed as the assembly lays it, in a folder of its own: its accepted scene record written in, each kit
piece at its kit spot, the surface line's bakes over its models and the place on its made ground. The settle drops
it and the motion models layer lays its models on it (2026-10-15: the motion models layer, then named machines, laid the hangar's ship on the
seed, whose structure still held the game's old ship, which the scene record no longer lays, and the hull stood 48
cm up on it in the assembly).
"""
import os
import pathlib
import shutil

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
    record.take_ground(inputs["terrain"], seed.name, root)
    return root


def take_bakes(inputs, folder, place):
    """The surface line's bakes over the seed's models, as the assembly lays them (baked.py: the place's own bake, a
    waiting entry its bake made, each model another place bakes for it), so the drop rests the very models the
    assembly lays: the seed's, rested and laid under the repainted bakes, tilted the hangar's control desk 2 degrees
    and left its keyboards on its sloping front (2026-10-15). The assets are copied, not linked, for it."""
    import score.stages.assembly.baked as baked
    from score.stages.assembly import made_waiting
    from score.stages.assembly.record import BASE_LAYER
    if "surfaces-bake" not in inputs:
        return
    bake = pathlib.Path(inputs["surfaces-bake"])
    baked.take_bake(bake, pathlib.Path(inputs["surfaces-paint"]), folder)
    for row in made_waiting.lay(folder, place, bake):
        baked.stamp_baked_hash(folder / BASE_LAYER, row, bake / "made" / f"{row}.gltf")
    for claimed in baked.claimed_bakes(inputs, folder):
        baked.take_bake(*claimed)


def linked(source, target):
    """A file linked where it can be (one disk), else copied."""
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)
