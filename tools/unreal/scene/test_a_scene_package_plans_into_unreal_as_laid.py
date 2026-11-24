"""Invariant: a scene package planned for Unreal (plan.planned) stands in Unreal as it was laid and wears its own looks:
every copy's actor transform puts its object's points where the copy's matrix puts them (through the expected basis and
through any other the calibration box reads); the calibration box's bounds give back the basis it was imported
through, the bounds UE 5.8's import gave (#222, run 8) read as the expected basis, and bounds of no such box are
refused; an object's parts are its glTF scene's mesh nodes, however deep; a look shared by two objects is one
Material Instance, a baked recipe's maps its own instance named by its surface (its map page dropped), its pictures
one texture a way they are read; glow is its factor times its strength in Unreal's units (times LUMENS_A_WATT), a
transmitting look is glass at 1 - transmission; a solid object is Nanite, a glass one and a character not; the film
path's camera keys see along each frame's aim with no roll at the focal length its field of view needs, its yaw
unwound, and a package seated in its area's frame has the path (in the place's own frame) laid on its seat, one in an
area's frame with no seat refused; the sun shines from where it stands, in lux, the sky light's strength is in
Unreal's units too, a place with no sky picture is lit by an even sky of its ambient, and the exposure divides the
lumens back out.

Breaks (each applied once, seen red, reverted), in tools/unreal/scene:
- frames.copy_transform: the turn taken B R (no B^T) -> the turned copies' points land off their laid spots
- frames.quaternion: the first branch's x sign flipped -> the turned copies' points land off their laid spots
- frames.basis_from_bounds: every side read +1 -> another basis's -1 side is read back as +1
- frames.BASIS: left at (-z, +x, +y) as first assumed -> run 8's measured bounds are not the expected basis
- looks.mesh_nodes: only the scene's root nodes counted -> the pane's two parts under a group count none
- frames.rotator: roll read from side against top swapped -> every level camera key rolls 90 degrees
- looks.factors_of: the emissive strength unread -> the glow is (683, 341.5, 0), not (2732, 1366, 0)
- looks.factors_of: LUMENS_A_WATT left out -> the glow is (4, 2, 0), 683 times too dark under the exposure
- looks.factors_of: the transmission unread -> the pane's glass is a solid look
- looks.texture_name: how a picture is read left out -> the map read as colour and as data is one texture
- looks.surface_of: the map page kept -> the rust's instance is named for "recipe/rust@1 map2"
- looks.solid: the glass unread -> the pane is Nanite
- camera.keys: the yaws left wound -> the fourth key's yaw is -170, not 190
- camera.keys: the eye not laid on the seat -> the seated camera stands at (0, 0, 160), not (1000, 500, 140)
- camera.keys: the aim not laid on the seat -> the seated camera looks along -y, not -x
- plan.seat_of: an area's frame with no seat let through -> that package is planned, not refused
- camera.focal_length: the half angle doubled (fov * 2) -> 90 degrees reads as no finite focal length, not 18 mm
- layout.directional: the sun's way not turned round -> the sun shines away from where it stands
- layout.environment: the sky's strength not in Unreal's units -> 1.0, not 683
- layout.lit_by_ambient: the ambient left unlaid -> a night has no sky light
- layout.rgbe: the exponent's bias 128 dropped -> the even sky reads 2 ** 128 times too bright
"""
import io
import json
import math
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import frames  # noqa: E402
import layout  # noqa: E402
import plan  # noqa: E402


def png(colour):
    held = io.BytesIO()
    Image.new("RGB", (8, 8), colour).save(held, format="PNG")
    return held.getvalue()


def gltf(path, materials, pictures, skinned=False, nodes=({"mesh": 0},)):
    """A glTF of materials and nodes only (what the plan reads), its pictures in its .bin by buffer view; its scene
    the first node."""
    binary, views = b"", []
    for data in pictures:
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data)})
        binary += data + b"\0" * (-len(data) % 4)
    path.with_suffix(".bin").write_bytes(binary)
    document = {"asset": {"version": "2.0"}, "materials": materials, "bufferViews": views,
                "images": [{"bufferView": number, "mimeType": "image/png"} for number in range(len(pictures))],
                "textures": [{"source": number} for number in range(len(pictures))],
                "buffers": [{"byteLength": len(binary), "uri": path.with_suffix(".bin").name}],
                "nodes": list(nodes), "scenes": [{"nodes": [0]}]}
    if skinned:
        document["skins"] = [{"joints": [0]}]
    path.write_text(json.dumps(document))


def turn_y(degrees, scale, spot):
    """A copy's matrix (16 numbers column by column) turned about +y, evenly scaled, at `spot`."""
    cos, sin = math.cos(math.radians(degrees)) * scale, math.sin(math.radians(degrees)) * scale
    return [cos, 0, -sin, 0, 0, scale, 0, 0, sin, 0, cos, 0, *spot, 1]


def turn_x(degrees, spot):
    cos, sin = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [1, 0, 0, 0, 0, cos, sin, 0, 0, -sin, cos, 0, *spot, 1]


def package(root):
    """A small package: a crate (a plain steel look, a baked rust recipe's map page, a glow), a pane (the same steel,
    a transmitting glass, the rust's data map read as colour too) and a walker, a lamp, a sun, a sky; and a film path."""
    (root / "objects").mkdir(parents=True)
    steel = {"name": "surface/steel@1", "pbrMetallicRoughness": {"baseColorFactor": [0.5, 0.5, 0.5, 1.0],
                                                                 "metallicFactor": 1.0, "roughnessFactor": 0.3},
             "doubleSided": True}
    rust = {"name": "recipe/rust@1 map2", "doubleSided": True, "normalTexture": {"index": 2},
            "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 1}}}
    glow = {"name": "surface/glow@1", "emissiveFactor": [1.0, 0.5, 0.0],
            "extensions": {"KHR_materials_emissive_strength": {"emissiveStrength": 4.0}}}
    glass = {"name": "surface/glass@1", "pbrMetallicRoughness": {"baseColorFactor": [0.9, 0.9, 1.0, 1.0]},
             "extensions": {"KHR_materials_transmission": {"transmissionFactor": 0.8},
                            "KHR_materials_ior": {"ior": 1.5}}}
    data = {"name": "surface/painted@1", "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}
    gltf(root / "objects/crate.gltf", [steel, rust, glow], [png((150, 60, 20)), png((0, 200, 0)), png((128, 128, 255))])
    gltf(root / "objects/pane.gltf", [steel, glass, data], [png((0, 200, 0))],
         nodes=({"children": [1]}, {"children": [2, 3]}, {"mesh": 0}, {"mesh": 1}))
    gltf(root / "objects/walker.gltf", [steel], [], skinned=True,
         nodes=({"children": [1, 2]}, {"mesh": 0}, {"mesh": 1}))
    scene = {"format": "score.scene", "version": 1, "place": "yard", "textures": {"use": "film"},
             "objects": {name: {"file": f"objects/{name}.gltf", "kind": "character" if name == "walker" else "model"}
                         for name in ("crate", "pane", "walker")},
             "instances": [{"object": "crate", "name": "crate", "matrix": turn_y(0, 1, [1, 2, 3])},
                           {"object": "crate", "name": "crate_2", "matrix": turn_y(90, 2, [-4, 0, 5])},
                           {"object": "pane", "name": "pane", "matrix": turn_x(30, [0, 1, -2])},
                           {"object": "walker", "name": "walker", "matrix": turn_y(200, 1, [2, 0, 2]),
                            "plays": {"animation": "walk", "starts": 0.0, "loops": True}}],
             "lamps": [{"name": "lamp", "kind": "point", "at": [0, 3, 0], "strength": 10.0, "radius": 0.1,
                        "colour": [1, 1, 1]}, {"name": "sun", "kind": "sun", "strength": 4.0, "colour": [1, 1, 1]}],
             "environment": {"sun": {"name": "sun", "elevation": 30.0, "heading": 90.0, "strength": 4.0,
                                     "colour": [1, 0.9, 0.8], "angle": 0.5}, "exposure": 2.0,
                             "sky": {"file": "environment/sky.hdr", "turn": 15.0, "strength": 1.0}}}
    (root / "scene.json").write_text(json.dumps(scene))
    views = [((0, 1.6, 0), (0, 1.6, -10)), ((0, 1.6, 0), (10, 1.6, 0)), ((0, 1.6, 0), (0, 1.6, 10)),
             ((0, 1.6, 0), (math.sin(math.radians(-10)) * 10, 1.6, math.cos(math.radians(-10)) * 10)),
             ((0, 1.6, 0), (0, 11.6, -10))]
    (root / "path.json").write_text(json.dumps({"fps": 24, "views": [
        {"frame": number, "eye": list(eye), "aim": list(aim), "up": [0, 1, 0], "fov": 90.0}
        for number, (eye, aim) in enumerate(views)]}))
    return root


def rotated(quaternion, way):
    """A way turned by a unit quaternion [x, y, z, w]."""
    axis, real = quaternion[:3], quaternion[3]
    inner = cross(axis, way)
    outer = cross(axis, inner)
    return [way[index] + 2 * real * inner[index] + 2 * outer[index] for index in range(3)]


def cross(first, second):
    return [first[1] * second[2] - first[2] * second[1], first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0]]


def placement_error(made, scene, basis):
    """The farthest any of an object's points lands from where its copy's matrix lays it, in centimetres."""
    worst = 0.0
    for actor, copy in zip(made["actors"], scene["instances"]):
        rows = frames.column_matrix(copy["matrix"])
        for local in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0.3, -0.7, 2.0)):
            laid = frames.point(basis, [sum(rows[row][column] * ([*local, 1])[column] for column in range(4))
                                        for row in range(3)])
            moved = rotated(actor["transform"]["rotation"],
                            [value * actor["transform"]["scale"] for value in frames.point(basis, local)])
            placed = [moved[index] + actor["transform"]["location"][index] for index in range(3)]
            worst = max(worst, max(abs(placed[index] - laid[index]) for index in range(3)))
    return worst


def bounds_through(basis):
    """The calibration box's Unreal bounds as an import through `basis` would give them."""
    corners = [frames.point(basis, (x, y, z)) for x in (0, frames.CALIBRATION[0]) for y in (0, frames.CALIBRATION[1])
               for z in (0, frames.CALIBRATION[2])]
    return [min(corner[axis] for corner in corners) for axis in range(3)], \
        [max(corner[axis] for corner in corners) for axis in range(3)]


def ahead_of(rotation):
    """A rotator's +x as Unreal's FRotationMatrix turns it."""
    pitch, yaw = math.radians(rotation["pitch"]), math.radians(rotation["yaw"])
    return [math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)]


def first_pixel(hdr):
    """A flat Radiance picture's first pixel as linear RGB."""
    data = hdr.read_bytes()
    pixel = data[data.index(b"+X") + data[data.index(b"+X"):].index(b"\n") + 1:][:4]
    return [value * 2.0 ** (pixel[3] - 136) for value in pixel[:3]]


def test_a_scene_package_plans_into_unreal_as_laid(tmp_path):
    root = package(tmp_path / "package")
    scene = json.loads((root / "scene.json").read_text())
    other = ((0, 1, 0), (0, 0, -1), (1, 0, 0))  # another import's axes, as a calibration might read them
    made = plan.planned(root, tmp_path / "into", root / "path.json")
    remade = plan.planned(root, tmp_path / "into_other", root / "path.json", other)
    seat = turn_y(90, 1, [10, -0.2, 5])  # the place turned a quarter and moved onto its area seat
    in_area = dict(scene, frame="the area square's frame (the place's seat): metres, y up")
    (root / "scene.json").write_text(json.dumps(dict(in_area, seat=seat)))
    seated = plan.planned(root, tmp_path / "into_seated", root / "path.json")["camera"]["keys"][0]
    (root / "scene.json").write_text(json.dumps(in_area))
    try:
        plan.planned(root, tmp_path / "into_unseated", root / "path.json")
        unseated = "planned"
    except ValueError:
        unseated = "refused"
    try:
        frames.basis_from_bounds([0, 0, 0], [100, 100, 300])  # two axes a metre long: no calibration box
        garbage = "read"
    except ValueError:
        garbage = "refused"
    materials = {look["name"]: look for look in made["materials"]}
    meshes = {mesh["object"]: mesh for mesh in made["meshes"]}
    crate, pane = ([materials[name] for name in meshes[key]["slots"].values()] for key in ("crate", "pane"))
    textures = {about["name"]: about for about in made["textures"]}
    keys = made["camera"]["keys"]
    sun = made["environment"]["sun"]
    night = layout.lit_by_ambient({"sky": None, "ambient": [0.5, 0.25, 0.125]}, tmp_path / "night")
    toward = frames.turned(frames.BASIS, [math.cos(math.radians(30)) * math.cos(math.radians(90)),
                                          math.sin(math.radians(30)),
                                          math.cos(math.radians(30)) * math.sin(math.radians(90))])
    answer = {
        "placed within a micron": placement_error(made, scene, frames.BASIS) < 1e-4,
        "placed through another basis": placement_error(remade, scene, other) < 1e-4,
        "basis read back": [frames.basis_from_bounds(*bounds_through(basis)) == basis for basis in (frames.BASIS, other)],
        "run 8's bounds are the expected basis": frames.basis_from_bounds([0, 0, 0], [100, 300, 200]) == frames.BASIS,
        "parts": {name: mesh["parts"] for name, mesh in meshes.items()},
        "sky strength": made["environment"]["sky"]["strength"],
        "night sky": (night["sky"]["strength"], first_pixel(pathlib.Path(night["sky"]["file"]))),
        "no box": garbage,
        "steel shared": meshes["crate"]["slots"]["surface/steel@1"] == meshes["pane"]["slots"]["surface/steel@1"],
        "rust": (crate[1]["surface"], crate[1]["master"], sorted(crate[1]["textures"])),
        "glow": crate[2]["vectors"]["Emissive"],
        "glass": (pane[1]["master"], round(pane[1]["scalars"]["Opacity"], 6), pane[1]["scalars"]["IOR"]),
        "textures read apart": sorted((about["srgb"], about["normal"]) for name, about in textures.items()
                                      if not name.startswith("T_White") and name != "T_FlatNormal"),
        "pictures written": all(pathlib.Path(about["file"]).is_file() for about in made["textures"])
        and Image.open(textures["T_FlatNormal"]["file"]).getpixel((0, 0)) == (128, 128, 255),
        "nanite": {name: (mesh["nanite"], mesh["character"]) for name, mesh in meshes.items()},
        "camera": [(round(key["rotation"]["yaw"], 6), round(key["rotation"]["pitch"], 6), round(key["rotation"]["roll"], 6),
                    round(key["focal_length"], 6)) for key in keys],
        "camera at": [round(value, 6) for value in keys[0]["location"]],
        "seated camera": ([round(value, 6) for value in seated["location"]],
                          [round(value, 6) + 0.0 for value in ahead_of(seated["rotation"])]),
        "area frame with no seat": unseated,
        "sun": ([round(value, 6) for value in ahead_of(sun["rotation"])] ==
                [round(-value, 6) for value in toward], sun["lux"]),
        "exposure": round(made["environment"]["exposure_bias"], 6),
        "lamp": (made["lamps"][0]["location"], made["lamps"][0]["lumens"]),
        "caps": made["caps"]["use"],
    }
    assert answer == {
        "placed within a micron": True, "placed through another basis": True, "basis read back": [True, True],
        "run 8's bounds are the expected basis": True, "parts": {"crate": 1, "pane": 2, "walker": 2},
        "sky strength": 683.0, "night sky": (683.0, [0.5, 0.25, 0.125]),
        "no box": "refused", "steel shared": True,
        "rust": ("recipe/rust@1", "solid", ["BaseColorMap", "MetalRoughnessMap", "NormalMap"]),
        "glow": [2732.0, 1366.0, 0.0, 1.0], "glass": ("glass", 0.2, 1.5),
        "textures read apart": [(False, False), (False, True), (True, False), (True, False)],
        "pictures written": True,
        "nanite": {"crate": (True, False), "pane": (False, False), "walker": (False, True)},
        "camera": [(-90.0, 0.0, 0.0, 18.0), (0.0, 0.0, 0.0, 18.0), (90.0, 0.0, 0.0, 18.0), (100.0, 0.0, 0.0, 18.0),
                   (270.0, 45.0, 0.0, 18.0)],
        "camera at": [0.0, 0.0, 160.0],
        "seated camera": ([1000.0, 500.0, 140.0], [-1.0, 0.0, 0.0]), "area frame with no seat": "refused",
        "sun": (True, 4.0 * 683.0), "exposure": round(math.log2(2.0 / 683.0), 6),
        "lamp": ([0.0, 0.0, 300.0], 6830.0), "caps": "film"}, answer
    json.dumps(made)  # the plan is what plan.py writes
