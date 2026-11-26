"""The face's brows and lashes as short strands (#226, grown the way the hair route grows a groom, #227): each a polyline
of points with a radius tapered root to tip, drawn as Blender hair curves in Cycles' Principled Hair BSDF and
written as USD BasisCurves by `tools/characters/hair/basis_curves.py`.

- **Brows** (`brows`): roots spread over a band along ICT-FaceKit's brow landmarks (the 68-point set's 17 to 26),
  tall at the brow's head and narrowing to its tail; each strand leaves the skin at a shallow angle and lies along it
  (every point kept LIFT off the skin under it), pointing up at the head, outward along the body and down at the tail,
  the lower hairs turned up and the upper ones down so they meet along the middle, as brows grow.
- **Lashes** (`lashes`): rooted along ICT-FaceKit's lash cards' root edges (the lids' margins), grown out along the
  card and curled off it, up from the upper lid and down from the lower; ICT's cards are flat strips standing straight
  out (their curl is painted in ICT's picture), so drawn as they are the upper lashes pointed at the camera.
- **Bound to the face**: a brow point moves as the skin under it (its closest skin point's offsets, barycentric), a
  lash point with its root's card triangle, turning with it; so both follow every control, a blink and a smile
  included.
- `checked` refuses strands whose roots left the skin or that pass into it.
"""
import numpy as np
import trimesh

import ict

BROW_LANDMARKS = {"right": [21, 20, 19, 18, 17], "left": [22, 23, 24, 25, 26]}  # head (by the nose) to tail
BROW_HAIRS = 450  # a brow holds about 250 to 600 hairs (650 drew the brows as dark blocks, round 1, 2026-11-26)
BROW_HEIGHT = (0.011, 0.0025)  # metres the brow's band spans at its head and its tail (it tapers to a point)
BROW_SOFT = 0.6  # the band's lower edge thins out over this share of its height: a soft edge, not a ruled line
BROW_TAIL = (0.7, 0.75)  # from this share along, the hairs thin out, by up to the second share at the tail's end
BROW_DROP = 0.7  # the band's middle this share of its height below the landmarks, which follow its upper part
BROW_LENGTH = {"head": (0.004, 0.007), "body": (0.007, 0.010), "tail": (0.004, 0.007)}  # metres, by where it grows
BROW_ROUND = 0.08  # the brow's head rounds off over this share of its length: its band and its hairs thin out
BROW_ANGLE = (75.0, 15.0, -20.0)  # degrees from outward toward up: at the head, the body (from 0.3 on) and the tail
BROW_MEET = 25.0  # degrees a hair at the band's bottom is turned up, at its top down
BROW_SPREAD = 8.0  # degrees of each hair's own turn
BROW_POINTS = 7
LIFT = 0.0006  # metres a brow hair lies off the skin once it has risen
RISE = 0.0015  # metres along a brow hair over which it rises to LIFT
BROW_RADIUS = (0.000055, 0.00001)  # a hair's radius at its root and tip (a brow hair is 0.08 to 0.15 mm thick)
LASHES_A_CARD = {"upper": 50, "lower": 25}  # three cards a lid: about 150 upper lashes and 75 lower, as on a lid
LASH_LENGTH = {"upper": (0.008, 0.011), "lower": (0.005, 0.007)}  # metres
LASH_CURL = {"upper": 0.35, "lower": 0.2}  # how far the tip rises off the root's line, as a share of the length
LASH_POINTS = 7
LASH_RADIUS = (0.00007, 0.00001)  # a lash 0.1 to 0.15 mm at its root (0.12 mm drew the lashes faint, round 1)
ROOT_OFF = 0.0003  # metres: a root further from the skin than this has left it
INSIDE = 0.00005  # metres: a strand point further than this behind the skin passes into it
SEED = 226


def skin_offsets(mesh, offsets, places):
    """The offsets (controls, points, 3) at the skin points closest to `places`, barycentric on their triangles; and
    those closest points."""
    closest, _, triangle = trimesh.proximity.closest_point(mesh, places)
    corners = mesh.faces[triangle]
    weights = trimesh.triangles.points_to_barycentric(mesh.vertices[corners], closest)
    return np.einsum("pc,kpcd->kpd", weights, offsets[:, corners, :]), closest, triangle


def band_place(line, along):
    """The brow line's point and its direction (head to tail) at a share `along` of its length."""
    steps = np.linalg.norm(np.diff(line, axis=0), axis=1)
    reached = np.concatenate([[0.0], np.cumsum(steps)]) / steps.sum()
    leg = np.clip(np.searchsorted(reached, along, side="right") - 1, 0, len(steps) - 1)
    share = (along - reached[leg]) / (reached[leg + 1] - reached[leg])
    direction = (line[leg + 1] - line[leg]) / steps[leg][:, None]
    return line[leg] + share[:, None] * (line[leg + 1] - line[leg]), direction


def brow_angle(along, across, rng):
    """Each hair's angle (radians) from outward toward up, by its share along the brow and across it (-1 bottom to 1
    top)."""
    head, body, tail = BROW_ANGLE
    angle = np.where(along < 0.3, head + (body - head) * along / 0.3,
                     body + (tail - body) * np.clip((along - 0.3) / 0.7, 0.0, 1.0) ** 2)
    return np.radians(angle - BROW_MEET * across + rng.normal(0.0, BROW_SPREAD, len(along)))


def thinned(along, across):
    """The share of hairs kept at each place in the band, as many a square metre as the head's in its middle: fewer
    towards its lower edge (BROW_SOFT, a soft edge) and towards its tail's end (BROW_TAIL, a tapering tail)."""
    lower = np.clip((across + 1.0) / (2.0 * BROW_SOFT), 0.0, 1.0)
    tail = 1.0 - BROW_TAIL[1] * np.clip((along - BROW_TAIL[0]) / (1.0 - BROW_TAIL[0]), 0.0, 1.0)
    return (0.25 + 0.75 * lower) * tail


def brow_strands(mesh, offsets, line, up, rng):
    """One brow's strands on the skin `mesh` (its points' offsets per control `offsets`) along `line` (head to tail,
    metres), `up` the head's up: (counts, points, radius, shapes)."""
    along = rng.random(BROW_HAIRS * 3)
    across = rng.uniform(-1.0, 1.0, len(along))
    rounded = np.sqrt(np.clip(along / BROW_ROUND, 0.25, 1.0))  # the head's band rounded, not cut square
    height = (BROW_HEIGHT[0] + (BROW_HEIGHT[1] - BROW_HEIGHT[0]) * along) * rounded
    keep = rng.random(len(along)) < height / BROW_HEIGHT[0] * thinned(along, across)
    along, across, height = along[keep][:BROW_HAIRS], across[keep][:BROW_HAIRS], height[keep][:BROW_HAIRS]
    centre, outward = band_place(line, along)
    rough = centre + (across[:, None] / 2.0 - BROW_DROP) * height[:, None] * up
    _, roots, triangle = skin_offsets(mesh, offsets, rough)
    normal = mesh.face_normals[triangle]
    outward = outward - np.einsum("pd,pd->p", outward, normal)[:, None] * normal
    outward /= np.linalg.norm(outward, axis=1, keepdims=True)
    upward = np.cross(normal, outward)
    upward *= np.sign(upward @ up)[:, None]
    angle = brow_angle(along, across, rng)
    heading = np.cos(angle)[:, None] * outward + np.sin(angle)[:, None] * upward
    part = np.where(along < 0.3, "head", np.where(along < 0.8, "body", "tail"))
    length = rng.uniform(*np.array([BROW_LENGTH[name] for name in part]).T)
    reach = np.linspace(0.0, 1.0, BROW_POINTS)[None, :] * length[:, None]  # (hairs, points)
    guess = roots[:, None, :] + reach[..., None] * heading[:, None, :]
    shapes, on_skin, under = skin_offsets(mesh, offsets, guess.reshape(-1, 3))
    lift = LIFT * (1.0 - np.exp(-reach.reshape(-1) / RISE * 3.0))
    points = on_skin + mesh.face_normals[under] * lift[:, None]
    radius = np.tile(np.linspace(BROW_RADIUS[0], BROW_RADIUS[1], BROW_POINTS), len(length))
    return np.full(len(length), BROW_POINTS), points, radius, shapes


def brows(model, points, offsets, mesh):
    """Both brows' strands on the laid face (`points`, every model point; `offsets` per control) grown on its skin
    `mesh` (its triangles turned outward): (counts, points, radius, shapes)."""
    up = np.array([0.0, 1.0, 0.0])
    rng = np.random.default_rng(SEED)
    made = [brow_strands(mesh, offsets, points[model["landmarks"][marks]], up, rng)
            for marks in BROW_LANDMARKS.values()]
    return tuple(np.concatenate(parts, axis=-2 if index == 3 else 0) for index, parts in enumerate(zip(*made)))


def card_weights(card_uv, card_triangles, samples):
    """Each UV sample's three card points and their weights (the triangle it lies in, else the nearest)."""
    first, second, third = card_uv[:, 0], card_uv[:, 1], card_uv[:, 2]
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
    first, last = ict.PIECES[f"lashes_{eye}"]
    rows = np.flatnonzero(((model["triangles"] >= first) & (model["triangles"] <= last)).all(axis=1))
    triangles = model["triangles"][rows]
    parts = trimesh.graph.connected_components(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]]]), min_len=1)
    eyeball = model["neutral"][slice(*ict.PIECES[f"eyeball_{eye}"])].mean(axis=0)
    cards = []
    for part in parts:
        own = np.isin(triangles, part).all(axis=1)
        side = "upper" if model["neutral"][part][:, 1].mean() > eyeball[1] else "lower"
        cards.append((triangles[own], model["uvs"][model["corners"][rows[own]]], side))
    return cards


def lash_frame(moved, root, out, rising):
    """A lash's root, forward and normal (both unit) on its card with the card's points at `moved`: `root` and `out`
    (corners, weights) its root's place and a place a quarter out along the card, the normal turned up for an upper
    lid's lash and down for a lower's (`rising` 1 or -1; the face's frame is y up), forward kept square to it.
    (Turned away from the eyeball's centre instead, an upper card standing out in front of it curled down.)"""
    (root_corners, root_weights), (out_corners, out_weights) = root, out
    corners = moved[root_corners]
    start = root_weights @ corners
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    normal /= np.linalg.norm(normal)
    normal = normal if normal[1] * rising > 0 else -normal
    forward = out_weights @ moved[out_corners] - start
    forward -= (forward @ normal) * normal
    return start, forward / np.linalg.norm(forward), normal


def lash_line(root, forward, normal, length, curl):
    """A lash's points: out from its root along `forward`, rising along `normal` by `curl` of its length at its tip
    (as the square of the way along)."""
    along = np.linspace(0.0, 1.0, LASH_POINTS)[:, None]
    return root + along * length * forward + (along ** 2) * curl * length * normal


def lashes(model, points, offsets):
    """The lashes grown on the lids' margins: each rooted on its lash card's root edge (the one nearer the eyeball)
    and grown out along the card from root to tip, curling up off the upper lid and down off the lower
    (LASH_LENGTH, LASH_CURL); ICT's cards are flat strips standing straight out, their curl painted in their picture.
    Each point is bound to its root's card triangle: it moves with the root and turns with the triangle's frame (its
    offsets per control the frame's change under that control, so a blink carries the lashes down with the lid):
    (counts, points, radius, shapes)."""
    rng = np.random.default_rng(SEED)
    made_points, made_shapes = [], []
    for eye in ("left", "right"):
        first, last = ict.PIECES[f"eyeball_{eye}"]
        eyeball = points[first:last + 1].mean(axis=0)
        for card_triangles, card_uv, side in lash_cards(model, eye):
            rising = 1.0 if side == "upper" else -1.0
            flat = card_uv.reshape(-1, 2)
            (u_low, v_low), (u_high, v_high) = flat.min(axis=0), flat.max(axis=0)
            near_low = points[card_triangles.reshape(-1)[flat[:, 1] < v_low + 0.1 * (v_high - v_low)]]
            near_high = points[card_triangles.reshape(-1)[flat[:, 1] > v_high - 0.1 * (v_high - v_low)]]
            low_is_root = (np.linalg.norm(near_low - eyeball, axis=1).mean() <
                           np.linalg.norm(near_high - eyeball, axis=1).mean())
            root, tip = (v_low, v_high) if low_is_root else (v_high, v_low)
            count = LASHES_A_CARD[side]
            margin = 0.03 * (u_high - u_low)
            across = u_low + margin + (u_high - u_low - 2 * margin) * (np.arange(count) + rng.random(count)) / count
            ends = [card_weights(card_uv, card_triangles, np.stack([across, np.full(count, at)], axis=1))
                    for at in (root, root + 0.25 * (tip - root))]
            (root_corners, root_weights), (out_corners, out_weights) = ends
            length = rng.uniform(*LASH_LENGTH[side], count)
            curl = LASH_CURL[side] * rng.uniform(0.8, 1.2, count)
            for lash in range(count):
                places = ((root_corners[lash], root_weights[lash]), (out_corners[lash], out_weights[lash]))
                rest = lash_line(*lash_frame(points, *places, rising), length[lash], curl[lash])
                made_points.append(rest)
                made_shapes.append(np.stack([lash_line(*lash_frame(points + offsets[control], *places, rising),
                                                       length[lash], curl[lash]) - rest
                                             for control in range(len(offsets))]))
    count = len(made_points)
    radius = np.tile(np.linspace(LASH_RADIUS[0], LASH_RADIUS[1], LASH_POINTS), count)
    return np.full(count, LASH_POINTS), np.vstack(made_points), radius, np.concatenate(made_shapes, axis=1)


def checked(counts, points, mesh):
    """The strands' measures, refused when a root lies further than ROOT_OFF from the skin `mesh` or a point lies more
    than INSIDE behind it: {strands, roots_off_mm (largest), deepest_mm (furthest behind the skin)}."""
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    _, root_apart, _ = trimesh.proximity.closest_point(mesh, points[starts])
    closest, _, triangle = trimesh.proximity.closest_point(mesh, points)
    height = np.einsum("pd,pd->p", points - closest, mesh.face_normals[triangle])
    measures = {"strands": int(len(counts)), "roots_off_mm": round(float(root_apart.max()) * 1000, 3),
                "deepest_mm": round(float(max(0.0, -height.min())) * 1000, 3)}
    if root_apart.max() > ROOT_OFF or -height.min() > INSIDE:
        raise RuntimeError(f"strands left the skin or passed into it: {measures}")
    return measures
