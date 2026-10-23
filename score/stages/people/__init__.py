"""The people stage (#5; experimental, docs/bible.md architecture/experimental): people made like every model (owner,
2026-10-11 and 2026-10-20): each look a row of the shared loop (score/stages/shapes_first, #41) on the line `people`,
which no place owns, its take finished by the loop's finish route and that finish baked onto its body, face and hair
too (dress.py), SOMA-X only for the skeleton so Kimodo's clips play. Each look's data a take of
data/surfaces/people.json; after the loop:

    people-made@people               the looks the loop made, handed on (loop.py, the people layer's after-step)
    people-clips-made                the Kimodo clips and the rig every body plays (people_bodies/made_clips.py)
    people-body-<look>               a look's body: build, the people route and every body gate (people_bodies/bodies.py)
    people-dress-<look>              the loop's library surfaces laid on the body and baked there (dress.py, paid)
    people-dress-<look>-in-<surface> the same worn in a fabric a design's person row reads (people_clothes.py)
    people-clips                     each full body's passing clips; the casts held to them (people_bodies/clips.py)
    people-look-<look>               a full look's review page, one a look the designs name (look.py)

    .venv/bin/python -m score run world1 --place people --stage people-look-<look> --object <look>-s1 --detach
    (one look: the loop's rows narrowed to its take, its body, dress and page; a --stage for every look for all)
"""
from score import contracts, graph
from score.stages import people_rows
from score.stages.people import dress, look
from score.stages.people_bodies import bodies, clips, made_clips
from score.stages.people_bodies.bodies import guarded


# What a dress row reads of the people line besides the hand-on: the palette's wear and dirt with its surface
# library (the bake's), and the bake's labelled takes (each finish's close-up colour, the bake's check).
DRESS_READS = ("finish-route-palette", "surface-library", "surfaces-bake")


def dress_row(name, surface=None):
    """A look's dress row; worn in a fabric a design's person row reads (people_rows.every_dressed)
    `people-dress-<look>-in-<surface>`, its fabrics that library surface."""
    return graph.Stage(f"people-dress-{name}" + (f"-in-{surface}" if surface else ""), "world", dress.make_dress,
                       contracts.Contract("people-dress", 1, dress.dress_faults),
                       (guarded("dressed", dress.judge_dressed), guarded("aligned", dress.judge_aligned),
                        guarded("baked", dress.judge_baked)),
                       files={"library": "{data}/library", "places": "{data}/definitions/place.json",
                              "tokens": "{repo}/design/tokens/tokens.json",
                              "skel_usd": "{repo}/tools/characters/skel_usd.py",
                              "bake": "{repo}/tools/props/library", "bake script": "{repo}/score/stages/people/inside"},
                       after={f"{bodies.BODY}-{name}": (bodies.BODY, 1)},
                       beside={bodies.MADE: (bodies.MADE, 1), **{row: (row, 1) for row in DRESS_READS}},
                       neighbours=bodies.the_line, params={"surface": surface} if surface else {},
                       paid=True, euros=dress.EUROS)


def cast_looks():
    """The full looks the places' designs name (data/people/rows.json, #26)."""
    named = people_rows.every_look()
    return [look for look, entry in bodies.looks().items() if not entry.get("far_only") and look in named]


FULL = cast_looks()
# Free: each full body's passing clips, and every place's people held to them (people_bodies/clips.py).
CLIPS = graph.Stage("people-clips", "world", clips.make_usable, contracts.Contract("people-clips", 1,
                                                                                 clips.usable_faults),
                    (guarded("casts use passing clips", clips.judge_casts),),
                    files={"casts": "{data}/people/rows.json"},
                    after={f"{bodies.BODY}-{look}": (bodies.BODY, 1) for look in FULL})


def look_row(name):
    """A full look's review page, `people-look-<look>` (paid): its dress and body rendered, a node of its own so one
    look runs, and is bought, without the others (#26)."""
    return graph.Stage(f"{look.ROW}-{name}", "world", look.make_look,
                       contracts.Contract(look.ROW, 1, look.look_faults), (guarded("rendered", look.judge_rendered),),
                       files={"shots": "{repo}/tools/characters/maker/blender_shots.py",
                              "review": "{repo}/tools/characters/maker/blender_review.py"},
                       after={f"people-dress-{name}": ("people-dress", 1), f"{bodies.BODY}-{name}": (bodies.BODY, 1)},
                       paid=True, euros=look.EUROS)


# The review page of each full body the designs name (FULL), one row a look. The two looks of the people benchmark
# (#26, the tube's player and the square's crowd) were made from the retired makes and went with them (owner,
# 2026-10-21: all old stuff is retired).
LOOKS = tuple(map(look_row, FULL))


def worn_rows():
    """A dress row for each line look a design's person row dresses in a fabric of its own (people_rows.every_dressed:
    the row's words and its measured torso, score/stages/people_clothes.py)."""
    return [dress_row(look, surface) for look, surface in sorted(people_rows.every_dressed())
            if look in bodies.looks()]


ROWS = (made_clips.ROW_STAGE, *bodies.rows(), *map(dress_row, bodies.looks()), *worn_rows(), CLIPS, *LOOKS)
