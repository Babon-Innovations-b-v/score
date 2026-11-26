"""A car built in code (2099 #161, the owner on the street's TRELLIS.2 police car, 2026-11-25: "door coming out of a
door", "yuck"): a saloon's body lofted from its sections along its length, its arches cut round its wheels, its
greenhouse of glass, its cabin seen through the glass and the open door, and one real door: the front door on the
right (Hong Kong drives on the left), the body's own skin and window over it cut out of the body and the greenhouse, so
when it swings open on its hinge at its front edge the opening behind it is the cabin, never a second door.

    car_parts(size)        the parts of a car of `size` (across, tall, along; y up, its front at +z), each a part of
                           moving_parts (its node's name its joint, its origin its pivot, its finish a library recipe)
    painted(scene, record, palette)   every part's material from the place's palette variant its part names
                                      (FINISHES), as glTF PBR: the variant's token colour, roughness and metal

A part's finish is (recipe, palette variant): the recipe names the library's, the variant the place's surface
library's (palette.json `families`), so the model's paint is the library's and no colour is the build's own.
"""
import numpy as np

# The car's sides as shares of its length from the rear (0) to the front (1): (share, top of its lower body, its
# bottom, its half width), the tops the boot deck, the beltline and the bonnet; heights as shares of its height.
LOWER = ((0.0, 0.42, 0.24, 0.86), (0.025, 0.58, 0.14, 0.95), (0.08, 0.63, 0.12, 0.99), (0.24, 0.65, 0.12, 1.0),
         (0.70, 0.65, 0.12, 1.0), (0.80, 0.61, 0.12, 1.0), (0.93, 0.55, 0.13, 0.97), (0.985, 0.47, 0.16, 0.92),
         (1.0, 0.36, 0.24, 0.86))
# The greenhouse over the beltline: (share, roof height as a share of the car's height), from the rear screen's foot
# to the windscreen's.
GREENHOUSE = ((0.20, 0.655), (0.27, 0.86), (0.36, 0.985), (0.58, 1.0), (0.66, 0.92), (0.75, 0.655))
GLASS_IN, ROOF_IN = 0.88, 0.70  # the greenhouse's half width at the beltline and at its roof, as shares of the body's
SECTIONS, AROUND = 240, 72  # sections along the length and points round each
ROUNDNESS = 5.0  # the sections' superellipse power: higher is boxier
WHEEL_RADIUS, TYRE_WIDE, RIM_SHARE = 0.215, 0.115, 0.66  # as shares of the height and width; the rim's of the tyre
AXLES = (0.17, 0.82)  # the axles as shares of the length from the rear
ARCH_ROOM = 1.12  # an arch's radius over its wheel's
DOOR = (0.47, 0.69)  # the front door's rear and front edges as shares of the length (its hinge at the front)
DOOR_FOOT = 0.20  # the door's foot as a share of the height
SKIN = 0.03  # a door's thickness, in metres
LIGHT_BAR = 0.12  # the light bar's height on the roof, in metres (the car's height its top)
WHEEL_FACES = 64
SPOKES = 5  # a rim's spokes
GLASS_SEEN = 0.97  # how much of what is behind the car's tinted glass it hides (glTF alpha): a patrol car's dark tint (at 0.93
# the seat backs stood as black slabs through the side glass, night car round 3)
ROOF_BAND = 0.9  # the greenhouse's roof cap: the ring's points this high up its section and over
FINISHES = {"body": ("painted_metal", "car_body_paint"), "door": ("painted_metal", "car_body_paint"),
            "glass": ("glass", "car_window"), "door_window": ("glass", "car_window"),
            "cabin": ("rubber", "lantern_cable"), "trim": ("bare_metal", "car_chrome"),
            "headlamps": ("glowing", "lamp_head_glow"), "tail_lamps": ("glowing", "sign_lettering_red"),
            "bar_base": ("rubber", "tyre_rubber"),
            "siren_blue": ("glowing", "siren_blue"), "siren_red": ("glowing", "siren_red"),
            "plates": ("painted_metal", "licence_plate"), "tyre": ("rubber", "tyre_rubber"),
            "rim": ("painted_metal", "gunmetal_steel"), "seams": ("rubber", "tyre_rubber")}
SEAMS = (0.27, 0.47, 0.69)  # the doors' shut lines as shares of the length from the rear, on both sides
END_ROOM = 0.03  # the body stops this short of the car's ends, metres: room for the plates and bumper bands on them
SEAM_WIDE, SEAM_PROUD = 0.008, 0.002  # a shut line's width and how far it stands off the skin, in metres


def along(table, share, column):
    """A column of a profile table at a share of the length, eased between its rows by a monotone cubic, so the body's
    lines run smooth through its rows (straight between them they creased the bonnet and boot into facets, night car
    round 2)."""
    from scipy.interpolate import PchipInterpolator
    shares = [row[0] for row in table]
    return float(PchipInterpolator(shares, [row[column] for row in table])(np.clip(share, shares[0], shares[-1])))


def ring(half_wide, bottom, top, power=ROUNDNESS, count=AROUND):
    """A section's points (count x 2: x, y), a superellipse between `bottom` and `top`, starting at its right side
    (-x) and going round under it."""
    angles = np.linspace(0.0, 2 * np.pi, count, endpoint=False) + np.pi
    cos, sin = np.cos(angles), np.sin(angles)
    exponent = 2.0 / power
    middle, half_tall = (bottom + top) / 2, (top - bottom) / 2
    return np.column_stack([half_wide * np.sign(cos) * np.abs(cos) ** exponent,
                            middle + half_tall * np.sign(sin) * np.abs(sin) ** exponent])


def lofted(sections, places):
    """A closed mesh through `sections` (each a ring of the same count) at lengths `places`, capped at both ends:
    (vertices, faces, the section each side face starts at, the ring point each starts at)."""
    count = len(sections[0])
    vertices = np.vstack([np.column_stack([section, np.full(count, place)]) for section, place in zip(sections, places)])
    faces, at, round_at = [], [], []
    for number in range(len(sections) - 1):
        for point in range(count):
            here, beside = number * count + point, number * count + (point + 1) % count
            faces += [(here, beside + count, beside), (here, here + count, beside + count)]
            at += [number, number]
            round_at += [point, point]
    ends = []
    for number, flip in ((0, True), (len(sections) - 1, False)):
        centre = len(vertices) + len(ends)
        ends.append(np.append(np.mean(sections[number], axis=0), places[number]))
        for point in range(count):
            first, second = number * count + point, number * count + (point + 1) % count
            faces.append((centre, first, second) if flip else (centre, second, first))
            at.append(-1)
            round_at.append(-1)
    return np.vstack([vertices, ends]), np.array(faces), np.array(at), np.array(round_at)


def mesh_of(vertices, faces):
    import trimesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.fix_normals()
    # Facing out from the car's long middle line: on an open skin (its door cut out) fix_normals chose its winding by
    # chance and turned the whole body inward, so the game drew its sides away and the cabin stood bare (night car
    # round 3).
    centres = mesh.triangles_center
    out = centres[:, :2] - np.array([0.0, centres[:, 1].mean()])
    if np.sum(np.einsum("ij,ij->i", mesh.face_normals[:, :2], out) * mesh.area_faces) < 0:
        mesh.invert()
    return mesh


def kept(vertices, faces, keep):
    """The faces chosen by `keep` as their own mesh, the points no kept face uses dropped."""
    mesh = mesh_of(vertices, faces[keep])
    mesh.remove_unreferenced_vertices()
    return mesh


def arch_bottom(place, bottom, axles, radius):
    """The body's bottom at a length `place`, raised round each wheel to its arch."""
    for axle in axles:
        reach = radius * ARCH_ROOM
        if abs(place - axle) < reach:
            bottom = max(bottom, radius + np.sqrt(reach ** 2 - (place - axle) ** 2) * 0.96)
    return bottom


def door_faces(vertices, faces, at_section, places, span, foot, top, side):
    """Side faces of a loft lying on the `side` (-1 right, +1 left) within the door's span and heights."""
    middles = vertices[faces].mean(axis=1)
    return (at_section >= 0) & (middles[:, 2] > span[0]) & (middles[:, 2] < span[1]) & \
        (middles[:, 1] > foot) & (middles[:, 1] < top) & (np.sign(middles[:, 0]) == side) & \
        (np.abs(middles[:, 0]) > 0.6 * np.abs(vertices[:, 0]).max())


def shell(mesh, thickness):
    """A thin solid of a side's skin: its faces and the same moved in towards the car's middle by `thickness`, their
    rims joined."""
    import trimesh
    inner = mesh.copy()
    inner.vertices = inner.vertices - np.column_stack([np.sign(inner.vertices[:, 0]) * thickness,
                                                       np.zeros(len(inner.vertices)), np.zeros(len(inner.vertices))])
    inner.invert()
    edges = trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1)
    rim = mesh.edges[edges]
    count = len(mesh.vertices)
    sides = [(first, second, second + count) for first, second in rim] + \
            [(first, second + count, first + count) for first, second in rim]
    joined = trimesh.Trimesh(vertices=np.vstack([mesh.vertices, inner.vertices]),
                             faces=np.vstack([mesh.faces, inner.faces + count, np.array(sides).reshape(-1, 3)]),
                             process=False)
    return joined


def body_section(across, tall, along_length, axles, radius, place):
    """The lower body's section (a ring of points, x and y) at a length `place` from the car's middle."""
    share = place / along_length + 0.5
    bottom = arch_bottom(place, along(LOWER, share, 2) * tall, axles, radius)
    top = along(LOWER, share, 1) * tall
    return ring(along(LOWER, share, 3) * across / 2, min(bottom, top - 0.08), top)


def body_and_door(across, tall, along_length, axles, radius):
    """The lower body (its door's skin cut out) and the door's skin."""
    places = np.linspace(-along_length / 2 + END_ROOM, along_length / 2 - END_ROOM, SECTIONS)
    sections = [body_section(across, tall, along_length, axles, radius, place) for place in places]
    vertices, faces, at_section, _ = lofted(sections, places)
    span = [(share - 0.5) * along_length for share in DOOR]
    door = door_faces(vertices, faces, at_section, places, span, DOOR_FOOT * tall, along(LOWER, 0.6, 1) * tall + 0.01,
                      -1)
    return kept(vertices, faces, ~door), shell(kept(vertices, faces, door), SKIN), span


def greenhouse(across, tall, along_length, span):
    """The greenhouse's glass (its door window cut out), the door's window and the roof's painted cap."""
    first, last = GREENHOUSE[0][0], GREENHOUSE[-1][0]
    places = np.linspace((first - 0.5) * along_length, (last - 0.5) * along_length, SECTIONS // 2)
    shares = (places + along_length / 2) / along_length
    belt = along(LOWER, 0.5, 1) * tall - 0.02
    sections = []
    for share in shares:
        roof = along(GREENHOUSE, share, 1) * tall
        half = along(LOWER, share, 3) * across / 2
        points = ring(1.0, 0.0, 1.0, power=3.0)
        # Its foot just under the body's own top at that length, not one beltline height: over the boot deck's rise the
        # glass's foot ran a centimetre under the paint, the two met in a stepped seam and the tint showed under the
        # rear screen (night car round 2).
        foot = along(LOWER, share, 1) * tall - 0.02
        heights = foot + (roof - foot) * np.clip(points[:, 1], 0.0, 1.0)
        rise = np.clip(points[:, 1], 0.0, 1.0)
        sections.append(np.column_stack([points[:, 0] * half * (GLASS_IN + (ROOF_IN - GLASS_IN) * rise), heights]))
    vertices, faces, at_section, round_at = lofted(sections, places)
    window = door_faces(vertices, faces, at_section, places, span, belt, tall * 0.93, -1)
    roof = roof_faces(at_section, round_at, [along(GREENHOUSE, share, 1) for share in shares]) & ~window
    glass = kept(vertices, faces, ~window & ~roof)
    return glass, shell(kept(vertices, faces, window), 0.006), kept(vertices, faces, roof)


def roof_faces(at_section, round_at, roof_shares):
    """The greenhouse's faces under its painted roof cap: a band of whole ring points along whole sections, so its
    edges run straight along the car and across it (picked by face middles they were jagged, night car round 1)."""
    points = ring(1.0, 0.0, 1.0, power=3.0)[:, 1]
    count = len(points)
    high = (points >= ROOF_BAND) & (np.roll(points, -1) >= ROOF_BAND)
    flat = np.asarray(roof_shares) >= max(roof_shares) * 0.97
    inside = at_section >= 0
    return inside & high[np.where(inside, round_at, 0) % count] & flat[np.clip(at_section, 0, len(flat) - 1)]


def cabin(across, tall, along_length):
    """The cabin seen through the glass and the open door: its liner (inside the body and greenhouse, its faces
    turned inward), two front seats, a rear bench, a
    dashboard and a steering wheel."""
    import trimesh
    half = across / 2 * 0.86
    rear, front = (0.28 - 0.5) * along_length, (0.71 - 0.5) * along_length
    belt = along(LOWER, 0.5, 1) * tall - 0.02
    places = np.linspace(rear, front, 24)
    sections = []
    for place in places:
        share = place / along_length + 0.5
        half = along(LOWER, share, 3) * across / 2
        low_half = half - 0.06
        # Inside the glass all the way up: at the beltline the glass stands GLASS_IN in from the body, and a liner as
        # wide as the body below came through it in a stepped line along both sides (night car round 3).
        belt_half, roof_half = half * GLASS_IN - 0.04, half * ROOF_IN - 0.06
        top = max(along(GREENHOUSE, share, 1) * tall - 0.06, belt + 0.02)
        sections.append(np.array([(-low_half, tall * 0.22), (-low_half, belt - 0.03), (-belt_half, belt),
                                  (-roof_half, top), (roof_half, top), (belt_half, belt), (low_half, belt - 0.03),
                                  (low_half, tall * 0.22)])[::-1])
    vertices, faces, _, _ = lofted(sections, places)
    liner = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    liner.fix_normals()
    liner.invert()
    parts = [liner]
    # The seats, bench and dash within the greenhouse's roof width: sized by the loop's last (widest, frontmost) body
    # half they stood out through the side glass as black posts (night car round 4: 2099-preview/night/car/round3-side.png).
    room = along(LOWER, 0.5, 3) * across / 2 * ROOF_IN - 0.08
    for side in (-1, 1):
        seat = trimesh.creation.box(extents=(room * 0.8, tall * 0.12, 0.5))
        seat.apply_translation((side * room * 0.5, tall * 0.33, along_length * 0.04))
        back = trimesh.creation.box(extents=(room * 0.8, tall * 0.36, 0.12))
        back.apply_transform(trimesh.transformations.rotation_matrix(-0.2, (1, 0, 0)))
        back.apply_translation((side * room * 0.5, tall * 0.55, along_length * 0.04 - 0.28))
        parts += [seat, back]
    bench = trimesh.creation.box(extents=(room * 1.9, tall * 0.12, 0.5))
    bench.apply_translation((0, tall * 0.33, -along_length * 0.12))
    bench_back = trimesh.creation.box(extents=(room * 1.9, tall * 0.34, 0.12))
    bench_back.apply_translation((0, tall * 0.53, -along_length * 0.12 - 0.3))
    dash = trimesh.creation.box(extents=(room * 2.0, tall * 0.14, 0.35))
    dash.apply_translation((0, tall * 0.6, front - 0.2))
    wheel = trimesh.creation.torus(0.18, 0.018)
    wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2 - 0.4, (1, 0, 0)))
    wheel.apply_translation((-room * 0.5, tall * 0.66, front - 0.48))
    return parts + [bench, bench_back, dash, wheel]


def lamps(across, tall, along_length):
    """(headlamps, tail lamps, plates, the light bar's blue and red lenses, its dark base, the trim: a grille bar and door
    handles, the wing mirrors in the body's paint)."""
    import trimesh
    nose, tail = along_length / 2, -along_length / 2

    def strip(size, middle):
        return trimesh.creation.box(extents=size).apply_translation(middle)

    head_y, tail_y = along(LOWER, 0.97, 1) * tall - 0.06, along(LOWER, 0.03, 1) * tall - 0.05
    headlamps = [strip((across * 0.24, 0.05, 0.04), (side * across * 0.32, head_y, nose - 0.035)) for side in (-1, 1)]
    # Two lamp clusters at the tail's corners and a thin bar between them, as the concept's saloon shows them lit.
    tail_lamps = [strip((across * 0.2, 0.085, 0.035), (side * across * 0.33, tail_y, tail + 0.04)) for side in (-1, 1)]
    tail_lamps.append(strip((across * 0.46, 0.022, 0.03), (0, tail_y + 0.02, tail + 0.03)))
    plates = [strip((0.52, 0.11, 0.012), (0, 0.31 * tall, nose - 0.012)),
              strip((0.52, 0.11, 0.012), (0, 0.335 * tall, tail + 0.012))]  # in the room left before the body's ends
    blue, red, base = light_bar(across, tall)
    grille = [strip((across * 0.36, 0.025, 0.03), (0, head_y - 0.02, nose - 0.025))]
    handle_y = along(LOWER, 0.5, 1) * tall - 0.1
    handles = [strip((0.03, 0.025, 0.16), (side * (across / 2 - 0.016), handle_y, (share - 0.5) * along_length))
               for side, share in ((1, 0.52), (1, 0.33), (-1, 0.33))]
    mirror_y = along(LOWER, 0.74, 1) * tall + 0.08
    mirrors = [strip((0.16, 0.1, 0.07), (side * (across / 2 - 0.08), mirror_y, (0.735 - 0.5) * along_length))
               for side in (-1, 1)]  # within the body's width: the row's size is the car's
    return headlamps, tail_lamps, plates, blue, red, base, grille + handles, mirrors


PLATE_TEXT = "PL 2099"  # each plate's characters, drawn as seven-segment strokes (a space is a gap)
SEGMENTS = {"P": "abefg", "L": "def", "0": "abcdef", "2": "abdeg", "9": "abcdfg"}
GLYPH_WIDE, GLYPH_TALL, STROKE = 0.044, 0.07, 0.01  # a character's box and its strokes' width, in metres


def glyph_strokes(character, middle_x, height, depth, face):
    """A plate character's strokes (boxes) as seven segments a-g round its box at `middle_x`, `height`, `depth`, read
    facing the plate on the `face` end (1 the nose, -1 the tail: its right towards -x)."""
    import trimesh
    half_wide, half_tall = GLYPH_WIDE / 2, GLYPH_TALL / 2
    level = (GLYPH_WIDE, STROKE, 0.006)
    upright = (STROKE, half_tall + STROKE / 2, 0.006)
    places = {"a": (level, 0, half_tall), "g": (level, 0, 0), "d": (level, 0, -half_tall),
              "f": (upright, -half_wide, half_tall / 2), "b": (upright, half_wide, half_tall / 2),
              "e": (upright, -half_wide, -half_tall / 2), "c": (upright, half_wide, -half_tall / 2)}
    strokes = []
    for name in SEGMENTS[character]:
        extents, across, up = places[name]
        strokes.append(trimesh.creation.box(extents=extents).apply_translation((middle_x + face * across, height + up, depth)))
    return strokes


def plate_marks(across, tall, along_length):
    """Each plate's dark surround and its characters (PLATE_TEXT in seven-segment strokes: six blocks read as a blank
    plate, night car round 3; one blank and white was the brightest thing on the car's back, round 2), and a dark
    bumper band across the nose and the tail under it."""
    import trimesh
    nose, tail = along_length / 2, -along_length / 2
    pitch = GLYPH_WIDE + 0.02
    marks = []
    for end, face, height in ((nose, 1, 0.31 * tall), (tail, -1, 0.335 * tall)):
        marks.append(trimesh.creation.box(extents=(0.56, 0.145, 0.004)).apply_translation(
            (0, height, end - face * 0.02)))
        for place, character in enumerate(PLATE_TEXT):
            if character != " ":
                # Left to right as read facing the plate: towards +x at the nose, towards -x at the tail.
                middle_x = face * (place - (len(PLATE_TEXT) - 1) / 2) * pitch
                marks += glyph_strokes(character, middle_x, height, end - face * 0.003, face)
        marks.append(trimesh.creation.box(extents=(across * 0.8, 0.04, 0.03)).apply_translation(
            (0, 0.255 * tall, end - face * 0.015)))
    return marks


def seam_ribbon(points, place):
    """A thin dark ribbon standing off the skin along a section's `points` (k x 2, in order) at length `place`: two rows
    of points SEAM_WIDE apart along the car, each moved SEAM_PROUD out along the section's own outward normal."""
    import trimesh
    middle = points.mean(axis=0)
    steps = np.gradient(points, axis=0)
    normals = np.column_stack([steps[:, 1], -steps[:, 0]])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-9
    outward = np.sign(np.sum(normals * (points - middle), axis=1, keepdims=True))
    outward[outward == 0] = 1.0
    lifted = points + normals * outward * SEAM_PROUD
    count = len(lifted)
    vertices = np.vstack([np.column_stack([lifted, np.full(count, place - SEAM_WIDE / 2)]),
                          np.column_stack([lifted, np.full(count, place + SEAM_WIDE / 2)])])
    faces = [face for at in range(count - 1)
             for face in ((at, at + 1, at + count + 1), (at, at + count + 1, at + count))]
    return mesh_of(vertices, np.array(faces))


def seams(across, tall, along_length, axles, radius):
    """The doors' shut lines down both sides (SEAMS, from the doors' foot to the beltline) and the bonnet's and boot
    lid's across the top: the body's own section at that length, so each lies on the skin (a flat side with no lines
    read as a toy, night car round 2)."""
    lines = []
    for share in SEAMS:
        place = (share - 0.5) * along_length
        section = body_section(across, tall, along_length, axles, radius, place)
        top = along(LOWER, share, 1) * tall
        for side in (-1, 1):
            chosen = section[(np.sign(section[:, 0]) == side) & (section[:, 1] > DOOR_FOOT * tall) &
                             (section[:, 1] < top - 0.015) & (np.abs(section[:, 0]) > 0.6 * across / 2)]
            if len(chosen) > 1:
                lines.append(seam_ribbon(chosen[np.argsort(chosen[:, 1])], place))
    for share in (0.79, 0.11):  # the bonnet's rear edge and the boot lid's front edge
        place = (share - 0.5) * along_length
        section = body_section(across, tall, along_length, axles, radius, place)
        top = along(LOWER, share, 1) * tall
        chosen = section[section[:, 1] > top - 0.04]
        if len(chosen) > 1:
            lines.append(seam_ribbon(chosen[np.argsort(chosen[:, 0])], place))
    for line in lines:  # within the car's width: standing off its widest point they made it 4 mm wider than its row
        line.vertices[:, 0] = np.clip(line.vertices[:, 0], -across / 2, across / 2)
    return lines


def light_bar(across, tall):
    """The roof's light bar: (its blue lenses, its red lenses, its dark base), the base a long low housing across the
    roof sunk 1 cm into it, each half's lens a rounded block on it (a capsule lying across), its top the car's height."""
    import trimesh
    roof = along(GREENHOUSE, 0.47, 1) * tall
    wide, deep, base_tall = across * 0.66, 0.26, 0.045
    base = trimesh.creation.box(extents=(wide, base_tall + 0.01, deep))
    base.apply_translation((0, roof - 0.01 + (base_tall + 0.01) / 2, -0.05))
    lens_tall = tall + LIGHT_BAR - roof - base_tall
    lens_long = wide / 2 - 0.03

    def lens(side):
        lens_mesh = trimesh.creation.capsule(height=lens_long - lens_tall, radius=lens_tall / 2, count=[24, 12])
        lens_mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
        lens_mesh.apply_scale((1.0, 1.0, (deep - 0.04) / lens_tall))
        return lens_mesh.apply_translation((side * (lens_long / 2 + 0.01), roof + base_tall + lens_tall / 2, -0.05))

    return [lens(-1)], [lens(1)], [base]


def wheel_meshes(radius, width, middle, side):
    """A tyre (a ring round its axle, x) and its rim (a dish set in on its outer side, its spokes, its hub and a dark
    barrel behind them, so the arch is never seen through) at `middle`."""
    import trimesh
    turn = trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0])
    inner = radius * RIM_SHARE
    tyre = trimesh.creation.annulus(r_min=inner * 0.97, r_max=radius, height=width, sections=WHEEL_FACES)
    tyre.apply_transform(turn)
    barrel = trimesh.creation.cylinder(radius=inner * 0.98, height=width * 0.5, sections=WHEEL_FACES)
    barrel.apply_transform(turn)
    barrel.apply_translation((-side * width * 0.2, 0, 0))
    face = side * width * 0.36  # the rim's outer face, a little in from the tyre's wall
    lip = trimesh.creation.annulus(r_min=inner * 0.86, r_max=inner, height=width * 0.12, sections=WHEEL_FACES)
    lip.apply_transform(turn)
    lip.apply_translation((face, 0, 0))
    hub = trimesh.creation.cylinder(radius=radius * 0.17, height=width * 0.2, sections=24)
    hub.apply_transform(turn)
    hub.apply_translation((face, 0, 0))
    rim = [lip, hub]
    for number in range(SPOKES):
        spoke = trimesh.creation.box(extents=(width * 0.1, inner * 0.8, inner * 0.2))
        spoke.apply_translation((face - side * width * 0.03, inner * 0.5, 0))
        spoke.apply_transform(trimesh.transformations.rotation_matrix(2 * np.pi * number / SPOKES, (1, 0, 0)))
        rim.append(spoke)
    return tyre.apply_translation(middle), barrel.apply_translation(middle), \
        [mesh.apply_translation(middle) for mesh in rim]


def finished(name, meshes, key, pivot=(0.0, 0.0, 0.0), joint=None, axis=None, sign=1):
    """A part (moving_parts.part) finished as FINISHES[key]: its recipe the part's finish, its palette variant beside."""
    from score.stages.props.moving_parts import part
    recipe, variant = FINISHES[key]
    return dict(part(name, meshes, recipe, pivot, joint, axis, sign), variant=variant)


def car_parts(size):
    """A saloon car along z, its front at +z: its still body, greenhouse, roof, cabin, lamps and trim, its right front
    door (skin and window, hinged about the upright at its front edge, opening outward) and four wheels, each tyre
    and rim spinning about its axle (x) at its own middle."""
    across, whole, along_length = size
    tall = whole - LIGHT_BAR  # the body's height, its light bar on top
    radius, width = whole * WHEEL_RADIUS, across * TYRE_WIDE
    axles = [(share - 0.5) * along_length for share in AXLES]
    body, door, span = body_and_door(across, tall, along_length, axles, radius)
    glass, window, roof = greenhouse(across, tall, along_length, span)
    headlamps, tail_lamps, plates, blue, red, bar_base, trim, mirrors = lamps(across, tall, along_length)
    hinge = (-across / 2, tall * 0.5, span[1])
    parts = [finished("body", [body, roof, *mirrors], "body"), finished("glass", [glass], "glass"),
             finished("cabin", cabin(across, tall, along_length), "cabin"),
             finished("headlamps", headlamps, "headlamps"), finished("tail_lamps", tail_lamps, "tail_lamps"),
             finished("plates", plates, "plates"), finished("siren_blue", blue, "siren_blue"),
             finished("siren_red", red, "siren_red"), finished("bar_base", bar_base, "bar_base"),
             finished("trim", trim, "trim"),
             finished("seams", seams(across, tall, along_length, axles, radius) +
                      plate_marks(across, tall, along_length), "seams"),
             finished("door", [door], "door", hinge, "hinge", "y", 1),
             finished("door_window", [window], "door_window", hinge, "hinge", "y", 1)]
    for number, (side, axle) in enumerate(((side, axle) for axle in axles for side in (-1, 1)), 1):
        middle = (side * (across / 2 - width / 2 - 0.02), radius, axle)
        tyre, barrel, rim = wheel_meshes(radius, width, middle, side)
        parts += [finished(f"wheel_{number}", [tyre, barrel], "tyre", middle, "spin", "x", 1),
                  finished(f"rim_{number}", rim, "rim", middle, "spin", "x", 1)]
    return parts


def linear(hex_colour):
    """An sRGB hex colour in linear light, as glTF's factors take it."""
    values = np.array([int(hex_colour[index:index + 2], 16) / 255 for index in (1, 3, 5)])
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def variant_of(palette, name):
    """The palette's variant `name` (palette.json `families`), with its family."""
    for family, held in palette["families"].items():
        if name in held["variants"]:
            return dict(held["variants"][name], family=family)
    raise KeyError(f"{name}: no variant of the palette")


def material_of(palette, recipe, name):
    """A part's glTF material (trimesh PBR) from its recipe and palette variant `name`: the token's colour, the
    variant's roughness and metal; glass see-through, a glow giving off its colour."""
    import trimesh
    variant = variant_of(palette, name)
    colour = linear(palette["tokens"][variant["token"]])
    if recipe == "glass":
        return trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=[*colour, GLASS_SEEN], alphaMode="BLEND",
                                                   roughnessFactor=variant["roughness"], metallicFactor=0.0,
                                                   doubleSided=True)
    glow = colour if recipe == "glowing" else [0.0, 0.0, 0.0]
    return trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=[*colour, 1.0], emissiveFactor=glow,
                                               roughnessFactor=variant["roughness"],
                                               metallicFactor=variant.get("metal") or 0.0)


def painted(scene, record, palette):
    """Each part's geometry given its material from the palette: its record's finish (a recipe) in its variant."""
    import trimesh
    for entry in record["parts"]:
        mesh = scene.geometry[entry["name"]]
        mesh.visual = trimesh.visual.TextureVisuals(material=material_of(palette, entry["finish"], entry["variant"]))
    return scene
