"""The surface check: a labelled model drawn unlit from its close-up's camera, one flat colour per library surface, held
against the close-up region by region (job repaint, 2026-10-09: round four passed the patchiness and stripped checks
and still showed the lander, the power unit and the wreck's aft section as big flat yellow blobs; this is the check
that was missing).

Each face's surface lands on the pixels its seen faces cover (the depth test labels.seen_faces makes); the gaps
between them take the nearest drawn pixel inside the object. For every region of the close-up (regions.py) over
REGION_SHARE of the object, the surface drawn over most of it is held against the region's colour by colour family:
neutral under FAMILY_CHROMA (white, grey and black alike, as a shade changes them), else the hue family. A region fails
when the close-up is coloured and the surface is of another family, or when the close-up is neutral and the surface
is strongly coloured (chroma past STRONG: gold over a white band); a surface the place gives a soft colour (the lab's
blue vinyl over a grey seat) is the place's palette and passes. A region darker than DARK is of the family "dark" and
passes a dark surface and fails a light one; only one the drawn model hardly covers is unknown, and unknown blocks as
fail does.
Two regions of different families over FINISH_SHARE each that got one surface are two finishes painted as one, and
fail too. The model fails past MISMATCH_LIMIT of its object's pixels in failed regions, or on any such pair.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

REGION_SHARE = 0.01
FAMILY_CHROMA = 10.0
STRONG = 25.0
DARK = 30.0
LIGHT = 72.0
FINISH_SHARE = 0.03
# A region the drawn model's seen faces land on under COVERED of is unknown; a dark region passes a surface darker
# than DARK_SURFACE.
COVERED = 0.05
DARK_SURFACE = 45.0
MISMATCH_LIMIT = 0.05
# Hue families by Lab hue angle (degrees), upper bounds: wide, as shade and wear move a hue (gold foil in shade reads
# orange-brown, in light yellow; one family).
HUES = ((105.0, "warm"), (200.0, "green"), (290.0, "blue"), (340.0, "purple"), (361.0, "warm"))


def family(colour):
    """A colour's family (Lab): "neutral", or the name of its hue."""
    chroma = float(np.hypot(colour[1], colour[2]))
    if chroma < FAMILY_CHROMA:
        return "neutral"
    angle = float(np.degrees(np.arctan2(colour[2], colour[1])) % 360.0)
    return next(name for limit, name in HUES if angle < limit)


def surface_family(colour):
    """A library surface's family for splitting (Lab, as a picture shows it): its hue family, a neutral one also by
    lightness (light, mid, dark): white paint and bare steel are two finishes, though both neutral."""
    found = family(colour)
    if found != "neutral":
        return found
    return "neutral-light" if colour[0] >= LIGHT else "neutral-dark" if colour[0] < DARK else "neutral-mid"


def drawn_surfaces(painted, view, inside):
    """Each pixel's surface as the model drawn from the close-up's camera shows it (-1 outside the object), and which
    pixels a seen face lands on: the gaps between faces take the nearest drawn pixel's surface."""
    _, seen, row, column = view
    found = np.full(inside.shape, -1)
    found[row[seen], column[seen]] = painted[seen]
    landed = found >= 0
    if (found >= 0).any():
        _, nearest = ndimage.distance_transform_edt(found < 0, return_indices=True)
        found = found[nearest[0], nearest[1]]
    found[~inside] = -1
    return found, landed


def picture(drawn, flat):
    """The unlit drawing: each surface in its flat colour (`flat`, sRGB 0..1 per surface), white around it."""
    image = np.ones((*drawn.shape, 3))
    image[drawn >= 0] = np.asarray(flat)[drawn[drawn >= 0]]
    return Image.fromarray((image * 255).clip(0, 255).astype(np.uint8))


def verdict(region_colour, surface_colour, covered):
    """A region's verdict, "pass", "fail" or "unknown" (which blocks as a fail does): unknown only where the drawn
    model covers under COVERED of it (the camera cannot read it); a region the close-up shows very dark (under DARK) is
    of the family "dark" and passes a dark surface (under DARK_SURFACE) and fails a light one; elsewhere it fails
    where the surface's colour family is not the close-up's."""
    if covered < COVERED:
        return "unknown"
    if region_colour[0] < DARK:  # the measured family "dark": a shaded interior, a black dial
        return "pass" if surface_colour[0] < DARK_SURFACE else "fail"
    if family(region_colour) == "neutral":
        return "fail" if float(np.hypot(surface_colour[1], surface_colour[2])) > STRONG else "pass"
    return "pass" if family(surface_colour) == family(region_colour) else "fail"


def check(drawn, landed, pixel_regions, region_colours, surface_colours, names):
    """The surface check on a drawn model (drawn_surfaces): each region's verdict, the pairs of finishes painted as
    one, pass."""
    inside = pixel_regions >= 0
    total = inside.sum()
    verdicts, failed_share, holder = [], 0.0, {}
    for region in range(int(pixel_regions.max()) + 1):
        pixels = pixel_regions == region
        share = pixels.sum() / total
        under = drawn[pixels]
        under = under[under >= 0]
        if share < REGION_SHARE or not len(under):
            continue
        surface = int(np.bincount(under).argmax())
        found = verdict(region_colours[region], surface_colours[surface], landed[pixels].mean())
        failed_share += share if found != "pass" else 0.0
        verdicts.append({"region": region, "share": round(float(share), 3), "surface": names[surface],
                         "close_up": family(region_colours[region]), "drawn": family(surface_colours[surface]),
                         "verdict": found})
        if share >= FINISH_SHARE and region_colours[region][0] >= DARK:
            holder.setdefault(surface, []).append((region, family(region_colours[region]), share))
    collapsed = [{"surface": names[surface], "regions": [first[0], second[0]],
                  "families": [first[1], second[1]]}
                 for surface, held in holder.items() for number, first in enumerate(held)
                 for second in held[number + 1:] if first[1] != second[1]]
    failed_share = round(float(failed_share), 3)
    return {"regions": verdicts, "failed_share": failed_share, "collapsed": collapsed,
            "pass": failed_share <= MISMATCH_LIMIT and not collapsed}


def outlined(close_up, pixel_regions, verdicts):
    """The close-up with each region that failed outlined in red and each unknown one in orange (RGB)."""
    image = np.asarray(close_up.convert("RGB")).copy()
    for entry in verdicts:
        if entry["verdict"] == "pass":
            continue
        pixels = pixel_regions == entry["region"]
        edge = ndimage.binary_dilation(pixels, iterations=3) & ~pixels
        image[edge] = (230, 30, 30) if entry["verdict"] == "fail" else (255, 150, 0)
    return Image.fromarray(image)