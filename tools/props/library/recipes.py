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
    dirt        a mask from cavities (ambient occlusion within the piece's own reach) with its own breakup
    layered     paint over bare metal through the wear mask, dirt over both through the dirt mask

A recipe (`painted_metal`, `bare_metal`, `rubber`, `glass`, `glowing`) takes every setting as an argument and has no
Python branch on one, so ProcFunc's tracer can trace it with its settings as inputs (`settings_of`), which is how the
tuning loop learns what it may turn. It returns `Channels`: base colour, roughness, metal, emission and displacement
as ProcFunc nodes, so the same recipe is rendered (`shaded`) and baked channel by channel (`emitted`). Colours come
only from the palette tokens the caller resolves (library.py); no recipe holds a colour of its own.
"""
import inspect
from typing import NamedTuple

import procfunc as pf
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


def dirt_mask(vector, dirt, reach, seed):
    """Where dirt gathers: cavities and inside corners within `reach` metres, broken up at a large scale."""
    occlusion = pf.nodes.shader.ambient_occlusion(distance=reach, only_local=True, samples=16)
    cavity = pf.nodes.math.map_range(value=1.0 - occlusion.ao, from_min=0.1, from_max=0.45)
    breakup = pf.nodes.texture.noise(vector=vector, scale=1.5, detail=2.0, noise_dimensions="4D", w=seed + 17.0)
    patchy = pf.nodes.math.map_range(value=breakup.fac, from_min=0.3, from_max=0.6)
    return pf.nodes.math.clamp(cavity * patchy * dirt)


def paint_relief(vector, bump, bump_size):
    """A painted surface's orange peel, from infinigen2's paint with its splats, strokes and globules off."""
    return paint(vector=vector, bump_height=bump, bump_size=bump_size, splat_height=0.0, stroke_height=0.0,
                 globule_height=0.0).displacement


def brushed_relief(vector, bump, bump_size):
    """Bare steel's brushing streaks, from infinigen2's metal_brushed."""
    return metal_brushed(vector=vector, brush_size=bump_size, height_scale=bump).displacement


def rubber_relief(vector, bump, bump_size):
    """Rubber's fine grain, from infinigen2's plastic_black_rubberized."""
    return plastic_black_rubberized(vector=vector, noise_size=bump_size, noise_height=bump).displacement


def layered(top, under, wear_mask, dirt_colour, dirt_amount):
    """Paint `top` over `under` through the wear mask, then dirt over both: (colour, roughness, metal) triples in,
    the same triple out."""
    colour = pf.nodes.color.mix_rgb(factor=wear_mask, a=top[0], b=under[0])
    roughness = pf.nodes.math.mix(a=top[1], b=under[1], factor=wear_mask)
    metal = pf.nodes.math.mix(a=top[2], b=under[2], factor=wear_mask)
    colour = pf.nodes.color.mix_rgb(factor=dirt_amount, a=colour, b=dirt_colour)
    roughness = pf.nodes.math.mix(a=roughness, b=0.9, factor=dirt_amount)
    return colour, roughness, metal


def painted_metal(colour, bare, dirt_colour, roughness, bare_roughness, metal, bump, bump_size, edge_width,
                  breakup_scale, dirt_reach, wear, dirt, seed):
    """Paint on steel: worn through to bare steel on the edges, dirty in the cavities."""
    vector = coordinates()
    wear_mask = edge_wear_mask(vector, wear, edge_width, breakup_scale, seed)
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    base, rough, shine = layered((colour, roughness, metal), (bare, bare_roughness, 1.0), wear_mask, dirt_colour, dirty)
    chipped = pf.nodes.shader.displacement(height=wear_mask * -0.0004, midlevel=0.0)
    return Channels(base, rough, shine, BLACK, paint_relief(vector, bump, bump_size) + chipped)


def bare_metal(colour, dirt_colour, roughness, metal, bump, bump_size, dirt_reach, dirt, seed):
    """Unpainted steel, brushed, dirty in the cavities; nothing to wear through."""
    vector = coordinates()
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=dirty, a=colour, b=dirt_colour)
    rough = pf.nodes.math.mix(a=roughness, b=0.9, factor=dirty)
    return Channels(base, rough, metal, BLACK, brushed_relief(vector, bump, bump_size))


def rubber(colour, dirt_colour, roughness, bump, bump_size, dirt_reach, dirt, seed):
    """Black rubber with a fine grain, dusty in the cavities."""
    vector = coordinates()
    dirty = dirt_mask(vector, dirt, dirt_reach, seed)
    base = pf.nodes.color.mix_rgb(factor=dirty, a=colour, b=dirt_colour)
    return Channels(base, roughness, 0.0, BLACK, rubber_relief(vector, bump, bump_size))


def glass(colour, roughness):
    """Dark glass drawn as its own flat colour and a sharp shine."""
    return Channels(colour, roughness, 0.0, BLACK, None)


def glowing(colour, roughness):
    """A token colour given off as light: screens, lamp lenses."""
    return Channels(colour, roughness, 0.0, colour, None)


RECIPES = {"painted_metal": painted_metal, "bare_metal": bare_metal, "rubber": rubber, "glass": glass,
           "glowing": glowing}
# Where each recipe starts from, for the page and the paper (the coordinator, 2026-10-06).
SOURCES = {
    "painted_metal": "infinigen2 paint.py (relief, BSD-3) + edgewear.py's bevel test (ported, new threshold band)"
                     " + new dirt and layering",
    "bare_metal": "infinigen2 metal_brushed.py (relief, BSD-3) + new dirt",
    "rubber": "infinigen2 plastic.py plastic_black_rubberized (relief, BSD-3) + new dirt",
    "glass": "written new (infinigen2 glass_colored needs transmission, which the ink look cannot draw)",
    "glowing": "written new",
}
# The helpers each recipe is built of, for counting its lines of code.
PARTS = {
    "painted_metal": (painted_metal, coordinates, edge_wear_mask, dirt_mask, paint_relief, layered),
    "bare_metal": (bare_metal, coordinates, dirt_mask, brushed_relief),
    "rubber": (rubber, coordinates, dirt_mask, rubber_relief),
    "glass": (glass,),
    "glowing": (glowing,),
}


def arguments(spec, wear, dirt, seed):
    """The recipe's keyword arguments from a resolved library entry (library.py) and the place's wear and dirt."""
    given = dict(spec, wear=wear, dirt=dirt, seed=float(seed), colour=pf.Color(tuple(spec["colour"])),
                 bare=pf.Color(tuple(spec["bare"])), dirt_colour=pf.Color(tuple(spec["dirt_colour"])))
    wanted = inspect.signature(RECIPES[spec["recipe"]]).parameters
    return {name: given[name] for name in wanted}


def channels(spec, wear, dirt, seed):
    """One library material at one wear and dirt setting, as Channels."""
    return RECIPES[spec["recipe"]](**arguments(spec, wear, dirt, seed))


def settings_of(recipe):
    """A recipe's settings as ProcFunc's tracer sees them: traced with every argument left an input, the graph's
    inputs are the settings, and its node count says how big the recipe is."""
    from procfunc import compute_graph as graph_tools

    traced = pf.trace(RECIPES[recipe], trace_level=pf.tracer.TraceLevel.PRIMITIVES)
    names = list(traced.inputs.dict())
    nodes = sum(1 for _ in graph_tools.traverse_depth_first(traced))
    return {"settings": names, "nodes": nodes,
            "lines": sum(len(inspect.getsource(part).splitlines()) for part in PARTS[recipe])}


def shaded(found):
    """The Channels as a material to render: a principled surface over the relief."""
    glows = 1.0 if found.displacement is None and found.emission is not BLACK else 0.0
    emission = pf.Color(found.emission) if isinstance(found.emission, tuple) else found.emission
    surface = pf.nodes.shader.principled_bsdf(base_color=found.base_color, roughness=found.roughness,
                                              metallic=found.metallic, emission_color=emission,
                                              emission_strength=glows)
    return pf.Material(surface=surface, displacement=found.displacement)


def emitted(value):
    """One channel given off as light, for baking or scoring it exactly (a colour node, or a number as grey)."""
    if isinstance(value, (int, float)):
        value = pf.Color((float(value), float(value), float(value)))
    elif isinstance(value, tuple):
        value = pf.Color(value)
    return pf.Material(surface=pf.nodes.shader.emission(color=value, strength=1.0))
