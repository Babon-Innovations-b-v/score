"""The theme's material library, read from data/definitions/place.json (job robust-exp, 2026-10-06): one set of
rule-based materials for the base theme (`shared.theme.library`), which every place of the theme takes by name in its
own `materials`, with its own palette token where it differs and its own wear level.

    python3 tools/props/library/library.py <place>            # print the place's resolved materials as JSON

Shape and material are kept apart (the robust route): a model or a code-built piece only names, per part, which
library material it is; the material itself is a ProcFunc recipe (recipes.py) with its settings here, coloured only
from palette tokens (design/tokens/tokens.json), so two rooms of the theme cannot drift apart and no picture's photo
texture reaches the game. Standard library only: the Blender side (inside/) and the tools both read this.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"
TOKENS = REPO / "design/tokens/tokens.json"
# Settings every library material has, so a recipe never reads a missing one.
SETTINGS = ("roughness", "metal", "bump", "bump_size", "edge_width", "breakup_scale", "dirt_reach", "bare_roughness")


def token_colours(path=TOKENS):
    """Every palette token's colour in the game's look (the `ops` theme), as linear RGB."""
    found = {}
    for token in json.loads(pathlib.Path(path).read_text())["color"]["tokens"]:
        value = token["value"]
        found[token["name"]] = linear(value["ops"] if isinstance(value, dict) else value)
    return found


def linear(hex_colour):
    """A #rrggbb colour as linear RGB, the way a renderer mixes it."""
    channels = [int(hex_colour.lstrip("#")[at:at + 2], 16) / 255 for at in (0, 2, 4)]
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]


def theme_library(path=PLACES):
    """The base theme's library block: its wear levels, dirt token and materials."""
    return json.loads(pathlib.Path(path).read_text())["shared"]["theme"]["library"]


def wear_of(place_id, path=PLACES):
    """A place's wear and dirt as numbers: (wear, dirt), from its named wear level."""
    places = json.loads(pathlib.Path(path).read_text())
    chosen = places[place_id]["wear"]
    return float(theme_library(path)["wear_levels"][chosen["level"]]), float(chosen["dirt"])


def resolved(place_id, path=PLACES, tokens_path=TOKENS):
    """A place's materials that take a library material, each as the recipe's full spec: the library entry's
    settings, the place's token (or the library's) as a linear colour, its bare metal and dirt colours."""
    places = json.loads(pathlib.Path(path).read_text())
    library = theme_library(path)
    colours = token_colours(tokens_path)
    found = {}
    for name, entry in places[place_id]["materials"].items():
        if "library" not in entry:
            continue
        found[name] = spec(library, entry["library"], entry["token"], colours)
    return found


def by_library(place_id, path=PLACES, tokens_path=TOKENS):
    """A place's materials keyed by the library material they take, in the place's own token (the first of the
    place's materials naming it): what a code-built piece's slots, which name library materials, are painted with
    in that place. A library material the place does not name keeps the library's own token."""
    found = library_specs(path, tokens_path)
    for entry in reversed(list(resolved(place_id, path, tokens_path).values())):
        found[entry["library"]] = entry
    return found


def spec(library, material, token, colours):
    """One library material in a given token colour, every setting filled in."""
    entry = library["materials"][material]
    missing = [name for name in SETTINGS if name not in entry]
    if missing:
        raise SystemExit(f"library material '{material}' has no {', '.join(missing)} in place.json")
    found = {name: entry[name] for name in SETTINGS}
    found.update(recipe=entry["recipe"], library=material, token=token, colour=colours[token],
                 bare=colours[entry.get("bare", "steel")], dirt_colour=colours[library["dirt"]],
                 wears=entry.get("wears", True), dirt_share=entry.get("dirt_share", 1.0),
                 reference=entry.get("reference"))
    return found


def library_specs(path=PLACES, tokens_path=TOKENS):
    """Every library material in its own default token: the swatch sheet's rows."""
    library = theme_library(path)
    colours = token_colours(tokens_path)
    return {name: spec(library, name, entry["token"], colours) for name, entry in library["materials"].items()}


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(json.dumps({"wear": wear_of(sys.argv[1]), "materials": resolved(sys.argv[1])}, indent=1))


if __name__ == "__main__":
    main()
