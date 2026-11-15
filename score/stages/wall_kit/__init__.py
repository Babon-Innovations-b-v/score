"""The wall kit: the detail a room's walls carry, built by code from the plan and the scene inventory's code rows
(issue #128, cause 2; D2: shell pieces are code-made library entries, their finishes the scene's own library
surfaces). An inventory row of kind "code" whose part the plan's shell lays itself (route `plan`) brought no geometry:
every wall stood one flat finish ("flat grey box", the commonest verdict of the 2026-11-15 stills). The kit lays it.

    pieces = wall_kit.pieces(plan, rows)       # [Piece]: plan metres, heights over the floor
    surface = wall_kit.surface(piece, library) # the scene library variant a piece is painted with, else None

Each piece is a set of thin solids (`parts`: {points [[x, y]] in plan metres, low, high}), or of rivet heads
(`specks`), standing on a face of a wall
the shell builds (design_shell.wall_lines: an outline wall's room face, `face_reach`; an inner wall's two faces), proud
of it into the room, round every opening the shell cuts there (design_shell.on_edge); the scene record lays each solid
as a `slab` structure entry and a piece's rivets as one `specks` entry (scene_record.writer kit_entries: builders
tools/usd already has, so no row reading tools/usd moves). What a row lays follows its own words (`row_words`):

    frames   every opening cut in a wall of an enclosed place (a door, window, opening): two jambs and a head FRAME
             wide, FRAME_PROUD proud, a sill bar under one standing off the floor (D5: a doorway is framed as cut)
    panels   a wall row named a panel, plate, plating, hull or cladding (PANEL_WORDS): a row tied to plan items of its
             own and narrower than WHOLE_WALL a riveted plate at each item, on the wall nearest it; the first other
             (one named a panel before one named the hull, CLADDING_WORDS) covers every wall face once (`clad`):
             panels PANEL wide (each face's spans split evenly), a seam SEAM between them and at KICK and every BAND
             over it (both grown on a wall over GROW_AT), RELIEF proud, a rivet at each panel corner, a stiffener
             every RIB_EVERY panels
    padded   a row named padded, quilted or cushioned (PADDED_WORDS) at each plan item tied to it, on the wall nearest
             it: cushions about CUSHION square, PAD_DEEP proud, in a trim frame, from its shape's base to its tall
    dado     a row named a dado, wainscot or skirting (DADO_WORDS): a band DADO high round every wall face and a rail
             on it
    facade   a row named a facade or frontage (FACADE_WORDS): every outline wall line raised to the row's tall, a band
             at each storey (STOREY), windows (pane, frame, sill) BAY apart over the ground storey, a balcony with its
             rail at every other bay, alternating storey to storey, and an awning over each ground opening

Every piece names its row (`row`), what it was made from (`said`) and the plain thing it is (placeholders: a plate or
a trim; the facade's raised wall the shell). Its finish is a scene library surface (`surface`): the first variant
whose name shares a word with the piece's own (`words`: its row's, then its part's), else the wall's
(design_shell.surface_for), else none (named missing by the record, never painted another way). Pure numpy.
"""
import dataclasses
import re

import numpy as np

from score.stages.earth_seed import design_shell

ALGORITHM = "wall_kit"  # the score_lib algorithm entry the pieces trace to (their score:from, the library check)

PANEL_WORDS = frozenset(("panel", "plate", "plating", "hull", "cladding", "sheet"))
CLADDING_WORDS = PANEL_WORDS - {"hull"}  # a row named a panel clads the walls before one named the hull
PADDED_WORDS = frozenset(("padded", "padding", "quilted", "cushion", "cushioned", "upholstered"))
DADO_WORDS = frozenset(("dado", "wainscot", "wainscoting", "skirting"))
FACADE_WORDS = frozenset(("facade", "frontage"))

PANEL = 1.2  # metres a wall panel is wide at most
SEAM = 0.015  # metres between two panels
RELIEF = 0.012  # metres a panel stands proud of its wall's face
KICK = 1.0  # metres over the floor of the seam between the kick panel and the panels over it
BAND = 1.25  # metres a panel is high at most over the kick
GROW_AT = 4.0  # metres of wall over which its panels grow with it (a hangar's 12 m walls: panels three times as big)
RIVET = 0.03  # metres a rivet head is across (half of it stands proud of its panel)
RIVET_IN = 0.05  # metres a rivet stands in from its panel's corner
RIB_EVERY = 3  # a stiffener every so many panels
RIB = 0.08  # metres a stiffener is wide
RIB_PROUD = 0.04  # metres a stiffener stands proud of the wall's face
WHOLE_WALL = 3.0  # metres: a panel row tied to items narrower than this lays plates at them, else clads the walls
FRAME = 0.1  # metres a frame's jamb and head are wide
FRAME_PROUD = 0.05  # metres a frame stands proud of the wall's face
CUSHION = 0.4  # metres a padded cushion is across at most
PAD_GAP = 0.02  # metres between two cushions
PAD_DEEP = 0.06  # metres a cushion stands proud of the wall's face
DADO = 1.0  # metres the dado band is high
DADO_PROUD = 0.008
RAIL = 0.05  # metres a dado rail is high
RAIL_PROUD = 0.025
STOREY = 3.0  # metres a facade's storey is high
BAY = 2.6  # metres between a facade's windows
WINDOW = (1.2, 1.5)  # metres a facade window is wide and high
WINDOW_SILL = 0.9  # metres over its storey's floor a facade window's sill stands
PANE_PROUD = 0.01
SILL = (0.06, 0.15)  # metres a window sill is high and proud
STOREY_BAND = (0.2, 0.06)  # metres a storey band is high and proud
BALCONY = (1.8, 0.9, 0.15)  # metres a balcony is wide, deep and thick
BALCONY_RAIL = (1.0, 0.05)  # metres its rail is high and thick
AWNING = (1.0, 0.06, 0.2)  # metres an awning reaches out, is thick, and overhangs its opening each side
LEAST = 0.05  # metres of span a piece needs along its face to be laid


@dataclasses.dataclass
class Piece:
    """One kit piece: its name, its row, its solids in plan metres (heights over the floor), the plain thing it is,
    the words its finish is chosen by and what it was made from; a rivet piece's rivets instead (`specks`: [x, y,
    height] in plan metres, each a head RIVET across, as tools/usd/builders' `specks` draws it)."""
    name: str
    row: str | None
    parts: list
    plain: str
    words: tuple
    said: str
    specks: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Face:
    """One face of a wall the shell builds: its name, its foot's start on the floor plan, its way along, its way into
    the room, its length, the openings cut in it ((from, to, sill, head) along it) and its height."""
    name: str
    start: np.ndarray
    along: np.ndarray
    into: np.ndarray
    length: float
    cuts: list
    high: float
    inner: bool


def row_words(row):
    """The words of a row's id, name and noun (design_shell.row_words)."""
    return design_shell.row_words(row)


def faces(plan):
    """[Face] of every wall the shell builds (design_shell.wall_lines): an outline wall's room face, out from its edge
    by its face_reach, facing in; an inner wall's two faces, half its thickness each side of its line."""
    openings, eave = design_shell.openings_of(plan), design_shell.lowest_eave(plan)
    found = []
    for name, start, end, thick, entry, inner in design_shell.wall_lines(plan):
        start, end = np.asarray(start, float), np.asarray(end, float)
        length = float(np.linalg.norm(end - start))
        along, out = (end - start) / length, design_shell.outward(start, end)
        cuts = design_shell.on_edge(openings, start, end, thick)
        high = design_shell.wall_height(plan, entry, eave)
        sides = [(out * thick / 2, out), (-out * thick / 2, -out)] if inner else \
            [(out * design_shell.face_reach(entry, list(start), list(end)), -out)]
        found += [Face(f"{name}{'_' + str(side) if inner else ''}", start + offset, along, into, length, cuts, high,
                       inner) for side, (offset, into) in enumerate(sides, 1)]
    return found


def rect(face, begin, finish, near, far, low, high):
    """A solid on a face: from `begin` to `finish` along it, `near` to `far` metres into the room, `low` to `high`."""
    corners = [face.start + face.along * begin + face.into * near, face.start + face.along * finish + face.into * near,
               face.start + face.along * finish + face.into * far, face.start + face.along * begin + face.into * far]
    return {"points": [[round(float(value), 4) for value in corner] for corner in corners],
            "low": round(float(low), 4), "high": round(float(high), 4)}


def open_spans(face, low, high):
    """(from, to) along a face that no opening cut in it crosses between heights `low` and `high`, each at least LEAST
    long."""
    blocked = sorted((begin, finish) for begin, finish, sill, head in face.cuts if sill < high and head > low)
    found, edge = [], 0.0
    for begin, finish in blocked:
        if begin - edge >= LEAST:
            found.append((edge, begin))
        edge = max(edge, finish)
    if face.length - edge >= LEAST:
        found.append((edge, face.length))
    return found


def bands(high, grow=1.0):
    """(low, high) of a wall's panel rows: the kick panel to KICK, then rows of at most BAND (grown by `grow`) to the
    wall's top."""
    if high <= KICK + LEAST:
        return [(0.0, high)]
    count = max(1, int(np.ceil((high - KICK) / (BAND * grow) - 1e-9)))
    step = (high - KICK) / count
    return [(0.0, KICK)] + [(KICK + step * number, KICK + step * (number + 1)) for number in range(count)]


def panel_parts(face, begin, finish, low, high):
    """(a panel's solid, its four rivets) : the panel SEAM short of its neighbours, RELIEF proud; a rivet ([x, y,
    height]) RIVET_IN in from each corner, its head's middle on the panel's face."""
    half = SEAM / 2
    left, right, bottom, top = begin + half, finish - half, low + half, high - half
    rivets = []
    if right - left > 2 * RIVET_IN and top - bottom > 2 * RIVET_IN:
        for along in (left + RIVET_IN, right - RIVET_IN):
            spot = face.start + face.along * along + face.into * RELIEF
            rivets += [[round(float(spot[0]), 4), round(float(spot[1]), 4), round(float(up), 4)]
                       for up in (bottom + RIVET_IN, top - RIVET_IN)]
    return rect(face, left, right, 0.0, RELIEF, bottom, top), rivets


def clad(face, row):
    """[Piece] of a face clad in panels (module docstring, panels): each band's open spans split evenly into panels
    of at most PANEL, rows of at most BAND, both grown by the wall's height over GROW_AT; a stiffener on every
    RIB_EVERY-th seam of the kick band's spans from the floor to the top."""
    panels, rivets, ribs, grow = [], [], [], max(1.0, face.high / GROW_AT)
    for low, high in bands(face.high, grow):
        for begin, finish in open_spans(face, low, high):
            count = max(1, int(np.ceil((finish - begin) / (PANEL * grow) - 1e-9)))
            step = (finish - begin) / count
            for number in range(count):
                panel, heads = panel_parts(face, begin + step * number, begin + step * (number + 1), low, high)
                panels.append(panel)
                rivets += heads
            if low == 0.0:
                ribs += [rect(face, begin + step * seam - RIB / 2, begin + step * seam + RIB / 2, 0.0, RIB_PROUD, 0.0,
                              face.high) for seam in range(RIB_EVERY, count, RIB_EVERY)
                         if not any(cut[0] - RIB < begin + step * seam < cut[1] + RIB for cut in face.cuts)]
    words = tuple(sorted(row_words(row)))
    found = [Piece(f"{row['id']}_{face.name}", row["id"], panels, "plate", words + ("panel",),
                   f"inventory row {row['id']}: {face.name} clad in riveted panels of at most {PANEL:g} m, "
                   f"{RELIEF:g} m proud, round its {len(face.cuts)} openings (wall_kit.clad)")] if panels else []
    if rivets:
        found.append(Piece(f"{row['id']}_{face.name}_rivets", row["id"], [], "trim", words + ("rivet", "bolt"),
                           f"inventory row {row['id']}: a rivet at each panel corner on {face.name}, {RIVET:g} m "
                           "across (wall_kit.clad)", rivets))
    if ribs:
        found.append(Piece(f"{row['id']}_{face.name}_ribs", row["id"], ribs, "trim", words + ("rib", "frame"),
                           f"inventory row {row['id']}: a stiffener every {RIB_EVERY} panels on {face.name}, "
                           f"{RIB:g} m wide, {RIB_PROUD:g} m proud (wall_kit.clad)"))
    return found


def frames(face):
    """[Piece] of the frames round the openings cut in a face (module docstring, frames), one piece for the face."""
    parts = []
    for begin, finish, sill, head in face.cuts:
        left, right = max(0.0, begin - FRAME), min(face.length, finish + FRAME)
        top = min(face.high, head + FRAME)
        if begin - left >= LEAST / 2:
            parts.append(rect(face, left, begin, 0.0, FRAME_PROUD, sill, top))
        if right - finish >= LEAST / 2:
            parts.append(rect(face, finish, right, 0.0, FRAME_PROUD, sill, top))
        if top - head >= LEAST / 2:
            parts.append(rect(face, left, right, 0.0, FRAME_PROUD, head, top))
        if sill >= FRAME:
            parts.append(rect(face, left, right, 0.0, FRAME_PROUD, sill - FRAME, sill))
    return [Piece(f"frames_{face.name}", None, parts, "trim", ("frame", "door", "trim", "hazard"),
                  f"the frames of the {len(face.cuts)} openings cut in {face.name}: jambs and head {FRAME:g} m wide, "
                  f"{FRAME_PROUD:g} m proud (wall_kit.frames)")] if parts else []


def item_spot(plan, item):
    """(face, from, to along it) of a plan item: the wall face nearest the item's middle that it stands within its
    depth of, its span along that face its longer side, else None: on no wall."""
    x, y, wide, deep = (float(value) for value in item[1:5])
    middle = np.array([x + wide / 2, y + deep / 2])
    best = None
    for face in faces(plan):
        offset = middle - face.start
        at, off = float(offset @ face.along), float(offset @ face.into)
        if -0.1 <= at <= face.length + 0.1 and abs(off) <= min(wide, deep) / 2 + design_shell.ON_WALL:
            if best is None or abs(off) < best[0]:
                best = (abs(off), face, at)
    if best is None:
        return None
    _, face, at = best
    half = max(wide, deep) / 2
    return face, max(0.0, at - half), min(face.length, at + half)


def own_items(plan, row):
    """The plan items tied to a row that have a shape of their own (never the walls-and-ceiling item round the room)."""
    tied, shapes = plan.get("rows") or {}, plan.get("shapes") or {}
    return [item for item in plan.get("items") or [] if (len(item) <= 6 or item[6] == "item")
            and row["id"] in (tied.get(item[0]) or []) and shapes.get(item[0])]


def item_height(plan, item, row):
    """(base, top) of a row's piece at a plan item: its shape's base, and its shape's tall over it (else the row's)."""
    shape = (plan.get("shapes") or {}).get(item[0]) or {}
    base = float(shape.get("base") or 0.0)
    size = design_shell.sized(row) or [0.0, 0.0, 0.0]
    return base, base + float(shape.get("tall") or size[2] or 0.0)


def plates(plan, row):
    """[Piece] of a small panel row's riveted plates, one at each of its own plan items on the wall nearest it."""
    found = []
    for number, item in enumerate(own_items(plan, row), 1):
        spot = item_spot(plan, item)
        base, top = item_height(plan, item, row)
        if spot is None or top - base < LEAST or spot[2] - spot[1] < LEAST:
            continue
        face, begin, finish = spot
        panel, rivets = panel_parts(face, begin, finish, base, top)
        said = f"plan item {item[0]!r}, inventory row {row['id']}: a riveted plate on {face.name}, " \
               f"{finish - begin:.3g} by {top - base:.3g} m (wall_kit.plates)"
        words = tuple(sorted(row_words(row)))
        found.append(Piece(f"{row['id']}_{number}", row["id"], [panel], "plate", words + ("panel",), said))
        if rivets:
            found.append(Piece(f"{row['id']}_{number}_rivets", row["id"], [], "trim", words + ("rivet", "bolt"), said,
                               rivets))
    return found


def cushions(face, begin, finish, base, top):
    """The solids of a padded section: a grid of cushions of at most CUSHION, PAD_GAP apart, PAD_DEEP proud."""
    across = max(1, int(np.ceil((finish - begin) / CUSHION - 1e-9)))
    up = max(1, int(np.ceil((top - base) / CUSHION - 1e-9)))
    wide, high = (finish - begin) / across, (top - base) / up
    return [rect(face, begin + wide * column + PAD_GAP / 2, begin + wide * (column + 1) - PAD_GAP / 2, 0.0, PAD_DEEP,
                 base + high * line + PAD_GAP / 2, base + high * (line + 1) - PAD_GAP / 2)
            for column in range(across) for line in range(up)]


def padded(plan, row):
    """[Piece] of a padded row's sections (module docstring, padded): cushions and their trim frame at each plan item."""
    found = []
    for number, item in enumerate(own_items(plan, row), 1):
        spot = item_spot(plan, item)
        base, top = item_height(plan, item, row)
        if spot is None or top - base < 2 * FRAME or spot[2] - spot[1] < 2 * FRAME:
            continue
        face, begin, finish = spot
        words = tuple(sorted(row_words(row)))
        found.append(Piece(f"{row['id']}_{number}", row["id"],
                           cushions(face, begin + FRAME, finish - FRAME, base + FRAME, top - FRAME), "plate",
                           words + ("padded", "cushion", "padding"),
                           f"plan item {item[0]!r}, inventory row {row['id']}: a padded section on {face.name}, "
                           f"{finish - begin:.3g} by {top - base:.3g} m (wall_kit.padded)"))
        border = [rect(face, begin, begin + FRAME, 0.0, FRAME_PROUD, base, top),
                  rect(face, finish - FRAME, finish, 0.0, FRAME_PROUD, base, top),
                  rect(face, begin + FRAME, finish - FRAME, 0.0, FRAME_PROUD, base, base + FRAME),
                  rect(face, begin + FRAME, finish - FRAME, 0.0, FRAME_PROUD, top - FRAME, top)]
        found.append(Piece(f"{row['id']}_{number}_frame", row["id"], border, "trim", words + ("frame", "trim"),
                           f"the trim frame of {row['id']}'s padded section {number}, {FRAME:g} m wide "
                           "(wall_kit.padded)"))
    return found


def dado(face, row):
    """[Piece] of a face's dado (module docstring, dado): its band round the openings, and its rail on top."""
    words = tuple(sorted(row_words(row)))
    spans = open_spans(face, 0.0, DADO + RAIL)
    band = [rect(face, begin, finish, 0.0, DADO_PROUD, 0.0, DADO) for begin, finish in spans]
    rail = [rect(face, begin, finish, 0.0, RAIL_PROUD, DADO, DADO + RAIL) for begin, finish in spans]
    return [Piece(f"{row['id']}_{face.name}", row["id"], band, "plate", words + ("dado",),
                  f"inventory row {row['id']}: a dado band {DADO:g} m high on {face.name} (wall_kit.dado)"),
            Piece(f"{row['id']}_{face.name}_rail", row["id"], rail, "trim", words + ("rail", "trim"),
                  f"inventory row {row['id']}: the dado's rail on {face.name} (wall_kit.dado)")] if spans else []


def window_parts(face, middle, sill):
    """(pane, frame and sill solids) of a facade window centred `middle` along a face, its sill at `sill`: the frame
    FRAME_PROUD proud and FRAME round the pane, which stands PANE_PROUD before it, so the frame shows round it."""
    wide, high = WINDOW
    left, right, top = middle - wide / 2, middle + wide / 2, sill + high
    pane = [rect(face, left, right, 0.0, FRAME_PROUD + PANE_PROUD, sill, top)]
    frame = [rect(face, left - FRAME, right + FRAME, 0.0, FRAME_PROUD, sill, top + FRAME),
             rect(face, left - FRAME - 0.05, right + FRAME + 0.05, 0.0, SILL[1], sill - SILL[0], sill)]
    return pane, frame


def balcony_parts(face, middle, floor):
    """The solids of a facade balcony centred `middle` along a face on a storey's `floor`: its slab and its front
    rail (a parapet)."""
    wide, deep, thick = BALCONY
    rail_high, rail_thick = BALCONY_RAIL
    left, right = middle - wide / 2, middle + wide / 2
    slab = [rect(face, left, right, 0.0, deep, floor - thick, floor)]
    rail = [rect(face, left, right, deep - rail_thick, deep, floor, floor + rail_high)]
    return slab, rail


def facade(face, row, thick):
    """[Piece] of a facade on an outline face (module docstring, facade): its wall raised to the row's tall, its
    storey bands, windows, balconies and awnings, each kind one piece."""
    tall = max(face.high, float((design_shell.sized(row) or [0.0, 0.0, face.high])[2]))
    words, rid = tuple(sorted(row_words(row))), row["id"]
    raised = [rect(face, 0.0, face.length, -thick, 0.0, face.high, tall)] if tall - face.high >= LEAST else []
    storeys = int((tall + 1e-9) // STOREY)
    bays = max(0, int(face.length // BAY))
    margin = (face.length - bays * BAY) / 2
    middles = [margin + BAY * (number + 0.5) for number in range(bays)]
    bands, panes, framing, slabs, rails = [], [], [], [], []
    for storey in range(1, storeys):
        floor = storey * STOREY
        bands.append(rect(face, 0.0, face.length, 0.0, STOREY_BAND[1], floor - STOREY_BAND[0], floor))
        for number, middle in enumerate(middles):
            if floor + WINDOW_SILL + WINDOW[1] + FRAME > tall:
                continue
            pane, frame = window_parts(face, middle, floor + WINDOW_SILL)
            panes += pane
            framing += frame
            if (number + storey) % 2 == 0:
                slab, rail = balcony_parts(face, middle, floor)
                slabs += slab
                rails += rail
    awnings = [rect(face, max(0.0, begin - AWNING[2]), min(face.length, finish + AWNING[2]), 0.0, AWNING[0],
                    head + 0.15, head + 0.15 + AWNING[1]) for begin, finish, sill, head in face.cuts
               if head + 0.15 + AWNING[1] < STOREY]
    said = f"inventory row {rid}: the facade on {face.name}, {tall:g} m tall, {storeys} storeys of {STOREY:g} m"
    kinds = [("raised", raised, "shell", ("facade", "wall"), f"{said}: its wall raised from {face.high:g} m"),
             ("bands", bands, "trim", ("band", "trim", "facade"), f"{said}: a band at each storey"),
             ("panes", panes, "plate", ("glass", "window", "pane"), f"{said}: {len(panes)} windows {BAY:g} m apart"),
             ("frames", framing, "trim", ("frame", "window", "trim"), f"{said}: the windows' frames and sills"),
             ("balconies", slabs, "plate", ("balcony", "concrete", "facade"), f"{said}: a balcony every other bay"),
             ("rails", rails, "trim", ("railing", "rail", "metal"), f"{said}: the balconies' rails"),
             ("awnings", awnings, "plate", ("awning", "canopy", "shutter"), f"{said}: an awning over each opening")]
    return [Piece(f"{rid}_{face.name}_{kind}", rid, parts, plain, words + extra, f"{text} (wall_kit.facade)")
            for kind, parts, plain, extra, text in kinds if parts]


def facade_faces(plan, rows):
    """{row id: [(face, its wall's thickness)]} of the facade rows: every outline face, split between the rows by
    which side of the outline's box's long middle line it stands (the first row the low side, x west or y north)."""
    outer = [face for face in faces(plan) if not face.inner]
    if not rows or not outer:
        return {}
    points = np.asarray(design_shell.outline_of(plan), float)
    low, high = points.min(axis=0), points.max(axis=0)
    across = 0 if high[0] - low[0] <= high[1] - low[1] else 1
    middle = (low[across] + high[across]) / 2
    thick = {name: thickness for name, _, _, thickness, _, _ in design_shell.wall_lines(plan)}
    found = {row["id"]: [] for row in rows}
    for face in outer:
        side = 0 if float((face.start + face.along * face.length / 2)[across]) < middle else 1
        found[rows[min(side, len(rows) - 1)]["id"]].append((face, thick[face.name]))
    return found


def is_wall_row(row):
    """Whether a row is a wall's (its part a wall, or its words a wall's)."""
    return row.get("part") == "wall" or "wall" in row_words(row)


def pieces(plan, rows):
    """[Piece] of the wall kit for a plan and the code rows its shell lays (module docstring): the frames round every
    opening, then each row's own pieces by its words."""
    walls = faces(plan)
    found = [piece for face in walls for piece in frames(face)]
    facades = [row for row in rows if row_words(row) & FACADE_WORDS]
    for row_id, laid in facade_faces(plan, facades).items():
        row = next(row for row in facades if row["id"] == row_id)
        found += [piece for face, thick in laid for piece in facade(face, row, thick)]
    clad_by = None
    for row in sorted(rows, key=lambda row: not row_words(row) & CLADDING_WORDS):
        words = row_words(row)
        if words & FACADE_WORDS:
            continue
        if words & PADDED_WORDS:
            found += padded(plan, row)
        elif words & DADO_WORDS:
            found += [piece for face in walls for piece in dado(face, row)]
        elif words & PANEL_WORDS and is_wall_row(row):
            if own_items(plan, row) and (design_shell.sized(row) or [WHOLE_WALL])[0] < WHOLE_WALL:
                found += plates(plan, row)
            elif clad_by is None:
                clad_by = row["id"]
                found += [piece for face in walls for piece in clad(face, row)]
    return found


def variants(library):
    """Every variant name the scene library holds, in its kinds' order, each once."""
    kinds = (library or {}).get("kinds") or {}
    return list(dict.fromkeys(name for names in kinds.values() for name in names))


def surface(piece, library):
    """The scene library variant a piece is painted with: the first (by the piece's words in order) whose name holds
    one of its words, else the wall's (design_shell.surface_for), else None."""
    names = variants(library)
    for word in piece.words:
        found = next((name for name in names if word in set(re.split(r"[^a-z]+", name.lower()))), None)
        if found:
            return found
    return design_shell.surface_for("wall", library)
