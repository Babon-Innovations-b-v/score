"""A wear mark is a library decal inked in its token: every kind draws a picture of its size at PX_PER_M whose colour
is its token's alone and whose transparency holds the mark (some clear, some inked), the same seed drawing the same
picture; written, its surface.json is a score_lib decal (family decal, its class a class word, its maps' decal.png);
and the carrier plate's face is one quad at the front whose texture coordinates span the unit square.

Breaks (each applied once, seen red, reverted), in wear_decals/__init__.py:
- drawn: the ink taken from the alpha's grey instead of the token -> a pixel's colour is not the token's
- drawn: the alpha left at 255 everywhere -> the picture has no transparency, which score_lib refuses
- noise: rng replaced by an unseeded generator -> the same seed draws another picture
- pixels: PX_PER_M not applied -> a 1.2 m streak is drawn LEAST_PX tall, not 614 px
- written: the class check dropped -> a mark of class "plaster" is written
- plate: the face's uv left off -> the face's coordinates do not span the unit square
"""
import json

import numpy as np
import pytest

from score.stages.surfaces import wear_decals

CASES = [("grime", [0.4, 0.4]), ("scorch", [1.0, 1.0]), ("wet_stain", [0.8, 0.5]), ("damp_stain", [0.6, 1.0]),
         ("hairline_crack", [0.4, 0.3]), ("streak", [0.3, 1.2])]


@pytest.mark.parametrize("kind, size", CASES)
def test_a_wear_mark_is_a_library_decal_inked_in_its_token(kind, size, tmp_path):
    picture = wear_decals.drawn(kind, size, "#7a4e2e", seed=5)
    assert picture.size == wear_decals.pixels(size), "drawn at its size"
    if kind == "streak":
        assert picture.size == (154, 614), "PX_PER_M sets its pixels"
    pixels = np.asarray(picture)
    assert (pixels[..., :3] == [0x7a, 0x4e, 0x2e]).all(), "the ink is the token's colour alone"
    assert pixels[..., 3].min() == 0 and pixels[..., 3].max() > 64, "clear somewhere, the mark inked somewhere"
    assert (np.asarray(wear_decals.drawn(kind, size, "#7a4e2e", seed=5)) == pixels).all(), "a seed draws one picture"
    mark = {"id": f"{kind}.test", "kind": kind, "size_m": size, "ink": "#7a4e2e", "token": "rust-brown",
            "place": "test", "class": "concrete", "seed": 5, "title": kind}
    row = wear_decals.written(mark, tmp_path / kind)
    surface = json.loads((tmp_path / kind / "surface.json").read_text())
    assert surface["family"] == "decal" and surface["maps"] == {"decal": "decal.png"} and surface["size_m"] == size
    assert row["tags"]["family"] == ["decal"] and row["tags"]["class"] == ["concrete"]
    with pytest.raises(ValueError):
        wear_decals.written(dict(mark, **{"class": "plaster"}), tmp_path / "refused")
    scene, record = wear_decals.plate()
    face = scene.geometry["face"]
    assert np.allclose(face.vertices[:, 2], wear_decals.PLATE_DEEP / 2) and len(face.faces) == 2, "one quad in front"
    assert np.allclose(face.visual.uv.min(axis=0), 0.0) and np.allclose(face.visual.uv.max(axis=0), 1.0), \
        "the face's coordinates span the unit square"
    assert [part["name"] for part in record["parts"]] == ["face", "edge"]
