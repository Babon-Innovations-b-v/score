"""A film script compiled to render items: per segment, whether it is made from words or pictures that exist (free),
reuses an accepted film's shot (free), needs a place's film row that the basket can buy, or needs new frames that no
row makes yet; priced from measured per-frame numbers only, else "not measured yet". Nothing is bought here: the
basket's plan and launch do that, after the owner's checks."""
from score.dashboard.films import script

# What a frame costs, by the kind of render, measured. "look": a frame of a place's stage in its look (no ink) at
# 1280x720 through tools/blender/inside/usd_views.py on a rented card (ledger batch blender-20261009-020545-2401425:
# 5,292 frames, EUR 15.76; score/stages/demo_film EUROS). The other kinds have never been rendered on a card.
MEASURED = {"look": {"euros": 15.76 / 5292, "from": "5,292 look frames at 1280x720 for EUR 15.76 "
                                                    "(ledger batch blender-20261009-020545-2401425)"}}
LOOK_CUTS = ("walk-through", "orbit", "hero-still")
NEW_CUTS = ("exploded", "isolate", "layer-focus", "layer-split")
WORD_CUTS = ("title", "text")
PICTURE_CUTS = ("step-card", "before-after")
# The frames an accepted place film is rendered with (score/stages/demo_film: 4 s at 24 frames a second).
FILM_FRAMES = 96

FREE, REUSE, BASKET, NEW = "free", "reuse", "basket", "new"


def item(number, segment, how, words, frames=0, kind=None, node=None):
    """One render item, priced where its kind is measured."""
    measured = MEASURED.get(kind)
    return {"segment": number, "cut": segment["cut"], "place": (segment.get("shows") or {}).get("place"),
            "how": how, "words": words, "frames": frames, "kind": kind, "node": node,
            "euros": round(frames * measured["euros"], 2) if measured and frames else (0.0 if not frames else None)}


def film_of(segment, media):
    """The accepted film a walk-through of this segment would reuse: the place's own, or the extra film it names."""
    named = (segment.get("shows") or {}).get("film")
    return (media.get("extras") or {}).get(named) if named else media.get("film")


def walk_item(number, segment, seconds, rate, media):
    """A walk-through: the accepted film's shot when it is long enough and from the film's own camera, the place's
    film row when it has no film, else new look frames."""
    film = film_of(segment, media)
    if film and not segment.get("camera") and seconds <= script.FILM_SHOT_SECONDS + 1e-6:
        return item(number, segment, REUSE, "the accepted film's shot")
    if not film and not (segment.get("shows") or {}).get("film"):
        place = segment["shows"]["place"]
        return item(number, segment, BASKET, "the place's own film, a row the basket can buy", FILM_FRAMES, "look",
                    f"demo-film@{place}")
    why = "its own camera" if segment.get("camera") else f"{seconds:g} s, longer than the film's shot"
    return item(number, segment, NEW, f"new frames: {why}", round(seconds * rate), "look")


def still_item(number, segment, media):
    """A hero still: the place's hero picture, or one new look frame from the camera it names."""
    if media.get("hero") and not segment.get("camera"):
        return item(number, segment, REUSE, "the place's hero picture")
    return item(number, segment, NEW, "one new frame", 1, "look")


def segment_item(number, segment, seconds, rate, media):
    """The render item of one segment."""
    cut = segment["cut"]
    if cut in WORD_CUTS:
        return item(number, segment, FREE, "words, made locally")
    if cut in PICTURE_CUTS:
        return item(number, segment, FREE, "pictures the steps made")
    if cut == "walk-through":
        return walk_item(number, segment, seconds, rate, media)
    if cut == "hero-still":
        return still_item(number, segment, media)
    if cut == "orbit":
        return item(number, segment, NEW, "new frames round the place", round(seconds * rate), "look")
    return item(number, segment, NEW, f"new frames: no row renders {script.CUTS[cut]['label'].lower()} yet",
                round(seconds * rate), cut)


def items(film_script, media_by_place):
    """Every segment's render item, in order."""
    rate = float(film_script.get("rate", 24))
    return [segment_item(number, segment, script.seconds_of(film_script, segment), rate,
                         media_by_place.get((segment.get("shows") or {}).get("place"), {}))
            for number, segment in enumerate(film_script.get("segments", []), 1)]


def totals(compiled):
    """The render items summed: new frames, their measured euros, the kinds not measured, the basket's rows."""
    unmeasured = sorted({entry["kind"] for entry in compiled if entry["euros"] is None})
    return {"frames": sum(entry["frames"] for entry in compiled),
            "euros": round(sum(entry["euros"] or 0.0 for entry in compiled), 2),
            "unmeasured": unmeasured,
            "unmeasured_frames": sum(entry["frames"] for entry in compiled if entry["euros"] is None),
            "reused": sum(entry["how"] == REUSE for entry in compiled),
            "free": sum(entry["how"] == FREE for entry in compiled),
            "basket": sorted({entry["node"] for entry in compiled if entry["how"] == BASKET})}
