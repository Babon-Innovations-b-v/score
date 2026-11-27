"""The strands' finish from the hair's colour in the close-up photograph (`fibre_of`): the library's strand finish
(`../hair/finish.py`'s `hair_strands_ash_brown`: a human fibre's index, roughness, cuticle tilt, spread and lighter
tips) with its melanin, redness and share of white strands fitted so the head drawn shows the photo's hair colour.

The fit is read off drawn strands, not a formula (round 3, 2026-11-27: the estimated lightness-to-pigment table drew
an older woman's silver-white bob, photo L 63 under its crown, as a dark grey; through a head's many fibres a white strand's
light is soaked up by the dark ones beside it, so a white share mixed by lightness reads far too dark). The table
(TABLE, `data/people/hair/melanin_swatch.json`) is a strand swatch (`blender_swatch.py`: a head-sized ball under a bob
of the library's strands, drawn the way `blender_sheet.py` draws a head, at the photographs' scale) per case of
melanin, redness and white share (SWATCH), each read as its strands' median CIELAB and the spread of their lightness
(`measured`). A coloured head's melanin is the one whose swatch shows its median lightness at its redness (between
the table's, in melanin); its redness the grid's whose single-fibre colour (Chiang et al. 2016's mapping, Cycles'
absorption of eumelanin and pheomelanin) has the hue nearest the photo's; a head darker than the darkest swatch
(the sky's sheen on the strands: L 20.5) gets the most melanin. A grey head (chroma under GREY_CHROMA, lightness over
GREY_LIGHT) is white strands among pigmented ones: the white share and the pigmented strands' melanin are the pair
whose swatch shows the photo's median colour and its lightness's spread nearest (CIELAB and the spread, one unit
each); with no spread read (a beard
read off the paint), the pigmented strands are a dark brown's (LIGHTNESS_OF_PIGMENTED) and the share is fitted to the
lightness alone.

    python -m tools.characters.generated.fibre <swatch renders> <table.json>

reads `blender_swatch.py`'s pictures into the table.
"""
import json
import math
import pathlib
import sys

import numpy as np

from tools.characters.hair import finish

EUMELANIN = np.array([0.506, 0.841, 1.653])
PHEOMELANIN = np.array([0.343, 0.733, 1.924])
RADIAL_ROUGHNESS = 0.3
GRID = 400
GREY_CHROMA = 10.0
GREY_LIGHT = 35.0
LIBRARY = "hair_strands_ash_brown"
TABLE = pathlib.Path(__file__).resolve().parents[3] / "data" / "people" / "hair" / "melanin_swatch.json"
# a grey head's pigmented strands when no spread is read: a dark brown's lightness
LIGHTNESS_OF_PIGMENTED = 15.0
SWATCH = {"melanin": (0.02, 0.15, 0.3, 0.45, 0.6, 0.7, 0.8, 0.86, 0.9, 0.93, 0.95, 0.97, 0.985, 0.995),
          "redness": (0.0, 0.5, 1.0), "white_share": (0.0, 0.4, 0.6, 0.75, 0.85, 0.93),
          "frame_m": 0.3, "mm_per_px": 0.75, "alpha": 0.98}
FINE = 200  # the grey fit's grid over white share and melanin, each way


def library_block():
    """The library strand finish's `hair` block."""
    return dict(finish.FINISHES[LIBRARY]["hair"])


def swatch_cases():
    """The swatch's cases: every melanin at every redness with no white strands, and every melanin at redness 0 with
    every white share (a grey head's pigmented strands are read without redness)."""
    cases = [{"melanin": melanin, "redness": redness, "white_share": 0.0}
             for redness in SWATCH["redness"] for melanin in SWATCH["melanin"]]
    cases += [{"melanin": melanin, "redness": 0.0, "white_share": share}
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


def melanin_of(lightness, redness, rows):
    """The melanin whose swatch with no white strands shows `lightness` at `redness`: read at the table's rednesses
    either side and mixed between them; the swatch's lightness falls as the melanin rises."""
    rednesses = sorted({row["redness"] for row in rows if row["white_share"] == 0.0})
    upper = min(int(np.searchsorted(rednesses, redness)), len(rednesses) - 1)
    lower = max(upper - 1, 0)
    found = []
    for chosen in (rednesses[lower], rednesses[upper]):
        melanins, lightnesses = pure_rows(rows, chosen)
        found.append(float(np.interp(-lightness, -lightnesses, melanins)))
    span = rednesses[upper] - rednesses[lower]
    weight = 0.0 if span == 0.0 else float(np.clip((redness - rednesses[lower]) / span, 0.0, 1.0))
    return found[0] + (found[1] - found[0]) * weight


def grey_grid(rows):
    """The table's grey rows (redness 0) on a fine grid, FINE x FINE, linear between the table's shares and melanins:
    (shares, melanins, {lab: FINE x FINE x 3, spread}). A share of 1 is the whitest swatch (all strands white, its
    pure row of least melanin) at every melanin."""
    shares = np.array(sorted({row["white_share"] for row in rows if row["redness"] == 0.0}) + [1.0])
    melanins = np.array(sorted({row["melanin"] for row in rows if row["white_share"] > 0.0}))
    lookup = {(row["white_share"], row["melanin"]): row for row in rows if row["redness"] == 0.0}
    white = lookup[(0.0, min(row["melanin"] for row in rows if row["white_share"] == 0.0))]
    found = [[white if share == 1.0 else lookup[(share, melanin)] for melanin in melanins] for share in shares]
    fine_shares = np.linspace(shares[0], shares[-1], FINE)
    fine_melanins = np.linspace(melanins[0], melanins[-1], FINE)

    def fine(values):
        across = np.array([np.interp(fine_melanins, melanins, line) for line in values])
        return np.array([np.interp(fine_shares, shares, column) for column in across.T]).T

    lab = np.stack([fine(np.array([[row["lab"][channel] for row in line] for line in found])) for channel in range(3)],
                   axis=-1)
    return fine_shares, fine_melanins, {"lab": lab, "spread": fine(np.array([[row["spread"] for row in line]
                                                                              for line in found]))}


def grey_fit(lab, spread, rows):
    """(white share, the pigmented strands' melanin) of a grey head of CIELAB `lab`: the pair whose swatch shows that
    colour and the lightness's `spread` nearest; with no spread, the pigmented strands a dark brown's and the share
    fitted to the lightness."""
    shares, melanins, grid = grey_grid(rows)
    if spread is None:
        pigmented = melanin_of(LIGHTNESS_OF_PIGMENTED, 0.0, rows)
        column = int(np.argmin(np.abs(melanins - pigmented)))
        share = int(np.argmin(np.abs(grid["lab"][:, column, 0] - lab[0])))
        return float(shares[share]), float(melanins[column])
    error = ((grid["lab"] - np.asarray(lab)) ** 2).sum(axis=-1) + (grid["spread"] - spread) ** 2
    share, column = np.unravel_index(np.argmin(error), error.shape)
    return float(shares[share]), float(melanins[column])


def chiang_factor(beta):
    """Chiang et al. 2016's factor between sqrt(sigma_a) and -ln(colour) at radial roughness `beta`."""
    return (5.969 - 0.215 * beta + 2.532 * beta ** 2 - 10.73 * beta ** 3 + 5.574 * beta ** 4 + 0.245 * beta ** 5)


def colour_of(absorption):
    """The colour a fibre of absorption `absorption` shows (linear RGB)."""
    return np.exp(-np.sqrt(absorption) * chiang_factor(RADIAL_ROUGHNESS))


def melanin_absorption(melanin, redness):
    """sigma_a of melanin m and redness r in Cycles' terms (broadcast over arrays)."""
    concentration = -np.log(np.maximum(1.0 - melanin, 1e-4))
    return concentration[..., None] * ((1.0 - redness)[..., None] * EUMELANIN + redness[..., None] * PHEOMELANIN)


def redness_of(colour, melanin):
    """The redness whose single fibre of `melanin` shows the hue nearest linear `colour`'s."""
    redness = np.linspace(0.0, 1.0, GRID)
    shown = colour_of(melanin_absorption(np.full(GRID, melanin), redness))
    hue = np.log(np.clip(colour, 1e-4, None))
    error = np.linalg.norm((np.log(shown) - np.log(shown).mean(axis=1, keepdims=True))
                           - (hue - hue.mean()), axis=1)
    return float(redness[np.argmin(error)])


def srgb_to_linear(colour):
    return np.where(colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4)


def is_grey(lab):
    """A grey head's colour (CIELAB median): chroma under GREY_CHROMA, lightness over GREY_LIGHT."""
    return math.hypot(lab[1], lab[2]) < GREY_CHROMA and lab[0] > GREY_LIGHT


def pigment_of(srgb, lab, spread, rows):
    """(melanin, redness, white share) of a head of hair of colour `srgb` (0..1), CIELAB `lab` and lightness `spread`
    (None when not read)."""
    if is_grey(lab):
        white, melanin = grey_fit(lab, spread, rows)
        return melanin, 0.0, white
    colour = srgb_to_linear(np.asarray(srgb, float))
    redness = redness_of(colour, melanin_of(lab[0], 0.0, rows))
    return melanin_of(lab[0], redness, rows), redness, 0.0


def fibre_of(srgb, lab, spread=None, rows=None):
    """The strand finish: the library's `hair` block with melanin and redness fitted to the hair's colour (`srgb`,
    0..1, its CIELAB `lab` and its lightness's `spread`), and `white_share` (the strands carrying no melanin)."""
    melanin, redness, white = pigment_of(srgb, lab, spread, loaded_table() if rows is None else rows)
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
