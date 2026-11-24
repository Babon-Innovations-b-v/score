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
"""
import math

import frames

LUMENS_A_WATT = 683.0


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
    """Every point lamp as an Unreal point light: {name, location (cm), lumens, radius (cm), colour}; a lamp of kind
    "sun" is the environment's sun (sun)."""
    return [{"name": lamp["name"], "location": frames.point(basis, lamp["at"]),
             "lumens": lamp["strength"] * LUMENS_A_WATT, "radius": lamp["radius"] * frames.CENTIMETRES,
             "colour": lamp["colour"]} for lamp in scene.get("lamps", []) if lamp["kind"] == "point"]


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
    grade (scene.json's, its file under the package)}."""
    found = scene.get("environment") or {}
    sky = found.get("sky")
    night = found.get("night") or {}
    return {"sun": directional(found["sun"], basis) if found.get("sun") else None,
            "moon": directional(night["moon"], basis) if night.get("moon") else None,
            "sky": {"file": str(package / sky["file"]), "turn": sky.get("turn", 0.0),
                    "strength": sky.get("strength", 1.0) * LUMENS_A_WATT} if sky and sky.get("file") else None,
            "exposure_bias": math.log2(float(found.get("exposure", 1.0)) / LUMENS_A_WATT),
            "ambient": found.get("ambient"),
            "grade": dict(found["grade"], file=str(package / found["grade"]["file"])) if found.get("grade") else None}


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
