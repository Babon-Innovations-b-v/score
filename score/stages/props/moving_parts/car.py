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
SECTIONS, AROUND = 140, 48  # sections along the length and points round each
ROUNDNESS = 5.0  # the sections' superellipse power: higher is boxier
WHEEL_RADIUS, TYRE_WIDE, RIM_SHARE = 0.235, 0.115, 0.68  # as shares of the height and width; the rim's of the tyre
AXLES = (0.17, 0.82)  # the axles as shares of the length from the rear
ARCH_ROOM = 1.12  # an arch's radius over its wheel's
DOOR = (0.47, 0.69)  # the front door's rear and front edges as shares of the length (its hinge at the front)
DOOR_FOOT = 0.20  # the door's foot as a share of the height
SKIN = 0.03  # a door's thickness, in metres
LIGHT_BAR = 0.07  # the light bar's height on the roof, in metres (the car's height its top)
WHEEL_FACES = 40
FINISHES = {"body": ("painted_metal", "car_body_paint"), "door": ("painted_metal", "car_body_paint"),
            "glass": ("glass", "car_window"), "door_window": ("glass", "car_window"),
            "cabin": ("rubber", "lantern_cable"), "trim": ("bare_metal", "car_chrome"),
            "headlamps": ("glowing", "lamp_head_glow"), "tail_lamps": ("rubber", "barrier_plastic_red"),
            "siren_blue": ("glowing", "siren_blue"), "siren_red": ("glowing", "siren_red"),
            "plates": ("painted_metal", "licence_plate"), "tyre": ("rubber", "tyre_rubber"),
            "rim": ("bare_metal", "car_chrome")}


def along(table, share, column):
    """A column of a profile table at a share of the length, eased between its rows."""
    shares = [row[0] for row in table]
    return float(np.interp(share, shares, [row[column] for row in table]))


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


def body_and_door(across, tall, along_length, axles, radius):
    """The lower body (its door's skin cut out) and the door's skin."""
    places = np.linspace(-along_length / 2, along_length / 2, SECTIONS)
    shares = (places + along_length / 2) / along_length
    sections = []
    for place, share in zip(places, shares):
        bottom = arch_bottom(place, along(LOWER, share, 2) * tall, axles, radius)
        top = along(LOWER, share, 1) * tall
        sections.append(ring(along(LOWER, share, 3) * across / 2, min(bottom, top - 0.08), top))
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
        heights = belt + (roof - belt) * np.clip(points[:, 1], 0.0, 1.0)
        rise = np.clip(points[:, 1], 0.0, 1.0)
        sections.append(np.column_stack([points[:, 0] * half * (GLASS_IN + (ROOF_IN - GLASS_IN) * rise), heights]))
    vertices, faces, at_section, _ = lofted(sections, places)
    middles = vertices[faces].mean(axis=1)
    window = door_faces(vertices, faces, at_section, places, span, belt, tall * 0.93, -1)
    roof = (middles[:, 1] > np.interp(middles[:, 2], places, [along(GREENHOUSE, share, 1) * tall for share in shares])
            - 0.045) & ~window
    glass = kept(vertices, faces, ~window & ~roof)
    return glass, shell(kept(vertices, faces, window), 0.006), kept(vertices, faces, roof)


def cabin(across, tall, along_length):
    """The cabin seen through the glass and the open door: its liner (inside the body and greenhouse, its faces
    turned inward), two front seats, a rear bench, a
    dashboard and a steering wheel."""
    import trimesh
    half = across / 2 * 0.86
    rear, front = (0.27 - 0.5) * along_length, (0.73 - 0.5) * along_length
    belt = along(LOWER, 0.5, 1) * tall - 0.02
    places = np.linspace(rear, front, 24)
    sections = []
    for place in places:
        share = place / along_length + 0.5
        low_half = along(LOWER, share, 3) * across / 2 - 0.06
        roof_half = low_half * ROOF_IN
        top = max(along(GREENHOUSE, share, 1) * tall - 0.05, belt + 0.02)
        sections.append(np.array([(-low_half, tall * 0.22), (-low_half, belt), (-roof_half, top), (roof_half, top),
                                  (low_half, belt), (low_half, tall * 0.22)])[::-1])
    vertices, faces, _, _ = lofted(sections, places)
    liner = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    liner.fix_normals()
    liner.invert()
    parts = [liner]
    for side in (-1, 1):
        seat = trimesh.creation.box(extents=(half * 0.75, tall * 0.12, 0.5))
        seat.apply_translation((side * half * 0.48, tall * 0.33, along_length * 0.04))
        back = trimesh.creation.box(extents=(half * 0.75, tall * 0.42, 0.12))
        back.apply_transform(trimesh.transformations.rotation_matrix(-0.2, (1, 0, 0)))
        back.apply_translation((side * half * 0.48, tall * 0.58, along_length * 0.04 - 0.28))
        parts += [seat, back]
    bench = trimesh.creation.box(extents=(half * 1.8, tall * 0.12, 0.5))
    bench.apply_translation((0, tall * 0.33, -along_length * 0.12))
    bench_back = trimesh.creation.box(extents=(half * 1.8, tall * 0.4, 0.12))
    bench_back.apply_translation((0, tall * 0.56, -along_length * 0.12 - 0.3))
    dash = trimesh.creation.box(extents=(half * 1.9, tall * 0.14, 0.35))
    dash.apply_translation((0, tall * 0.6, front - 0.2))
    wheel = trimesh.creation.torus(0.18, 0.018)
    wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2 - 0.4, (1, 0, 0)))
    wheel.apply_translation((-half * 0.48, tall * 0.66, front - 0.48))
    return parts + [bench, bench_back, dash, wheel]


def lamps(across, tall, along_length):
    """(headlamps, tail lamps, plates, a light bar's blue and red halves, the trim: a grille bar and door handles)."""
    import trimesh
    nose, tail = along_length / 2, -along_length / 2

    def strip(size, middle):
        return trimesh.creation.box(extents=size).apply_translation(middle)

    head_y, tail_y = along(LOWER, 0.97, 1) * tall - 0.06, along(LOWER, 0.03, 1) * tall - 0.05
    headlamps = [strip((across * 0.24, 0.05, 0.04), (side * across * 0.32, head_y, nose - 0.035)) for side in (-1, 1)]
    tail_lamps = [strip((across * 0.78, 0.045, 0.03), (0, tail_y, tail + 0.03))]
    plates = [strip((0.52, 0.12, 0.012), (0, 0.42 * tall * 0.9, nose - 0.01)),
              strip((0.52, 0.12, 0.012), (0, 0.45 * tall * 0.9, tail + 0.01))]
    roof = along(GREENHOUSE, 0.47, 1) * tall
    bar_tall = tall + LIGHT_BAR - roof + 0.01  # sunk 1 cm into the roof, its top the car's height
    bar = (across * 0.3, bar_tall, 0.22)
    blue = [strip(bar, (-across * 0.16, roof - 0.01 + bar_tall / 2, -0.05))]
    red = [strip(bar, (across * 0.16, roof - 0.01 + bar_tall / 2, -0.05))]
    grille = [strip((across * 0.36, 0.025, 0.03), (0, head_y - 0.02, nose - 0.025))]
    handle_y = along(LOWER, 0.5, 1) * tall - 0.1
    handles = [strip((0.03, 0.025, 0.16), (side * (across / 2 - 0.016), handle_y, (share - 0.5) * along_length))
               for side, share in ((1, 0.52), (1, 0.33), (-1, 0.33))]
    return headlamps, tail_lamps, plates, blue, red, grille + handles


def wheel_meshes(radius, width, middle, side):
    """A tyre (a ring round its axle, x) and its rim (a disc set in on its outer side) at `middle`."""
    import trimesh
    tyre = trimesh.creation.annulus(r_min=radius * RIM_SHARE, r_max=radius, height=width, sections=WHEEL_FACES)
    turn = trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0])
    tyre.apply_transform(turn)
    rim = trimesh.creation.cylinder(radius=radius * RIM_SHARE, height=width * 0.8, sections=WHEEL_FACES)
    rim.apply_transform(turn)
    hub = trimesh.creation.cylinder(radius=radius * 0.18, height=width * 0.9, sections=16)
    hub.apply_transform(turn)
    hub.apply_translation((side * width * 0.08, 0, 0))
    return tyre.apply_translation(middle), [rim.apply_translation(middle), hub.apply_translation(middle)]


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
    headlamps, tail_lamps, plates, blue, red, trim = lamps(across, tall, along_length)
    hinge = (-across / 2, tall * 0.5, span[1])
    parts = [finished("body", [body, roof], "body"), finished("glass", [glass], "glass"),
             finished("cabin", cabin(across, tall, along_length), "cabin"),
             finished("headlamps", headlamps, "headlamps"), finished("tail_lamps", tail_lamps, "tail_lamps"),
             finished("plates", plates, "plates"), finished("siren_blue", blue, "siren_blue"),
             finished("siren_red", red, "siren_red"), finished("trim", trim, "trim"),
             finished("door", [door], "door", hinge, "hinge", "y", 1),
             finished("door_window", [window], "door_window", hinge, "hinge", "y", 1)]
    for number, (side, axle) in enumerate(((side, axle) for axle in axles for side in (-1, 1)), 1):
        middle = (side * (across / 2 - width / 2 - 0.02), radius, axle)
        tyre, rim = wheel_meshes(radius, width, middle, side)
        parts += [finished(f"wheel_{number}", [tyre], "tyre", middle, "spin", "x", 1),
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
        return trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=[*colour, 0.45], alphaMode="BLEND",
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
