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
- `water`: a harbour's water, one slab `wide` x `deep` and `depth` deep, its top at y = 0, shaded flat (its top's
  normals straight up: the pad's harbour laid as blocks drew smooth, each chamfered corner's lean spread over strips
  kilometres long, and the near water mirrored the city in a patch cut off by a ruler-straight edge); part water.
- `coast`: a stretch of coast round a harbour (2099 #161, the owner: "zero terrain", the pad on a flat plane with no
  land, shore or sea round it): one closed solid `wide` (x, centred) whose shoreline wobbles about z = 0 (the
  waterline y = 0, seeded), its land rolling inland (-z) `deep` metres in seeded hills up to `rise` over a `shore`
  band (a beach or rock edge rising to its `berm`), its sea bed sinking seaward (+z) `sea` metres out to `depth`
  under the water; each `site` [x, z, radius, height] levelled at its height and eased into the land round it (a
  launch site's deck); parts land and shore (the shore band and the sea bed: a sand or rock look). Lay `water` over it
  for the sea itself.
- `ferry`: a harbour ferry on the water (its waterline at y = 0): a hull with a pointed bow, a two-deck cabin with
  its window bands lit, and its wake spreading behind it on the water; parts hull, cabin, window, wake.
- `door_wall`: a flat wall `wide` (x, centred) by `high` (y, its foot on 0) and `thick` (z, centred) holding a
  doorway of a door's own outline (`rows`: [up, left, right] from its sill up, across from the doorway's middle, which
  stands on the wall's x = 0, as a join reads a leaf's middle): the access arm's end
  cut to the capsule's round hatch (2099 #161), so the walkway's door is the hatch's shape, never a rectangle the
  hatch is seated in; one closed solid, part frame. Its doorway is recorded as the place's (`doorways`), so a
  neighbour place joins it there (area/).

    doorways(kind, sizes)       a piece's doorways in its own frame ({key: sill middle, inward, wide, sill, head})
"""
import math

import numpy as np

from score.stages.place_build.cockpit_kit import about, box, moved, outline_slab, tube, turned, written

UP = about("x", -90)
BAND_STEP = 0.25  # metres between the rings of a ship's hatch band, round its hatch's rows
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


def ship(radius=3.74, high=54.0, nose=13.5, ring=2.0, segments=96, engines=6, fore=2.2, aft=3.0, aft_chord=10.4,
         hatch=None):
    """The ship standing on its aft skirt's foot (y = 0), its engine bells inside the skirt, its body `radius`, its tip
    at `high`; a weld seam every `ring` metres up the barrel (none with `ring` 0: one seamless steel barrel); its
    forward flaps `fore` metres out on the x axis, its aft flaps `aft` out and `aft_chord` along the hull likewise.
    With `hatch` ({around, sill, rows, low, high, thick}: hatch_band's) its skin from `low` to `high` is a band
    `thick` deep round a hollow holding the crew capsule, opened at the hatch the access arm meets (2099 #161: the
    pad's walkway door led into the steel), the hull under it and the nose over it closed solids HATCH_GAP apart."""
    bells = 1.4
    foot = bells  # the skirt's foot
    shoulder = high - nose
    tip_from = shoulder + nose * 0.8
    profile = nose_profile(radius, shoulder, nose)
    steel = [point for point in profile if point[1] <= tip_from]
    black = [point for point in profile if point[1] >= steel[-1][1]]
    if hatch:
        found = hatched(radius, nose, foot, shoulder, steel, segments, **hatch)
    else:
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


WATER_LINES = (0.0, 0.01, 0.025, 0.06, 0.15, 0.4, 1.0)  # shares of the half width the water's grid lines stand at


def water(wide=12000.0, deep=12000.0, depth=3.0):
    """A harbour's water: a closed flat-shaded slab `wide` (x) by `deep` (z), `depth` deep, its top at y = 0,
    centred, its faces a grid finer near its middle (WATER_LINES), so the place laid on it has the water's corners
    round it (the check keeps a ground's faces by their corners near the place)."""
    across = np.unique([sign * share * wide / 2 for share in WATER_LINES for sign in (-1.0, 1.0)])
    along = np.unique([sign * share * deep / 2 for share in WATER_LINES for sign in (-1.0, 1.0)])
    count_x, count_z = len(across), len(along)
    grid_x, grid_z = np.meshgrid(across, along, indexing="ij")
    top = np.column_stack([grid_x.ravel(), np.zeros(grid_x.size), grid_z.ravel()])
    points = np.vstack([top, top - [0.0, depth, 0.0]])
    below = len(top)

    def at(column, row, under=False):
        return column * count_z + row + (below if under else 0)

    triangles = []
    for column in range(count_x - 1):
        for row in range(count_z - 1):
            corners = [at(column, row), at(column, row + 1), at(column + 1, row + 1), at(column + 1, row)]
            triangles += [[corners[0], corners[1], corners[2]], [corners[0], corners[2], corners[3]]]  # up
            under = [corner + below for corner in corners]
            triangles += [[under[0], under[2], under[1]], [under[0], under[3], under[2]]]  # down
    rim = ([at(column, 0) for column in range(count_x)] + [at(count_x - 1, row) for row in range(1, count_z)]
           + [at(column, count_z - 1) for column in range(count_x - 2, -1, -1)]
           + [at(0, row) for row in range(count_z - 2, 0, -1)])
    for here, there in zip(rim, rim[1:] + rim[:1]):
        triangles += [[here, here + below, there + below], [here, there + below, there]]
    triangles = np.asarray(triangles)
    corners = points[triangles]
    faces = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    outward = np.einsum("ij,ij->i", faces, corners.mean(axis=1) - [0.0, -depth / 2, 0.0]) >= 0
    triangles[~outward] = triangles[~outward][:, ::-1]
    from score.stages.place_build.cockpit_kit import piece
    return [piece("water", points, triangles, False)]


COAST_WAVES = 4  # the seeded sines summed for a coast's shoreline and its hills each


def seeded_waves(generator, count, longest, size):
    """A smooth seeded relief, a function of (x, z) in [-size, size]: `count` sines of wavelengths from `longest` down
    by halves, each at a random heading and phase, its amplitude halving with them."""
    waves = [(generator.uniform(0, 2 * math.pi), generator.uniform(0, 2 * math.pi), longest / 2 ** number,
              size / 2 ** number) for number in range(count)]
    total = sum(wave[3] for wave in waves)

    def relief(x, z):
        return sum(height * np.sin(2 * math.pi * (x * math.cos(heading) + z * math.sin(heading)) / length + phase)
                   for heading, phase, length, height in waves) * size / total

    return relief


def coast_heights(x, z, wide, deep, sea, rise, shore, berm, depth, sites, seed):
    """A coast's surface height at (x, z) and how far inland of its shoreline each point is (metres; negative out
    at sea): the sea bed falling from the waterline to `depth` over the first quarter of `sea`, the shore band rising
    to `berm`, the hills inland rising to `rise` over a third of `deep` (coast's words), every site levelled."""
    generator = np.random.default_rng(seed)
    shoreline = seeded_waves(generator, COAST_WAVES, wide / 2, shore * 1.5)
    hills = seeded_waves(generator, COAST_WAVES, deep, 0.5)
    inland = shoreline(x, 0.0) - z
    out = np.clip(-inland / (sea * 0.25), 0.0, 1.0)
    height = np.where(inland <= 0, -depth * out * out * (3 - 2 * out), berm * np.clip(inland / shore, 0.0, 1.0))
    past = np.clip(inland - shore, 0.0, None)
    height = height + rise * (1.0 - np.exp(-past / (deep / 3))) * (0.6 + hills(x, z))
    for across, along, radius, level in sites:
        reach = np.hypot(x - across, z - along)
        ease = np.clip((reach - radius) / (radius * 0.5), 0.0, 1.0)
        ease = ease * ease * (3 - 2 * ease)
        height = level + (height - level) * ease
    return height, inland


def coast(wide=4000.0, deep=1500.0, sea=800.0, rise=60.0, shore=40.0, berm=2.5, depth=8.0, cell=20.0, sites=(),
          seed=0):
    """A coast (the docstring's `coast`): a heightfield on a grid of `cell` metres, closed by a flat bottom 2 m under
    the sea bed's deepest and its four sides; parts land and shore (inland of the shore band, or not)."""
    across = np.linspace(-wide / 2, wide / 2, int(round(wide / cell)) + 1)
    along = np.linspace(-deep, sea, int(round((deep + sea) / cell)) + 1)
    grid_x, grid_z = np.meshgrid(across, along, indexing="ij")
    heights, inland = coast_heights(grid_x, grid_z, wide, deep, sea, rise, shore, berm, depth,
                                    [tuple(float(value) for value in site) for site in sites], seed)
    count_x, count_z = grid_x.shape
    top = np.column_stack([grid_x.ravel(), heights.ravel(), grid_z.ravel()])
    floor = float(heights.min()) - 2.0
    points = np.vstack([top, np.column_stack([grid_x.ravel(), np.full(grid_x.size, floor), grid_z.ravel()])])
    below = len(top)
    cells = np.arange(count_x * count_z).reshape(count_x, count_z)[:-1, :-1].ravel()
    corners = np.column_stack([cells, cells + 1, cells + count_z + 1, cells + count_z])
    upward = np.vstack([corners[:, [0, 1, 2]], corners[:, [0, 2, 3]]])  # +z then +x under a corner: faces up
    middle_inland = inland.ravel()[upward].mean(axis=1)
    rim = ([cells_at for cells_at in range(0, count_z)]
           + [column * count_z + count_z - 1 for column in range(1, count_x)]
           + [(count_x - 1) * count_z + row for row in range(count_z - 2, -1, -1)]
           + [column * count_z for column in range(count_x - 2, 0, -1)])
    sides = []
    for here, there in zip(rim, rim[1:] + rim[:1]):
        sides += [[here, there, there + below], [here, there + below, here + below]]
    sides = np.asarray(sides)
    centre = np.array([0.0, 0.0, (sea - deep) / 2])
    faces = points[sides]
    normal = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    inward = np.einsum("ij,ij->i", normal[:, [0, 2]], (faces.mean(axis=1) - centre)[:, [0, 2]]) < 0
    sides[inward] = sides[inward][:, ::-1]
    closed = np.vstack([upward[middle_inland <= shore], upward[:, ::-1] + below, sides])
    from score.stages.place_build.cockpit_kit import piece
    return [piece("land", points, upward[middle_inland > shore], True), piece("shore", points, closed, True)]


HATCH_GAP = 0.0005  # metres between a hatched ship's band and the hull under it and the nose over it (no face shared)


def hatched(radius, nose, foot, shoulder, steel, segments, around, sill, rows, low, high, thick=0.05):
    """A hatched ship's hull (ship's `hatch`): the hull closed under `low`, the hatch band (hatch_band) from `low` to
    `high` and the nose closed over `high`, each a closed solid; ValueError when the band leaves the steel or the
    hatch the band."""
    radius_at = lambda height: radius if height <= shoulder else nose_radius(radius, nose, height - shoulder)  # noqa
    rows = [[float(value) for value in row] for row in rows]
    if not foot + 0.8 + HATCH_GAP < low < sill + rows[0][0] <= sill + rows[-1][0] < high < steel[-1][1] - HATCH_GAP:
        raise ValueError(f"a ship's hatch band stands on its steel ({foot + 0.8} to {steel[-1][1]} m) round its hatch "
                         f"({sill + rows[0][0]} to {sill + rows[-1][0]} m), not {low} to {high}")
    if any(max(abs(row[1]), abs(row[2])) >= radius_at(sill + row[0]) - thick for row in rows):
        raise ValueError("a ship's hatch is narrower than its skin")
    under, over = low - HATCH_GAP, high + HATCH_GAP
    lower = ([(0.0, foot), (radius * 0.92, foot), (radius, foot + 0.8)] + [point for point in steel if point[1] < under]
             + [(radius_at(under), under), (0.0, under)])
    upper = ([(0.0, over), (radius_at(over), over)] + [point for point in steel if point[1] > over]
             + [(0.0, steel[-1][1])])
    return (stood(turned("hull", lower, segments=segments, smooth=False))
            + hatch_band(radius_at, low, high, around, sill, rows, thick, segments)
            + stood(turned("hull", upper, segments=segments, smooth=False)))


def door_rows(wide, high, rows):
    """A door wall's doorway rows ([up, left, right] from its sill up) as floats, refused (ValueError) unless two or
    more rise strictly, each left of its right, all inside the wall and under its top."""
    rows = [[float(value) for value in row] for row in rows]
    if len(rows) < 2 or any(len(row) != 3 for row in rows):
        raise ValueError("a door wall's doorway is two or more rows of up, left, right")
    if any(later[0] <= row[0] for row, later in zip(rows, rows[1:])) or rows[0][0] < 0 or rows[-1][0] >= high:
        raise ValueError(f"a door wall's doorway rows rise from 0 or more to under its top {high} m")
    if any(not -wide / 2 < left < right < wide / 2 for _, left, right in rows):
        raise ValueError(f"each doorway row's left stands left of its right, inside the wall {wide} m wide")
    return rows


def thickened(part, front, outside, inside):
    """One closed solid from a face laid in its own two coordinates: `front` its triangles over the keys of its points
    (hashable, wound anticlockwise as seen from outside), `outside` and `inside` each putting the keys (a list) where
    the face's outer and inner skins stand ([n, 3]); a side between the skins along every edge only one triangle has
    (the rim and a doorway's reveal)."""
    keys = {}
    for triangle in front:
        for corner in triangle:
            keys.setdefault(corner, len(keys))
    count = len(keys)
    points = np.vstack([outside(list(keys)), inside(list(keys))])
    front = [[keys[corner] for corner in triangle] for triangle in front]
    used = set()
    for triangle in front:
        used.update(zip(triangle, triangle[1:] + triangle[:1]))
    rim = [(here, there) for (here, there) in used if (there, here) not in used]
    triangles = front + [[a + count, c + count, b + count] for a, b, c in front]
    for here, there in rim:
        triangles += [[there, here, here + count], [there, here + count, there + count]]
    from score.stages.place_build.cockpit_kit import piece
    return [piece(part, points, triangles, False)]


def key(across, up):
    return (round(float(across), 7), round(float(up), 7))


def door_wall(wide=2.4, high=2.6, thick=0.1, rows=((0.0, -0.45, 0.45), (2.0, -0.45, 0.45))):
    """A flat wall holding a doorway of a door's own outline (`rows`, door_rows): its front face (z = thick / 2) laid
    in quads row by row, either side of the doorway between its rows, under the doorway's sill and over its head split
    where the doorway's corners stand (no corner of one quad on another's edge), its back face the same, and a side
    between them along every edge only one quad has (the wall's rim and the doorway's reveal): one closed solid."""
    rows = door_rows(wide, high, rows)
    half = wide / 2
    quads = []
    for (low, left_low, right_low), (top, left_top, right_top) in zip(rows, rows[1:]):
        quads += [[(-half, low), (left_low, low), (left_top, top), (-half, top)],
                  [(right_low, low), (half, low), (half, top), (right_top, top)]]
    for low, top, (_, left, right) in ((0.0, rows[0][0], rows[0]), (rows[-1][0], high, rows[-1])):
        if top > low:
            edges = [-half, left, right, half]
            quads += [[(edges[at], low), (edges[at + 1], low), (edges[at + 1], top), (edges[at], top)]
                      for at in range(3)]
    front = []
    for quad in quads:
        at = [key(*corner) for corner in quad]
        front += [[at[0], at[1], at[2]], [at[0], at[2], at[3]]]
    return thickened("frame", front, lambda flat: np.column_stack([flat, np.full(len(flat), thick / 2)]),
                     lambda flat: np.column_stack([flat, np.full(len(flat), -thick / 2)]))


def zipped(below, above):
    """The triangles (anticlockwise, the first coordinate across) of the strip between two runs of points [(order,
    key)] each walked one way (the lower run, then the upper), taking each next point from the run whose next stands
    first."""
    triangles, low, high = [], 0, 0
    while low < len(below) - 1 or high < len(above) - 1:
        if high == len(above) - 1 or (low < len(below) - 1 and below[low + 1][0] <= above[high + 1][0]):
            triangles.append([below[low][1], below[low + 1][1], above[high][1]])
            low += 1
        else:
            triangles.append([below[low][1], above[high + 1][1], above[high][1]])
            high += 1
    return triangles


def hatch_band(radius_at, low, high, around, sill, rows, thick=0.05, segments=96):
    """The ship's skin from `low` to `high` (its outer face `radius_at(y)` from the axis, `thick` deep) holding a
    hatch: an opening of `rows` ([up, left, right] from its `sill` up, across from its middle, as door_rows) on the
    skin seen along the level way out at `around` degrees (from +z toward +x), so the access arm's walkway meets the
    capsule's hatch through it (2099 #161). Laid in rings of `segments` round, a ring every BAND_STEP and one at each
    of the hatch's rows, each split where the hatch's sides stand (no corner on another's edge); its inner skin the
    outer's points drawn in `thick`, the hatch's sides kept parallel to its way out: one closed solid, part hull."""
    rows = [[float(value) for value in row] for row in rows]
    turn = math.radians(around)
    sides = {round(sill + up, 7): (left, right) for up, left, right in rows}
    bottom, top = min(sides), max(sides)
    grid = np.linspace(low, high, max(2, int(math.ceil((high - low) / BAND_STEP))) + 1)
    heights = sorted({round(float(height), 7) for height in grid if not bottom <= height <= top} | set(sides))
    ring = np.linspace(-math.pi, math.pi, segments + 1)[:-1]
    clear = math.pi / segments * 0.5  # a ring's angle this near a hatch side is left out of its run

    def run(height, beside):
        """The (order, key) points round the skin at `height`: the ring's angles and the hatch's sides where it
        stands; `beside` (a row of the hatch), from its right side round to its left, else the whole ring closed."""
        side = sides.get(height)
        if side is None:
            found = [(angle, (round(angle, 7), height)) for angle in ring]
            return found + [(found[0][0] + 2 * math.pi, found[0][1])]
        left, right = (math.asin(edge / radius_at(height)) for edge in side)
        others = [angle for angle in ring if not left - clear <= angle <= right + clear]
        ends = [(left, (("side", round(side[0], 7)), height)), (right, (("side", round(side[1], 7)), height))]
        if not beside:
            found = sorted([(angle, (round(angle, 7), height)) for angle in others] + ends)
            return found + [(found[0][0] + 2 * math.pi, found[0][1])]
        walked = sorted((angle if angle > right else angle + 2 * math.pi, (round(angle, 7), height)) for angle in others)
        return [ends[1]] + walked + [(left + 2 * math.pi, ends[0][1])]

    front = []
    for below, above in zip(heights, heights[1:]):
        beside = below in sides and above in sides
        front += zipped(run(below, beside), run(above, beside))

    def placed(keys, inset):
        found = []
        for angle, height in keys:
            rho = radius_at(height) - inset
            if isinstance(angle, tuple):
                angle = math.asin(angle[1] / rho)
            found.append((rho * math.sin(turn + angle), height, rho * math.cos(turn + angle)))
        return np.asarray(found, dtype=np.float64)

    return thickened("hull", front, lambda keys: placed(keys, 0.0), lambda keys: placed(keys, thick))


KINDS = {"ship": ship, "launch_ring": launch_ring, "lattice": lattice, "railing": railing, "flood_head": flood_head,
         "ferris_wheel": ferris_wheel, "skyscraper": skyscraper, "mound": mound, "ferry": ferry,
         "water": water, "coast": coast, "door_wall": door_wall}


def doorways(kind, sizes):
    """The doorways a piece of `kind` holds with its `sizes`, in its own frame: {key: {middle (its sill middle),
    inward (its +z: give the join its inward way), wide, sill, head}}; none but a door wall's."""
    if kind != "door_wall":
        return {}
    defaults = door_wall.__defaults__
    wide, high = float(sizes.get("wide", defaults[0])), float(sizes.get("high", defaults[1]))
    rows = door_rows(wide, high, sizes.get("rows", defaults[3]))
    left, right = min(row[1] for row in rows), max(row[2] for row in rows)
    return {"door": {"middle": [0.0, rows[0][0], 0.0], "inward": [0.0, 0.0, 1.0],
                     "wide": round(right - left, 4), "sill": rows[0][0], "head": rows[-1][0]}}


def write(path, kind, sizes):
    """The piece of `kind` (KINDS) with its `sizes` written at `path` as built (cockpit_kit.written); its parts."""
    if kind not in KINDS:
        raise ValueError(f"no launch piece {kind!r} (pieces are {', '.join(sorted(KINDS))})")
    return written(path, KINDS[kind](**sizes))
