"""The picture judge (#184) passes a made look at measures.BARS only when no kind of fault is at `fault` and it is no
worse than the previous round's: one table of looks (small RGBA pictures) against one input render, each answered by a
stand-in for Claude that keeps the bodies it was asked, each row the bar a known answer must break or keep. The same
pictures are shown alike: laid on the close-up's backdrop, cut to one frame round every object drawn, SHOWN px. The
regression is its own ask (COMPARE, #205), the two looks shown as A and B in both orders, regressed only when both
answers choose the previous look.

Breaks (each applied once, seen red, reverted), in tools/props/bench/judge/__init__.py unless named:
- counted: a kind a fault when its verdict is not `clean` (`!= "clean"`) -> the slight look fails its colour bar.
- regression_of: `regressed` not set from the two answers (`regressed = False`) -> the look worse than the previous
  round passes; regressed when either answer chooses the previous look (`"A" in chose`-style `or`) -> the look one
  answer alone (its position) prefers fails as regressed.
- looked: the `drawn` check dropped -> the empty look is asked (the stand-in refuses) and is not `drawn` 0.
- looked: the compare asked in one order (previous_first's pictures not swapped) -> the second ask shows the made look
  as B, not A; the previous look not shown -> a compare ask holds two pictures, not three.
- shown: the picture's alpha not laid on BACKDROP (its RGB alone) -> the shown corners are black, not the backdrop.
- framed: the first object's box alone, not the union -> the input's object in the far corner is cut out of the
  shown input.
- asking_body: `pictured` not read (#159 round 7) -> the cockpit close-up is named NVIDIA's render in the ask.
- asking_body: CHROME left out of the ask (#159: tc5r's chrome drawn dull grey passed as a difference of reflection)
  -> the ask does not hold chrome drawn dull as a `colour` fault.
- asking_body: STRENGTH left out of the ask (#198: tc5r's royal seat and near-black cabinet forgiven as brightness)
  -> the ask does not hold a part's colour strength and value as a `colour` fault.
- measures.BARS: the picture rows left out -> the faulty look passes (no picture row judged).
- counted: `cutout` not read for a pictured case (#159: tc5r's torn cockpit cut-outs) -> the torn close-up passes and
  the pictured answer with no cut-out verdict raises nothing; measures.PICTURED_BARS without ("picture", "cutout")
  -> the torn close-up passes.
- asking_body: CUTOUT not asked for a pictured case -> its ask names no `cutout_faults`.
"""
import base64
import io
import json

import pytest
from PIL import Image

from tools.props.bench import judge, measures


def picture(path, box, colour=(200, 40, 40, 255), size=64):
    """A transparent square picture with one opaque box (left, top, right, bottom in px) drawn in `colour`."""
    drawn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if box:
        drawn.paste(Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), colour), box[:2])
    drawn.save(path)
    return path


def answer(faults=(), missing=(), cutout=None):
    """The stand-in's answer; `cutout` (a pictured case's) its close-up's own cut-out verdict, one fault listed."""
    verdicts = {kind: "clean" for kind in judge.KINDS if kind not in missing}
    listed = []
    for kind, verdict in faults:
        verdicts[kind] = verdict
        listed.append({"kind": kind, "where": "the body", "what": f"a {verdict} {kind}"})
    found = {"faults": listed, "verdicts": verdicts}
    if cutout is not None:
        found.update(cutout=cutout, cutout_faults=[{"where": "its outline", "what": "torn"}])
    return json.dumps(found)


def compared(closer):
    """The stand-in's answer to one regression ask: `closer` A, B or same."""
    return json.dumps({"a_better": "its lid" if closer == "A" else "", "b_better": "its lid" if closer == "B" else "",
                       "closer": closer})


# name, the look's box (None: nothing drawn), the input's box, the previous look's two answers (None: no previous
# look; the made look shown as A, then the previous as A), the stand-in's faults answer, the failed measures, the
# pictures the faults ask shows (None: not asked); a row named "pictured" holds its look to a close-up, not a render
ROWS = [
    ("clean", (16, 16, 48, 48), (16, 16, 48, 48), None, answer(), [], 2),
    ("slight", (16, 16, 48, 48), (16, 16, 48, 48), None, answer([("colour", "slight")]), [], 2),
    ("holes", (16, 16, 48, 48), (16, 16, 48, 48), None, answer([("holes", "fault"), ("specks", "slight")]),
     ["picture.holes"], 2),
    ("regressed", (16, 16, 48, 48), (16, 16, 48, 48), ("B", "A"), answer(), ["picture.regressed"], 2),
    ("held", (16, 16, 48, 48), (16, 16, 48, 48), ("same", "same"), answer(), [], 2),
    ("better", (16, 16, 48, 48), (16, 16, 48, 48), ("A", "B"), answer(), [], 2),
    # one answer choosing the previous look and the other the other picture shown second: its position, not the look
    ("one order", (16, 16, 48, 48), (16, 16, 48, 48), ("B", "B"), answer(), [], 2),
    ("unchosen", (16, 16, 48, 48), (16, 16, 48, 48), ("B", "neither"), answer(), ValueError, 2),
    ("empty", None, (16, 16, 48, 48), None, None, ["picture.drawn"], None),
    ("apart", (2, 2, 12, 12), (52, 52, 62, 62), None, answer(), [], 2),
    ("unjudged", (16, 16, 48, 48), (16, 16, 48, 48), None, answer(missing=("text",)), ValueError, 2),
    ("pictured", (16, 16, 48, 48), (16, 16, 48, 48), ("same", "same"), answer([("shape", "fault")], cutout="clean"),
     ["picture.shape"], 2),
    # tc5r's torn cockpit cut-outs (#159): the outline the look copies is the close-up's fault, booked as its own
    ("pictured torn", (16, 16, 48, 48), (16, 16, 48, 48), None, answer(cutout="fault"), ["picture.cutout"], 2),
    ("pictured unjudged", (16, 16, 48, 48), (16, 16, 48, 48), None, answer(), ValueError, 2),
]


@pytest.mark.parametrize("name, made_box, given_box, previous, said, failed, asked", ROWS,
                         ids=[row[0] for row in ROWS])
def test_a_look_passes_only_with_no_fault_and_no_regression(tmp_path, name, made_box, given_box, previous, said,
                                                            failed, asked):
    made = picture(tmp_path / "look.png", made_box)
    given = picture(tmp_path / "rgba.png", given_box, colour=(40, 40, 200, 255))
    before = picture(tmp_path / "before.png", made_box, colour=(40, 200, 40, 255)) if previous else None
    bodies, compares = [], []

    def ask(body):
        if said is None:
            raise AssertionError("an empty look is asked nothing")
        if "closer" not in body["generationConfig"]["responseSchema"]["properties"]:
            bodies.append(body)
            return said
        compares.append(body)
        return compared(previous[len(compares) - 1])

    if failed is ValueError:
        with pytest.raises(ValueError):
            judge.looked("a red box", made, given, before, ask=ask, pictured=name.startswith("pictured"))
        return
    pictured = name.startswith("pictured")
    found = judge.looked("a red box", made, given, before, ask=ask, pictured=pictured)
    assert measures.judged({"picture": found}, measures.PICTURED_BARS if pictured else measures.BARS)["failed"] == failed
    assert {row[1] for row in measures.BARS if row[0] == "picture"} >= {"drawn", "regressed", *judge.KINDS}
    if asked is None:
        assert bodies == [] and found["drawn"] == 0
        return
    text = bodies[0]["contents"][0]["parts"][-1]["text"]
    assert ("close-up picture the model was made from" in text, "NVIDIA" in text, "cutout_faults" in text) == (
        pictured, not pictured, pictured), text
    assert judge.CHROME in text and "`colour` fault" in judge.CHROME, text
    assert judge.STRENGTH in text and "`colour` fault" in judge.STRENGTH, text
    shown = [Image.open(io.BytesIO(base64.b64decode(part["inline_data"]["data"])))
             for part in bodies[0]["contents"][0]["parts"] if "inline_data" in part]
    assert len(shown) == asked
    # the regression asked in both orders, the original then A and B, each picture the same bytes both times
    shown_compared = [[part["inline_data"]["data"] for part in body["contents"][0]["parts"] if "inline_data" in part]
                      for body in compares]
    if previous:
        (given_a, made_a, previous_b), (given_b, previous_a, made_b) = shown_compared
        assert (given_a, made_a, previous_b) == (given_b, made_b, previous_a) and made_a != previous_b
        assert ("close-up picture" in compares[0]["contents"][0]["parts"][0]["text"]) == pictured
    else:
        assert compares == [] and "regressed" not in found
    assert all(max(each.size) == judge.SHOWN for each in shown)
    corner = judge.BACKDROP if name != "apart" else None
    for each in shown:
        colours = {colour for _, colour in each.getcolors(judge.SHOWN ** 2)}
        assert len(colours) > 1, f"{name}: a shown picture holds no object"
        if corner:
            assert each.getpixel((0, 0)) == corner
