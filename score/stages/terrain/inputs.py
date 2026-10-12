"""Terrain's declared inputs, narrowed to the part of each layout folder it reads (2026-10-12: keyed on the whole
data/kit, data/scene and data/motion folders, every light, scene-record and machine edit re-keyed the EUR 6 ground
and every place's assembly after it). Each folder is keyed by the runner's (pattern, part) file-slice key: the text
of what terrain's make and gates read of each seated place's record (gates.place_files, footprint, kit_doors,
shell_doors, probes and leaves; outside.water_mirror and write_places; record.dented). The stage table reads FILES
from here and terrain's own modules never import this one, so a change here moves no stage's code version, only
terrain's file keys. A new read of these records in terrain's code needs its field added here.
"""
import json
import pathlib

from score.stages import terrain


def seated_records(folder):
    """{place: its record in `folder` (data/scene, data/kit or data/motion)} for every place a ground plan seats or
    judges (data/ground/plan, beside the folder); a place without one is left out."""
    plans = pathlib.Path(folder).parent / "ground" / "plan"
    places = sorted(set().union(*({*plan.get("seats", {}), *plan.get("judged", [])}
                                  for plan in (json.loads(path.read_text()) for path in plans.glob("*.json")))))
    paths = {place: pathlib.Path(folder) / f"{place}.json" for place in places}
    return {place: json.loads(path.read_text()) for place, path in paths.items() if path.exists()}


def scene_part(folder):
    """The part of the scene records terrain and its gates read, as text: each seated place's floor, neighbours,
    water mirror, room walls' doors and view eyes. A layout edit it never reads (lights, machines, people) moves no
    ground."""
    def part(scene):
        rooms = [{key: entry.get(key) for key in ("name", "wide", "deep", "doors")}
                 for entry in scene.get("structure", []) if entry.get("builder") == "room_walls"]
        return {"floor": scene.get("floor"), "places": scene.get("places", []), "rooms": rooms,
                "mirror": water_mirror_of(scene), "eyes": [view["eye"] for view in scene.get("views", [])]}
    return json.dumps({place: part(scene) for place, scene in seated_records(folder).items()}, sort_keys=True)


def water_mirror_of(scene):
    """The scene record's first water mirror, as outside.water_mirror reads it."""
    return next((entry["mirror"] for entry in scene.get("water") or [] if "mirror" in entry), None)


def kit_part(folder):
    """The part of the kits terrain and its gates read, as text: each seated place's seat offset, its pieces' spots
    when its scene record has no floor (`footprint`), its walls with openings (`kit_doors`) and its door leaves'
    models (`leaves`). A piece added elsewhere (a lamp, a machine) moves no ground."""
    floored = {place for place, scene in seated_records(pathlib.Path(folder).parent / "scene").items()
               if scene.get("floor")}

    def part(place, kit):
        pieces = kit.get("pieces", [])
        return {"on_seat": kit.get("on_seat"),
                "spots": None if place in floored else [piece["at"] for piece in pieces],
                "walls": [{key: piece.get(key) for key in ("at", "kind", "model", "openings", "x", "y", "z")}
                          for piece in pieces if piece.get("openings") and "wall" in piece["kind"]],
                "leaves": sorted(piece["model"] for piece in pieces
                                 if piece["kind"].endswith("_leaf") and piece.get("model"))}
    return json.dumps({place: part(place, kit) for place, kit in seated_records(folder).items()}, sort_keys=True)


def motion_part(folder):
    """The part of the motion records terrain's gates read, as text: each seated place's sliding prims."""
    return json.dumps({place: [entry["prim"] for entry in motion.get("motions", []) if "slide" in entry]
                       for place, motion in seated_records(folder).items()}, sort_keys=True)


FILES = {**terrain.FILES, "scenes": ("{data}/scene", scene_part), "kits": ("{data}/kit", kit_part),
         "motion": ("{data}/motion", motion_part)}
