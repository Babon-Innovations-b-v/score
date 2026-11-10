"""The light stage's sweep, worked out on the per-lamp passes of one render (inside/light_passes.py) with no render
again: light is linear in a lamp's strength, so a view's light at any strengths is its `combined` luminance plus
each lamp's pass times its scale less one, and the view's look at those strengths is that light through the view's
own tone curve, fitted on the render's look against its light.

    tone_curve(light, look) -> curve       the render's light (linear luminance) to its look's luminance (0 to 1)
    mixed(passes, scales) -> light         a view's light with each group at its scale
    smoothed(values, guide) -> values      values smoothed where the guide (the denoised look) is flat, kept
                                           across its edges
    gain(passes, scales, guide) -> gain    a view's mixed light over its rendered light, smoothed on the guide
    displayed(transform, colour) -> look   linear colour through Blender's view transform (light_passes'
                                           view-transform.npz), 0 to 1
    lamp_light(rgb) -> rgb                 the light a lamp painted `rgb` throws: a white lamp's its black body's
                                           (white_fit, black_body), a coloured part's its own hue; luminance 1
    tint(passes, scales, colours, guide)   each pixel's change of colour when the groups take the scales and their
                                           shipped colours, its luminance's change taken out
    adaptation_degree(lux) -> D            CIECAM02's degree of adaptation of an eye standing in `lux`
    adaptation(white, degree) -> matrix    the eye's adaptation (CAT02 von Kries) from `white` to the render's white
    adapting_white(views, scales,          the colour of the light the views take from the groups at the scales
                   colours) -> rgb
    sweep(views, swept, target, held,      the scale of the swept lamps (from LAMP_SCALES, at most `most`) that
          most) -> scale                   brings the place's brightness nearest its concept's
    own_share(views, scales, groups)       the share of the views' light the place's own lamps give (median), on
                                           each group's whole-view sum
    sun_down(views, suns, target, scales,  the suns' greatest scale (from theirs down SCALES) at which `unblown`
             unblown)                      holds (no view more blown than its concept), the place and every view kept
                                           within
    fill_sweep(views, fill, target, scales, the concept fill's least scale (from the floor of SCALES up) at which
               exposed)                    every view is within VIEW_WITHIN, the place within BRIGHT_WITHIN and
                                           `exposed` holds (no view more black or blown than its concept)
    pinned(scale, top)                     whether a sweep stopped at an end of its range (SCALES' floor, `top`)
    lamp_faults(views, scales, seen)       each lamp unlit (on screen, lighting nothing) or blown out (where it is the
                                           light, its look at white)

The rules were set on 2026-10-12, before any light pass was rendered:
- A place's brightness is the median over its views of each view's mean look luminance; its concept's the mean of its
  concept pictures' (data/inventory's plan views). BRIGHT_WITHIN: the place within 1.5 times either way of its
  concept, every view within VIEW_WITHIN (2.5 times).
- The sweep's order (light.strengths): one scale for every lamp without a shaft; the suns (the concept's fill with
  them) where the lamps cannot; the suns stepped down SCALES where a view's surfaces are more blown than its
  concept's, as far as that needs and the brightness rules allow (sun_down); the fill alone, raised from the floor of SCALES only as far as the views need: the
  least scale at which every view is within VIEW_WITHIN, the place within BRIGHT_WITHIN and no view's surfaces more
  black or blown than its concept's (the exposure gate's rule), the suns' scale kept where none is (fill_sweep); then
  each blown lamp turned down; the floodlights last, by their heads. The fill's own sweep was added on 2026-10-30,
  after the rules: at hangar the sun carried 84-94% of every view and spot-2, the floor in the parked ship's shadow,
  read 0.120 against its concept's 0.304; the fill, the concept's light from no source in view, is what lights a
  shadow. Its floor and the exposure in its need the same day: base's sun, its only light, swept to 1/32 for the
  bright views, left its shaded walls 53% black in a brightness within x2.5; a fill the views do not need adds none.
  The suns' step down was added on 2026-10-31, after the rules: camp's sunlit shell read 2.2-4.3% blown in seven
  views (campgrounds' spot-4 2.4%) against its concept's 0.0%, the sun 99.7% of the light there; a sun is no lamp, so
  the lamp rule below never judged it, and it would not have caught it (a view's 4% is not BLOWN_MOST of its pixels).
- A sun is the sky's physics: it is never swept past its physical strength, SUN_MOST (1). Where an inside place's
  concept shows no daylight (its reading's concept light) its suns stand at the floor of SCALES before the lamps are
  swept, so its own lamps light it as its concept does, and they are raised back, at most to SUN_MOST, only where
  the lamps cannot. Its own lamps then give at least LAMP_SHARE_LEAST of its light (the light gate `light source`).
  Both added on 2026-11-04, after the rules, by the light audit: hangar's sun swept to x19 (about 2.4 million lux)
  in a night hangar, its lamps 8% of its light; airlock's, garage's, tube's and hub's lamps at the 1/32 floor, 0.5 to
  5% of the light, their concepts' lamp pools gone. LAMP_SHARE_LEAST is the audit's own figure, set before any look
  it judges is made.
- A lamp-lit place's lamps are swept up to the top of LAMP_SCALES (x1024), every other place's to the top of SCALES
  (x32), where the suns take over. Added on 2026-11-10, after the rules: the library's lamp strength is an estimate
  that grows with its reach, while the floor a lamp lights grows with the square of it, so a big room's lamps start
  far under its concept; hangar's (wall lamps 7.5 m up, 12.75 m reach, in a 60 m hall) stopped at x32 with 14% of its
  light, the sun raised to SUN_MOST and the fill to x25 in a night hangar, and reached its concept at x512 alone on
  its passes of 2026-11-02. A lamp has no physical strength to stop at, as a sun has; a place lit by daylight keeps
  the old top, so its sun, not a blazing lamp, lights it.
- A share of the light is read on each group's sum over the whole view, the light no group holds (the combined less
  every group, over the view) at its rendered strength (own_share). Changed on 2026-11-10, after the rules: on the
  pixels it was mixed(): the combined light is denoised and the groups are not, so their pixel-by-pixel difference is
  noise of either sign that no scale turns; at tube's lamps x0.096 and its suns x1/32 that noise, clipped at black,
  read as half the light (own lamps 21%, 39% on the sums).
- A lamp is unlit when it stands in some view's picture and its light reaches under UNLIT_SHARE of every view's
  light; one in no view's picture lighting nothing is unseen and said, not judged. UNLIT_SHARE was 0.0005 until the
  first fan-out (2026-10-12): the stairwell's landing light, behind its landing's ceiling from shot1 (standing in the
  picture says nothing of walls), lit 0.04% of it and read unlit; a lamp that lights any of a picture is lit.
- A lamp is blown out when, of the pixels where it gives at least half the light (DOMINANT), over BLOWN_MOST look
  white (WHITE), in a view where it is the light of at least DOMINATES_LEAST of the picture. A blown lamp is turned
  down by halves, at most HALVINGS times, before it is judged.
"""
import numpy as np
from scipy import ndimage

BINS = 48
SCALES = 2.0 ** np.arange(-5.0, 5.0 + 1e-9, 0.125)
LAMP_SCALES = 2.0 ** np.arange(-5.0, 10.0 + 1e-9, 0.125)
BRIGHT_WITHIN = 1.5
VIEW_WITHIN = 2.5
UNLIT_SHARE = 0.00001
SUN_MOST = 1.0
LAMP_SHARE_LEAST = 0.3
DOMINANT = 0.5
DOMINATES_LEAST = 0.005
WHITE = 0.98
BLOWN_MOST = 0.2
HALVINGS = 5
FLOOR = 1e-6
# The guided filter (He, Sun and Tang 2010) that keeps a lamp group's sampling noise out of a mixed look (only the
# render's combined light is denoised; the owner, 2026-10-20: the camp's look full of specks): a window GUIDED_REACH
# halved pixels out each way, and edges of the look whose variance passes GUIDED_EDGE (about 8 levels of 255) kept.
GUIDED_REACH = 4
GUIDED_EDGE = 1e-3


def tone_curve(light, look):
    """(log light knots, look knots): the median look in each of BINS quantile bins of log light, made rising."""
    logs = np.log(np.maximum(light.astype(np.float64), FLOOR)).ravel()
    looks = look.astype(np.float64).ravel()
    edges = np.unique(np.quantile(logs, np.linspace(0.0, 1.0, BINS + 1)))
    if len(edges) < 2:  # one light all over (a black view: light@base, 2026-10-29): one knot, never none
        return edges, np.asarray([float(np.median(looks))])
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


def smoothed(values, guide):
    """`values` filtered by the guided filter on `guide` (both the same shape): each window's values fitted as a line
    of the guide, the fits averaged."""
    def mean(field):
        return ndimage.uniform_filter(field, 2 * GUIDED_REACH + 1, mode="nearest")
    guide_mean, values_mean = mean(guide), mean(values)
    slope = (mean(guide * values) - guide_mean * values_mean) / (mean(guide * guide) - guide_mean ** 2 + GUIDED_EDGE)
    return mean(slope) * guide + mean(values_mean - slope * guide_mean)


def gain(passes, scales, guide):
    """Each pixel's light mixed at the scales over its rendered light, both smoothed on `guide` (the lamp groups are not
    denoised; one scale on every lamp stays that scale, edges and all); where the guided filter leaves the rendered
    light at none (its ring by a glare, a black), the ratio of their plain window means."""
    light, light_mixed = passes["combined"].astype(np.float64), mixed(passes, scales)
    rendered = smoothed(light, guide)
    def mean(field):
        return ndimage.uniform_filter(field, 2 * GUIDED_REACH + 1, mode="nearest")
    plain = mean(light_mixed) / np.maximum(mean(light), FLOOR)
    guided = np.maximum(smoothed(light_mixed, guide), 0.0) / np.maximum(rendered, FLOOR)
    return np.where(rendered > FLOOR, guided, plain)


def displayed(transform, colour):
    """`colour` (linear RGB, ... x 3) as Blender's view transform shows it: its table trilinear in log2 light, the
    light under its lowest knot or over its highest held there."""
    table = np.asarray(transform["table"], dtype=np.float64)
    low, high, knots = float(transform["low"]), float(transform["high"]), table.shape[0]
    at = (np.log2(np.maximum(np.asarray(colour, dtype=np.float64), 2.0 ** low)) - low) / (high - low) * (knots - 1)
    at = np.clip(at, 0.0, knots - 1).reshape(-1, 3).T
    shown = [ndimage.map_coordinates(table[..., channel], at, order=1) for channel in range(3)]
    return np.stack(shown, axis=-1).reshape(np.shape(colour))


# A lamp's colour as light (2026-11-10, light@hub, garage, habitat, greenhouse: rooms warmer than their concepts).
# Linear sRGB (D65) to CIE XYZ, and the Planckian locus in CIE 1960 (u, v) by Krystek's rational fit (1985: within
# 1e-4 of the locus from 1000 K to 15000 K). A glowing part the concept paints within WHITE_DUV of the locus is a white
# lamp: the paint's saturation is the painter's (a bulb drawn #ffcc00 is no sodium lamp), so its light is the black
# body's at the colour temperature nearest its paint. One further off (a magenta grow light, a cyan screen) throws its
# own hue. WHITE_DUV is three times the 0.006 a white lamp may stand off the locus (ANSI C78.377), so the bulbs the
# concepts paint (#ffdd88 at 0.012, #ffcc00 at 0.022) are white and env1's coloured parts (grow light #ff55ff at 0.108,
# screens #44ccff at 0.037 and #44ffcc at 0.061) are not.
SRGB_XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
LUMA = SRGB_XYZ[1]
KELVINS = np.geomspace(1000.0, 15000.0, 4000)
WHITE_DUV = 0.03


def locus_uv(kelvin):
    """The black body's (u, v) at `kelvin` (Krystek's fit)."""
    kelvin = np.asarray(kelvin, dtype=np.float64)
    u = (0.860117757 + 1.54118254e-4 * kelvin + 1.28641212e-7 * kelvin ** 2) / \
        (1.0 + 8.42420235e-4 * kelvin + 7.08145163e-7 * kelvin ** 2)
    v = (0.317398726 + 4.22806245e-5 * kelvin + 4.20481691e-8 * kelvin ** 2) / \
        (1.0 - 2.89741816e-5 * kelvin + 1.61456053e-7 * kelvin ** 2)
    return u, v


def unit_light(rgb):
    """A linear colour scaled to luminance 1 (black as white)."""
    rgb = np.asarray(rgb, dtype=np.float64)
    luma = float(LUMA @ rgb)
    return rgb / luma if luma > FLOOR else np.ones(3)


def black_body(kelvin):
    """The black body's light at `kelvin` as linear sRGB at luminance 1."""
    u, v = locus_uv(kelvin)
    x, y = 3.0 * u / (2.0 * u - 8.0 * v + 4.0), 2.0 * v / (2.0 * u - 8.0 * v + 4.0)
    return unit_light(np.maximum(np.linalg.solve(SRGB_XYZ, np.array([x / y, 1.0, (1.0 - x - y) / y])), 0.0))


def white_fit(rgb):
    """(kelvin, duv) of a linear colour: the colour temperature on KELVINS whose black body stands nearest its (u, v),
    and how far off the locus it stands."""
    big_x, big_y, big_z = SRGB_XYZ @ np.asarray(rgb, dtype=np.float64)
    under = big_x + 15.0 * big_y + 3.0 * big_z
    if under <= FLOOR:
        return None, float("inf")
    u, v = 4.0 * big_x / under, 6.0 * big_y / under
    locus_u, locus_v = locus_uv(KELVINS)
    nearest = int(np.argmin((locus_u - u) ** 2 + (locus_v - v) ** 2))
    return float(KELVINS[nearest]), float(np.hypot(locus_u[nearest] - u, locus_v[nearest] - v))


def lamp_light(rgb):
    """The light a lamp painted in linear `rgb` throws, at luminance 1: a white lamp's (within WHITE_DUV of the locus)
    the black body's at its nearest colour temperature, any other its own hue."""
    kelvin, duv = white_fit(rgb)
    return black_body(kelvin) if duv <= WHITE_DUV else unit_light(rgb)


# The eye adapted to the light it stands in (CIE 159:2004, CIECAM02's chromatic adaptation): von Kries gains in the
# CAT02 cone space from the adapting light's white to the render's (equal linear sRGB, D65), to the degree
# D = F (1 - e^((-L_A - 42) / 92) / 3.6); F 1.0, the average surround of an eye inside the lit place; L_A, the
# adapting luminance, a fifth of a white surface's under the light the eye stands in (E / pi / 5, CIE 159's
# 20% grey world).
CAT02 = np.array([[0.7328, 0.4296, -0.1624], [-0.7036, 1.6975, 0.0061], [0.0030, 0.0136, 0.9834]])
SURROUND = 1.0
ADAPTING_SHARE = 0.2


def adaptation_degree(lux):
    """CIECAM02's degree of adaptation D for an eye standing in `lux` (an average surround)."""
    adapting = float(lux) / np.pi * ADAPTING_SHARE
    return SURROUND * (1.0 - np.exp((-adapting - 42.0) / 92.0) / 3.6)


def adaptation(white, degree):
    """The 3 x 3 linear sRGB matrix that takes colours seen under the adapting light `white` (linear sRGB) as the eye
    adapted to it to `degree` takes them, onto the render's white (CAT02 von Kries)."""
    cones = CAT02 @ SRGB_XYZ
    gains = degree * (cones @ np.ones(3)) / (cones @ unit_light(white)) + 1.0 - degree
    return np.linalg.inv(cones) @ np.diag(gains) @ cones


def adapting_white(views, scales, colours):
    """The colour (linear sRGB, luminance 1) of the light the views take from the groups at the scales: each group's
    whole-view sum in its shipped colour (`colours` {group: (rendered, shipped)}). The light no group holds is taken
    in the same colour (light.night_adapted): at a night place it is its shown places' lamps (2026-11-10: the
    stairwell's warm lamps through flat's door, 30 to 46% of its views' light, its night air's glow under 2%)."""
    total = np.zeros(3)
    for held, _ in views.values():
        for group, (_, sent) in colours.items():
            if group in held:
                total += scales.get(group, 1.0) * float(held[group].astype(np.float64).sum()) * \
                    np.asarray(sent, dtype=np.float64)
    return unit_light(total)


# `colours`' entry for the light no group holds: (as rendered, as shipped), its shipped colour the change of each
# channel the eye's adaptation makes to it (light.night_adapted); with none it stays as rendered.
REST = "rest"


def rest_colour(colours):
    """The colour the light no group holds is shipped in (colours' REST entry), neutral where it has none."""
    return np.asarray((colours or {}).get(REST, (None, np.ones(3)))[1], dtype=np.float64)


def tint(passes, scales, colours, guide):
    """Each pixel's change of colour (h x w x 3, at the passes' size, its luminance's change taken out) when the
    groups take the scales and their shipped colours (`colours` {group: (rendered, shipped)}, each at luminance 1):
    every group's light carries its colour over the surfaces it lights, the light no group holds (the sky's dome, a
    shown place's lamps, glow) stays as rendered, taken as neutral (its REST entry's change, where given); each channel smoothed on the guide as gain is. All 1 at
    scale 1 in the colours rendered. The look kept the render's colour under any scales until 2026-11-10: greenhouse's
    lamps swept 25 times up, its sun 32 times down, read its sunlit render's colour."""
    def mean(field):
        return ndimage.uniform_filter(field, 2 * GUIDED_REACH + 1, mode="nearest")
    light = passes["combined"].astype(np.float64)
    rest = light.copy()
    rendered, shipped = np.zeros(light.shape + (3,)), np.zeros(light.shape + (3,))
    for group, (made, sent) in colours.items():
        if group not in passes:
            continue
        lit = passes[group].astype(np.float64)
        rest -= lit
        rendered += lit[..., None] * np.asarray(made, dtype=np.float64)
        shipped += (scales.get(group, 1.0) * lit)[..., None] * np.asarray(sent, dtype=np.float64)
    rest = np.maximum(rest, 0.0)[..., None]
    rendered, shipped = rendered + rest, shipped + rest * rest_colour(colours)
    before = np.stack([smoothed(rendered[..., channel], guide) for channel in range(3)], axis=-1)
    after = np.stack([smoothed(shipped[..., channel], guide) for channel in range(3)], axis=-1)
    plain = np.stack([mean(shipped[..., channel]) / np.maximum(mean(rendered[..., channel]), FLOOR)
                      for channel in range(3)], axis=-1)
    change = np.where(before > FLOOR, np.maximum(after, 0.0) / np.maximum(before, FLOOR), plain)
    luma = change @ LUMA
    return np.where(luma[..., None] > FLOOR, change / np.maximum(luma, FLOOR)[..., None], 1.0)


# The lamps' balance (2026-11-10, after the look took each lamp's colour: greenhouse's warm wall panels outshone its
# magenta grow light, which its concept shows the brightest, and read 30 levels warmer than the concept): the lamps of
# one colour (a class) are swept together against the others, each sun and the concept's fill a class of its own,
# each class by half octaves over twice the sweep's own range either way, every light kept within SCALES (its
# `most`), none held (the brightness is set after), to bring the place's colour cast nearest its concept's (camp,
# 2026-11-10: its screens and laptop swept 32 times up lit it cool, its sun and its warm fill under them; hub's fill
# at the floor). A lamp's strength is measured against the concept as its brightness is; its colour stays what it
# throws. A sun is only turned down; a faint emitter (a screen: its share of a lamp an estimate, lamps.json
# `glowing`) is a class of its own, raised past its share only where its concept's colour asks it (hub's cyan
# screens). Kept only where it brings the cast at least BALANCE_GAIN levels nearer, so a place already in its
# concept's colour keeps one scale.
BALANCE = 2.0 ** np.arange(-10.0, 10.0 + 1e-9, 0.5)
BALANCE_ROUNDS = 3
BALANCE_GAIN = 1.0
# Each octave a class moves costs this many levels of cast, so of balances that read alike the least is taken
# (2026-11-10: airlock's white lamps put out x1/1024 for its orange beacon, its cast 0.1 levels off on the balance's
# estimate and 15.2 on its looks).
BALANCE_COST = 0.25


def balance(classes, held, gap_of, most=None):
    """{class: multiplier} (each from BALANCE, at most its `most` entry where given, `held` at 1) bringing
    gap_of(multipliers) least, each octave a class moves costing BALANCE_COST levels, one class at a time for
    BALANCE_ROUNDS rounds; all 1 unless that brings the gap at least BALANCE_GAIN lower. (multipliers, gap at all 1,
    gap at the multipliers)."""
    most = most or {}
    ones = dict.fromkeys(classes, 1.0)
    found, start = dict(ones), gap_of(ones)
    best, gap_found = start, start
    for _ in range(BALANCE_ROUNDS):
        moved = False
        for name in classes:
            if name == held:
                continue
            for value in BALANCE[BALANCE <= most.get(name, BALANCE[-1]) + 1e-9]:
                tried = {**found, name: float(value)}
                gap = gap_of(tried)
                cost = gap + BALANCE_COST * sum(abs(np.log2(each)) for each in tried.values())
                if cost < best - 1e-9:
                    found, best, gap_found, moved = tried, cost, gap, True
        if not moved:
            break
    return (found, start, gap_found) if gap_found <= start - BALANCE_GAIN else (ones, start, start)


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


def capped(swept, scale, factors=None, caps=None):
    """{group: scale} of the swept groups at `scale` times each one's `factors` entry, at most its `caps` entry."""
    return {group: min(scale * (factors or {}).get(group, 1.0), (caps or {}).get(group, float("inf")))
            for group in swept}


def sweep(views, swept, target, held=None, most=None, factors=None, caps=None):
    """The scale (from LAMP_SCALES, at most `most` where given) of every swept lamp, each times its `factors` entry (its
    balance, else 1) and at most its `caps` entry (a faint emitter: x1), that brings the place's brightness nearest
    `target`, the other groups at their `held` scales; 1.0 when no lamp is swept."""
    if not swept:
        return 1.0
    tried = [scale for scale in LAMP_SCALES if most is None or scale <= most + 1e-9]
    gaps = [abs(np.log(max(place_brightness(views, dict(held or {}, **capped(swept, scale, factors, caps))), FLOOR)
                       / target)) for scale in tried]
    return float(tried[int(np.argmin(gaps))])


def own_share(views, scales, groups):
    """The median over the views of the share of each view's light (all its pixels' light summed) that `groups` (the
    place's own lamps) give at the scales; None with no view or no group. Each group (lamp_<n>) is summed over the
    view before it is scaled, and the light no group holds is the view's combined sum less theirs, at its rendered
    strength: the pixels' differences are the denoiser's noise, which cancels in the sum."""
    shares = []
    for passes, _ in views.values():
        held = [group for group in groups if group in passes]
        if not held:
            continue
        sums = {group: float(values.astype(np.float64).sum()) for group, values in passes.items()
                if group.startswith("lamp_")}
        rest = max(float(passes["combined"].astype(np.float64).sum()) - sum(sums.values()), 0.0)
        total = sum(scales.get(group, 1.0) * value for group, value in sums.items()) + rest
        shares.append(sum(scales.get(group, 1.0) * sums[group] for group in held) / max(total, FLOOR))
    return float(np.median(shares)) if shares else None


def within(views, scales, target):
    """Whether the place's brightness at the scales is within BRIGHT_WITHIN of `target`."""
    return abs(np.log(max(place_brightness(views, scales), FLOOR) / target)) <= np.log(BRIGHT_WITHIN)


def views_within(views, scales, target):
    """Whether every view's brightness at the scales is within VIEW_WITHIN of `target`."""
    return all(abs(np.log(max(value, FLOOR) / target)) <= np.log(VIEW_WITHIN)
               for value in brightness(views, scales).values())


def sun_down(views, suns, target, scales, unblown=lambda scales: True):
    """The greatest of SCALES at or under the suns' scale in `scales` at which `unblown(scales)` holds, the place
    within BRIGHT_WITHIN and every view within VIEW_WITHIN; the suns' scale where none is."""
    held = scales[suns[0]]
    for scale in SCALES[::-1]:
        if scale > held:
            continue
        tried = dict(scales, **dict.fromkeys(suns, float(scale)))
        if not (within(views, tried, target) and views_within(views, tried, target)):
            break
        if unblown(tried):
            return float(scale)
    return held


def fill_sweep(views, fill, target, scales, exposed=lambda scales: True):
    """The least of SCALES for the fill at which every view is within VIEW_WITHIN, the place within BRIGHT_WITHIN and
    `exposed(scales)` holds; the fill's scale in `scales` (the suns') where none is."""
    for scale in SCALES:
        tried = dict(scales, **{fill: float(scale)})
        if views_within(views, tried, target) and within(views, tried, target) and exposed(tried):
            return float(scale)
    return scales.get(fill, 1.0)


def pinned(scale, top=SCALES[-1]):
    """Whether a sweep's scale stands at either end of its range (the floor of SCALES, `top`): the lamps went as far
    as the sweep goes and may not have reached (2026-10-30: airlock's lamps at the floor, its brightness x1.44 its
    concept's, carried by the sun and the fill the sweep never turned)."""
    return scale in (float(SCALES[0]), float(top))


def lamp_measures(views, scales, groups):
    """One lamp's share of each view's light and, where it gives at least DOMINANT of it, its white share. A lamp is
    its `groups` together: the record's lights at one spot are one lamp (each alone gives half where they are the
    light, never DOMINANT, so none of them could read blown out)."""
    found = {}
    for name, (passes, curve) in views.items():
        if not all(group in passes for group in groups):
            continue
        light = mixed(passes, scales)
        own = sum(scales.get(group, 1.0) * passes[group].astype(np.float64) for group in groups)
        share = float(own.sum() / max(light.sum(), FLOOR))
        dominated = own >= DOMINANT * np.maximum(light, FLOOR)
        lit = dominated & (light > FLOOR)
        white = float((toned(curve, light[lit]) >= WHITE).mean()) if lit.any() else 0.0
        found[name] = {"share": round(share, 5), "dominates": round(float(lit.mean()), 5), "white": round(white, 4)}
    return found


def blown(measures):
    return any(entry["dominates"] >= DOMINATES_LEAST and entry["white"] > BLOWN_MOST for entry in measures.values())


def turned_down(views, scales, groups):
    """The lamp's scale (each of its `groups`, set in `scales`) halved until it is not blown out (at most HALVINGS
    times): (scale, measures)."""
    measures = lamp_measures(views, scales, groups)
    for _ in range(HALVINGS):
        if not blown(measures):
            break
        scales.update({group: scales.get(group, 1.0) / 2.0 for group in groups})
        measures = lamp_measures(views, scales, groups)
    return scales.get(groups[0], 1.0), measures


def lamp_faults(measures, on_screen):
    """'unlit', 'blown', 'unseen' or None for one lamp: its measures per view and the views whose picture it stands
    in."""
    if blown(measures):
        return "blown"
    if not on_screen:
        return None if any(entry["share"] >= UNLIT_SHARE for entry in measures.values()) else "unseen"
    return None if any(entry["share"] >= UNLIT_SHARE for entry in measures.values()) else "unlit"
