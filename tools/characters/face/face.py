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

import expressions
import fit
import ict

REPO = pathlib.Path(__file__).resolve().parents[3]
# Each piece's score_lib surfaces (its finishes); a piece of more than one says which triangle wears which.
SURFACES = {"skin": ["surface/face_skin_light"], "mouth": ["surface/face_mouth_inside"],
            "teeth": ["surface/simready_m_opaque_ceramic_glossy_white_a01_ab8f1883"],
            "eyes": ["surface/simready_m_opaque_ceramic_glossy_white_a01_ab8f1883", "surface/face_iris_brown",
                     "surface/face_pupil"],
            "lashes": ["surface/face_lash_dark"], "tears": ["surface/face_tear_film"]}
# The model's pieces drawn in each piece of the face (the eye blend and occlusion meshes are shading helpers for
# ICT's own renderer, not surfaces, and are left out).
MODEL_PIECES = {"skin": ("face", "eye_socket_left", "eye_socket_right"), "mouth": ("mouth_socket", "gums_and_tongue"),
                "teeth": ("teeth",), "eyes": ("eyeball_left", "eyeball_right"),
                "lashes": ("lashes_left", "lashes_right"), "tears": ("lacrimal_left", "lacrimal_right")}
# The eyeball's UV runs out from its front (0.5, 0.5) in rings; read off ICT's eyeball, a ring 0.125 out is 11.7 mm
# across (an iris) and one 0.048 out 3.5 mm (a pupil).
IRIS_UV = 0.125
PUPIL_UV = 0.048
SHOTS = [{"name": "neutral", "weights": {}},
         {"name": "smile", "weights": {"lipCornerPuller_L": 1.0, "lipCornerPuller_R": 1.0, "cheekRaiser_L": 0.6,
                                       "cheekRaiser_R": 0.6}},
         {"name": "blink", "weights": {"eyesClosed_L": 1.0, "eyesClosed_R": 1.0}},
         {"name": "jaw_open", "weights": {"jawDrop": 0.8}}]
# The lashes: thin ribbons grown along ICT-FaceKit's lash cards (each card a row of lashes in ICT's own picture, which
# drawn solid reads as a black band round the eye), root to tip in the card's v, spread along its u.
LASHES_A_CARD = {"upper": 40, "lower": 22}
LASH_STEPS = 5  # segments root to tip
LASH_ROOT_WIDTH = 0.00009  # metres; a lash is about 0.1 mm thick at its root
LASH_TIP_WIDTH = 0.00002
LASH_SHORTEST = 0.75  # a lash's length as a share of its card, at least
LASH_SEED = 226
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
    count = ict.PIECES["face"][1] + 1
    under = body_field(body, laid["points"][:count])
    mapped = matrix.any(axis=1)[:, None, None]
    share = laid["share"][None, :, None]
    offsets[:, :count] = np.where(mapped, share * under + (1.0 - share) * offsets[:, :count], under)
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


def eye_finish(uv):
    """Each eye triangle's finish from its UV corners: 0 the white, 1 the iris, 2 the pupil, by its distance out
    from the eyeball's front in UV."""
    out = np.linalg.norm(uv.mean(axis=1) - 0.5, axis=1)
    return np.where(out < PUPIL_UV, 2, np.where(out < IRIS_UV, 1, 0))


def card_weights(card_uv, card_triangles, samples):
    """Each UV sample's three card points and their weights (the triangle it lies in, else the nearest)."""
    corners = card_uv  # (triangles, 3, 2)
    first, second, third = corners[:, 0], corners[:, 1], corners[:, 2]
    across, up = second - first, third - first
    determinant = across[:, 0] * up[:, 1] - across[:, 1] * up[:, 0]
    found_points, found_weights = [], []
    for sample in samples:
        offset = sample - first
        along_second = (offset[:, 0] * up[:, 1] - offset[:, 1] * up[:, 0]) / determinant
        along_third = (across[:, 0] * offset[:, 1] - across[:, 1] * offset[:, 0]) / determinant
        weights = np.stack([1.0 - along_second - along_third, along_second, along_third], axis=1)
        best = int(np.argmax(weights.min(axis=1)))
        chosen = np.clip(weights[best], 0.0, None)
        found_points.append(card_triangles[best])
        found_weights.append(chosen / chosen.sum())
    return np.array(found_points), np.array(found_weights)


def lash_cards(model, eye):
    """One eye's lash cards: each a (triangles, their UV corners, upper or lower) by connected part."""
    triangles, rows = model_triangles(model, [f"lashes_{eye}"])
    parts = trimesh.graph.connected_components(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]]]), min_len=1)
    eyeball = model["neutral"][slice(*ict.PIECES[f"eyeball_{eye}"])].mean(axis=0)
    cards = []
    for part in parts:
        own = np.isin(triangles, part).all(axis=1)
        side = "upper" if model["neutral"][part][:, 1].mean() > eyeball[1] else "lower"
        cards.append((triangles[own], model["uvs"][model["corners"][rows[own]]], side))
    return cards


def lash_strands(model, points, offsets, rng):
    """The lashes as thin ribbons: (points, triangles, shapes), each ribbon point a weighted mix of its card's
    points (so it moves with the lids in every expression) and a fixed sideways half width."""
    made_points, made_shapes, made_triangles = [], [], []
    for eye in ("left", "right"):
        eyeball = points[slice(ict.PIECES[f"eyeball_{eye}"][0], ict.PIECES[f"eyeball_{eye}"][1] + 1)].mean(axis=0)
        for card_triangles, card_uv, side in lash_cards(model, eye):
            flat = card_uv.reshape(-1, 2)
            (u_low, v_low), (u_high, v_high) = flat.min(axis=0), flat.max(axis=0)
            near_low = points[card_triangles.reshape(-1)[flat[:, 1] < v_low + 0.1 * (v_high - v_low)]]
            near_high = points[card_triangles.reshape(-1)[flat[:, 1] > v_high - 0.1 * (v_high - v_low)]]
            low_is_root = (np.linalg.norm(near_low - eyeball, axis=1).mean() <
                           np.linalg.norm(near_high - eyeball, axis=1).mean())
            root, tip = (v_low, v_high) if low_is_root else (v_high, v_low)
            count = LASHES_A_CARD[side]
            margin = 0.03 * (u_high - u_low)
            for along in u_low + margin + (u_high - u_low - 2 * margin) * (np.arange(count) + rng.random(count)) / count:
                reach = root + (tip - root) * rng.uniform(LASH_SHORTEST, 1.0)
                steps = np.linspace(root, reach, LASH_STEPS + 1)
                samples = np.stack([np.full(len(steps), along), steps], axis=1)
                nudged = samples + [1e-3 * (u_high - u_low), 0.0]
                corners, weights = card_weights(card_uv, card_triangles, samples)
                nudged_corners, nudged_weights = card_weights(card_uv, card_triangles, nudged)
                centre = np.einsum("sc,scd->sd", weights, points[corners])
                sideways = np.einsum("sc,scd->sd", nudged_weights, points[nudged_corners]) - centre
                sideways /= np.maximum(np.linalg.norm(sideways, axis=1, keepdims=True), 1e-12)
                half = np.linspace(LASH_ROOT_WIDTH, LASH_TIP_WIDTH, len(steps))[:, None] / 2.0
                moved = np.einsum("sc,kscd->ksd", weights, offsets[:, corners])
                start = sum(len(chunk) for chunk in made_points)
                made_points.append(np.vstack([centre - half * sideways, centre + half * sideways]))
                made_shapes.append(np.concatenate([moved, moved], axis=1))
                left, right = start + np.arange(len(steps)), start + len(steps) + np.arange(len(steps))
                for step in range(LASH_STEPS):
                    made_triangles += [[left[step], right[step], right[step + 1]],
                                       [left[step], right[step + 1], left[step + 1]]]
    return np.vstack(made_points), np.array(made_triangles), np.concatenate(made_shapes, axis=1)


def pieces(body, model, laid, matrix):
    """The face's pieces: {name: points, triangles, finish, shapes, uv?} with the skin the body joined to the face."""
    offsets = face_offsets(body, model, laid, matrix)
    centre = fit.head_centre(body)
    made = {}
    face_triangles, _ = model_triangles(model, MODEL_PIECES["skin"])
    joined_points = np.vstack([body["points"], laid["points"]])
    joined_shapes = np.concatenate([body["offsets"].astype(np.float64), offsets], axis=1)
    skin = fit.joined_skin(body["points"], laid["kept"], laid["strip"], laid["points"], face_triangles, centre)
    points, triangles, shapes = compact(joined_points, skin, joined_shapes)
    made["skin"] = {"points": points, "triangles": triangles, "finish": np.zeros(len(triangles), np.int64),
                    "shapes": shapes}
    lash_points, lash_triangles, lash_shapes = lash_strands(model, laid["points"], offsets,
                                                            np.random.default_rng(LASH_SEED))
    made["lashes"] = {"points": lash_points, "triangles": lash_triangles, "shapes": lash_shapes,
                      "finish": np.zeros(len(lash_triangles), np.int64)}
    for name in ("mouth", "teeth", "eyes", "tears"):
        triangles, rows = model_triangles(model, MODEL_PIECES[name])
        piece = {"finish": np.zeros(len(triangles), np.int64)}
        piece["uv"] = model["uvs"][model["corners"][rows]]
        if name == "eyes":
            piece["finish"] = eye_finish(piece["uv"])
        piece["points"], piece["triangles"], piece["shapes"] = compact(laid["points"], triangles, offsets)
        made[name] = piece
    return made


def face_file(made, body, out):
    """Write the pieces, their surfaces, the shots and the camera's aim as `blender_face.py` reads them."""
    eyes = (body["joint_LeftEye"] + body["joint_RightEye"]) / 2.0
    arrays = {"pieces": np.array(list(made)), "shape_names": np.array(expressions.MHR_EXPRESSIONS),
              "shots": np.array(json.dumps(SHOTS)), "aim": eyes + [0.0, -0.04, 0.0],
              "eye_distance": np.array(LENS_DISTANCE)}
    for name, piece in made.items():
        arrays[f"{name}.surfaces"] = np.array([address.split("/", 1)[1] for address in SURFACES[name]])
        for field in ("points", "triangles", "finish", "uv"):
            if field in piece:
                arrays[f"{name}.{field}"] = piece[field]
        arrays[f"{name}.shapes"] = piece["shapes"].astype(np.float32)
    np.savez_compressed(out, **arrays)
    return out


def fetched_surfaces(folder):
    """Every surface the face wears copied from score_lib under `folder`'s assets (place_build's fetch)."""
    sys.path.insert(0, str(REPO))
    from score.stages import place_build
    for address in sorted({address for addresses in SURFACES.values() for address in addresses}):
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
    print(f"face: scale {laid['scale']:.5f}, {len(made['skin']['triangles'])} skin triangles, "
          f"{len(stills)} stills -> {out / 'stills'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
