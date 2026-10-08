"""A place's design system, read from data/definitions/place.json: the style text every painting
and picture of the place is worded with, its palette, materials, light and do and don't pictures,
and the scale rules every place shares (the scene workflow of 2026-10-04, #121).

A place is filled in only when it is migrated, the habitat first. Wording comes only from this
file: a painting, a plan world or an object's picture for a place with no style text is refused,
so no session can word a room from its own head again.

    python3 tools/props/scene/place.py <place>        # print the place's style text
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"
# The entry every place shares: the scale rules, not a place.
SHARED = "shared"


def places(path=PLACES):
    """Every entry in the place file, the shared one among them."""
    return json.loads(pathlib.Path(path).read_text())


def place(place_id, path=PLACES):
    """One place's entry; refused for one the file does not have."""
    found = places(path)
    if place_id == SHARED or place_id not in found:
        known = ", ".join(name for name in found if name != SHARED)
        raise SystemExit(f"no place '{place_id}' in {path}; the places are: {known}")
    return found[place_id]


def style_text(place_id, path=PLACES):
    """The style text a place is painted and pictured in; refused while it has none."""
    text = place(place_id, path).get("style", {}).get("text", "")
    if not text.strip():
        raise SystemExit(f"the place '{place_id}' has no style text in {path}: write it there first")
    return text


def object_wording(place_id, name, size, path=PLACES):
    """What a row's picture is told: the object by name at its real size, alone, in the place's look."""
    wide, deep, high = size
    return (f"one {name}, {wide:.2f} m wide, {deep:.2f} m deep and {high:.2f} m tall, a single "
            f"whole object standing alone, in the look of this place: {style_text(place_id, path)}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(style_text(sys.argv[1]))


if __name__ == "__main__":
    main()
