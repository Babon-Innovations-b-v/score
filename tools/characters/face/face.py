"""A kept person's face made and drawn close up (#226): the SOMA body's own MHR face as the base, ICT-FaceKit's face
fitted onto its head and joined into its skin, MHR's 72 expressions as the controls of both, every finish a score_lib
surface.

    python face.py <body.npz> <out folder>

`body.npz` is `body_face.py`'s (the motion environment's step). Writes `<out>/face.npz` (the pieces `blender_face.py`
draws) and draws the shots (`SHOTS`) on this PC's card through the card queue into `<out>/stills/`.
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from matplotlib.path import Path
from scipy.spatial import cKDTree

import expressions
import fit
import ict
import strands

REPO = pathlib.Path(__file__).resolve().parents[3]
# Each piece's score_lib surfaces (its finishes); a piece of more than one says which triangle wears which.
SURFACES = {"skin": ["surface/face_skin_light"], "mouth": ["surface/face_mouth_inside"],
            "teeth": ["surface/simready_m_opaque_ceramic_glossy_white_a01_ab8f1883"],
            "eyes": ["surface/face_sclera", "surface/face_iris_brown", "surface/face_pupil"],
            "cornea": ["surface/face_cornea", "surface/face_eye_film"],
            "lashes": ["surface/face_lash_dark"], "brows": ["surface/face_brow_brown"],
            "tears": ["surface/face_tear_film"]}
# The model's pieces drawn in each piece of the face besides the skin's own (fit.skin_triangles: the face and the
# ears' backs); the eye blend and occlusion meshes are shading helpers for ICT's own renderer, not surfaces, and are
# left out.
MODEL_PIECES = {"skin": ("eye_socket_left", "eye_socket_right"), "mouth": ("mouth_socket", "gums_and_tongue"),
                "teeth": ("teeth",), "eyes": ("eyeball_left", "eyeball_right"),
                "tears": ("lacrimal_left", "lacrimal_right")}
# The eyeball's UV runs out from its front (0.5, 0.5) in rings; read off ICT's eyeball, a ring 0.125 out is 11.7 mm
# across (an iris) and one 0.048 out 3.5 mm (a pupil).
IRIS_UV = 0.125
PUPIL_UV = 0.048
# The cornea (Gullstrand's schematic eye): its front a sphere of 7.7 mm radius on an eye of about 12 mm, so a dome
# CORNEA_OF_EYE of the eye's radius rising over the iris and meeting the eye at its edge (the limbus); the rest of the
# eye's front under a tear film TEAR_FILM_M thick. The shell covers the eye out to EYE_FRONT_UV, past what the lids show;
# its triangles past LIMBUS_UV wear the tear film's finish (glossy, bending no light), the rest the cornea's glass.
CORNEA_OF_EYE = 7.7 / 12.0
TEAR_FILM_M = 0.0001
EYE_FRONT_UV = 0.3
LIMBUS_UV = 0.135
# The skin's tones by region, read on ICT's neutral face (centimetres, y up, the face along +z) round its 68 landmarks
# (iBUG order): each a centre (a landmark or a mean of them, then moved), a spread (x, y) and a strength. Where they
# sit is anatomy; their colours, gloss and depths are the skin's library record's (`regions`), not here. The channels
# (TONES, in order): the redder flush on the cheeks' apples, the nose's tip and wings, the chin and the ears; the bluish
# thin skin in the hollow under the lower lids; the lips inside their outer line; the lids' own darker, browner skin
# (the upper lid to its crease and the inner corner by the nose's root); the T-zone's oily sheen (the forehead's middle,
# the nose's ridge and tip, the chin); the relief's change on the face from the scanned forehead's (signed: the nose's
# and the cheeks' larger pores deeper, the lids', the under-eyes' and the lips' finer skin shallower); the wet skin
# (each lid's waterline within WET_CM of its eyeball and the conjunctiva lining the socket, the caruncle at the inner
# corner); and the face itself (1 on the face's skin, 0 on the body's, whose relief is the record's `body` share).
TONES = ("flush", "thin", "lips", "lids", "sheen", "relief", "wet", "face")
FLUSH = [((40, 41), (0.3, -2.2), (1.6, 1.4), 0.8), ((46, 47), (-0.3, -2.2), (1.6, 1.4), 0.8),
         ((30,), (0.0, 0.0), (0.9, 0.8), 0.9), ((31,), (0.0, 0.0), (0.6, 0.6), 0.8), ((35,), (0.0, 0.0), (0.6, 0.6), 0.8),
         ((8,), (0.0, 0.5), (1.4, 1.0), 0.35)]
UNDER_EYE = [((39, 40, 41), (0.0, -0.55), (1.0, 0.4), 0.9), ((42, 46, 47), (0.0, -0.55), (1.0, 0.4), 0.9)]
LIDS = [((37, 38), (0.0, 0.45), (1.3, 0.5), 0.9), ((43, 44), (0.0, 0.45), (1.3, 0.5), 0.9),
        ((39,), (-0.35, 0.35), (0.45, 0.45), 0.7), ((42,), (0.35, 0.35), (0.45, 0.45), 0.7)]
SHEEN = [((19, 24), (0.0, 2.6), (2.4, 1.4), 0.9), ((27, 28), (0.0, 0.0), (0.55, 1.2), 0.8),
         ((29, 30), (0.0, 0.0), (0.6, 0.9), 1.0), ((8,), (0.0, 0.9), (1.1, 0.7), 0.6)]
COARSE = [((30, 31, 35), (0.0, 0.2), (1.2, 1.1), 0.6), ((40, 41), (0.4, -2.4), (1.8, 1.5), 0.2),
          ((46, 47), (-0.4, -2.4), (1.8, 1.5), 0.2)]
FINE = [((37, 38, 40, 41), (0.0, 0.0), (1.4, 1.0), 0.7), ((43, 44, 46, 47), (0.0, 0.0), (1.4, 1.0), 0.7)]
LIPS_FINE = 0.85  # the lips' relief taken down by this share inside their line
CARUNCLE = [((39,), (0.12, 0.0), (0.16, 0.14), 1.0), ((42,), (-0.12, 0.0), (0.16, 0.14), 1.0)]
WET_CM = (0.1, 0.2)  # a lid's skin this near its eyeball is wet, fading to dry by the second
# An ear's flush: the skin within EAR_REACH_CM of its helix's rim and back (fit.ears, fit.ear_backs), fading out over
# EAR_FADE_CM, and none past EAR_FADE_CM over the rim's top. Read as all the side of the head over the jaw's angle, the
# flush reached up the temples onto the scalp (#227) and showed as a pink patch over each ear (photoreal round 2).
EAR_REACH_CM = 1.5
EAR_FADE_CM = 0.5
LIP_EDGE_CM = 0.06  # the lips' tone fades in over this inside their outer line: a defined vermilion border
SHOTS = [{"name": "neutral", "weights": {}},
         {"name": "smile", "weights": {"lipCornerPuller_L": 1.0, "lipCornerPuller_R": 1.0, "cheekRaiser_L": 0.6,
                                       "cheekRaiser_R": 0.6}},
         {"name": "blink", "weights": {"eyesClosed_L": 1.0, "eyesClosed_R": 1.0}},
         {"name": "jaw_open", "weights": {"jawDrop": 0.8}}]
# The stills' light: the score_lib sky the whole person is photographed under (../whole/__main__.py's SETTING), so a
# face is judged in the light it is seen in (a studio light hid the orange lids and nostrils round 1's sky showed).
SKY = "polyhaven_cloudy_vondelpark"
CARD_GB = 3  # the stills' share of the card (a 26k-point face at 1024 x 1280 holds under 2 GB)
LENS_DISTANCE = 0.75  # metres from the face: a head and neck fill an 85 mm portrait


def ict_offsets(model, laid, matrix):
    """Each MHR control's offsets on every model point through its mapped ICT expressions, in the body's frame."""
    mixed = np.tensordot(matrix, model["expressions"].astype(np.float64), axes=1)  # (72, points, 3)
    return laid["scale"] * mixed @ laid["turn"].T


def body_field(body, points):
    """The body's own 72 MHR offsets at the skin points nearest `points` (barycentric on its triangles)."""
    head = fit.head_mesh(body)
    nearest, _, triangle = trimesh.proximity.closest_point(head, points)
    corners = head.faces[triangle]
    weights = trimesh.triangles.points_to_barycentric(head.points[corners] if hasattr(head, "points")
                                                      else head.vertices[corners], nearest)
    return np.einsum("pc,kpcd->kpd", weights, body["offsets"][:, corners, :].astype(np.float64))


def face_offsets(body, model, laid, matrix):
    """Every model point's offsets per control: on the face, the ICT expressions blended into the body's own offsets
    by the face's share of the body (the body's alone for a control ICT has no expression for); elsewhere ICT's."""
    offsets = ict_offsets(model, laid, matrix)
    skin = np.unique(fit.skin_triangles(model))
    under = body_field(body, laid["points"][skin])
    mapped = matrix.any(axis=1)[:, None, None]
    share = laid["share"][None, skin, None]
    offsets[:, skin] = np.where(mapped, share * under + (1.0 - share) * offsets[:, skin], under)
    return offsets


def model_triangles(model, names):
    """The model's triangles of the named pieces, and their rows in the model's triangle list."""
    rows = np.concatenate([np.flatnonzero(np.isin(model["triangles"], np.arange(ict.PIECES[name][0],
                                                                                 ict.PIECES[name][1] + 1)).all(axis=1))
                           for name in names])
    return model["triangles"][rows], rows


def compact(points, triangles, shapes):
    """Only the points the triangles use, renumbered."""
    used, renumbered = np.unique(triangles, return_inverse=True)
    return points[used], renumbered.reshape(triangles.shape), shapes[:, used]


def blobs(points, landmarks, rows):
    """The largest of the Gaussian blobs (`rows` as FLUSH) at each point, by its (x, y) on ICT's neutral face."""
    found = np.zeros(len(points))
    for marks, (move_x, move_y), (spread_x, spread_y), strength in rows:
        centre = landmarks[list(marks)].mean(axis=0)[:2] + [move_x, move_y]
        across = ((points[:, 0] - centre[0]) / spread_x) ** 2 + ((points[:, 1] - centre[1]) / spread_y) ** 2
        found = np.maximum(found, strength * np.exp(-0.5 * across))
    return found


def lips(points, landmarks):
    """1 inside the lips' outer line (landmarks 48 to 59) on the face's front, fading in over LIP_EDGE_CM."""
    line = landmarks[48:60, :2]
    inside = Path(line).contains_points(points[:, :2]) & (points[:, 2] > landmarks[48:60, 2].min() - 1.0)
    starts, ends = line, np.roll(line, -1, axis=0)
    along = ends - starts
    share = np.clip(np.einsum("psd,sd->ps", points[:, None, :2] - starts[None], along) / (along ** 2).sum(axis=1), 0, 1)
    edge = np.linalg.norm(points[:, None, :2] - (starts[None] + share[..., None] * along[None]), axis=2).min(axis=1)
    return inside * np.clip(edge / LIP_EDGE_CM, 0.0, 1.0)


def eyeball_gap(model, points):
    """Each point's distance (cm) off the nearer eyeball's surface on ICT's neutral face (each eyeball a sphere: its
    points' mean and median reach)."""
    gaps = []
    for eye in ("left", "right"):
        first, last = ict.PIECES[f"eyeball_{eye}"]
        ball = model["neutral"][first:last + 1]
        centre = ball.mean(axis=0)
        gaps.append(np.linalg.norm(points - centre, axis=1) - np.median(np.linalg.norm(ball - centre, axis=1)))
    return np.min(gaps, axis=0)


def ear_share(model, points):
    """Each point's share of an ear's flush (EAR_REACH_CM of its rim, under its top), on ICT's neutral face (cm)."""
    rims = np.concatenate([np.concatenate([rim, np.asarray(back)])
                           for (rim, _), back in zip(fit.ears(model), fit.ear_backs(model))])
    near = cKDTree(model["neutral"][rims]).query(points)[0]
    top = model["neutral"][rims][:, 1].max()
    return (np.clip((EAR_REACH_CM + EAR_FADE_CM - near) / EAR_FADE_CM, 0.0, 1.0)
            * np.clip((top + EAR_FADE_CM - points[:, 1]) / EAR_FADE_CM, 0.0, 1.0))


def tones(model):
    """Each model point's skin tones (TONES, each 0 to 1 but the signed relief) from its place on ICT's neutral face;
    zero off the face's skin. The eye sockets' lining is wet and smooth."""
    neutral = model["neutral"]
    landmarks = neutral[model["landmarks"]]
    found = np.zeros((len(neutral), len(TONES)))
    skin = np.unique(fit.skin_triangles(model))
    points = neutral[skin]
    ear = ear_share(model, points)
    lip = lips(points, landmarks)
    wet = np.clip((WET_CM[1] - eyeball_gap(model, points)) / (WET_CM[1] - WET_CM[0]), 0.0, 1.0)
    found[skin, TONES.index("flush")] = np.maximum(blobs(points, landmarks, FLUSH), 0.7 * ear)
    found[skin, TONES.index("thin")] = blobs(points, landmarks, UNDER_EYE)
    found[skin, TONES.index("lips")] = lip
    found[skin, TONES.index("lids")] = blobs(points, landmarks, LIDS) * (1.0 - wet)
    found[skin, TONES.index("sheen")] = blobs(points, landmarks, SHEEN)
    found[skin, TONES.index("relief")] = (blobs(points, landmarks, COARSE) - blobs(points, landmarks, FINE)
                                         - LIPS_FINE * lip - wet)
    found[skin, TONES.index("wet")] = np.maximum(wet, blobs(points, landmarks, CARUNCLE))
    found[skin, TONES.index("face")] = 1.0
    sockets = np.concatenate([np.arange(ict.PIECES[name][0], ict.PIECES[name][1] + 1) for name in MODEL_PIECES["skin"]])
    found[sockets, TONES.index("wet")] = 1.0
    found[sockets, TONES.index("face")] = 1.0
    found[sockets, TONES.index("relief")] = -1.0
    return found


def corner_values(triangles, corners, count):
    """Per-corner values (triangles x 3 x k) as per-point ones, each point the mean of its corners."""
    total = np.zeros((count, corners.shape[-1]))
    np.add.at(total, triangles.reshape(-1), corners.reshape(-1, corners.shape[-1]))
    return total / np.maximum(np.bincount(triangles.reshape(-1), minlength=count), 1)[:, None]


def dome(direction, axis, radius, limbus):
    """How far from the eye's centre its outer surface lies along each unit `direction`: the cornea's sphere
    (CORNEA_OF_EYE of the eye's `radius`, meeting the eye where it is `limbus` across from the axis) over the iris, the
    eye's own sphere and its tear film elsewhere."""
    cornea = CORNEA_OF_EYE * radius
    behind = np.sqrt(radius ** 2 - limbus ** 2) - np.sqrt(cornea ** 2 - limbus ** 2)
    cosine = np.clip(direction @ axis, -1.0, 1.0)
    reach = behind * cosine + np.sqrt(np.clip(cornea ** 2 - behind ** 2 * (1.0 - cosine ** 2), 0.0, None))
    return np.maximum(radius + TEAR_FILM_M, reach)


def cornea(eyes):
    """The clear shell over each eye's front (out to EYE_FRONT_UV): the cornea's dome over the iris (finish 0) and a
    tear film over the white (finish 1, past LIMBUS_UV), each point over its eye's point and moving with it; a piece as
    the eyes are."""
    out = np.linalg.norm(corner_values(eyes["triangles"], eyes["uv"], len(eyes["points"])) - 0.5, axis=1)
    points = eyes["points"].copy()
    side = points[:, 0] > np.median(points[:, 0])
    for one in (side, ~side):
        centre = eyes["points"][one].mean(axis=0)
        offset = eyes["points"][one] - centre
        axis = offset[out[one] < PUPIL_UV / 2].mean(axis=0)
        axis /= np.linalg.norm(axis)
        radius = float(np.median(np.linalg.norm(offset[(out[one] > IRIS_UV * 1.3) & (out[one] < 0.25)], axis=1)))
        ring = offset[np.abs(out[one] - IRIS_UV) < 0.01]
        limbus = float(np.median(np.linalg.norm(ring - np.outer(ring @ axis, axis), axis=1)))
        direction = offset / np.linalg.norm(offset, axis=1, keepdims=True)
        points[one] = centre + direction * dome(direction, axis, radius, limbus)[:, None]
    front = (out[eyes["triangles"]] < EYE_FRONT_UV).all(axis=1)
    triangles = eyes["triangles"][front]
    used, renumbered = np.unique(triangles, return_inverse=True)
    return {"points": points[used], "triangles": renumbered.reshape(triangles.shape),
            "finish": (out[triangles].mean(axis=1) > LIMBUS_UV).astype(np.int64), "shapes": eyes["shapes"][:, used]}


def eye_finish(uv):
    """Each eye triangle's finish from its UV corners: 0 the white, 1 the iris, 2 the pupil, by its distance out
    from the eyeball's front in UV."""
    out = np.linalg.norm(uv.mean(axis=1) - 0.5, axis=1)
    return np.where(out < PUPIL_UV, 2, np.where(out < IRIS_UV, 1, 0))


def pieces(body, model, laid, matrix):
    """The face's pieces: {name: points, triangles, finish, shapes, uv?} with the skin the body joined to the face, and
    the brows and lashes as strands {counts, points, radius, shapes} (the brows' measures with them)."""
    offsets = face_offsets(body, model, laid, matrix)
    centre = fit.head_centre(body)
    made = {}
    face_triangles = np.vstack([fit.skin_triangles(model), model_triangles(model, MODEL_PIECES["skin"])[0]])
    joined_points = np.vstack([body["points"], laid["points"]])
    joined_shapes = np.concatenate([body["offsets"].astype(np.float64), offsets], axis=1)
    skin = fit.joined_skin(body["points"], laid["kept"], laid["strip"], laid["points"], face_triangles, centre)
    points, triangles, shapes = compact(joined_points, skin, joined_shapes)
    joined_tones = np.vstack([np.zeros((len(body["points"]), len(TONES))), tones(model)])
    made["skin"] = {"points": points, "triangles": triangles, "finish": np.zeros(len(triangles), np.int64),
                    "shapes": shapes, "tones": joined_tones[np.unique(skin)]}
    brow_skin = trimesh.Trimesh(laid["points"], fit.outward(fit.piece_triangles(model, "face"), laid["points"], centre),
                                process=False)
    for name, grown in (("brows", strands.brows(model, laid["points"], offsets, brow_skin)),
                        ("lashes", strands.lashes(model, laid["points"], offsets))):
        counts, points, radius, shapes = grown
        made[name] = {"counts": counts, "points": points, "radius": radius, "shapes": shapes}
    made["brows"]["measures"] = strands.checked(made["brows"]["counts"], made["brows"]["points"], brow_skin)
    for name in ("mouth", "teeth", "eyes", "tears"):
        triangles, rows = model_triangles(model, MODEL_PIECES[name])
        piece = {"finish": np.zeros(len(triangles), np.int64)}
        piece["uv"] = model["uvs"][model["corners"][rows]]
        if name == "eyes":
            piece["finish"] = eye_finish(piece["uv"])
        piece["points"], piece["triangles"], piece["shapes"] = compact(laid["points"], triangles, offsets)
        made[name] = piece
    made["cornea"] = cornea(made["eyes"])
    return made


def face_file(made, body, out):
    """Write the pieces, their surfaces, the shots and the camera's aim as `blender_face.py` reads them."""
    eyes = (body["joint_LeftEye"] + body["joint_RightEye"]) / 2.0
    arrays = {"pieces": np.array(list(made)), "shape_names": np.array(expressions.MHR_EXPRESSIONS),
              "shots": np.array(json.dumps(SHOTS)), "aim": eyes + [0.0, -0.04, 0.0], "sky": np.array(SKY),
              "eye_distance": np.array(LENS_DISTANCE)}
    for name, piece in made.items():
        arrays[f"{name}.surfaces"] = np.array([address.split("/", 1)[1] for address in SURFACES[name]])
        for field in ("points", "triangles", "finish", "uv", "counts", "radius", "tones"):
            if field in piece:
                arrays[f"{name}.{field}"] = piece[field]
        arrays[f"{name}.shapes"] = piece["shapes"].astype(np.float32)
    np.savez_compressed(out, **arrays)
    return out


def fetched_surfaces(folder):
    """Every surface the face wears copied from score_lib under `folder`'s assets (place_build's fetch)."""
    sys.path.insert(0, str(REPO))
    from score.stages import place_build
    for address in sorted({address for addresses in SURFACES.values() for address in addresses}) + [f"light/{SKY}"]:
        place_build.fetch(folder, address)
    return folder / "assets"


def drawn(face_path, library, stills):
    """The shots drawn by Blender on this PC's card through the card queue; raises on a failed draw."""
    import subprocess
    sys.path.insert(0, str(REPO))
    from score.stages.place_build import render
    command = render.queued("face-stills", pathlib.Path(__file__).with_name("blender_face.py"),
                            [str(face_path), str(library), str(stills)], seconds=3600, card_gb=CARD_GB)
    log = stills.parent / "blender.log"
    with log.open("w") as out:
        done = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, cwd=REPO)
    if done.returncode:
        raise RuntimeError(f"the stills failed (exit {done.returncode}): {log}")
    return sorted(stills.glob("*.png"))


def main(body_path, out):
    """Fit, join, write and draw the face of the body at `body_path` into `out`."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    body = dict(np.load(body_path))
    model = ict.load()
    laid = fit.fitted(body, model)
    made = pieces(body, model, laid, expressions.mapping(model["expression_names"]))
    face_path = face_file(made, body, out / "face.npz")
    stills = drawn(face_path, fetched_surfaces(out), out / "stills")
    (out / "measures.json").write_text(json.dumps({"ears_mm": laid["ears"], "neck": laid["neck"],
                                                   "seam_turn_most_degrees": laid["seam_turn_most"],
                                                   "brows": made["brows"]["measures"],
                                                   "lashes": int(len(made["lashes"]["counts"]))}, indent=1))
    print(f"face: scale {laid['scale']:.5f}, {len(made['skin']['triangles'])} skin triangles, ears {laid['ears']}, "
          f"brows {made['brows']['measures']}, {len(stills)} stills -> {out / 'stills'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
