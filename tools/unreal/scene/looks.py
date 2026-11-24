"""A scene package's looks as Unreal materials (#221): every picture an object's glTF carries written out once as a
texture to import, and every glTF material one Material Instance of one of our MASTERS, its parameters our own factors
and maps. The finishes are the package's own (a palette recipe's baked maps, a library surface's maps and factors),
never an outside texture matched by name (the library rule, #217).

One Material Instance a library surface: materials of equal master, parameters and pictures are one instance however
many objects wear them (a plain or image surface laid on many objects is one); a baked recipe's maps belong to one
object's unwrap, so each of its maps is an instance of its own. Glow is its factor times its strength
(KHR_materials_emissive_strength) set by us, glass its transmission and IOR (KHR_materials_transmission, _ior): neither
is left to the glTF import (#217's open point). Plain Python with no numpy: Unreal's own Python runs it.
"""
import base64
import hashlib
import json
import pathlib
import re
import struct
import zlib

# Our master materials (editor.py builds them from code): `solid` opaque, `masked` cut by its colour's alpha at its
# cutoff, `glass` see-through (its opacity 1 - transmission, refracting at its IOR).
MASTERS = ("solid", "masked", "glass")
# A picture's slot: glTF's texture name, the master's parameter, whether it is read as colour (sRGB) and a normal map.
SLOTS = (("baseColorTexture", "BaseColorMap", True, False), ("metallicRoughnessTexture", "MetalRoughnessMap", False, False),
         ("normalTexture", "NormalMap", False, True), ("emissiveTexture", "EmissiveMap", True, False),
         ("occlusionTexture", "OcclusionMap", False, False))
# Our own 4 x 4 fillers, what a master reads in a slot a material has no picture for (a factor times white is the
# factor, as glTF reads it): white read as colour, white read as data, a flat normal; {name: (colour, srgb, normal)}.
FILLERS = {"T_White": ((255, 255, 255), True, False), "T_WhiteData": ((255, 255, 255), False, False),
           "T_FlatNormal": ((128, 128, 255), False, True)}
MAP_PAGE = re.compile(r" map\d+$")  # scene_package's name for a baked look's second and later maps


def document_of(gltf):
    """An object's glTF document and its buffers' bytes (each a file beside it or a data URI)."""
    document = json.loads(gltf.read_text())
    buffers = []
    for buffer in document.get("buffers", []):
        uri = buffer.get("uri", "")
        buffers.append(base64.b64decode(uri.split(",", 1)[1]) if uri.startswith("data:")
                       else (gltf.parent / uri).read_bytes())
    return document, buffers


def picture_bytes(gltf, document, buffers, image):
    """One glTF image's bytes and its file ending: from its buffer view, its data URI or its file."""
    if "bufferView" in image:
        view = document["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        data = buffers[view.get("buffer", 0)][start:start + view["byteLength"]]
    elif image.get("uri", "").startswith("data:"):
        data = base64.b64decode(image["uri"].split(",", 1)[1])
    else:
        data = (gltf.parent / image["uri"]).read_bytes()
    return bytes(data), ".jpg" if data[:2] == b"\xff\xd8" else ".png"


def texture_name(data, colour, normal):
    """A picture's texture asset name: its bytes' digest and how it is read, so the same bytes read alike are one
    texture and read otherwise (as colour, as linear data, as a normal) are another."""
    kind = "N" if normal else "C" if colour else "L"
    return f"T_{hashlib.sha256(data).hexdigest()[:16]}_{kind}"


def surface_of(name):
    """A glTF material's library surface (scene_package.look_name: the surface and its part) without a baked look's
    map page."""
    return MAP_PAGE.sub("", name or "no_look")


def factors_of(material):
    """A glTF material's parameters as our masters read them: {master, vectors, scalars, two_sided}."""
    metal = material.get("pbrMetallicRoughness", {})
    extensions = material.get("extensions", {})
    colour = [float(value) for value in metal.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])]
    strength = float(extensions.get("KHR_materials_emissive_strength", {}).get("emissiveStrength", 1.0))
    glow = [float(value) * strength for value in material.get("emissiveFactor", [0.0, 0.0, 0.0])]
    transmission = float(extensions.get("KHR_materials_transmission", {}).get("transmissionFactor", 0.0))
    alpha_mode = material.get("alphaMode", "OPAQUE")
    master = "glass" if transmission > 0 or alpha_mode == "BLEND" else "masked" if alpha_mode == "MASK" else "solid"
    scalars = {"Metallic": float(metal.get("metallicFactor", 1.0)), "Roughness": float(metal.get("roughnessFactor", 1.0))}
    if master == "glass":
        scalars.update(Opacity=1.0 - transmission if transmission > 0 else colour[3],
                       IOR=float(extensions.get("KHR_materials_ior", {}).get("ior", 1.5)))
    if master == "masked":
        scalars["AlphaCutoff"] = float(material.get("alphaCutoff", 0.5))
    return {"master": master, "vectors": {"BaseColor": colour, "Emissive": glow + [1.0]}, "scalars": scalars,
            "two_sided": bool(material.get("doubleSided", False))}


def instance_name(surface, look):
    """A Material Instance's asset name: its surface's, made safe, and its look's digest."""
    digest = hashlib.sha256(json.dumps(look, sort_keys=True).encode()).hexdigest()[:10]
    return f"MI_{re.sub(r'[^A-Za-z0-9]+', '_', surface).strip('_')[:48]}_{digest}"


def object_looks(gltf, textures):
    """An object's glTF materials as Material Instances: [(slot name, its glTF material name, the instance {name,
    surface, master, vectors, scalars, two_sided, textures {parameter: texture name}})], every picture it reads
    added to `textures` {name: {data, ending, srgb, normal}}."""
    document, buffers = document_of(gltf)
    found = []
    for material in document.get("materials", []):
        look = factors_of(material)
        maps = {}
        for slot, parameter, colour, normal in SLOTS:
            if slot not in material and slot not in material.get("pbrMetallicRoughness", {}):
                continue
            reference = material.get(slot) or material["pbrMetallicRoughness"][slot]
            image = document["images"][document["textures"][reference["index"]]["source"]]
            data, ending = picture_bytes(gltf, document, buffers, image)
            name = texture_name(data, colour, normal)
            textures.setdefault(name, {"data": data, "ending": ending, "srgb": colour, "normal": normal})
            maps[parameter] = name
        look["textures"] = maps
        surface = surface_of(material.get("name"))
        found.append((material.get("name") or "no_look", dict(look, surface=surface,
                                                                 name=instance_name(surface, look))))
    return found


def solid(gltf):
    """Whether an object is drawn by Nanite: no skin and no see-through look (Nanite draws opaque and masked
    materials; a skinned character is a Skeletal Mesh)."""
    document = json.loads(gltf.read_text())
    return not document.get("skins") and all(factors_of(material)["master"] != "glass"
                                             for material in document.get("materials", []))


def chunk(kind, body):
    """One PNG chunk: its length, kind, body and check sum."""
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def filler_png(colour):
    """A 4 x 4 PNG of one colour, written with the standard library (Unreal's Python has no PIL)."""
    row = b"\x00" + bytes(colour) * 4
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(row * 4)) + chunk(b"IEND", b"")


def written_textures(textures, into):
    """Every texture (and the FILLERS) written under <into>/textures as <name><ending>: [{name, file, srgb,
    normal}], fillers first."""
    folder = pathlib.Path(into) / "textures"
    folder.mkdir(parents=True, exist_ok=True)
    listed = []
    for name, (colour, srgb, normal) in FILLERS.items():
        (folder / f"{name}.png").write_bytes(filler_png(colour))
        listed.append({"name": name, "file": str(folder / f"{name}.png"), "srgb": srgb, "normal": normal})
    for name in sorted(textures):
        about = textures[name]
        path = folder / f"{name}{about['ending']}"
        path.write_bytes(about["data"])
        listed.append({"name": name, "file": str(path), "srgb": about["srgb"], "normal": about["normal"]})
    return listed
