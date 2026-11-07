"""The paint's colour gate on what the bake made (row surfaces-paint, gate "colour against the close-up"): every
baked model's surfaces are measured on the bake's own base colour map, each against its finish's colour in the
close-up, so a surface that bakes another colour than its close-up shows fails here, a batch gap of its take the
finish route can fix, never first at likeness.

Why: the gate compared each finish's library colour, its palette token, with the close-up
(finish_parts.checked_finishes) and never saw the bake. After the hub's surface library was remade (2026-11-05) the list gave its consoles
`rust_streaked_hull` (recipe rusted_metal, its `bare` rust brown, worn at the scene's wear): its token hull-grey lay
dE 10.5 from the right console's grey close-up and passed, while the bake laid rust over half of the console (48% of
its hull's area over OFF_AB off both its grey close-up and its grey token), its close-up showing none; likeness failed
it at 0.116 under 0.14. The check's own close-up comparison
(bake_check.close_up_faults) takes each channel's area median, which a half-rust half-grey surface keeps near grey on
L* and pulls only partway on a*b* (baked [45.4, 12.3, 18.5] against [46.1, 0.8, 2.4], dE 19.8 under 32).

The measure: each baked triangle named by the bake's own ray (bake_check.baked_surfaces), its colour the texel it was
baked into (baked_gltf.base_colours), as surfaces-check names them; per surface with a close-up colour
(bake_check.close_up_colours: glass, glow, lamp light, print and a coloured cover judged by their own colour, left
out), the share of its area whose a*b* lies over OFF_AB from its close-up's a*b* and from every colour its recipe
draws (bake_check.library_shades): what the bake laid over the library colour. A token itself off its close-up stays
the listed check's (judge_concept_colour, dE 32): the close-up's light moves saturated colours' chroma, and 81 of
world 1's 876 judged surfaces that check passed (hazard yellows, red cables, notes) have tokens over 20 a*b* off
their close-ups. Lightness is free:
the light lifts a right surface's L* by 15 to 30 (bake_check.CLOSE_UP_DELTA_E). A surface fails when over OFF_SHARE
of its area bakes so. OFF_AB and OFF_SHARE: see their comment.

The measure runs in the prop environment (trimesh, SciPy) inside the paint's make, written into painted.json per take
(`baked_colours`), so the batch gap's per-take judging (route_paint.item_findings) reads it with the rest.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS = HERE.parents[2] / "tools/props"
for folder in (HERE, PROPS, PROPS / "library"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import bake_check  # noqa: E402
import prop_env  # noqa: E402
import surface_gates as gates  # noqa: E402
from score import checks  # noqa: E402

GATE = "colour against the close-up"
FIELD = "baked_colours"
# A baked triangle is off when its a*b* lies over OFF_AB both from its close-up's and from every colour its recipe
# draws: the light keeps a right surface's hue and chroma within it (the hub's copper pipe baked 10 to 15 off its
# close-up), rust on grey paint lies 20 to 30 off. A surface fails when over OFF_SHARE of its area is off. Measured on
# world 1's 27 accepted bakes of 2026-11-07 (876 surfaces of PART_LEAST or more with a close-up colour, own-colour
# families left out): 485 are 0 off; 27 are over 0.4, every one a worn recipe's bare (21 rusted_metal, 5
# painted_metal, 1 painted_plaster) over a surface its close-up shows painted: the hub's rust_streaked_hull on its
# consoles, control bank, monitor and wall lamp at 0.40 to 0.85 (likeness failed the right console, 0.48 here, at
# 0.116 under 0.14), the tube's rusted_hull_plate on eight models, the stairwell's rusty_gate_steel on three; the next
# below, the hangar's lamp housing at 0.37 and the stairwell's meter box at 0.35, pass.
OFF_AB = 20.0
OFF_SHARE = 0.4


def measure_model(model, entry, bake, specs):
    """One baked model's surfaces against its close-up: {surface: {share, close_up, off}} (its share of the model, its
    close-up L*a*b*, the share of its area the bake moved off it: surface_offs) for each surface with a close-up colour,
    or {"unmeasured": why} when the bake left no base colour map; `specs`: the bake's specs.json."""
    import numpy as np
    import baked_gltf
    import labels
    made = bake / "made"
    labelled = bake / "labelled" / entry["parts"]
    geometry, maps = bake_check.gltf_model(made / f"{model}.gltf")
    if "base_color" in bake_check.map_roles(maps)[1]:
        return {"unmeasured": "no base_color map"}
    picture_colours, rows, columns, sizes = baked_gltf.base_colours(geometry, maps)
    colour = labels.lab(picture_colours)
    corners = geometry["positions"][geometry["triangles"]]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    names, surface, _ = bake_check.baked_surfaces(geometry, labelled, entry,
                                                  bake_check.sampled_points(geometry, rows, columns, sizes),
                                                  made / f"{model}.parts")
    return surface_offs(colour, areas, [names[index] for index in surface], bake_check.close_up_colours(labelled),
                        {name: bake_check.library_shades(specs[name]) for name in names if name in specs})


def surface_offs(colour, areas, named, close_up, shades):
    """Each surface's measure from its baked triangles (`colour` their L*a*b*, `areas`, `named` each one's surface;
    `close_up`: {surface: its close-up L*a*b*}; `shades`: {surface: the L*a*b* colours its recipe draws,
    bake_check.library_shades}): {surface: {share, close_up, off}} for each with a close-up colour, `off` the share of
    its area whose a*b* lies over OFF_AB both from its close-up's and from every colour its recipe draws: what the bake
    laid over the library colour (a worn surface's bare, rust) that the close-up does not show. A token itself off its
    close-up is the listed check's (place_line.judge_concept_colour, finish_parts.COLOUR_DELTA_E), not this one's."""
    import numpy as np
    named = np.asarray(named)
    found = {}
    for name in sorted(set(named.tolist()) & set(close_up)):
        chosen = named == name
        seen = colour[chosen][:, 1:]
        moved = np.linalg.norm(seen - np.asarray(close_up[name][1:]), axis=1) > OFF_AB
        for shade in shades.get(name, []):
            moved &= np.linalg.norm(seen - np.asarray(shade[1:]), axis=1) > OFF_AB
        found[name] = {"share": round(float(areas[chosen].sum() / areas.sum()), 4), "close_up": close_up[name],
                       "off": round(float(areas[chosen][moved].sum() / areas[chosen].sum()), 4)}
    return found


def measure_step(inputs, out):
    """The prop environment's side: each take's baked models measured (measure_model) into its painted.json report
    as `baked_colours` {model: its surfaces}, the bake's models found by their entry's take (`parts`)."""
    bake = inputs["bake"]
    baked = json.loads((bake / "baked.json").read_text())
    specs = json.loads((bake / "specs.json").read_text())
    painted = json.loads((out / "painted.json").read_text())
    for model, entry in sorted(baked.items()):
        report = painted["takes"].get(entry["parts"])
        if report is not None:
            report.setdefault(FIELD, {})[model] = measure_model(model, entry, bake, specs)
    (out / "painted.json").write_text(json.dumps(painted, indent=1))


def measured(inputs, out):
    """The paint's make's step: the baked models measured in the prop environment (measure_step)."""
    prop_env.handover(__file__, "measure", inputs, out)


def baked_faults(takes, families):
    """Each baked surface over OFF_SHARE off its close-up's colour, and each model left unmeasured, named by take and
    model; `families`: {surface: family} (the bake's specs), a surface of an own-colour family left out."""
    faults = []
    for take, report in sorted(takes.items()):
        for model, surfaces in sorted(report.get(FIELD, {}).items()):
            if "unmeasured" in surfaces:
                faults.append(f"{take}: {model} baked colour unmeasured ({surfaces['unmeasured']})")
                continue
            faults += [f"{take}: {model} {surface} bakes {entry['off']:.0%} of its area over {OFF_AB:.0f} a*b* off "
                       f"its close-up's {entry['close_up']}"
                       for surface, entry in sorted(surfaces.items())
                       if entry["share"] >= bake_check.PART_LEAST and entry["off"] > OFF_SHARE
                       and families.get(surface) not in bake_check.OWN_COLOUR]
    return faults


def judge_colour(output, inputs, evidence):
    """The paint's colour gate: every finish's library surface near its close-up colour (place_line's
    judge_concept_colour) and every baked surface baking it (baked_faults); a take the bake made models for that
    carries no measure cannot be told."""
    import place_line
    listed = place_line.judge_concept_colour(output, inputs, evidence)
    takes = json.loads((pathlib.Path(output) / "painted.json").read_text())["takes"]
    baked = json.loads((pathlib.Path(inputs["surfaces-bake"]) / "baked.json").read_text())
    unmeasured = sorted({entry["parts"] for entry in baked.values()
                         if entry["parts"] in takes and FIELD not in takes[entry["parts"]]})
    if unmeasured:
        return gates.unknown(GATE, f"cannot tell: no baked colour measured for {', '.join(unmeasured)}")
    specs = json.loads((pathlib.Path(inputs["surfaces-bake"]) / "specs.json").read_text())
    faults = baked_faults(takes, {name: spec.get("family") for name, spec in specs.items()})
    surfaces = sum(len(surfaces) for report in takes.values() for surfaces in report.get(FIELD, {}).values())
    failing = listed.measures["failing"] + len(faults)
    return checks.Verdict(GATE, checks.FAIL if failing else checks.PASS,
                          f"listed: {listed.reason}; baked: {len(faults)} of {surfaces} surfaces off their close-up",
                          {**listed.measures, "failing": failing, "baked off": len(faults)}, {"failing": "lower"},
                          (*listed.findings, *faults)[:40])


STEPS = {"measure": measure_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
