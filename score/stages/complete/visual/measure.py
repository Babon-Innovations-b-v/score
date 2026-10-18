"""A place's evidence for the visual check, from the store (read only): its pictures (frames.of_place) and what each
picture's camera sees on the stage it was drawn from (seen.record), written to a folder the judge reads:

    <folder>/pictures/<number>.png     each picture at frames.SIZE
    <folder>/evidence.json             {"place", "outputs": {node: output read}, "rooms", "pictures": [{"name", "file",
                                       "view", "stage", "sight"}]}

`sight` is None when the picture names no stage output the store holds. `rooms` is {stage output: the neighbour
meshes standing inside the place's room on it (room.intrusions)}. Every stage is opened once, however many
pictures were drawn from it.
"""
import json
import pathlib

from pxr import Usd

from score.stages.complete.visual import frames, room, seen

EVIDENCE = "evidence.json"


def stage_root(store, output):
    """The root OpenUSD file of a stored stage output (a read-only checkout)."""
    from score.stages.assembly import stage_file
    return stage_file(pathlib.Path(store.checkout(output)))


def opened(store, output):
    """A stored stage opened from its read-only checkout."""
    return Usd.Stage.Open(str(stage_root(store, output)))


def sights_on(stage, views):
    """What each view sees on one stage."""
    scene = seen.gathered(stage)
    return [seen.record(stage, scene, view) for view in views]


def stored_stages(store, pictures):
    """The stage outputs the pictures were drawn from that the store holds."""
    return [output for output in sorted({picture.stage for picture in pictures if picture.stage})
            if store.objects.exists(f"outputs/{output}.json")]


def sights(store, pictures, place):
    """Each picture's sight record, None for a picture whose stage the store lacks; and {stage output: the
    neighbours standing in its room (room.intrusions)}."""
    found, rooms = [None] * len(pictures), {}
    for output in stored_stages(store, pictures):
        stage = opened(store, output)
        rooms[output] = room.intrusions(stage, place)
        numbers = [number for number, picture in enumerate(pictures) if picture.stage == output]
        for number, record in zip(numbers, sights_on(stage, [pictures[number].view for number in numbers])):
            found[number] = record
    return found, rooms


def write(place, outputs, pictures, measured, folder):
    """The evidence folder of a place; its evidence file's path."""
    (folder / "pictures").mkdir(parents=True, exist_ok=True)
    records, rooms = measured
    listed = []
    for number, (picture, record) in enumerate(zip(pictures, records)):
        name = f"pictures/{number}.png"
        picture.image.save(folder / name)
        listed.append({"name": picture.name, "file": name, "view": picture.view, "stage": picture.stage,
                       "sight": record})
    path = folder / EVIDENCE
    path.write_text(json.dumps({"place": place, "outputs": outputs, "rooms": rooms, "pictures": listed}))
    return path


def gather(store, place, folder):
    """Measure a place into its evidence folder; the evidence file's path."""
    outputs = frames.read_outputs(store, place)
    pictures = frames.of_place(store, outputs)
    return write(place, outputs, pictures, sights(store, pictures, place), pathlib.Path(folder))
