"""The room consistency sweep (hub round six, 2026-10-07): every made model a room lays, judged against the room's
library surfaces, so no piece brings a colour, a wear or a value of its own ("inconsistent with the rest of the
room", the owner on round four, whose pieces each carried their picture's rust and stains).

    ~/.farm-factory-props/env/bin/python tools/props/library/sweep.py <room>        # e.g. hub; writes nothing

Per model, the colour picture's texels under its own UV islands (a shared set holds many pieces) are compared with
the room's palette: every colour a library variant the room takes can bake to (its token, its bare metal, its second
colour, the room's dirt, and each mixed with the dirt and the bare metal, as wear and dirt mix them). A piece is an
outlier when fewer than ON_PALETTE of its texels lie within NEAR (CIE76) of the palette. Prints, screens, lamps and
glass are tokens too, so they count as the library's. Its median lightness is reported beside it.
"""
import json
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
MASK_SIDE = 512
TILE = 8


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
    colours = []
    for spec in specs.values():
        dirt = np.array(spec["dirt_colour"])
        own = [np.array(spec["colour"])] + [np.array(spec[key]) for key in ("bare", "second") if key in spec]
        for colour in own:
            for share in MIXES:
                colours.append(colour * (1 - share) + dirt * share)
                if "bare" in spec:
                    colours.append(colour * (1 - share) + np.array(spec["bare"]) * share)
    return lab(np.array(colours))


def islands_mask(uv, faces, side=MASK_SIDE):
    """Which texels of a side x side picture the faces' UV triangles cover."""
    from PIL import Image, ImageDraw
    mask = Image.new("L", (side, side), 0)
    draw = ImageDraw.Draw(mask)
    for triangle in uv[faces]:
        draw.polygon([(float(u) * side, (1.0 - float(v)) * side) for u, v in triangle], fill=255)
    return np.asarray(mask) > 0


def piece_colours(path):
    """A model's colour texels under its own UV islands, as linear RGB (n, 3), and the lightness spread (0..255) of
    each TILE x TILE tile wholly inside them: a surface's own blotches and streaks, which the library keeps low."""
    import trimesh
    from PIL import Image
    scene = trimesh.load(path, force="scene")
    found, spreads = [], []
    for geometry in scene.geometry.values():
        visual = geometry.visual
        if not hasattr(visual, "uv") or visual.uv is None:
            continue
        picture = getattr(visual.material, "baseColorTexture", None)
        if picture is None:
            continue
        mask = islands_mask(np.asarray(visual.uv), np.asarray(geometry.faces))
        shown = np.asarray(picture.convert("RGB").resize((MASK_SIDE, MASK_SIDE), Image.BILINEAR))
        found.append(linear_of(shown[mask]))
        grey = shown.astype(np.float64) @ np.array([0.299, 0.587, 0.114])
        tiles = MASK_SIDE // TILE
        for row in range(tiles):
            for column in range(tiles):
                window = (slice(row * TILE, (row + 1) * TILE), slice(column * TILE, (column + 1) * TILE))
                if mask[window].all():
                    spreads.append(float(grey[window].std()))
    return (np.concatenate(found) if found else np.zeros((0, 3))), spreads


def judged(found, room):
    """A piece's share of texels on the room's palette, its median lightness and how blotchy its surfaces are."""
    colours, spreads = found
    if not len(colours):
        return {"on_palette": 1.0, "lightness": None, "blotchy": 0.0}
    sample = colours[np.random.default_rng(3).choice(len(colours), min(4000, len(colours)), replace=False)]
    points = lab(sample)
    nearest = np.min(np.linalg.norm(points[:, None, :] - room[None, :, :], axis=2), axis=1)
    return {"on_palette": round(float(np.mean(nearest < NEAR)), 3), "lightness": round(float(np.median(points[:, 0])), 1),
            "blotchy": round(float(np.percentile(spreads, 75)) if spreads else 0.0, 1)}


def sweep(place, folder, layout):
    """Every made model the room lays (its pieces, its furniture and their children), judged; the outliers flagged."""
    room = palette(place)
    report = {}
    for name, about in layout["models"].items():
        path = folder / f"{name}.gltf"
        if not path.exists() or about.get("glows"):
            continue
        report[name] = dict(judged(piece_colours(path), room), route=about.get("route"))
    for entry in report.values():
        entry["outlier"] = ([f"{100 * (1 - entry['on_palette']):.0f}% of its colour is off the room's library"]
                            if entry["on_palette"] < ON_PALETTE else [])
    return report


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    room = sys.argv[1]
    layout = json.loads((library.REPO / f"data/kit/{room}.json").read_text())
    # A room's palette is its place's (place.json): the room's own name unless the layout names its place.
    report = sweep(layout.get("place", room), library.REPO / f"game/base/models/{room}_kit", layout)
    for name, entry in sorted(report.items(), key=lambda item: item[1]["on_palette"]):
        print(f"{name:32} {entry['route'] or '-':6} on palette {entry['on_palette']:.2f}  L* {entry['lightness']}  "
              f"blotchy {entry['blotchy']}  "
              f"{'; '.join(entry['outlier']) or 'ok'}")
    print(sum(bool(entry["outlier"]) for entry in report.values()), "outliers of", len(report))


if __name__ == "__main__":
    main()
