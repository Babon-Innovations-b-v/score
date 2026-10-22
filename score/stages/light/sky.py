"""A scene's sky in its light layer, from the environment concept's physics (CONTEXT.md "physics"; the owner,
2026-10-21: no fixed sky, each thing in the form its scale calls for): what is overhead at the scene's site at its
scene time (score/review/overhead.py on the inputs score/review/scene_sky.py keeps), never a sky record of its own.

    lights     each light over the level horizon (a shining body's, a far light's; one under it lights nothing here,
               the ground between: `risen`) a distant light shining from its direction,
               /<scene>/Lights/sky_<key>: its colour its kelvin, its strength its lux (W/m² at LUMENS_PER_WATT); a
               shining body's also its disc, a ball at its true size, /<scene>/Sky/Discs/<body>
    bodies     every other body a ball at its true direction and size SKY_DISTANCE out, /<scene>/Sky/Bodies/<body>;
               the light of its star lights its phase as it lights the scene
    backdrops  a dome a dome light of its lux and kelvin, a skyline its record (its look is a library item to come),
               /<scene>/Sky/Backdrops/<key>

A ball is painted with its surface (`<body>_disc` for a shining body, `<body>_face` for another): a framework look
(shaders.LOOKS: the Earth's NASA surface) first, else a body's face as its `body-face-<body>` row made it (`faces`,
score/stages/surfaces/body_faces.py; never read by a library name), else the library's where the library holds it;
one with none is named on the ball (`score:surface:missing`) for the library check, never painted grey. The scene's frame is the plan's: x east, y up, z south, its middle at the site.

The old sky the seed or the record drew (its suns, its sun discs, the Moon's pictures, the star field, a world hung
as structure) is turned off in the layer (`retired`), so the physics' sky is the only one.

`held` reads the sky back off the layer's geometry and `faults` holds it to what overhead.py says is overhead at that
site: the light layer's gate "sky bodies".

    kept_input(place) -> {name: path pattern}      the scene's kept sky, declared when it exists
    seen_of(kept) -> overhead.seen(...) | None
    risen(seen) -> seen with only the lights over the horizon
    faces_of(inputs) -> {body: its face.json}      the accepted body faces among a node's inputs
    write(stage, place, seen, out=None, faces=None) -> {lights, bodies, backdrops}
    held(stage, place) -> {lights, bodies, backdrops}
    faults(seen, held) -> [str]
"""
import json
import math
import pathlib
import sys

import numpy as np

from score.review import overhead, scene_sky, setting as settings

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import builders  # noqa: E402
import scene  # noqa: E402
import shaders  # noqa: E402

KEPT = "{home}/design/sky/{place}.json"
FACE_ROW = "body-face-"  # a body's face row (score/stages/surfaces/body_faces.py PREFIX), which the light layer reads
# How far out a ball of the sky hangs, metres: past every scene's ground and inside every view's far clip (the old
# Moon squares and star field hung 1800 to 1900 m out).
SKY_DISTANCE = 1800.0
# Lumens a watt at 555 nm (the CIE's definition of the candela): a light's lux as the W/m² Blender's sun takes.
LUMENS_PER_WATT = 683.0
# The gate's steps: a ball's or a light's way within this of overhead.py's (its numbers are kept to 0.01 degree), a
# ball's size within ACROSS_SHARE of its own or ACROSS_LEAST, whichever is more (a point-like world is millimetres
# across 1800 m out, under the float32 points' own step).
WAY_WITHIN = 0.05
ACROSS_SHARE = 0.02
ACROSS_LEAST = 1e-4
BALL_RINGS, BALL_SEGMENTS = 24, 48
FROM = "the environment concept's physics overhead at the scene's site at its scene time (score/review/overhead.py)"


def kept_input(place):
    """{"sky": its kept sky's path pattern} when the scene has one (scene_sky.keep), else {}."""
    return {"sky": KEPT} if (scene_sky.KEPT / f"{place}.json").is_file() else {}


def read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.is_file() else None


def seen_of(kept):
    """What is overhead at the kept site at its scene time, None while its position is not known."""
    return overhead.seen(kept["setting"], kept["site"], kept["time"]) if kept else None


def way(azimuth, altitude):
    """A sky direction (degrees) as a way in the scene's frame (x east, y up, z south)."""
    turn, rise = math.radians(azimuth), math.radians(altitude)
    return np.array([math.sin(turn) * math.cos(rise), math.sin(rise), -math.cos(turn) * math.cos(rise)])


def bearing(toward):
    """(azimuth, altitude) in degrees of a way in the scene's frame."""
    east, up, south = np.asarray(toward, dtype=float) / np.linalg.norm(toward)
    return math.degrees(math.atan2(east, -south)) % 360.0, math.degrees(math.asin(float(np.clip(up, -1.0, 1.0))))


def apart(first, second):
    """Degrees between two sky directions given as (azimuth, altitude)."""
    cosine = float(np.dot(way(*first), way(*second)))
    return math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))


def risen(seen):
    """What is overhead with only the lights whose disc stands at least partly over the level horizon (altitude over
    minus half its `across`; a far light, with none, over 0): a light under the horizon reaches the scene through no
    ground, so it is not one of the scene's lights."""
    return {**seen, "lights": [light for light in seen["lights"]
                               if light["altitude"] + (light.get("across") or 0.0) / 2.0 > 0.0]}


def tagged(prim, values):
    from pxr import Sdf
    types = {str: Sdf.ValueTypeNames.String, float: Sdf.ValueTypeNames.Double, bool: Sdf.ValueTypeNames.Bool}
    for key, value in values.items():
        if value is not None:
            prim.CreateAttribute(f"score:{key}", types[type(value)]).Set(value)


def faces_of(inputs):
    """{body: its face (face.json)} of every body face row among a node's inputs."""
    return {name[len(FACE_ROW):]: json.loads((pathlib.Path(path) / "face.json").read_text())
            for name, path in inputs.items()
            if name.startswith(FACE_ROW) and (pathlib.Path(path) / "face.json").is_file()}


def face_material(stage, place, face):
    """A body's face as its row made it: a flat UsdPreviewSurface under /<place>/Looks (its token's colour, roughness
    and metal; its recipe, token, family and row ride along)."""
    from pxr import Gf, Sdf, UsdShade
    path = f"/{place}/Looks/{face['surface']}"
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*face["colour"]))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(face["roughness"]))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(face["metal"]))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    for key, value in (("recipe", face["recipe"]), ("token", face["token"]), ("family", face["family"]),
                       ("from", f"{FACE_ROW}{face['body']}")):
        material.GetPrim().CreateAttribute(f"score:{key}", Sdf.ValueTypeNames.String).Set(str(value))
    return material


def painted(stage, prim, place, surface, out, face=None):
    """The ball painted with its surface: a framework look, else the body's face (`face`, its row's), else the
    library's where the library holds it, else that surface named as missing."""
    from pxr import UsdShade
    material = shaders.look(stage, place, surface, out) or (face and face_material(stage, place, face)) or \
        UsdShade.Material(stage.GetPrimAtPath(f"/{place}/Library/{surface}"))
    tagged(prim, {"surface": surface})
    if material:
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
    else:
        tagged(prim, {"surface:missing": f"the library has no surface {surface} yet"})


def ball(stage, path, azimuth, altitude, across):
    """A ball SKY_DISTANCE out along (azimuth, altitude), as wide as `across` degrees from the scene's middle."""
    centre = way(azimuth, altitude) * SKY_DISTANCE
    radius = SKY_DISTANCE * math.sin(math.radians(across) / 2.0)
    return scene.mesh_prim(stage, path, builders.sphere(centre.tolist(), radius, "sky", BALL_RINGS,
                                                        BALL_SEGMENTS)).GetPrim()


def write_light(stage, place, light, out):
    """A light overhead as a distant light shining from its direction, and a shining body's disc."""
    from pxr import Gf, UsdGeom, UsdLux
    path = f"/{place}/Lights/sky_{settings.key_of(light['name'])}"
    UsdGeom.Scope.Define(stage, f"/{place}/Lights")
    distant = UsdLux.DistantLight.Define(stage, path)
    distant.CreateIntensityAttr(light["lux"] / LUMENS_PER_WATT / scene.DISTANT_STRENGTH_PER_INTENSITY)
    distant.CreateEnableColorTemperatureAttr(True)
    distant.CreateColorTemperatureAttr(float(light["kelvin"]))
    if light.get("across"):
        distant.CreateAngleAttr(float(light["across"]))
    distant.AddOrientOp().Set(Gf.Quatf(scene.aim_turn([0.0, 0.0, 0.0], -way(light["azimuth"], light["altitude"]))))
    tagged(distant.GetPrim(), {"kind": "sky light", "sky:of": light.get("of"), "sky:lux": float(light["lux"]),
                               "sky:kelvin": float(light["kelvin"]), "from": FROM})
    found = {"name": light["name"], "path": path, "of": light.get("of")}
    if light.get("of") and light.get("across"):
        UsdGeom.Scope.Define(stage, f"/{place}/Sky/Discs")
        disc = ball(stage, f"/{place}/Sky/Discs/{light['of']}", light["azimuth"], light["altitude"], light["across"])
        painted(stage, disc, place, f"{light['of']}_disc", out)
        tagged(disc, {"kind": "sky disc", "sky:body": light["of"], "from": FROM})
        found["disc"] = str(disc.GetPath())
    return found


def write_body(stage, place, body, out, face=None):
    """Another body overhead as a ball at its true direction and size, its phase lit by the scene's own lights,
    painted with its face (`face`: its body face row's, None while that waits)."""
    prim = ball(stage, f"/{place}/Sky/Bodies/{body['body']}", body["azimuth"], body["altitude"], body["across"])
    painted(stage, prim, place, f"{body['body']}_face", out, face)
    tagged(prim, {"kind": "sky body", "sky:body": body["body"], "sky:lit": float(body["lit"]), "from": FROM})
    return {"body": body["body"], "path": str(prim.GetPath()), "surface": f"{body['body']}_face"}


def write_backdrop(stage, place, backdrop):
    """A dome backdrop as a dome light giving its lux (luminance lux over pi), a skyline as its record."""
    from pxr import UsdGeom, UsdLux
    path = f"/{place}/Sky/Backdrops/{settings.key_of(backdrop['name'])}"
    if backdrop["shape"] == "dome":
        dome = UsdLux.DomeLight.Define(stage, path)
        dome.CreateIntensityAttr(backdrop["lux"] / math.pi / LUMENS_PER_WATT)
        if backdrop.get("kelvin"):
            dome.CreateEnableColorTemperatureAttr(True)
            dome.CreateColorTemperatureAttr(float(backdrop["kelvin"]))
        prim = dome.GetPrim()
    else:
        prim = UsdGeom.Scope.Define(stage, path).GetPrim()
    tagged(prim, {"kind": "sky backdrop", "sky:shape": backdrop["shape"], "sky:lux": float(backdrop["lux"]),
                  "from": FROM})
    return {"name": backdrop["name"], "path": path, "shape": backdrop["shape"]}


def write(stage, place, seen, out=None, faces=None):
    """The scene's sky from what is overhead (overhead.seen's answer; its lights the risen ones) into the stage's edit
    target, each body painted with its face (`faces`: faces_of's); what was written."""
    from pxr import UsdGeom
    seen = risen(seen)
    UsdGeom.Scope.Define(stage, f"/{place}/Sky")
    for group in ("Bodies", "Backdrops"):
        UsdGeom.Scope.Define(stage, f"/{place}/Sky/{group}")
    return {"lights": [write_light(stage, place, light, out) for light in seen["lights"]],
            "bodies": [write_body(stage, place, body, out, (faces or {}).get(body["body"]))
                       for body in seen["bodies"]],
            "backdrops": [write_backdrop(stage, place, backdrop) for backdrop in seen["backdrops"]]}


def sun_entries(seen):
    """The brightest light overhead as the record's unnamed sun the day dome is scattered from (scene.write_sky_dome:
    its `toward`, the way it shines); [] with none over the horizon."""
    seen = risen(seen)
    return [{"type": "sun", "toward": (-way(light["azimuth"], light["altitude"])).tolist()}
            for light in seen["lights"][:1]]


def is_old_sky(prim, place):
    """A prim of the sky the seed or the record drew before the physics: a distant light, a ball or picture of the
    sky (score:kind sky), the star field, a world hung as structure (score:plain sky outside /<scene>/Sky)."""
    from pxr import UsdLux
    kind = prim.GetAttribute("score:kind").Get() if prim.HasAttribute("score:kind") else None
    if kind in ("sky light", "sky disc", "sky body", "sky backdrop"):
        return False
    plain = prim.GetAttribute("score:plain").Get() if prim.HasAttribute("score:plain") else None
    return prim.IsA(UsdLux.DistantLight) or kind in ("sky", "stars") or (
        plain == "sky" and not str(prim.GetPath()).startswith(f"/{place}/Sky/"))


def retired(stage, place):
    """The old sky turned off in the stage's edit target; the paths turned off."""
    from pxr import Usd
    root = stage.GetPrimAtPath(f"/{place}")
    found = [prim for prim in Usd.PrimRange(root)] if root else []
    off = [str(prim.GetPath()) for prim in found if is_old_sky(prim, place)]
    for path in off:
        stage.GetPrimAtPath(path).SetActive(False)
    return off


# --- the gate ------------------------------------------------------------------------------------------------------

def tag(prim, key):
    return prim.GetAttribute(f"score:{key}").Get() if prim.HasAttribute(f"score:{key}") else None


def ball_seen(prim):
    """(azimuth, altitude, across) of a ball as its geometry stands: its bounds' middle and half its height."""
    from pxr import Usd, UsdGeom
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(prim)
    box = box.ComputeAlignedRange()
    centre = np.asarray(box.GetMidpoint(), dtype=float)
    radius = (box.GetMax()[1] - box.GetMin()[1]) / 2.0
    azimuth, altitude = bearing(centre)
    return azimuth, altitude, math.degrees(2.0 * math.asin(min(1.0, radius / np.linalg.norm(centre))))


def light_seen(prim):
    """(azimuth, altitude) a distant light shines from: its -z turned into the scene's frame, reversed."""
    from pxr import UsdGeom
    matrix = np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(prim), dtype=float)
    return bearing(-(np.array([0.0, 0.0, -1.0]) @ matrix[:3, :3]))


def held(stage, place):
    """The physics' sky the stage holds, read off its geometry: {lights: {of or name: (az, alt)}, bodies: {body: (az,
    alt, across)}, discs: {body: (az, alt, across)}, backdrops: {name: shape}}; only active prims."""
    from pxr import Usd
    root = stage.GetPrimAtPath(f"/{place}")
    found = {"lights": {}, "bodies": {}, "discs": {}, "backdrops": {}}
    # every prim, an `over` too: the light layer read on its own holds the scene's root only as an over
    for prim in (Usd.PrimRange(root, Usd.PrimAllPrimsPredicate) if root else []):
        kind = tag(prim, "kind")
        if not prim.IsActive() or kind not in ("sky light", "sky body", "sky disc", "sky backdrop"):
            continue
        if kind == "sky light":
            found["lights"][prim.GetName()[len("sky_"):]] = light_seen(prim)
        elif kind == "sky backdrop":
            found["backdrops"][prim.GetName()] = tag(prim, "sky:shape")
        else:
            found["bodies" if kind == "sky body" else "discs"][tag(prim, "sky:body")] = ball_seen(prim)
    return found


def ball_faults(what, wanted, have):
    """A ball against overhead.py's: its way and its size."""
    found = []
    if have is None:
        return [f"{what}: overhead at {wanted[0]:.2f}, {wanted[1]:.2f} degrees, missing from the sky"]
    if apart(wanted[:2], have[:2]) > WAY_WITHIN:
        found.append(f"{what}: at azimuth {have[0]:.2f}, altitude {have[1]:.2f}; overhead.py has it at "
                     f"{wanted[0]:.2f}, {wanted[1]:.2f}")
    if abs(have[2] - wanted[2]) > max(ACROSS_SHARE * wanted[2], ACROSS_LEAST):
        found.append(f"{what}: {have[2]:.5f} degrees across; overhead.py has it {wanted[2]:.5f}")
    return found


def faults(seen, found):
    """Each way the sky the stage holds differs from what overhead.py says is overhead (module docstring; a light under
    the horizon held is one in the sky but not overhead)."""
    seen = risen(seen)
    faults_found = []
    for body in seen["bodies"]:
        faults_found += ball_faults(body["name"], (body["azimuth"], body["altitude"], body["across"]),
                                    found["bodies"].get(body["body"]))
    for light in seen["lights"]:
        key = settings.key_of(light["name"])
        if key not in found["lights"]:
            faults_found.append(f"the light {light['name']}: overhead, missing from the scene's lights")
        elif apart((light["azimuth"], light["altitude"]), found["lights"][key]) > WAY_WITHIN:
            have = found["lights"][key]
            faults_found.append(f"the light {light['name']}: shines from {have[0]:.2f}, {have[1]:.2f}; overhead.py "
                                f"has it at {light['azimuth']:.2f}, {light['altitude']:.2f}")
        if light.get("of") and light.get("across"):
            faults_found += ball_faults(f"{light['name']}'s disc", (light["azimuth"], light["altitude"],
                                                                    light["across"]), found["discs"].get(light["of"]))
    for backdrop in seen["backdrops"]:
        if found["backdrops"].get(settings.key_of(backdrop["name"])) != backdrop["shape"]:
            faults_found.append(f"the backdrop {backdrop['name']} ({backdrop['shape']}): missing from the sky")
    wanted = {"bodies": {body["body"] for body in seen["bodies"]},
              "lights": {settings.key_of(light["name"]) for light in seen["lights"]},
              "discs": {light["of"] for light in seen["lights"] if light.get("of") and light.get("across")},
              "backdrops": {settings.key_of(backdrop["name"]) for backdrop in seen["backdrops"]}}
    words = {"bodies": "the body", "lights": "the light", "discs": "the disc of", "backdrops": "the backdrop"}
    faults_found += [f"{words[group]} {name}: in the sky, but not overhead" for group, names in wanted.items()
                     for name in sorted(set(found[group]) - names)]
    return faults_found
