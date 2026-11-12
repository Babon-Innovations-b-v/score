"""A thing laid on its holder's top where the top under it is one plane sloping past the resting check's LEAN_MOST,
and no spot of it holds the thing standing upright (built_tops.let_down and crest_tops.laid_on left it leaning),
turned to lie flush on that plane, as a thing comes to rest on a slope: its up along the plane's, let down until it
touches, kept only where it then rests by the resting check's own measure (crest_tops.stands) and the plane slopes
SLOPE_MOST at most (tops_levelled.laid, after crest_tops).

camp, 2026-11-12 (settle@camp in Buy 95): its kitchen counter's model is made leaning 16 degrees in its frame (its
oriented box reads 9.4, under the bake's stand-square's tumble.DEGREES, and its footing holds it as made, so neither
the bake nor big_bases.upright stands it up), its top one plane sloping 18 degrees with no level spot. The coffee
maker let down onto it stood upright and leaned 18.3 degrees from what it stood on. Laid flush, it rests on the
counter's top as the counter stands.

    SLOPE_MOST                        the steepest plane a thing is laid flush on
    plane(exact, low, high)           (its unit up, degrees it slopes) of the holder's top under a footprint, or None
                                      where it is no one plane (a ridge, a step, a crest)
    laid(stage, place, entries)       each thing on its holders' top (`entries`, built_tops.held_on's) that does not
                                      rest where it is laid flush on the plane under it; the fits
"""
import pathlib
import sys

import numpy as np

from score.stages.assembly import fitting

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# The steepest plane, degrees, a thing is laid flush on: a thing on a steeper slope slides off it (a friction of 0.47,
# a dry plastic or rubber foot on painted wood or metal), and is left for the held and resting gates to name.
SLOPE_MOST = 25.0
# The rays read under a footprint across each side, and how far, metres, the top under it may stand off one plane
# and still be read as one: the fitting's BOARD_BED.
RAYS = 7
FLAT_WITHIN = fitting.BOARD_BED


def plane(exact, low, high):
    """(unit up, degrees) of the plane the holder's top (`exact`: spots [n, 2] -> heights, nan where none) makes under
    a footprint (a box low, high): its heights read on RAYS x RAYS spots across the footprint's inner half, every one
    met and within FLAT_WITHIN of the plane through them; None otherwise."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    middle, half = (low + high) / 2, (high - low) / 4
    xs = np.linspace(middle[0] - half[0], middle[0] + half[0], RAYS)
    zs = np.linspace(middle[2] - half[2], middle[2] + half[2], RAYS)
    spots = np.array([(x, z) for x in xs for z in zs], float)
    heights = exact(spots)
    if not np.all(np.isfinite(heights)):
        return None
    terms = np.c_[spots, np.ones(len(spots))]
    across, along, level = np.linalg.lstsq(terms, heights, rcond=None)[0]
    if np.max(np.abs(terms @ [across, along, level] - heights)) > FLAT_WITHIN:
        return None
    up = np.array([-across, 1.0, -along]) / np.linalg.norm([across, 1.0, along])
    return up, float(np.degrees(np.arccos(np.clip(up[1], -1.0, 1.0))))


def laid(stage, place, entries):
    """Each thing on its holders' top (`entries`) that does not rest where it is (crest_tops.stands), over one plane
    sloping past LEAN_MOST and at most SLOPE_MOST (plane), turned about its foot middle to lie flush on it and let
    down CLEAR over it where nearest, when it then rests there; the fits [{name, how, ..., "top at"}]."""
    import triage
    import trimesh
    from score.stages.assembly import crest_tops
    fits = []
    for entry in entries:
        if entry["on"].get("how") != "top" or entry["on"].get("holder scope", "Objects") != "Objects":
            continue
        holders = [f"/{place}/Objects/{holder}" for holder in entry["on"].get("holder") or []
                   if stage.GetPrimAtPath(f"/{place}/Objects/{holder}")]
        found = [mesh for mesh in (fitting.surface_mesh(stage, path) for path in holders) if mesh is not None]
        path = f"/{place}/Objects/{entry['name']}"
        own = crest_tops.as_levelled(stage.GetPrimAtPath(path), fitting.surface_mesh(stage, path))
        if not found or own is None or own.area <= 0:
            continue
        boxes = [fitting.world_box(stage, holder) for holder in holders]
        exact = crest_tops.exact_field(trimesh.util.concatenate(found), (
            np.min([low for low, _ in boxes], axis=0), np.max([high for _, high in boxes], axis=0)))
        if crest_tops.stands(own, exact, np.zeros(3)):
            continue
        low, high = fitting.world_box(stage, path)
        sloped = plane(exact, low, high)
        if sloped is None or not triage.LEAN_MOST < sloped[1] <= SLOPE_MOST:
            continue
        up, degrees = sloped
        axis = np.cross([0.0, 1.0, 0.0], up)
        axis /= np.linalg.norm(axis)
        pivot = fitting.foot_middle(low, high)
        turn = trimesh.transformations.rotation_matrix(np.radians(degrees), axis, pivot)
        tilted = own.copy()
        tilted.apply_transform(turn)
        every = np.vstack([tilted.vertices, tilted.sample(crest_tops.EVERY, seed=0)])
        tops = exact(every[:, [0, 2]])
        if not np.isfinite(tops).any():
            continue
        lift = float(np.nanmax(tops - every[:, 1])) + crest_tops.CLEAR
        if not crest_tops.stands(tilted, exact, np.array([0.0, lift, 0.0]), turn):
            continue
        fitting.pitched_by(stage.GetPrimAtPath(path), pivot, axis, degrees, pivot + [0.0, lift, 0.0])
        fit = fitting.laid_fit(stage, path, entry, "top", entry["on"].get("holder"), abs(lift), 1.0,
                               f"laid flush on {', '.join(entry['on'].get('holder'))}'s top, which slopes "
                               f"{degrees:.1f} degrees under it: turned to it and {lift:+.2f} m to touch")
        fits.append({**fit, "top at": round(float(pivot[1] + lift), 4)})
    return fits
