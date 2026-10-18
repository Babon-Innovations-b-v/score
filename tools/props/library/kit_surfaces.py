"""The library surfaces a room's code-built kit is made of, read from the builders' code without Blender: every
library variant named in a builder of a kit piece the room lays on the code route (data/kit/<room>.json), or in any
function of the builders' modules it calls, however deep. A variant a builder takes only from its laid data is not
seen here.

    surfaces("hangar")  -> ["bare_steel", "dark_panel", "deck", ...]

The paint takes these first (score/stages/surfaces/finish_parts.py kit_taken): a prop's finish that one of the room's
own kit surfaces fits within the colour check's tolerance takes the kit's, so a prop and the walls round it are one
paint (the materials audit, 2026-10-18: props given surfaces the kit never uses).
"""
import ast
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
KITS = REPO / "data/kit"
LIBRARY = REPO / "data/library/materials.json"
# The builders' modules (inside/pieces.py and the modules it takes builders from) and the shapes they are made of.
MODULES = ("pieces.py", "pieces_earth.py", "pieces_ship.py", "shapes.py")


def variant_names():
    library = json.loads(LIBRARY.read_text())
    return {name for family in library["families"].values() for name in family.get("variants", {})}


def builder_functions():
    """{function name: its syntax tree} of every module-level function of the builders' modules (the first module
    to define a name keeps it)."""
    found = {}
    for module in MODULES:
        for node in ast.parse((HERE / "inside" / module).read_text()).body:
            if isinstance(node, ast.FunctionDef):
                found.setdefault(node.name, node)
    return found


def called_name(call):
    """The plain name a call calls (`box(...)` or `shapes.box(...)`), or None."""
    if isinstance(call.func, ast.Name):
        return call.func.id
    return call.func.attr if isinstance(call.func, ast.Attribute) else None


def named_in(name, functions, names, seen):
    """The library variants function `name` names, and every function it calls names."""
    if name in seen or name not in functions:
        return set()
    seen.add(name)
    found = set()
    for node in ast.walk(functions[name]):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in names:
            found.add(node.value)
        elif isinstance(node, ast.Call) and called_name(node):
            found |= named_in(called_name(node), functions, names, seen)
    return found


def code_kinds(room):
    """The builders of the kit pieces the room lays on the code route (a kind without its room's prefix)."""
    path = KITS / f"{room}.json"
    if not path.exists():
        return []
    kit = json.loads(path.read_text())
    return sorted({piece["kind"].split("_", 1)[1] for piece in kit.get("pieces", [])
                   if kit.get("models", {}).get(piece.get("model"), {}).get("route") == "code"})


def surfaces(room):
    """The library surfaces the room's code-built kit is made of, sorted."""
    functions = builder_functions()
    names = variant_names()
    found = set()
    for kind in code_kinds(room):
        found |= named_in(kind, functions, names, set())
    return sorted(found)
