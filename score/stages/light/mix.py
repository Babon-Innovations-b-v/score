"""The light stage's sweep, worked out on the per-lamp passes of one render (inside/light_passes.py) with no render
again: light is linear in a lamp's strength, so a view's light at any strengths is its `combined` luminance plus
each lamp's pass times its scale less one, and the view's look at those strengths is that light through the view's
own tone curve, fitted on the render's look against its light.

    tone_curve(light, look) -> curve       the render's light (linear luminance) to its look's luminance (0 to 1)
    mixed(passes, scales) -> light         a view's light with each group at its scale
    sweep(views, swept, target) -> scale   the scale of the swept lamps that brings the place's brightness nearest
                                           its concept's
    lamp_faults(views, scales, seen)       each lamp unlit (on screen, lighting nothing) or blown out (where it is the
                                           light, its look at white)

The rules were set on 2026-10-12, before any light pass was rendered:
- A place's brightness is the median over its views of each view's mean look luminance; its concept's the mean of its
  concept pictures' (data/inventory's plan views). BRIGHT_WITHIN: the place within 1.5 times either way of its
  concept, every view within VIEW_WITHIN (2.5 times).
- A lamp is unlit when it stands in some view's picture and its light reaches under UNLIT_SHARE of every view's
  light; one in no view's picture lighting nothing is unseen and said, not judged. UNLIT_SHARE was 0.0005 until the
  first fan-out (2026-10-12): the stairwell's landing light, behind its landing's ceiling from shot1 (standing in the
  picture says nothing of walls), lit 0.04% of it and read unlit; a lamp that lights any of a picture is lit.
- A lamp is blown out when, of the pixels where it gives at least half the light (DOMINANT), over BLOWN_MOST look
  white (WHITE), in a view where it is the light of at least DOMINATES_LEAST of the picture. A blown lamp is turned
  down by halves, at most HALVINGS times, before it is judged.
"""
import numpy as np

BINS = 48
SCALES = 2.0 ** np.arange(-5.0, 5.0 + 1e-9, 0.125)
BRIGHT_WITHIN = 1.5
VIEW_WITHIN = 2.5
UNLIT_SHARE = 0.00001
DOMINANT = 0.5
DOMINATES_LEAST = 0.005
WHITE = 0.98
BLOWN_MOST = 0.2
HALVINGS = 5
FLOOR = 1e-6


def tone_curve(light, look):
    """(log light knots, look knots): the median look in each of BINS quantile bins of log light, made rising."""
    logs = np.log(np.maximum(light.astype(np.float64), FLOOR)).ravel()
    looks = look.astype(np.float64).ravel()
    edges = np.unique(np.quantile(logs, np.linspace(0.0, 1.0, BINS + 1)))
    knots, values = [], []
    for low, high in zip(edges[:-1], edges[1:]):
        inside = (logs >= low) & (logs <= high)
        if inside.any():
            knots.append(float(np.median(logs[inside])))
            values.append(float(np.median(looks[inside])))
    return np.asarray(knots), np.maximum.accumulate(np.asarray(values))


def toned(curve, light):
    """The look of `light` on the curve; past its brightest knot along the slope of its last quarter in log light (a
    lamp turned up past what was rendered), at most white; under its darkest in proportion to the light."""
    knots, values = curve
    logs = np.log(np.maximum(np.asarray(light, dtype=np.float64), FLOOR))
    found = np.interp(logs, knots, values)
    tail = max(len(knots) // 4, 1)
    if len(knots) > tail and knots[-1] > knots[-1 - tail]:
        slope = (values[-1] - values[-1 - tail]) / (knots[-1] - knots[-1 - tail])
        found = np.where(logs > knots[-1], np.minimum(values[-1] + slope * (logs - knots[-1]), 1.0), found)
    return np.where(logs < knots[0], values[0] * np.exp(logs - knots[0]), found)


def mixed(passes, scales):
    """A view's light with each group (lamp_<n>) at its scale ({group: scale}; others at 1)."""
    light = passes["combined"].astype(np.float64)
    for group, scale in scales.items():
        if group in passes and scale != 1.0:
            light = light + (scale - 1.0) * passes[group].astype(np.float64)
    return np.maximum(light, 0.0)


def brightness(views, scales):
    """{view: mean look luminance} at the scales; views {name: (passes, curve)}."""
    return {name: float(toned(curve, mixed(passes, scales)).mean()) for name, (passes, curve) in views.items()}


def place_brightness(views, scales):
    return float(np.median(list(brightness(views, scales).values())))


def sweep(views, swept, target, held=None):
    """The scale (from SCALES) of every swept lamp that brings the place's brightness nearest `target`, the other
    groups at their `held` scales; 1.0 when no lamp is swept."""
    if not swept:
        return 1.0
    gaps = [abs(np.log(max(place_brightness(views, dict(held or {}, **dict.fromkeys(swept, scale))), FLOOR) / target))
            for scale in SCALES]
    return float(SCALES[int(np.argmin(gaps))])


def within(views, scales, target):
    """Whether the place's brightness at the scales is within BRIGHT_WITHIN of `target`."""
    return abs(np.log(max(place_brightness(views, scales), FLOOR) / target)) <= np.log(BRIGHT_WITHIN)


def lamp_measures(views, scales, group):
    """One lamp's share of each view's light and, where it gives at least DOMINANT of it, its white share."""
    found = {}
    for name, (passes, curve) in views.items():
        if group not in passes:
            continue
        light = mixed(passes, scales)
        own = scales.get(group, 1.0) * passes[group].astype(np.float64)
        share = float(own.sum() / max(light.sum(), FLOOR))
        dominated = own >= DOMINANT * np.maximum(light, FLOOR)
        lit = dominated & (light > FLOOR)
        white = float((toned(curve, light[lit]) >= WHITE).mean()) if lit.any() else 0.0
        found[name] = {"share": round(share, 5), "dominates": round(float(lit.mean()), 5), "white": round(white, 4)}
    return found


def blown(measures):
    return any(entry["dominates"] >= DOMINATES_LEAST and entry["white"] > BLOWN_MOST for entry in measures.values())


def turned_down(views, scales, group):
    """The lamp's scale halved until it is not blown out (at most HALVINGS times): (scale, measures)."""
    measures = lamp_measures(views, scales, group)
    for _ in range(HALVINGS):
        if not blown(measures):
            break
        scales[group] = scales.get(group, 1.0) / 2.0
        measures = lamp_measures(views, scales, group)
    return scales.get(group, 1.0), measures


def lamp_faults(measures, on_screen):
    """'unlit', 'blown', 'unseen' or None for one lamp: its measures per view and the views whose picture it stands
    in."""
    if blown(measures):
        return "blown"
    if not on_screen:
        return None if any(entry["share"] >= UNLIT_SHARE for entry in measures.values()) else "unseen"
    return None if any(entry["share"] >= UNLIT_SHARE for entry in measures.values()) else "unlit"
