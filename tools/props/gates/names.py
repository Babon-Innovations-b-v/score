"""The name check (the coordinator, 2026-10-08): a piece's own name means one thing in every room. The library's
shared records are keyed by own name (fittings.json's parts seen, details.json, the builders), so a second room's
piece under a name another room already uses silently takes the first one's record: the camp's lamp on a rod, baked
as `pendant_lamp`, wrote its parts over the workshop's pendant lamp and broke main; the stairwell's code-built
`junction_box` nearly routed the lab's generated one to code. Run before install; a fault stops the install.

    ~/.farm-factory-props/env/bin/python tools/props/gates/names.py <game layout.json> <room>

It fails on a code-built model whose name reads as another thing's own name (the shared records read a model `<name>_<n>` as
`<name>`): `pendant_lamp_1` laid as `camp_rod_lamp`, where `pendant_lamp` is the workshop's kind, a fitting and a
builder (a model named for its place, `cable_run_1p28`, is not judged while nothing else is called `cable_run`); on an
own name
this room makes on one route that another room's installed layout (data/kit/*.json) made on the other (code here, a
generated model there), and on a builder defined twice in one builder module or in two (pieces.py and the Earth
rooms' modules beside it), where the later one silently replaces the first.
"""
import ast
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
INSIDE = REPO / "tools/props/library/inside"


def own_name(kind, room):
    """A kind's name without its room's prefix."""
    return kind[len(room) + 1:] if kind.startswith(f"{room}_") else kind.split("_", 1)[-1]


def model_own_name(model):
    """A model's own name: its name without its count (`pendant_lamp_1` -> `pendant_lamp`)."""
    return model.rsplit("_", 1)[0]


def routes(layout, room):
    """{own name: route} of every model a game layout lays (glowing and screen parts left out)."""
    found = {}
    for piece in layout["pieces"]:
        if "part" in piece:
            continue
        route = layout["models"].get(piece["model"], {}).get("route")
        if route:
            found.setdefault(own_name(piece["kind"], room), route)
    return found


def misnamed(layout, room, taken):
    """Faults: code-built models whose name reads as an own name in `taken` that is not their kind's (the fittings'
    parts-seen record reads a code build's model name, route.record_fittings)."""
    return sorted({f"{piece['model']} is laid as {piece['kind']}, but {model_own_name(piece['model'])} is another "
                   f"thing's name: a model takes its kind's own name"
                   for piece in layout["pieces"] if "part" not in piece
                   and layout["models"].get(piece["model"], {}).get("route") == "code"
                   and model_own_name(piece["model"]) != own_name(piece["kind"], room)
                   and model_own_name(piece["model"]) in taken})


def taken_names(others, texts, fittings):
    """Every own name already meaning something: other rooms' kinds, the fittings and the builders."""
    found = set(fittings)
    for other, laid in others.items():
        found |= {own_name(piece["kind"], other) for piece in laid["pieces"] if "part" not in piece}
    for text in texts.values():
        listed = text[text.index("BUILDERS = "):] if "BUILDERS = " in text else ""
        found |= set(re.findall(r'"(\w+)"', listed))
    return found


def crossed(layout, room, others):
    """Faults: own names this room makes on one route and another room on the other. `others`: {room: layout}."""
    mine = routes(layout, room)
    found = []
    for other, laid in sorted(others.items()):
        for name, route in sorted(routes(laid, other).items()):
            if name in mine and mine[name] != route:
                found.append(f"{name} is {mine[name]} here and {route} in {other}: give one of them its own name")
    return found


def twice_defined(texts):
    """Faults: a function defined twice in one module, or a builder named in two modules. `texts`: {module: text}."""
    found = []
    builders = {}
    for module, text in texts.items():
        names = [node.name for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)]
        found += [f"{module}: {name} is defined twice" for name in sorted({name for name in names
                                                                           if names.count(name) > 1})]
        listed = text[text.index("BUILDERS = "):] if "BUILDERS = " in text else ""
        listed = listed[:listed.index("EARTH_ROOMS")] if "EARTH_ROOMS" in listed else listed
        for name in set(re.findall(r'"(\w+)"', listed)) & set(names):
            builders.setdefault(name, []).append(module)
    found += [f"builder {name} is in {' and '.join(sorted(modules))}" for name, modules in sorted(builders.items())
              if len(modules) > 1]
    return found


def builder_texts():
    """{module: its text} of pieces.py and the Earth rooms' builder modules it names (`EARTH_ROOMS`)."""
    texts = {"pieces": (INSIDE / "pieces.py").read_text()}
    named = re.search(r"EARTH_ROOMS = \(([^)]*)\)", texts["pieces"])
    for name in re.findall(r'"(\w+)"', named.group(1)) if named else []:
        texts[name] = (INSIDE / f"{name}.py").read_text()
    return texts


def installed(but):
    """{room: its game layout} of every kit room installed in the game but `but`."""
    return {path.stem: json.loads(path.read_text()) for path in sorted((REPO / "data/kit").glob("*.json"))
            if path.stem != but}


def fittings_names():
    """The fittings' own names (data/library/fittings.json)."""
    return set(json.loads((REPO / "data/library/fittings.json").read_text())["fittings"])


def check(layout, room, others=None, texts=None, fittings=None):
    """Every fault: [text]."""
    others = installed(room) if others is None else others
    texts = builder_texts() if texts is None else texts
    fittings = fittings_names() if fittings is None else fittings
    return (misnamed(layout, room, taken_names(others, texts, fittings)) + crossed(layout, room, others)
            + twice_defined(texts))


def main():
    layout = json.loads(pathlib.Path(sys.argv[1]).read_text())
    faults = check(layout, sys.argv[2])
    for fault in faults:
        print(fault)
    print(len(faults), "name faults")
    if faults:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
