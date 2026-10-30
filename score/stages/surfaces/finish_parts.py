"""The finish route's shared steps on a take's faces (route_split.py and route_parts.py run them): each face's votes
over the views that see it (voted), a face no view reaches given the finish of the nearest voted face along the
surface (walked), smoothed with its crumbs joined (cleaned), every island under ISLAND_LEAST taken into the nearest
larger island of its own finish (merged_islands: the aft section's ~9,600 loose bits were parts), and each finish's
library surface checked against its colour (checked_finishes) before each part takes it (part_rows). The method's
interface's faults (parts_faults: PARTS in __init__.py). The finish-map method these came from (its maps, turntable
and SegviGen rows) was deleted on 2026-10-20 (#26), when the crops and people left it.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", REPO / "tools/cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FRONT_VOTE = 2.0  # the close-up's map is the one the owner checked (2026-10-12: "finish map seed 1 looks great")
ISLAND_LEAST = 0.002  # split_compare.CRUMB: an island under this share of the area joins the nearest larger one
# A finish's library surface must lie within this (CIE76) of its colour in the close-up. A photo's light, dirt and
# muted saturation move a right surface far: on round 4's six models the right ones lay up to dE 29.7 from it (the
# lander's light paint, its gold foil 29.5, black rubber 29.4), the wrong ones 33.2 to 44.9 (the power unit's grey
# steel as near-black dark_panel 44.9, the lab chair's grey vinyl as navy vinyl_seat 37.8, the power unit's silver
# tape as dark galvanized_dull 33.2; 2026-10-12). At the bake check's 20 the gold foil turned silver.
COLOUR_DELTA_E = 32.0


# --- the finishes on the model ----------------------------------------------------------------------------------------


def voted(per_map, count):
    """Each face's votes per finish over the maps that see it (the close-up's FRONT_VOTE, a view's 1)."""
    import numpy as np
    faces = len(next(iter(per_map.values())))
    votes = np.zeros((faces, count))
    for name, label in per_map.items():
        seen = label >= 0
        votes[np.flatnonzero(seen), label[seen]] += FRONT_VOTE if name == "front" else 1.0
    return votes


def walked(mesh, face_label):
    """Every unlabelled face given the label of the nearest labelled face along the surface (face middles joined
    across shared edges, weighed by their distance); faces no walk reaches take the nearest labelled face in space."""
    import numpy as np
    from scipy import sparse
    from scipy.sparse.csgraph import dijkstra
    from scipy.spatial import cKDTree
    pairs = mesh.face_adjacency
    middles = mesh.triangles_center
    length = np.linalg.norm(middles[pairs[:, 0]] - middles[pairs[:, 1]], axis=1) + 1e-9
    count = len(mesh.faces)
    graph = sparse.coo_matrix((np.r_[length, length], (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                              shape=(count, count)).tocsr()
    sources = np.flatnonzero(face_label >= 0)
    distance, _, source = dijkstra(graph, directed=False, indices=sources, min_only=True, return_predecessors=True)
    found = face_label.copy()
    reached = np.isfinite(distance) & (source >= 0)
    found[reached] = face_label[source[reached]]
    lost = found < 0
    if lost.any():
        found[lost] = face_label[sources[cKDTree(middles[sources]).query(middles[lost])[1]]]
    return found


def cleaned(mesh, face_label, count):
    """The labels smoothed over the surface (labels.smoothed_parts, hardly across a crease) and every island under
    ISLAND_LEAST of the area that borders others joined to the label it borders most; a finish this would remove,
    or leave under ISLAND_LEAST of the area, keeps its faces (kept_finishes)."""
    import numpy as np
    import labels
    votes = np.zeros((len(face_label), count))
    votes[np.arange(len(face_label)), face_label] = 1.0
    smoothed = labels.smoothed_parts(votes, labels.neighbour_matrix(mesh))
    saved = labels.PART_CRUMB
    labels.PART_CRUMB = ISLAND_LEAST
    try:
        return kept_finishes(face_label, labels.without_crumbs(mesh, smoothed), mesh.area_faces)
    finally:
        labels.PART_CRUMB = saved


def without_strays(mesh, face_label):
    """Each face's finish once every stray is given the finish it shares the most edges with, round by round until
    none is left. A stray is an island of one finish (its faces joined by shared edges) under patchy.py's STRAY_ISLAND
    of the area, not a whole piece of the shape, whose finish holds an island of at least that elsewhere: a detail
    that small is a decal or a part of its own, never a patch of paint (patchy.py), and a finish with no such island
    keeps its islands (the porthole glass, merged_islands) unless they cover that much together (fragmented_largest).
    The walk paints each face no view sees from its nearest seen face, and the views' labels follow a texture's
    shading: on astronaut-made-s1 (71% of its area seen by no view) that left jagged islands of the dark joints at the
    collar, wrists, lower back and inner thighs, stray 0.054 against patchy's 0.03 (2026-10-23)."""
    import numpy as np
    import patchy
    pairs = mesh.face_adjacency
    areas = mesh.area_faces  # as patchy.score weighs them, so a whole piece is told as it tells one
    piece = patchy.components(len(face_label), pairs)
    piece_area = np.bincount(piece, weights=areas)
    label = face_label.copy()
    while True:  # each round joins at least one island into a larger one, so it ends
        island = patchy.islands(label, pairs)
        area = np.bincount(island, weights=areas)
        face_of = np.zeros(len(area), dtype=int)
        face_of[island] = np.arange(len(island))
        finish = label[face_of]
        least = patchy.STRAY_ISLAND * areas.sum()
        standing = (area >= least) | fragmented_largest(area, finish, least)
        stray = ~standing & ~np.isclose(area, piece_area[piece[face_of]]) & np.isin(finish, finish[standing])
        across = np.r_[pairs, pairs[:, ::-1]]
        # voted by larger islands only: two strays never swap, and a small piece's strays join its largest island
        across = across[stray[island[across[:, 0]]] & (area[island[across[:, 1]]] > area[island[across[:, 0]]])]
        if not len(across):
            return label
        votes = np.zeros((len(area), int(label.max()) + 1))
        np.add.at(votes, (island[across[:, 0]], label[across[:, 1]]), 1.0)
        label = np.where((votes.sum(1) > 0)[island], votes.argmax(1)[island], label)


def fragmented_largest(area, finish, least):
    """Per island (its `area`, its `finish`), whether it is the largest island of a fragmented finish: one whose
    islands are each under `least` but cover at least `least` together. That much paint is no small detail, and kept
    as islands it is patchy paint: camp kitchen_counter_2's black glass cooktop, 2233 islands the largest 0.92% of the
    area, stray 0.068, and lab_table_1's flask glass, 18 islands, stray 0.035 (#36, 2026-10-31). Its largest island
    stands for it and the rest are strays."""
    import numpy as np
    count = int(finish.max()) + 1
    total = np.bincount(finish, weights=area, minlength=count)
    order = np.lexsort((-np.arange(len(area)), area, finish))  # per finish, its largest island (the first on a tie) last
    first = np.zeros(len(area), dtype=bool)
    first[order[np.r_[finish[order][1:] != finish[order][:-1], True]]] = True
    return first & (area < least) & (total[finish] >= least)


# A small detail finish (detail_finish): its family, or these words in its finish or parts. merged_islands gathers a
# finish with no larger island into one part, so nine steel fittings or a sheet of stickers were one part of many
# islands and read as stray: garage storage_box 0.042 (decals, paper stickers), old_station solar_panel_mast 0.032
# (steel fittings), lab chair 0.033 (rubber casters, paper notes), 2026-10-28.
DETAIL_FAMILIES = ("print", "paper", "rubber")
DETAIL_WORDS = ("decal", "sticker", "label", "note", "fitting", "rubber")


def detail_finish(finish):
    """True for a finish of small separate details (decals, stickers, labels, notes, fittings, rubber parts)."""
    words = f"{finish['finish']} {finish['parts']}".lower()
    return finish.get("family") in DETAIL_FAMILIES or any(word in words for word in DETAIL_WORDS)


def patchiness(mesh, face_label, part_of, finishes):
    """patchy.py's numbers and pass of a split take, each part its own region as the paint judges its painted parts
    (place_line.paint_take): a finish's edge along a part's is the paint the views show. Each island of a detail
    finish (detail_finish) is a part of its own, as a lone fitting is, so details sharing a part are no stray;
    blotches of any other finish still are."""
    import numpy as np
    import patchy
    details = [index for index, finish in enumerate(finishes) if detail_finish(finish)]
    island = patchy.islands(face_label, mesh.face_adjacency)
    own = np.where(np.isin(face_label, details), part_of.max() + 1 + island, part_of)
    return patchy.score(mesh, face_label, own, own)


def kept_finishes(before, after, areas):
    """`after` with each finish it lost given back its faces of `before`: one it lost entirely, or one left under
    ISLAND_LEAST of the area (`areas`, each face's) and under what it had. Smoothing and crumbs see no finish: a
    finish of many small islands (the cargo rack's white label plates, 0.9% of its area in 483 islands; the outer
    hatch's black stripes and glass) went into its neighbours whole, so no part owned it and merged_islands, whose own
    rule gathers such a finish into one part, never saw it (ship rooms, 2026-10-15); crumbs keep only loose bits, so
    the engine room desk's paper label kept 2 faces of no area of its 0.16% and no part owned it (#36, 2026-10-30)."""
    import numpy as np
    count = int(max(before.max(), after.max())) + 1
    had, left = (np.bincount(label, weights=areas, minlength=count) for label in (before, after))
    shrunk = np.flatnonzero((had > 0) & (left < ISLAND_LEAST * areas.sum()) & (left < had))
    lost = np.union1d(np.setdiff1d(np.unique(before), np.unique(after)), shrunk)
    return np.where(np.isin(before, lost), before, after)


def merged_islands(mesh, face_label):
    """Each face's part and finish once every island (one finish's faces joined by shared edges) under ISLAND_LEAST
    of the area, joined to the rest or loose (a loose bit shares no edge, so without_crumbs never reaches it), is
    taken in by its finish: into the larger island of its own finish nearest it in space; when its finish has no
    larger island, its finish's small islands together are one part, however small: a finish the close-up lists is
    no crumb (the outer hatch's porthole glass, 0.16% of its area, vanished into the steel, 2026-10-15). Taken in by
    space alone, the crane trolley's black warning stripes (each band a crumb) and the cut's yellow and rope crumbs
    went into its forged steel, the black finish vanished and that part mixed (2026-10-12). With no larger island,
    the largest island takes the rest."""
    import numpy as np
    from scipy.spatial import cKDTree
    import patchy
    island = np.unique(patchy.islands(face_label, mesh.face_adjacency), return_inverse=True)[1]
    area = np.bincount(island, weights=mesh.area_faces)
    large = area >= ISLAND_LEAST * mesh.area
    if not large.any():
        large[area.argmax()] = True
    kept = large[island]
    part_of, label = island.copy(), face_label.copy()
    middles = mesh.triangles_center
    hosts = kept.copy()
    for finish in np.unique(face_label[~kept]):
        lost = np.flatnonzero(~kept & (face_label == finish))
        host = np.flatnonzero(hosts & (face_label == finish))
        if not len(host):
            part_of[lost] = island[lost[0]]
            continue
        nearest = host[cKDTree(middles[host]).query(middles[lost])[1]]
        part_of[lost], label[lost] = part_of[nearest], face_label[nearest]
    return np.unique(part_of, return_inverse=True)[1], label


# --- measures and pictures -----------------------------------------------------------------------------------------

def agreement(mesh, face_label, per_map):
    """Per map, the area share of the faces it labels that are painted its finish."""
    areas = mesh.area_faces
    found = {}
    for name, label in per_map.items():
        seen = label >= 0
        found[name] = round(float(areas[seen & (face_label == label)].sum() / max(areas[seen].sum(), 1e-12)), 3)
    return found


def surface_colours(every, names):
    """Each surface's library colour, sRGB 0-255 (`every`: the take's surfaces, palette_library.take_surfaces)."""
    import numpy as np
    import labels
    return {name: np.clip(labels.srgb(np.array(every[name]["colour"], dtype=float)) * 255, 0, 255).astype(np.uint8)
            for name in names}


# --- each finish's surface against the close-up's colour -----------------------------------------------------------


def library_lab(spec):
    import labels
    import numpy as np
    return labels.lab(labels.srgb(np.array(spec["colour"], dtype=float))[None])[0]


# Not paint (owner, #8, 2026-10-12): glass, screen glow, lamp light and print are judged by their own colour, so one
# off the close-up's lit colour keeps its surface. A finish the close-up shows over ORDER_L lighter than another is
# named again when it lies over ORDER_LIBRARY darker in the library (bake_check's ORDER_L and ORDER_BAKED), and its
# parts keep the order in the library itself (ORDER_KEPT): the bake moves a surface's L* on its own (the hangar's parts
# shelving, 2026-10-13: plastic_grey 1.5 under galvanized_steel in the library, the steel baked 3.0 over its colour, so
# the plastic seen 27.7 L* lighter baked 4.5 darker).
# A finish seen through (see_through): its surface's family, or these words in its finish or parts.
SEEN_THROUGH_FAMILIES = ("glass", "screen", "light")
SEEN_THROUGH_WORDS = ("transparent", "translucent")
OWN_COLOUR = ("glass", "screen", "light", "print")
ORDER_L, ORDER_LIBRARY, ORDER_KEPT = 10.0, 3.0, 0.0


def checked_finishes(entry, finishes, measured, every, kit=()):
    """Each finish with its surface checked against the close-up's colour: the listed surface when it lies within
    COLOUR_DELTA_E of the measured colour, else the nearest surface of the same family (library `family`) of the
    take's surfaces (`every`: palette_library.take_surfaces), when within it; else the listed one kept, a new surface
    tinted to the measured colour proposed, and the finish marked off its colour (the paint's gate fails it). A
    see-through finish of a surface that is not glass, glow or light keeps its surface (coloured_cover). A finish that fits takes the room's own kit
    surface where one of its family fits too (`kit`, kit_taken)."""
    import numpy as np
    found = []
    for finish, colour in zip(finishes, measured):
        record = dict(finish, listed_surface=finish.get("listed_surface", finish["surface"]), measured_lab=None,
                      delta_e=None, by=finish.get("by", "the list"))
        if colour is None or finish["surface"] not in every:
            found.append(record)
            continue
        # in its own colour where the finish names one (the finish route's: its settings' token, which the bake
        # paints), not its surface's default token (astronaut-made-s1, 2026-10-22: suit_patches red under glass-brown)
        listed = dict(every[finish["surface"]], **({"colour": finish["colour"]} if finish.get("colour") else {}))
        apart = float(np.linalg.norm(library_lab(listed) - colour))
        record.update(measured_lab=[round(float(value), 1) for value in colour], delta_e=round(apart, 1))
        if apart > COLOUR_DELTA_E and coloured_cover(finish, every):
            record.update(by="its own colour", cover=True)
        elif apart > COLOUR_DELTA_E:
            family = [(float(np.linalg.norm(library_lab(spec) - colour)), name) for name, spec in every.items()
                      if spec.get("family") == listed.get("family") and "colour" in spec]
            nearest_apart, nearest = min(family) if family else (float("inf"), None)
            if nearest_apart <= COLOUR_DELTA_E:
                record.update(surface=nearest, delta_e=round(nearest_apart, 1), by="nearest of its family by colour")
            elif listed.get("family") in OWN_COLOUR:
                record.update(by="its own colour")
            else:
                record.update(by="off its colour", fits=False, new_surface={
                    "name": f"{finish['finish']} ({take_words(entry)})",
                    "description": f"{finish['finish']}, measured in the close-up at L*a*b* "
                                   f"{[round(float(value), 1) for value in colour]}",
                    "why": f"no {listed.get('family')} surface lies within dE {COLOUR_DELTA_E:.0f} of the close-up's "
                           f"colour (nearest {nearest}, dE {nearest_apart:.1f})",
                    "lab": [round(float(value), 1) for value in colour]})
        found.append(kit_taken(record, colour, every, kit))
    return in_close_up_order(entry, found, every)


def kit_taken(record, colour, every, kit):
    """A finish that fits by colour given the scene's own shell surface (`kit`: palette_library.shell_surfaces) where
    one of its surface's family lies within COLOUR_DELTA_E of the close-up's colour, the nearest such; as it was otherwise, and
    always for glass, glow, light and print, judged by their own colour (the materials audit, 2026-10-18: the hangar's
    ship took painted_grey_light, 165 L* grey, beside kit walls of painted_panel)."""
    import numpy as np
    family = every.get(record["surface"], {}).get("family")
    if (record.get("by") not in ("the list", "nearest of its family by colour") or record["surface"] in kit
            or family in OWN_COLOUR):
        return record
    fits = sorted((float(np.linalg.norm(library_lab(every[name]) - colour)), name) for name in kit
                  if name in every and every[name].get("family") == family and "colour" in every[name])
    if not fits or fits[0][0] > COLOUR_DELTA_E:
        return record
    return dict(record, surface=fits[0][1], delta_e=round(fits[0][0], 1), by="the room's kit surface by colour",
                kit_over=record["surface"])


def coloured_cover(finish, every):
    """True for a see-through finish whose surface is not glass, glow or light (the garage beacon's red transparent
    dome as red_plastic): its close-up pixels are its highlights and what lies behind it, not its colour, so like
    glass (owner, #8) it is judged by its own colour. Its pale highlights took the dome to plastic_grey (2026-10-13)."""
    return see_through(finish, every) and every.get(finish["surface"], {}).get("family") not in OWN_COLOUR


def opaque_lightness(every):
    """{surface: its library L*} of the take's surfaces that are paint (not OWN_COLOUR) and have a colour."""
    return {name: float(library_lab(spec)[0]) for name, spec in every.items()
            if "colour" in spec and spec.get("family") not in OWN_COLOUR}


def finish_lab(finish, every):
    """A finish's colour as it paints (L*a*b*): its own where it names one and keeps its listed surface (the finish
    route's: its settings' token, which the bake paints), else its surface's library colour. The order check read the
    library's alone (astronaut-made, 2026-10-23: its white shell in suit-white over its grey fabric in base-grey was
    held out of order by the variants' own tokens, base-grey under suit-white, and made the take a gap)."""
    own = finish.get("colour") and finish["surface"] == finish.get("listed_surface", finish["surface"])
    return library_lab(dict(every[finish["surface"]], **({"colour": finish["colour"]} if own else {})))


def out_of_order(lighter, darker, every, lightness, slack=ORDER_LIBRARY):
    """True when the close-up shows `lighter` over ORDER_L lighter than `darker` while it paints over `slack` darker
    (finish_lab; `lightness`: opaque_lightness, the surfaces judged by order)."""
    return (lighter.get("measured_lab") is not None and darker.get("measured_lab") is not None
            and lighter["surface"] in lightness and darker["surface"] in lightness
            and lighter["measured_lab"][0] - darker["measured_lab"][0] > ORDER_L
            and finish_lab(lighter, every)[0] < finish_lab(darker, every)[0] - slack)


def nearest_in_order(finish, every, lightness, keeps):
    """The surface of `finish`'s family nearest its close-up colour, within COLOUR_DELTA_E, whose library L* `keeps`
    (a test on it) allows: (dE, name), or None."""
    import numpy as np
    colour = np.array(finish["measured_lab"])
    family = every[finish["surface"]].get("family")
    fits = sorted((float(np.linalg.norm(library_lab(every[name]) - colour)), name) for name in lightness
                  if every[name].get("family") == family and keeps(lightness[name]))
    return fits[0] if fits and fits[0][0] <= COLOUR_DELTA_E else None


def in_close_up_order(entry, found, every):
    """The finishes with their opaque surfaces in the close-up's lightness order. Where the close-up shows a finish
    over ORDER_L lighter than another whose surface lies over ORDER_LIBRARY lighter in the library (painted_panel L*
    61.6 under bare_steel 66.3 on the greenhouse's water tank, the panel 13 lighter in its close-up), the order is
    kept (reordered) or the lighter finish is marked off its colour by its order (the paint's gate fails it). Where it
    lies lighter by less (the bake may still reverse them: the hangar's parts shelving), the order is kept only by a
    surface nearer the finish's close-up colour. Glass, glow, lamp light and print (OWN_COLOUR) and a finish judged by
    its own colour are left out; a take with no such pair comes back as it was."""
    lightness = opaque_lightness(every)
    for lighter in found:
        for darker in found:
            if (lighter.get("by") == "off its colour" or "its own colour" in (lighter.get("by"), darker.get("by"))
                    or not out_of_order(lighter, darker, every, lightness, ORDER_KEPT)):
                continue
            wide = out_of_order(lighter, darker, every, lightness)
            if not reordered(lighter, darker, every, lightness, wide) and wide:
                lighter.update(by="off its colour", fits=False, new_surface=order_proposal(entry, lighter, darker))
    return found


def reordered(lighter, darker, every, lightness, wide):
    """Whether one of the pair took the nearest surface of its family by colour, within COLOUR_DELTA_E, that keeps
    the close-up's order (ORDER_KEPT): the lighter finish first, else the darker (the hangar's parts shelving: its
    steel seen at L* 42 takes cast_steel under its light grey plastic bins). Unless the pair is `wide` apart, only a
    surface nearer the finish's close-up colour than its own is taken."""
    floor = finish_lab(darker, every)[0] - ORDER_KEPT
    ceiling = finish_lab(lighter, every)[0] + ORDER_KEPT
    for finish, keeps in ((lighter, lambda level: level >= floor), (darker, lambda level: level <= ceiling)):
        fit = nearest_in_order(finish, every, lightness, keeps)
        if fit and (wide or fit[0] < close_up_apart(finish, every)):
            finish.update(surface=fit[1], delta_e=round(fit[0], 1), by="nearest of its family in order")
            return True
    return False


def close_up_apart(finish, every):
    """CIE76 distance between a finish's colour as it paints (finish_lab) and its colour in the close-up."""
    import numpy as np
    return float(np.linalg.norm(finish_lab(finish, every) - np.array(finish["measured_lab"])))


def order_proposal(entry, lighter, darker):
    """The new surface proposed for a finish the close-up shows lighter than `darker` when no surface of either's
    family keeps the order."""
    seen = lighter["measured_lab"][0] - darker["measured_lab"][0]
    return {"name": f"{lighter['finish']} ({take_words(entry)})",
            "description": f"{lighter['finish']}, measured in the close-up at L*a*b* {lighter['measured_lab']}",
            "why": f"{seen:.1f} L* lighter than {darker['surface']} in the close-up, but no surface of its family or "
                   f"{darker['surface']}'s within dE {COLOUR_DELTA_E:.0f} keeps that order in the library",
            "lab": lighter["measured_lab"]}


def take_words(entry):
    return entry["object"][:40]


# --- parts: the method's interface ---------------------------------------------------------------------------------

def part_rows(mesh, part_of, face_label, finishes):
    """parts.json's rows: per part its share, its finish's library surface and words, the proposed new surface."""
    import numpy as np
    areas = mesh.area_faces
    rows = []
    for part in range(int(part_of.max()) + 1):
        members = part_of == part
        finish = finishes[int(np.bincount(face_label[members], weights=areas[members]).argmax())]
        rows.append({"part": part, "share": round(float(areas[members].sum() / areas.sum()), 4), "finish": None,
                     "judge": finish["surface"], "words": finish["finish"], "set_aside": False,
                     "proposed": None if finish["fits"] else finish.get("new_surface")})
    return rows


def see_through(finish, every):
    """True for a finish one sees through or that gives its own light: its surface glass, a screen or a light (or its
    words a transparent or translucent material)."""
    words = f"{finish['finish']} {finish['parts']}".lower()
    return (every.get(finish["surface"], {}).get("family") in SEEN_THROUGH_FAMILIES
            or any(word in words for word in SEEN_THROUGH_WORDS))


def parts_faults(folder):
    if not (folder / "parts.json").exists():
        return ["no parts.json"]
    missing = [take for take in json.loads((folder / "parts.json").read_text())["takes"]
               if not (folder / take / "parts.npy").exists()]
    return [f"no parts.npy for {missing}"] if missing else []
