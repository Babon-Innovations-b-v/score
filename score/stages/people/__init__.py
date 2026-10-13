"""The people stage (#5; experimental, docs/bible.md architecture/experimental): people made like every prop (owner,
2026-10-11): Pixal3D's shape, split into parts, the clothing painted through the surface stage, the face by its own
step (prop_prints.py's print), the hair as the mesh carries it, SOMA-X only for the skeleton so Kimodo's clips play.
World rows, each look's data a take of data/people/surfaces.json:

    people-inputs ... people-paint   the surface stage's method and paint on the looks' takes (line.py)
    people-body-<look>               a look's body: rig, build, settle and every body gate (bodies.py)
    people-dress-<look>              the paint's library surfaces laid on the body (dress.py)
    people-clips                     each full body's passing clips; the casts held to them (clips.py)
    people-look                      the review page of the LOOKED looks (look.py)

    .venv/bin/python -m score run world1 --stage people-look --detach
"""
from score import contracts, graph
from score.stages.people import bodies, clips, dress, line, look
from score.stages.people.bodies import guarded

# The looks the review page shows: the player and Nev first (#5), the casts' looks once they pass.
LOOKED = ("player-work", "nev-space")


def dress_row(name):
    return graph.Stage(f"people-dress-{name}", "world", dress.make_dress,
                       contracts.Contract("people-dress", 1, dress.dress_faults),
                       (guarded("dressed", dress.judge_dressed), guarded("aligned", dress.judge_aligned)),
                       files={"library": "{data}/library", "places": "{data}/definitions/place.json",
                              "tokens": "{repo}/design/tokens/tokens.json",
                              "skel_usd": "{repo}/tools/characters/skel_usd.py"},
                       after={f"{bodies.BODY}-{name}": (bodies.BODY, 1), "people-paint": ("people-paint", 1)})


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
# Free: each full body's passing clips, and every world 1 cast held to them (clips.py).
CLIPS = graph.Stage("people-clips", "world", clips.make_usable, contracts.Contract("people-clips", 1,
                                                                                 clips.usable_faults),
                    (guarded("casts use passing clips", clips.judge_casts),),
                    files={"casts": "{data}/characters", "cut": "{data}/people/bodies.json"},
                    after={f"{bodies.BODY}-{look}": (bodies.BODY, 1) for look in FULL})
ROWS = (*line.ROWS, *bodies.rows(), *map(dress_row, bodies.looks()), CLIPS, LOOK)
