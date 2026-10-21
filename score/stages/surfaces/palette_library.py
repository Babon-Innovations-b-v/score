"""The library as a scene's palette offers it (owner, 2026-10-21: every scene made from its design alone): the finish
route's rows read a scene's palette tokens and wear from its scene palette (scene_palette.py, `palette.json`: read from
its locked concept), never from a hand-kept list in data/definitions/place.json.

    palette = {"tokens": [token, ...], "wear": {"level": <a library wear level>, "dirt": 0..1, "dirt_token": token}}

    offered(palette)              the surfaces a scene's models may take: every variant whose own token is one of its
    take_surfaces(entry, palette) a take's: offered, less what an object never is, its kind's own list on top
    specs(palette)                every variant in its own token, dirtied in the scene's dirt token (the bake's, the
                                  check's)
    wear(palette)                 (wear, dirt) as numbers
    library_tokens()              {token: linear RGB} of every token the library's variants are drawn in
    read(inputs)                  the scene palette of a row's inputs

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

DETAILS = library.REPO / "data/library/details.json"
# What an object is never painted as (labels.NOT_ON_OBJECTS): the floor's deck plates.
NOT_ON_OBJECTS = ("deck",)


def library_tokens():
    """{token: linear RGB} of the palette tokens the library's variants are drawn in, sorted by name."""
    every = library.token_colours()
    used = {variant["token"] for variant in library.variants(library.theme_library()).values()}
    return {token: every[token] for token in sorted(used) if token in every}


def specs(palette):
    """Every variant in its own token, dirtied in the scene's dirt token (else the library's)."""
    return library.library_specs(dirt=palette["wear"].get("dirt_token"))


def offered(palette):
    """Every variant whose own token is one of the scene's palette tokens, as specs gives it."""
    tokens = set(palette["tokens"])
    return {name: spec for name, spec in specs(palette).items() if spec["token"] in tokens}


def kind_list(kind):
    """The library variants a kind names as its own (details.json `materials`), [] when it names none."""
    found = json.loads(DETAILS.read_text()).get(kind, {}) if kind else {}
    return list(found.get("materials") or []) if isinstance(found, dict) else []


def take_surfaces(entry, palette):
    """Every library surface a take may take: the palette's offer less what an object never is, and its kind's own
    variants on top (in their own token: a kind's list names what such an object is made of)."""
    every = specs(palette)
    found = {name: spec for name, spec in offered(palette).items() if name not in NOT_ON_OBJECTS}
    found.update({name: every[name] for name in kind_list(entry.get("kind")) if name in every})
    return found


def wear(palette):
    """The scene's (wear, dirt) as numbers: its level by the library's wear levels, its dirt as read."""
    return float(library.theme_library()["wear_levels"][palette["wear"]["level"]]), float(palette["wear"]["dirt"])


def read(inputs):
    """The scene palette of a row's inputs: palette.json of its `finish-route-palette` input."""
    return json.loads((pathlib.Path(inputs["finish-route-palette"]) / "palette.json").read_text())
