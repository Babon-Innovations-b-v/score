"""The expedition camp habitat's kit layout: where every made piece of the two domes stands (mars-build, 2026-10-07;
the camp's concept picks, door dome K01 and far dome K08, coordinator's pick, owner may change).

    python3 tools/props/scene/camp_kit.py <out.json>     # writes the laid-out habitat for tools/props/library/route.py

Every number is the game's own, ported from game/world/mars/expedition_camp/ (camp_habitat.gd's DOMES, openings and
shell; camp_lining.gd's panels, ceiling rings and passage; camp_rooms.gd's partition and lamps), so the kit stands
exactly where the lining's collision and the air place are: the kit draws, the lining keeps collision and air. Frame:
the CampHabitat node's own, the deck at nought; a dome's degrees run from +x towards +z.

Pieces, in the kit's frame (x wide, y up, z back, front toward -z), as hub_kit.py writes them:
  inside   every lining panel as a quilted wall panel, a window panel or an opening's frame; a rib at every join that
           is not an opening's side; a ceiling gore over every panel; the roof cap; a deck wedge under every panel; the
           way through's lining; the partition; a pendant lamp at every lamp.
  outside  a shell gore over every panel (a window gore where the lining has a window, an open gore over an opening),
           the padded foot ring round every walled panel, the hull over the way through.
Each curved piece carries its numbers in `arc` (camp_pieces.py builds from them).
"""
import json
import math
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
ROOM = "camp"
PLACE = "expedition_camp"

# camp_habitat.gd
OPENING_WIDE = 2.4
OPENING_TALL = 2.6
DOORWAY = -40.5
DOOR_DOME = {"name": "door", "middle": (1.539, -7.164), "radius": 5.0, "other": (0.492, 3.16), "doorway": DOORWAY,
             "windows": [(-16.0, 50.0), (124.0, 213.0), (-131.0, -122.0), (-100.0, -64.0)]}
FAR_DOME = {"name": "far", "middle": (0.492, 3.16), "radius": 4.5, "other": (1.539, -7.164),
            "windows": [(-30.0, -15.0), (-8.0, 68.0), (70.0, 94.0), (100.0, 226.0)]}
DOMES = {"door": DOOR_DOME, "far": FAR_DOME}
SHELL_OUT = 0.45
SHELL_FOOT = -0.7
SHELL_SHOULDER = 3.5
SHELL_RISE = 2.6
SHELL_OPEN = 3.0
RING_THICK = 0.6
RING_OUT = 0.5
RING_MIDDLE = -0.45
COVER_OUT = 0.3
# camp_lining.gd
WALL_TALL = 3.4
CEILING_RISE = 2.0
CEILING_IN = 0.6
CEILING_RINGS = 6
PANEL_WIDE = 2.0
SKIN = 0.08
RIB_WIDE = 0.14
RIB_IN = 0.06
# camp_rooms.gd
PARTITION_PANELS = (3, 9)
PARTITION_TALL = 3.0
PARTITION_THICK = 0.12
PARTITION_DOOR_AT = 2.2
PARTITION_DOOR = (1.2, 2.3)
LAMPS = [("door", "polar", (152.0, 3.1)), ("door", "polar", (62.0, 3.1)), ("door", "polar", (-70.0, 2.45)),
         ("far", "polar", (228.0, 2.4)), ("far", "polar", (-52.0, 2.4)), ("far", "at", (-0.72, 2.6))]
LAMP_HEIGHT = 2.9
LAMP_WIDE = 0.36
LAMP_HOUSING = 0.12

# The cables over the deck: (dome, degrees round it the run starts at, how far it turns off the way to the middle),
# each CABLE_LONG long, starting CABLE_FROM_WALL in from the lining, lying on the deck.
CABLE_RUNS = [(DOOR_DOME, 35.0, 12.0), (DOOR_DOME, 180.0, -15.0), (DOOR_DOME, 15.0, 25.0),
              (DOOR_DOME, 124.5, -10.0), (DOOR_DOME, 290.0, 20.0),
              (FAR_DOME, 193.0, 10.0), (FAR_DOME, 238.0, -20.0), (FAR_DOME, 300.0, 15.0), (FAR_DOME, 140.0, 25.0),
              (FAR_DOME, 343.0, -25.0)]
# The ceiling ring lamps and the wall nets (the density pass): how many lamps a dome, how far out as a share of its
# radius, how far under the ceiling, how wide; a net's size and how high its foot stands, and the wall degrees a net
# keeps off (the hygiene cubicle stands 2.2 m tall there).
RING_LAMPS = 3
RING_OUT = 0.55
RING_UNDER = 0.25
RING_WIDE = 0.7
NET_WIDE = 1.2
NET_TALL = 0.8
NET_DEEP = 0.12
NET_FROM = 2.05
NET_SKIP = {"door": (249.0,)}
CABLE_LONG = 3.0
CABLE_FROM_WALL = 1.2
CABLE_OVER_DECK = 0.0

KINDS = {"dome_wall_panel": "hangs", "dome_window_panel": "hangs", "dome_rib": "hangs", "dome_ceiling_gore": "hangs",
         "dome_roof_cap": "hangs", "dome_deck_wedge": "floors", "dome_opening_frame": "hangs", "passage_lining": "floors",
         "partition": "hangs", "rod_lamp": "hangs", "shell_gore": "hangs", "shell_gore_window": "hangs",
         "shell_gore_open": "hangs", "foot_ring": "hangs", "passage_hull": "hangs", "ring_lamp": "hangs",
         "wall_net": "hangs"}


def round_the_dome(dome, degrees, out, high=0.0):
    angle = math.radians(degrees)
    middle = dome["middle"]
    return np.array([middle[0] + math.cos(angle) * out, high, middle[1] + math.sin(angle) * out])


def passage_facing(dome):
    middle, other = np.asarray(dome["middle"]), np.asarray(dome["other"])
    way = other - middle
    return math.degrees(math.atan2(way[1], way[0]))


def openings(dome):
    half = math.degrees(math.asin(OPENING_WIDE * 0.5 / dome["radius"]))
    middles = sorted([passage_facing(dome)] + ([dome["doorway"]] if "doorway" in dome else []))
    return [(middle - half, middle + half) for middle in middles]


def walled_arcs(dome):
    gaps = openings(dome)
    found = []
    for index in range(len(gaps)):
        after, before = gaps[index], gaps[(index + 1) % len(gaps)]
        until = before[0] if before[0] > after[1] else before[0] + 360.0
        found.append((after[1], until))
    return found


def has_a_window(dome, degrees):
    return any((degrees - window[0]) % 360.0 <= window[1] - window[0] for window in dome["windows"])


def panels(dome):
    """Every panel round a dome in order from its first opening: {span, kind: wall | window | opening}."""
    found = []
    gaps, arcs = openings(dome), walled_arcs(dome)
    for index in range(len(gaps)):
        found.append({"span": gaps[index], "kind": "opening"})
        start, end = arcs[index]
        count = max(1, round(math.radians(end - start) * dome["radius"] / PANEL_WIDE))
        share = (end - start) / count
        for at in range(count):
            span = (start + share * at, start + share * (at + 1))
            found.append({"span": span, "kind": "window" if has_a_window(dome, sum(span) / 2) else "wall"})
    return found


def ceiling_rings(dome):
    radius = dome["radius"]
    return [(radius - radius * CEILING_IN * (1.0 - math.cos(math.pi / 2 * step / CEILING_RINGS)),
             WALL_TALL + CEILING_RISE * math.sin(math.pi / 2 * step / CEILING_RINGS)) for step in range(CEILING_RINGS + 1)]


def ceiling_over(dome, out):
    rings = ceiling_rings(dome)
    for index in range(1, len(rings)):
        inner, outer = rings[index], rings[index - 1]
        if out >= inner[0]:
            return inner[1] + (outer[1] - inner[1]) * (out - inner[0]) / max(outer[0] - inner[0], 0.0001)
    return rings[-1][1]


def frame(x, y, z):
    return [np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis) for axis in (x, y, z)]


def radial_frame(degrees, inward=False):
    """A frame on a dome's round at `degrees`: y up, z out of the dome (or into it), x = y x z."""
    angle = math.radians((degrees))
    out = np.array([math.cos(angle), 0.0, math.sin(angle)])
    z = -out if inward else out
    y = np.array([0.0, 1.0, 0.0])
    return frame(np.cross(y, z), y, z)


def piece(kind, origin, axes, size, **more):
    x, y, z = axes
    found = {"kind": f"{ROOM}_{kind}", "at": [round(float(value), 4) for value in origin],
             "x": [round(float(value), 5) for value in x], "y": [round(float(value), 5) for value in y],
             "z": [round(float(value), 5) for value in z], "size": [round(float(value), 4) for value in size], "layer": 1}
    found.update(more)
    return found


def rounded(numbers):
    if isinstance(numbers, dict):
        return {key: rounded(value) for key, value in numbers.items()}
    if isinstance(numbers, (list, tuple)):
        return [rounded(value) for value in numbers]
    if isinstance(numbers, float):
        return round(numbers, 4)
    return numbers


def lining(dome):
    """One dome's lining: panels, ribs, ceiling gores, the roof cap and the deck wedges."""
    found = []
    radius = dome["radius"]
    rings = ceiling_rings(dome)
    every = panels(dome)
    for index, panel in enumerate(every):
        low, high = panel["span"]
        half = (high - low) / 2
        middle = (low + high) / 2
        chord = 2 * radius * math.sin(math.radians(half))
        axes = radial_frame(middle)
        foot = round_the_dome(dome, middle, radius * math.cos(math.radians(half)))
        if panel["kind"] == "opening":
            found.append(piece("dome_opening_frame", foot, axes, (chord + 0.2, WALL_TALL, SKIN + 0.12),
                               arc=rounded({"opening": [OPENING_WIDE, OPENING_TALL]})))
        else:
            kind = "dome_window_panel" if panel["kind"] == "window" else "dome_wall_panel"
            found.append(piece(kind, foot, axes, (chord, WALL_TALL, 0.14 if kind == "dome_wall_panel" else 0.2)))
            before = every[(index - 1) % len(every)]
            if before["kind"] != "opening":
                found.append(piece("dome_rib", round_the_dome(dome, low, radius), radial_frame(low),
                                   (RIB_WIDE, WALL_TALL, RIB_IN * 2)))
        top = round_the_dome(dome, middle, radius * math.cos(math.radians(half)), WALL_TALL)
        found.append(piece("dome_ceiling_gore", top, axes, (chord, CEILING_RISE, radius * CEILING_IN),
                           arc=rounded({"half": half, "rings": rings, "origin_radius": radius * math.cos(math.radians(half)),
                                        "origin_height": WALL_TALL})))
        reach = radius + SKIN
        found.append(piece("dome_deck_wedge", round_the_dome(dome, middle, 0.0),
                           frame(np.cross(radial_frame(middle)[2], [0.0, -1.0, 0.0]), radial_frame(middle)[2],
                                 [0.0, -1.0, 0.0]),
                           (2 * reach * math.sin(math.radians(half)), reach, 0.04),
                           arc=rounded({"half": half, "reach": reach})))
    cap = rings[-1]
    found.append(piece("dome_roof_cap", round_the_dome(dome, 0.0, 0.0, cap[1]),
                       frame([1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]),
                       (cap[0] * 2, cap[0] * 2, 0.11)))
    return found


def shell(dome):
    """One dome's shell outside: a gore over every panel, the padded foot ring round every walled one."""
    found = []
    out = dome["radius"] + SHELL_OUT
    for panel in panels(dome):
        low, high = panel["span"]
        half = (high - low) / 2
        middle = (low + high) / 2
        origin_radius = out * math.cos(math.radians(half))
        axes = radial_frame(middle, inward=True)
        foot = round_the_dome(dome, middle, origin_radius, SHELL_FOOT)
        arc = {"half": half, "out": out, "foot": SHELL_FOOT, "shoulder": SHELL_SHOULDER, "rise": SHELL_RISE,
               "origin_radius": origin_radius, "origin_height": SHELL_FOOT}
        chord = 2 * out * math.sin(math.radians(half))
        if panel["kind"] == "opening":
            found.append(piece("shell_gore_open", foot, axes, (chord, SHELL_SHOULDER + SHELL_RISE - SHELL_OPEN, out),
                               arc=rounded(dict(arc, **{"from": SHELL_OPEN}))))
            continue
        kind = "shell_gore_window" if panel["kind"] == "window" else "shell_gore"
        found.append(piece(kind, foot, axes, (chord, SHELL_SHOULDER + SHELL_RISE - SHELL_FOOT, out), arc=rounded(arc)))
        found.append(piece("foot_ring", foot, axes, (chord + 1.0, RING_THICK * 2, RING_THICK * 2 + RING_OUT),
                           arc=rounded(dict(arc, middle=out + RING_OUT, high=RING_MIDDLE, thick=RING_THICK))))
    return found


def passage():
    """The way through: the middle of its door dome end on the deck, its way along, its length."""
    ends = []
    for dome in (DOOR_DOME, FAR_DOME):
        half = math.asin(OPENING_WIDE * 0.5 / dome["radius"])
        ends.append(round_the_dome(dome, passage_facing(dome), dome["radius"] * math.cos(half)))
    along = (ends[1] - ends[0]) / np.linalg.norm(ends[1] - ends[0])
    return ends[0], along, float(np.linalg.norm(ends[1] - ends[0]))


def way_through():
    start, along, length = passage()
    axes = frame(np.cross([0.0, 1.0, 0.0], along), [0.0, 1.0, 0.0], along)
    return [piece("passage_lining", start, axes, (OPENING_WIDE + 2 * SKIN, OPENING_TALL + SKIN, length),
                  arc=rounded({"length": length, "wide": OPENING_WIDE, "tall": OPENING_TALL})),
            piece("passage_hull", start, axes, (OPENING_WIDE + 2 * COVER_OUT, OPENING_TALL + COVER_OUT - SHELL_FOOT, length),
                  arc=rounded({"length": length, "half_wide": OPENING_WIDE / 2 + COVER_OUT,
                               "top": OPENING_TALL + COVER_OUT, "foot": SHELL_FOOT}))]


def the_partition():
    walled = [panel for panel in panels(FAR_DOME) if panel["kind"] != "opening"]
    ends = [round_the_dome(FAR_DOME, walled[index]["span"][0], FAR_DOME["radius"]) for index in PARTITION_PANELS]
    along = (ends[1] - ends[0]) / np.linalg.norm(ends[1] - ends[0])
    axes = frame(along, [0.0, 1.0, 0.0], np.cross(along, [0.0, 1.0, 0.0]))
    length = float(np.linalg.norm(ends[1] - ends[0]))
    return [piece("partition", ends[0], axes, (length, PARTITION_TALL, PARTITION_THICK),
                  arc=rounded({"length": length, "tall": PARTITION_TALL, "thick": PARTITION_THICK,
                               "door_at": PARTITION_DOOR_AT, "door": list(PARTITION_DOOR)}))]


def lamps():
    found = []
    for dome_name, how, value in LAMPS:
        dome = DOMES[dome_name]
        if how == "polar":
            foot = round_the_dome(dome, value[0], value[1])
            out = value[1]
        else:
            foot = np.array([dome["middle"][0] + value[0], 0.0, dome["middle"][1] + value[1]])
            out = math.hypot(*value)
        ceiling = ceiling_over(dome, out)
        low = LAMP_HEIGHT - LAMP_HOUSING / 2
        found.append(piece("rod_lamp", foot + np.array([0.0, low, 0.0]),
                           frame([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]),
                           (LAMP_WIDE, round(ceiling - low, 2), LAMP_WIDE)))
    return found


def cables():
    """Power cables run loose over the deck from the furniture that draws power (the comms desk, the galley, the far
    dome's terminal desk, the growth chamber) and from a wall socket toward the middle, as the concept picks show them
    (the concept density pass, the owner 2026-10-08)."""
    found = []
    for dome, degrees, turn in CABLE_RUNS:
        start = round_the_dome(dome, degrees, dome["radius"] - CABLE_FROM_WALL)
        inward = np.array([-math.cos(math.radians(degrees + turn)), 0.0, -math.sin(math.radians(degrees + turn))])
        middle = start + inward * CABLE_LONG / 2 + np.array([0.0, CABLE_OVER_DECK, 0.0])
        axes = frame(inward, [0.0, 1.0, 0.0], np.cross(inward, [0.0, 1.0, 0.0]))
        found.append(piece("floor_cable", middle, axes, (CABLE_LONG, 0.06, 0.15)))
    return found


def ring_lamps(dome):
    """The concept picks' ceiling ring lamps: RING_LAMPS of them round the ceiling, RING_OUT of the way out, hung a
    little under it, their lens facing down."""
    found = []
    for index in range(RING_LAMPS):
        degrees = 360.0 * index / RING_LAMPS + 30.0
        out = dome["radius"] * RING_OUT
        high = ceiling_over(dome, out) - RING_UNDER
        found.append(piece("ring_lamp", round_the_dome(dome, degrees, out, high),
                           frame([1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]), (RING_WIDE, RING_WIDE, 0.17)))
    return found


def wall_nets(dome):
    """Soft storage nets high on the plain wall panels (none on a window panel or an opening), over the furniture, as
    the concept picks hang bags and pockets on the lining."""
    found = []
    for panel in panels(dome):
        if panel["kind"] != "wall":
            continue
        low, high = panel["span"]
        middle = (low + high) / 2
        if any(abs((middle - skip + 180.0) % 360.0 - 180.0) < 8.0 for skip in NET_SKIP.get(dome["name"], ())):
            continue
        half = (high - low) / 2
        axes = radial_frame(middle)
        foot = round_the_dome(dome, middle, dome["radius"] * math.cos(math.radians(half)) - NET_DEEP / 2, NET_FROM)
        found.append(piece("wall_net", foot, axes, (NET_WIDE, NET_TALL, NET_DEEP)))
    return found


def laid_out():
    found = []
    for dome in (DOOR_DOME, FAR_DOME):
        found += lining(dome) + shell(dome) + ring_lamps(dome) + wall_nets(dome)
    return found + way_through() + the_partition() + lamps() + cables()


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    pieces = laid_out()
    counts = {}
    for laid in pieces:
        counts[laid["kind"]] = counts.get(laid["kind"], 0) + 1
    kinds = {f"{ROOM}_{kind}": {"group": group} for kind, group in KINDS.items()}
    layout = {"room": ROOM, "place": PLACE, "frame": "the CampHabitat node's own: deck at nought, a dome's degrees from +x "
              "towards +z", "counts": counts, "kinds": kinds, "pieces": pieces}
    pathlib.Path(sys.argv[1]).write_text(json.dumps(layout, indent=1))
    print(len(pieces), "pieces", counts)


if __name__ == "__main__":
    main()
