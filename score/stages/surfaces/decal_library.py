"""The library's decals as the finish route offers them (score #164): score_lib's surfaces of family `decal`, each a
printed mark (a label, a logo, a button's legend) cut at its size in metres, laid over a part's base finish by the
placement record (route_parts.decal_placements) and baked by the finish's recipe (recipes.decal_layer).

    catalogue(root)                    every decal in force: [{address, class, ink, size_m, words, title}]
    offered(decals, material_class, ink)   those of one material class and ink (either None: any)
    picture(address)                   its decal.png on disk (tools/library/library_files), or None: a gap
    patterns(root)                     every pattern in force (#210): [{address, opening, shape, length_share, relief,
                                       roughness, title}]
    hardware(root)                     every hardware piece in force (#212): [{address, kind, size_m, moves, title}]
    piece(address)                     a hardware piece's hardware.glb on disk, or None: a gap

A pattern (#210) is a surface of family `pattern`: the shape of one opening of a vent or perforation pattern (round
holes, slots, ribs), its length share, its relief and its roughness, all in its tags, which pattern_decals.py tiles
at a mark's pitch inside its outline.

A hardware piece (#212) is a `model` entry of family `hardware` (score_lib's `hardware cut`: a lock, knob, handle,
hinge or latch cut from an adopted model): `hardware.glb` in its own frame (+z out of the face it is mounted on, its
back at z 0, centred, metres), its kind, size [wide, tall, deep] and how it moves in its tags, which the finish route
lays where the close-up shows such a piece (route_parts.hardware_placements) in place of TRELLIS.2's blob.

Read through score/library (ADR-0007: score reads score_lib's files only there) from its index of surfaces; an entry
withdrawn is not offered, and nothing is offered from a library that is not set (an empty catalogue, never a guess).
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
if str(REPO / "tools/library") not in sys.path:
    sys.path.append(str(REPO / "tools/library"))

FAMILY = "decal"
PICTURE = "decal.png"
PATTERN_FAMILY = "pattern"
HARDWARE_FAMILY, PIECE = "hardware", "hardware.glb"


def size_of(tags):
    """A decal's [width, height] in metres from its `size_m` tag (`0.100x0.060`), or None."""
    for written in tags.get("size_m", []):
        wide, _, tall = written.partition("x")
        try:
            return [float(wide), float(tall)]
        except ValueError:
            return None
    return None


def catalogue(root):
    """Every decal in force in the library at `root` (None: no library, no decal)."""
    from score import library
    if root is None or not (pathlib.Path(root) / "index" / "surface.json").is_file():
        return []
    found = []
    for row in library.index(root, "surface")["entries"]:
        tags = row.get("tags", {})
        if FAMILY not in tags.get("family", []) or row.get("state") == "withdrawn":
            continue
        found.append({"address": row["address"], "class": (tags.get("class") or [None])[0],
                      "ink": (tags.get("ink") or [None])[0], "size_m": size_of(tags),
                      "words": tags.get("words", []), "title": row.get("title", "")})
    return found


def first_number(tags, name):
    """A tag's first value as a number, or None."""
    try:
        return float((tags.get(name) or [None])[0])
    except (TypeError, ValueError):
        return None


def patterns(root):
    """Every pattern in force in the library at `root` (None: no library, no pattern), one an opening: those naming
    an opening shape pattern_decals draws."""
    import pattern_decals
    from score import library
    if root is None or not (pathlib.Path(root) / "index" / "surface.json").is_file():
        return []
    found = {}
    for row in library.index(root, "surface")["entries"]:
        tags = row.get("tags", {})
        if PATTERN_FAMILY not in tags.get("family", []) or row.get("state") == "withdrawn":
            continue
        shape, opening = (tags.get("shape") or [None])[0], (tags.get("opening") or [None])[0]
        if shape not in pattern_decals.SHAPES or not opening or opening in found:
            continue
        found[opening] = {"address": row["address"], "opening": opening, "shape": shape,
                          "length_share": first_number(tags, "length_share") or 1.0,
                          "relief": first_number(tags, "relief_m") or 0.0,
                          "roughness": first_number(tags, "roughness") or 0.9, "title": row.get("title", "")}
    return list(found.values())


def piece_size(tags):
    """A hardware piece's [wide, tall, deep] in metres from its `size_m` tag (`0.0327x0.0496x0.0122`), or None."""
    for written in tags.get("size_m", []):
        try:
            sides = [float(side) for side in written.split("x")]
        except ValueError:
            return None
        return sides if len(sides) == 3 else None
    return None


def hardware(root):
    """Every hardware piece in force in the library at `root` (None: no library, no piece): its address, kind, size,
    how it moves and title."""
    from score import library
    if root is None or not (pathlib.Path(root) / "index" / "model.json").is_file():
        return []
    found = []
    for row in library.index(root, "model")["entries"]:
        tags = row.get("tags", {})
        if HARDWARE_FAMILY not in tags.get("family", []) or row.get("state") == "withdrawn":
            continue
        size = piece_size(tags)
        if size is None or not tags.get("kind"):
            continue
        found.append({"address": row["address"], "kind": tags["kind"][0], "size_m": size,
                      "moves": (tags.get("moves") or ["none"])[0], "title": row.get("title", "")})
    return found


def piece(address):
    """A hardware piece's mesh on disk through the library's files (library_files.resolve), or None when the library
    does not hold it."""
    import library_files
    return library_files.resolve(library_files.reference(address, PIECE))


def offered(decals, material_class=None, ink=None):
    """The decals of one material class and ink; either None takes any."""
    return [decal for decal in decals if (material_class is None or decal["class"] == material_class)
            and (ink is None or decal["ink"] == ink)]


def picture(address):
    """A decal's picture on disk through the library's files (library_files.resolve), or None when the library does
    not hold it."""
    import library_files
    return library_files.resolve(library_files.reference(address, PICTURE))
