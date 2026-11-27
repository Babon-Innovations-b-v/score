"""The strands' finish from the hair's colour in the close-up photograph (`fibre_of`): the library's strand finish
(`../hair/finish.py`'s `hair_strands_ash_brown`: a human fibre's index, roughness, cuticle tilt, spread and lighter
tips) with its melanin, redness and share of white strands fitted so the head drawn shows the photo's hair colour.

The fit is read off drawn strands, not a formula (round 3, 2026-11-27: the estimated lightness-to-pigment table drew
an older woman's silver-white bob, photo L 63 under its crown, as a dark grey; through a head's many fibres a white strand's
light is soaked up by the dark ones beside it, so a white share mixed by lightness reads far too dark). The table
(TABLE, `data/people/hair/melanin_swatch.json`) is a strand swatch (`blender_swatch.py`: a head-sized ball under a bob
of the library's strands, drawn the way `blender_sheet.py` draws a head, at the photographs' scale) per case of
melanin, redness and white share (SWATCH), each read as its strands' median CIELAB and the spread of their lightness
(`measured`). Every grey share is drawn at every redness too (round 4, 2026-11-27: with redness drawn only on pure
heads and fitted by a single fibre's hue, a warm brown head, photo CIELAB (17.7, 6.2, 6.7), was fitted the most melanin
and no redness and drew a neutral black (15.8, 1.1, 1.0); an older woman's silver bob drew green-yellow).

A coloured head's melanin and redness are the pair whose swatch shows its colour nearest in CIELAB (the table read
linearly on a fine grid); a grey head (chroma under GREY_CHROMA, lightness over GREY_LIGHT) is white strands among
pigmented ones: its white share, the pigmented strands' melanin and the redness are the three whose swatch shows the
photo's colour and its lightness's spread nearest (one unit each); with no spread read (a beard read off the paint),
the pigmented strands are a dark brown's (LIGHTNESS_OF_PIGMENTED). The colour matched is the photo's less
DRAWN_OFFSET: a head on the sheet draws darker and yellower than the swatch's ball of the same strands (its lower hair
hangs in its own shade), by (-5.65, 0.04, 1.48), (-4.35, 0.84, 1.98) and (-5.0, 0.1, 1.03) on round 3's three sheets
(the sheet's drawn colour less the swatch's at the fitted strands); their mean.

    python -m tools.characters.generated.fibre <swatch renders> <table.json>

reads `blender_swatch.py`'s pictures into the table.
"""
import json
import math
import pathlib
import sys

import numpy as np

from tools.characters.hair import finish

GREY_CHROMA = 10.0
GREY_LIGHT = 35.0
LIBRARY = "hair_strands_ash_brown"
TABLE = pathlib.Path(__file__).resolve().parents[3] / "data" / "people" / "hair" / "melanin_swatch.json"
# a grey head's pigmented strands when no spread is read: a dark brown's lightness
LIGHTNESS_OF_PIGMENTED = 15.0
SWATCH = {"melanin": (0.02, 0.15, 0.3, 0.45, 0.6, 0.7, 0.8, 0.86, 0.9, 0.93, 0.95, 0.97, 0.985, 0.995),
          "redness": (0.0, 0.5, 1.0), "white_share": (0.0, 0.4, 0.6, 0.75, 0.85, 0.93),
          "frame_m": 0.3, "mm_per_px": 0.75, "alpha": 0.98}
FINE = 200  # the fit's grid over white share and melanin, each way
REDNESS_STEPS = 21  # and over redness
DRAWN_OFFSET = np.array([-5.0, 0.33, 1.5])  # the sheet's head less the swatch's ball, CIELAB (round 3's mean)


def library_block():
    """The library strand finish's `hair` block."""
    return dict(finish.FINISHES[LIBRARY]["hair"])


def swatch_cases():
    """The swatch's cases: every melanin at every redness with no white strands, and every melanin but the least at
    every redness with every white share."""
    cases = [{"melanin": melanin, "redness": redness, "white_share": 0.0}
             for redness in SWATCH["redness"] for melanin in SWATCH["melanin"]]
    cases += [{"melanin": melanin, "redness": redness, "white_share": share} for redness in SWATCH["redness"]
              for share in SWATCH["white_share"][1:] for melanin in SWATCH["melanin"][1:]]
    for case in cases:
        case["name"] = f"m{case['melanin']:.3f}_r{case['redness']:.2f}_w{case['white_share']:.2f}"
    return cases


def measured(srgb):
    """The hair's colour from its pixels (sRGB 0..1, n x 3): {srgb, lab (medians), spread (the lightness's standard
    deviation)}."""
    from skimage.color import rgb2lab
    lab = rgb2lab(np.asarray(srgb, float)[None])[0]
    return {"srgb": np.median(srgb, axis=0), "lab": np.median(lab, axis=0), "spread": float(lab[:, 0].std())}


def swatch_table(folder):
    """The table read off `blender_swatch.py`'s pictures in `folder`: each case's strands (alpha over SWATCH's, above
    its `rows_measured`) as `measured`."""
    from PIL import Image
    record = json.loads((pathlib.Path(folder) / "cases.json").read_text())
    rows = []
    for case in record["cases"]:
        picture = np.asarray(Image.open(pathlib.Path(folder) / f"{case['name']}.png").convert("RGBA")) / 255.0
        strands = picture[..., 3] > SWATCH["alpha"]
        strands[record["rows_measured"]:] = False
        found = measured(picture[..., :3][strands])
        rows.append({key: case[key] for key in ("melanin", "redness", "white_share")}
                    | {"lab": np.round(found["lab"], 2).tolist(), "spread": round(found["spread"], 2)})
    return {"read_from": "blender_swatch.py's strand swatch (tools/characters/generated), drawn as blender_sheet.py "
                         "draws a head", "samples": record["samples"], "mm_per_px": record["mm_per_px"], "rows": rows}


def loaded_table(path=TABLE):
    return json.loads(pathlib.Path(path).read_text())["rows"]


def pure_rows(rows, redness):
    """(melanins, lightnesses) of the table's rows with no white strands at `redness`, by melanin."""
    chosen = sorted((row["melanin"], row["lab"][0]) for row in rows
                    if row["white_share"] == 0.0 and row["redness"] == redness)
    return np.array([pair[0] for pair in chosen]), np.array([pair[1] for pair in chosen])


def melanin_of(lightness, rows):
    """The melanin whose swatch with no white strands and no redness shows `lightness` (the swatch's lightness falls
    as the melanin rises)."""
    melanins, lightnesses = pure_rows(rows, 0.0)
    return float(np.interp(-lightness, -lightnesses, melanins))


def fined(axes, values, steps):
    """`values` (on the table's `axes`, a last axis of channels) read linearly on a grid of `steps` points along each
    axis between its ends: (the fine axes, the fine values)."""
    # imported here: Blender's Python, which draws the swatch, has no scipy
    from scipy.interpolate import RegularGridInterpolator
    fine_axes = [np.linspace(axis[0], axis[-1], count) for axis, count in zip(axes, steps)]
    mesh = np.stack(np.meshgrid(*fine_axes, indexing="ij"), axis=-1)
    read = RegularGridInterpolator(tuple(np.asarray(axis, float) for axis in axes), values)
    return fine_axes, read(mesh.reshape(-1, len(axes))).reshape(*mesh.shape[:-1], values.shape[-1])


def table_axes(rows, grey):
    """The table's rednesses and melanins, those of its grey rows when `grey`."""
    rednesses = sorted({row["redness"] for row in rows})
    melanins = sorted({row["melanin"] for row in rows if (row["white_share"] > 0.0) == grey})
    return rednesses, melanins


def pure_grid(rows):
    """The table's rows with no white strands on a fine grid (REDNESS_STEPS rednesses x FINE melanins): (rednesses,
    melanins, CIELAB)."""
    rednesses, melanins = table_axes(rows, False)
    lookup = {(row["redness"], row["melanin"]): row["lab"] for row in rows if row["white_share"] == 0.0}
    values = np.array([[lookup[(redness, melanin)] for melanin in melanins] for redness in rednesses], float)
    (fine_rednesses, fine_melanins), lab = fined((rednesses, melanins), values, (REDNESS_STEPS, FINE))
    return fine_rednesses, fine_melanins, lab


def grey_grid(rows):
    """The table's grey rows on a fine grid, REDNESS_STEPS x FINE x FINE over redness, white share and melanin, linear
    between the table's: (rednesses, shares, melanins, {lab, spread}). A share of 1 is the whitest swatch at its
    redness (all strands white: its pure row of least melanin) at every melanin; a share of 0 the pure rows."""
    rednesses, melanins = table_axes(rows, True)
    shares = sorted({row["white_share"] for row in rows}) + [1.0]
    lookup = {(row["redness"], row["white_share"], row["melanin"]): row for row in rows}
    least = min(row["melanin"] for row in rows)

    def row_of(redness, share, melanin):
        return lookup[(redness, 0.0, least)] if share == 1.0 else lookup[(redness, share, melanin)]

    values = np.array([[[[*row_of(redness, share, melanin)["lab"], row_of(redness, share, melanin)["spread"]]
                         for melanin in melanins] for share in shares] for redness in rednesses], float)
    (fine_rednesses, fine_shares, fine_melanins), fine = fined((rednesses, shares, melanins), values,
                                                                (REDNESS_STEPS, FINE, FINE))
    return fine_rednesses, fine_shares, fine_melanins, {"lab": fine[..., :3], "spread": fine[..., 3]}


def drawn_target(lab):
    """The swatch colour a head must show for the sheet to draw CIELAB `lab`: `lab` less DRAWN_OFFSET."""
    return np.asarray(lab, float) - DRAWN_OFFSET


def coloured_fit(lab, rows):
    """(melanin, redness) of a head of CIELAB `lab`: the pair whose swatch with no white strands shows the drawn
    target (`drawn_target`) nearest in CIELAB; a head darker than the darkest swatch gets its hue's darkest."""
    rednesses, melanins, grid = pure_grid(rows)
    redness, melanin = np.unravel_index(np.argmin(((grid - drawn_target(lab)) ** 2).sum(axis=-1)), grid.shape[:2])
    return float(melanins[melanin]), float(rednesses[redness])


def grey_fit(lab, spread, rows):
    """(white share, the pigmented strands' melanin, redness) of a grey head of CIELAB `lab`: the three whose swatch
    shows the drawn target (`drawn_target`) and the lightness's `spread` nearest; with no spread, the pigmented
    strands a dark brown's and the share and redness fitted to the colour."""
    rednesses, shares, melanins, grid = grey_grid(rows)
    error = ((grid["lab"] - drawn_target(lab)) ** 2).sum(axis=-1)
    if spread is None:
        column = int(np.argmin(np.abs(melanins - melanin_of(LIGHTNESS_OF_PIGMENTED, rows))))
        error = np.where(np.arange(len(melanins)) == column, error, np.inf)
    else:
        error = error + (grid["spread"] - spread) ** 2
    redness, share, melanin = np.unravel_index(np.argmin(error), error.shape)
    return float(shares[share]), float(melanins[melanin]), float(rednesses[redness])


def srgb_to_linear(colour):
    return np.where(colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4)


def is_grey(lab):
    """A grey head's colour (CIELAB median): chroma under GREY_CHROMA, lightness over GREY_LIGHT."""
    return math.hypot(lab[1], lab[2]) < GREY_CHROMA and lab[0] > GREY_LIGHT


def pigment_of(lab, spread, rows):
    """(melanin, redness, white share) of a head of hair of CIELAB `lab` and lightness `spread` (None when not
    read)."""
    if is_grey(lab):
        white, melanin, redness = grey_fit(lab, spread, rows)
        return melanin, redness, white
    melanin, redness = coloured_fit(lab, rows)
    return melanin, redness, 0.0


def fibre_of(srgb, lab, spread=None, rows=None):
    """The strand finish: the library's `hair` block with melanin and redness fitted to the hair's colour (`srgb`,
    0..1, its CIELAB `lab` and its lightness's `spread`), and `white_share` (the strands carrying no melanin)."""
    melanin, redness, white = pigment_of(lab, spread, loaded_table() if rows is None else rows)
    block = library_block()
    block.update({"melanin": round(melanin, 4), "redness": round(redness, 4), "white_share": round(white, 3),
                  "from": f"{LIBRARY} (tools/characters/hair/finish.py), melanin, redness and white share fitted on "
                          f"the strand swatch (data/people/hair/melanin_swatch.json) to the hair's colour sRGB "
                          f"{np.round(srgb, 3).tolist()}, CIELAB {np.round(lab, 1).tolist()}, lightness spread "
                          f"{None if spread is None else round(spread, 1)}"})
    return block


def main():
    folder, out = sys.argv[1:3]
    table = swatch_table(folder)
    pathlib.Path(out).write_text(json.dumps(table, indent=1) + "\n")
    print(f"swatch table: {len(table['rows'])} cases -> {out}")


if __name__ == "__main__":
    main()
