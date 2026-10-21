"""A room's palette and the colour measures the paint's patchiness and the review's style read (hub round six,
2026-10-07: no piece brings a colour, a wear or a value of its own). The sweep over a kit room's installed models
(data/kit/<room>.json) went with the old kits on 2026-10-21.

The room's palette: every colour a library variant the room takes can bake to (its token, its bare metal, its second
colour, the room's dirt, and each mixed with the dirt and the bare metal, as wear and dirt mix them). A colour is on
the palette within NEAR (CIE76), a piece when ON_PALETTE of its colour is. Prints, screens, lamps and glass are
tokens too, so they count as the library's.
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402

NEAR = 8.0
ON_PALETTE = 0.9
# The families every room may show beside its own materials: print, screens, lamps and glass.
SHARED_FAMILIES = ("print", "screen", "light", "glass")
MIXES = np.linspace(0.0, 1.0, 6)


def lab(rgb_linear):
    """Linear RGB (n, 3) in 0..1 as CIE L*a*b* (D65)."""
    matrix = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = rgb_linear @ matrix.T / np.array([0.9505, 1.0, 1.089])
    bent = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * bent[:, 1] - 16, 500 * (bent[:, 0] - bent[:, 1]), 200 * (bent[:, 1] - bent[:, 2])], 1)


def linear_of(srgb):
    srgb = np.asarray(srgb, dtype=np.float64) / 255.0
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def palette(place):
    """Every colour the room's own library materials (place.json) and the shared families bake to, as L*a*b*: each
    token colour, mixed with the room's dirt and with its variant's bare metal over MIXES."""
    every = library.by_library(place)
    specs = dict(library.resolved(place))
    specs.update({name: spec for name, spec in every.items() if spec.get("family") in SHARED_FAMILIES})
    pictures = library.theme_library()["pictures"]
    tokens = library.token_colours(library.theme_library())
    colours = []
    for spec in specs.values():
        dirt = np.array(spec["dirt_colour"])
        own = [np.array(spec["colour"])] + [np.array(spec[key]) for key in ("bare", "second") if key in spec]
        for colour in own:
            for share in MIXES:
                colours.append(colour * (1 - share) + dirt * share)
                if "bare" in spec:
                    colours.append(colour * (1 - share) + np.array(spec["bare"]) * share)
        # A print's ink is the library's too (the prologue build: the couplets' gold on their red), and so are the
        # mixes of ink and ground along its strokes' edges.
        picture = pictures.get(spec.get("picture", ""), {})
        for key in ("ink", "accent", "panel"):
            if picture.get(key) in tokens:
                for share in MIXES:
                    colours.append(np.array(spec["colour"]) * (1 - share) + np.array(tokens[picture[key]]) * share)
        if picture.get("style") == "drawn":  # a photograph printed on paper: its own colours are the print's
            colours += drawn_colours(library.PICTURES / f"{spec['picture']}.png")
    return lab(np.array(colours))


def drawn_colours(path, count=24):
    """A drawn picture's main colours (a photograph's), as linear RGB."""
    from PIL import Image
    picture = Image.open(path).convert("RGB").quantize(count)
    palette_rgb = np.array(picture.getpalette()[:count * 3]).reshape(-1, 3)
    return list(linear_of(palette_rgb))

