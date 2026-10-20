"""The inputs a line reads that are not there (the old disk's work folder, lost 2026-10-19), each a hole with the node
that makes it again or its code work: never fetched back as a loose file (an old paid output made to look current,
score/store/restore's key rule), never passed.

    found = inputs.lost(runner, place)   # [{"id", "sentence", "node", "work"}], one a lost thing, ids stable run to run
    found = inputs.lost(runner, None)    # the same of the environment's own (world) nodes

Read from the stage table: every node's declared world files (a ship place's through the table's own wrappers) under
the work folder ({seeds}, {home}/work) or in the repository ({data}, {repo}) that are not there, grouped by what they
are (KINDS: an earth seed, a ship seed, a place's views copy, a Pixal3D take), each kind with its code work; and the
owner's reference pictures the concept views of the place name (a view whose id names the place, or `ship` for a ship
place). A Pixal3D take some place's pixal row makes is that row's hole (node `pixal@<place>`), priced through it. An
id names the lost thing itself, never the place reading it, so one input many places read is one hole world-wide
(`distinct`).
"""
import pathlib

from score import stages
from score.stages import concept_view
from score.stages.props import prop_data

WORK_ROOTS = ("{seeds}/", "{home}/work/")
DATA_ROOTS = ("{data}/", "{repo}/")
EARTH, SHIP, VIEWS, PIXAL, OTHER, DATA, PICTURE = ("earth-seed", "ship-seed", "views", "pixal", "work", "data",
                                                   "reference")
# What a lost path under the work folder is, by its start there: (kind, the code work that makes it again).
KINDS = (("usd-r3/", EARTH, "earth seed lost: the earth-seed row exports a place's base from its kit once the kit is "
                            "laid (score/stages/earth_seed); a place with no kit laid has none, and terrain-look still "
                            "reads the round-three folder until the owner decides its horizon check (#27)"),
         ("usd-ship/", SHIP, "ship seed lost: ship_kit@{place} (paid, the ship kits' own table) made again, then a "
                             "free ship-seed row that exports its base from that output's models (tools/usd/export.py "
                             "write_base) in place of the usd-ship folder"),
         ("demo/world1-r4/views/", VIEWS, "views lost (a copy of the scene record under work/demo, made by hand): the "
                                          "rows that read it read the place's views from its own scene record, as "
                                          "the light rows do (their light layer's views.json)"),
         ("pixal/", PIXAL, "Pixal3D take lost: pixal@<place>'s accepted output carries its takes (<take>.glb, "
                           ".svviews, -final.glb, takes.json) and every reader reads them through an `after` on it; "
                           "then each lost take is a pixal hole, priced"))
EARTH_VIEWS_WORK = ("views lost (a copy of the scene record under work/demo, made by hand): {nodes} read it by path; "
                    "they read the place's views from its own scene-record output instead, or a row writes the copy")
OTHER_WORK = "an input under the work folder no row makes: a row that makes it, or the code that stops reading it"
DATA_WORK = "an input the repository should hold and does not: {name} ({path})"
PICTURE_WORK = ("the owner supplies {name}, his own reference picture (kept off the public repository until he says "
                "it may be public, then under data/)")
TAKE_ENDS = ("-final.glb", ".glb", ".svviews")


def relative(pattern, roots=WORK_ROOTS):
    """A declared pattern's path under one of `roots` (the work folder's by default), or None for one elsewhere."""
    root = next((root for root in roots if pattern.startswith(root)), None)
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


def data_item(pattern, name):
    """A lost repository input's item: its file there (the pattern's first word under {data} or {repo}) and the name
    the node reads it by, so one name in two places' files is two holes."""
    return f"{relative(pattern, DATA_ROOTS).split(' ', 1)[0]}:{name}"


def work_of(kind, place, nodes):
    """The code work that makes a lost thing of `kind` again; the views copy an earth place's rows read names them."""
    if kind == VIEWS and not stages.ship_place(place):
        return EARTH_VIEWS_WORK.format(nodes=", ".join(nodes))
    return next((work for _, found, work in KINDS if found == kind), OTHER_WORK).replace("{place}", str(place))


def pixal_makers(place):
    """{take: place} of every take a place's pixal row makes (its prop objects' takes), the place's own first."""
    found = {}
    others = sorted(path.stem for path in prop_data.FOLDER.glob("*.json") if path.stem != place)
    for maker in ([place] if place else []) + others:
        for entry in prop_data.prop_objects({"objects": prop_data.objects(maker)}).values():
            found.setdefault(entry["take"], maker)
    return found


def declared_lost(runner, place):
    """{(kind, item): {"paths", "nodes", "names"}} of the declared world files of the place's nodes (the world's own
    nodes for place None) that are not there."""
    found = {}
    for stage, node_place in runner.nodes([place] if place else []):
        if node_place != place:
            continue
        for name, pattern in runner.files_of(stage, place).items():
            pattern = pattern[0] if isinstance(pattern, tuple) else pattern
            pattern = pattern.replace("{place}", place) if place else pattern
            rest = relative(pattern)
            if rest is None and not pattern.startswith(DATA_ROOTS):
                continue
            path = runner.file_path(stage, name, place)
            if path.exists():
                continue
            key = what(rest) if rest is not None else (DATA, data_item(pattern, name))
            entry = found.setdefault(key, {"paths": set(), "nodes": set(), "names": set()})
            entry["paths"].add(str(path))
            entry["nodes"].add(f"{stage.name}@{place}" if place else stage.name)
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


def lost_id(kind, item):
    """A lost input's hole id (its rule's prefix apart): it names the thing, so every place that reads it shares it."""
    return f"lost:{kind}:{item}"


def declared_hole(kind, item, entry, place, makers):
    """One declared lost thing as a hole: a take a pixal row makes with that node, anything else with its code work."""
    nodes, paths = sorted(entry["nodes"]), sorted(entry["paths"])
    more = f" and {len(nodes) - 1} more" if len(nodes) > 1 else ""
    node = f"{PIXAL}@{makers[item]}" if kind == PIXAL and item in makers else None
    if node:
        work = None
    elif kind == DATA:
        work = DATA_WORK.format(name=item.split(":", 1)[1], path=paths[0])
    else:
        work = work_of(kind, place, nodes)
    return {"id": lost_id(kind, item), "sentence": f"lost input {item} ({paths[0]}), read by {nodes[0]}{more}",
            "node": node, "work": work}


def lost(runner, place):
    """The lost inputs of the place's line (of the world's own nodes for None) as holes (module docstring), declared
    ones first, then the owner's pictures."""
    makers = pixal_makers(place)
    found = [declared_hole(kind, item, entry, place, makers)
             for (kind, item), entry in sorted(declared_lost(runner, place).items())]
    for path, views in sorted((lost_pictures(runner, place) if place else {}).items()):
        name = pathlib.Path(path).name
        found.append({"id": lost_id(PICTURE, name),
                      "sentence": f"owner's reference picture {name} missing ({path}), for the concept views "
                                  f"{', '.join(views)}", "node": None, "work": PICTURE_WORK.format(name=name)})
    return found


def is_lost(hole_id):
    """Whether a finding's id is a lost input's (`<rule>:lost:<kind>:<item>`)."""
    return hole_id.partition(":")[2].startswith("lost:")


def distinct(holes):
    """The holes counted once world-wide: a lost input once however many places read it (its id names the thing),
    every other hole as it is."""
    seen, found = set(), []
    for hole in holes:
        if is_lost(hole["id"]):
            if hole["id"] in seen:
                continue
            seen.add(hole["id"])
        found.append(hole)
    return found
