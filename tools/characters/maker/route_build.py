"""The people route on a made body (owner, 2026-10-18, score #10), a free prototype on the PC: the accepted made
body's look and clips rebuilt on the SOMA-X base with the route's four changes, written as a glTF the checks read
(joins.py, pokes.py, route_stretch.py) and Blender renders.

    ~/.farm-factory-props/env/bin/python route_build.py <made body.glb> <made rig.npz> <base.npz> <out.glb>
        [--face made|drawn] [--old <old body.glb>] [--correctives <correctives.npz>] [--base under|shell]
        [--labels under|shell] [--no-cut] [--no-under] [--shapes 24]

- the garments bound by limb on the base, the arm and leg webs cut and closed (route_bind.py), then eased onto the
  hard and skin parts next to them, which take no correctives there (`garment_bind`, `clip_offsets`);
- the head by `--face` (route_head.FACE, the owner's one setting): `made` keeps the made head whole, the face
  Pixal3D made with its face print from the close-up; `drawn` splits it, keeps the made hair, drops the made face and
  lays the old SOMA-X head with its drawn face and eyes (`--old`) on the made skeleton, run down the neck to 2 cm
  under the collar line, its neck a tuck (route_head.py);
- no settled cloth: the made body's per-clip garment shapes (the Newton settle) are dropped, the clothes move with
  the body (the owner's option A);
- SOMA-X's pose correctives (route_base.py correctives) carried onto the garments by their bind places and baked as
  `--shapes` shared morph targets (the main directions of every clip's offsets), keyed per frame in every clip;
- the base body drawn in the suit's cloth under the cut webs (`under_layer`), so the gap where an arm lifts off the
  side shows cloth, not the inside of the suit, only where it lies under the cloth (`--no-under` leaves it out).

Hard parts, hands and hair keep their made weights (one joint each), but a boot's shaft, graded from its foot onto its
shin round the ankle (`shafted`), with the cloth eased onto it. The far body is copied as it is.
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
# A boot's shaft bends (owner, 2026-10-27): ridden wholly by its foot, the astronaut's 17 cm shaft swung forward with
# the sitting clip's 61-degree pointed foot and stretched the trouser cuff over it 12 cm. Footwear rising above its
# ankle is graded from its foot onto its shin like a fan round the ankle joint, by the angle a point stands off the
# shin's line (ankle to knee): wholly the shin within SHAFT_DEGREES, wholly the foot from FOOT_DEGREES, so the sole
# and the foot stay rigid and the bend spreads round the ankle; a point's swing between the two turns grows with its
# distance from the ankle as its share's change per metre shrinks, so every ring takes the same part of the bend
# (graded by height, the shaft's top rings took it and stretched 2.0 times sitting).
SHAFT_FROM = 0.03  # metres over the ankle joint a footwear's top must rise to have a shaft
SHAFT_DEGREES = 5.0
FOOT_DEGREES = 90.0
SHAPES = 24
OLD_HEAD = ("skin_head", "eyes", "irises", "eyebrows")
NODE = "work"
# The body drawn under the cut webs (under_layer): base points this close to a web point's bind place, set this far in.
UNDER_REACH = 0.09
UNDER_INSET = 0.003
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


def body_node(document):
    """The name of a built body's own skinned mesh node, its outfit's (prop_build.py names it for the outfit:
    `made` since one body a look, 2026-10-22; `work` before), not its far body's."""
    found = [node["name"] for node in document["nodes"] if "mesh" in node and "skin" in node
             and node.get("name") != "far"]
    if len(found) != 1:
        raise SystemExit(f"the body has {len(found)} skinned outfit nodes ({found}), not one")
    return found[0]


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


def skin_points(document, surfaces):
    """The skin parts' own points (their tucks left out) and their weights: the made face, bare hands."""
    own = [(surface, surface.tuck_from or len(surface.points)) for surface in surfaces
           if role_of(document, surface) == "skin"]
    count = surfaces[0].weights.shape[1] if surfaces else 0
    return (np.concatenate([np.zeros((0, 3))] + [surface.points[:end] for surface, end in own]),
            np.concatenate([np.zeros((0, count))] + [surface.weights[:end] for surface, end in own]))


def skin_share(points, weights, skin, parents):
    """(the nearest skin point's weights, how far each garment point rides them, points x 1), by prop_build's
    EASE_HOLD and EASE_REACH, only where the point's strongest joint is the skin point's own, its parent or
    grandparent: the made face rides the head while the helmet round it bent with the neck, and went 10 mm through
    it on the bench (astronaut, 2026-10-22)."""
    skin_points, skin_weights = skin
    if not len(skin_points):
        return np.zeros_like(weights), np.zeros((len(points), 1))
    from scipy.spatial import cKDTree
    distance, nearest = cKDTree(skin_points).query(points)
    own = skin_weights[nearest].argmax(1)
    family = np.stack([own, parents[own], np.where(parents[own] >= 0, parents[parents[own]], -1)], 1)
    mine = (family == weights.argmax(1)[:, None]).any(1)
    share = np.clip(1.0 - (distance - prop_build.EASE_HOLD) / (prop_build.EASE_REACH - prop_build.EASE_HOLD), 0, 1)
    return skin_weights[nearest], np.where(mine, share, 0.0)[:, None]


def shaft_tops(document, surfaces, names, bind):
    """{(foot, shin): the top of the footwear riding that foot}, for each foot whose footwear (a hard part riding it)
    rises over its ankle joint by more than SHAFT_FROM: the shafts that bend."""
    tops = {}
    for side in ("Left", "Right"):
        foot, shin = names.index(f"{side}Foot"), names.index(f"{side}Shin")
        heights = [surface.points[:surface.tuck_from or len(surface.points), 1].max() for surface in surfaces
                   if role_of(document, surface) == "hard" and surface.weights.sum(0).argmax() == foot]
        if heights and max(heights) > bind[foot, 1, 3] + SHAFT_FROM:
            tops[(foot, shin)] = float(max(heights))
    return tops


def shafted(points, weights, bind, tops):
    """Weights with each point's foot share graded onto its shin by the angle it stands off the shin's line at the
    ankle joint (SHAFT_DEGREES, FOOT_DEGREES), for each foot whose footwear has a shaft (`tops`, shaft_tops)."""
    found = weights.copy()
    for foot, shin in tops:
        ankle = bind[foot, :3, 3]
        line = bind[shin, :3, 3] - ankle
        away = points - ankle
        cosine = away @ line / np.maximum(np.linalg.norm(away, axis=1) * np.linalg.norm(line), 1e-9)
        degrees = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        moved = found[:, foot] * np.clip((FOOT_DEGREES - degrees) / (FOOT_DEGREES - SHAFT_DEGREES), 0.0, 1.0)
        found[:, foot] -= moved
        found[:, shin] += moved
    return found


def garment_bind(garments, label_points, base_points, base_faces, base_weights, names, bind, cut, hard, skin,
                 parents, tops):
    """The welded garments' regions (by the nearest of `label_points`), bind, weights and web edges
    (route_bind.py); the weights then eased onto the hard parts next to them (prop_build.hard_share: a trouser
    leg goes with the boot it covers, or the boot's tuck shows through it, 19 mm on the player standing) and onto the
    skin parts next to them (skin_share), a boot's graded up its shaft as the boot is (`tops`, shafted); `eased`, how
    far each point rides a hard or skin part."""
    numbers, places, edges, starts = welding(garments)
    regions = route_bind.point_regions(places, edges, label_points, route_bind.base_regions(base_weights, names))
    bound = route_bind.bound_by_region(places, regions, base_points, base_faces, base_weights, names)
    web = np.zeros(len(edges), bool)
    if cut:
        web = route_bind.web_edges(places, edges, regions, bound.places)
        web |= route_bind.underarm_edges(places, edges, regions, shoulder_heights(bind, names))
    weights = route_bind.smoothed(bound.carried(base_weights), edges[~web])
    weights = route_bind.kept_to_limb(weights, regions, names)
    target, hard_eased = prop_build.hard_share(places, weights, *hard, list(names), parents)
    weights = shafted(places, weights * (1 - hard_eased) + target * hard_eased, bind, tops)
    target, skin_eased = skin_share(places, weights, skin, parents)
    weights = weights * (1 - skin_eased) + target * skin_eased
    return {"numbers": numbers, "starts": starts, "regions": regions, "bound": bound, "weights": weights,
            "eased": np.maximum(hard_eased, skin_eased)[:, 0],
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
    for surface in surfaces_of(old_document, old_blob, body_node(old_document)):
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
    if old_head:  # the drawn face's neck is a tuck; the made face keeps its own record
        materials[old_head["skin_head"].material]["extras"]["tuck_from"] = old_head["skin_head"].tuck_from
    made = body_node(document)
    work_node = next(number for number, node in enumerate(document["nodes"]) if node.get("name") == made)
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
            node["mesh"] = 1 if node.get("name") == made else 0
    nodes[work_node]["name"] = NODE  # the routed body's node, as skel_usd's worn names and the route's shots read it
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


def clip_offsets(correctives, clips, welded):
    """Each clip's corrective offsets on the welded garment points, none where a point rides a hard or skin part
    (`eased`): the base's correctives moved the trouser hem riding the boot into the boot, 4.5 to 5 mm deep walking
    and sitting (astronaut, 2026-10-22)."""
    kept = (1.0 - welded["eased"])[None, :, None]
    return {clip: welded_offsets(correctives, clip, welded["bound"]) * kept for clip in clips}


def kept_surfaces(document, surfaces, face):
    """The made surfaces carried as they are: all but the garments, and but the made face where the drawn head
    takes its place (route_head.FACE)."""
    dropped = ("skin_head",) if face == "drawn" else ()
    return [surface for surface in surfaces
            if role_of(document, surface) != pokes.GARMENT and name_of(document, surface) not in dropped]


def drawn_head(options, document, surfaces, rig, base, names, bind):
    """The old body's drawn head laid on the made skeleton (`--face drawn`): ({name: Surface}, head record, hair
    record, old document, old blob)."""
    if options.old is None:
        raise SystemExit("--face drawn lays the old body's drawn head: give its file with --old")
    old_document, old_blob = joins.read_glb(options.old)
    old_head = old_surfaces(old_document, old_blob, names, bind)
    hair_record = hair_on_old_head(document, surfaces, old_head, bind, names)
    line, centre = made_collar(document, surfaces, bind, names)
    picture = picture_of(old_document, old_blob, old_head["skin_head"].material)
    old_head["skin_head"], head_record = new_head(old_head["skin_head"], picture, rig, base["weights"], names, line,
                                                  centre)
    return old_head, {"face": "drawn", **head_record}, hair_record, old_document, old_blob


def build(options):
    document, blob = joins.read_glb(options.made)
    rig, base = np.load(options.rig), np.load(options.base)
    names = skin_names(document)
    bind = bind_of(document, blob)
    surfaces = surfaces_of(document, blob, body_node(document))
    base_points = base[f"{options.base_body}_points"]
    garments = [surface for surface in surfaces if role_of(document, surface) == pokes.GARMENT]
    tops = shaft_tops(document, surfaces, names, bind)
    welded = garment_bind(garments, base[f"{options.labels}_points"], base_points, base["faces"], base["weights"],
                          names, bind, not options.no_cut, hard_points(document, surfaces, names),
                          skin_points(document, surfaces), np.asarray(rig["parents"]), tops)
    correctives = np.load(options.correctives) if options.correctives else None
    clips = [animation["name"] for animation in document["animations"]]
    welded_moves = clip_offsets(correctives, clips, welded) if correctives is not None else None
    out, cut_faces, closings = [], 0, 0
    for surface, start in zip(garments, welded["starts"]):
        new, removed, middles = rebound(surface, welded, start)
        if welded_moves is not None:
            new.offsets = {clip: rebound_offsets(moves, welded, start, surface) for clip, moves in welded_moves.items()}
        out.append(new)
        cut_faces, closings = cut_faces + removed, closings + middles
    kept = kept_surfaces(document, surfaces, options.face)
    for surface in kept:
        if role_of(document, surface) == "hard":
            surface.weights = shafted(surface.points, surface.weights, bind, tops)
    bands_rebound(document, kept, out, np.asarray(rig["parents"]))
    old_head, head_record, hair_record, old_document, old_blob = (
        drawn_head(options, document, surfaces, rig, base, names, bind) if options.face == "drawn"
        else ({}, {"face": "made"}, None, None, None))
    layer = None if options.no_under else under_layer(garments, welded, base_points, base["faces"], base["weights"],
                                                      correctives, clips)
    drawn = out + ([] if layer is None else [layer]) + kept + [old_head[name] for name in OLD_HEAD if old_head]
    if correctives is not None:
        bands_follow_cloth(drawn, out, clips)
    shapes, clip_weights, energy = (corrective_shapes(drawn, clips, options.shapes) if correctives is not None
                                    else (None, None, None))
    written(options.out, document, blob, old_document, old_blob, old_head, drawn, shapes, clip_weights)
    return {"out": str(options.out), "base": options.base_body, "labels": options.labels,
            "web_edges": welded["web_edges"],
            "cut_triangles": cut_faces, "closings": closings, "regions": {
                region: int((welded["regions"] == number).sum()) for number, region in enumerate(route_bind.REGIONS)},
            "under_layer": None if layer is None else {"points": len(layer.points), "triangles": len(layer.faces)},
            "head": head_record, "hair": hair_record, "corrective_shapes": None if shapes is None else len(shapes[0]),
            "corrective_energy_kept": None if energy is None else round(energy, 4)}


def under_layer(garments, welded, base_points, base_faces, base_weights, correctives, clips):
    """The body under the cut webs, drawn in the cloth of the garment that lost the most there: the base's triangles
    within UNDER_REACH of where a web point binds, UNDER_INSET inside the base, on the base's weights and pose
    correctives. Where the arm lifts off the side the cut leaves a gap; through it the inside of the suit's far side
    showed black (sitting, reaching, lifting on the player, 2026-10-18); this closes it with cloth colour. Only
    triangles lying at least UNDER_INSET under the cloth are drawn: where the base stood out of a slim suit it showed
    through it at rest, white patches on the astronaut's brown chest and hips (2026-10-22). None when nothing was
    cut."""
    web_points = np.unique(np.array(sorted(welded["web"]), int).ravel()) if welded["web"] else np.zeros(0, int)
    if not len(web_points):
        return None
    from scipy.spatial import cKDTree
    near = cKDTree(welded["bound"].places[web_points]).query(base_points, distance_upper_bound=UNDER_REACH)[0]
    inset = base_points - UNDER_INSET * normals_of(base_points, base_faces)
    drawn = np.isfinite(near) & (under_cloth(inset, garments) >= UNDER_INSET)
    faces = base_faces[drawn[base_faces].all(1)]
    if not len(faces):
        return None
    used = np.unique(faces)
    renumber = np.full(len(base_points), -1)
    renumber[used] = np.arange(len(used))
    points = inset[used]
    layer = Surface(cloth_of_web(garments, welded), points, None, base_weights[used], renumber[faces])
    if correctives is not None:
        layer.offsets = {clip: correctives[f"clip_{clip}"].astype(np.float64)[:, used] for clip in clips}
    return layer


def under_cloth(points, garments):
    """How far each point lies under the garments (negative: outside them), along its nearest garment point's
    normal."""
    from scipy.spatial import cKDTree
    starts = np.cumsum([0] + [len(surface.points) for surface in garments])
    cloth = np.concatenate([surface.points for surface in garments])
    normals = normals_of(cloth, np.concatenate([surface.faces + start for surface, start in zip(garments, starts)]))
    _, nearest = cKDTree(cloth).query(points)
    return np.einsum("ij,ij->i", cloth[nearest] - points, normals[nearest])


def cloth_of_web(garments, welded):
    """The material of the garment with the most web points (the suit's own cloth at the armpits and crotch)."""
    counts = [len({int(number) for number in welded["numbers"][start:start + len(surface.points)]}
                  & {point for pair in welded["web"] for point in pair}) for surface, start in
              zip(garments, welded["starts"])]
    return garments[int(np.argmax(counts))].material


def rebound_offsets(moves, welded, start, surface):
    """One garment's share of a clip's welded offsets, its closing middles appended (frames, points, 3)."""
    numbers = welded["numbers"][start:start + len(surface.points)]
    cut = route_bind.web_faces(numbers[surface.faces], welded["web"])
    _, middles = route_bind.closed(surface.faces, welded["regions"][numbers], cut, len(surface.points))
    moved = moves[:, numbers].transpose(1, 0, 2)
    return route_bind.with_middles(moved, middles).transpose(1, 0, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for name in ("made", "rig", "base", "out"):
        parser.add_argument(name, type=pathlib.Path)
    parser.add_argument("--face", choices=route_head.FACES, default=route_head.FACE,
                        help="made: keep the face Pixal3D made with its print; drawn: the old body's drawn head")
    parser.add_argument("--old", type=pathlib.Path, help="the old body whose drawn head --face drawn lays")
    parser.add_argument("--correctives", type=pathlib.Path)
    parser.add_argument("--base", dest="base_body", choices=("under", "shell"), default="under")
    parser.add_argument("--labels", choices=("under", "shell"), default="under",
                        help="the base whose nearest point gives each look point its limb")
    parser.add_argument("--no-cut", action="store_true")
    parser.add_argument("--no-under", action="store_true", help="leave the body under the cut webs undrawn")
    parser.add_argument("--shapes", type=int, default=SHAPES)
    options = parser.parse_args()
    record = build(options)
    options.out.with_suffix(".json").write_text(json.dumps(record, indent=1))
    print(f"route build: {options.out} (web edges {record['web_edges']}, cut {record['cut_triangles']}, "
          f"closings {record['closings']}, face {record['head']['face']})")


if __name__ == "__main__":
    main()
