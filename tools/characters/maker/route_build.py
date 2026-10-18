"""The people route on a made body (owner, 2026-10-18, score #10), a free prototype on the PC: the accepted made
body's look and clips rebuilt on the SOMA-X base with the route's four changes, written as a glTF the checks read
(joins.py, pokes.py, route_stretch.py) and Blender renders.

    ~/.farm-factory-props/env/bin/python route_build.py <made body.glb> <made rig.npz> <base.npz> <old body.glb>
        <out.glb> [--correctives <correctives.npz>] [--base under|shell] [--labels under|shell] [--no-cut]
        [--shapes 24]

- the garments bound by limb on the base, the arm and leg webs cut and closed (route_bind.py);
- the head split: the made hair kept, the made face dropped, the old SOMA-X head with its drawn face and eyes laid on
  the made skeleton and run down the neck to 2 cm under the collar line, its neck a tuck (route_head.py);
- no settled cloth: the made body's per-clip garment shapes (the Newton settle) are dropped, the clothes move with
  the body (the owner's option A);
- SOMA-X's pose correctives (route_base.py correctives) carried onto the garments by their bind places and baked as
  `--shapes` shared morph targets (the main directions of every clip's offsets), keyed per frame in every clip.

Hard parts, hands and hair keep their made weights (one joint each). The far body is copied as it is.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(MAKER), str(MAKER.parent / "people")]
import glb  # noqa: E402
import joins  # noqa: E402
import pokes  # noqa: E402
import prop_build  # noqa: E402
import route_bind  # noqa: E402
import route_head  # noqa: E402

JOINTS_A_POINT = 4
SHAPES = 24
OLD_HEAD = ("skin_head", "eyes", "irises", "eyebrows")
NODE = "work"
_BYTES = {glb.FLOAT: 4, glb.UNSIGNED_BYTE: 1, glb.UNSIGNED_SHORT: 2, glb.UNSIGNED_INT: 4}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Surface:
    """One drawn surface: material (its document's number), points, normals, texture places, dense weights,
    triangles, and its first tuck point (None: no tuck)."""

    def __init__(self, material, points, uv, weights, faces, tuck_from=None):
        self.material = material
        self.points = points
        self.uv = uv
        self.weights = weights
        self.faces = faces
        self.tuck_from = tuck_from
        self.offsets = None
        self.picture = None


# --- reading --------------------------------------------------------------------------------------------------------

def skin_names(document):
    return [document["nodes"][joint]["name"] for joint in document["skins"][0]["joints"]]


def bind_of(document, blob):
    """The skin's joints' bind (world) matrices."""
    skin = document["skins"][0]
    inverse = joins.accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    return np.linalg.inv(inverse)


def dense(joints, weights, count):
    """Four joints and weights a point as one weight per joint."""
    found = np.zeros((len(joints), count))
    np.add.at(found, (np.repeat(np.arange(len(joints)), joints.shape[1]), joints.ravel().astype(int)),
              weights.ravel())
    return found


def surfaces_of(document, blob, node_name):
    """The node's surfaces in its mesh's order."""
    node = next(found for found in document["nodes"] if found.get("name") == node_name)
    count = len(document["skins"][0]["joints"])
    found = []
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        attributes = primitive["attributes"]
        points = joins.accessor(document, blob, attributes["POSITION"])
        uv = joins.accessor(document, blob, attributes["TEXCOORD_0"]) if "TEXCOORD_0" in attributes else None
        weights = dense(joins.accessor(document, blob, attributes["JOINTS_0"]),
                        joins.accessor(document, blob, attributes["WEIGHTS_0"]), count)
        faces = joins.accessor(document, blob, primitive["indices"]).astype(int).reshape(-1, 3)
        extras = document["materials"][primitive["material"]].get("extras", {})
        found.append(Surface(primitive["material"], points, uv, weights, faces, extras.get("tuck_from")))
    return found


def role_of(document, surface):
    return document["materials"][surface.material].get("extras", {}).get("role")


def name_of(document, surface):
    return document["materials"][surface.material]["name"]


# --- the garments bound by limb -------------------------------------------------------------------------------------

def welding(garments):
    """The garments' points welded where their borders meet: each point's welded number, the welded places and
    the welded triangles' edges."""
    numbers = pokes.weld_map(np.concatenate([surface.points for surface in garments]))
    places = np.zeros((int(numbers.max()) + 1, 3))
    places[numbers] = np.concatenate([surface.points for surface in garments])
    starts = np.cumsum([0] + [len(surface.points) for surface in garments])
    faces = np.concatenate([numbers[surface.faces + start] for surface, start in zip(garments, starts)])
    return numbers, places, route_bind.edges_of(faces), starts


def shoulder_heights(bind, names):
    """Each arm region's shoulder joint height (route_bind.underarm_edges)."""
    return {route_bind.REGIONS.index(arm): float(bind[names.index(arm), 1, 3]) for arm in ("LeftArm", "RightArm")}


def hard_points(document, surfaces, names):
    """The hard parts' own points (their tucks left out) and the joint each rides, as prop_build.py gathers them."""
    points, joints = [np.zeros((0, 3))], [np.zeros(0, dtype=object)]
    for surface in surfaces:
        if role_of(document, surface) == "hard":
            own = surface.tuck_from or len(surface.points)
            points.append(surface.points[:own])
            joints.append(np.full(own, names[int(surface.weights.sum(0).argmax())], dtype=object))
    return np.concatenate(points), np.concatenate(joints)


def garment_bind(garments, label_points, base_points, base_faces, base_weights, names, bind, cut, hard, parents):
    """The welded garments' regions (by the nearest of `label_points`), bind, weights and web edges
    (route_bind.py); the weights then eased onto the hard parts next to them (prop_build.eased_to_hard: a trouser
    leg goes with the boot it covers, or the boot's tuck shows through it, 19 mm on the player standing)."""
    numbers, places, edges, starts = welding(garments)
    regions = route_bind.point_regions(places, edges, label_points, route_bind.base_regions(base_weights, names))
    bound = route_bind.bound_by_region(places, regions, base_points, base_faces, base_weights, names)
    web = np.zeros(len(edges), bool)
    if cut:
        web = route_bind.web_edges(places, edges, regions, bound.places)
        web |= route_bind.underarm_edges(places, edges, regions, shoulder_heights(bind, names))
    weights = route_bind.smoothed(bound.carried(base_weights), edges[~web])
    weights = route_bind.kept_to_limb(weights, regions, names)
    weights = prop_build.eased_to_hard(places, weights, *hard, list(names), parents)
    return {"numbers": numbers, "starts": starts, "regions": regions, "bound": bound, "weights": weights,
            "web": {tuple(pair) for pair in edges[web].tolist()}, "web_edges": int(web.sum())}


def rebound(surface, welded, start):
    """One garment with its new weights and its web cut and closed: the surface, triangles cut, closings."""
    numbers = welded["numbers"][start:start + len(surface.points)]
    cut = route_bind.web_faces(numbers[surface.faces], welded["web"])
    faces, middles = route_bind.closed(surface.faces, welded["regions"][numbers], cut, len(surface.points))
    out = Surface(surface.material, route_bind.with_middles(surface.points, middles),
                  None if surface.uv is None else route_bind.with_middles(surface.uv, middles),
                  route_bind.with_middles(welded["weights"][numbers], middles), faces)
    return out, int(cut.sum()), len(middles)


def bands_rebound(document, surfaces, garments, parents):
    """The tuck bands that take their weights from the garment over them (the bare hands', tucks.py; a boot's
    rides its foot) weighted again from the rebound garments: each band point the nearest garment point's off the
    hand's seam among those on its hand's limb (tucks.limb_weights). Kept on the old weights, a band stood
    10 mm out of the right cuff all through dragging."""
    from scipy.spatial import cKDTree

    import tucks
    cloth_points = np.concatenate([surface.points for surface in garments])
    cloth_weights = np.concatenate([surface.weights for surface in garments])
    for surface in surfaces:
        if name_of(document, surface) != "skin_hands" or surface.tuck_from is None:
            continue
        seam = np.isfinite(cKDTree(surface.points[:surface.tuck_from]).query(
            cloth_points, distance_upper_bound=tucks.SEAM)[0])
        band = surface.points[surface.tuck_from:]
        ring = np.full(len(band), int(surface.weights[:surface.tuck_from].sum(0).argmax()))
        surface.weights = surface.weights.copy()
        surface.weights[surface.tuck_from:] = tucks.limb_weights(band, ring, cloth_points[~seam],
                                                                 cloth_weights[~seam], parents)


def bands_follow_cloth(surfaces, garments, clips):
    """Every tuck band (the hands' and the neck's) given the corrective offsets of the nearest garment point, the part's
    own points none: a band left still while the cuff over it took SOMA-X's correctives showed 2 mm more through it
    (5.8 mm in dragging)."""
    from scipy.spatial import cKDTree
    cloth_points = np.concatenate([surface.points for surface in garments])
    nearest = cKDTree(cloth_points)
    for surface in surfaces:
        if surface.tuck_from is None or surface.offsets is not None:
            continue
        band = nearest.query(surface.points[surface.tuck_from:])[1]
        surface.offsets = {}
        for clip in clips:
            cloth = np.concatenate([garment.offsets[clip] for garment in garments], axis=1)
            moved = np.zeros((len(cloth), len(surface.points), 3), np.float32)
            moved[:, surface.tuck_from:] = cloth[:, band]
            surface.offsets[clip] = moved


# --- the head -------------------------------------------------------------------------------------------------------

def made_collar(document, surfaces, bind, names):
    """The made face's collar line by direction round the neck, and the neck's centre."""
    centre = bind[names.index("Neck1"), :3, 3]
    border = []
    for surface in surfaces:
        if name_of(document, surface) == "skin_head":
            own = surface.tuck_from or len(surface.points)
            visible = surface.faces[(surface.faces < own).all(1)]
            border.append(surface.points[route_head.border_points(visible)])
    line = route_head.collar_line(np.concatenate(border), centre, bind[names.index("Neck2"), 1, 3])
    return line, centre


def old_surfaces(old_document, old_blob, names, new_bind):
    """The old body's head surfaces laid on the made bind, with their weights on the made joints: {name: Surface}."""
    old_names = skin_names(old_document)
    order = [old_names.index(name) for name in names]
    old_bind = bind_of(old_document, old_blob)[order]
    found = {}
    for surface in surfaces_of(old_document, old_blob, NODE):
        name = name_of(old_document, surface)
        if name in OLD_HEAD and name not in found:
            surface.weights = surface.weights[:, order]
            surface.points = route_head.laid_on(surface.points, surface.weights, old_bind, new_bind)
            found[name] = surface
    return found


def picture_of(document, blob, material):
    """A material's base colour picture as an array (rows, columns, channels)."""
    import io

    from PIL import Image
    texture = document["textures"][document["materials"][material]["pbrMetallicRoughness"]["baseColorTexture"]["index"]]
    view = document["bufferViews"][document["images"][texture["source"]]["bufferView"]]
    start = view.get("byteOffset", 0)
    return np.asarray(Image.open(io.BytesIO(blob[start:start + view["byteLength"]])).convert("RGB"))


def new_head(old_skin, picture, rig, base_weights, names, line, centre):
    """The old head run down the neck to the seam, tucked under the collar line: a Surface on the old material."""
    cut = float(line.min()) - route_head.SEAM_BELOW
    piece = route_head.head_piece(rig["source_points"], rig["source_faces"], base_weights, names, centre, cut)
    neck = route_head.Extension(*piece[:3], old_skin.points, old_skin.faces, old_skin.uv, old_skin.weights)
    points = np.concatenate([old_skin.points, neck.points])
    faces = np.concatenate([old_skin.faces, neck.faces])
    order, tuck_from = route_head.tuck_order(points, line, centre)
    uv = np.concatenate([old_skin.uv, neck.uv])
    head = Surface(old_skin.material, points[order], uv[order],
                   np.concatenate([old_skin.weights, neck.weights])[order], route_head.reordered(order, faces),
                   tuck_from)
    head.picture = route_head.painted_neck(picture, old_skin.points, old_skin.faces, old_skin.uv)
    return head, {"cut_m": round(cut, 4), "collar_line_m": [round(float(value), 4) for value in line],
                  "points": len(points), "neck_triangles_added": len(neck.faces), "piece_points_on_old_head":
                  neck.found, "old_points": len(old_skin.points), "tuck_points": len(points) - tuck_from}


def made_face(document, surfaces, above):
    """The made face's drawn points above the neck (`above`)."""
    found = []
    for surface in surfaces:
        if name_of(document, surface) == "skin_head":
            own = surface.points[:surface.tuck_from or len(surface.points)]
            found.append(own[own[:, 1] > above])
    return np.concatenate(found)


def hair_on_old_head(document, surfaces, old_head, bind, names):
    """The made hair laid on the old head and the old scalp drawn under it (route_head.py): the record."""
    neck = bind[names.index("Neck2"), 1, 3]
    old = old_head["skin_head"]
    matrix = route_head.rigid_fit(made_face(document, surfaces, neck), old.points[old.points[:, 1] > neck])
    hair = [surface for surface in surfaces if name_of(document, surface) == "hair"]
    centre = 0.5 * (bind[names.index("Head"), :3, 3] + bind[names.index("HeadEnd"), :3, 3])
    brow_top = float(old_head["eyebrows"].points[:, 1].max()) + 0.01
    covered = route_head.scalp(old.points, centre, brow_top, bind[names.index("Head"), 1, 3] + 0.03)
    starts = np.cumsum([0] + [len(surface.points) for surface in hair])
    hair_faces = np.concatenate([surface.faces + start for surface, start in zip(hair, starts)])
    laid = np.concatenate([surface.points for surface in hair]) @ matrix[:3, :3].T + matrix[:3, 3]
    scale = route_head.hair_scale(old.points[covered], laid, hair_faces, centre)
    laid = centre + (laid - centre) * scale
    for surface, start in zip(hair, starts):
        surface.points = laid[start:start + len(surface.points)]
    old.points, moved = route_head.under_hair(old.points, laid, hair_faces, centre, covered)
    return {"hair_scale": float(scale), "hair_shift_mm": [round(float(value) * 1000, 1) for value in matrix[:3, 3]],
            "scalp_points_drawn_under_hair": moved, "scalp_points_hair_may_cover": int(covered.sum())}


# --- correctives as shared shapes -----------------------------------------------------------------------------------

def welded_offsets(correctives, clip, bound):
    """A clip's corrective offsets carried onto the welded garment points (frames, points, 3)."""
    offsets = correctives[f"clip_{clip}"].astype(np.float64)
    return np.einsum("pc,fpcd->fpd", bound.shares, offsets[:, bound.corners])


def principal_shapes(stacked, count):
    """The `count` main directions of every frame's offsets (rows of `stacked`, frames x values) by the frames'
    Gram matrix: (shapes x values, each frame's weights, the share of the offsets' energy kept)."""
    gram = stacked @ stacked.T
    values, vectors = np.linalg.eigh(gram)
    top = np.argsort(values)[::-1][:count]
    shapes = (vectors[:, top].T @ stacked) / np.sqrt(np.maximum(values[top], 1e-18))[:, None]
    weights = stacked @ shapes.T
    kept = float(values[top].sum() / max(values.sum(), 1e-18))
    return shapes, weights, kept


# --- writing --------------------------------------------------------------------------------------------------------

class Copying(glb.Contents):
    """glb.Contents that can also take another file's accessors and pictures as they are."""

    def copied(self, document, blob, index):
        """Another file's accessor copied (its bytes and its reading): the new accessor's number."""
        found = document["accessors"][index]
        view = document["bufferViews"][found["bufferView"]]
        size = found["count"] * _WIDTH[found["type"]] * _BYTES[found["componentType"]]
        start = view.get("byteOffset", 0) + found.get("byteOffset", 0)
        self._pad()
        place = len(self._blob)
        self._blob.extend(blob[start:start + size])
        self.views.append({"buffer": 0, "byteOffset": place, "byteLength": size})
        reading = {key: value for key, value in found.items() if key not in ("bufferView", "byteOffset", "sparse")}
        self.accessors.append(dict(reading, bufferView=len(self.views) - 1))
        return len(self.accessors) - 1

    def picture_of(self, document, blob, image):
        """Another file's picture copied: the new image's number."""
        view = document["bufferViews"][document["images"][image]["bufferView"]]
        start = view.get("byteOffset", 0)
        return self.picture(blob[start:start + view["byteLength"]], document["images"][image]["mimeType"])


def strongest(weights):
    """The JOINTS_A_POINT strongest joints a point, their weights shared out to one."""
    order = np.argsort(-weights, axis=1)[:, :JOINTS_A_POINT]
    kept = np.take_along_axis(weights, order, axis=1)
    return order, kept / np.maximum(kept.sum(1, keepdims=True), 1e-12)


def normals_of(points, faces):
    corners = points[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], crossed)
    length = np.linalg.norm(found, axis=1, keepdims=True)
    return np.where(length > 1e-12, found / np.maximum(length, 1e-12), [0.0, 1.0, 0.0])


def flat(values):
    return np.asarray(values, np.float64).ravel().tolist()


def primitive_of(contents, surface, shapes):
    """A surface written: its glTF primitive (with `shapes`, its morph targets, (count, points, 3), or None)."""
    joints, weights = strongest(surface.weights)
    attributes = {
        "POSITION": contents.reading(flat(surface.points), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER, with_bounds=True),
        "NORMAL": contents.reading(flat(normals_of(surface.points, surface.faces)), "VEC3", glb.FLOAT,
                                   glb.ARRAY_BUFFER),
        "JOINTS_0": contents.reading(joints.ravel().tolist(), "VEC4", glb.UNSIGNED_BYTE, glb.ARRAY_BUFFER),
        "WEIGHTS_0": contents.reading(flat(weights), "VEC4", glb.FLOAT, glb.ARRAY_BUFFER)}
    if surface.uv is not None:
        attributes["TEXCOORD_0"] = contents.reading(flat(surface.uv), "VEC2", glb.FLOAT, glb.ARRAY_BUFFER)
    primitive = {"attributes": attributes, "material": surface.material,
                 "indices": contents.reading(surface.faces.ravel().tolist(), "SCALAR", glb.UNSIGNED_INT,
                                             glb.ELEMENT_ARRAY_BUFFER)}
    if shapes is not None:
        primitive["targets"] = [{"POSITION": contents.reading(flat(shape), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER,
                                                              with_bounds=True)} for shape in shapes]
    return primitive


def copied_mesh(contents, document, blob, mesh):
    """A mesh of the made file copied as it is (the far body)."""
    primitives = []
    for primitive in mesh["primitives"]:
        copy = {"attributes": {key: contents.copied(document, blob, index)
                               for key, index in primitive["attributes"].items()},
                "indices": contents.copied(document, blob, primitive["indices"]), "material": primitive["material"]}
        primitives.append(copy)
    return {"primitives": primitives}


def copied_animations(contents, document, blob, clip_weights, node):
    """The clips copied without their morph weights, each keyed with its frames' shape weights when given."""
    found = []
    for animation in document["animations"]:
        samplers, channels, done = [], [], {}
        for channel in animation["channels"]:
            if channel["target"]["path"] == "weights":
                continue
            sampler = animation["samplers"][channel["sampler"]]
            for key in ("input", "output"):
                if sampler[key] not in done:
                    done[sampler[key]] = contents.copied(document, blob, sampler[key])
            samplers.append({"input": done[sampler["input"]], "output": done[sampler["output"]],
                             "interpolation": sampler.get("interpolation", "LINEAR")})
            channels.append({"sampler": len(samplers) - 1, "target": channel["target"]})
        if clip_weights is not None:
            keyed = clip_weights[animation["name"]]
            samplers.append({"input": samplers[0]["input"], "interpolation": "LINEAR",
                             "output": contents.reading(flat(keyed), "SCALAR", glb.FLOAT)})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "weights"}})
        found.append({"name": animation["name"], "samplers": samplers, "channels": channels})
    return found


def png_of(picture):
    """A picture array encoded as PNG bytes."""
    import io

    from PIL import Image
    encoded = io.BytesIO()
    Image.fromarray(picture).save(encoded, format="PNG")
    return encoded.getvalue()


def copied_materials(contents, document, blob, old_document, old_blob, old_head):
    """The made file's materials and pictures, then the old head's (each old head surface's material renumbered)."""
    images = [contents.picture_of(document, blob, image) for image in range(len(document.get("images", [])))]
    textures = [{"source": images[texture["source"]], "sampler": 0} for texture in document.get("textures", [])]
    materials = [dict(material) for material in document["materials"]]
    for name, surface in old_head.items():
        material = json.loads(json.dumps(old_document["materials"][surface.material]))
        source = old_document["textures"][material["pbrMetallicRoughness"]["baseColorTexture"]["index"]]["source"]
        textures.append({"source": contents.picture_of(old_document, old_blob, source) if surface.picture is None
                         else contents.picture(png_of(surface.picture)), "sampler": 0})
        material["pbrMetallicRoughness"]["baseColorTexture"]["index"] = len(textures) - 1
        material["extras"] = {"role": "skin" if name == "skin_head" else "face", "print": True}
        materials.append(material)
        surface.material = len(materials) - 1
    return materials, textures


def written(path, document, blob, old_document, old_blob, old_head, surfaces, shapes, clip_weights):
    """The new body file: the made file's skeleton, far body and clips, the new work surfaces."""
    contents = Copying()
    materials, textures = copied_materials(contents, document, blob, old_document, old_blob, old_head)
    materials[old_head["skin_head"].material]["extras"]["tuck_from"] = old_head["skin_head"].tuck_from
    work_node = next(number for number, node in enumerate(document["nodes"]) if node.get("name") == NODE)
    far = next(node for node in document["nodes"] if node.get("name") == "far")
    meshes = [copied_mesh(contents, document, blob, document["meshes"][far["mesh"]])]
    work = {"name": NODE, "primitives": [primitive_of(contents, surface, None if shapes is None else
                                                      shapes[number])
                                         for number, surface in enumerate(surfaces)]}
    if shapes is not None:
        work["weights"] = [0.0] * len(shapes[0])
        work["extras"] = {"targetNames": [f"corrective.{number}" for number in range(len(shapes[0]))]}
    meshes.append(work)
    nodes = [dict(node) for node in document["nodes"]]
    for node in nodes:
        if "mesh" in node:
            node["mesh"] = 1 if node.get("name") == NODE else 0
    skin = dict(document["skins"][0], inverseBindMatrices=contents.copied(
        document, blob, document["skins"][0]["inverseBindMatrices"]))
    out = {"asset": document["asset"], "scene": 0, "scenes": document["scenes"], "nodes": nodes, "meshes": meshes,
           "skins": [skin], "materials": materials, "textures": textures, "samplers": document["samplers"],
           "animations": copied_animations(contents, document, blob, clip_weights, work_node)}
    return glb.write(path, out, contents)


# --- the build ------------------------------------------------------------------------------------------------------

def stacked_offsets(surfaces, clips):
    """Every clip's frames' offsets over all surfaces as rows (frames x values, float32; zeros on a surface with
    none), and each clip's first row and frame count."""
    sizes = [len(surface.points) for surface in surfaces]
    lengths = {clip: next(len(surface.offsets[clip]) for surface in surfaces if surface.offsets is not None)
               for clip in clips}
    rows = np.zeros((sum(lengths.values()), sum(sizes) * 3), np.float32)
    frames, row = {}, 0
    for clip in clips:
        column = 0
        for surface, size in zip(surfaces, sizes):
            if surface.offsets is not None:
                rows[row:row + lengths[clip], column:column + size * 3] = surface.offsets[clip].reshape(
                    lengths[clip], -1)
            column += size * 3
        frames[clip], row = (row, lengths[clip]), row + lengths[clip]
    return rows, frames


def corrective_shapes(surfaces, clips, count):
    """Every surface's shapes (count, points, 3), each clip's frame weights and the energy share kept, from the
    garments' corrective offsets."""
    sizes = [len(surface.points) for surface in surfaces]
    rows, frames = stacked_offsets(surfaces, clips)
    shapes, weights, kept = principal_shapes(rows, count)
    starts = np.cumsum([0] + sizes) * 3
    per_surface = [shapes[:, start:end].reshape(len(shapes), -1, 3) for start, end in zip(starts[:-1], starts[1:])]
    clip_weights = {clip: weights[first:first + length] for clip, (first, length) in frames.items()}
    return per_surface, clip_weights, kept


def clip_offsets(correctives, clips, bound):
    """Each clip's corrective offsets on the welded garment points."""
    return {clip: welded_offsets(correctives, clip, bound) for clip in clips}


def build(options):
    document, blob = joins.read_glb(options.made)
    old_document, old_blob = joins.read_glb(options.old)
    rig, base = np.load(options.rig), np.load(options.base)
    names = skin_names(document)
    bind = bind_of(document, blob)
    surfaces = surfaces_of(document, blob, NODE)
    base_points = base[f"{options.base_body}_points"]
    garments = [surface for surface in surfaces if role_of(document, surface) == pokes.GARMENT]
    welded = garment_bind(garments, base[f"{options.labels}_points"], base_points, base["faces"], base["weights"],
                          names, bind, not options.no_cut, hard_points(document, surfaces, names),
                          np.asarray(rig["parents"]))
    correctives = np.load(options.correctives) if options.correctives else None
    clips = [animation["name"] for animation in document["animations"]]
    welded_moves = clip_offsets(correctives, clips, welded["bound"]) if correctives is not None else None
    out, cut_faces, closings = [], 0, 0
    for surface, start in zip(garments, welded["starts"]):
        new, removed, middles = rebound(surface, welded, start)
        if welded_moves is not None:
            new.offsets = {clip: rebound_offsets(moves, welded, start, surface) for clip, moves in welded_moves.items()}
        out.append(new)
        cut_faces, closings = cut_faces + removed, closings + middles
    kept = [surface for surface in surfaces
            if role_of(document, surface) != pokes.GARMENT and name_of(document, surface) != "skin_head"]
    bands_rebound(document, kept, out, np.asarray(rig["parents"]))
    old_head = old_surfaces(old_document, old_blob, names, bind)
    hair_record = hair_on_old_head(document, surfaces, old_head, bind, names)
    line, centre = made_collar(document, surfaces, bind, names)
    picture = picture_of(old_document, old_blob, old_head["skin_head"].material)
    old_head["skin_head"], head_record = new_head(old_head["skin_head"], picture, rig, base["weights"], names, line,
                                                  centre)
    drawn = out + kept + [old_head[name] for name in OLD_HEAD]
    if correctives is not None:
        bands_follow_cloth(drawn, out, clips)
    shapes, clip_weights, energy = (corrective_shapes(drawn, clips, options.shapes) if correctives is not None
                                    else (None, None, None))
    written(options.out, document, blob, old_document, old_blob, old_head, drawn, shapes, clip_weights)
    return {"out": str(options.out), "base": options.base_body, "labels": options.labels,
            "web_edges": welded["web_edges"],
            "cut_triangles": cut_faces, "closings": closings, "regions": {
                region: int((welded["regions"] == number).sum()) for number, region in enumerate(route_bind.REGIONS)},
            "head": head_record, "hair": hair_record, "corrective_shapes": None if shapes is None else len(shapes[0]),
            "corrective_energy_kept": None if energy is None else round(energy, 4)}


def rebound_offsets(moves, welded, start, surface):
    """One garment's share of a clip's welded offsets, its closing middles appended (frames, points, 3)."""
    numbers = welded["numbers"][start:start + len(surface.points)]
    cut = route_bind.web_faces(numbers[surface.faces], welded["web"])
    _, middles = route_bind.closed(surface.faces, welded["regions"][numbers], cut, len(surface.points))
    moved = moves[:, numbers].transpose(1, 0, 2)
    return route_bind.with_middles(moved, middles).transpose(1, 0, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for name in ("made", "rig", "base", "old", "out"):
        parser.add_argument(name, type=pathlib.Path)
    parser.add_argument("--correctives", type=pathlib.Path)
    parser.add_argument("--base", dest="base_body", choices=("under", "shell"), default="under")
    parser.add_argument("--labels", choices=("under", "shell"), default="under",
                        help="the base whose nearest point gives each look point its limb")
    parser.add_argument("--no-cut", action="store_true")
    parser.add_argument("--shapes", type=int, default=SHAPES)
    options = parser.parse_args()
    record = build(options)
    options.out.with_suffix(".json").write_text(json.dumps(record, indent=1))
    print(f"route build: {options.out} (web edges {record['web_edges']}, cut {record['cut_triangles']}, "
          f"closings {record['closings']}, head cut {record['head']['cut_m']} m)")


if __name__ == "__main__":
    main()
