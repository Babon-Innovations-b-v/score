"""The ground's material detail as the game's own ground shader draws it, baked into the near ground's maps.

2099 draws its Moon's ground with one shader (game/art/shaders/ink_ground.gdshader with ground.gdshaderinc and
ground_ink.gdshaderinc, the material game/art/materials/regolith_ground.tres): the moon rock colour, lightened and
darkened by two scans of real ground and the plan's skin, tipped by the scans' grains, by small pits too small for the
mesh and by the plan's relief picture, and inked over with a stipple, outlined pebbles and broken strokes round the
pits' rims. None of it is geometry. Here the same arithmetic runs once over the near ground's patch, a texel `texel`
metres wide, and gives two maps the stage's ground is drawn with: its colour (sRGB) and its facing (a tangent-space
normal map: u along the place's +x, v along its -z). A decal the game paints on the ground (the wreck's scorch: a
darker regolith mixed over the colour) is mixed in the same way.

Everything is laid as the shader lays it: on the Moon's own axes, three ways (across x, y and z), each texel taking
mostly the way that faces it; the hash that scatters pits, pebbles and dots is the shader's, in single precision (a
GPU's fused multiply-adds can round a few cells' draws apart, so a pit here and there may differ from a given frame of
the game's). What depends on the eye in the game (a line's width in pixels, the ink and pits fading out with distance)
is taken at the texel's size and at the distance from the place's middle.

    bake(ground, detail, decals, world, low, high, out) -> {"colour": path, "facing": path, "low", "high"}
"""
import math
import pathlib
import sys

import numpy as np
from PIL import Image

import builders

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
import world as world_assets  # noqa: E402

# ground.gdshaderinc
LAYING_SHARPNESS = 8.0
PITS_FADE = (35.0, 70.0)
PIT_CELLS = (4.0, 1.6, 0.6)
PIT_CHANCES = (0.14, 0.22, 0.3)
PIT_CROWDS_WIDE = 23.0
RIM_REACH = 0.5
# ground_ink.gdshaderinc
INK_FADE = (30.0, 60.0)
DOT_CELL, DOT_CHANCE, DOT_SIZES = 0.1, 0.22, (0.007, 0.018)
PEBBLE_CELL, PEBBLE_CHANCE, PEBBLE_SIZES = 0.35, 0.2, (0.025, 0.1)
PEBBLE_LIGHT, PEBBLE_HEIGHT = 0.18, 0.7
LINE_PIXELS, LINE_SHARE = 1.5, 0.1
RIM_PIECES, RIM_DRAWN, RIM_LEAST_PIXELS = 9.0, 0.7, 8.0
# ink_ground.gdshader
PLAN_SKIN_MIDDLE, PLAN_SKIN_SHADE, PLAN_TILT_SCALE = 0.42, 1.6, 1.5
PLAN_SLOW_LEFT, PLAN_PITS_LEFT = 0.4, 0.3
WIDE_ACROSS, CLOSE_ACROSS, SLOW_ACROSS, SLOW_TURN = 3.1, 0.4, 13.7, 0.61
WIDE_SHADE, CLOSE_SHADE, SLOW_SHADE = 0.35, 0.25, 0.3
WIDE_BUMPS, CLOSE_BUMPS = 0.75, 0.5
SCAN_STIPPLE = 0.5
# How many texel rows are worked out at once (bounds the memory a bake takes).
ROWS_AT_ONCE = 96
# A way of laying whose share is under this everywhere on the patch adds nothing that shows and is left out.
LEAST_SHARE = 0.004

F32 = np.float32


def srgb_to_linear(values):
    values = np.asarray(values, dtype=np.float64)
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(values):
    values = np.clip(values, 0.0, 1.0)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * values ** (1 / 2.4) - 0.055)


def fract(values):
    return values - np.floor(values)


def scatter(cell_x, cell_y):
    """The shader's hash of a cell (ground.gdshaderinc `scatter`), in single precision."""
    cell_x = fract(F32(cell_x) * F32(123.34))
    cell_y = fract(F32(cell_y) * F32(456.21))
    spread = cell_x * (cell_x + F32(45.32)) + cell_y * (cell_y + F32(45.32))
    return fract((cell_x + spread) * (cell_y + spread))


def scatter_two(cell_x, cell_y):
    first = scatter(cell_x, cell_y)
    return first, scatter(cell_x + first * F32(91.7), cell_y + first * F32(91.7))


def smooth_patch(at_x, at_y):
    """A smooth wandering value between 0 and 1, one hill or hollow per unit (`smooth_patch`)."""
    cell_x, cell_y = np.floor(at_x), np.floor(at_y)
    part_x, part_y = at_x - cell_x, at_y - cell_y
    part_x = part_x * part_x * (F32(3.0) - F32(2.0) * part_x)
    part_y = part_y * part_y * (F32(3.0) - F32(2.0) * part_y)
    top = scatter(cell_x, cell_y) * (1 - part_x) + scatter(cell_x + 1, cell_y) * part_x
    bottom = scatter(cell_x, cell_y + 1) * (1 - part_x) + scatter(cell_x + 1, cell_y + 1) * part_x
    return top * (1 - part_y) + bottom * part_y


def smoothstep(low, high, values):
    part = np.clip((values - low) / (high - low), 0.0, 1.0)
    return part * part * (3.0 - 2.0 * part)


def covered(away, radius, pixel):
    """How much of a round mark of a radius covers a spot this far from its middle, soft by a pixel (`covered`)."""
    return 1.0 - smoothstep(radius - pixel * 0.5, radius + pixel * 0.5, away)


def pit_in(here_x, here_y, cell, chance):
    """The pit a cell holds (`pit_in`): its middle, radius (nothing when the cell holds none) and freshness."""
    first, second = scatter_two(here_x + F32(17.0), here_y + F32(17.0))
    middle_x, middle_y = (here_x + first) * F32(cell), (here_y + second) * F32(cell)
    crowd = smooth_patch(middle_x / F32(PIT_CROWDS_WIDE), middle_y / F32(PIT_CROWDS_WIDE))
    crowding = 0.05 + (2.6 - 0.05) * smoothstep(0.45, 0.8, crowd)
    held = scatter(here_x + F32(3.1), here_y + F32(3.1)) <= chance * crowding
    radius = cell * (0.12 + (0.42 - 0.12) * scatter(here_x + F32(31.0), here_y + F32(31.0)) ** 2)
    fresh = scatter(here_x + F32(57.0), here_y + F32(57.0)) ** 3
    return middle_x, middle_y, np.where(held, radius, 0.0), fresh


def pits_on(at_x, at_y, pixel):
    """Every size of pit at a spot on one way of laying: the rise per metre they tip it by (`all_pits_tilt`) and the
    ink of their broken rim strokes (`pits_ink_on`)."""
    tilt_x, tilt_y, ink = np.zeros_like(at_x), np.zeros_like(at_x), np.zeros_like(at_x)
    for cell, chance in zip(PIT_CELLS, PIT_CHANCES):
        home_x, home_y = np.floor(at_x / F32(cell)), np.floor(at_y / F32(cell))
        for across in (-1, 0, 1):
            for along in (-1, 0, 1):
                here_x, here_y = home_x + across, home_y + along
                middle_x, middle_y, radius, fresh = pit_in(here_x, here_y, cell, chance)
                gap_x, gap_y = at_x - middle_x, at_y - middle_y
                away = np.hypot(gap_x, gap_y)
                inside = (away < radius * (1.0 + RIM_REACH)) & (away >= 0.0001) & (radius > 0.0)
                safe_radius = np.where(radius > 0.0, radius, 1.0)
                part = away / safe_radius
                depth = (0.12 + (0.45 - 0.12) * fresh) * safe_radius
                rim = (0.03 + (0.1 - 0.03) * fresh) * safe_radius
                outside = (1.0 + RIM_REACH - part) / RIM_REACH
                rise = np.where(part < 1.0, depth * 2.0 * part + rim * 4.0 * part ** 3, -2.0 * rim * outside / RIM_REACH)
                along_gap = np.where(inside, rise / safe_radius / np.maximum(away, 0.0001), 0.0)
                tilt_x += along_gap * gap_x
                tilt_y += along_gap * gap_y
                piece = np.floor((np.arctan2(gap_y, gap_x) / (2.0 * math.pi) + 0.5) * RIM_PIECES)
                drawn = scatter(here_x + piece * F32(1.37) + F32(71.0), here_y + piece * F32(1.37) + F32(71.0)) <= RIM_DRAWN
                stroked = (radius >= pixel * RIM_LEAST_PIXELS) & drawn
                ink = np.maximum(ink, np.where(stroked, covered(np.abs(away - radius), pixel * LINE_PIXELS * 0.5, pixel),
                                               0.0))
    return tilt_x, tilt_y, ink


def pebbles_on(at_x, at_y, pixel):
    """The pebbles at a spot (`pebbles_on`): their outlines' ink, how much lighter their tops are and their domes'
    rise per metre."""
    ink, light = np.zeros_like(at_x), np.zeros_like(at_x)
    tilt_x, tilt_y = np.zeros_like(at_x), np.zeros_like(at_x)
    home_x, home_y = np.floor(at_x / F32(PEBBLE_CELL)), np.floor(at_y / F32(PEBBLE_CELL))
    for across in (-1, 0, 1):
        for along in (-1, 0, 1):
            here_x, here_y = home_x + across, home_y + along
            held = scatter(here_x + F32(41.0), here_y + F32(41.0)) <= PEBBLE_CHANCE
            first, second = scatter_two(here_x + F32(43.0), here_y + F32(43.0))
            middle_x, middle_y = (here_x + first) * F32(PEBBLE_CELL), (here_y + second) * F32(PEBBLE_CELL)
            radius = PEBBLE_SIZES[0] + (PEBBLE_SIZES[1] - PEBBLE_SIZES[0]) * scatter(here_x + F32(47.0),
                                                                                       here_y + F32(47.0)) ** 3
            gap_x, gap_y = at_x - middle_x, at_y - middle_y
            away = np.hypot(gap_x, gap_y)
            near = held & (away <= radius + pixel * 2.0)
            line = np.maximum(pixel * LINE_PIXELS, radius * LINE_SHARE)
            ink = np.maximum(ink, np.where(near, covered(np.abs(away - radius), line * 0.5, pixel), 0.0))
            light = np.maximum(light, np.where(near, covered(away, radius, pixel), 0.0))
            on_top = near & (away < radius) & (away > 0.0001)
            part = np.minimum(away / radius, 0.999)
            rise = PEBBLE_HEIGHT * part / np.sqrt(np.maximum(1.0 - part * part, 0.05))
            along_gap = np.where(on_top, rise / np.maximum(away, 0.0001), 0.0)
            tilt_x += along_gap * gap_x
            tilt_y += along_gap * gap_y
    return ink, light, tilt_x, tilt_y


def stipple_on(at_x, at_y, pixel):
    """The fine dots' ink at a spot (`stipple_on`)."""
    ink = np.zeros_like(at_x)
    home_x, home_y = np.floor(at_x / F32(DOT_CELL)), np.floor(at_y / F32(DOT_CELL))
    for across in (-1, 0, 1):
        for along in (-1, 0, 1):
            here_x, here_y = home_x + across, home_y + along
            held = scatter(here_x + F32(5.7), here_y + F32(5.7)) <= DOT_CHANCE
            first, second = scatter_two(here_x + F32(11.0), here_y + F32(11.0))
            middle_x, middle_y = (here_x + first) * F32(DOT_CELL), (here_y + second) * F32(DOT_CELL)
            radius = DOT_SIZES[0] + (DOT_SIZES[1] - DOT_SIZES[0]) * scatter(here_x + F32(23.0), here_y + F32(23.0)) ** 2
            seen = np.clip(radius / pixel, 0.0, 1.0)
            away = np.hypot(at_x - middle_x, at_y - middle_y)
            ink = np.maximum(ink, np.where(held, covered(away, np.maximum(radius, pixel * 0.5), pixel) * seen, 0.0))
    return ink


class Picture:
    """A picture the shader reads, at about the bake's texel: averaged down (a mipmap's level) to `across` metres in
    `texel`s, read between its four nearest points and repeated (or held at its edge)."""

    def __init__(self, path, across=None, texel=None, mode="L"):
        picture = Image.open(path).convert(mode)
        if across is not None and texel is not None:
            side = int(max(2, min(picture.size[0], round(across / texel))))
            if side < picture.size[0]:
                picture = picture.resize((side, side), Image.BOX)
        self.values = np.asarray(picture, dtype=np.float64) / 255.0
        if self.values.ndim == 2:
            self.values = self.values[..., None]

    def read(self, u, v, repeat=True):
        """The picture at (u, v), its first row at v = 0 (as the engine reads a picture), read bilinearly."""
        tall, wide = self.values.shape[:2]
        x, y = u * wide - 0.5, v * tall - 0.5
        column, row = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        part_x, part_y = (x - column)[..., None], (y - row)[..., None]

        def at(columns, rows):
            if repeat:
                return self.values[rows % tall, columns % wide]
            return self.values[np.clip(rows, 0, tall - 1), np.clip(columns, 0, wide - 1)]
        top = at(column, row) * (1 - part_x) + at(column + 1, row) * part_x
        bottom = at(column, row + 1) * (1 - part_x) + at(column + 1, row + 1) * part_x
        return top * (1 - part_y) + bottom * part_y


class Scans:
    """The two scans of real ground the shader lays (wide and close, shade and bumps), at the bake's texel."""

    def __init__(self, detail, world, texel):
        found = {name: world_assets.resolve(path, world) for name, path in detail["scans"].items()}
        self.wide_shade = Picture(found["wide_shade"], WIDE_ACROSS, texel)
        self.slow_shade = Picture(found["wide_shade"], SLOW_ACROSS, texel)
        self.close_shade = Picture(found["close_shade"], CLOSE_ACROSS, texel)
        self.wide_bumps = Picture(found["wide_bumps"], WIDE_ACROSS, texel, "RGB")
        self.close_bumps = Picture(found["close_bumps"], CLOSE_ACROSS, texel, "RGB")

    def shade(self, at_x, at_y):
        """How much the scans lighten and darken the rock colour at a spot (`shade_on`)."""
        turned_x = math.cos(SLOW_TURN) * at_x - math.sin(SLOW_TURN) * at_y
        turned_y = math.sin(SLOW_TURN) * at_x + math.cos(SLOW_TURN) * at_y
        return ((self.wide_shade.read(at_x / WIDE_ACROSS, at_y / WIDE_ACROSS)[..., 0] - 0.5) * WIDE_SHADE
                + (self.close_shade.read(at_x / CLOSE_ACROSS, at_y / CLOSE_ACROSS)[..., 0] - 0.5) * CLOSE_SHADE
                + (self.slow_shade.read(turned_x / SLOW_ACROSS, turned_y / SLOW_ACROSS)[..., 0] - 0.5) * SLOW_SHADE)

    def tilt(self, at_x, at_y):
        """The rise per metre the scans' grains tip the ground by at a spot (`bumps_tilt`, both scans)."""
        found = []
        for picture, across, strength in ((self.wide_bumps, WIDE_ACROSS, WIDE_BUMPS),
                                          (self.close_bumps, CLOSE_ACROSS, CLOSE_BUMPS)):
            facing = picture.read(at_x / across, at_y / across) * 2.0 - 1.0
            found.append(-facing[..., :2] / np.maximum(facing[..., 2:3], 0.2) * strength)
        total = found[0] + found[1]
        return total[..., 0], total[..., 1]


def laid(points, way):
    """A point's spot on one of the three ways of laying (`laid_x`, `laid_y`, `laid_z`)."""
    return {0: (points[..., 2], points[..., 1]), 1: (points[..., 0], points[..., 2]),
            2: (points[..., 0], points[..., 1])}[way]


def from_way(way, tilt_x, tilt_y, facing):
    """One way's tipped facing on the Moon's axes (`laid_facing`'s from_x, from_y, from_z)."""
    if way == 0:
        return np.stack([facing[..., 0], -tilt_y + facing[..., 1], -tilt_x + facing[..., 2]], axis=-1)
    if way == 1:
        return np.stack([-tilt_x + facing[..., 0], facing[..., 1], -tilt_y + facing[..., 2]], axis=-1)
    return np.stack([-tilt_x + facing[..., 0], -tilt_y + facing[..., 1], facing[..., 2]], axis=-1)


def normalised(vectors):
    return vectors / np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12)


def scorch(decal, points):
    """How much of a burn decal (wreck.gd `_burn_mark`: solid to `solid` of its reach, fading out in `rays` rays drawn
    from `seed`) lies at place points (x, z), from nothing to one."""
    draws = builders.pcg32_floats(int(decal["seed"]), int(decal["rays"]))
    reach = np.array([1.0 - float(decal["ray_reach"]) * float(draw) for draw in draws])
    away_x = (points[..., 0] - decal["centre"][0]) / float(decal["radius"])
    away_y = (points[..., 2] - decal["centre"][2]) / float(decal["radius"])
    out = np.hypot(away_x, away_y)
    turn = np.mod(np.arctan2(away_y, away_x), 2.0 * math.pi) / (2.0 * math.pi) * len(reach)
    first = turn.astype(np.int64) % len(reach)
    between = smoothstep(0.0, 1.0, turn - np.floor(turn))
    edge = reach[first] * (1.0 - between) + reach[(first + 1) % len(reach)] * between
    solid = float(decal["solid"])
    fading = np.clip(1.0 - (out - solid) / np.maximum(edge - solid, 0.01), 0.0, 1.0)
    inside_box = (np.abs(away_x) <= 1.0) & (np.abs(away_y) <= 1.0)
    return np.where(out <= solid, 1.0, fading) * inside_box


class Bake:
    """One bake of a place's near ground: its ground, its detail record (the world's flat colours, pictures and
    shares), the decals painted on it and the world's folder holding the pictures."""

    def __init__(self, ground, detail, decals, world, texel):
        self.ground, self.detail, self.decals, self.texel = ground, detail, decals, texel
        self.flat = srgb_to_linear(detail["flat_colour"])
        self.ink_colour = srgb_to_linear(detail["ink_colour"])
        self.pits_share = float(detail.get("pits_share", 1.0))
        self.pebbles_share = float(detail.get("pebbles_share", 1.0))
        self.scans = Scans(detail, world, texel)
        self.skin = Picture(ground.skin)
        self.relief = Picture(world_assets.resolve(detail["relief"], world), mode="RGB")

    def rows(self, xs, zs):
        """The colour (linear) and the tipped facing (place frame) of a block of texels at xs across and zs along."""
        grid_x, grid_z = np.meshgrid(xs, zs)
        step = self.texel
        corners = []
        for offset_x, offset_z in ((0.0, 0.0), (step, 0.0), (0.0, step)):
            flat = (self.ground.frame[1] * self.ground.radius + (grid_x + offset_x)[..., None] * self.ground.frame[0]
                    + (grid_z + offset_z)[..., None] * self.ground.frame[2])
            directions = flat / np.linalg.norm(flat, axis=-1, keepdims=True)
            height, plan_flat = self.ground.plan_height(directions.reshape(-1, 3))
            corners.append((directions * (self.ground.radius + height.reshape(grid_x.shape))[..., None],
                            plan_flat.reshape(grid_x.shape + (2,))))
        moon, plan_flat = corners[0]
        facing = normalised(np.cross(corners[2][0] - moon, corners[1][0] - moon))
        facing = np.where((np.sum(facing * moon, axis=-1) > 0.0)[..., None], facing, -facing)
        place = self.ground.in_place_frame(moon.reshape(-1, 3)).reshape(moon.shape)
        distance = np.hypot(place[..., 0], place[..., 2])
        return self.shaded(moon, facing, place, plan_flat, distance)

    def shaded(self, moon, facing, place, plan_flat, distance):
        """The shader's fragment for texels at Moon points with their mesh facing: colour and tipped facing."""
        shares = np.abs(facing) ** LAYING_SHARPNESS
        shares /= shares.sum(axis=-1, keepdims=True)
        pits = (1.0 - smoothstep(*PITS_FADE, distance)) * PLAN_PITS_LEFT * self.pits_share
        ink_left = 1.0 - smoothstep(*INK_FADE, distance)
        pixel = self.texel
        shade = np.zeros(distance.shape)
        ink = np.zeros(distance.shape)
        light = np.zeros(distance.shape)
        tipped = np.zeros(facing.shape)
        moon32 = moon.astype(np.float32)
        for way in range(3):
            share = shares[..., way]
            if share.max() < LEAST_SHARE:
                continue
            at_x, at_y = laid(moon32, way)
            pebble_ink, pebble_light, pebble_x, pebble_y = pebbles_on(at_x, at_y, pixel)
            pebble_ink, pebble_light = pebble_ink * self.pebbles_share, pebble_light * self.pebbles_share
            pebble_x, pebble_y = pebble_x * self.pebbles_share, pebble_y * self.pebbles_share
            pit_x, pit_y, pit_ink = pits_on(at_x, at_y, pixel)
            way_ink = np.maximum(np.maximum(stipple_on(at_x, at_y, pixel) * SCAN_STIPPLE, pebble_ink), pit_ink * pits)
            scan_x, scan_y = self.scans.tilt(at_x.astype(np.float64), at_y.astype(np.float64))
            tilt_x = scan_x + pit_x * pits + pebble_x * ink_left
            tilt_y = scan_y + pit_y * pits + pebble_y * ink_left
            tipped += from_way(way, tilt_x, tilt_y, facing) * share[..., None]
            shade += self.scans.shade(at_x.astype(np.float64), at_y.astype(np.float64)) * share
            ink += way_ink * ink_left * share
            light += pebble_light * ink_left * share
        tipped = normalised(tipped)
        skin = self.skin.read(plan_flat[..., 0] / self.ground.side + 0.5, plan_flat[..., 1] / self.ground.side + 0.5,
                              repeat=False)[..., 0]
        shade = shade * PLAN_SLOW_LEFT + (skin - PLAN_SKIN_MIDDLE) * PLAN_SKIN_SHADE
        relief = self.relief.read(plan_flat[..., 0] / self.ground.side + 0.5, plan_flat[..., 1] / self.ground.side + 0.5,
                                  repeat=False)
        rise = (relief[..., :2] - 0.5) * 2.0 * PLAN_TILT_SCALE
        plan_across, plan_along = self.ground.plan[0], self.ground.plan[2]
        across_here = normalised(plan_across - facing * (facing @ plan_across)[..., None])
        along_here = normalised(plan_along - facing * (facing @ plan_along)[..., None])
        tipped = normalised(tipped - rise[..., :1] * across_here - rise[..., 1:2] * along_here)
        colour = self.flat * np.clip(1.0 + shade, 0.0, 2.0)[..., None] * (1.0 + light * PEBBLE_LIGHT)[..., None]
        colour = colour * (1.0 - ink[..., None]) + self.ink_colour * ink[..., None]
        for decal in self.decals:
            share = scorch(decal, place)[..., None]
            colour = colour * (1.0 - share) + srgb_to_linear(decal["colour"]) * share
        return colour, tipped @ self.ground.frame.T, facing @ self.ground.frame.T


def tangent_encoded(tipped, facing):
    """A tipped facing as a tangent-space normal map's colour: tangent along the place's +x, bitangent along its -z
    (the map's v runs toward -z), normal the mesh's own facing."""
    tangent = normalised(np.array([1.0, 0.0, 0.0]) - facing * facing[..., :1])
    bitangent = np.cross(facing, tangent)
    local = np.stack([np.sum(tipped * tangent, axis=-1), np.sum(tipped * bitangent, axis=-1),
                      np.sum(tipped * facing, axis=-1)], axis=-1)
    return np.clip(np.round((local * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)


def bake(ground, detail, decals, world, low, high, out, texel=None):
    """Bake the near ground's colour and facing maps over the box low..high (place x, z) into `out`; the two files and
    the box they cover. Rows of texels run along +z from low; the pictures' first row is the box's -z edge."""
    texel = float(texel or detail.get("texel", 0.02))
    wide = int(math.ceil((high[0] - low[0]) / texel))
    tall = int(math.ceil((high[1] - low[1]) / texel))
    baked = Bake(ground, detail, decals, world, texel)
    colour = np.zeros((tall, wide, 3), dtype=np.uint8)
    facing = np.zeros((tall, wide, 3), dtype=np.uint8)
    xs = low[0] + (np.arange(wide) + 0.5) * texel
    for start in range(0, tall, ROWS_AT_ONCE):
        zs = low[1] + (np.arange(start, min(tall, start + ROWS_AT_ONCE)) + 0.5) * texel
        linear, tipped, mesh_facing = baked.rows(xs, zs)
        colour[start:start + len(zs)] = np.round(linear_to_srgb(linear) * 255.0).astype(np.uint8)
        facing[start:start + len(zs)] = tangent_encoded(tipped, mesh_facing)
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    colour_file, facing_file = out / "ground_colour.jpg", out / "ground_facing.png"
    Image.fromarray(colour).save(colour_file, quality=92)
    Image.fromarray(facing).save(facing_file)
    return {"colour": colour_file, "facing": facing_file, "low": [float(low[0]), float(low[1])],
            "high": [float(low[0] + wide * texel), float(low[1] + tall * texel)]}


def far_colour(detail, skin):
    """The far ground's colour from the plan's skin as the shader shades it where the scans' grain averages out: the
    rock colour lightened and darkened by the skin's red about its middle (`plan_skin` is read as plain data)."""
    values = np.asarray(skin.convert("RGB"), dtype=np.float64)[..., 0] / 255.0
    shade = (values - PLAN_SKIN_MIDDLE) * PLAN_SKIN_SHADE
    linear = srgb_to_linear(detail["flat_colour"]) * np.clip(1.0 + shade, 0.0, 2.0)[..., None]
    return Image.fromarray(np.round(linear_to_srgb(linear) * 255.0).astype(np.uint8))
