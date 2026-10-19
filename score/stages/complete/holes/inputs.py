"""The inputs a place's line reads that are not there and no row makes (the old disk's work folder, lost 2026-10-19),
each a hole of the whole place with its code work: never fetched back as a loose file (an old paid output made to look
current, score/store/restore's key rule), never passed.

    found = inputs.lost(runner, place)   # [{"id", "sentence", "work"}], one a lost thing, ids stable run to run

Read from the stage table: every place node's declared world files (a ship place's through the table's own wrappers)
under the work folder ({seeds}, {home}/work) or in the repository ({data}, {repo}) that are not there, grouped by what
they are (KINDS: an earth seed, a ship seed, a ship place's views, a Pixal3D take), each kind with its code work; and
the owner's reference pictures the concept views of the place name (a view whose id names the place, or `ship` for a
ship place). A world node's inputs are no place's and are left to the run's own refusal.
"""
import pathlib

from score import stages
from score.stages import concept_view

WORK_ROOTS = ("{seeds}/", "{home}/work/")
EARTH, SHIP, VIEWS, PIXAL, OTHER, DATA, PICTURE = ("earth-seed", "ship-seed", "views", "pixal", "work", "data",
                                                   "reference")
# What a lost path under the work folder is, by its start there: (kind, the code work that makes it again).
KINDS = (("usd-r3/", EARTH, "earth seed lost: a seed row that exports each place's base from its accepted "
                            "surfaces-bake models and its kit (tools/usd/export.py), replacing the round-three folder; "
                            "terrain and every row after it stay blocked until it lands"),
         ("usd-ship/", SHIP, "ship seed lost: ship_kit@{place} (paid, the ship kits' own table) made again, then a "
                             "free ship-seed row that exports its base from that output's models (tools/usd/export.py "
                             "write_base) in place of the usd-ship folder"),
         ("demo/world1-r4/views/", VIEWS, "views lost (a copy of the scene record under work/demo, made by hand): the "
                                          "light rows read a ship place's views from its own scene-record output, as "
                                          "cast and surfaces-check do (light.passes reads them by path, DEMO)"),
         ("pixal/", PIXAL, "Pixal3D take lost: pixal@<place>'s accepted output carries its takes (<take>.glb, "
                           ".svviews, -final.glb, takes.json) and every reader reads them through an `after` on it; "
                           "then each lost take is a pixal hole, priced"))
OTHER_WORK = "an input under the work folder no row makes: a row that makes it, or the code that stops reading it"
DATA_WORK = "an input the repository should hold and does not: {name} ({path})"
PICTURE_WORK = ("the owner supplies {name}, his own reference picture (kept off the public repository until he says "
                "it may be public, then under data/)")
TAKE_ENDS = ("-final.glb", ".glb", ".svviews")


def relative(pattern):
    """A declared pattern's path under the work folder, or None for one elsewhere."""
    root = next((root for root in WORK_ROOTS if pattern.startswith(root)), None)
    return pattern[len(root):] if root else None


def what(rest):
    """(kind, item) of a lost path under the work folder: the kind KINDS names by its start, the item its first part
    there (a place, or a take without its ending; the whole folder when declared whole); any other path is one of
    its folder's lost files, the item that folder."""
    for start, kind, _ in KINDS:
        if rest.startswith(start) or rest == start.rstrip("/"):
            item = rest[len(start):].split("/", 1)[0] or rest
            return kind, next((item[:-len(end)] for end in TAKE_ENDS if item.endswith(end)), item)
    folder, _, name = rest.rpartition("/")
    return OTHER, folder if folder and "." in name else rest


def work_of(kind, place):
    return next((work for _, found, work in KINDS if found == kind), OTHER_WORK).replace("{place}", place)


def declared_lost(runner, place):
    """{(kind, item): {"paths", "nodes", "names"}} of the place nodes' declared world files that are not there."""
    found = {}
    for stage, node_place in runner.nodes([place]):
        if node_place is None:
            continue
        for name, pattern in runner.files_of(stage, place).items():
            pattern = (pattern[0] if isinstance(pattern, tuple) else pattern).replace("{place}", place)
            rest = relative(pattern)
            if rest is None and not pattern.startswith(("{data}", "{repo}")):
                continue
            path = runner.file_path(stage, name, place)
            if path.exists():
                continue
            key = what(rest) if rest is not None else (DATA, name)
            entry = found.setdefault(key, {"paths": set(), "nodes": set(), "names": set()})
            entry["paths"].add(str(path))
            entry["nodes"].add(f"{stage.name}@{place}")
            entry["names"].add(name)
    return found


def lost_pictures(runner, place):
    """The owner's reference pictures a concept view of the place names that are not there: {path: [view ids]}."""
    found = {}
    for view in concept_view.record()["views"]:
        named = view["id"].split("_")
        if place in named or ("ship" in named and stages.ship_place(place)):
            path = pathlib.Path(view["reference"].format(**runner.world.roots))
            if not path.exists():
                found.setdefault(str(path), []).append(view["id"])
    return found


def lost(runner, place):
    """The place's lost inputs as holes (module docstring), declared ones first, then the owner's pictures."""
    found = []
    for (kind, item), entry in sorted(declared_lost(runner, place).items()):
        nodes, paths = sorted(entry["nodes"]), sorted(entry["paths"])
        more = f" and {len(nodes) - 1} more" if len(nodes) > 1 else ""
        work = DATA_WORK.format(name=item, path=paths[0]) if kind == DATA else work_of(kind, place)
        found.append({"id": f"lost:{kind}:{item}", "sentence": f"lost input {item} ({paths[0]}), read by {nodes[0]}"
                                                              f"{more}", "work": work})
    for path, views in sorted(lost_pictures(runner, place).items()):
        name = pathlib.Path(path).name
        found.append({"id": f"lost:{PICTURE}:{name}",
                      "sentence": f"owner's reference picture {name} missing ({path}), for the concept views "
                                  f"{', '.join(views)}", "work": PICTURE_WORK.format(name=name)})
    return found
