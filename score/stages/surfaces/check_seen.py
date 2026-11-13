"""surfaces-check's make with a ship place's view distance: route_check.make_check, given a kit laid from its own
scene record. bake_check.seen_degrees sizes a model from the kit it reads, and the old kits were retired on
2026-10-21, so every ship model's view distance was none and the one-look check named it unknown (shiplock's sliding
door, 2026-11-11: "no view distance"). The kit laid here is each scene-record object that names its bake, at its spot,
sized as its bake made it (baked.json). Its gate "baked matches its surfaces" (judge_lit, its batch gaps too) judges a
surface of the scene library's `glowing` recipe by its own colour whatever family the library coined. Its own module, set on the row in the table (stages.bake_checked), so no row
reading bake_check.py (the people's, the crops') moves for it.
"""
import contextlib
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import route_check  # noqa: E402
import surface_gates  # noqa: E402


def make_check(inputs, out, seed, params):
    """route_check.make_check, with `kit` (laid_kit) beside a scene record its inputs carry, and its batch gaps judged
    by the row's own gates (lit_gates: this module's judge_lit)."""
    with lit_gates():
        scene = inputs.get("scene record")
        if scene is None or not pathlib.Path(scene).is_file() or "kit" in inputs:
            return route_check.make_check(inputs, out, seed, params)
        baked = json.loads((pathlib.Path(inputs["surfaces-bake"]) / "baked.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            kit = pathlib.Path(temporary) / "kit.json"
            kit.write_text(json.dumps(laid_kit(json.loads(pathlib.Path(scene).read_text()), baked)))
            return route_check.make_check(dict(inputs, kit=kit), out, seed, params)


@contextlib.contextmanager
def lit_gates():
    """route_check.check_gates with "baked matches its surfaces" judged by judge_lit while the block runs, so the
    batch gaps the make writes are the gate's as the table sets it (stages.bake_checked)."""
    gates = route_check.check_gates

    def held():
        return tuple(surface_gates.guarded(check.name, judge_lit) if check.name == "baked matches its surfaces"
                     else check for check in gates())
    route_check.check_gates = held
    try:
        yield
    finally:
        route_check.check_gates = gates


def laid_kit(record, baked):
    """A kit of the scene record's objects (bake_check.seen_degrees' `pieces`): each top-level object whose bake the
    bake made, at its spot, in its baked size."""
    return {"pieces": [{"model": entry["bake"], "at": entry["at"], "size": baked[entry["bake"]]["size"]}
                       for entry in record.get("objects", [])
                       if entry.get("bake") in baked and isinstance(entry.get("at"), list) and len(entry["at"]) == 3
                       and "size" in baked[entry["bake"]]]}


def judge_lit(output, inputs, evidence):
    """bake_check.judge_lit with each surface the scene library makes with its `glowing` recipe judged by its own
    colour, as a light's family is (bake_check.OWN_COLOUR, SEEN_THROUGH), whatever family the library coined for it.
    The engine room's core glow, family "energy", baked its reactor blue and failed against its close-up's white-hot
    column (dE 55.7, 2026-11-13): a glow's close-up shows the light it gives, not its colour (owner, #8)."""
    import bake_check
    glowing = glowing_surfaces(inputs)
    found = json.loads((pathlib.Path(output) / "checks.json").read_text())
    failing = []
    for name, record in found.items():
        failing += [f"{name}: no {role} map" for role in record["missing_maps"]]
        failing += bake_check.surface_faults(name, lit_as_light(record, glowing))
    return surface_gates.verdict("baked matches its surfaces", failing, len(found), "faults over the models")


def glowing_surfaces(inputs):
    """The scene library's variants made with its `glowing` recipe, for a row that reads a scene palette and library;
    none for one that reads no library."""
    import palette_library
    if palette_library.ROW not in inputs or "finish-route-palette" not in inputs:
        return set()
    return {name for name, spec in palette_library.specs(palette_library.read(inputs)).items()
            if spec.get("recipe") == "glowing"}


def lit_as_light(record, glowing):
    """A checked model's record with each surface baked from a `glowing` variant (by the name it bakes as,
    route_settings.settings_name: its variant before the separator) counted in a light's family."""
    import route_settings
    surfaces = {surface: dict(entry, family="light") if surface.split(route_settings.SEPARATOR)[0] in glowing
                else entry for surface, entry in record["surfaces"].items()}
    return {**record, "surfaces": surfaces}
