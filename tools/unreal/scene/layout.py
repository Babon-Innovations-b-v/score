"""A scene package's copies, lamps and light as Unreal places them (#221): each copy an actor of its object's one
mesh at its laid transform (frames.copy_transform), each lamp a point light, the sun a directional light, the sky a
sky light, the exposure a post-process volume's manual exposure. Plain Python with no numpy: Unreal's own Python runs
it.

Light units: scene.json's `strength` is Blender's (watts, a sun's W/m²), as the final render lights with it; Unreal
lights in lumens and lux. LUMENS_A_WATT (the luminous efficacy of 555 nm light) turns one into the other, and the
manual exposure divides it back out, so a pixel reads as Blender's; both are assumptions the side-by-side test (#218)
measures against Blender's frames. What Unreal reads as a luminance (a sky light's picture, a look's glow) is
therefore Blender's radiance times LUMENS_A_WATT too, or the exposure leaves it 683 times too dark (#222, run 8: the
glows barely showed). A place with no sky picture (a night's) is lit by its ambient as Blender's world colour lights
it: a sky light of one even colour (ambient_sky).

A point light in Unreal stops at its attenuation radius (1000 cm unless set: #222, run 11 cut every floodlight 23 m up
off the facades), so each lamp reaches as far as its light still shows: until it lights a white wall facing it to
FAINTEST of Blender's exposed linear value (reach). The final render's look is Blender's view transform and look over
the exposed radiance; Unreal's own tonemapper (its filmic curve, vignette, local exposure) is replaced by a post-process
material reading the package's grade picture (scene_package.GRADE) as Blender's grade_lut made it (grade_code), and
the background the camera sees where nothing stands (a night's dark blue) is laid there in the same pass.
"""
import math

import frames

LUMENS_A_WATT = 683.0
# The faintest exposed linear value a lamp's light still adds on a white wall facing it (far below the grade's darkest
# step, scene_package.GRADE's 0.18 * 2 ** -12.5 = 3e-5 times ten: a lamp past it adds nothing the eye sees).
FAINTEST = 1e-4
# Unreal's scene depth (cm) past which a pixel has nothing standing in it (the sky): 10 km, past any place.
SKY_DEPTH = 1.0e6


def actors(scene, basis):
    """Every copy in scene.json as an actor: {name, object, kind, character, transform, plays}."""
    found = []
    for copy in scene["instances"]:
        about = scene["objects"][copy["object"]]
        found.append({"name": copy["name"], "object": copy["object"], "kind": copy.get("kind"),
                      "character": about.get("kind") == "character",
                      "transform": frames.copy_transform(basis, copy["matrix"]), "plays": copy.get("plays")})
    return found


def lamps(scene, basis):
    """Every point lamp as an Unreal point light: {name, location (cm), lumens, radius (cm), reach (cm, its
    attenuation radius), colour}; a lamp of kind "sun" is the environment's sun (sun)."""
    exposure = float((scene.get("environment") or {}).get("exposure", 1.0))
    return [{"name": lamp["name"], "location": frames.point(basis, lamp["at"]),
             "lumens": lamp["strength"] * LUMENS_A_WATT, "radius": lamp["radius"] * frames.CENTIMETRES,
             "reach": reach(lamp["strength"], exposure), "colour": lamp["colour"]}
            for lamp in scene.get("lamps", []) if lamp["kind"] == "point"]


def reach(watts, exposure):
    """How far (cm) a point lamp of `watts` (Blender's) lights a white wall facing it to FAINTEST once `exposure`
    is on it: its intensity watts / 4 pi over the distance squared, a white Lambert wall's radiance that over pi."""
    return math.sqrt(watts / (4.0 * math.pi) * exposure / (math.pi * FAINTEST)) * frames.CENTIMETRES


def toward(body):
    """The glTF way toward a sun or moon (its elevation, and heading round from +x towards +z)."""
    elevation, heading = math.radians(body["elevation"]), math.radians(body["heading"])
    return [math.cos(elevation) * math.cos(heading), math.sin(elevation), math.cos(elevation) * math.sin(heading)]


def directional(body, basis):
    """A sun or moon as an Unreal directional light, which shines along its own +x: {name, rotation (rotator),
    lux, colour, angle}."""
    shines = [-value for value in frames.turned(basis, toward(body))]
    return {"name": body["name"], "rotation": frames.rotator(shines, frames.turned(basis, [0.0, 1.0, 0.0])),
            "lux": body["strength"] * LUMENS_A_WATT, "colour": body["colour"], "angle": body["angle"]}


def environment(scene, package, basis):
    """The place's sky and light for Unreal: {sun, moon, sky {file, turn, strength (Unreal's units)} or null,
    exposure_bias (EV, Unreal's manual exposure: Blender's exposure with LUMENS_A_WATT divided back out), ambient,
    background (the radiance the camera sees where nothing stands, Unreal's units), grade (scene.json's, its file
    under the package, its material's HLSL `code`: grade_code)}."""
    found = scene.get("environment") or {}
    sky = found.get("sky")
    night = found.get("night") or {}
    background = [value * LUMENS_A_WATT for value in found["background"]] if found.get("background") else None
    return {"sun": directional(found["sun"], basis) if found.get("sun") else None,
            "moon": directional(night["moon"], basis) if night.get("moon") else None,
            "sky": {"file": str(package / sky["file"]), "turn": sky.get("turn", 0.0),
                    "strength": sky.get("strength", 1.0) * LUMENS_A_WATT} if sky and sky.get("file") else None,
            "exposure_bias": math.log2(float(found.get("exposure", 1.0)) / LUMENS_A_WATT),
            "ambient": found.get("ambient"),
            "background": background,
            "grade": dict(found["grade"], file=str(package / found["grade"]["file"]),
                          code=grade_code(found["grade"], float(found.get("exposure", 1.0)), background))
            if found.get("grade") else None}


def grade_place(colour, grade):
    """Where the grade picture holds an exposed scene linear `colour` (grade_lut's lattice: `size` tiles of size by
    size side by side, red along a tile, blue tile by tile, green up from the bottom row, each channel's step c at
    middle * 2 ** (low + c * (high - low))): (u of the lower blue tile, u of the next, v, the blend between them), as
    a bilinear sample reads red and green between their steps. grade_code is this in HLSL."""
    size, low, high, middle = grade["size"], grade["low"], grade["high"], grade["middle"]
    steps = [min(max((math.log2(max(value, 1e-10) / middle) - low) / (high - low), 0.0), 1.0) * (size - 1.0)
             for value in colour]
    lower = math.floor(steps[2])
    upper = min(lower + 1.0, size - 1.0)
    across = (steps[0] + 0.5) / (size * size)
    return across + lower / size, across + upper / size, 1.0 - (steps[1] + 0.5) / size, steps[2] - lower


def grade_code(grade, exposure, background):
    """The HLSL of the post-process material that replaces Unreal's tonemapper: the scene colour (its pre-exposure
    taken off, Unreal's radiance), or the `background` radiance where nothing stands (depth past SKY_DEPTH), times
    the `exposure` (Blender's, LUMENS_A_WATT divided out), looked up in the grade picture as grade_place does; inputs
    Color, Depth (scene textures) and Grade (the picture). Its output is the display's sRGB value Blender shows."""
    size, low, high, middle = (float(grade[key]) for key in ("size", "low", "high", "middle"))
    back = ", ".join(f"{value:.9g}" for value in (background or [0.0, 0.0, 0.0]))
    return "\n".join((
        f"float3 radiance = Depth.r > {SKY_DEPTH:.9g} ? float3({back}) : Color.rgb;",
        f"float3 exposed = max(radiance * {exposure / LUMENS_A_WATT:.9g}, 1e-10);",
        f"float3 steps = saturate((log2(exposed / {middle:.9g}) - ({low:.9g})) / ({high - low:.9g})) * {size - 1.0:.9g};",
        "float lower = floor(steps.b);",
        f"float upper = min(lower + 1.0, {size - 1.0:.9g});",
        f"float across = (steps.r + 0.5) / {size * size:.9g};",
        f"float up = 1.0 - (steps.g + 0.5) / {size:.9g};",
        f"float3 below = Grade.SampleLevel(GradeSampler, float2(across + lower / {size:.9g}, up), 0).rgb;",
        f"float3 above = Grade.SampleLevel(GradeSampler, float2(across + upper / {size:.9g}, up), 0).rgb;",
        "return lerp(below, above, steps.b - lower);"))


def rgbe(colour):
    """One Radiance pixel (RGBE) of a linear colour."""
    largest = max(colour)
    if largest < 1e-32:
        return bytes(4)
    mantissa, exponent = math.frexp(largest)
    scale = mantissa * 256.0 / largest
    return bytes([int(value * scale) for value in colour] + [exponent + 128])


def ambient_sky(colour, path, width=64):
    """An even sky of the ambient `colour` written at `path` as a long-lat Radiance picture (width by width / 2, as
    Unreal imports one as a cube map); the path."""
    height = width // 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {height} +X {width}\n".encode()
                     + rgbe(colour) * (width * height))
    return path


def lit_by_ambient(environment, into):
    """The environment with its sky made from its ambient (ambient_sky, under `into`) when it has no sky picture: a
    night's dome lights Blender's frame though it shows no picture; unchanged otherwise."""
    if environment["sky"] or not environment["ambient"]:
        return environment
    file = ambient_sky([float(value) for value in environment["ambient"]], into / "ambient_sky.hdr")
    return dict(environment, sky={"file": str(file), "turn": 0.0, "strength": LUMENS_A_WATT})
