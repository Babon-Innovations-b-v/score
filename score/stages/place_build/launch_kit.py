"""The launch kit (the pad, 2099 judge 2026-11-23: "the wrong ship and looks messy", "a plain grey rectangular slab
box", "the diagonal bracing is drawn as stair-stepped block zigzags"): a launch site's big pieces built in code at
their real size, every piece one mesh `geo` of named parts for the place's palette (cockpit_kit.written), so the
ship, its launch mount and the tower's bracing are clean turned and straight solids, never a picture-made lump or a
stack of boxes.

    write(path, kind, sizes)    the piece of `kind` (KINDS) with its `sizes` written as a USD file at `path`; its parts

Every piece is built standing up (y up, its foot on y = 0, centred on x = z = 0 unless said) and written as built.

- `ship`: a slim single-stage steel ship (a stainless hull of welded rings, each ring's seam a raised band, or one
  seamless barrel with `ring` 0), an ogive nose with its black heat-shield tip and the black band under it, two
  forward flaps (canards, `fore` metres out) on the nose and two aft flaps (`aft` out, `aft_chord` along the hull) at
  its foot, a skirt and its engine bells; parts hull, seam (only with seams), tiles, flap, engine.
- `launch_ring`: the round launch mount: a ring on slanted legs over a round plinth, its clamps, hoses down to the
  deck and orange-lit hardware boxes round its rim; parts ring, leg, plinth, clamp, hose, glow.
- `lattice`: a square tower's straight X-bracing, bay over bay on its four faces between its corner posts, with a
  girder at each bay; parts brace, girder.
- `railing`: a square platform's railing round its edge (posts, top and middle rails); part rail.
- `flood_head`: a floodlight's head, a frame of `columns` x `rows` round lamps facing +z; parts frame, lamp.
- `ferris_wheel`: a big wheel on its A-frame legs: twin rims, spokes, gondolas; parts rim, spoke, cabin, leg.
- `skyscraper`: a far city's glass tower set back in tiers, its windows lit here and there, mullion fins, a neon band
  round each tier's top and a spire; parts glass, fin, window, neon, spire.
- `mound`: a smooth hill behind a far city; part hill.
- `ferry`: a harbour ferry on the water (its waterline at y = 0): a hull with a pointed bow, a two-deck cabin with
  its window bands lit, and its wake spreading behind it on the water; parts hull, cabin, window, wake.
"""
import math

import numpy as np

from score.stages.place_build.cockpit_kit import about, box, moved, outline_slab, tube, turned, written

UP = about("x", -90)
NOSE_POWER = 2.4  # the nose's fullness: its radius falls as (1 - share^power)^0.5, a blunt ogive  # a turned piece's axis (z) stood up along y


def stood(pieces, offset=(0.0, 0.0, 0.0)):
    """Turned pieces (axis z) stood up along y and moved by `offset`."""
    return moved(pieces, UP, offset)


def nose_profile(radius, foot, length, steps=24):
    """The (radius, height) points of an ogive nose of `length` over a body of `radius` from height `foot`, rounded
    at its tip (no point below a tenth of the radius before the pole)."""
    found = []
    for step in range(steps + 1):
        share = step / steps
        found.append((radius * max((1.0 - share ** NOSE_POWER) ** 0.5, 0.0), foot + length * share))
    found[-1] = (0.0, foot + length)
    return found


def nose_radius(radius, length, up):
    """The nose's radius `up` metres over its shoulder (nose_profile's curve)."""
    share = min(max(up / length, 0.0), 1.0)
    return radius * max((1.0 - share ** NOSE_POWER) ** 0.5, 0.0)


def flap(part, root, tip, span, thick):
    """A flap's plate in the (out, up) plane: its root chord `root` (low, high) along the hull, its tip chord `tip`
    (low, high) `span` metres out; `thick` through z."""
    outline = [(0.0, root[0]), (span, tip[0]), (span, tip[1]), (0.0, root[1])]
    return outline_slab(part, outline, -thick / 2, thick / 2)


def ship(radius=3.74, high=54.0, nose=13.5, ring=2.0, segments=96, engines=6, fore=2.2, aft=3.0, aft_chord=10.4):
    """The ship standing on its aft skirt's foot (y = 0), its engine bells inside the skirt, its body `radius`, its tip
    at `high`; a weld seam every `ring` metres up the barrel (none with `ring` 0: one seamless steel barrel); its
    forward flaps `fore` metres out on the x axis, its aft flaps `aft` out and `aft_chord` along the hull likewise."""
    bells = 1.4
    foot = bells  # the skirt's foot
    shoulder = high - nose
    tip_from = shoulder + nose * 0.8
    profile = nose_profile(radius, shoulder, nose)
    steel = [point for point in profile if point[1] <= tip_from]
    black = [point for point in profile if point[1] >= steel[-1][1]]
    hull = [(0.0, foot), (radius * 0.92, foot), (radius, foot + 0.8)] + steel + [(0.0, steel[-1][1])]
    found = stood(turned("hull", hull, segments=segments, smooth=False))
    tucked = (black[0][0] * 0.97, black[0][1] - 0.1)  # the tip's foot inside the steel, so no face is shared
    found += stood(turned("tiles", [(0.0, tucked[1]), tucked] + black, segments=segments, smooth=True))
    band = 0.9
    found += stood(turned("tiles", [(radius - 0.05, shoulder - band), (radius + 0.03, shoulder - band),
                                    (radius + 0.03, shoulder), (radius - 0.05, shoulder), (radius - 0.05, shoulder - band)],
                          segments=segments))
    height = foot + 0.8 + ring
    while ring > 0 and height < shoulder - band - 0.3:
        found += stood(turned("seam", [(radius - 0.05, height - 0.04), (radius + 0.02, height - 0.04),
                                       (radius + 0.02, height + 0.04), (radius - 0.05, height + 0.04),
                                       (radius - 0.05, height - 0.04)], segments=segments))
        height += ring
    for side in (1.0, -1.0):
        turn = about("y", 0 if side > 0 else 180)
        forward = flap("flap", (shoulder + 0.4, shoulder + 5.0), (shoulder + 1.6, shoulder + 4.2), fore, 0.22)
        found += moved(moved(forward, None, (nose_radius(radius, nose, 4.6) - 0.15, 0.0, 0.0)), turn)
        aft_flap = flap("flap", (foot + 0.6, foot + 0.6 + aft_chord), (foot + 0.6, foot + 0.6 + aft_chord * 0.52),
                        aft, 0.3)
        found += moved(moved(aft_flap, None, (radius - 0.15, 0.0, 0.0)), turn)
    for number in range(engines):
        angle = 2 * math.pi * (number + 0.5) / engines
        at = (radius * 0.48 * math.cos(angle), 0.0, radius * 0.48 * math.sin(angle))
        bell = [(0.0, 0.08), (0.9, 0.08), (0.55, bells * 0.75), (0.4, bells + 0.05), (0.0, bells + 0.05)]
        found += stood(turned("engine", bell, segments=32), at)
    skirt = radius * 0.92 - 0.02  # the aft skirt round the bells, its foot what the ship stands on
    found += stood(turned("hull", [(skirt - 0.4, 0.0), (skirt, 0.0), (skirt, foot + 0.05), (skirt - 0.4, foot + 0.05),
                                   (skirt - 0.4, 0.0)], segments=segments))
    return moved(found, None, (0.0, 0.0, 0.0))


def launch_ring(outer=6.2, inner=3.4, top=6.0, thick=1.3, legs=6, clamps=12, hoses=3):
    """The launch mount: a ring `outer` x `inner` with its top at `top`, on `legs` slanted legs over a round plinth,
    `clamps` clamps on its top, its rim's hardware boxes lit orange, and `hoses` hoses down to the deck."""
    low = top - thick
    found = stood(turned("ring", [(inner, low), (outer, low), (outer, top), (inner, top), (inner, low)], segments=96))
    found += stood(turned("plinth", [(0.0, 0.0), (outer + 3.0, 0.0), (outer + 2.8, 0.35), (0.0, 0.35)], segments=96))
    found += stood(turned("leg", [(inner - 0.6, 0.35), (inner + 0.2, 0.35), (inner + 0.2, 0.9), (inner - 0.6, 0.9),
                                  (inner - 0.6, 0.35)], segments=64))
    for number in range(legs):
        angle = 2 * math.pi * (number + 0.5) / legs
        out = np.array([math.cos(angle), 0.0, math.sin(angle)])
        foot = out * (outer + 1.6) + np.array([0.0, 0.35, 0.0])
        head = out * (outer - 0.6) + np.array([0.0, low, 0.0])
        found += tube("leg", [foot, head], 0.42, 16)
        across = np.array([-out[2], 0.0, out[0]])
        middle = (foot + head) / 2
        found += tube("leg", [out * (inner + 0.1) + np.array([0.0, 0.9, 0.0]), middle - across * 0.0], 0.22, 12)
    for number in range(clamps):
        angle = 2 * math.pi * number / clamps
        clamp = box("clamp", (-0.35, top, inner + 0.45), (0.35, top + 0.8, inner + 1.35), 0.04)
        found += moved(clamp, about("y", -math.degrees(angle) + 90))
    for number in range(clamps * 2):
        angle = 2 * math.pi * (number + 0.25) / (clamps * 2)
        lit = box("glow", (-0.18, low + 0.35, outer - 0.02), (0.18, low + 0.6, outer + 0.1), 0.02)
        found += moved(lit, about("y", -math.degrees(angle) + 90))
        if number % 2 == 0:
            housing = box("clamp", (-0.5, low + 0.7, outer - 0.05), (0.5, top - 0.2, outer + 0.3), 0.03)
            found += moved(housing, about("y", -math.degrees(angle) + 90))
    for number in range(hoses):
        angle = math.radians(200.0 + 40.0 * number)
        out = np.array([math.cos(angle), 0.0, math.sin(angle)])
        path = [out * (outer + 0.25) + np.array([0.0, low + 0.3, 0.0])]
        for step in range(1, 9):
            share = step / 8
            reach = outer + 0.25 + share * 6.0
            height = (low + 0.3) * (1.0 - share) ** 2 + 0.55 * (1 - (1.0 - share) ** 2)
            path.append(out * reach + np.array([0.0, max(height, 0.55), 0.0]))
        found += tube("hose", path, 0.2, 12)
    return found


def lattice(wide=10.6, deep=10.6, high=41.8, foot=0.0, bay=3.5, panels=3, bar=0.12, inset=0.2):
    """A square tower's bracing: each of its four faces (`wide` along x, `deep` along z, centred on x = z = 0) split
    into `panels` panels across, its bars in the face's plane `inset` in from the tower's outside, one straight X per
    panel and bay of about `bay` metres from `foot` to `high`, and a girder at every bay line."""
    count = max(1, round((high - foot) / bay))
    step = (high - foot) / count
    half_x, half_z = wide / 2 - inset, deep / 2 - inset
    faces = [((-half_x, half_z), (half_x, half_z)), ((half_x, half_z), (half_x, -half_z)),
             ((half_x, -half_z), (-half_x, -half_z)), ((-half_x, -half_z), (-half_x, half_z))]
    lift = np.array([0.0, 1.0, 0.0])
    found = []
    for start, end in faces:
        start, end = np.array([start[0], 0.0, start[1]]), np.array([end[0], 0.0, end[1]])
        for panel in range(panels):
            left = start + (end - start) * panel / panels
            right = start + (end - start) * (panel + 1) / panels
            for number in range(count):
                low, top = foot + number * step, foot + (number + 1) * step
                found += tube("brace", [left + lift * low, right + lift * top], bar, 8)
                found += tube("brace", [right + lift * low, left + lift * top], bar, 8)
        for number in range(count + 1):
            height = max(foot + number * step, foot + bar * 1.5)
            low_corner = np.minimum(start, end) + lift * height - bar * 1.4
            high_corner = np.maximum(start, end) + lift * height + bar * 1.4
            found += box("girder", low_corner, high_corner, 0.02)  # flat-topped, so a lamp stands on it
    return found


def railing(wide=10.6, deep=10.6, high=1.1, spacing=1.5, bar=0.035):
    """A railing round a `wide` x `deep` platform's edge (centred on x = z = 0, standing on y = 0): posts every
    `spacing` metres or less, a top rail at `high` and a middle rail."""
    corners = [(-wide / 2, -deep / 2), (wide / 2, -deep / 2), (wide / 2, deep / 2), (-wide / 2, deep / 2)]
    found = []
    for number, (x0, z0) in enumerate(corners):
        x1, z1 = corners[(number + 1) % 4]
        length = math.hypot(x1 - x0, z1 - z0)
        posts = max(2, math.ceil(length / spacing) + 1)
        for post in range(posts - 1):
            share = post / (posts - 1)
            x, z = x0 + (x1 - x0) * share, z0 + (z1 - z0) * share
            found += tube("rail", [(x, 0.0, z), (x, high, z)], bar, 8)
        for height in (high, high * 0.5):
            found += tube("rail", [(x0, height, z0), (x1, height, z1)], bar, 8)
    return found


def flood_head(columns=3, rows=3, lamp=0.6, gap=0.12):
    """A floodlight's head: a frame plate with `columns` x `rows` round lamps `lamp` across facing +z, its foot on
    y = 0, centred on x."""
    pitch = lamp + gap
    wide, high = columns * pitch + gap, rows * pitch + gap
    found = box("frame", (-wide / 2, 0.0, -0.25), (wide / 2, high, 0.0), 0.03)
    for column in range(columns):
        for row in range(rows):
            x = -wide / 2 + gap + pitch * column + lamp / 2
            y = gap + pitch * row + lamp / 2
            found += moved(turned("frame", [(0.0, 0.0), (lamp / 2 + 0.03, 0.0), (lamp / 2 + 0.03, 0.12),
                                            (0.0, 0.12)], segments=24), None, (x, y, 0.0))
            found += moved(turned("lamp", [(0.0, 0.1), (lamp / 2 - 0.02, 0.1), (lamp / 2 - 0.05, 0.16),
                                           (0.0, 0.17)], segments=24, smooth=True), None, (x, y, 0.0))
    return found


def ferris_wheel(radius=30.0, cabins=24, spokes=24, width=4.0, rim=0.35):
    """A big wheel facing ±z: twin rims `width` apart, `spokes` spokes to its hub, `cabins` gondolas hanging from
    its rim, on A-frame legs to y = 0 (the hub at `radius` + 4 m)."""
    hub = radius + 4.0
    found = []
    for side in (-width / 2, width / 2):
        circle = [(radius * math.cos(angle), hub + radius * math.sin(angle), side)
                  for angle in np.linspace(0, 2 * math.pi, 97)]
        found += tube("rim", circle, rim, 10)
        for number in range(spokes):
            angle = 2 * math.pi * number / spokes
            found += tube("spoke", [(0.0, hub, side), (radius * math.cos(angle), hub + radius * math.sin(angle), side)],
                          rim * 0.35, 6)
        for lean in (-1, 1):
            found += tube("leg", [(lean * radius * 0.45, 0.0, side * 1.8), (0.0, hub, side * 1.1)], rim * 1.6, 10)
    found += tube("leg", [(0.0, hub, -width / 2 - 1.0), (0.0, hub, width / 2 + 1.0)], 1.0, 16)
    for number in range(cabins):
        angle = 2 * math.pi * (number + 0.5) / cabins
        x, y = radius * math.cos(angle), hub + radius * math.sin(angle)
        found += box("cabin", (x - 1.1, y - 2.6, -1.1), (x + 1.1, y - 0.6, 1.1), 0.15)
    return found


def skyscraper(wide=40.0, deep=40.0, high=300.0, tiers=3, floor=4.0, lit=0.35, seed=1, spire=0.0):
    """A glass tower `wide` x `deep` x `high` (its foot on y = 0, centred), set back `tiers` times as it rises; each
    face a dark glass skin with its windows a few floors tall, a `lit` share of them lit (seeded), a mullion fin at
    each column, a neon band round the top of every tier and a `spire` metres tall on its crown; parts glass, fin,
    window, neon, spire."""
    generator = np.random.default_rng(seed)
    found = []
    low = 0.0
    for tier in range(tiers):
        share = 1.0 - 0.18 * tier
        half_x, half_z = wide * share / 2, deep * share / 2
        top = high * (tier + 1) / tiers if tier < tiers - 1 else high
        found += box("glass", (-half_x, low - (0.5 if tier else 0.0), -half_z), (half_x, top, half_z), 0.2)  # sunk in
        found += box("neon", (-half_x - 0.3, top - 2.0, -half_z - 0.3), (half_x + 0.3, top - 0.8, half_z + 0.3), 0.1)
        columns_x, columns_z = max(2, round(2 * half_x / 6.0)), max(2, round(2 * half_z / 6.0))
        rows = max(1, int((top - low - 3.0) / (floor * 2)))
        for (axis, half_across, half_depth, columns) in (("x", half_x, half_z, columns_x), ("z", half_z, half_x, columns_z)):
            pitch = 2 * half_across / columns
            for side in (-1.0, 1.0):
                for column in range(columns + 1):
                    at = -half_across + column * pitch
                    low_corner = [at - 0.4, low, side * half_depth - 0.6]
                    high_corner = [at + 0.4, top - 2.0, side * half_depth + 0.6]
                    if axis == "z":
                        low_corner = [low_corner[2], low_corner[1], low_corner[0]]
                        high_corner = [high_corner[2], high_corner[1], high_corner[0]]
                    found += box("fin", low_corner, high_corner, 0.05)
                for row in range(rows):
                    for column in range(columns):
                        if generator.random() > lit:
                            continue
                        left = -half_across + column * pitch + 0.8
                        right = left + pitch - 1.6
                        bottom = low + 1.5 + row * floor * 2
                        face = side * half_depth
                        corner_a = [left, bottom, face - 0.25]
                        corner_b = [right, bottom + floor * 2 - 1.2, face + 0.25]
                        if axis == "z":
                            corner_a = [corner_a[2], corner_a[1], corner_a[0]]
                            corner_b = [corner_b[2], corner_b[1], corner_b[0]]
                        found += box("window", corner_a, corner_b, 0.05)
        low = top
    if spire > 0:
        found += stood(turned("spire", [(0.0, high - 0.5), (wide * 0.06, high - 0.5), (0.15, high + spire), (0.0, high + spire)],
                              segments=12))
    return found


def mound(radius=800.0, high=400.0, segments=64, rings=24, seed=0):
    """A hill: a smooth round mound `radius` wide and `high` tall, its slopes a bell (falling as exp(-(2r/R)^2)),
    its rim a little uneven (seeded); part hill."""
    generator = np.random.default_rng(seed)
    wobble = 1.0 + 0.12 * np.sin(np.linspace(0, 2 * math.pi, segments, endpoint=False) * 3 + generator.random() * 6)
    profile = [(radius * (1.0 - step / rings), high * math.exp(-4.0 * (1.0 - step / rings) ** 2) - high * math.exp(-4.0))
               for step in range(rings)]
    points = [(0.0, 0.0, 0.0)]
    for ring_radius, height in profile:
        for number in range(segments):
            angle = 2 * math.pi * number / segments
            points.append((ring_radius * wobble[number] * math.cos(angle), height, ring_radius * wobble[number] * math.sin(angle)))
    points.append((0.0, high - high * math.exp(-4.0), 0.0))
    triangles = []
    count = len(profile)
    for number in range(segments):
        nxt = (number + 1) % segments
        triangles.append([0, 1 + number, 1 + nxt])  # the base, faced down below
    for ring in range(count - 1):
        for number in range(segments):
            nxt = (number + 1) % segments
            here, there = 1 + ring * segments + number, 1 + ring * segments + nxt
            triangles += [[here, there + segments, there], [here, here + segments, there + segments]]
    apex = len(points) - 1
    last = 1 + (count - 1) * segments
    for number in range(segments):
        triangles.append([last + number, apex, last + (number + 1) % segments])
    points = np.asarray(points)
    triangles = np.asarray(triangles)
    fixed = []
    middle = np.array([0.0, high * 0.3, 0.0])
    for triangle in triangles:
        corners = points[triangle]
        normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        fixed.append(triangle if np.dot(normal, corners.mean(axis=0) - middle) >= 0 else triangle[::-1])
    from score.stages.place_build.cockpit_kit import piece
    return [piece("hill", points, fixed, True)]


def ferry(long=32.0, wide=8.0, freeboard=1.6, decks=2, wake=90.0):
    """A ferry along +x, its bow at +x, its waterline at y = 0: a hull of `long` x `wide` standing `freeboard` out of
    the water (sunk 1 m below it) with a pointed bow, `decks` cabin decks set back from the bow, each a band of lit
    windows round it, and its wake: a thin V of foam on the water behind its stern, `wake` metres long, spreading."""
    half = wide / 2
    bow = long / 2
    outline = [(-bow, -half), (bow - wide, -half), (bow, 0.0), (bow - wide, half), (-bow, half)]
    found = moved(outline_slab("hull", outline, -1.0, freeboard), about("x", -90))  # the slab's z stood up as y
    low = freeboard
    for deck in range(decks):
        inset = 1.0 + deck * 1.2
        front, back = bow - wide - inset * 1.5, -bow + inset
        found += box("cabin", (back, low - 0.05, -half + inset), (front, low + 2.6, half - inset), 0.05)  # sunk in
        found += box("window", (back + 0.6, low + 1.0, -half + inset - 0.04),
                     (front - 0.6, low + 1.9, half - inset + 0.04), 0.02)
        low += 2.6
    stern = -bow
    for side in (-1.0, 1.0):  # each arm of the V a thin flat strip on the water, its far end wider and further out
        spread = half + wake * 0.18
        arm = [(stern - 1.0, side * half * 0.6), (stern - wake, side * spread),
               (stern - wake, side * (spread + 3.0 + wake * 0.04)), (stern - 1.0, side * (half * 0.6 + 1.2))]
        found += moved(outline_slab("wake", counter_clockwise(arm), 0.02, 0.08), about("x", -90))
    middle = [(stern - 0.5, -half * 0.7), (stern - wake * 0.5, -1.2), (stern - wake * 0.5, 1.2),
              (stern - 0.5, half * 0.7)]
    found += moved(outline_slab("wake", counter_clockwise(middle), 0.03, 0.09), about("x", -90))
    return found


def counter_clockwise(outline):
    """The plan `outline` [(x, y)] walked counter-clockwise (outline_slab's way), reversed when it was not."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    return outline if area > 0 else outline[::-1]


KINDS = {"ship": ship, "launch_ring": launch_ring, "lattice": lattice, "railing": railing, "flood_head": flood_head,
         "ferris_wheel": ferris_wheel, "skyscraper": skyscraper, "mound": mound, "ferry": ferry}


def write(path, kind, sizes):
    """The piece of `kind` (KINDS) with its `sizes` written at `path` as built (cockpit_kit.written); its parts."""
    if kind not in KINDS:
        raise ValueError(f"no launch piece {kind!r} (pieces are {', '.join(sorted(KINDS))})")
    return written(path, KINDS[kind](**sizes))
