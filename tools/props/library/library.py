"""The surface library's loader. data/library/materials.json holds the method alone (owner, 2026-10-21, every old
material retired: "a chance of contaminating with old is not worth it"): the wear levels and each ProcFunc recipe's
(recipes.py) default settings, no families, tokens or pictures. A scene's surfaces are made fresh from its design by
the `surface-library` row (score/stages/surfaces/scene_library.py): a materials.json of the same form in its output,
its families of variants (each a recipe name, a token and its settings over the recipe's defaults) and its own
palette tokens ({name: "#rrggbb"}, read off its locked concept by its scene palette). The kit routes' place takes
variants by name in its own `materials` (data/definitions/place.json).

    python3 tools/props/library/library.py <place>            # the place's resolved materials as JSON
    python3 tools/props/library/library.py --list             # every family and variant
    ... [--verbose]    # print the whole output; without it one summary line, the output written under OUTPUT

Shape and material are kept apart (the robust route): a model or a code-built piece only names, per part, which
library variant it is; colours come only from the library's own palette tokens, never a picture's photo texture. A
surface or token the library lacks answers LibraryEmpty, a missing input named ("surface library empty: run
surface-library first"), never a KeyError; a lookup of every variant finds none. Standard library only: the Blender side (inside/) and the tools both read this.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"
LIBRARY = REPO / "data/library/materials.json"
PICTURES = REPO / "data/library/pictures"
EMPTY = "surface library empty: run surface-library first"
# Settings that name a palette token rather than hold a number.
COLOUR_SETTINGS = ("bare", "second")
# Where the command line writes its whole output; the summary line it prints names the file.
OUTPUT = pathlib.Path("/tmp/score-output")


class LibraryEmpty(FileNotFoundError):
    """The surface library holds no variant, or not the one asked for: a missing input, named, so a gate reading it
    answers unknown and a row refuses before it spends."""


def token_colours(library):
    """Every palette token of a library (its `tokens`, {name: "#rrggbb"}, its scene palette's), as linear RGB."""
    return {name: linear(value) for name, value in (library.get("tokens") or {}).items()}


def linear(hex_colour):
    """A #rrggbb colour as linear RGB, the way a renderer mixes it."""
    channels = [int(hex_colour.lstrip("#")[at:at + 2], 16) / 255 for at in (0, 2, 4)]
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]


def theme_library(path=LIBRARY):
    """A surface library: its wear levels, recipes' defaults, and (a scene's) families, tokens, dirt and pictures."""
    return json.loads(pathlib.Path(path).read_text())


def variants(library):
    """Every variant by name, its family named in it; none for the method's library (a lookup then finds no surface,
    and spec names the missing input)."""
    found = {}
    for family, entry in library["families"].items():
        for name, variant in entry["variants"].items():
            if name in found:
                raise SystemExit(f"the library names '{name}' twice (in {found[name]['family']} and {family})")
            found[name] = dict(variant, family=family)
    return found


def wear_of(place_id, path=PLACES, library_path=LIBRARY):
    """A place's wear and dirt as numbers: (wear, dirt), from its named wear level; refused by name for a place
    place.json holds no wear for (the per-place wear was retired on 2026-10-21: a scene's wear is its scene palette's,
    score/stages/surfaces/scene_palette.py)."""
    chosen = json.loads(pathlib.Path(path).read_text()).get(place_id, {}).get("wear")
    if chosen is None:
        raise LibraryEmpty(f"{place_id}: no wear in {path} (per-place wear retired 2026-10-21; a scene's wear is its "
                           "scene palette's)")
    return float(theme_library(library_path)["wear_levels"][chosen["level"]]), float(chosen["dirt"])


def dirt_token_of(place_id, path=PLACES):
    """The token a place's dirt is drawn in: its own (`wear.dirt_token`, Mars's dust on the camp, 2026-10-07), else
    none and the library's (a place place.json holds no wear for: the per-place wear was retired on 2026-10-21)."""
    return (json.loads(pathlib.Path(path).read_text()).get(place_id, {}).get("wear") or {}).get("dirt_token")


def spec(library, name, token, colours, dirt=None):
    """One library variant in a given token colour, as its recipe wants it: the recipe's defaults under the
    variant's own settings, every token setting as a linear colour, its picture as a file; its dirt in the place's
    dirt token (`dirt`), else the library's, else its own token. A variant or token the library lacks is
    LibraryEmpty."""
    every = variants(library)
    dirt = dirt or library.get("dirt") or token
    missing = [what for what, absent in ((f"surface {name}", name not in every),
                                         (f"token {token}", token not in colours),
                                         (f"dirt token {dirt}", dirt not in colours)) if absent]
    if missing:
        raise LibraryEmpty(f"{' and '.join(missing)} not in the surface library ({EMPTY})")
    variant = every[name]
    found = dict(library["recipes"][variant["recipe"]])
    found.update(variant)
    found.update(library=name, token=token, colour=colours[token], dirt_colour=colours[dirt])
    for setting in COLOUR_SETTINGS:
        if setting in found:
            found[setting] = colours[found[setting]]
    if "picture" in found:
        found["image"] = str(PICTURES / f"{found['picture']}.png")
    return found


def library_specs(library_path=LIBRARY, dirt=None):
    """Every variant in its own default token: the swatch sheet's rows (dirty in `dirt`'s token, else the library's)."""
    library = theme_library(library_path)
    colours = token_colours(library)
    return {name: spec(library, name, variant["token"], colours, dirt) for name, variant in variants(library).items()}


def resolved(place_id, path=PLACES, library_path=LIBRARY):
    """A place's materials that take a library variant, each as its full spec in the place's token; none while the
    library holds no variant (every old one retired, 2026-10-21: a place's old `materials` take nothing, and a reader
    that needs a surface names it missing)."""
    library = theme_library(library_path)
    if not variants(library):
        return {}
    colours = token_colours(library)
    found = {}
    dirt = dirt_token_of(place_id, path)
    for name, entry in json.loads(pathlib.Path(path).read_text()).get(place_id, {}).get("materials", {}).items():
        if "library" in entry:
            found[name] = spec(library, entry["library"], entry["token"], colours, dirt)
    return found


def by_library(place_id, path=PLACES, library_path=LIBRARY):
    """Every library variant keyed by its own name, in the place's token where the place names it (the first of the
    place's materials taking it) and in the library's own otherwise: what a code-built piece's slots, which name
    library variants, are painted with in that place."""
    found = library_specs(library_path, dirt_token_of(place_id, path))
    for entry in reversed(list(resolved(place_id, path, library_path).values())):
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
    try:
        if arguments == ["--list"]:
            library = theme_library()
            text = list_text(library)
            if verbose:
                print(text, end="")
            else:
                print(list_summary(library, write_output("library-list.txt", text)))
            return
        found = place_found(arguments[0])
    except LibraryEmpty as empty:
        raise SystemExit(f"library: {empty}")
    text = json.dumps(found, indent=1) + "\n"
    if verbose:
        print(text, end="")
        return
    print(place_summary(arguments[0], found, write_output(f"library-{arguments[0]}.json", text)))


if __name__ == "__main__":
    main()
