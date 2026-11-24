"""The theme's material library as ProcFunc recipes (job robust-exp, 2026-10-06; the owner: every recipe is written in
ProcFunc, composable, its settings exposed and its seed explicit).

Runs inside Blender (`inside/runtime.py` puts vendor/procfunc and vendor/infinigen2 on the path first). A library
material is a composition of small functions, each one thing:

    relief      infinigen2's own base materials (paint, metal_brushed, plastic_black_rubberized), of which only the
                relief (their displacement) is kept: the ink look draws flat colour by region, so a base material's
                own colour noise is left out on purpose
    edge wear   a mask from the true geometry: infinigen2's edgewear test (the bevelled normal against the true
                normal) with a low-frequency breakup and a narrow band, so wear sits on real edges and corners as
                crisp chips, never as grit on flat faces; `wear` widens the band and lowers the threshold
    dirt        a mask from cavities (ambient occlusion within the piece's own reach, less what lies pressed on the
                surface) with its own breakup
    layered     paint over bare metal through the wear mask, dirt over both through the dirt mask

A recipe (`painted_metal`, `bare_metal`, `rubber`, `glass`, `glowing`) takes every setting as an argument and has no
Python branch on one, so ProcFunc's tracer can trace it with its settings as inputs (`settings_of`), which is how the
tuning loop learns what it may turn. It returns `Channels`: base colour, roughness, metal, emission and displacement
as ProcFunc nodes, so the same recipe is rendered (`shaded`) and baked channel by channel (`emitted`). Colours come
only from the palette tokens the caller resolves (library.py); no recipe holds a colour of its own.
"""
import inspect
import math
from typing import NamedTuple

import procfunc as pf
from infinigen2.shaders.base_materials.fabric import fabric
from infinigen2.shaders.base_materials.metal_brushed import metal_brushed
from infinigen2.shaders.base_materials.paint import paint
from infinigen2.shaders.base_materials.plastic import plastic_black_rubberized

BLACK = (0.0, 0.0, 0.0)


class Channels(NamedTuple):
    base_color: object
    roughness: object
    metallic: object
    emission: object
    displacement: object
    alpha: object = 1.0  # how much of the surface is there: under 1 a glass lets what lies behind it through (#186)


def coordinates():
    """The surface's own object coordinates, so a pattern stays on a piece however it is laid."""
    return pf.nodes.shader.coord().object


def edge_wear_mask(vector, wear, edge_width, breakup_scale, seed):
    """Where paint is worn off: real edges and corners only. infinigen2's edgewear measures an edge as the bevelled
    normal leaving the true normal within a radius; that measure, lifted by a low-frequency breakup, passes a narrow
    threshold band, so chips are crisp and sit on edges. `wear` 0 gives none; toward 1 the radius grows from
    `edge_width` and the threshold drops, so 0.4 chips corners and edges in places and 0.8 wears whole edges."""
    radius = edge_width * (0.5 + 4.0 * wear * wear)
    bevelled = pf.nodes.shader.bevel(radius=radius, samples=16)
    edge = pf.nodes.math.vector_length(bevelled - pf.nodes.shader.geometry().normal)
    breakup = pf.nodes.texture.noise(vector=vector, scale=breakup_scale, detail=1.0, noise_dimensions="4D", w=seed)
    # The breakup only scales the edge measure, so a flat face (edge 0) never wears, whatever the noise does: the
    # first cloud swatches (2026-10-06) showed chips in the middle of faces at wear 0.8 when the noise was added.
    field = edge * 1.6 * (1.0 + (breakup.fac - 0.5) * 1.6)
    threshold = 1.05 - 0.9 * wear
    band = pf.nodes.math.map_range(value=field, from_min=threshold, from_max=threshold + 0.06,
                                   interpolation_type="SMOOTHSTEP")
    return band * pf.nodes.math.greater_than(wear, 0.001)


# Wear from a cause (hub round five, method B): boots and carts scuff paint off a piece's foot up to KICK_HIGH metres
# over the floor it stands on, in patches, as hard as the room's one wear setting; dirt gathers there too. A piece
# tells how high its foot stands (`foot`): a porthole's or a tool board's is far above any kick. A place says whether
# anyone walks it (`kicks`: 1 where people walk, 0 where nobody does, the wreck's crash site, 2026-10-13).
KICK_HIGH = 0.32
KICK_SOFT = 0.08


def kick_mask(vector, foot, wear, kicks, breakup_scale, seed):
    """Where kicks have worn paint: within KICK_HIGH of the floor (the object's own up plus its foot's height), in
    patches from a breakup noise, scaled by the room's wear and by `kicks`; nothing on a piece whose foot stands high
    or in a place nobody walks."""
    point = pf.nodes.math.separate_xyz(vector)
    band = pf.nodes.math.map_range(value=point.z + foot, from_min=KICK_HIGH, from_max=KICK_SOFT,
                                   interpolation_type="SMOOTHSTEP")
    scuffs = pf.nodes.texture.noise(vector=vector, scale=breakup_scale * 1.5, detail=4.0, noise_dimensions="4D",
                                    w=seed + 31.0)
    patchy = pf.nodes.math.map_range(value=scuffs.fac, from_min=0.46, from_max=0.6)
    return pf.nodes.math.clamp(band * patchy * wear * kicks * 1.6)


# What occludes a surface within this share of the dirt's reach is a layer pressed on it, not a cavity: a garment over
# a garment, the inner shell Pixal3D grows under a model's skin. On the astronaut (2026-10-23) every seen face with a
# layer within 1.5 mm (median) along its normal read as a cavity (occlusion 0.94 against 0.13), so the moon dust lay
# in hard-edged patches where the layers cross, not in the creases.
PRESSED_SHARE = 0.2


def dirt_mask(vector, dirt, reach, seed):
    """Where dirt gathers: cavities and inside corners within `reach` metres, less what lies pressed on the surface
    (PRESSED_SHARE), broken up at a large scale."""
    within_reach = pf.nodes.shader.ambient_occlusion(distance=reach, only_local=True, samples=16)
    pressed = pf.nodes.shader.ambient_occlusion(distance=reach * PRESSED_SHARE, only_local=True, samples=16)
    cavity = pf.nodes.math.map_range(value=pressed.ao - within_reach.ao, from_min=0.1, from_max=0.45)
    breakup = pf.nodes.texture.noise(vector=vector, scale=1.5, detail=2.0, noise_dimensions="4D", w=seed + 17.0)
    patchy = pf.nodes.math.map_range(value=breakup.fac, from_min=0.3, from_max=0.6)
    return pf.nodes.math.clamp(cavity * patchy * dirt)


def paint_relief(vector, bump, bump_size):
    """A painted surface's orange peel, from infinigen2's paint with its splats, strokes and globules off."""
    return paint(vector=vector, bump_height=bump, bump_size=bump_size, splat_height=0.0, stroke_height=0.0,
                 globule_height=0.0).displacement


# infinigen2's metal_brushed draws its streaks' noise at 1000 a unit of its brush_size and displaces by
# brush_size * height_scale * 0.0001: the units brushed_relief turns its metres into.
BRUSH_NOISE_SCALE = 1000.0
BRUSH_HEIGHT_UNIT = 0.0001


def brushed_relief(vector, bump, bump_size):
    """Bare steel's brushing streaks, from infinigen2's metal_brushed: streaks `bump_size` metres across, `bump`
    metres high (passed as its own brush_size and height_scale, a fitted 5 cm, 0.3 mm relief was drawn 50 micrometres
    across and 1e-8 m high, flat at any render, #155)."""
    brush_size = bump_size * BRUSH_NOISE_SCALE
    return metal_brushed(vector=vector, brush_size=brush_size,
                         height_scale=bump / (brush_size * BRUSH_HEIGHT_UNIT)).displacement


def cloth_relief(vector, thread, bump):
    """Woven cloth's threads `thread` metres apart, `bump` high, from infinigen2's fabric (its weave at 500 threads a
    unit over `size`, its height 0.0002 a unit of size)."""
    size = thread * 500.0
    return fabric(vector=vector, size=size, size_variation=0.0, height_scale=bump / (size * 0.0002),
                  gab=0.1).displacement


def rubber_relief(vector, bump, bump_size):
    """Rubber's fine grain, from infinigen2's plastic_black_rubberized."""
    return plastic_black_rubberized(vector=vector, noise_size=bump_size, noise_height=bump).displacement


def mottled(colour, second, roughness, vector, mottle_size, contrast, roughness_spread, seed):
    """A flat finish's colour mottled toward `second` in soft patches `mottle_size` across (by `contrast`, as
    concrete's), and its roughness spread by `roughness_spread` in patches of its own (a scuffed plastic's, a
    stained paint's): the colour and roughness. Both 0 draw the flat finish (#155: plastic, rubber, cloth and paint
    had one colour and one roughness, so a smudged or speckled map could not be matched)."""
    mottle = pf.nodes.texture.noise(vector=vector, scale=1.0 / mottle_size, detail=4.0, noise_dimensions="4D",
                                    w=seed + 11.0)
    patches = pf.nodes.texture.noise(vector=vector, scale=1.0 / mottle_size, detail=4.0, noise_dimensions="4D",
                                     w=seed + 13.0)
    base = pf.nodes.color.mix_rgb(factor=pf.nodes.math.clamp((mottle.fac - 0.5) * 2.0 * contrast), a=colour,
                                  b=second)
    return base, pf.nodes.math.clamp(roughness + (patches.fac - 0.5) * 2.0 * roughness_spread)


# Scuffs (score #164): handling and contact scratches on flat faces, which edges never give. Thin scratches SCUFF_SCALE
# a metre across, stretched SCUFF_STRETCH times along one way, on faces turned up or out (SCUFF_UP: the object's up
# share of a face's normal from which it is fully scuffed), as far as the place's wear times the recipe's `scuffs`.
SCUFF_SCALE = 60.0
SCUFF_STRETCH = 25.0
SCUFF_UP = 0.6


def scuff_mask(vector, wear, scuffs, seed):
    """Where handling has scratched paint on flat faces: thin directional scratch noise, strongest on faces turned up,
    scaled by `wear` and `scuffs` (0, the default, draws none)."""
    point = pf.nodes.math.separate_xyz(vector)
    stretched = pf.nodes.math.combine_xyz(x=point.x * SCUFF_SCALE, y=point.y * (SCUFF_SCALE / SCUFF_STRETCH),
                                          z=point.z * SCUFF_SCALE)
    lines = pf.nodes.texture.noise(vector=stretched, scale=1.0, detail=2.0, noise_dimensions="4D", w=seed + 41.0)
    thin = pf.nodes.math.map_range(value=lines.fac, from_min=0.66, from_max=0.7, interpolation_type="SMOOTHSTEP")
    facing = pf.nodes.math.separate_xyz(pf.nodes.shader.coord().normal)
    upward = pf.nodes.math.map_range(value=facing.z, from_min=-0.2, from_max=SCUFF_UP)
    return pf.nodes.math.clamp(thin * upward * wear * scuffs)


# A decal (score #164): a library print laid on a part of a piece by a box projector in the piece's own frame. It is
# part of its part's finish's material, so it prints only on that finish's faces, and only within DECAL_FACING (60
# degrees) of its facing and within DECAL_DEPTH of its plane (a quarter of its short side when that is less, or the
# depth its ink was seen at off its plane when more: a placement's `depth`, score route_parts.ink_extent), so it never
# wraps round a corner or prints through a thin part.
DECAL_DEPTH = 0.02
DECAL_FACING = math.cos(math.radians(60.0))


def unit(vector):
    """A vector of three floats scaled to length 1."""
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector]


def decal_axes(decal):
    """(right, up, normal) unit axes of a decal placement: its `up` made square to its `normal`, both turned by its
    `turn` degrees about its normal."""
    normal = unit(decal["normal"])
    along = sum(mine * theirs for mine, theirs in zip(decal["up"], normal))
    up = unit([value - along * axis for value, axis in zip(decal["up"], normal)])
    right = [up[1] * normal[2] - up[2] * normal[1], up[2] * normal[0] - up[0] * normal[2],
             up[0] * normal[1] - up[1] * normal[0]]
    turn = math.radians(decal.get("turn", 0.0))
    turned_right = [math.cos(turn) * mine + math.sin(turn) * theirs for mine, theirs in zip(right, up)]
    turned_up = [math.cos(turn) * mine - math.sin(turn) * theirs for mine, theirs in zip(up, right)]
    return turned_right, turned_up, normal


def decal_depth(decal):
    """How far off its plane a decal placement prints (DECAL_DEPTH at most): a quarter of its short side, or the depth
    its ink was seen at (`depth`) when more."""
    return min(DECAL_DEPTH, max(0.25 * min(decal["size_m"]), decal.get("depth", 0.0)))


def decal_layer(vector, decal, image):
    """One decal as (mask, colour, roughness): its picture read through a box projector at its placement (`at`,
    `normal`, `up`, `size_m`, `turn`), masked to the faces facing it within its depth; a single-ink decal (`ink` a
    colour) drawn in that colour through its transparency."""
    right, up, normal = decal_axes(decal)
    point = pf.nodes.math.separate_xyz(vector)
    offset = [point.x - decal["at"][0], point.y - decal["at"][1], point.z - decal["at"][2]]

    def along(axis):
        return offset[0] * axis[0] + offset[1] * axis[1] + offset[2] * axis[2]

    width, height = decal["size_m"]
    across = pf.nodes.math.combine_xyz(x=along(right) * (1.0 / width) + 0.5, y=along(up) * (1.0 / height) + 0.5,
                                       z=0.0)
    picture = pf.nodes.texture.image(vector=across, image=image, extension="CLIP")
    facing = pf.nodes.math.separate_xyz(pf.nodes.shader.coord().normal)
    turned = facing.x * normal[0] + facing.y * normal[1] + facing.z * normal[2]
    depth = decal_depth(decal)
    near = pf.nodes.math.less_than(pf.nodes.math.absolute(along(normal)), depth)
    mask = picture.fac * near * pf.nodes.math.greater_than(turned, DECAL_FACING)
    colour = pf.Color(tuple(decal["ink"])) if decal.get("ink") else picture.color
    return mask, colour, float(decal.get("roughness", 0.45))


def with_decals(top, decals):
    """A (colour, roughness, metal) layer with each decal (mask, colour, roughness) printed over it in order: print
    is not metal."""
    colour, roughness, metal = top
    for mask, ink, ink_roughness in decals or ():
        colour = pf.nodes.color.mix_rgb(factor=mask, a=colour, b=ink)
        roughness = pf.nodes.math.mix(a=roughness, b=ink_roughness, factor=mask)
        metal = pf.nodes.math.mix(a=metal, b=0.0, factor=mask)
    return colour, roughness, metal


def layered(top, under, wear_mask, dirt_colour, dirt_amount, decals=None):
    """Paint `top` with its decals printed on it (with_decals, in layer order) over `under` through the wear mask,
    so wear chips the print with the paint, then dirt over all: (colour, roughness, metal) triples in, the same triple
    out."""
    top = with_decals(top, decals)
    colour = pf.nodes.color.mix_rgb(factor=wear_mask, a=top[0], b=under[0])
    roughness = pf.nodes.math.mix(a=top[1], b=under[1], factor=wear_mask)
    metal = pf.nodes.math.mix(a=top[2], b=under[2], factor=wear_mask)
    colour = pf.nodes.color.mix_rgb(factor=dirt_amount, a=colour, b=dirt_colour)
    roughness = pf.nodes.math.mix(a=roughness, b=0.9, factor=dirt_amount)
    return colour, roughness, metal


def painted_metal(colour, bare, dirt_colour, roughness, bare_roughness, metal, bump, bump_size, edge_width,
                  breakup_scale, dirt_reach, wear, dirt, seed, foot, kicks, second=None, mottle_size=0.15,
                  contrast=0.0, roughness_spread=0.0, scuffs=0.0, decals=None):
    """Paint on steel, mottled (mottled), its decals printed on the paint: worn through to bare steel on the edges,
    where feet kick it and where handling scuffs its flat faces, dirty in the cavities."""
    vector = coordinates()
    kicked = kick_mask(vector, foot, wear, kicks, breakup_scale, seed)
    wear_mask = pf.nodes.math.maximum(pf.nodes.math.maximum(
        edge_wear_mask(vector, wear, edge_width, breakup_scale, seed), kicked), scuff_mask(vector, wear, scuffs, seed))
    dirty = pf.nodes.math.maximum(dirt_mask(vector, dirt, dirt_reach, seed), kicked * dirt * 0.5)
    colour, roughness = mottled(colour, second, roughness, vector, mottle_size, contrast, roughness_spread, seed)
    base, rough, shine = layered((colour, roughness, metal), (bare, bare_roughness, 1.0), wear_mask, dirt_colour, dirty,
                                 decals)
    chipped = pf.nodes.shader.displacement(height=wear_mask * -0.0004, midlevel=0.0)
    return Channels(base, rough, shine, BLACK, paint_relief(vector, bump, bump_size) + chipped)


def bare_metal(colour, dirt_colour, roughness, metal, bump, bump_size, dirt_reach, dirt, seed):
    """Unpainted steel, brushed, dirty in the cavities; nothing to wear through."""
    vector = coordinates()
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=dirty, a=colour, b=dirt_colour)
    rough = pf.nodes.math.mix(a=roughness, b=0.9, factor=dirty)
    return Channels(base, rough, metal, BLACK, brushed_relief(vector, bump, bump_size))


def rubber(colour, dirt_colour, roughness, bump, bump_size, dirt_reach, dirt, seed, second=None, mottle_size=0.15,
           contrast=0.0, roughness_spread=0.0):
    """Black rubber with a fine grain, mottled (mottled), dusty in the cavities."""
    vector = coordinates()
    colour, roughness = mottled(colour, second, roughness, vector, mottle_size, contrast, roughness_spread, seed)
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=dirty, a=colour, b=dirt_colour)
    return Channels(base, roughness, 0.0, BLACK, rubber_relief(vector, bump, bump_size))


def cloth(colour, dirt_colour, roughness, thread, bump, dirt_reach, dirt, seed, second=None, mottle_size=0.15,
          contrast=0.0, roughness_spread=0.0, check=0.0, check_pitch=0.02, check_line=0.002, print_colour=None):
    """Plain woven cloth (overalls, jackets, straps, upholstery): its colour, mottled (mottled, a heather's), a printed
    check (lines `check_line` wide on a square grid `check_pitch` apart in `print_colour`, by `check`: 0 none), a fine
    weave, dirt in its creases."""
    vector = coordinates()
    colour, roughness = mottled(colour, second, roughness, vector, mottle_size, contrast, roughness_spread, seed)
    lines = face_joints(vector, check_pitch, check_pitch, check_line)
    colour = pf.nodes.color.mix_rgb(factor=lines * check, a=colour, b=print_colour)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    return Channels(base, rough, 0.0, BLACK, cloth_relief(vector, thread, bump))


def glass(colour, roughness, opacity=1.0):
    """Glass drawn as its own flat colour and a sharp shine, `opacity` of it there (its alpha): what lies behind shows
    through the rest (#186: drawn opaque, the tc4r fridge's glass door was a grey panel)."""
    return Channels(colour, roughness, 0.0, BLACK, None, opacity)


def glowing(colour, roughness, glow=1.0):
    """A token colour given off as light: screens, lamp lenses; `glow` times over (a fitted lamp's 3.7: its source's
    emissiveColor holds its strength in its size, #155)."""
    return Channels(colour, roughness, 0.0, pf.nodes.math.vector_scale(vector=colour, scale=glow), None)


def face_plane(vector):
    """Two coordinates across the surface, from the object's axes it lies most across: a floor reads x and y, a
    wall facing front x and z, a side y and z (the first swatches striped every floor with a wall's grid)."""
    point = pf.nodes.math.separate_xyz(vector)
    facing = pf.nodes.math.separate_xyz(pf.nodes.shader.geometry().normal)
    side, front, up = (pf.nodes.math.absolute(facing.x), pf.nodes.math.absolute(facing.y),
                       pf.nodes.math.absolute(facing.z))
    is_up = pf.nodes.math.greater_than(up, side) * pf.nodes.math.greater_than(up, front)
    is_side = pf.nodes.math.greater_than(side, front) * (1.0 - is_up)
    across = pf.nodes.math.mix(a=point.x, b=point.y, factor=is_side)
    upward = pf.nodes.math.mix(a=point.z, b=point.y, factor=is_up)
    return across, upward


def face_grid(vector, pitch):
    """A square grid on the surface's own plane (face_plane), each point's offset from its cell's middle in cells,
    from -0.5 to 0.5 on each axis."""
    across, upward = face_plane(vector)
    return pf.nodes.math.fraction(across / pitch) - 0.5, pf.nodes.math.fraction(upward / pitch) - 0.5


def dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed):
    """A surface's colour and roughness with dirt gathered in its cavities."""
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    return (pf.nodes.color.mix_rgb(factor=dirty, a=colour, b=dirt_colour),
            pf.nodes.math.mix(a=roughness, b=0.9, factor=dirty))


def cast_metal(colour, dirt_colour, roughness, metal, bump, bump_size, dirt_reach, dirt, seed):
    """Sand-cast steel or iron: a soft pitted relief, flat colour, dirt in the cavities."""
    vector = coordinates()
    pits = pf.nodes.texture.noise(vector=vector, scale=1.0 / bump_size, detail=3.0, noise_dimensions="4D", w=seed)
    relief = pf.nodes.shader.displacement(height=(pits.fac - 0.5) * bump, midlevel=0.0)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    return Channels(base, rough, metal, BLACK, relief)


def wood(colour, dirt_colour, roughness, bump, bump_size, dirt_reach, dirt, seed):
    """Plain timber: a flat colour with a soft relief stretched along the board, dirt in the cavities; its grain and
    wear come from the piece's own picture (bake.Atlas.lay_picture), not from noise."""
    vector = coordinates()
    point = pf.nodes.math.separate_xyz(vector)
    stretched = pf.nodes.math.combine_xyz(x=point.x, y=point.y * 0.08, z=point.z)
    fibres = pf.nodes.texture.noise(vector=stretched, scale=1.0 / bump_size, detail=2.0, noise_dimensions="4D", w=seed)
    relief = pf.nodes.shader.displacement(height=(fibres.fac - 0.5) * bump, midlevel=0.0)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    return Channels(base, rough, 0.0, BLACK, relief)


def perforated_metal(colour, second, dirt_colour, roughness, metal, pitch, hole_share, dirt_reach, dirt, seed):
    """Perforated sheet: a square grid of round holes (dark, sunk) through painted or bare sheet."""
    vector = coordinates()
    across, up = face_grid(vector, pitch)
    hole = pf.nodes.math.less_than(pf.nodes.math.sqrt(across * across + up * up), hole_share * 0.5)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=hole, a=base, b=second)
    return Channels(base, rough, metal, BLACK, pf.nodes.shader.displacement(height=hole * -0.002, midlevel=0.0))


def chequer_plate(colour, dirt_colour, roughness, metal, pitch, bump, dirt_reach, dirt, seed):
    """Tread plate: raised lugs on a grid, each lug long and thin on a diagonal, turned against its neighbours."""
    vector = coordinates()
    across, up = face_grid(vector, pitch)
    turned = pf.nodes.texture.checker(vector=vector, scale=1.0 / pitch).fac
    along = pf.nodes.math.mix(a=across + up, b=across - up, factor=turned)
    side = pf.nodes.math.mix(a=across - up, b=across + up, factor=turned)
    # A lug's sides slope (a smoothstep down to its edge), so a bump render shows its relief, not its outline alone.
    lug = pf.nodes.math.map_range(value=pf.nodes.math.absolute(along), from_min=0.4, from_max=0.3,
                                  interpolation_type="SMOOTHSTEP") * pf.nodes.math.map_range(
        value=pf.nodes.math.absolute(side), from_min=0.1, from_max=0.0, interpolation_type="SMOOTHSTEP")
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    return Channels(base, rough, metal, BLACK, pf.nodes.shader.displacement(height=lug * bump, midlevel=0.0))


def galvanized(colour, second, dirt_colour, roughness, metal, cell_size, contrast, dirt_reach, dirt, seed):
    """Hot-dip galvanized steel: zinc spangle, crystal cells a little lighter or darker than their neighbours."""
    vector = coordinates()
    cells = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / cell_size, voronoi_dimensions="4D", w=seed)
    shade = pf.nodes.color.rgb_to_bw(cells.color)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=shade * contrast, a=base, b=second)
    return Channels(base, pf.nodes.math.mix(a=rough, b=rough * 0.7, factor=shade), metal, BLACK, None)


def anodized(colour, roughness, metal, bump, bump_size):
    """Anodized aluminium: a coloured metal with a fine brushed grain, clean."""
    return Channels(colour, roughness, metal, BLACK, brushed_relief(coordinates(), bump, bump_size))


def quilted(colour, second, dirt_colour, roughness, quilt_size, puff, seam_width, dirt_reach, dirt, seed):
    """Quilted insulation or padding: square pillows stitched along darker seams."""
    vector = coordinates()
    across, up = face_grid(vector, quilt_size)
    edge = pf.nodes.math.maximum(pf.nodes.math.absolute(across), pf.nodes.math.absolute(up)) * 2.0
    pillow = 1.0 - pf.nodes.math.power(pf.nodes.math.clamp(edge), 4.0)
    seam = pf.nodes.math.greater_than(edge, 1.0 - seam_width)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=seam, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=pillow * puff, midlevel=0.0))


def pile(colour, second, dirt_colour, roughness, tuft_size, mottle_size, contrast, bump, dirt_reach, dirt, seed):
    """A rug's or a mat's pile: its tufts mottled toward a second colour in soft patches, a fine tufted relief, dirt
    in the cavities (stairwell's door mat and quarters' rug, plain cloth in one colour, could never look like their
    close-ups' mottled pile, 2026-11-08)."""
    vector = coordinates()
    mottle = pf.nodes.texture.noise(vector=vector, scale=1.0 / mottle_size, detail=4.0, noise_dimensions="4D", w=seed)
    tufts = pf.nodes.texture.noise(vector=vector, scale=1.0 / tuft_size, detail=1.0, noise_dimensions="4D", w=seed)
    patch = pf.nodes.math.clamp((mottle.fac - 0.5) * 3.0 + 0.5)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=patch * contrast, a=base, b=second)
    relief = pf.nodes.shader.displacement(height=(tufts.fac - 0.5) * bump, midlevel=0.0)
    return Channels(base, rough, 0.0, BLACK, relief)


def written(colour, second, roughness, line_pitch, stroke, word_size, ink_share, seed):
    """A note's or a paper's writing or print: rows of ink in a second colour across its face (face_plane), one every
    `line_pitch`, each `stroke` of the pitch tall, broken into words by a noise along it (about `ink_share` of a row
    inked); the paper flat and clean (quarters' sticky note, one plain paper colour, could never look like its
    close-up's handwritten lines, 2026-11-08)."""
    vector = coordinates()
    _, upward = face_plane(vector)
    off_middle = pf.nodes.math.absolute(pf.nodes.math.fraction(upward / line_pitch) - 0.5) * 2.0
    words = pf.nodes.texture.noise(vector=vector, scale=1.0 / word_size, detail=2.0, noise_dimensions="4D", w=seed)
    inked = pf.nodes.math.less_than(off_middle, stroke) * pf.nodes.math.less_than(words.fac, ink_share)
    return Channels(pf.nodes.color.mix_rgb(factor=inked, a=colour, b=second), roughness, 0.0, BLACK, None)


def composite(colour, second, roughness, weave, bump):
    """A woven composite panel (glass or carbon fibre): a 2/2 twill, each tow `weave` wide passing over two and under
    two and the pattern stepping one tow a row, so it runs on a diagonal as carbon cloth does (a plain checker at twice
    the tow drew four carbon panels as a chequerboard, #155); bands one way and the other, a little lighter and darker,
    under a clear coat."""
    vector = coordinates()
    warp = pf.nodes.texture.wave(vector=vector, scale=1.0 / weave, bands_direction="X", wave_profile="TRI", detail=0.0)
    weft = pf.nodes.texture.wave(vector=vector, scale=1.0 / weave, bands_direction="Z", wave_profile="TRI", detail=0.0)
    point = pf.nodes.math.separate_xyz(vector)
    step = pf.nodes.math.floor(point.x / weave) + pf.nodes.math.floor(point.z / weave)
    over = pf.nodes.math.less_than(pf.nodes.math.floor_mod(step, 4.0), 2.0)
    woven = pf.nodes.math.mix(a=warp.fac, b=weft.fac, factor=over)
    base = pf.nodes.color.mix_rgb(factor=woven * 0.35, a=colour, b=second)
    return Channels(base, roughness, 0.0, BLACK, pf.nodes.shader.displacement(height=woven * bump, midlevel=0.0))


def picture_on(colour, image):
    """A picture printed over a colour through its own transparency, read on the part's `content` UV map: the
    colour and the picture node."""
    picture = pf.nodes.texture.image(vector=pf.nodes.shader.uv_map(uv_map="content"), image=image, extension="CLIP")
    return pf.nodes.color.mix_rgb(factor=picture.fac, a=colour, b=picture.color), picture


def screen(colour, roughness, image):
    """A screen: dark glass with a slight shine, its content a picture lit from behind, so only the content
    glows (in the game, a screen's kind glows in its own colour, and the glass's own colour is near black)."""
    base, picture = picture_on(colour, image)
    lit = pf.nodes.color.mix_rgb(factor=picture.fac, a=pf.Color(BLACK), b=picture.color)
    return Channels(base, roughness, 0.0, lit, None)


def printed(colour, roughness, image):
    """A label, plate or stencil: its picture printed on a colour."""
    base, _ = picture_on(colour, image)
    return Channels(base, roughness, 0.0, BLACK, None)


# Earth's surfaces (the prologue build, 2026-10-07: Hong Kong 2099 public housing at night): paint on plaster, tiles,
# terrazzo, painted floorboards, paint over rust and wet asphalt. Each wears from a cause, as the base's do: edges and
# corners chip, feet scuff the foot of a wall or a piece (kick_mask), feet wear a floor's paint, rain rusts steel.


def lumpy_relief(vector, bump, bump_size, seed):
    """Rendered plaster's soft lumps and trowel marks: a low noise, no grain."""
    lumps = pf.nodes.texture.noise(vector=vector, scale=1.0 / bump_size, detail=3.0, noise_dimensions="4D", w=seed)
    return pf.nodes.shader.displacement(height=(lumps.fac - 0.5) * bump, midlevel=0.0)


def painted_plaster(colour, bare, dirt_colour, roughness, bare_roughness, bump, bump_size, edge_width, breakup_scale,
                    dirt_reach, wear, dirt, seed, foot, kicks, scuffs=0.0, decals=None):
    """Whitewash or gloss paint on rendered plaster, its decals printed on the paint: chipped to the bare render on
    edges and corners and scuffed where feet kick the foot of the wall and where handling scratches it, dirty in the
    cavities."""
    vector = coordinates()
    kicked = kick_mask(vector, foot, wear, kicks, breakup_scale, seed)
    wear_mask = pf.nodes.math.maximum(pf.nodes.math.maximum(
        edge_wear_mask(vector, wear, edge_width, breakup_scale, seed), kicked), scuff_mask(vector, wear, scuffs, seed))
    dirty = pf.nodes.math.maximum(dirt_mask(vector, dirt, dirt_reach, seed), kicked * dirt * 0.5)
    base, rough, shine = layered((colour, roughness, 0.0), (bare, bare_roughness, 0.0), wear_mask, dirt_colour, dirty,
                                 decals)
    chipped = pf.nodes.shader.displacement(height=wear_mask * -0.0008, midlevel=0.0)
    return Channels(base, rough, shine, BLACK, lumpy_relief(vector, bump, bump_size, seed) + chipped)


# How wide a rain streak runs, and how dark it is against the place's dirt (2026-10-10: thin, hard, dark streaks 6 cm
# wide read as wood grain on the street's render; soft ones 10 cm wide read as rain).
STREAK_WIDE = 0.1
STREAK_DARK = 0.85


def rain_streaks(vector, streaks, streak_length, seed):
    """Where rain running down a wall has left dirt: thin streaks hanging down the surface's own plane, each a few
    centimetres across and about `streak_length` long, on upright faces only (a sill's top or a roof gathers dirt
    in its cavities instead); `streaks` scales how many."""
    across, upward = face_plane(vector)
    stretched = pf.nodes.math.combine_xyz(x=across / STREAK_WIDE, y=upward / streak_length, z=0.0)
    runs = pf.nodes.texture.noise(vector=stretched, scale=1.0, detail=2.0, noise_dimensions="4D", w=seed + 41.0)
    streak = pf.nodes.math.map_range(value=runs.fac, from_min=0.6 - 0.15 * streaks, from_max=0.8 - 0.15 * streaks,
                                     interpolation_type="SMOOTHSTEP")
    upright = pf.nodes.math.map_range(value=pf.nodes.math.absolute(
        pf.nodes.math.separate_xyz(pf.nodes.shader.geometry().normal).z), from_min=0.5, from_max=0.2)
    return pf.nodes.math.clamp(streak * upright * pf.nodes.math.greater_than(streaks, 0.001))


def weathered_render(colour, bare, dirt_colour, roughness, bare_roughness, bump, bump_size, edge_width, breakup_scale,
                     dirt_reach, peel, streaks, streak_length, mottle, wear, dirt, seed, foot, kicks):
    """Painted render on an old block's outside walls (the street's tenements, 2026-10-10: the flat plates read as
    new paint up close): painted_plaster's chips and kicks, the paint peeled off the render in patches as far as the
    place's wear (`peel`), rain streaks down the upright faces as dirty as the place (`streaks`), and the paint's
    shade mottled by patches of fading and repainting (`mottle`)."""
    vector = coordinates()
    kicked = kick_mask(vector, foot, wear, kicks, breakup_scale, seed)
    patches = pf.nodes.texture.noise(vector=vector, scale=breakup_scale, detail=5.0, noise_dimensions="4D",
                                     w=seed + 23.0)
    peeled = pf.nodes.math.map_range(value=patches.fac, from_min=0.74 - 0.25 * wear * peel,
                                     from_max=0.77 - 0.25 * wear * peel,
                                     interpolation_type="SMOOTHSTEP") * pf.nodes.math.greater_than(peel * wear, 0.001)
    wear_mask = pf.nodes.math.maximum(pf.nodes.math.maximum(edge_wear_mask(vector, wear, edge_width, breakup_scale,
                                                                           seed), kicked), peeled)
    streaked = rain_streaks(vector, streaks, streak_length, seed) * dirt * STREAK_DARK
    dirty = pf.nodes.math.maximum(pf.nodes.math.maximum(dirt_mask(vector, dirt, dirt_reach, seed), kicked * dirt * 0.5),
                                  streaked)
    shades = pf.nodes.texture.noise(vector=vector, scale=0.7, detail=2.0, noise_dimensions="4D", w=seed + 29.0)
    faded = pf.nodes.math.map_range(value=shades.fac, from_min=0.4, from_max=0.65) * mottle
    painted = pf.nodes.color.mix_rgb(factor=faded, a=colour, b=bare)
    base, rough, shine = layered((painted, roughness, 0.0), (bare, bare_roughness, 0.0), wear_mask, dirt_colour, dirty)
    chipped = pf.nodes.shader.displacement(height=wear_mask * -0.0006, midlevel=0.0)
    return Channels(base, rough, shine, BLACK, lumpy_relief(vector, bump, bump_size, seed) + chipped)


def face_joints(vector, across_pitch, up_pitch, joint):
    """Where a grid of `across_pitch` by `up_pitch` cells on the surface's own plane has its joints, `joint` metres
    wide: 1 in a joint, 0 on a cell."""
    across, upward = face_plane(vector)
    side = pf.nodes.math.fraction(across / across_pitch)
    rise = pf.nodes.math.fraction(upward / up_pitch)
    near_side = pf.nodes.math.minimum(side, 1.0 - side) * across_pitch
    near_rise = pf.nodes.math.minimum(rise, 1.0 - rise) * up_pitch
    return pf.nodes.math.less_than(pf.nodes.math.minimum(near_side, near_rise), joint * 0.5)


def tiles(colour, second, dirt_colour, roughness, pitch, grout, bump, dirt_reach, dirt, seed):
    """Glazed square tiles in grout: the tiles glossy, the grout matt, sunk and dirtier."""
    vector = coordinates()
    joint = face_joints(vector, pitch, pitch, grout)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=joint, a=base, b=second)
    rough = pf.nodes.math.mix(a=rough, b=0.85, factor=joint)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=joint * -bump, midlevel=0.0))


def terrazzo(colour, second, dirt_colour, roughness, chip_size, chip_share, contrast, dirt_reach, dirt, seed):
    """Terrazzo: stone chips set in a ground and polished flat, each chip a little lighter or darker."""
    vector = coordinates()
    cells = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / chip_size, voronoi_dimensions="4D", w=seed)
    chip = pf.nodes.math.less_than(cells.distance, chip_share)
    shade = pf.nodes.color.rgb_to_bw(cells.color)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=chip * (0.4 + shade * contrast), a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, None)


def boards(colour, bare, second, dirt_colour, roughness, bare_roughness, board_width, gap, bump, wear,
           breakup_scale, dirt_reach, dirt, seed):
    """Painted floorboards: boards `board_width` across with dark gaps, the paint worn through to the timber in long
    patches along the boards where feet go, as far as the place's wear, dirt in the gaps."""
    vector = coordinates()
    across, upward = face_plane(vector)
    side = pf.nodes.math.fraction(across / board_width)
    in_gap = pf.nodes.math.less_than(pf.nodes.math.minimum(side, 1.0 - side) * board_width, gap * 0.5)
    stretched = pf.nodes.math.combine_xyz(x=across * 3.0, y=upward * 0.4, z=0.0)
    patches = pf.nodes.texture.noise(vector=stretched, scale=breakup_scale, detail=3.0, noise_dimensions="4D", w=seed)
    worn = pf.nodes.math.map_range(value=patches.fac, from_min=0.76 - 0.22 * wear, from_max=0.8 - 0.22 * wear,
                                   interpolation_type="SMOOTHSTEP") * pf.nodes.math.greater_than(wear, 0.001)
    dirty = pf.nodes.math.maximum(dirt_mask(vector, dirt, dirt_reach, seed), in_gap * dirt)
    base, rough, _ = layered((colour, roughness, 0.0), (bare, bare_roughness, 0.0), worn, dirt_colour, dirty)
    base = pf.nodes.color.mix_rgb(factor=in_gap, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=in_gap * -bump, midlevel=0.0))


def rusted_metal(colour, bare, dirt_colour, roughness, bare_roughness, metal, bump, bump_size, edge_width,
                 breakup_scale, dirt_reach, wear, dirt, seed, foot, kicks, scuffs=0.0, decals=None):
    """Paint on mild steel outdoors, its decals printed on the paint: rust on the edges, in blooms where the paint let
    the rain in, where feet kick it and where handling scuffs it, as far as the place's wear; rust is matt and dark,
    pitted, never shiny."""
    vector = coordinates()
    blooms = pf.nodes.texture.noise(vector=vector, scale=breakup_scale * 2.0, detail=4.0, noise_dimensions="4D",
                                    w=seed + 7.0)
    bloomed = pf.nodes.math.map_range(value=blooms.fac, from_min=0.72 - 0.3 * wear, from_max=0.78 - 0.3 * wear,
                                      interpolation_type="SMOOTHSTEP") * pf.nodes.math.greater_than(wear, 0.001)
    kicked = kick_mask(vector, foot, wear, kicks, breakup_scale, seed)
    rusted = pf.nodes.math.maximum(pf.nodes.math.maximum(pf.nodes.math.maximum(
        edge_wear_mask(vector, wear, edge_width, breakup_scale, seed), bloomed), kicked),
        scuff_mask(vector, wear, scuffs, seed))
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    base, rough, shine = layered((colour, roughness, metal), (bare, bare_roughness, 0.0), rusted, dirt_colour, dirty,
                                 decals)
    pits = pf.nodes.texture.noise(vector=vector, scale=1.0 / bump_size, detail=3.0, noise_dimensions="4D", w=seed)
    relief = pf.nodes.shader.displacement(height=(pits.fac - 0.5) * bump * rusted - rusted * 0.0003, midlevel=0.0)
    return Channels(base, rough, shine, BLACK, relief)


def wet_asphalt(colour, second, dirt_colour, roughness, wet_roughness, chip_size, contrast, wet_share, bump,
                dirt_reach, dirt, seed):
    """Asphalt after rain: dark aggregate in a darker binder, puddles lying flat and glossy in the low places."""
    vector = coordinates()
    cells = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / chip_size, voronoi_dimensions="4D", w=seed)
    shade = pf.nodes.color.rgb_to_bw(cells.color)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=shade * contrast, a=base, b=second)
    pools = pf.nodes.texture.noise(vector=vector, scale=0.35, detail=2.0, noise_dimensions="4D", w=seed + 5.0)
    wet = pf.nodes.math.map_range(value=pools.fac, from_min=1.0 - wet_share - 0.03, from_max=1.0 - wet_share + 0.03,
                                  interpolation_type="SMOOTHSTEP")
    rough = pf.nodes.math.mix(a=rough, b=wet_roughness, factor=wet)
    base = pf.nodes.color.mix_rgb(factor=wet * 0.35, a=base, b=pf.Color(BLACK))
    relief = pf.nodes.shader.displacement(height=(1.0 - cells.distance) * bump * (1.0 - wet), midlevel=0.0)
    return Channels(base, rough, 0.0, BLACK, relief)


# Natural grounds (2026-10-22: the bodies' faces and the outdoor grounds took the nearest man-made recipe): regolith,
# rock, sand, ocean and ice, each from what made it. Which one a body or a ground row gets is a rule
# (score/stages/natural_grounds.py: the row's words, else the body's physics), never a picture's colour.


def ridges(vector, scale, width, seed):
    """Thin lines where a noise field crosses its middle (a crack's or a crest's path): 1 on a line `width` wide in
    the field's own units, 0 off it."""
    field = pf.nodes.texture.noise(vector=vector, scale=scale, detail=3.0, noise_dimensions="4D", w=seed)
    return pf.nodes.math.map_range(value=pf.nodes.math.absolute(field.fac - 0.5), from_min=width, from_max=0.0,
                                   interpolation_type="SMOOTHSTEP")


def regolith(colour, second, roughness, grain_size, contrast, crater_scale, crater_share, bump, seed):
    """An airless body's ground: fine dust over rubble, ground by impacts for ages, pitted with small craters whose
    rims are fresher and lighter (`second`); matt, nothing wears it but the impacts."""
    vector = coordinates()
    rubble = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / grain_size, voronoi_dimensions="4D", w=seed)
    base = pf.nodes.color.mix_rgb(factor=pf.nodes.color.rgb_to_bw(rubble.color) * contrast, a=colour, b=second)
    pits = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / crater_scale, voronoi_dimensions="4D", w=seed + 11.0)
    inside = pf.nodes.math.less_than(pits.distance, crater_share)
    bowl = pf.nodes.math.map_range(value=pits.distance, from_min=0.0, from_max=crater_share,
                                   interpolation_type="SMOOTHSTEP")
    rim = inside * pf.nodes.math.map_range(value=pits.distance, from_min=crater_share * 0.7, from_max=crater_share)
    base = pf.nodes.color.mix_rgb(factor=rim * 0.5, a=base, b=second)
    height = (bowl - 1.0) * inside * bump + rubble.distance * bump * 0.15
    return Channels(base, roughness, 0.0, BLACK, pf.nodes.shader.displacement(height=height, midlevel=0.0))


def rock(colour, second, roughness, strata_pitch, contrast, crack_scale, crack_width, bump, bump_size, seed):
    """Bare bedrock: bands of strata laid one over another across the face (`second` the other layer's shade), split
    by cracks, lumpy where it weathered; matt."""
    vector = coordinates()
    _, upward = face_plane(vector)
    warp = pf.nodes.texture.noise(vector=vector, scale=0.5 / strata_pitch, detail=2.0, noise_dimensions="4D",
                                  w=seed + 3.0)
    layer = pf.nodes.math.absolute(pf.nodes.math.fraction(upward / strata_pitch + warp.fac) - 0.5) * 2.0
    cracks = ridges(vector, crack_scale, crack_width, seed + 13.0)
    base = pf.nodes.color.mix_rgb(factor=layer * contrast, a=colour, b=second)
    base = pf.nodes.color.mix_rgb(factor=cracks * 0.6, a=base, b=pf.Color(BLACK))
    lumps = pf.nodes.texture.noise(vector=vector, scale=1.0 / bump_size, detail=4.0, noise_dimensions="4D", w=seed)
    height = (lumps.fac - 0.5) * bump - cracks * bump * 0.5
    return Channels(base, roughness, 0.0, BLACK, pf.nodes.shader.displacement(height=height, midlevel=0.0))


def sand(colour, second, roughness, ripple_pitch, ripple_height, grain_size, contrast, seed):
    """Wind-laid sand: ripples across the ground `ripple_pitch` apart, bent by the wind's eddies, their crests a
    lighter sand (`second`), fine grains over all; matt."""
    vector = coordinates()
    across, _ = face_plane(vector)
    eddies = pf.nodes.texture.noise(vector=vector, scale=0.25 / ripple_pitch, detail=2.0, noise_dimensions="4D",
                                    w=seed + 5.0)
    crest = 1.0 - pf.nodes.math.absolute(pf.nodes.math.fraction(across / ripple_pitch + eddies.fac * 2.0) - 0.5) * 2.0
    grains = pf.nodes.texture.noise(vector=vector, scale=1.0 / grain_size, detail=1.0, noise_dimensions="4D", w=seed)
    base = pf.nodes.color.mix_rgb(factor=crest * contrast + (grains.fac - 0.5) * contrast * 0.5, a=colour, b=second)
    return Channels(base, roughness, 0.0, BLACK, pf.nodes.shader.displacement(height=crest * ripple_height,
                                                                               midlevel=0.0))


def ocean(colour, second, roughness, wave_scale, wave_height, foam_share, seed):
    """Open water: a deep colour heaving in waves, foam (`second`) on the highest crests, glossy where it is not
    foam."""
    vector = coordinates()
    waves = pf.nodes.texture.noise(vector=vector, scale=1.0 / wave_scale, detail=4.0, noise_dimensions="4D", w=seed)
    foam = pf.nodes.math.map_range(value=waves.fac, from_min=1.0 - foam_share - 0.03, from_max=1.0 - foam_share + 0.03,
                                   interpolation_type="SMOOTHSTEP")
    base = pf.nodes.color.mix_rgb(factor=foam, a=colour, b=second)
    rough = pf.nodes.math.mix(a=roughness, b=0.9, factor=foam)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=(waves.fac - 0.5) * wave_height,
                                                                          midlevel=0.0))


def ice(colour, second, roughness, crack_scale, crack_width, frost_share, bump, bump_size, seed):
    """An ice sheet: smooth and glossy, split by pressure cracks in a deeper shade (`second`), frost lying rough in
    patches."""
    vector = coordinates()
    cracks = ridges(vector, crack_scale, crack_width, seed + 19.0)
    patches = pf.nodes.texture.noise(vector=vector, scale=0.5 / crack_scale, detail=3.0, noise_dimensions="4D",
                                     w=seed + 7.0)
    frost = pf.nodes.math.map_range(value=patches.fac, from_min=1.0 - frost_share - 0.05,
                                    from_max=1.0 - frost_share + 0.05, interpolation_type="SMOOTHSTEP")
    base = pf.nodes.color.mix_rgb(factor=cracks, a=colour, b=second)
    rough = pf.nodes.math.mix(a=roughness, b=0.85, factor=frost)
    swells = pf.nodes.texture.noise(vector=vector, scale=1.0 / bump_size, detail=2.0, noise_dimensions="4D", w=seed)
    height = (swells.fac - 0.5) * bump - cracks * bump
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=height, midlevel=0.0))


# The adopted set's finish families (#155, 2026-11-22): the shared tiling materials of the adopted set the 30 recipes
# above did not cover (moulded plastic, polished metal, concrete, corrugated board, leather, glazed ceramic, gel-coated
# fibreglass, grained timber). Each is our own; a material of the set is fitted to one of these from its maps
# (likeness/fit.py) and checked to look the same (likeness/check.py).


def plastic(colour, dirt_colour, roughness, grain_size, bump, dirt_reach, dirt, seed, second=None, mottle_size=0.15,
            contrast=0.0, roughness_spread=0.0):
    """Moulded plastic, glossy to matt by its roughness: its colour, mottled (mottled, smudges and scuffs), the mould's
    fine grain as relief, dirt in the cavities."""
    vector = coordinates()
    colour, roughness = mottled(colour, second, roughness, vector, mottle_size, contrast, roughness_spread, seed)
    grain = pf.nodes.texture.noise(vector=vector, scale=1.0 / grain_size, detail=2.0, noise_dimensions="4D", w=seed)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=(grain.fac - 0.5) * bump,
                                                                           midlevel=0.0))


def polished_metal(colour, roughness, metal, scratch_scale, scratches, seed):
    """Polished metal (chrome, polished bronze or gold): a mirror finish, rougher along its fine scratches, clean."""
    scratched = ridges(coordinates(), scratch_scale, 0.02, seed)
    rough = pf.nodes.math.mix(a=roughness, b=pf.nodes.math.minimum(roughness + 0.25, 1.0), factor=scratched * scratches)
    return Channels(colour, rough, metal, BLACK, None)


def concrete(colour, second, dirt_colour, roughness, mottle_size, contrast, pore_size, pore_share, bump, dirt_reach,
             dirt, seed):
    """Cast concrete: its cement mottled toward a second shade in soft patches, small air pores sunk and darker,
    dirt in the cavities."""
    vector = coordinates()
    mottle = pf.nodes.texture.noise(vector=vector, scale=1.0 / mottle_size, detail=4.0, noise_dimensions="4D", w=seed)
    pores = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / pore_size, voronoi_dimensions="4D", w=seed + 7.0)
    pore = pf.nodes.math.less_than(pores.distance, pore_share)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=pf.nodes.math.clamp((mottle.fac - 0.5) * 2.0 * contrast + pore * 0.6),
                                  a=base, b=second)
    height = (mottle.fac - 0.5) * bump - pore * bump
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=height, midlevel=0.0))


def cardboard(colour, second, roughness, flute_pitch, flute_height, fibre_size, contrast, seed):
    """Corrugated board: the flutes under the liner as faint ridges across the face (face_plane), its fibres mottled
    toward a second shade; matt and clean."""
    vector = coordinates()
    across, _ = face_plane(vector)
    flute = 1.0 - pf.nodes.math.absolute(pf.nodes.math.fraction(across / flute_pitch) - 0.5) * 2.0
    fibres = pf.nodes.texture.noise(vector=vector, scale=1.0 / fibre_size, detail=3.0, noise_dimensions="4D", w=seed)
    base = pf.nodes.color.mix_rgb(factor=pf.nodes.math.clamp((fibres.fac - 0.5) * 2.0 * contrast + 0.5 * contrast),
                                  a=colour, b=second)
    return Channels(base, roughness, 0.0, BLACK, pf.nodes.shader.displacement(height=flute * flute_height,
                                                                               midlevel=0.0))


def leather(colour, second, dirt_colour, roughness, grain_size, contrast, bump, dirt_reach, dirt, seed):
    """Grained leather: pebbles of grain parted by creases a shade darker (`second`), dirt in the creases."""
    vector = coordinates()
    pebbles = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / grain_size, feature="F2", voronoi_dimensions="4D",
                                       w=seed)
    nearest = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / grain_size, voronoi_dimensions="4D", w=seed)
    crease = pf.nodes.math.map_range(value=pebbles.distance - nearest.distance, from_min=0.15, from_max=0.0,
                                     interpolation_type="SMOOTHSTEP")
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=crease * contrast, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=-crease * bump, midlevel=0.0))


def ceramic(colour, second, roughness, speckle_size, speckle_share, bump, bump_size, seed):
    """Glazed ceramic or porcelain: a glossy glaze with a soft swell, fine speckles of a second shade in the body;
    clean."""
    vector = coordinates()
    specks = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / speckle_size, voronoi_dimensions="4D", w=seed)
    speck = pf.nodes.math.less_than(specks.distance, speckle_share)
    base = pf.nodes.color.mix_rgb(factor=speck, a=colour, b=second)
    return Channels(base, roughness, 0.0, BLACK, lumpy_relief(vector, bump, bump_size, seed))


def fiberglass(colour, second, roughness, fibre_size, contrast, bump, seed):
    """Gel-coated glass fibre: a glossy coat over a mat of chopped strands, the strands showing through as a faint
    streaky mottle toward a second shade and a slight print-through relief."""
    vector = coordinates()
    point = pf.nodes.math.separate_xyz(vector)
    one_way = pf.nodes.texture.noise(vector=pf.nodes.math.combine_xyz(x=point.x * 0.15, y=point.y, z=point.z),
                                     scale=1.0 / fibre_size, detail=2.0, noise_dimensions="4D", w=seed)
    other_way = pf.nodes.texture.noise(vector=pf.nodes.math.combine_xyz(x=point.x, y=point.y * 0.15, z=point.z),
                                       scale=1.0 / fibre_size, detail=2.0, noise_dimensions="4D", w=seed + 3.0)
    strands = pf.nodes.math.maximum(one_way.fac, other_way.fac)
    base = pf.nodes.color.mix_rgb(factor=pf.nodes.math.clamp((strands - 0.5) * 2.0) * contrast, a=colour, b=second)
    return Channels(base, roughness, 0.0, BLACK, pf.nodes.shader.displacement(height=(strands - 0.5) * bump,
                                                                               midlevel=0.0))


def mat(colour, second, dirt_colour, roughness, pitch, stud_share, ribs, contrast, bump, dirt_reach, dirt, seed):
    """A moulded mat, rubber or plastic: raised studs or coins on a square grid on the surface's plane, or ribs along
    it (`ribs` 1), each `stud_share` of its pitch across with sloped sides, their tops a shade toward `second` by
    `contrast`, dirt between them."""
    vector = coordinates()
    across, up = face_grid(vector, pitch)
    reach = pf.nodes.math.mix(a=pf.nodes.math.sqrt(across * across + up * up), b=pf.nodes.math.absolute(across),
                              factor=ribs)
    raised = pf.nodes.math.map_range(value=reach, from_min=stud_share * 0.5, from_max=stud_share * 0.5 - MAT_SLOPE,
                                     interpolation_type="SMOOTHSTEP")
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt * (1.0 - raised), dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=raised * contrast, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=raised * bump, midlevel=0.0))


def strand_board(colour, second, dirt_colour, roughness, flake_size, contrast, bump, dirt_reach, dirt, seed):
    """Oriented strand or fibre board (OSB, HDF): flakes of wood pressed flat along the board (face_plane),
    `flake_size` across and FLAKE_LENGTH times as long (a fibre board's fine, its speckle), each its own shade between
    colour and `second` by `contrast` and a little proud of or under its neighbours; dirt in the cavities."""
    vector = coordinates()
    across, upward = face_plane(vector)
    pressed = pf.nodes.math.combine_xyz(x=across / FLAKE_LENGTH, y=upward, z=0.0)
    flakes = pf.nodes.texture.voronoi(vector=pressed, scale=1.0 / flake_size, voronoi_dimensions="4D", w=seed)
    shade = pf.nodes.color.rgb_to_bw(flakes.color)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=shade * contrast, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=(shade - 0.5) * bump, midlevel=0.0))


def knit(colour, second, dirt_colour, roughness, stitch, contrast, bump, dirt_reach, dirt, seed):
    """Knitted cloth (a jumper's, a blanket's): columns of V-shaped loops `stitch` wide on the surface's plane, each
    loop two slanted ovals leaning together, the gaps between them sunk and a shade toward `second` by `contrast`;
    dirt in the gaps."""
    vector = coordinates()
    across, upward = face_plane(vector)
    side = pf.nodes.math.absolute(pf.nodes.math.fraction(across / stitch) - 0.5)  # 0 a column's middle, 0.5 its edge
    row = pf.nodes.math.fraction(upward / (stitch * KNIT_ROW) + side) - 0.5  # the loops lean in: a V
    off_side, off_row = (side - 0.25) * 4.0, row * 2.0
    oval = pf.nodes.math.sqrt(off_side * off_side + off_row * off_row)
    loop = pf.nodes.math.map_range(value=oval, from_min=1.0, from_max=0.3, interpolation_type="SMOOTHSTEP")
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt * (1.0 - loop), dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=(1.0 - loop) * contrast, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=loop * bump, midlevel=0.0))


def hammered(colour, second, dirt_colour, roughness, dent_size, contrast, bump, dirt_reach, dirt, seed):
    """A hammered (dimpled) finish, a moulded plastic's or a paint's: round dents `dent_size` across packed edge to
    edge (voronoi cells, each sunk most at its middle), their floors a shade toward `second` by `contrast`, the
    ridges between them catching the light; dirt in the dents."""
    vector = coordinates()
    cells = pf.nodes.texture.voronoi(vector=vector, scale=1.0 / dent_size, voronoi_dimensions="4D", w=seed)
    dent = pf.nodes.math.clamp(1.0 - cells.distance * 2.0)  # 1 at a dent's middle, 0 at its rim
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt * dent, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=dent * contrast, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=-dent * dent * bump, midlevel=0.0))


def grained_wood(colour, second, dirt_colour, roughness, ring_pitch, contrast, bump, dirt_reach, dirt, seed):
    """Timber with its grain (planks, plywood, oak): growth rings as bands along the board, bent by a noise, the late
    wood a second shade and a little sunk, dirt in the cavities."""
    vector = coordinates()
    point = pf.nodes.math.separate_xyz(vector)
    bend = pf.nodes.texture.noise(vector=pf.nodes.math.combine_xyz(x=point.x * 0.1, y=point.y, z=point.z),
                                  scale=0.5 / ring_pitch, detail=2.0, noise_dimensions="4D", w=seed)
    late = pf.nodes.math.power(1.0 - pf.nodes.math.absolute(
        pf.nodes.math.fraction(point.y / ring_pitch + bend.fac * 3.0) - 0.5) * 2.0, 3.0)
    base, rough = dirty_flat(colour, roughness, dirt_colour, vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=late * contrast, a=base, b=second)
    return Channels(base, rough, 0.0, BLACK, pf.nodes.shader.displacement(height=-late * bump, midlevel=0.0))


RECIPES = {"painted_metal": painted_metal, "bare_metal": bare_metal, "cast_metal": cast_metal,
           "perforated_metal": perforated_metal, "chequer_plate": chequer_plate, "galvanized": galvanized,
           "anodized": anodized, "rubber": rubber, "cloth": cloth, "quilted": quilted, "pile": pile,
           "written": written, "composite": composite, "glass": glass,
           "glowing": glowing, "screen": screen, "printed": printed, "wood": wood,
           "painted_plaster": painted_plaster, "weathered_render": weathered_render, "tiles": tiles,
           "terrazzo": terrazzo, "boards": boards, "rusted_metal": rusted_metal, "wet_asphalt": wet_asphalt,
           "regolith": regolith, "rock": rock, "sand": sand, "ocean": ocean, "ice": ice, "plastic": plastic,
           "polished_metal": polished_metal, "concrete": concrete, "cardboard": cardboard, "leather": leather,
           "ceramic": ceramic, "fiberglass": fiberglass, "grained_wood": grained_wood, "mat": mat,
           "strand_board": strand_board, "knit": knit, "hammered": hammered}
# A mat stud's sloped side, a share of the pitch; a strand board's flake as long as this many times its width; a knit
# loop's row this share of its stitch's width high.
MAT_SLOPE = 0.08
FLAKE_LENGTH = 3.0
KNIT_ROW = 0.7
# Where each recipe starts from, for the page and the paper (the coordinator, 2026-10-06).
SOURCES = {
    "painted_metal": "infinigen2 paint.py (relief, BSD-3) + edgewear.py's bevel test (ported, new threshold band)"
                     " + new dirt and layering",
    "bare_metal": "infinigen2 metal_brushed.py (relief, BSD-3) + new dirt",
    "cast_metal": "written new (noise relief) + the library's dirt",
    "perforated_metal": "written new (hole grid) + the library's dirt",
    "chequer_plate": "written new (diagonal lug grid) + the library's dirt",
    "galvanized": "written new (voronoi spangle) + the library's dirt",
    "anodized": "infinigen2 metal_brushed.py (relief, BSD-3), clean",
    "rubber": "infinigen2 plastic.py plastic_black_rubberized (relief, BSD-3) + new dirt",
    "cloth": "infinigen2 fabric.py (weave relief, BSD-3) + the library's dirt",
    "quilted": "written new (stitched pillow grid) + the library's dirt",
    "pile": "written new (noise mottle toward a second colour, fine tuft relief) + the library's dirt",
    "written": "written new (rows of ink on the surface's plane, broken into words by a noise)",
    "composite": "written new (2/2 twill of two wave textures)",
    "glass": "written new (infinigen2 glass_colored needs transmission, which the ink look cannot draw)",
    "glowing": "written new",
    "screen": "written new: dark glass, its content a picture lit from behind",
    "printed": "written new: a picture printed on a colour",
    "wood": "written new (soft stretched-noise relief, flat colour) + the library's dirt; its grain comes from the "
            "piece's picture layer",
    "painted_plaster": "painted_metal's edge wear, kick wear and layering over a bare render + new lumpy relief",
    "weathered_render": "painted_plaster + rusted_metal's blooms as peeled patches + new rain streaks and mottled shade",
    "tiles": "written new (joint grid on the surface's plane) + the library's dirt",
    "terrazzo": "written new (voronoi chips) + the library's dirt",
    "boards": "written new (board gaps, foot-worn patches stretched along the boards) + the library's layering",
    "rusted_metal": "painted_metal's edge and kick wear + new rust blooms and pits",
    "wet_asphalt": "written new (voronoi aggregate, puddle noise) + the library's dirt",
    "regolith": "written new (voronoi rubble, voronoi impact pits with lighter rims)",
    "rock": "written new (warped strata bands on the surface's plane, ridged-noise cracks, lumpy relief)",
    "sand": "written new (eddy-bent wind ripples on the surface's plane, fine grain noise)",
    "ocean": "written new (wave noise relief, foam on the crests as wet_asphalt's puddles)",
    "ice": "written new (ridged-noise pressure cracks, rough frost patches)",
    "plastic": "written new (fine noise mould grain) + the library's dirt",
    "polished_metal": "written new (ridged-noise scratches rougher on a mirror finish)",
    "concrete": "written new (noise mottle, voronoi air pores) + the library's dirt",
    "cardboard": "written new (flute ridges on the surface's plane, noise fibre mottle)",
    "leather": "written new (voronoi F2 minus F1 creases between grain pebbles) + the library's dirt",
    "ceramic": "written new (voronoi speckles) + plaster's lumpy relief as the glaze's swell",
    "fiberglass": "written new (two stretched noises as chopped strands under a gel coat)",
    "grained_wood": "written new (noise-bent growth-ring bands along the board) + the library's dirt",
    "mat": "written new (studs or ribs on the surface's plane, sloped sides) + the library's dirt",
    "strand_board": "written new (voronoi flakes stretched along the board, a shade each) + the library's dirt",
    "knit": "written new (columns of leaning loop ovals on the surface's plane) + the library's dirt",
    "hammered": "written new (voronoi dents, deepest at their middles) + the library's dirt",
}
# The helpers each recipe is built of, for counting its lines of code.
PARTS = {
    "painted_metal": (painted_metal, coordinates, mottled, edge_wear_mask, kick_mask, scuff_mask, dirt_mask,
                      paint_relief, layered),
    "bare_metal": (bare_metal, coordinates, dirt_mask, brushed_relief),
    "cast_metal": (cast_metal, coordinates, dirty_flat, dirt_mask),
    "perforated_metal": (perforated_metal, coordinates, face_plane, face_grid, dirty_flat, dirt_mask),
    "chequer_plate": (chequer_plate, coordinates, face_plane, face_grid, dirty_flat, dirt_mask),
    "galvanized": (galvanized, coordinates, dirty_flat, dirt_mask),
    "anodized": (anodized, coordinates, brushed_relief),
    "rubber": (rubber, coordinates, mottled, dirt_mask, rubber_relief),
    "cloth": (cloth, coordinates, mottled, face_plane, face_joints, dirty_flat, dirt_mask, cloth_relief),
    "quilted": (quilted, coordinates, face_plane, face_grid, dirty_flat, dirt_mask),
    "pile": (pile, coordinates, dirty_flat, dirt_mask),
    "written": (written, coordinates, face_plane),
    "composite": (composite, coordinates),
    "glass": (glass,),
    "glowing": (glowing,),
    "screen": (screen, picture_on),
    "printed": (printed, picture_on),
    "wood": (wood, coordinates, dirty_flat, dirt_mask),
    "painted_plaster": (painted_plaster, coordinates, edge_wear_mask, kick_mask, scuff_mask, dirt_mask, lumpy_relief,
                        layered),
    "weathered_render": (weathered_render, coordinates, edge_wear_mask, kick_mask, dirt_mask, rain_streaks, face_plane,
                         lumpy_relief, layered),
    "tiles": (tiles, coordinates, face_plane, face_joints, dirty_flat, dirt_mask),
    "terrazzo": (terrazzo, coordinates, dirty_flat, dirt_mask),
    "boards": (boards, coordinates, face_plane, dirt_mask, layered),
    "rusted_metal": (rusted_metal, coordinates, edge_wear_mask, kick_mask, scuff_mask, dirt_mask, layered),
    "wet_asphalt": (wet_asphalt, coordinates, dirty_flat, dirt_mask),
    "regolith": (regolith, coordinates),
    "rock": (rock, coordinates, face_plane, ridges),
    "sand": (sand, coordinates, face_plane),
    "ocean": (ocean, coordinates),
    "ice": (ice, coordinates, ridges),
    "plastic": (plastic, coordinates, mottled, dirty_flat, dirt_mask),
    "polished_metal": (polished_metal, coordinates, ridges),
    "concrete": (concrete, coordinates, dirty_flat, dirt_mask),
    "cardboard": (cardboard, coordinates, face_plane),
    "leather": (leather, coordinates, dirty_flat, dirt_mask),
    "ceramic": (ceramic, coordinates, lumpy_relief),
    "fiberglass": (fiberglass, coordinates),
    "grained_wood": (grained_wood, coordinates, dirty_flat, dirt_mask),
    "mat": (mat, coordinates, face_plane, face_grid, dirty_flat, dirt_mask),
    "strand_board": (strand_board, coordinates, face_plane, dirty_flat, dirt_mask),
    "knit": (knit, coordinates, face_plane, dirty_flat, dirt_mask),
    "hammered": (hammered, coordinates, dirty_flat, dirt_mask),
}
COLOUR_ARGUMENTS = ("colour", "bare", "second", "dirt_colour", "print_colour")


# A piece that does not say where its foot stands is taken to stand clear of any kick; a spec that does not say
# whether its place is walked (place_line.unwalked, from the surface data's foot_traffic) is taken to be walked.
NO_FOOT = 100.0
WALKED = 1.0
# The job's seed a spec naming none of its own is drawn at (a library model remade part by part, tools/library/part_looks,
# carries its old variants' settings, some with no seed): a place's preview and its package's bake draw it alike.
SEED = 0.0


def arguments(spec, wear, dirt, seed, foot=None):
    """The recipe's keyword arguments from a resolved library entry (library.py), the place's wear and dirt and how
    high the piece's foot stands over its floor: its colours as ProcFunc colours, its picture (if it has one) loaded
    into Blender, the wear scaled by its age. A spec's own `wear` and `seed` (the finish route's settings,
    route_settings.set_spec) stand over the place's wear and the job's seed."""
    given = dict(spec, wear=min(1.0, spec.get("wear", wear) * spec.get("wear_scale", 1.0)), dirt=dirt,
                 seed=float(spec.get("seed", seed)),
                 foot=NO_FOOT if foot is None else float(foot), kicks=float(spec.get("kicks", WALKED)))
    for name in COLOUR_ARGUMENTS:
        if name in spec:
            given[name] = pf.Color(tuple(spec[name]))
    if spec.get("image"):
        import bpy

        given["image"] = pf.Image(bpy.data.images.load(spec["image"], check_existing=True))
    wanted = inspect.signature(RECIPES[spec["recipe"]]).parameters
    if spec.get("decals") and "decals" in wanted:
        given["decals"] = decal_layers(spec["decals"])
    for name in ("second", "print_colour"):
        if name in wanted and wanted[name].default is None and name not in given:
            given[name] = given["colour"]  # a mottled or printed finish whose spec names no second shade: its own
    return {name: given[name] for name, about in wanted.items()
            if name in given or about.default is inspect.Parameter.empty}


def decal_layers(decals):
    """Each decal placement of a spec (score #164: {image, at, normal, up, size_m, turn, layer, ink}) as a
    decal_layer, lowest `layer` first, its picture loaded into Blender."""
    import bpy

    found = []
    for decal in sorted(decals, key=lambda each: each.get("layer", 0)):
        image = pf.Image(bpy.data.images.load(decal["image"], check_existing=True))
        found.append(decal_layer(coordinates(), decal, image))
    return found


def channels(spec, wear, dirt, seed, foot=None):
    """One library material at one wear and dirt setting, on a piece whose foot stands `foot` over its floor, as
    Channels. A recipe that layers paint (it takes `decals`) prints its decals under its wear and dirt; any other gets
    them printed over its finish; print gives off no light, so a glowing finish's light is masked under it (#159 round
    8: the push button's IGN and ARMED vanished in its lit cap's glow)."""
    given = arguments(spec, wear, dirt, seed, foot)
    found = RECIPES[spec["recipe"]](**given)
    if not spec.get("decals") or "decals" in given:
        return found
    layers = decal_layers(spec["decals"])
    colour, roughness, metal = with_decals((found.base_color, found.roughness, found.metallic), layers)
    emission = pf.Color(found.emission) if isinstance(found.emission, tuple) else found.emission
    if found.emission is not BLACK:
        for mask, _, _ in layers:
            emission = pf.nodes.math.vector_scale(vector=emission, scale=1.0 - mask)
    return found._replace(base_color=colour, roughness=roughness, metallic=metal,
                          emission=found.emission if found.emission is BLACK else emission)


def settings_of(recipe):
    """A recipe's settings as ProcFunc's tracer sees them: traced with every argument left an input, the graph's
    inputs are the settings, and its node count says how big the recipe is."""
    from procfunc import compute_graph as graph_tools

    traced = pf.trace(RECIPES[recipe], trace_level=pf.tracer.TraceLevel.PRIMITIVES)
    names = list(traced.inputs.dict())
    nodes = sum(1 for _ in graph_tools.traverse_depth_first(traced))
    return {"settings": names, "nodes": nodes,
            "lines": sum(len(inspect.getsource(part).splitlines()) for part in PARTS[recipe])}


def shaded(found, through=False):
    """The Channels as a material to render: a principled surface over the relief; `through`, its alpha drawn (what
    a baked piece's base colour carries, bake.py: a glass seen through), else drawn whole."""
    glows = 1.0 if found.displacement is None and found.emission is not BLACK else 0.0
    emission = pf.Color(found.emission) if isinstance(found.emission, tuple) else found.emission
    surface = pf.nodes.shader.principled_bsdf(base_color=found.base_color, roughness=found.roughness,
                                              metallic=found.metallic, emission_color=emission,
                                              emission_strength=glows, alpha=found.alpha if through else 1.0)
    return pf.Material(surface=surface, displacement=found.displacement)


def seen_through(found):
    """Whether a recipe's Channels let what lies behind them through (an alpha under 1)."""
    return not isinstance(found.alpha, (int, float)) or found.alpha < 1.0


def occluded(found, occlusion):
    """The Channels with their base colour darkened by `occlusion` (a number node, 1 open to 0 shut): the model's own
    ambient occlusion (bake.occlusion, #206), so a finish shades into its seams and corners as a modelled one does."""
    colour = pf.Color(found.base_color) if isinstance(found.base_color, tuple) else found.base_color
    return found._replace(base_color=pf.nodes.math.vector_scale(vector=colour, scale=occlusion))


def masked(entries, shader_of, relief=True, uv_map="texels", occlusion=None):
    """One material of several surfaces, each drawn by its texel mask (#182): `entries` [(its mask picture's path,
    its Channels)] base first, each one's material (`shader_of(channels)`: shaded, or a channel emitted) mixed over
    those before it by its mask (Non-Color, its first channel) read on the model's own UVs (`uv_map`, the raw take's,
    make_chunky.TEXELS_UV), its relief mixed alike where `relief`. A mask read between texels blends its border over
    one texel. `occlusion` (a Blender picture on the same UVs: bake.occlusion's) darkens every surface's base colour
    by the model's own ambient occlusion (occluded, #206)."""
    import bpy
    surface, displacement = None, None
    uv = pf.nodes.shader.uv_map(uv_map=uv_map)
    shut = None if occlusion is None else pf.nodes.math.separate_xyz(
        pf.nodes.texture.image(vector=uv, image=pf.Image(occlusion), extension="EXTEND").color).x
    for path, found in entries:
        made = shader_of(found if shut is None else occluded(found, shut))
        if surface is None:
            surface, displacement = made.surface, found.displacement if relief else None
            continue
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "Non-Color"
        factor = pf.nodes.math.separate_xyz(pf.nodes.texture.image(vector=uv, image=pf.Image(image),
                                                                   extension="EXTEND").color).x
        surface = pf.nodes.shader.mix_shader(factor, surface, made.surface)
        if relief and (found.displacement is not None or displacement is not None):
            zero = (0.0, 0.0, 0.0)
            displacement = pf.nodes.math.mix(a=zero if displacement is None else displacement,
                                             b=zero if found.displacement is None else found.displacement,
                                             factor=factor, data_type=pf.NodeDataType.FLOAT_VECTOR)
    return pf.Material(surface=surface, displacement=displacement)


def emitted(value):
    """One channel given off as light, for baking or scoring it exactly (a colour node, or a number as grey)."""
    if isinstance(value, (int, float)):
        value = pf.Color((float(value), float(value), float(value)))
    elif isinstance(value, tuple):
        value = pf.Color(value)
    return pf.Material(surface=pf.nodes.shader.emission(color=value, strength=1.0))
