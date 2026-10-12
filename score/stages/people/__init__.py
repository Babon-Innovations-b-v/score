"""The people stage (#5; experimental, docs/bible.md architecture/experimental): people made like every prop (owner,
2026-10-11): Pixal3D's shape, split into parts, the clothing painted through the surface stage, the face by its own
step (prop_prints.py's print), the hair as the mesh carries it, SOMA-X only for the skeleton so Kimodo's clips play.
World rows, each look's data a take of data/surfaces/people.json:

    people-inputs ... people-paint   the surface stage's method and paint on the looks' takes (line.py)
    people-body-<look>               a look's body: rig, build, settle and every body gate (bodies.py)
    people-dress-<look>              the paint's library surfaces laid on the body (dress.py)
    people-look                      the review page of the LOOKED looks (look.py)

    .venv/bin/python -m score run world1 --stage people-look --detach
"""
from score import contracts, graph
from score.stages.people import bodies, dress, line, look
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
ROWS = (*line.ROWS, *bodies.rows(), *map(dress_row, bodies.looks()), LOOK)
