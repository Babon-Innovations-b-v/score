"""A laid place as a piece list (`package --pieces`, 2099 #245): score.scene version 2, beside (never instead of) the
version 1 package scene_package.py writes, in tools/props/library/package.py's format (its docstring the format, its
check the check). Written straight from the laid USD with usd-core: no Blender, no bake, no card.

    python -m score.stages.place_build package <folder> <out> --pieces

<out>/scene.json names each distinct piece once (`pieces`) and stands every copy of it (`copies`, its whole transform
as its matrix: a copy stretched unevenly stays a copy, its stretch in the matrix):
- a library piece (a model, take, kit piece, effect or ground laid from score_lib) by its address and the entry's
  content digest from the library's own index, so an engine knows when its held copy is stale; its geometry is the
  entry's: `gltf` names the entry's file an engine reads it from (its web3d/full.glb, else the glTF the laid USD was
  converted from), and an entry that holds no glTF (a kit piece or model kept as USD alone) has its geometry as laid
  written once as meshes/<name>.glb (`mesh`, `sha256`: positions, normals, texture coordinates (`paged`) and a primitive a part),
  still held by the engine once for its address and digest;
- a made piece (an algorithm's: the stair core, blocks, dome shells, tubes, terrain, a ground disc; anything without
  a library entry) as its own small made/<name>.glb in the piece's own frame: positions, normals and one primitive a
  part, no texture, no texture coordinates, no material; two copies of one content are one piece;
- a character (a SkelRoot, a crowd's every copy) as its skinned glTF (skinned.py, as version 1 carries it: its own
  texture), made/<name>.glb, its copy's `plays`; its pictures apart, each once at made/pictures/<sha256>.<ending>.
A piece's parts are its GeomSubsets by name (a model's colour regions), a laid layer as one part by the layer's name
(a lit screen), the rest of a mesh by the mesh's name. Each copy's `looks` gives each part a look id; `looks` holds
each look once, with its surface's `library` address: a palette recipe's `score:recipe:spec` word for word (`spec`),
any other surface's factors (colour, roughness, metal, opacity, glow) and its maps as library references, or `own`
(the piece's own texture: a picture-made model left in its bake, a character). Lamps, doors, chambers, colliders and
the environment are version 1's (scene_package), but the sky is named by its library reference, never copied, and
nothing drawn by Blender is written: no grade lattice (the same for every place: scene_package.VIEW and GRADE) and no
ground albedo (it came from the bake). Every place, seated in an area or not, keeps its own light and its own
exposure (`environment.exposure`, its Environment's score:exposure: the value its own render was drawn at), never an
area's: the game exposes each place at its own value and eases between them at a join (2099 #161: the prologue lit
at the street's 4.5 blew the square, drawn for 0.55, out to white).
Every picture the list names is at most scene_package.HELD_TEXELS a side as the game holds it: a character's taken
down as it is set apart (pictures_apart), and a library picture over it (a look's map, a library glTF's own picture)
held once taken down at made/pictures/<sha256>.png, every look and piece naming it reading that one (held_pictures,
the list's `pictures`).
"""
import hashlib
import json
import pathlib
import shutil
import time

import numpy as np
from pxr import Usd, UsdGeom, UsdShade

from score.stages import place_build
from score.stages.place_build import finished, scene_package
import package  # tools/props/library/package.py, on the path by place_build: the format and its check

MADE = "made"  # the made pieces' folder in the package
MESHES = "meshes"  # the folder of a library piece's geometry as laid, for an entry that holds no glTF
WEB_COPY = "web3d/full.glb"  # an entry's whole web 3D copy (score_lib's web3d), a glTF of it
EVERY_PART = package.EVERY_PART  # a copy's look on every part of its piece (a character in its own texture)
LIBRARY_KINDS = ("model", "take", "kit", "effect", "ground")  # a laid entry of these kinds is a library piece


# --- a piece's parts ------------------------------------------------------------------------------------------------

def layer_of(gprim, holder):
    """The laid layer (a model's own extra layer: a lit screen) a mesh is under, or None."""
    inside = gprim
    while inside.GetPath() != holder.GetPath():
        if place_build.is_layer(inside):
            return inside
        inside = inside.GetParent()
    return None


def face_parts(gprim, holder, face_count):
    """Each face's part name (place_build.parts_of's parts: a mesh under a laid layer the layer's whole, else its
    GeomSubsets', the rest of it the mesh's own name), and the looks bound with each face's number in them
    (scene_package.face_looks)."""
    layer = layer_of(gprim, holder)
    names = np.full(face_count, (layer or gprim).GetName(), dtype=object)
    for subset in UsdShade.MaterialBindingAPI(gprim).GetMaterialBindSubsets() if layer is None else ():
        names[np.asarray(subset.GetIndicesAttr().Get(), dtype=np.int64)] = subset.GetPrim().GetName()
    looks, chosen = scene_package.face_looks(gprim, face_count)
    return names, looks, chosen


def same_look(one, other):
    """Whether two bound looks are one look: the same prim, or two prims telling the same glTF PBR (a SimReady
    model's meshes each carry their own copy of a material of one name, #156)."""
    if scene_package.pbr_key(one) == scene_package.pbr_key(other):
        return True
    if one is None or other is None:
        return False
    told = scene_package.pbr(one).get("tells")
    return told is not None and told == scene_package.pbr(other).get("tells")


def part_corners(prim):
    """An object's triangles by part in its own frame (its transforms below the object alone, as scene_package's
    gprim_pieces reads them): {part: (positions (k x 3), normals (k x 3), texture coordinates (k x 2) or None when
    a mesh of it has none)} a corner each, and {part: the look bound on it} (Refused when one part wears two
    looks)."""
    corners, bound = {}, {}
    for gprim in scene_package.gprims(prim):
        found = scene_package.drawn(gprim)
        if found is None or not len(found[2]):
            continue
        points, indices, triangles, faces, normals, uv = found
        own = points[indices]
        if normals is not None:
            normals_at = triangles
        elif gprim.IsA(UsdGeom.Mesh):
            normals, normals_at = scene_package.smooth_normals(points, indices, triangles), triangles
        else:
            normals = np.repeat(scene_package.flat_normals(own, triangles), 3, axis=0)
            normals_at = np.arange(len(triangles) * 3).reshape(-1, 3)
        matrix = np.asarray(UsdGeom.XformCache().ComputeRelativeTransform(gprim, prim)[0])
        turn = np.linalg.inv(matrix[:3, :3]).T
        flipped = np.linalg.det(matrix[:3, :3]) < 0
        names, looks, per_face = face_parts(gprim, prim, int(faces.max()) + 1)
        per_triangle = names[faces]
        for part in sorted(set(per_triangle)):
            for look in {scene_package.pbr_key(looks[number]): looks[number]
                         for number in np.unique(per_face[names == part])}.values():
                if not same_look(bound.setdefault(part, look), look):
                    raise place_build.Refused(f"{prim.GetName()}: its part {part} wears two looks "
                                              f"({scene_package.pbr_key(bound[part])}, {scene_package.pbr_key(look)})")
            chosen = per_triangle == part
            placed = own[triangles[chosen].ravel()] @ matrix[:3, :3] + matrix[3, :3]
            turned = normals[normals_at[chosen].ravel()] @ turn
            turned /= np.maximum(np.linalg.norm(turned, axis=1, keepdims=True), 1e-12)
            page = None if uv is None else uv[triangles[chosen].ravel()]
            if flipped:
                placed = placed.reshape(-1, 3, 3)[:, ::-1].reshape(-1, 3)
                turned = turned.reshape(-1, 3, 3)[:, ::-1].reshape(-1, 3)
                page = None if page is None else page.reshape(-1, 3, 2)[:, ::-1].reshape(-1, 2)
            held = corners.get(part)
            corners[part] = (placed, turned, page) if held is None else (
                np.vstack([held[0], placed]), np.vstack([held[1], turned]),
                None if held[2] is None or page is None else np.vstack([held[2], page]))
    return corners, bound


PAGE_AREA = 1e-6  # texture coordinates whose triangles cover less of the unit square than this lay no page


def covers(uv):
    """Whether corner texture coordinates lay a page: their triangles cover some of the unit square (a kit piece's
    palette swatch puts each face's corners on one point of its swatch sheet, which covers none)."""
    if uv is None:
        return False
    triangle = uv.reshape(-1, 3, 2)
    one, other = triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]
    return float(np.abs(one[:, 0] * other[:, 1] - one[:, 1] * other[:, 0]).sum()) / 2.0 > PAGE_AREA


def boxed(corners):
    """Each part's corners given texture coordinates projected from the piece's own box (v up the piece, its y),
    each triangle onto the box side its face looks out of, read as one looking at that side (u to the right), so a
    side's face spans the unit square: a decal's page laid on a kit card whose own coordinates are its palette
    swatch (the flat's calendar, 2099 #161)."""
    points = np.vstack([positions for positions, _, _ in corners.values()])
    low, side = points.min(axis=0), np.maximum(np.ptp(points, axis=0), 1e-9)
    paged = {}
    for part, (positions, normals, _) in corners.items():
        triangle = positions.reshape(-1, 3, 3)
        facing = np.cross(triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0])
        axis = np.repeat(np.abs(facing).argmax(axis=1), 3)
        sign = np.repeat(np.sign(facing[np.arange(len(facing)), np.abs(facing).argmax(axis=1)]), 3)
        across = (positions - low) / side
        u = np.where(axis == 0, np.where(sign > 0, 1.0 - across[:, 2], across[:, 2]),
                     np.where(axis == 2, np.where(sign > 0, across[:, 0], 1.0 - across[:, 0]), across[:, 0]))
        v = np.where(axis == 1, across[:, 2], across[:, 1])
        paged[part] = (positions, normals, np.stack([u, v], axis=1))
    return paged


def paged(corners):
    """A library piece's corners with the texture coordinates its glTF carries: its meshes' own where every part's
    lay a page (a SimReady model's maps read by them), else its box's (`boxed`)."""
    if all(covers(uv) for _, _, uv in corners.values()):
        return corners
    return boxed(corners)


def made_glb(corners, pages=False):
    """A piece's GLB: one mesh a part (named by it), welded positions and normals, no material; texture coordinates
    (TEXCOORD_0, `paged`) when `pages` (a library piece's geometry as laid, whose looks' maps read them), none for a
    made piece."""
    import trimesh
    scene = trimesh.Scene()
    corners = paged(corners) if pages else corners
    for part in sorted(corners):
        positions, normals, uv = corners[part]
        vertices, normals, uv, faces = scene_package.welded(positions, normals, uv if pages else None)
        visual = trimesh.visual.TextureVisuals(uv=uv) if pages else None
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_normals=normals, visual=visual, process=False)
        scene.add_geometry(mesh, node_name=part, geom_name=part)
    document, binary = scene_package.unpacked(scene.export(file_type="glb", include_normals=True), None)
    document.pop("materials", None)
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            primitive.pop("material", None)
    return scene_package.packed(document, binary)


def size_of(corners):
    """A piece's box sides (x, y, z, metres) in its own frame and its triangle count."""
    points = np.vstack([positions for positions, _, _ in corners.values()])
    return [round(float(side), 4) for side in np.ptp(points, axis=0)], sum(len(positions) // 3
                                                                           for positions, _, _ in corners.values())


# --- looks ----------------------------------------------------------------------------------------------------------

def look_record(folder, look):
    """A place's look as the piece list keeps it: its library surface (`library`) and its palette recipe's spec word
    for word (`spec`, score:recipe:spec), else its factors as the look has them and its maps as library references;
    None for no look."""
    if look is None:
        return None
    surface = scene_package.text_of(look.GetPrim(), "score:surface")
    spec = scene_package.recipe_spec(look)
    if spec is not None:
        return {"library": surface, "spec": spec}
    shader = look.ComputeSurfaceSource()[0]
    record = {"library": surface}
    if not shader:
        return record
    record.update(
        colour=[round(float(value), 6) for value in scene_package.value_of(shader, "diffuseColor", (0.18, 0.18, 0.18))],
        roughness=round(float(scene_package.value_of(shader, "roughness", 0.5)), 6),
        metal=round(float(scene_package.value_of(shader, "metallic", 0.0)), 6),
        opacity=round(float(scene_package.value_of(shader, "opacity", 1.0)), 6),
        glow=[round(float(value), 6) for value in scene_package.value_of(shader, "emissiveColor", (0.0, 0.0, 0.0))])
    maps = {}
    for name in ("diffuseColor", "roughness", "metallic", "normal", "emissiveColor"):
        found = scene_package.texture_of(shader, name)
        if found is not None:
            reference = scene_package.library_reference(folder, found[0])
            if reference is None:
                raise place_build.Refused(f"{look.GetPath()}: its map {found[0]} is from no library entry")
            maps[name] = {"file": reference, "read": found[1],
                          "scale": None if found[2] is None else [round(float(value), 6) for value in found[2]]}
    if maps:
        record["maps"] = maps
        record["tile_metres"] = scene_package.tile_of([pathlib.Path(found[0]) for found in (
            scene_package.texture_of(shader, name) for name in maps)])
    return record


def look_id(record):
    """A look's id: its surface's name and the start of its record's hash, so one look laid on many parts is one."""
    name = (record.get("library") or "none").split("/")[-1].split("@")[0]
    return f"{name}-{hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:10]}"


def own_look(prim, look):
    """Whether the look is the object's own bake (bound from inside it and naming no library surface): never a place's
    look, nor a library surface a model binds on its own parts (wardrobe_1's varnished wood), which the engine draws
    from the library as any place look; its mesh piece carries no material, and 2099 drew such models white (#161)."""
    return (look is not None and look.GetPath().HasPrefix(prim.GetPath())
            and not scene_package.text_of(look.GetPrim(), "score:surface"))


def copy_looks(folder, prim, piece, bound, looks):
    """A copy's {part: look id}, each new look added to `looks` (own: the piece's own texture)."""
    chosen = {}
    for part, look in sorted(bound.items()):
        record = {"own": piece} if own_look(prim, look) else look_record(folder, look)
        if record is None:
            record = {"library": None}
        key = f"own-{piece}" if "own" in record else look_id(record)
        looks.setdefault(key, record)
        chosen[part] = key
    return chosen


# --- pieces ---------------------------------------------------------------------------------------------------------

def library_address(prim):
    """The library entry a copy lays, when it is one of LIBRARY_KINDS at a version; else None (made for the place)."""
    address = scene_package.text_of(prim, "score:library")
    if not address or "@" not in address or address.split("/", 1)[0] not in LIBRARY_KINDS:
        return None
    return address


def placed_copy(name, piece, kind, world):
    """One copy: its piece, name, kind and whole transform as glTF writes a node's matrix (column by column)."""
    return {"piece": piece, "name": name, "kind": kind,
            "matrix": [round(float(value), 6) + 0.0 for value in np.asarray(world).reshape(-1)]}


def even_scale(world):
    """The scale a copy's mass goes by: the cube root of its volume's stretch."""
    return round(float(abs(np.linalg.det(np.asarray(world)[:3, :3])) ** (1.0 / 3.0)), 6)


def laid_file(prim):
    """The file name a copy's first reference lays (a library copy's converted USD under assets/), or None."""
    references = prim.GetMetadata("references").GetAddedOrExplicitItems() if prim.HasMetadata("references") else []
    paths = [str(reference.assetPath) for reference in references if reference.assetPath]
    return pathlib.PurePosixPath(paths[0]).name if paths else None


def engine_source(files, laid_name, parts):
    """Where an engine reads a library piece's geometry from, of the entry's `files`: {gltf: its glTF of the laid USD's
    stem, else its web3d/full.glb}, or None when it holds no glTF or the place re-finished it part by part (its
    parts finished.PART<n> are the place's own cut of the entry's faces, which no glTF of the entry holds)."""
    if any(part.startswith(finished.PART) and part[len(finished.PART):].isdigit() for part in parts):
        return None
    stem = pathlib.PurePosixPath(laid_name).stem if laid_name else None
    found = [name for name in files if name.endswith((".glb", ".gltf")) and pathlib.PurePosixPath(name).stem == stem]
    if len(found) == 1:
        return {"gltf": found[0]}
    return {"gltf": WEB_COPY} if WEB_COPY in files else None


def sourced(out, pieces, held, laid):
    """Each library piece given its engine source: the entry's glTF (`gltf`), else its geometry as laid written once
    at meshes/<name>.glb (`mesh`, `sha256`)."""
    for name, piece in pieces.items():
        if "library" not in piece:
            continue
        laid_name, corners = laid[name]
        source = engine_source(held.get(piece["library"], {}).get("files", ()), laid_name, piece["parts"])
        if source is not None:
            piece.update(source)
            continue
        glb = made_glb(corners, pages=True)
        (out / MESHES).mkdir(exist_ok=True)
        (out / MESHES / f"{name}.glb").write_bytes(glb)
        piece.update(mesh=f"{MESHES}/{name}.glb", sha256=hashlib.sha256(glb).hexdigest())


def object_piece(out, prim, pieces, made, laid):
    """The piece an object copies (added to `pieces` when new) and its parts' looks: a library piece by its address
    (its laid file and corners kept in `laid` for its engine source), else a made piece written once by its content
    (`made`: {sha256: piece name}); (piece name, {part: look}) or (None, None) when it draws no face."""
    corners, bound = part_corners(prim)
    if not corners:
        return None, None
    size, triangles = size_of(corners)
    address = library_address(prim)
    if address is not None:
        name = address.split("/", 1)[1].split("@")[0]
        held = pieces.setdefault(name, {"library": address, "parts": sorted(corners), "size": size,
                                        "triangles": triangles})
        if held.get("library") != address:
            raise place_build.Refused(f"{prim.GetName()}: two library entries name the piece {name}")
        held["parts"] = sorted(set(held["parts"]) | set(corners))
        laid.setdefault(name, (laid_file(prim), corners))
        return name, bound
    glb = made_glb(corners)
    digest = hashlib.sha256(glb).hexdigest()
    if digest not in made:
        name = prim.GetName()
        made[digest] = name
        (out / MADE / f"{name}.glb").write_bytes(glb)
        pieces[name] = {"made": f"{MADE}/{name}.glb", "sha256": digest,
                        "from": scene_package.text_of(prim, "score:library"), "parts": sorted(corners),
                        "size": size, "triangles": triangles}
    return made[digest], bound


PICTURES = "pictures"  # under made/: a character's pictures, each once by its sha256 (pictures_apart)
ENDINGS = {"image/png": "png", "image/jpeg": "jpg"}


def pictures_apart(glb):
    """A skinned GLB with its embedded pictures taken out into files of their own, each at most HELD_TEXELS a side as
    the game holds it (scene_package.taken_down): (the GLB naming each as pictures/<sha256>.<ending> beside it, {that
    name: its bytes}). A crowd's copies of one character differ in a few
    pose keys only, so each copy's GLB is its own but their pictures, nearly all their bytes, are held once (the
    square's 1,081 people were 13.8 GB of GLBs, 702 distinct, 20 MB of them pictures each)."""
    document, binary = scene_package.unpacked(glb, None)
    views = document.get("bufferViews", [])
    taken, pictures = {}, {}
    for image in document.get("images", []):
        if "bufferView" not in image:
            continue
        view = views[image.pop("bufferView")]
        start = view.get("byteOffset", 0)
        own = image.pop("mimeType", "")
        data, mime = scene_package.taken_down(binary[start:start + view["byteLength"]])
        mime = mime or own
        name = f"{PICTURES}/{hashlib.sha256(data).hexdigest()}.{ENDINGS.get(mime, 'png')}"
        pictures[name] = data
        image["uri"] = name
        taken[id(view)] = True
    kept, numbers, packed = [], {}, bytearray()
    for number, view in enumerate(views):
        if id(view) in taken:
            continue
        start = view.get("byteOffset", 0)
        packed += b"\0" * (-len(packed) % 4)
        numbers[number] = len(kept)
        kept.append({**view, "byteOffset": len(packed)})
        packed += binary[start:start + view["byteLength"]]
    for accessor in document.get("accessors", []):
        if "bufferView" in accessor:
            accessor["bufferView"] = numbers[accessor["bufferView"]]
    document["bufferViews"] = kept
    if document.get("buffers"):
        document["buffers"][0]["byteLength"] = len(packed)
    return scene_package.packed(document, bytes(packed)), pictures


def library_file(folder, reference):
    """The file a library reference (`kind/id@version/file`) names: the place's assets copy (library_files'
    stage_name: assets/kind/id/version/file, the inverse of scene_package.library_reference), else the library's own
    (library_files.resolve, fetched into its capped cache); None when neither holds it."""
    kind, rest = reference.split("/", 1)
    address, name = rest.split("/", 1)
    entry_id, version = address.rsplit("@", 1)
    copied = pathlib.Path(folder) / "assets" / kind / entry_id / version / name
    if copied.is_file():
        return copied
    return place_build.library_files.resolve(reference)


def library_pictures(folder, looks, pieces):
    """{library reference: its bytes' getter} of every library picture the piece list names: each look's maps, and
    each library glTF piece's own pictures (a file beside it by its uri, `<glTF's folder>/<uri>`, or one in its
    buffer, `<glTF>#images/<n>`), each read where library_file finds it; and [the references neither the place's
    assets nor the library hold]."""
    found, unread = {}, []
    for look in looks.values():
        for given in (look.get("maps") or {}).values():
            found[given["file"]] = library_file(folder, given["file"])
    for piece in pieces.values():
        if "gltf" not in piece:
            continue
        reference = f"{piece['library']}/{piece['gltf']}"
        path = library_file(folder, reference)
        if path is None:
            unread.append(reference)
            continue
        data = path.read_bytes()
        if data[:4] == b"glTF":
            document, binary = scene_package.unpacked(data, None)
        else:  # a .gltf: its buffer the file its uri names beside it
            document = json.loads(data)
            uri = (document.get("buffers") or [{}])[0].get("uri")
            binary = b""
            if uri and not uri.startswith("data:"):
                beside = library_file(folder, f"{piece['library']}/{pathlib.PurePosixPath(piece['gltf']).parent / uri}")
                binary = beside.read_bytes() if beside else b""
        for number, image in enumerate(document.get("images", [])):
            if "bufferView" in image:
                view = document["bufferViews"][image["bufferView"]]
                start = view.get("byteOffset", 0)
                found[f"{reference}#images/{number}"] = bytes(binary[start:start + view["byteLength"]])
            elif not image.get("uri", "data:").startswith("data:"):
                beside = f"{piece['library']}/{pathlib.PurePosixPath(piece['gltf']).parent / image['uri']}"
                found[beside] = library_file(folder, beside)
    unread += [reference for reference, given in found.items() if given is None]
    return {reference: given for reference, given in found.items() if given is not None}, sorted(unread)


def held_pictures(folder, out, looks, pieces):
    """The list's `pictures`: {held: {library reference: {file (made/pictures/<sha256>.png under the package), size
    [w, h], from [w, h]}}, unread [references]}: every library picture it names (library_pictures) that is over
    scene_package.HELD_TEXELS a side written once taken down (scene_package.taken_down), so every look and piece naming
    it reads the one copy at the size the game holds it; `unread` the references no copy of which was found, so not
    measured."""
    import io
    from PIL import Image
    found, unread = library_pictures(folder, looks, pieces)
    held = {}
    for reference, given in sorted(found.items()):
        data = given if isinstance(given, bytes) else given.read_bytes()
        size = Image.open(io.BytesIO(data)).size
        if max(size) <= scene_package.HELD_TEXELS:
            continue
        taken, _ = scene_package.taken_down(data)
        name = f"{MADE}/{PICTURES}/{hashlib.sha256(taken).hexdigest()}.png"
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_bytes(taken)
        held[reference] = {"file": name, "size": list(Image.open(io.BytesIO(taken)).size), "from": list(size)}
    return {"held": held, "unread": unread}


def character_pieces(out, prim, kind, pieces, made, looks):
    """A laid character's copies (scene_package.character_copies: skinned glTFs, checked against UsdSkel's skin) as
    made pieces in their own texture, their pictures apart and held once (pictures_apart): [copy] and [{name, why}] of
    those not carried."""
    laid, refused = scene_package.character_copies(prim)
    walks = walks_of(prim)
    copies = []
    for name, frame, scale, embedded, facts, check in laid:
        glb, pictures = pictures_apart(embedded)
        for picture, data in pictures.items():
            (out / MADE / picture).parent.mkdir(exist_ok=True)
            (out / MADE / picture).write_bytes(data)
        digest = hashlib.sha256(glb).hexdigest()
        if digest not in made:
            made[digest] = name
            (out / MADE / f"{name}.glb").write_bytes(glb)
            pieces[name] = {"made": f"{MADE}/{name}.glb", "sha256": digest, "skinned": True,
                            "from": scene_package.text_of(prim, "score:library"), "parts": [],
                            "size": scene_package.box_size(glb), "triangles": check["triangles"],
                            "clips": facts["clips"], "check": check}
        piece = made[digest]
        looks.setdefault(f"own-{piece}", {"own": piece})
        copy = placed_copy(name, piece, kind, frame)
        copy.update(looks={EVERY_PART: f"own-{piece}"}, plays=facts["plays"])
        if name in walks:
            copy["walks"] = walks[name]
        copies.append(copy)
    return copies, refused


def walks_of(prim):
    """{copy name: {"to": [x, y, z]}} of a crowd's walkers (a PointInstancer whose `score:walks_to` names each
    instance's far end, crowd.py): the end in the scene's frame, the copy walking to it over and over on its walking clip;
    {} for any other character."""
    attribute = prim.GetAttribute("score:walks_to") if prim.IsA(UsdGeom.PointInstancer) else None
    ends = attribute.Get() if attribute and attribute.HasValue() else None
    if not ends:
        return {}
    world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    return {f"{prim.GetName()}_{number}": {"to": [round(float(value), 4) for value in
                                                 (np.array([*end, 1.0]) @ world)[:3]]}
            for number, end in enumerate(ends)}


def write(folder, out):
    """The laid place in <folder> as a piece list in <out>, laid at its area seat (scene_package.seated); scene.json's
    content."""
    folder, out = pathlib.Path(folder), pathlib.Path(out)
    stage, place = place_build.opened(folder)
    seat = place_build.record_of(folder).get("seat")
    with scene_package.seated(stage, place, seat):
        return written_pieces(folder, out, stage, place, seat)


def written_pieces(folder, out, stage, place, seat):
    """write's body: every object a copy of a piece, every character a skinned made piece, the place's looks, lamps,
    doors and environment (version 1's), the library digests read from its index."""
    ready_file = folder / "ready.json"
    roles = json.loads(ready_file.read_text())["roles"] if ready_file.is_file() else None
    for written in (MADE, MESHES):  # a piece list written before: its made pieces, meshes and scene.json
        if (out / written).exists():
            shutil.rmtree(out / written)
    (out / "scene.json").unlink(missing_ok=True)
    (out / MADE).mkdir(parents=True)
    found, characters, left_out = scene_package.laid_objects(stage, place)
    neighbours = set(place_build.record_of(folder).get("backdrop") or []) if seat else set()
    found, characters = ([(prim, kind) for prim, kind in listed if prim.GetName() not in neighbours]
                         for listed in (found, characters))
    left_out += [{"name": name, "why": f"the concept's backdrop: a neighbour place of the area {seat['area']} "
                                       "stands for it (place.json backdrop)"} for name in sorted(neighbours)]
    pieces, made, looks, copies, counts, first_laid = {}, {}, {}, [], {}, {}
    for prim, kind in found:
        piece, bound = object_piece(out, prim, pieces, made, first_laid)
        if piece is None:
            left_out.append({"name": prim.GetName(), "why": "it draws no face"})
            continue
        world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        copy = placed_copy(prim.GetName(), piece, kind, world)
        copy["looks"] = copy_looks(folder, prim, piece, bound, looks)
        if roles is not None:
            copy["role"] = roles.get(prim.GetName())
            copy["collider"] = scene_package.collider_of(folder, prim, copy["role"], even_scale(world))
        copies.append(copy)
        counts[kind] = counts.get(kind, 0) + 1
    for prim, kind in characters:
        laid, refused = character_pieces(out, prim, kind, pieces, made, looks)
        copies += laid
        left_out += refused
        counts[kind] = counts.get(kind, 0) + len(laid)
    addresses = sorted({piece["library"] for piece in pieces.values() if "library" in piece})
    held = package.held_entries(addresses)
    for piece in pieces.values():
        if "library" in piece:
            piece["digest"] = held.get(piece["library"], {}).get("digest")
    sourced(out, pieces, held, first_laid)
    doors, chambers = scene_package.doors_of(stage, place, [copy["name"] for copy in copies])
    for copy in copies:
        if copy["name"] in doors:
            copy["door"] = doors[copy["name"]]
    environment = scene_package.environment_of(stage, place, None)
    environment.update(ground_albedo=None, grade=None)
    lamps = [lamp for lamp in scene_package.lamps_of(stage, place) if lamp["name"] not in neighbours]
    scene = {"format": package.FORMAT, "version": package.PIECES, "place": place,
             "frame": f"the area {seat['area']}'s frame (the place's seat, {seat['from']}): metres, y up"
             if seat else "the place's own frame: metres, y up", "units": "metre", "up": "+y",
             "ground": scene_package.GROUND, "on_seat": [0.0, 0.0], "pieces": pieces, "looks": looks,
             "copies": copies, "lamps": lamps,
             "counts": counts, "physics": "ready.json" if roles is not None else None, "left_out": left_out,
             "chambers": chambers, "environment": environment, "pictures": held_pictures(folder, out, looks, pieces)}
    (out / "scene.json").write_text(json.dumps(scene, indent=1) + "\n")
    return scene


def packaged(folder, out):
    """The piece list written and checked by package.py's own check: its summary, or Refused naming its problems."""
    started = time.monotonic()
    scene = write(folder, out)
    found = package.problems(pathlib.Path(out))
    if found:
        raise place_build.Refused(f"the piece list fails its check: {'; '.join(found[:12])}")
    made_bytes = sum(path.stat().st_size for folder in (MADE, MESHES) for path in (pathlib.Path(out) / folder).rglob("*")
                     if path.is_file())
    return {"package": str(out), "summary": package.summary(pathlib.Path(out)), "pieces": len(scene["pieces"]),
            "library_pieces": sum("library" in piece for piece in scene["pieces"].values()),
            "parts": sum(len(piece["parts"]) for piece in scene["pieces"].values()), "looks": len(scene["looks"]),
            "copies": len(scene["copies"]), "scene_bytes": (pathlib.Path(out) / "scene.json").stat().st_size,
            "made_bytes": made_bytes, "seconds": round(time.monotonic() - started, 1),
            "left_out": scene["left_out"], "check": "sound"}
