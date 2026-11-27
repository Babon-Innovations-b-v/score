"""How curly the close-up's hair is (`photo_curl`), and the strands' wave, locks and frizz set from it (`styled`).

Round 1 typed the wave into each style by eye and hair.py's locks, flyaways and frizz were a curly head's for every
head: loose waves grew as tight ringlets and a sleek bob as a straggly mop (2026-11-26). Here the photo says it.

The hair in the photo is the pixels near the colour of the hair over the eyes (`hair_mask`), off the backdrop,
never skin, and never the face's or beard's box under the eyes (FACE_HALF of the pupils' distance either
side of their middle); scaled by the pupils' distance (`eyes.photo_pupils`, 63 mm). The strands' way at each pixel is
the least axis of the lightness's structure tensor (SIGMA_M). From seeds SEED_M apart, streamlines run along it both
ways, TRACE_M at most, in the hair; along each at least LEAST_TRACE_M long, the way's angle less its own quadratic
trend (the style's sweep and fall) is the wave: its root mean square (`swing`, degrees) and its period (twice the
run between its zero crossings). A wave of amplitude A and period P swings its way by atan(2 pi A / P), a root mean
square of that over the square root of two, so A = sqrt(2) tan(swing) P / (2 pi).

How curly it is (0 straight, 1 curly) is the swing between STRAIGHT_DEG and CURLY_DEG (an estimate, set on the three
gen2 close-ups and checked on their sheets). The wave is the one read, none under half STRAIGHT_DEG (the tensor's own
noise on straight hair); straight hair's locks are drawn together only at their tips and hardly (LOCK_PULL's low
end), with few flyaways and no frizz; curly hair gets hair.py's own."""
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.color import rgb2lab

from tools.characters.generated import eyes, labels
from tools.characters.whole import hair

SIZE = 1024
HAIR_SPREAD = 3.0  # the hair's colour within this many of its spreads (each of L, a, b)
SPREAD_FLOOR = (3.0, 1.5, 1.5)
BACKDROP_DELTA = 10.0
FACE_HALF = 1.0
TEXTURE = 3.0  # a pixel whose lightness varies this many times the backdrop's most is textured (hair)
SIGMA_M = (0.0004, 0.0025)  # the lightness's derivative's and the structure tensor's Gaussian
SEED_M = 0.004
STEP_M = 0.0005
TRACE_M = 0.08
LEAST_TRACE_M = 0.03
CLEAR = 0.25  # a streamline runs only through pixels this coherent
PERIOD_M = (0.015, 0.12)
STRAIGHT_DEG = 4.0
CURLY_DEG = 22.0
LOCK_PULL = ((0.05, 0.2), hair.LOCK_PULL)  # straight's, curly's
FLYAWAY = (0.2, 1.0)  # a share of hair.py's FLYAWAY_SHARE, straight's and curly's
FRIZZ = (0.0, 1.0)  # of its FRIZZ_SHARE


def picture_of(path):
    """The photo at SIZE x SIZE: (sRGB 0..1, CIELAB)."""
    picture = np.asarray(Image.open(path).convert("RGB").resize((SIZE, SIZE)), np.float64) / 255.0
    return picture, rgb2lab(picture)


def textured(lab, energy):
    """The pixels off the plain backdrop: by colour, or by texture where the hair's colour is the backdrop's (a silver
    head on a pale grey wall)."""
    corner = SIZE // 16
    corners = np.concatenate([lab[:corner, :corner].reshape(-1, 3), lab[:corner, -corner:].reshape(-1, 3)])
    plain = np.concatenate([energy[:corner, :corner].ravel(), energy[:corner, -corner:].ravel()])
    return ((np.linalg.norm(lab - np.median(corners, axis=0), axis=-1) > BACKDROP_DELTA)
            | (energy > TEXTURE * np.percentile(plain, 99)))


def hair_mask(lab, energy, pupils):
    """The photo's hair pixels: off the backdrop, never skin or the face's box, within HAIR_SPREAD of the colour of
    the hair over the eyes (its median and spread there: a bob lighter than its roots is still hair, a cream scarf
    is not), in a piece reaching over the eyes (the hair, not a coat of its colour)."""
    off = textured(lab, energy) & ~labels.skin_like(lab.reshape(-1, 3)).reshape(lab.shape[:2])
    rows, columns = np.mgrid[:SIZE, :SIZE]
    apart = np.linalg.norm(pupils[1] - pupils[0])
    middle, eyes_row = pupils[:, 0].mean(), pupils[:, 1].mean()
    face = (rows > eyes_row - 0.3 * apart) & (np.abs(columns - middle) < FACE_HALF * apart)
    over = off & (rows < eyes_row - 0.5 * apart) & (np.abs(columns - middle) < 2.5 * apart)
    median = np.median(lab[over], axis=0)
    spread = np.maximum(1.4826 * np.median(np.abs(lab[over] - median), axis=0), SPREAD_FLOOR)
    near_hair = (np.abs(lab - median) / spread).max(axis=-1) < HAIR_SPREAD
    mask = ndimage.binary_opening(near_hair & off & ~face, iterations=2)
    pieces, _ = ndimage.label(mask)
    top = int(eyes_row - 0.5 * apart)
    reaching = np.unique(pieces[:top][mask[:top]])
    return np.isin(pieces, reaching[reaching > 0])


def strand_ways(lab, metre):
    """Each pixel's strand angle (radians, columns then rows), its coherence (0..1) and its lightness's local
    energy."""
    lightness = lab[..., 0] / 100.0
    small, large = (sigma / metre for sigma in SIGMA_M)
    along_columns = ndimage.gaussian_filter(lightness, small, order=(0, 1))
    along_rows = ndimage.gaussian_filter(lightness, small, order=(1, 0))
    xx, xy, yy = (ndimage.gaussian_filter(product, large) for product in
                  (along_columns ** 2, along_columns * along_rows, along_rows ** 2))
    across = 0.5 * np.arctan2(2.0 * xy, xx - yy)
    coherence = np.sqrt((xx - yy) ** 2 + 4.0 * xy ** 2) / np.maximum(xx + yy, 1e-12)
    return across + np.pi / 2.0, coherence, xx + yy


def traced(angle, usable, seeds, metre, sign):
    """Streamlines from the seeds (columns, rows) along the strands' way, `sign` choosing which way: (steps x seeds x
    2 places, steps x seeds angles, steps x seeds alive)."""
    place = seeds.astype(float)
    way = None
    places, angles, alive_all = [], [], []
    alive = np.ones(len(seeds), dtype=bool)
    for _ in range(int(TRACE_M / STEP_M)):
        column, row = (np.clip(np.round(place[:, axis]).astype(int), 0, SIZE - 1) for axis in (0, 1))
        alive &= usable[row, column]
        local = angle[row, column]
        step = np.stack([np.cos(local), np.sin(local)], axis=1)
        reference = np.tile([0.0, sign], (len(seeds), 1)) if way is None else way
        step *= np.where((step * reference).sum(axis=1) < 0.0, -1.0, 1.0)[:, None]
        way = step
        places.append(place.copy())
        angles.append(np.arctan2(step[:, 1], step[:, 0]))
        alive_all.append(alive.copy())
        place = place + np.where(alive[:, None], step * STEP_M / metre, 0.0)
    return np.array(places), np.array(angles), np.array(alive_all)


def wave_of(angles, metre_step):
    """One streamline's swing (degrees, its angle less its quadratic trend, root mean square) and its period (m, or
    nan with under two zero crossings)."""
    along = np.arange(len(angles)) * metre_step
    unwrapped = np.unwrap(angles)
    residual = unwrapped - np.polyval(np.polyfit(along, unwrapped, 2), along)
    crossings = np.flatnonzero(np.diff(np.sign(residual)) != 0)
    period = 2.0 * (along[crossings[-1]] - along[crossings[0]]) / (len(crossings) - 1) if len(crossings) > 2 else np.nan
    return float(np.degrees(np.sqrt(np.mean(residual ** 2)))), period


def lines_of(angle, usable, metre):
    """The streamlines from seeds SEED_M apart, each run both ways and joined: a list of each one's way's angle along
    it (radians, STEP_M apart), those at least LEAST_TRACE_M long."""
    spacing = max(1, int(SEED_M / metre))
    rows, columns = np.mgrid[spacing // 2:SIZE:spacing, spacing // 2:SIZE:spacing]
    seeds = np.column_stack([columns.ravel(), rows.ravel()])
    seeds = seeds[usable[seeds[:, 1], seeds[:, 0]]]
    down, _, alive_down = traced(angle, usable, seeds, metre, 1.0)
    up, _, alive_up = traced(angle, usable, seeds, metre, -1.0)
    found = []
    for index in range(len(seeds)):
        joined = np.vstack([up[:int(alive_up[:, index].sum()), index][::-1],
                            down[1:int(alive_down[:, index].sum()), index]])
        if len(joined) * STEP_M < LEAST_TRACE_M:
            continue
        steps = np.diff(joined, axis=0)
        found.append(np.arctan2(steps[:, 1], steps[:, 0]))
    return found


def curl_of(lines):
    """The hair's curl from its streamlines: {swing_deg, period_m, wave_m, curly (0..1), lines}."""
    if not lines:
        return {"swing_deg": 0.0, "period_m": PERIOD_M[1], "wave_m": 0.0, "curly": 0.0, "lines": 0}
    read = [wave_of(angles, STEP_M) for angles in lines]
    swing = float(np.average([one[0] for one in read], weights=[len(angles) for angles in lines]))
    periods = np.array([one[1] for one in read])
    found = np.isfinite(periods)
    period = float(np.clip(np.median(periods[found]), *PERIOD_M)) if found.any() else PERIOD_M[1]
    wave = float(np.sqrt(2.0) * np.tan(np.radians(swing)) * period / (2.0 * np.pi))
    curly = float(np.clip((swing - STRAIGHT_DEG) / (CURLY_DEG - STRAIGHT_DEG), 0.0, 1.0))
    wave *= float(np.clip(2.0 * swing / STRAIGHT_DEG - 1.0, 0.0, 1.0))  # none under half STRAIGHT_DEG (the tensor's
    # own noise on straight hair)
    return {"swing_deg": round(swing, 2), "period_m": round(period, 4), "wave_m": round(wave, 5),
            "curly": round(curly, 3), "lines": len(lines)}


def photo_curl(path):
    """The close-up's hair's curl (`curl_of`), read on its hair (`hair_mask`), scaled by its pupils' distance."""
    picture, lab = picture_of(path)
    pupils = eyes.photo_pupils(picture)
    metre = eyes.PUPIL_DISTANCE_M / float(np.linalg.norm(pupils[1] - pupils[0]))
    angle, coherence, energy = strand_ways(lab, metre)
    usable = hair_mask(lab, energy, pupils) & (coherence > CLEAR)
    return curl_of(lines_of(angle, usable, metre))


def styled(style, curl):
    """The style with the wave, the locks' pull, the flyaways and the frizz set from the photo's `curl`."""
    share = curl["curly"]
    pull = tuple(float(straight + share * (curly - straight)) for straight, curly in zip(*LOCK_PULL))
    return {**style, "wave_m": curl["wave_m"], "wave_period_m": curl["period_m"], "lock_pull": pull,
            "flyaway_share": hair.FLYAWAY_SHARE * (FLYAWAY[0] + share * (FLYAWAY[1] - FLYAWAY[0])),
            "frizz_share": hair.FRIZZ_SHARE * (FRIZZ[0] + share * (FRIZZ[1] - FRIZZ[0]))}
