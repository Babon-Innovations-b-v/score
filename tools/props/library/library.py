"""The base theme's material library, read from data/library/materials.json (job robust-exp, 2026-10-06): families
of variants, each a ProcFunc recipe (recipes.py) with its settings, which every place of the theme takes by name in
its own `materials` (data/definitions/place.json), with its own palette token where it differs and its own wear level.

    python3 tools/props/library/library.py <place>            # the place's resolved materials as JSON
    python3 tools/props/library/library.py --list             # every family and variant
    ... [--verbose]    # print the whole output; without it one summary line, the output written under OUTPUT

Shape and material are kept apart (the robust route): a model or a code-built piece only names, per part, which
library variant it is; colours come only from palette tokens (design/tokens/tokens.json), so two rooms of the theme
cannot drift apart and no picture's photo texture reaches the game. The library only grows: a room adds variants,
and never edits one another room already uses. Standard library only: the Blender side (inside/) and the tools both
read this.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"
LIBRARY = REPO / "data/library/materials.json"
PICTURES = REPO / "data/library/pictures"
TOKENS = REPO / "design/tokens/tokens.json"
# Settings that name a palette token rather than hold a number.
COLOUR_SETTINGS = ("bare", "second")
# Where the command line writes its whole output; the summary line it prints names the file.
OUTPUT = pathlib.Path("/tmp/score-output")


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


def theme_library(path=LIBRARY):
    """The base theme's library: its wear levels, dirt token, recipes' defaults, families and pictures."""
    return json.loads(pathlib.Path(path).read_text())


def variants(library):
    """Every variant by name, its family named in it."""
    found = {}
    for family, entry in library["families"].items():
        for name, variant in entry["variants"].items():
            if name in found:
                raise SystemExit(f"the library names '{name}' twice (in {found[name]['family']} and {family})")
            found[name] = dict(variant, family=family)
    return found


def wear_of(place_id, path=PLACES, library_path=LIBRARY):
    """A place's wear and dirt as numbers: (wear, dirt), from its named wear level."""
    chosen = json.loads(pathlib.Path(path).read_text())[place_id]["wear"]
    return float(theme_library(library_path)["wear_levels"][chosen["level"]]), float(chosen["dirt"])


def dirt_token_of(place_id, path=PLACES):
    """The token a place's dirt is drawn in: its own (`wear.dirt_token`, Mars's dust on the camp, 2026-10-07), else
    none and the library's."""
    return json.loads(pathlib.Path(path).read_text())[place_id]["wear"].get("dirt_token")


def spec(library, name, token, colours, dirt=None):
    """One library variant in a given token colour, as its recipe wants it: the recipe's defaults under the
    variant's own settings, every token setting as a linear colour, its picture as a file; its dirt in the place's
    dirt token (`dirt`) or the library's."""
    variant = variants(library)[name]
    found = dict(library["recipes"][variant["recipe"]])
    found.update(variant)
    found.update(library=name, token=token, colour=colours[token], dirt_colour=colours[dirt or library["dirt"]])
    for setting in COLOUR_SETTINGS:
        if setting in found:
            found[setting] = colours[found[setting]]
    if "picture" in found:
        found["image"] = str(PICTURES / f"{found['picture']}.png")
    return found


def library_specs(library_path=LIBRARY, tokens_path=TOKENS, dirt=None):
    """Every variant in its own default token: the swatch sheet's rows (dirty in `dirt`'s token, else the library's)."""
    library = theme_library(library_path)
    colours = token_colours(tokens_path)
    return {name: spec(library, name, variant["token"], colours, dirt) for name, variant in variants(library).items()}


def resolved(place_id, path=PLACES, library_path=LIBRARY, tokens_path=TOKENS):
    """A place's materials that take a library variant, each as its full spec in the place's token."""
    library = theme_library(library_path)
    colours = token_colours(tokens_path)
    found = {}
    dirt = dirt_token_of(place_id, path)
    for name, entry in json.loads(pathlib.Path(path).read_text())[place_id]["materials"].items():
        if "library" in entry:
            found[name] = spec(library, entry["library"], entry["token"], colours, dirt)
    return found


def by_library(place_id, path=PLACES, library_path=LIBRARY, tokens_path=TOKENS):
    """Every library variant keyed by its own name, in the place's token where the place names it (the first of the
    place's materials taking it) and in the library's own otherwise: what a code-built piece's slots, which name
    library variants, are painted with in that place."""
    found = library_specs(library_path, tokens_path, dirt_token_of(place_id, path))
    for entry in reversed(list(resolved(place_id, path, library_path, tokens_path).values())):
        found[entry["library"]] = entry
    return found


def list_text(library):
    """Every family and its variants, a line each, then the count of variants."""
    lines = [f"{family}: {', '.join(entry['variants'])}" for family, entry in library["families"].items()]
    return "\n".join(lines + [f"{len(variants(library))} variants"]) + "\n"


def list_summary(library, path):
    """The list in one line: its families and variants, and the file holding it."""
    return f"library: {len(library['families'])} families, {len(variants(library))} variants; list: {path}"


def place_found(place_id):
    """A place's wear and its resolved library materials, as the command line shows them."""
    return {"wear": wear_of(place_id), "materials": resolved(place_id)}


def place_summary(place_id, found, path):
    """A place's materials in one line: how many take a library variant, its wear and dirt, and the JSON file."""
    wear, dirt = found["wear"]
    used = {entry["library"] for entry in found["materials"].values()}
    return (f"library {place_id}: {len(found['materials'])} materials on {len(used)} library variants, wear {wear}, "
            f"dirt {dirt}; JSON: {path}")


def write_output(name, text):
    """Write the command line's whole output to OUTPUT/<name>; return the path."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    path.write_text(text)
    return path


def main():
    verbose = "--verbose" in sys.argv[1:]
    arguments = [argument for argument in sys.argv[1:] if argument != "--verbose"]
    if len(arguments) != 1:
        raise SystemExit(__doc__)
    if arguments == ["--list"]:
        library = theme_library()
        text = list_text(library)
        if verbose:
            print(text, end="")
        else:
            print(list_summary(library, write_output("library-list.txt", text)))
        return
    found = place_found(arguments[0])
    text = json.dumps(found, indent=1) + "\n"
    if verbose:
        print(text, end="")
        return
    print(place_summary(arguments[0], found, write_output(f"library-{arguments[0]}.json", text)))


if __name__ == "__main__":
    main()
