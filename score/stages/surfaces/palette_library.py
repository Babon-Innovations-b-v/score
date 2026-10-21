"""The library as a scene's palette offers it (owner, 2026-10-21: every scene made from its design alone; every old
material retired, the library starts empty). A scene's surfaces are its own surface library, made fresh from its
design by the `surface-library` row (scene_library.py: materials.json in its output, in its scene palette's tokens),
never a hand-kept list in data/definitions/place.json and never the retired base theme. The finish route's rows read
the scene palette (scene_palette.py, `palette.json`: read from its locked concept) and that library together.

    palette = {"tokens": {token: "#rrggbb", ...}, "wear": {"level": <a wear level>, "dirt": 0..1, "dirt_token": token},
               "library": <the scene library's materials.json, when the row reads one>}

    read(inputs)                  the scene palette of a row's inputs, with its scene library's path
    scene_library(palette)        the scene library (LibraryEmpty, named, when the row reads none or it is empty)
    library_tokens(palette)       {token: linear RGB} of the scene library's tokens
    specs(palette)                every variant in its own token, dirtied in the scene's dirt token (the bake's, the
                                  check's)
    offered(palette)              the surfaces a scene's models may take: every variant in one of its palette tokens
    take_surfaces(entry, palette) a take's: offered, less what an object never is, its kind's own list on top
    wear(palette)                 (wear, dirt) as numbers

Standard library only: the prop environment and the framework both read it.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LIBRARY_TOOLS = HERE.parents[2] / "tools/props/library"
if str(LIBRARY_TOOLS) not in sys.path:
    sys.path.append(str(LIBRARY_TOOLS))

import library  # noqa: E402

ROW = "surface-library"  # the row whose output is a scene's surface library (scene_library.py)
# What an object is never painted as (labels.NOT_ON_OBJECTS): the floor's deck plates.
NOT_ON_OBJECTS = ("deck",)


def read(inputs):
    """The scene palette of a row's inputs (palette.json of its `finish-route-palette` input), with the path of its
    scene library (`library`: materials.json of its `surface-library` input) when the row reads one."""
    palette = json.loads((pathlib.Path(inputs["finish-route-palette"]) / "palette.json").read_text())
    if ROW in inputs:
        palette["library"] = str(pathlib.Path(inputs[ROW]) / "materials.json")
    return palette


def scene_library(palette):
    """The scene's surface library; LibraryEmpty when the row reads none or it holds no variant."""
    if "library" not in palette:
        raise library.LibraryEmpty(library.EMPTY)
    found = library.theme_library(palette["library"])
    if not library.variants(found):
        raise library.LibraryEmpty(f"{palette['library']} holds no surface: {library.EMPTY}")
    return found


def library_tokens(palette):
    """{token: linear RGB} of the scene library's palette tokens, sorted by name."""
    every = library.token_colours(scene_library(palette))
    return {token: every[token] for token in sorted(every)}


def specs(palette):
    """Every variant in its own token, dirtied in the scene's dirt token (else the library's)."""
    scene_library(palette)
    return library.library_specs(palette["library"], dirt=palette["wear"].get("dirt_token"))


def offered(palette):
    """Every variant whose own token is one of the scene's palette tokens, as specs gives it."""
    tokens = set(palette["tokens"])
    return {name: spec for name, spec in specs(palette).items() if spec["token"] in tokens}


def kind_list(kind, palette):
    """The variants the scene library made for a kind as its own (its `kinds`), [] when it names none."""
    return list((scene_library(palette).get("kinds") or {}).get(kind) or []) if kind else []


def take_surfaces(entry, palette):
    """Every library surface a take may take: the palette's offer less what an object never is, and its kind's own
    variants on top (in their own token: a kind's list names what such an object is made of)."""
    every = specs(palette)
    found = {name: spec for name, spec in offered(palette).items() if name not in NOT_ON_OBJECTS}
    found.update({name: every[name] for name in kind_list(entry.get("kind"), palette) if name in every})
    return found


def wear(palette):
    """The scene's (wear, dirt) as numbers: its level by the library's wear levels, its dirt as read."""
    levels = library.theme_library(palette.get("library", library.LIBRARY))["wear_levels"]
    return float(levels[palette["wear"]["level"]]), float(palette["wear"]["dirt"])
