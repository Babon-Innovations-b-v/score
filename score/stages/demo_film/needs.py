"""What a place needs filmed, worked out free from the environment's film scripts and the place's own records (#28),
as the holes check's layer holes (score/stages/complete/holes/layers.py):

    film    every film a script (data/films/<film>.json) shows of the place, in a walk-through or a hero still: the
            place's own (data/definitions/demo_films/<place>.json, demo-film@<place>) or the one a segment names
            (<name>.json, demo-film-extra@<place>). No record is a hole (its work: the record, a camera of the
            place's scene record); a record without the creator's `"final": true` is its node's hole, which waits on
            his yes after the free preview and forecast
    shot    a place film needs two steady shots (demo_film.SHOTS, the owner's 7 s a place): a record with no `then`
            whose seed scene record (data/scene/<place>.json) holds one camera only is a hole (its work: a second
            spot, `then`, from the plan's clear standing spots)

Whether a made film passes (its pace, clearance, people, event sounds) is the film row's own gate.
"""
import json
import pathlib

WALK, STILL = "walk-through", "hero-still"


def read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.is_file() else None


def wanted(place, data):
    """The film names the scripts show of the place, in order: its own name for its own film, else the named one."""
    found = []
    for path in sorted((pathlib.Path(data) / "films").glob("*.json")):
        for segment in json.loads(path.read_text()).get("segments", []):
            shows = segment.get("shows") or {}
            if segment.get("cut") in (WALK, STILL) and shows.get("place") == place:
                found.append(shows.get("film") or place)
    return list(dict.fromkeys(found))


def node_of(place, film):
    return f"demo-film@{place}" if film == place else f"demo-film-extra@{place}"


def hole(place, kind, film, sentence, node=None, work=None):
    return {"id": f"film:{kind}:{film}", "prim": f"/{place}", "sentence": sentence, "node": node, "work": work}


def one_camera(place, data):
    """Whether the place's seed scene record holds a single camera (no second shot to take without a `then`)."""
    record = read(pathlib.Path(data) / "scene" / f"{place}.json")
    return record is not None and len(record.get("views", [])) < 2


def holes(place, data):
    """The place's film needs not met: [{"id", "prim", "sentence", "node", "work"}]."""
    found = []
    for film in wanted(place, data):
        record = read(pathlib.Path(data) / "definitions/demo_films" / f"{film}.json")
        if record is None:
            found.append(hole(place, "record", film, f"a film script shows {film} and it has no film record",
                              work=f"data/definitions/demo_films/{film}.json: its place, a camera of {place}'s scene "
                                   "record and a second shot (`then`)"))
            continue
        if record.get("final") is not True:
            found.append(hole(place, "yes", film, f"the film {film} waits on the creator's yes after its free preview",
                              node=node_of(place, film)))
        if "then" not in record and one_camera(place, data):
            found.append(hole(place, "shot", film, f"the film {film} has one steady shot, not two",
                              work=f"a second spot (`then`) in data/definitions/demo_films/{film}.json from "
                                   f"{place}'s plan's clear standing spots"))
    return found
