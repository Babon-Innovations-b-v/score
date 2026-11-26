"""The fabrics and construction marks clothes worn today are made of (#225, owner 2026-11-25: plain flat-colour cloth
"looks from 1950"), drawn by score (MIT) and written as score_lib surfaces to take in. score_lib held no denim and no
knit: its cottons are NVIDIA's flat woven props' cloth.

    python -m tools.characters.garments.fabrics <folder> <score commit>

Fabrics, each a tile of TILE_M square (its st over the garment's flat panels, cache.TEXTURE_METRES a unit, so the
material repeats it TEXTURE_METRES / TILE_M times a unit), with its colour, normal and ORM maps drawn from its
construction at its real thread counts:
- denim: a 3/1 right-hand warp-faced twill, 26 ends and 26 picks a centimetre (a 12 oz jeans denim's 25 to 30 ends), an
  indigo warp ring-dyed (each end its own depth of shade, slubs along it, ridge tops worn lighter) over a weft that
  shows as the grey-blue an ecru weft takes from the indigo beside it after washing;
- jersey: a single jersey knit, 12.8 wales and 16 courses a centimetre (a 160 g/m2 tee jersey's 12 to 16), each loop
  two legs in a V, a heather melange of a dark and a light fibre.

Construction marks (decals: colour with transparency, and a normal for the thread's relief), each drawn at its
maker's measures; a strip mark's u runs along its seam or edge (STRIP_PERIOD_MM a repeat), its v from the seam (0) out
across its width; a patch mark covers its patch once, its u towards the garment's side seam, its v up:
- a seam's fold shadow (the seam allowance under it pressing the cloth up beside a sunk line),
- jeans topstitching: two rows of 3 mm stitches in a tobacco gold thread 1.5 and 7.5 mm off a felled seam,
- a jeans hem: the fold's roll and one gold chain stitch 11 mm up,
- a tee's coverstitch hem: two tonal rows 6.4 mm apart, 15 and 21.4 mm up, the turned allowance's ridge at 25 mm,
- a tee's crew neck: a 13 mm 1x1 rib band, its seam's coverstitch under it,
- jeans pockets: a five-sided back patch pocket with its double topstitch and an arc stitch, a front scoop with its
  coin pocket, the fly's J-stitch, a belt loop, and a copper rivet;
- a jeans back yoke's felled seam, falling from the centre back to the side seam (GarmentCode shapes Pants' back with
  darts, which a pair of jeans has none of), and the waistband's brass tack button;
- a worn pair's fading where the cloth creases and rubs (#223 photoreal round 1: "denim wash and fading with knee and
  crotch creases"): whiskers fanning from the crotch over the thighs' tops, the knees' rubbed lighter, honeycombs
  behind the knees; the faded indigo laid partly over the twill (it shows through), each crease's ridge raised and its
  fold sunk.

Colours are linear albedo; each mark's thread colour is named beside it. Writes each surface's material.usda,
surface.json and maps under <folder>/<id>/, and <folder>/take-in.json for `score-lib take-in`.
"""
import json
import math
import pathlib
import sys

import numpy as np

TILE_M = 0.1  # a fabric tile's side
TILE_PX = 2048
STRIP_PERIOD_MM = 12.0  # four 3 mm stitches
MARK_PX_PER_MM = 20.0  # strip marks
PATCH_PX_PER_MM = 8.0  # patch marks

DENIM = {"ends": 256, "picks": 256, "warp": (0.021, 0.042, 0.115), "worn": (0.115, 0.188, 0.352),
         "weft": (0.30, 0.30, 0.33), "relief_mm": 0.18, "roughness": 0.82}
JERSEY = {"wales": 128, "courses": 160, "dark": (0.30, 0.30, 0.295), "light": (0.40, 0.40, 0.39),
          "light_share": 0.55, "relief_mm": 0.22, "roughness": 0.88}
GOLD_THREAD = (0.58, 0.26, 0.045)  # jeans' tobacco gold topstitch thread, sRGB (200, 140, 60)
GREY_THREAD = (0.24, 0.24, 0.235)  # a heather grey tee's tonal thread, a shade under its cloth
COPPER = (0.80, 0.42, 0.25)  # a copper rivet's base colour (metallic)
BRASS = (0.62, 0.45, 0.20)  # a jeans tack button's antique brass (metallic)
FADED = (0.30, 0.42, 0.62)  # indigo worn down to its ring-dyed core's lighter blue where it creases and rubs


def periodic_noise(size, cycles, seed):
    """A smooth random field on a size x size torus, its features about size / cycles across, mean 0, sd 1."""
    rng = np.random.default_rng(seed)
    spectrum = np.fft.fft2(rng.standard_normal((size, size)))
    frequency = np.fft.fftfreq(size) * size
    radius = np.hypot(*np.meshgrid(frequency, frequency, indexing="ij"))
    field = np.real(np.fft.ifft2(spectrum * np.exp(-(radius / cycles) ** 2)))
    return (field - field.mean()) / (field.std() + 1e-12)


def normal_map(height_mm, mm_per_px):
    """A tangent-space normal map (0..1, OpenGL's +y up) of a periodic height field."""
    across = (np.roll(height_mm, -1, axis=1) - np.roll(height_mm, 1, axis=1)) / (2.0 * mm_per_px)
    down = (np.roll(height_mm, -1, axis=0) - np.roll(height_mm, 1, axis=0)) / (2.0 * mm_per_px)
    normal = np.stack([-across, down, np.ones_like(height_mm)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return normal * 0.5 + 0.5


def encoded(linear):
    """Linear values (0..1) in sRGB's transfer."""
    linear = np.clip(linear, 0.0, 1.0)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1.0 / 2.4) - 0.055)


def denim_maps(spec=DENIM, size=TILE_PX):
    """Denim's colour (linear), height (mm) and roughness: the twill's cells, each end's shade and slubs, worn
    ridges, streaks along the warp."""
    pixel = np.arange(size)
    across, along = np.meshgrid(pixel * spec["ends"] / size, pixel * spec["picks"] / size, indexing="xy")
    end, pick = np.floor(across).astype(int), np.floor(along).astype(int)
    inside_u, inside_v = across - end, along - pick
    warp_up = (end - pick) % 4 != 0  # 3 up, 1 down, stepping one end each pick: the right-hand twill line
    warp_height = np.sqrt(np.clip(np.sin(np.pi * inside_u), 0.0, 1.0)) * (0.85 + 0.15 * np.sin(np.pi * inside_v))
    weft_height = 0.8 * np.sqrt(np.clip(np.sin(np.pi * inside_v), 0.0, 1.0))
    height = np.where(warp_up, warp_height, weft_height)
    rng = np.random.default_rng(7)
    end_shade = rng.normal(0.0, 0.12, spec["ends"])[end % spec["ends"]]  # each end dyed its own depth
    slubs = periodic_noise(size, 40.0, 11)  # ring-spun slubs: streaks along the warp
    streak = np.repeat(periodic_noise(size, 6.0, 12).mean(axis=0, keepdims=True), size, axis=0)
    # no wear mottle across the tile: 3 cm clouds repeating every 10 cm read as an acid wash painted on (#225 round
    # 9); a jeans' fading follows the body, not the tile
    worn = np.clip(0.25 + 0.15 * streak + 0.1 * slubs * (np.abs(slubs) > 1.2), 0.0, 1.0)
    warp_colour = np.asarray(spec["warp"]) * (1.0 + end_shade + 0.08 * slubs)[..., None]
    warp_colour = warp_colour + (np.asarray(spec["worn"]) - np.asarray(spec["warp"])) * (worn * height)[..., None]
    weft_colour = np.asarray(spec["weft"]) * (0.92 + 0.08 * periodic_noise(size, 60.0, 14))[..., None]
    colour = np.where(warp_up[..., None], warp_colour, weft_colour) * (0.75 + 0.25 * height)[..., None]
    roughness = spec["roughness"] + 0.03 * slubs
    return colour, height * spec["relief_mm"], roughness


def jersey_maps(spec=JERSEY, size=TILE_PX):
    """Jersey's colour (linear), height (mm) and roughness: each loop's two legs in a V, a heather melange."""
    pixel = np.arange(size)
    across, along = np.meshgrid(pixel * spec["wales"] / size, pixel * spec["courses"] / size, indexing="xy")
    inside_u, inside_v = across - np.floor(across), along - np.floor(along)
    height = np.zeros((size, size))
    for shift in (0.0, 1.0):  # this course's legs and the one above's tails reaching into it
        leg_v = inside_v + shift
        for side in (-1.0, 1.0):
            centre = 0.5 + side * 0.28 * (1.0 - np.clip(leg_v / 1.3, 0.0, 1.0))
            weight = np.clip(1.3 - leg_v, 0.0, 1.0) * np.clip(leg_v + 0.15, 0.0, 1.0)
            height = np.maximum(height, weight * np.exp(-((inside_u - centre) / 0.13) ** 2))
    # the yarn's fibres: streaks along the course (x), a few loops long, a loop's height across
    grain = periodic_noise(size, 500.0, 21)
    fibre = sum(np.roll(grain, shift, axis=1) for shift in range(0, 64, 4)) / 16.0
    fibre = fibre / fibre.std() + 0.5 * periodic_noise(size, 200.0, 22)
    light = (fibre > np.quantile(fibre, 1.0 - spec["light_share"]))[..., None]
    colour = np.where(light, np.asarray(spec["light"]), np.asarray(spec["dark"]))
    colour = colour * (0.85 + 0.15 * height)[..., None]
    roughness = spec["roughness"] + 0.03 * periodic_noise(size, 20.0, 23)
    return colour, height * spec["relief_mm"], roughness


class Mark:
    """A decal drawn in millimetres: premultiplied colour, coverage and the thread's height."""

    def __init__(self, width_mm, height_mm, px_per_mm):
        self.px_per_mm = px_per_mm
        self.shape = (int(round(height_mm * px_per_mm)), int(round(width_mm * px_per_mm)))
        self.colour = np.zeros(self.shape + (3,))
        self.cover = np.zeros(self.shape)
        self.height = np.zeros(self.shape)
        rows, columns = np.indices(self.shape)
        self.u_mm = (columns + 0.5) / px_per_mm
        self.v_mm = (self.shape[0] - rows - 0.5) / px_per_mm  # v up: row 0 is the top

    def laid(self, cover, colour):
        """`colour` laid over what is drawn with coverage `cover` (0..1 per pixel)."""
        cover = np.clip(cover, 0.0, 1.0)
        self.colour = np.asarray(colour) * cover[..., None] + self.colour * (1.0 - cover[..., None])
        self.cover = cover + self.cover * (1.0 - cover)

    def shadow(self, distance_mm, reach_mm, strength):
        """A soft shadow falling off from distance 0 to `reach_mm`."""
        self.laid(strength * np.clip(1.0 - distance_mm / reach_mm, 0.0, 1.0) ** 2, (0.0, 0.0, 0.0))

    def thread(self, starts, ends, colour, radius_mm=0.28):
        """Stitches as capsules from `starts` to `ends` (mm, n x 2), raised as a round thread."""
        for start, end in zip(np.asarray(starts, float), np.asarray(ends, float)):
            low = np.floor((np.minimum(start, end) - radius_mm * 2) * self.px_per_mm).astype(int)
            high = np.ceil((np.maximum(start, end) + radius_mm * 2) * self.px_per_mm).astype(int)
            columns = slice(max(low[0], 0), min(high[0], self.shape[1]))
            rows = slice(max(self.shape[0] - high[1], 0), min(self.shape[0] - low[1], self.shape[0]))
            if columns.start >= columns.stop or rows.start >= rows.stop:
                continue
            u, v = self.u_mm[rows, columns], self.v_mm[rows, columns]
            span = end - start
            along = np.clip(((u - start[0]) * span[0] + (v - start[1]) * span[1]) / max(span @ span, 1e-9), 0, 1)
            distance = np.hypot(u - start[0] - along * span[0], v - start[1] - along * span[1])
            cover = np.clip((radius_mm - distance) * self.px_per_mm + 0.5, 0.0, 1.0)
            twist = 0.85 + 0.15 * np.cos((along * math.hypot(*span) / 0.35 + distance / radius_mm) * 2 * np.pi)
            shade = (0.55 + 0.45 * np.sqrt(np.clip(1.0 - (distance / radius_mm) ** 2, 0.0, 1.0))) * twist
            region_colour = self.colour[rows, columns]
            region_cover = self.cover[rows, columns]
            self.colour[rows, columns] = (np.asarray(colour) * (cover * shade)[..., None]
                                          + region_colour * (1.0 - cover[..., None]))
            self.cover[rows, columns] = cover + region_cover * (1.0 - cover)
            relief = radius_mm * np.sqrt(np.clip(1.0 - (distance / radius_mm) ** 2, 0.0, 1.0))
            self.height[rows, columns] = np.maximum(self.height[rows, columns], relief)

    def stitched(self, line_mm, colour, stitch_mm=3.0, gap_mm=0.5, radius_mm=0.28, periodic_mm=None):
        """A row of stitches along a polyline (mm), each `stitch_mm` long with `gap_mm` where the thread goes under;
        with `periodic_mm`, the row's stitches also drawn a period either side so a strip repeats seamlessly."""
        line = np.asarray(line_mm, float)
        lengths = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))]
        count = int(lengths[-1] // stitch_mm)
        heads = np.arange(count) * stitch_mm + gap_mm / 2.0
        starts = np.stack([np.interp(heads, lengths, line[:, axis]) for axis in (0, 1)], axis=1)
        tails = heads + stitch_mm - gap_mm
        ends = np.stack([np.interp(tails, lengths, line[:, axis]) for axis in (0, 1)], axis=1)
        shifts = [0.0] if periodic_mm is None else [-periodic_mm, 0.0, periodic_mm]
        for shift in shifts:
            self.thread(starts + [shift, 0.0], ends + [shift, 0.0], colour, radius_mm)

    def maps(self):
        """(RGBA in sRGB, 0..1; the normal map, 0..1)."""
        straight = self.colour / np.maximum(self.cover, 1e-6)[..., None]
        rgba = np.concatenate([encoded(straight), self.cover[..., None]], axis=-1)
        return rgba, normal_map(self.height[::-1], 1.0 / self.px_per_mm)[::-1]


def strip_row(mark, v_mm, colour, width_mm=STRIP_PERIOD_MM):
    """One stitch row across a strip at `v_mm` from its seam, repeating every strip period."""
    mark.stitched([[0.0, v_mm], [width_mm, v_mm]], colour, periodic_mm=width_mm)


def seam_shadow_mark():
    """A plain seam's side: its sunk line's shadow and the pressed allowance's soft rise beside it, 6 mm wide."""
    mark = Mark(STRIP_PERIOD_MM, 6.0, MARK_PX_PER_MM)
    mark.shadow(mark.v_mm, 1.6, 0.55)
    mark.height = 0.12 * np.exp(-((mark.v_mm - 2.5) / 1.5) ** 2)
    return mark


def topstitch_mark(colour=GOLD_THREAD):
    """A felled jeans seam's topstitched side: the fold's shadow and two gold rows 1.5 and 7.5 mm off it."""
    mark = Mark(STRIP_PERIOD_MM, 10.0, MARK_PX_PER_MM)
    mark.shadow(mark.v_mm, 1.2, 0.55)
    mark.shadow(np.abs(mark.v_mm - 9.0), 1.5, 0.18)  # the felled allowance's edge under the cloth
    mark.height = 0.15 * np.exp(-((mark.v_mm - 4.5) / 3.0) ** 2)
    for row in (1.5, 7.5):
        strip_row(mark, row, colour)
    return mark


def jeans_hem_mark(colour=GOLD_THREAD):
    """A jeans hem or waistband edge: the fold's roll at the edge, one gold chain stitch 11 mm in, the turned
    allowance's edge at 16 mm."""
    mark = Mark(STRIP_PERIOD_MM, 18.0, MARK_PX_PER_MM)
    mark.shadow(mark.v_mm, 0.8, 0.35)
    mark.shadow(np.abs(mark.v_mm - 16.0), 1.4, 0.25)
    mark.height = 0.25 * np.exp(-((mark.v_mm - 8.0) / 5.0) ** 2)
    strip_row(mark, 11.0, colour)
    strip_row(mark, 3.0, colour)
    return mark


def coverstitch_hem_mark(colour=GREY_THREAD):
    """A tee's hem: the folded edge's roll, two tonal coverstitch rows 15 and 21.4 mm in, the turned allowance's
    ridge at 25 mm."""
    mark = Mark(STRIP_PERIOD_MM, 27.0, MARK_PX_PER_MM)
    mark.shadow(mark.v_mm, 0.8, 0.3)
    mark.shadow(np.abs(mark.v_mm - 25.0), 1.5, 0.2)
    mark.height = 0.18 * np.exp(-((mark.v_mm - 12.0) / 8.0) ** 2)
    for row in (15.0, 21.4):
        strip_row(mark, row, colour, STRIP_PERIOD_MM)
    return mark


def rib_neck_mark(cloth=JERSEY, colour=GREY_THREAD):
    """A women's fitted crew neck's 13 mm 1x1 rib band (the tee's own melange, ribs 1.5 mm apart, eight to the strip's
    repeat) from the edge, its join's shadow and the coverstitch 3 mm under it. Owner 2026-11-25: the 18 mm band, its
    1.6 mm ribs broken every 12 mm repeat, read as "neck rib too thick" and a band of blocks."""
    mark = Mark(STRIP_PERIOD_MM, 19.0, MARK_PX_PER_MM)
    band = mark.v_mm < 13.0
    ribs = 0.5 + 0.5 * np.cos(mark.u_mm / 1.5 * 2 * np.pi)
    melange = np.where(ribs[..., None] > 0.5, np.asarray(cloth["light"]), np.asarray(cloth["dark"]) * 1.3)
    mark.laid(band * 1.0, (0.0, 0.0, 0.0))
    mark.colour = np.where(band[..., None], melange * (0.7 + 0.3 * ribs)[..., None], mark.colour)
    mark.height = band * 0.3 * ribs
    mark.shadow(np.abs(mark.v_mm - 13.0), 1.2, 0.45)
    mark.shadow(mark.v_mm, 0.6, 0.3)
    strip_row(mark, 16.0, colour)
    return mark


def polygon_distance(mark, corners):
    """Each pixel's distance (mm) to a closed polygon's outline and whether it lies inside."""
    corners = np.asarray(corners, float)
    best = np.full(mark.shape, np.inf)
    inside = np.zeros(mark.shape, bool)
    for start, end in zip(corners, np.roll(corners, -1, axis=0)):
        span = end - start
        along = np.clip(((mark.u_mm - start[0]) * span[0] + (mark.v_mm - start[1]) * span[1]) / (span @ span), 0, 1)
        best = np.minimum(best, np.hypot(mark.u_mm - start[0] - along * span[0], mark.v_mm - start[1] - along * span[1]))
        crosses = ((start[1] > mark.v_mm) != (end[1] > mark.v_mm))
        meet = start[0] + (mark.v_mm - start[1]) * span[0] / np.where(span[1] == 0, 1e-9, span[1])
        inside ^= crosses & (mark.u_mm < meet)
    return best, inside


def inset(corners, by_mm):
    """A convex polygon's corners moved `by_mm` inside along its edges' normals (counter-clockwise corners)."""
    corners = np.asarray(corners, float)
    moved = []
    for index in range(len(corners)):
        before, here, after = corners[index - 1], corners[index], corners[(index + 1) % len(corners)]
        normals = []
        for start, end in ((before, here), (here, after)):
            span = (end - start) / np.linalg.norm(end - start)
            normals.append(np.array([-span[1], span[0]]))
        bisector = normals[0] + normals[1]
        bisector /= np.linalg.norm(bisector)
        moved.append(here + bisector * by_mm / max(bisector @ normals[0], 0.2))
    return np.array(moved)


def back_pocket_mark(colour=GOLD_THREAD):
    """A five-sided jeans back patch pocket (140 x 150 mm, its point down): the patch's edge raised over the seat
    with its shadow outside, its top hem's two rows, the sides' double topstitch, an arc stitched across it, bar
    tacks at its top corners."""
    width, height, margin = 140.0, 150.0, 6.0
    mark = Mark(width + 2 * margin, height + 2 * margin, PATCH_PX_PER_MM)
    corners = np.array([[0, 20], [70, 0], [140, 20], [140, 150], [0, 150]], float) + margin
    distance, inside = polygon_distance(mark, corners)
    mark.shadow(np.where(inside, np.inf, distance), 2.5, 0.45)
    mark.laid(inside * np.clip(1.0 - distance / 1.2, 0.0, 1.0) * 0.25, (1.0, 1.0, 1.0))  # the folded edge's light
    mark.height = inside * 0.35 * np.clip(distance / 3.0, 0.0, 1.0)
    for by in (1.5, 7.5):
        line = inset(corners, by)
        mark.stitched(np.vstack([line[3], line[4], line[0], line[1], line[2], line[3]]), colour)
    for down in (12.0, 18.0):
        mark.stitched([[margin + 2, margin + height - down], [margin + width - 2, margin + height - down]], colour)
    mark.shadow(np.abs(mark.v_mm - (margin + height - 22.0)) + (~inside) * 99, 1.2, 0.2)
    sweep = np.linspace(0.0, 1.0, 60)
    for lift in (0.0, 6.0):
        arc = np.stack([margin + 12 + sweep * (width - 24),
                        margin + 75 + lift + 28 * np.sin(sweep * np.pi) - 10 * sweep], axis=1)
        mark.stitched(arc, colour)
    for corner in (corners[4], corners[3]):
        side = 1.0 if corner[0] < margin + 1 else -1.0
        tack_u = corner[0] + side * np.array([2.0, 9.0])
        for step in np.linspace(-3.5, 3.5, 9):
            mark.thread([[tack_u[0], corner[1] - 4.0 + step]], [[tack_u[1], corner[1] - 4.0 + step + 0.6]], colour,
                        0.3)
    return mark


def front_scoop_mark(colour=GOLD_THREAD):
    """A jeans front pocket's scoop (110 x 90 mm patch whose top edge meets the waistband and whose right edge, +u, is
    the side seam): the opening's folded edge curving from 100 mm in to 75 mm down the side seam, its shadow into the
    pocket and two gold rows, the coin pocket's top and sides with their rows inside the scoop."""
    width, height = 110.0, 90.0
    mark = Mark(width, height, PATCH_PX_PER_MM)
    sweep = np.linspace(0.0, 1.0, 80)
    curve = np.stack([width - 100.0 + 100.0 * np.sin(sweep * np.pi / 2) ** 1.3,
                      height - 75.0 * (1.0 - np.cos(sweep * np.pi / 2)) ** 0.9], axis=1)
    distance = np.full(mark.shape, np.inf)
    for start, end in zip(curve[:-1], curve[1:]):
        span = end - start
        along = np.clip(((mark.u_mm - start[0]) * span[0] + (mark.v_mm - start[1]) * span[1]) / (span @ span), 0, 1)
        distance = np.minimum(distance, np.hypot(mark.u_mm - start[0] - along * span[0],
                                                 mark.v_mm - start[1] - along * span[1]))
    facing = mark.v_mm > np.interp(mark.u_mm, curve[:, 0], curve[:, 1])  # the pocket's facing, under the opening
    mark.shadow(np.where(facing, distance, np.inf), 2.2, 0.6)  # the opening's edge throws its shadow onto it
    mark.height = 0.3 * np.exp(-(distance / 2.0) ** 2)
    for by in (1.5, 7.5):
        normal = np.gradient(curve, axis=0)[:, ::-1] * [1.0, -1.0]
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        mark.stitched(curve - normal * by, colour)
    coin = np.array([[width - 62.0, height], [width - 62.0, height - 48.0], [width - 22.0, height - 52.0],
                     [width - 22.0, height]])
    mark.stitched(coin[:2], colour)
    mark.stitched(coin[2:][::-1], colour)
    mark.stitched([[width - 60.0, height - 40.0], [width - 24.0, height - 43.0]], colour)
    mark.shadow(np.abs(mark.u_mm - (width - 62.0)) + (mark.v_mm < height - 48.0) * 99, 0.9, 0.25)
    mark.shadow(np.abs(mark.u_mm - (width - 22.0)) + (mark.v_mm < height - 52.0) * 99, 0.9, 0.25)
    return mark


def fly_mark(colour=GOLD_THREAD):
    """The fly's J-stitch (40 x 190 mm, u from the centre front): two gold rows 32 and 38 mm off the centre down to
    40 mm over its foot, curving into the centre front at the bottom, and the fly's fold shadow along the centre."""
    width, height = 45.0, 190.0
    mark = Mark(width, height, PATCH_PX_PER_MM)
    for offset in (32.0, 38.0):
        sweep = np.linspace(0.0, np.pi / 2, 30)
        straight = np.array([[offset, height], [offset, 40.0]])
        hook = np.stack([offset * np.cos(sweep), 6.0 + 34.0 * (1.0 - np.sin(sweep))], axis=1)
        mark.stitched(np.vstack([straight, hook[1:]]), colour)
    mark.shadow(np.abs(mark.u_mm - 1.0), 1.5, 0.45)
    return mark


def belt_loop_mark(colour=GOLD_THREAD):
    """A belt loop over the waistband (12 x 50 mm): its raised strip, its two edges' shadows and rows, bar tacks at
    both ends."""
    width, height, margin = 12.0, 50.0, 3.0
    mark = Mark(width + 2 * margin, height, PATCH_PX_PER_MM * 2)
    inside = (mark.u_mm > margin) & (mark.u_mm < margin + width)
    edge = np.minimum(np.abs(mark.u_mm - margin), np.abs(mark.u_mm - margin - width))
    mark.shadow(np.where(inside, np.inf, edge), 1.8, 0.5)
    mark.laid(inside * np.exp(-(edge / 0.8) ** 2) * 0.25, (1.0, 1.0, 1.0))
    mark.height = inside * 0.6 * np.clip(edge / 2.0, 0.0, 1.0)
    for row in (margin + 2.0, margin + width - 2.0):
        mark.stitched([[row, 4.0], [row, height - 4.0]], colour)
    for end in (5.0, height - 5.0):
        for step in np.linspace(margin + 1.0, margin + width - 1.0, 10):
            mark.thread([[step, end - 2.5]], [[step + 0.5, end + 2.5]], colour, 0.3)
    return mark


def rivet_mark():
    """A copper rivet's 8 mm domed head and its ring, with the cloth's dimple's shadow round it."""
    mark = Mark(12.0, 12.0, PATCH_PX_PER_MM * 4)
    distance = np.hypot(mark.u_mm - 6.0, mark.v_mm - 6.0)
    mark.shadow(np.where(distance > 4.0, distance - 4.0, np.inf), 1.5, 0.5)
    mark.laid(np.clip((4.0 - distance) * mark.px_per_mm, 0.0, 1.0), COPPER)
    mark.height = 0.8 * np.sqrt(np.clip(1.0 - (distance / 4.0) ** 2, 0.0, 1.0)) - 0.15 * (np.abs(distance - 3.2) < 0.3)
    return mark


def yoke_mark(colour=GOLD_THREAD):
    """A jeans back yoke's felled seam across one back panel (230 x 90 mm, u from the centre back towards the side
    seam, v up, its top at the panel's top): falling from 70 mm under the top at the centre back to 35 mm at the side,
    its fold's shadow on the seat side, the felled allowance's ridge and two gold rows 1.5 and 7.5 mm under it."""
    width, height = 230.0, 90.0
    mark = Mark(width, height, PATCH_PX_PER_MM)
    line = np.array([[0.0, height - 70.0], [width, height - 35.0]])
    slope = (line[1, 1] - line[0, 1]) / width
    under = (line[0, 1] + slope * mark.u_mm - mark.v_mm) / math.hypot(1.0, slope)  # mm under the seam, + below it
    mark.shadow(np.where(under > 0.0, under, np.inf), 1.2, 0.55)
    mark.shadow(np.abs(under + 2.0), 1.0, 0.25)  # the yoke's fold over the seam
    mark.shadow(np.abs(under - 9.0), 1.5, 0.18)  # the felled allowance's edge under the cloth
    mark.height = 0.15 * np.exp(-((under - 4.5) / 3.0) ** 2)
    for row in (1.5, 7.5):
        drop = row * math.hypot(1.0, slope)
        mark.stitched(line - [0.0, drop], colour)
    return mark


def button_mark():
    """A jeans waistband's 17 mm tack button (22 x 22 mm): its domed antique brass head, a rolled rim and a stamped
    ring of beads, the cloth's dimple's shadow round it."""
    mark = Mark(22.0, 22.0, PATCH_PX_PER_MM * 4)
    distance = np.hypot(mark.u_mm - 11.0, mark.v_mm - 11.0)
    mark.shadow(np.where(distance > 8.5, distance - 8.5, np.inf), 2.0, 0.55)
    head = np.clip((8.5 - distance) * mark.px_per_mm, 0.0, 1.0)
    angle = np.arctan2(mark.v_mm - 11.0, mark.u_mm - 11.0)
    beads = (np.abs(distance - 6.6) < 0.45) * (np.cos(angle * 24.0) > 0.2)
    shade = 0.75 + 0.25 * np.clip(1.0 - distance / 8.5, 0.0, 1.0) - 0.25 * beads - 0.2 * (np.abs(distance - 7.8) < 0.3)
    mark.laid(head, np.asarray(BRASS) * shade[..., None])
    mark.height = head * (1.2 * np.sqrt(np.clip(1.0 - (distance / 8.5) ** 2, 0.0, 1.0)) + 0.25 * (distance > 7.5)
                          - 0.12 * beads)
    return mark


def crease_fade(mark, centre_line, half_width_mm, strength):
    """One worn crease along a polyline (mm): the faded indigo laid over the twill, strongest along its ridge and
    tapering to its ends, the ridge raised and a sunk fold beside it."""
    line = np.asarray(centre_line, float)
    distance = np.full(mark.shape, np.inf)
    share = np.zeros(mark.shape)
    lengths = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))]
    for index, (start, end) in enumerate(zip(line[:-1], line[1:])):
        span = end - start
        along = np.clip(((mark.u_mm - start[0]) * span[0] + (mark.v_mm - start[1]) * span[1]) / (span @ span), 0, 1)
        here = np.hypot(mark.u_mm - start[0] - along * span[0], mark.v_mm - start[1] - along * span[1])
        nearer = here < distance
        distance = np.where(nearer, here, distance)
        share = np.where(nearer, (lengths[index] + along * np.linalg.norm(span)) / lengths[-1], share)
    taper = np.sin(np.pi * np.clip(share, 0.0, 1.0)) ** 0.6
    width = half_width_mm * taper + 1e-6
    cover = strength * taper * np.exp(-(distance / width) ** 2)
    mark.laid(cover, FADED)
    mark.height = mark.height + 0.35 * taper * np.exp(-(distance / (0.6 * width)) ** 2) \
        - 0.25 * taper * np.exp(-((distance - 1.2 * width) / (0.4 * width)) ** 2)


def whiskers_mark():
    """Whiskers over a thigh's top (170 x 100 mm, u from the crotch side towards the side seam, v up): six creases
    fanning from the crotch up and out over the thigh, the longest in the middle, a soft fade under them."""
    width, height = 170.0, 100.0
    mark = Mark(width, height, PATCH_PX_PER_MM)
    mark.laid(0.18 * np.exp(-(((mark.u_mm - 60.0) / 70.0) ** 2 + ((mark.v_mm - 55.0) / 40.0) ** 2)), FADED)
    for number, (rise, length) in enumerate(((4.0, 90.0), (10.0, 120.0), (17.0, 140.0), (24.0, 130.0),
                                             (31.0, 105.0), (38.0, 80.0))):
        sweep = np.linspace(0.0, 1.0, 24)
        start = np.array([8.0 + 4.0 * number, 18.0 + 7.0 * number])
        line = start + np.stack([sweep * length, sweep * rise + 8.0 * np.sin(sweep * np.pi) * (number % 2 - 0.5)],
                                axis=1)
        crease_fade(mark, line, 3.0, 0.3)
    return mark


def knee_mark():
    """A knee's rub (130 x 160 mm, centred on the knee): an oval fade lighter at its middle, two soft creases across
    it where the knee bends."""
    width, height = 130.0, 160.0
    mark = Mark(width, height, PATCH_PX_PER_MM)
    mark.laid(0.3 * np.exp(-(((mark.u_mm - 65.0) / 45.0) ** 2 + ((mark.v_mm - 80.0) / 60.0) ** 2) * 1.5), FADED)
    for level, bow in ((58.0, 6.0), (104.0, -5.0)):
        sweep = np.linspace(0.0, 1.0, 24)
        crease_fade(mark, np.stack([20.0 + sweep * 90.0, level + bow * np.sin(sweep * np.pi)], axis=1), 4.0, 0.25)
    return mark


def honeycomb_mark():
    """Honeycombs behind a knee (140 x 90 mm, centred on the knee's fold): three or four short creases stacked across
    the fold, each bowed, a soft fade round them."""
    width, height = 140.0, 90.0
    mark = Mark(width, height, PATCH_PX_PER_MM)
    mark.laid(0.15 * np.exp(-(((mark.u_mm - 70.0) / 55.0) ** 2 + ((mark.v_mm - 45.0) / 30.0) ** 2)), FADED)
    for level, start, length, bow in ((18.0, 25.0, 90.0, 5.0), (36.0, 15.0, 110.0, -4.0), (54.0, 20.0, 100.0, 5.0),
                                      (72.0, 35.0, 70.0, -3.0)):
        sweep = np.linspace(0.0, 1.0, 24)
        crease_fade(mark, np.stack([start + sweep * length, level + bow * np.sin(sweep * np.pi)], axis=1), 3.0, 0.4)
    return mark


FABRICS = {
    "denim_indigo_twill": {"title": "Denim, mid indigo 3/1 twill", "maps": denim_maps, "spec": DENIM,
                           "why": "a 12 oz jeans denim: 3/1 right-hand twill, 26 ends and picks a cm, ring-dyed "
                                  "indigo warp (each end its own shade, slubs, worn ridges) over a washed ecru weft"},
    "jersey_heather_grey": {"title": "Cotton jersey, heather grey", "maps": jersey_maps, "spec": JERSEY,
                            "why": "a 160 g/m2 single jersey: 12.8 wales and 16 courses a cm, V loops, a melange of "
                                   "a dark and a light grey fibre"},
}
MARKS = {
    "seam_shadow": ("Seam line (decal)", seam_shadow_mark, 0.85, 0.0, "strip"),
    "topstitch_jeans_gold": ("Jeans topstitch, two gold rows (decal)", topstitch_mark, 0.6, 0.0, "strip"),
    "hem_jeans_gold": ("Jeans hem, gold chain stitch (decal)", jeans_hem_mark, 0.6, 0.0, "strip"),
    "hem_coverstitch_grey": ("Tee hem, tonal coverstitch (decal)", coverstitch_hem_mark, 0.7, 0.0, "strip"),
    "neck_rib_heather_grey": ("Crew neck rib band, heather grey (decal)", rib_neck_mark, 0.88, 0.0, "strip"),
    "pocket_back_jeans_gold": ("Jeans back patch pocket (decal)", back_pocket_mark, 0.6, 0.0, "patch"),
    "pocket_front_jeans_gold": ("Jeans front scoop and coin pocket (decal)", front_scoop_mark, 0.6, 0.0, "patch"),
    "fly_jeans_gold": ("Jeans fly J-stitch (decal)", fly_mark, 0.6, 0.0, "patch"),
    "belt_loop_jeans_gold": ("Jeans belt loop (decal)", belt_loop_mark, 0.6, 0.0, "patch"),
    "rivet_copper": ("Copper jeans rivet (decal)", rivet_mark, 0.35, 1.0, "patch"),
    "yoke_jeans_gold": ("Jeans back yoke seam, two gold rows (decal)", yoke_mark, 0.6, 0.0, "patch"),
    "button_jeans_brass": ("Jeans waistband tack button, antique brass (decal)", button_mark, 0.4, 1.0, "patch"),
    "whiskers_denim_fade": ("Denim whiskers, faded creases over the thigh (decal)", whiskers_mark, 0.85, 0.0,
                            "patch"),
    "knee_denim_fade": ("Denim knee rub, faded (decal)", knee_mark, 0.85, 0.0, "patch"),
    "honeycomb_denim_fade": ("Denim honeycombs behind the knee, faded creases (decal)", honeycomb_mark, 0.85, 0.0,
                             "patch"),
}


def texture_shader(surface, name, file, colour_space, outputs, mapped):
    """One UsdUVTexture shader block reading `file` through the st (or its mapping when `mapped`)."""
    source = "mapping" if mapped else "st"
    lines = [f'    def Shader "{name}"', "    {", '        uniform token info:id = "UsdUVTexture"',
             f"        asset inputs:file = @./{file}@", f'        token inputs:sourceColorSpace = "{colour_space}"',
             f"        float2 inputs:st.connect = </{surface}/{source}.outputs:result>",
             '        token inputs:wrapS = "repeat"', '        token inputs:wrapT = "repeat"']
    if name == "normal":
        lines += ["        float4 inputs:bias = (-1, -1, -1, 0)", "        float4 inputs:scale = (2, 2, 2, 1)"]
    lines += [f"        {kind} outputs:{output}" for kind, output in outputs] + ["    }", ""]
    return "\n".join(lines)


def fabric_usda(surface):
    """A fabric's material: colour, normal and ORM maps through a mapping that repeats the tile at its size."""
    repeat = 0.5 / TILE_M  # cache.TEXTURE_METRES of cloth is one st unit
    inputs = [f"        color3f inputs:diffuseColor.connect = </{surface}/colour.outputs:rgb>",
              f"        normal3f inputs:normal.connect = </{surface}/normal.outputs:rgb>",
              f"        float inputs:occlusion.connect = </{surface}/orm.outputs:r>",
              f"        float inputs:roughness.connect = </{surface}/orm.outputs:g>",
              "        float inputs:metallic = 0"]
    shaders = [texture_shader(surface, "colour", "colour.png", "sRGB", [("float3", "rgb")], True),
               texture_shader(surface, "normal", "normal.png", "raw", [("float3", "rgb")], True),
               texture_shader(surface, "orm", "orm.png", "raw", [("float", "r"), ("float", "g")], True)]
    mapping = (f'    def Shader "mapping"\n    {{\n        uniform token info:id = "UsdTransform2d"\n'
               f"        float2 inputs:in.connect = </{surface}/st.outputs:result>\n"
               f"        float2 inputs:scale = ({repeat:g}, {repeat:g})\n        float2 outputs:result\n    }}\n")
    return material_text(surface, inputs, mapping + "\n" + "\n".join(shaders))


def mark_usda(surface, roughness, metallic):
    """A decal's material: colour and coverage from decal.png, the thread's relief from normal.png."""
    inputs = [f"        color3f inputs:diffuseColor.connect = </{surface}/decal.outputs:rgb>",
              f"        float inputs:opacity.connect = </{surface}/decal.outputs:a>",
              f"        normal3f inputs:normal.connect = </{surface}/normal.outputs:rgb>",
              f"        float inputs:roughness = {roughness:g}", f"        float inputs:metallic = {metallic:g}"]
    shaders = [texture_shader(surface, "decal", "decal.png", "sRGB", [("float3", "rgb"), ("float", "a")], False),
               texture_shader(surface, "normal", "normal.png", "raw", [("float3", "rgb")], False)]
    return material_text(surface, inputs, "\n".join(shaders))


def material_text(surface, inputs, shaders):
    """The material.usda text around its preview surface's inputs and its shaders."""
    reader = (f'    def Shader "st"\n    {{\n        uniform token info:id = "UsdPrimvarReader_float2"\n'
              f'        string inputs:varname = "st"\n        float2 outputs:result\n    }}\n\n')
    return (f'#usda 1.0\n(\n    defaultPrim = "{surface}"\n)\n\ndef Material "{surface}"\n{{\n'
            f"    token outputs:surface.connect = </{surface}/surface.outputs:surface>\n\n"
            f'    def Shader "surface"\n    {{\n        uniform token info:id = "UsdPreviewSurface"\n'
            + "\n".join(inputs) + "\n        token outputs:surface\n    }\n\n" + reader + shaders + "}\n")


def saved(path, values, mode):
    """An 8-bit PNG of 0..1 values."""
    from PIL import Image
    Image.fromarray(np.round(np.clip(values, 0.0, 1.0) * 255).astype(np.uint8), mode).save(path, optimize=True)


def fabric_written(own, surface, fabric):
    """A fabric's maps, material and record in `own`; its file names."""
    colour, height, roughness = fabric["maps"](fabric["spec"])
    occlusion = 0.55 + 0.45 * height / max(height.max(), 1e-9)
    saved(own / "colour.png", encoded(colour), "RGB")
    saved(own / "normal.png", normal_map(height, TILE_M * 1000.0 / TILE_PX), "RGB")
    saved(own / "orm.png", np.stack([occlusion, roughness, np.zeros_like(roughness)], axis=-1), "RGB")
    (own / "material.usda").write_text(fabric_usda(surface))
    record = {"family": "fabric", "tile_m": TILE_M, "why": fabric["why"],
              "made_by": "score tools/characters/garments/fabrics.py",
              "maps": {"colour": "colour.png", "normal": "normal.png", "orm": "orm.png"}}
    (own / "surface.json").write_text(json.dumps(record, indent=2) + "\n")
    return ["colour.png", "normal.png", "orm.png", "material.usda", "surface.json"]


def mark_written(own, surface, entry):
    """A decal's maps, material and record in `own`; its file names and its size (m, u x v)."""
    title, drawn, roughness, metallic, form = entry
    mark = drawn()
    rgba, normal = mark.maps()
    saved(own / "decal.png", rgba, "RGBA")
    saved(own / "normal.png", normal, "RGB")
    (own / "material.usda").write_text(mark_usda(surface, roughness, metallic))
    size = (mark.shape[1] / mark.px_per_mm / 1000.0, mark.shape[0] / mark.px_per_mm / 1000.0)
    record = {"family": "decal", "form": form, "size_m": [round(size[0], 4), round(size[1], 4)], "why": title,
              "made_by": "score tools/characters/garments/fabrics.py"}
    (own / "surface.json").write_text(json.dumps(record, indent=2) + "\n")
    return ["decal.png", "normal.png", "material.usda", "surface.json"], size


def written(folder, commit):
    """Every fabric's and mark's files and the take-in listing under `folder`; the listing's path."""
    folder = pathlib.Path(folder)
    entries = []
    made_with = [{"what": "drawn by score from the fabric's or the seam's construction (#225)", "source": "score"}]
    for surface, fabric in FABRICS.items():
        own = folder / surface
        own.mkdir(parents=True, exist_ok=True)
        names = fabric_written(own, surface, fabric)
        entries.append({"kind": "surface", "id": surface, "title": fabric["title"], "made_with": made_with,
                        "files": {name: {"path": str(own / name), "from": f"score fabrics.py ({surface})"}
                                  for name in names},
                        "tags": {"family": ["fabric"], "use": ["garment"]}})
    for surface, entry in MARKS.items():
        own = folder / surface
        own.mkdir(parents=True, exist_ok=True)
        names, size = mark_written(own, surface, entry)
        entries.append({"kind": "surface", "id": surface, "title": entry[0], "made_with": made_with,
                        "files": {name: {"path": str(own / name), "from": f"score fabrics.py ({surface})"}
                                  for name in names},
                        "tags": {"family": ["decal"], "use": ["garment"], "class": ["fabric"],
                                 "size_m": [f"{size[0]:.3f}x{size[1]:.3f}"]}})
    listing = folder / "take-in.json"
    listing.write_text(json.dumps({"world": "world1", "commit": commit,
                                   "taken_from": "the fabrics and construction marks drawn by score's garment tools "
                                                 "(#225, PRD #223)", "entries": entries}, indent=1) + "\n")
    return listing


if __name__ == "__main__":
    print(written(sys.argv[1], sys.argv[2]))
