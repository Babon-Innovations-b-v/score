"""A character maker spec: what one make is asked for, read from data/characters/makes/<name>.json and checked before
anything is rented. Paths are absolute or start from ~ (the creator's own pictures stay outside the repo).

    {"name": "nev_rebuild", "kind": "person",
     "approved": "owner, job characters-full, 2026-10-09",
     "picture": "<abs path of a full-body A-pose picture>" or null,
     "description": "<who: drawn into the A-pose picture when there is no picture>",
     "references": ["<abs path>", ...],          pictures the A-pose drawing follows (the owner's drawing of them)
     "head": "<abs path of a picture of the head>" or null,   what the face and the hair are drawn after
     "hair": "<the hair in words>", "face": "<the face in words>",
     "outfits": ["work", "space"],              GarmentCode designs draped on the body (data/characters/garments)
     "garment_body": "mean_male" or "mean_female",   GarmentCode body the measurements are scaled from
     "clips": ["standing", "walking", ...],     sentences of tools/characters/people/clips.py (all when left out)
     "look": {...},                             tools/characters/people/person.py's settings (scale, colours, ...)
     "drape_simulator": "newton" or "blender",  the drapes' simulator; experimental, so a person is made only when
                                                its spec names one (make.py refuses it otherwise)
     "route": "prop"}                           the prop route (prop_person.py) instead of the shipped one; it also
                                                takes "outfit_words" ({outfit: the outfit by its parts, in words}),
                                                "pose_picture" (someone standing in the bind pose, a last reference
                                                the close-up takes the pose from) and "closeup_seeds"

An animal's spec is the animal route's (tools/characters/animals/): "kind": "animal" and its "body". Every make must
say who asked for it in "approved": the maker makes only characters somebody asked for.
"""
import json
import pathlib

KINDS = ("person", "animal")
OUTFITS = ("work", "space", "jacket", "coat", "trousers")
REQUIRED = ("name", "kind", "approved")
DRAPE_SIMULATORS = ("newton", "blender")


class SpecError(ValueError):
    """A spec the maker cannot make."""


def read(path):
    """The spec at `path`, checked; its paths as given (absolute)."""
    spec = json.loads(pathlib.Path(path).read_text())
    problems = problems_of(spec)
    if problems:
        raise SpecError(f"{path}: " + "; ".join(problems))
    return spec


def problems_of(spec):
    """Everything wrong with a spec, in words; empty when it can be made."""
    problems = [f"no {key}" for key in REQUIRED if not spec.get(key)]
    if spec.get("kind") and spec["kind"] not in KINDS:
        problems.append(f"kind {spec['kind']!r} is not one of {', '.join(KINDS)}")
    if not spec.get("picture") and not spec.get("description"):
        problems.append("neither a picture nor a description")
    for path in [spec.get("picture"), spec.get("head"), *spec.get("references", [])]:
        if path and not pathlib.Path(path).expanduser().is_absolute():
            problems.append(f"{path} is not an absolute path (or one from ~)")
    if spec.get("kind") == "person":
        problems += person_problems(spec)
    return problems


def person_problems(spec):
    """What is wrong with a person's own part of the spec."""
    problems = [f"outfit {outfit!r} is not one of {', '.join(OUTFITS)}"
                for outfit in spec.get("outfits", ["work"]) if outfit not in OUTFITS]
    if not spec.get("hair"):
        problems.append("no hair in words")
    if not spec.get("face"):
        problems.append("no face in words")
    if spec.get("drape_simulator") not in (None, *DRAPE_SIMULATORS):
        problems.append(f"drape_simulator {spec['drape_simulator']!r} is not one of {', '.join(DRAPE_SIMULATORS)}")
    if spec.get("route") not in (None, "prop"):
        problems.append(f"route {spec['route']!r} is not prop (or left out for the shipped route)")
    if spec.get("route") == "prop":
        problems += [f"no outfit_words for {outfit}" for outfit in spec.get("outfits", ["work"])
                     if outfit not in spec.get("outfit_words", {})]
    return problems


def inputs_of(spec):
    """Every file of this machine the spec names, by the name it carries up there."""
    named = {"picture": spec.get("picture"), "head": spec.get("head")}
    named.update({f"reference_{number}": path for number, path in enumerate(spec.get("references", []))})
    return {name: pathlib.Path(path).expanduser() for name, path in named.items() if path}
