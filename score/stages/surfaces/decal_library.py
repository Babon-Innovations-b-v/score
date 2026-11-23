"""The library's decals as the finish route offers them (score #164): score_lib's surfaces of family `decal`, each a
printed mark (a label, a logo, a button's legend) cut at its size in metres, laid over a part's base finish by the
placement record (route_parts.decal_placements) and baked by the finish's recipe (recipes.decal_layer).

    catalogue(root)                    every decal in force: [{address, class, ink, size_m, words, title}]
    offered(decals, material_class, ink)   those of one material class and ink (either None: any)
    picture(address)                   its decal.png on disk (tools/library/library_files), or None: a gap

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


def offered(decals, material_class=None, ink=None):
    """The decals of one material class and ink; either None takes any."""
    return [decal for decal in decals if (material_class is None or decal["class"] == material_class)
            and (ink is None or decal["ink"] == ink)]


def picture(address):
    """A decal's picture on disk through the library's files (library_files.resolve), or None when the library does
    not hold it."""
    import library_files
    return library_files.resolve(library_files.reference(address, PICTURE))
