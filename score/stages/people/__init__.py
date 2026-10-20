"""The people stage (#5; experimental, docs/bible.md architecture/experimental): people made like every prop (owner,
2026-10-11): Pixal3D's shape, split into parts, the clothing painted through the surface stage, the face by its own
step (prop_prints.py's print), the hair as the mesh carries it, SOMA-X only for the skeleton so Kimodo's clips play.
World rows, each look's data a take of data/people/surfaces.json:

    people-route-views ... people-paint   the finish route and the paint on the looks' takes (line.py)
    people-body-<look>               a look's body: rig, build, settle and every body gate (people_bodies/bodies.py)
    people-dress-<look>              the paint's library surfaces laid on the body (dress.py)
    people-dress-<look>-in-<place>   the same in a coloured place: its fabrics the concept's colour (colours.json)
    people-clips                     each full body's passing clips; the casts held to them (people_bodies/clips.py)
    people-look                      the review page of the LOOKED looks (look.py)

    .venv/bin/python -m score run world1 --stage people-look --detach
"""
from score import contracts, graph
from score.stages.people import dress, line, look
from score.stages.people_bodies import bodies, clips
from score.stages.people_bodies.bodies import guarded

# The looks the review page shows: the player and Nev first (#5), the casts' looks once they pass.
LOOKED = ("player-work", "nev-space")


def dress_row(name, place=None, surface=None):
    """A look's dress row; in a coloured place (data/people/colours.json) `people-dress-<look>-in-<place>`, its
    fabrics that place's surface."""
    return graph.Stage(f"people-dress-{name}" + (f"-in-{place}" if place else ""), "world", dress.make_dress,
                       contracts.Contract("people-dress", 1, dress.dress_faults),
                       (guarded("dressed", dress.judge_dressed), guarded("aligned", dress.judge_aligned)),
                       files={"library": "{data}/library", "places": "{data}/definitions/place.json",
                              "tokens": "{repo}/design/tokens/tokens.json",
                              "skel_usd": "{repo}/tools/characters/skel_usd.py"},
                       after={f"{bodies.BODY}-{name}": (bodies.BODY, 1), "people-paint": ("people-paint", 1)},
                       params={"surface": surface} if surface else {})


LOOK = graph.Stage("people-look", "world", look.make_look, contracts.Contract("people-look", 1, look.look_faults),
                   (guarded("rendered", look.judge_rendered),),
                   files={"shots": "{repo}/tools/characters/maker/blender_shots.py",
                          "review": "{repo}/tools/characters/maker/blender_review.py"},
                   after={**{f"people-dress-{name}": ("people-dress", 1) for name in LOOKED},
                          **{f"{bodies.BODY}-{name}": (bodies.BODY, 1) for name in LOOKED}},
                   paid=True, euros=look.EUROS * len(LOOKED))
def cast_looks():
    """The full looks a world 1 cast names (<name>_<outfit>, or another name bodies.json gives the look)."""
    import json
    import pathlib
    data = pathlib.Path(__file__).resolve().parents[3] / "data"
    named = {entry.get("look") or f"{entry.get('character')}_{entry.get('outfit')}"
             for path in (data / "characters").glob("*.json")
             for entry in [*json.loads(path.read_text()).get("people", []),
                           *json.loads(path.read_text()).get("groups", [])]}
    extra = json.loads((data / "people/bodies.json").read_text()).get("cast_names", {})
    return [look for look, entry in bodies.looks().items() if not entry.get("far_only")
            and (look.replace("-", "_", 1) in named or set(extra.get(look, [])) & named)]


FULL = cast_looks()
# Free: each full body's passing clips, and every world 1 cast held to them (people_bodies/clips.py).
CLIPS = graph.Stage("people-clips", "world", clips.make_usable, contracts.Contract("people-clips", 1,
                                                                                 clips.usable_faults),
                    (guarded("casts use passing clips", clips.judge_casts),),
                    files={"casts": "{data}/characters", "cut": "{data}/people/bodies.json"},
                    after={f"{bodies.BODY}-{look}": (bodies.BODY, 1) for look in FULL})
def coloured_rows():
    """A dress row for each look a coloured place's cast names (its <name>_<outfit>, or a name bodies.json gives)."""
    import json
    import pathlib
    data = pathlib.Path(__file__).resolve().parents[3] / "data"
    places = json.loads((data / "people/colours.json").read_text())["places"]
    extra = json.loads((data / "people/bodies.json").read_text()).get("cast_names", {})
    rows = []
    for place, chosen in places.items():
        cast = json.loads((data / "characters" / f"{place}.json").read_text())
        named = {entry.get("look") or f"{entry.get('character')}_{entry.get('outfit')}"
                 for entry in [*cast.get("people", []), *cast.get("groups", [])]}
        rows += [dress_row(look, place, chosen["surface"]) for look in bodies.looks()
                 if look.replace("-", "_", 1) in named or set(extra.get(look, [])) & named]
    return rows


ROWS = (*line.ROWS, *bodies.rows(), *map(dress_row, bodies.looks()), *coloured_rows(), CLIPS, LOOK)
