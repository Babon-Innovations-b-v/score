"""Terrain's declared inputs, narrowed to the part of each layout folder it reads (2026-10-12: keyed on the whole
data/kit, data/scene and data/motion folders, every light, scene-record and machine edit re-keyed the ground and
every place's assembly after it). Each folder is keyed by the runner's (pattern, part) file-slice key: the text of
what terrain's make reads of each seated place's record (gates.place_files and footprint, outside.water_mirror,
record.dented). Its place gates are ground-fit's (fit.py), which reads each place's own records. The stage table reads FILES
from here and terrain's own modules never import this one, so a change here moves no stage's code version, only
terrain's file keys. A new read of these records in terrain's code needs its field added here.
"""
import json
import pathlib

from score.stages import terrain


def seated_records(folder):
    """{place: its record in `folder` (data/scene or data/kit)} for every place a ground plan seats (data/ground/plan,
    beside the folder); a place without one is left out."""
    plans = pathlib.Path(folder).parent / "ground" / "plan"
    places = sorted(set().union(*(set(plan.get("seats", {}))
                                  for plan in (json.loads(path.read_text()) for path in plans.glob("*.json")))))
    paths = {place: pathlib.Path(folder) / f"{place}.json" for place in places}
    return {place: json.loads(path.read_text()) for place, path in paths.items() if path.exists()}


def scene_part(folder):
    """The part of the scene records terrain reads, as text: each seated place's floor and water mirror. A layout
    edit it never reads (lights, machines, people, views, doors, the places it shows) moves no ground."""
    def part(scene):
        return {"floor": scene.get("floor"), "mirror": water_mirror_of(scene)}
    return json.dumps({place: part(scene) for place, scene in seated_records(folder).items()}, sort_keys=True)


def water_mirror_of(scene):
    """The scene record's first water mirror, as outside.water_mirror reads it."""
    return next((entry["mirror"] for entry in scene.get("water") or [] if "mirror" in entry), None)


def kit_part(folder):
    """The part of the kits terrain reads, as text: each seated place's seat offset and its pieces' spots when its
    scene record has no floor (`footprint`). A piece added elsewhere (a lamp, a machine) moves no ground."""
    floored = {place for place, scene in seated_records(pathlib.Path(folder).parent / "scene").items()
               if scene.get("floor")}

    def part(place, kit):
        pieces = kit.get("pieces", [])
        return {"on_seat": kit.get("on_seat"),
                "spots": None if place in floored else [piece["at"] for piece in pieces]}
    return json.dumps({place: part(place, kit) for place, kit in seated_records(folder).items()}, sort_keys=True)


FILES = {**terrain.FILES, "scenes": ("{data}/scene", scene_part), "kits": ("{data}/kit", kit_part)}
