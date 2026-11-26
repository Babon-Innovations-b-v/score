"""The strands' finish from the model's own paint (`fibre_of`): the library's strand finish (`../hair/finish.py`'s
`hair_strands_ash_brown`: a human fibre's index, roughness, cuticle tilt, spread and lighter tips) with its melanin and
redness fitted to the hair's painted colour.

Cycles' Principled Hair BSDF takes melanin m (0..1) as the concentration -ln(1 - m), split by redness r into eumelanin
(1 - r) and pheomelanin r, each with its own absorption (EUMELANIN, PHEOMELANIN: Cycles' kernel, from d'Eon et al.
2011); the colour a fibre of absorption sigma_a shows is Chiang et al. 2016's mapping, the inverse of the one Cycles'
direct colouring uses (its radial roughness 0.3). That mapping is a single fibre's: a head of hair, lit through many
fibres, reads lighter, and drawn from it a near-black paint came out mid brown (2026-11-26). So the pigment's amount
is read from the colour's lightness by pbrt-v3's own reference heads (`../hair/finish.py`: eumelanin about 0.3
blonde, 1.3 brown, 8 black), set at the lightness such heads show in a soft-lit photograph (REFERENCE_L, read by eye,
an estimate to check against the close-up on the sheet), between them in log; the redness is the grid's whose fibre
colour has the hue nearest the paint's. A grey head is pigmented hair among white: GREY_SHARE of
the strands carry no melanin when the colour's chroma is under GREY_CHROMA and its lightness over GREY_LIGHT, so the
mix of white and dark brown (LIGHTNESS_OF_PIGMENTED) strands shows its lightness.
"""
import math

import numpy as np

from tools.characters.hair import finish

EUMELANIN = np.array([0.506, 0.841, 1.653])
PHEOMELANIN = np.array([0.343, 0.733, 1.924])
RADIAL_ROUGHNESS = 0.3
GRID = 400
GREY_CHROMA = 10.0
GREY_LIGHT = 35.0
LIBRARY = "hair_strands_ash_brown"
REFERENCE_L = ((65.0, 0.3), (25.0, 1.3), (5.0, 8.0))  # (CIELAB lightness, eumelanin): blonde, brown, black
WHITE_L = 85.0  # a white hair's lightness in a soft-lit photograph (an estimate)
# a grey head's pigmented strands taken as a dark brown's (a mid brown's mixed in read brown, not silver, 2026-11-26)
LIGHTNESS_OF_PIGMENTED = 15.0


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


def concentration_of(lightness):
    """The melanin concentration a head of hair of CIELAB `lightness` shows (REFERENCE_L, log between)."""
    table = np.asarray(REFERENCE_L)
    return float(np.exp(np.interp(-lightness, -table[:, 0], np.log(table[:, 1]))))


def melanin_fit(colour, lightness):
    """The melanin and redness for a head of hair of linear `colour` and CIELAB `lightness`: (m, r)."""
    concentration = concentration_of(lightness)
    melanin = 1.0 - math.exp(-concentration)
    redness = np.linspace(0.0, 1.0, GRID)
    shown = colour_of(melanin_absorption(np.full(GRID, melanin), redness))
    hue = np.log(np.clip(colour, 1e-4, None))
    error = np.linalg.norm((np.log(shown) - np.log(shown).mean(axis=1, keepdims=True))
                           - (hue - hue.mean()), axis=1)
    return melanin, float(redness[np.argmin(error)])


def srgb_to_linear(colour):
    return np.where(colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4)


def grey_share(lab):
    """The share of white strands a grey head (CIELAB median: chroma under GREY_CHROMA, lightness over GREY_LIGHT)
    asks for: its lightness the mix of white strands' (WHITE_L) and pigmented ones' (LIGHTNESS_OF_PIGMENTED); 0 for a
    coloured head."""
    chroma = math.hypot(lab[1], lab[2])
    if chroma >= GREY_CHROMA or lab[0] <= GREY_LIGHT:
        return 0.0
    return float(np.clip((lab[0] - LIGHTNESS_OF_PIGMENTED) / (WHITE_L - LIGHTNESS_OF_PIGMENTED), 0.0, 0.95))


def fibre_of(srgb, lab):
    """The strand finish: the library's `hair` block with melanin and redness fitted to the hair's colour (`srgb`,
    0..1, and its CIELAB `lab`), and `white_share` (the strands carrying no melanin)."""
    block = dict(finish.FINISHES[LIBRARY]["hair"])
    white = grey_share(lab)
    colour = srgb_to_linear(np.asarray(srgb, float))
    melanin, redness = melanin_fit(colour, lab[0] if white == 0.0 else LIGHTNESS_OF_PIGMENTED)
    block.update({"melanin": round(melanin, 4), "redness": round(redness, 4), "white_share": round(white, 3),
                  "from": f"{LIBRARY} (tools/characters/hair/finish.py), melanin and redness fitted to the "
                          f"hair's colour sRGB {np.round(srgb, 3).tolist()}"})
    return block
