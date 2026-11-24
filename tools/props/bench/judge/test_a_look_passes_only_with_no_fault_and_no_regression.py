"""The picture judge (#184) passes a made look at measures.BARS only when no kind of fault is at `fault` and it is no
worse than the previous round's: one table of looks (small RGBA pictures) against one input render, each answered by a
stand-in for Claude that keeps the body it was asked, each row the bar a known answer must break or keep. The same
pictures are shown alike: laid on the close-up's backdrop, cut to one frame round every object drawn, SHOWN px.

Breaks (each applied once, seen red, reverted), in tools/props/bench/judge/__init__.py unless named:
- counted: a kind a fault when its verdict is not `clean` (`!= "clean"`) -> the slight look fails its colour bar.
- counted: `regressed` not read -> the look worse than the previous round passes.
- looked: the `drawn` check dropped -> the empty look is asked (the stand-in refuses) and is not `drawn` 0.
- asking_body: the previous look not shown -> the regression row's ask holds two pictures, not three.
- shown: the picture's alpha not laid on BACKDROP (its RGB alone) -> the shown corners are black, not the backdrop.
- framed: the first object's box alone, not the union -> the input's object in the far corner is cut out of the
  shown input.
- measures.BARS: the picture rows left out -> the faulty look passes (no picture row judged).
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


def answer(faults=(), regressed=None, missing=()):
    verdicts = {kind: "clean" for kind in judge.KINDS if kind not in missing}
    listed = []
    for kind, verdict in faults:
        verdicts[kind] = verdict
        listed.append({"kind": kind, "where": "the body", "what": f"a {verdict} {kind}"})
    found = {"faults": listed, "verdicts": verdicts}
    if regressed is not None:
        found.update(regressed=regressed, regression="worse" if regressed else "")
    return json.dumps(found)


# name, the look's box (None: nothing drawn), the input's box, a previous look, the stand-in's answer, the failed
# measures, the pictures asked (None: not asked)
ROWS = [
    ("clean", (16, 16, 48, 48), (16, 16, 48, 48), False, answer(), [], 2),
    ("slight", (16, 16, 48, 48), (16, 16, 48, 48), False, answer([("colour", "slight")]), [], 2),
    ("holes", (16, 16, 48, 48), (16, 16, 48, 48), False, answer([("holes", "fault"), ("specks", "slight")]),
     ["picture.holes"], 2),
    ("regressed", (16, 16, 48, 48), (16, 16, 48, 48), True, answer(regressed=True), ["picture.regressed"], 3),
    ("held", (16, 16, 48, 48), (16, 16, 48, 48), True, answer(regressed=False), [], 3),
    ("empty", None, (16, 16, 48, 48), False, None, ["picture.drawn"], None),
    ("apart", (2, 2, 12, 12), (52, 52, 62, 62), False, answer(), [], 2),
    ("unjudged", (16, 16, 48, 48), (16, 16, 48, 48), False, answer(missing=("text",)), ValueError, 2),
]


@pytest.mark.parametrize("name, made_box, given_box, previous, said, failed, asked", ROWS,
                         ids=[row[0] for row in ROWS])
def test_a_look_passes_only_with_no_fault_and_no_regression(tmp_path, name, made_box, given_box, previous, said,
                                                            failed, asked):
    made = picture(tmp_path / "look.png", made_box)
    given = picture(tmp_path / "rgba.png", given_box, colour=(40, 40, 200, 255))
    before = picture(tmp_path / "before.png", made_box, colour=(40, 200, 40, 255)) if previous else None
    bodies = []

    def ask(body):
        if said is None:
            raise AssertionError("an empty look is asked nothing")
        bodies.append(body)
        return said

    if failed is ValueError:
        with pytest.raises(ValueError):
            judge.looked("a red box", made, given, before, ask=ask)
        return
    found = judge.looked("a red box", made, given, before, ask=ask)
    assert measures.judged({"picture": found})["failed"] == failed
    assert {row[1] for row in measures.BARS if row[0] == "picture"} >= {"drawn", "regressed", *judge.KINDS}
    if asked is None:
        assert bodies == [] and found["drawn"] == 0
        return
    shown = [Image.open(io.BytesIO(base64.b64decode(part["inline_data"]["data"])))
             for part in bodies[0]["contents"][0]["parts"] if "inline_data" in part]
    assert len(shown) == asked
    assert all(max(each.size) == judge.SHOWN for each in shown)
    corner = judge.BACKDROP if name != "apart" else None
    for each in shown:
        colours = {colour for _, colour in each.getcolors(judge.SHOWN ** 2)}
        assert len(colours) > 1, f"{name}: a shown picture holds no object"
        if corner:
            assert each.getpixel((0, 0)) == corner
