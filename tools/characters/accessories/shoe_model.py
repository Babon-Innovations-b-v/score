"""A library shoe model fitted to a person's feet (#228): the shoe the outfit names (`accessories.shoes.model`, a
score_lib model entry's glTF, a left shoe in its own frame: x towards the toe, y up, z to the wearer's right, metres)
scaled to each foot and set on it where the foot stands flattest, the right shoe its mirror. Its own geometry and UVs
are kept (scaled, its heel's drop levelled, its upper stretched where the foot presses); its finish is the library
surface the outfit names (`accessories.shoes.finish`).

- `read`: the model's points, triangles and texture coordinates (its seams kept), its insole's height along it (the
  upper's lowest, its strobel, `floor`) and its collar's (the upper's top at each step along it, the lower side, at
  most the dip at its sides, `collar`); the heel's drop levelled (`levelled`: a clip's bare foot stands flat).
- `cavity`: where a foot may be inside it. The model is no closed solid (an upper, a sole, a tongue and laces, each an
  open sheet), so the sheets that wall the foot in (`walls`: not the overlays sewn on one side) are laid into voxels
  of PITCH_M, closed by one voxel, and each horizontal slice's holes filled: below the collar every slice of an upper
  is a ring (the tongue closing the throat), so its inside is the shoe's; over the collar the slice is open and nothing
  is inside. The cavity is that inside less the shell, `clearance` its distance to the shell (negative outside it).
- `fitted`: the smallest shoe that takes the foot (`fit`: the length with room ahead of the toes and behind the heel,
  then the height, then the width; the place along, across and turned), its upper stretched over what is still short
  of MARGIN_M (`stretched`, at most STRETCH_LIMIT_M), its points carried by the skin weights of the foot points
  nearest them, so it moves with the foot and bends with the toes.
- `out_of`: how far each of the foot's covered skin points is out of the worn shoe on a clip frame: the point taken
  to where the shoe was fitted through the skinning of the shoe point nearest it, then its clearance read.
- `tucked`: the foot's skin under the shoe's own top (`top_heights` of the sheets that wall the foot in: the highest
  each step along, the heel counter over the collar's dip at the sides kept) moved in from the shoe's walls, MARGIN_M inside them, fading out over
  TUCK_FADE_M under that top: a heel counter rises over the dip the cavity is cut at, the skin behind it was never
  asked to be inside it, and the Achilles stood out through the runner's heel in a torn V (#223 photoreal round 1).
  `walls_out` reads how far a point is out through the shoe's walls: no shoe surface outwards of it from the shoe's
  middle, the nearest inwards.
- `shell`: the same skin moved out to the shoe's outside, the shoe as the drape's cloth meets it (the garments' drape
  collides with the body alone; a jeans hem cut onto the shoe went through it).
"""
import numpy as np
import numpy as np

PITCH_M = 0.0015  # the cavity's voxels, in the model's own metres
MARGIN_M = 0.002  # the covered skin at least this far inside the shoe at the bind
INSOLE_M = 0.001  # the foot's lowest this far over the insole
STANDING_M = 0.012  # the foot's skin this near the insole stands on it and round its rounded edge
SHELL_VOXELS = 2.5  # the shell's voxels a point standing on the insole may lie in (the surface closed by one voxel)
COVERED_UNDER_M = 0.006  # the skin this far under the collar is covered by the shoe
FIRST_COVER_M = 0.04  # before the first fit: the foot's skin this far over its lowest is covered
LENGTHS = np.arange(0.80, 1.20, 0.005)  # the shoe's length scales tried, smallest first
HEIGHTS = np.arange(1.0, 1.301, 0.02)  # its height over its length scale (a toe box taller before a longer shoe)
WIDTHS = np.arange(0.95, 1.351, 0.02)  # its width over its length scale
ALONG_M = np.arange(0.0, 0.0401, 0.002)  # its heel's back this far behind the foot's (the heel counter's wall)
ACROSS_M = np.arange(-0.012, 0.0121, 0.002)  # and across it off the middles together
YAWS = np.arange(-14.0, 14.1, 2.0)  # its turn off the foot's ankle-to-toe-end line, degrees
STEP_M = 0.005  # the steps along the model its insole and collar heights are read at
BLEND_NEAREST = 4
STRETCH_LIMIT_M = 0.006  # the most the upper is stretched over the foot (a foot shorter of room asks a bigger shoe)
STRETCH_M = 0.012  # how far a stretch fades over the upper, in the model's own metres
STRETCH_NEAREST = 400  # the model points a short skin point stretches
STRETCH_ROUNDS = 5
ENDS_M = 0.008  # the foot's toes' and heel's ends: this far of the foot from each end
ENDS_LOW_M = 0.035  # and this low (over the heel the collar's padding hugs the Achilles)
STRETCH_ENDS_M = 0.03  # the foot's middle line ends this far in from its toe and its heel, in the model's metres
TUCK_FADE_M = 0.01  # the tuck fades out over this much under the shoe's top
SHELL_CLEAR_M = 0.002  # the drape's shoe this far outside the shoe
HEEL_SHARE = 0.25  # the back of the shoe whose top is read leaning (its heel counter)
LEAN_M = 0.04  # how far ahead of the heel's skin its counter's rim may lean, in the model's metres
TUCK_ROUNDS = 3  # the tuck's rounds into the cavity


def read(path):
    """The model's surface, its heel's drop levelled: {"points", "faces", "uv" (one a point), "floor" and "collar"
    ((steps along x, heights))}."""
    import trimesh
    mesh = trimesh.load(str(path), process=False, force="mesh")
    points, faces = np.asarray(mesh.vertices, dtype=float), np.asarray(mesh.faces, dtype=np.int64)
    uv = np.asarray(mesh.visual.uv, dtype=float)
    steps = np.arange(points[:, 0].min(), points[:, 0].max() + STEP_M, STEP_M)
    points = levelled(points, steps, insole_heights(largest_sheet(points, faces), steps))
    upper = largest_sheet(points, faces)
    import trimesh
    walled = trimesh.util.concatenate(walls({"points": points, "faces": faces}))
    return {"points": points, "faces": faces, "uv": uv, "floor": (steps, insole_heights(upper, steps)),
            "collar": (steps, collar_heights(upper, steps)), "top": (steps, leaning(top_heights(walled, steps), steps))}


def levelled(points, steps, floor):
    """The model with its heel's drop taken out (a running shoe's insole falls ~1 cm from its heel to its ball; a
    clip's bare foot stands flat, so with the drop kept its toes stood a centimetre over the insole and through the
    toe box, 2026-11-25): behind the ball (the insole's lowest) everything over the insole lowered by the insole's
    rise there over the ball's, at most its rise a third of the way along (the heel cup's curve up the back is no
    drop), and the sole under it pressed down to match, so the outsole stays where it is."""
    ball = int(np.argmin(floor))
    third = int(len(steps) / 3)
    drop = np.clip(floor - floor[ball], 0.0, floor[third] - floor[ball])
    drop[ball:] = 0.0
    lowered = np.interp(points[:, 0], steps, drop)
    under = np.interp(points[:, 0], steps, floor)
    found = points.copy()
    found[:, 1] = np.where(points[:, 1] < under, points[:, 1] * (under - lowered) / np.maximum(under, 1e-9),
                           points[:, 1] - lowered)
    return found


def largest_sheet(points, faces):
    """The points and faces of the model's largest connected sheet (its upper), its seams welded for telling edges."""
    import trimesh
    welded = trimesh.Trimesh(points, faces)
    return max(welded.split(only_watertight=False), key=lambda part: len(part.faces))


def insole_heights(upper, steps):
    """The insole's height at each step along the model: the upper's lowest point there (its strobel, the bottom it
    is sewn to the sole by; the sole under it is hollow), the nearest step's where a step has none."""
    points = np.asarray(upper.vertices)
    found = np.array([points[np.abs(points[:, 0] - step) < STEP_M, 1].min()
                      if (np.abs(points[:, 0] - step) < STEP_M).any() else np.nan for step in steps])
    known = ~np.isnan(found)
    return np.interp(steps, steps[known], found[known])


def collar_heights(upper, steps):
    """The collar's height at each step along the model: its top there (`top_heights`), at most its lowest over the
    back half (a slice over the collar's dip at the sides is open all along, so nothing over it is inside, the heel
    cup's top neither)."""
    found = top_heights(upper, steps)
    share = (steps - steps[0]) / np.ptp(steps)
    return np.minimum(found, found[(share > 0.1) & (share < 0.5)].min())


def top_heights(upper, steps):
    """The top of `upper` (a sheet, or the sheets that wall the foot in: a heel counter sewn on is one) at each step
    along the model: the lower of its highest point on either side (the heel counter over the collar's dip kept)."""
    points = np.asarray(upper.vertices)
    middle = (points[:, 2].max() + points[:, 2].min()) / 2.0
    found = []
    for step in steps:
        near = np.abs(points[:, 0] - step) < STEP_M
        sides = [points[near & (points[:, 2] < middle), 1], points[near & (points[:, 2] >= middle), 1]]
        found.append(min(side.max() for side in sides) if all(len(side) for side in sides) else np.nan)
    found = np.asarray(found)
    known = ~np.isnan(found)
    return np.interp(steps, steps[known], found[known])


def leaning(top, steps):
    """The top over the heel's skin: at each step of the shoe's back HEEL_SHARE, the highest top within LEAN_M ahead
    of it (a runner's heel counter leans forward over the Achilles, its rim 3.5 cm ahead of its foot; read at the
    skin's own step, the Achilles behind the leaning counter was taken for skin over the shoe, #223)."""
    found = top.copy()
    heel = steps < steps[0] + HEEL_SHARE * np.ptp(steps)
    for index in np.flatnonzero(heel):
        found[index] = top[(steps >= steps[index]) & (steps <= steps[index] + LEAN_M)].max()
    return found


def walls(model):
    """The model's sheets that wall the foot in: those that cross its middle across (the upper, the tongue, the
    laces, the sole round the upper's lower edge). An overlay sewn on one side (a stripe, a heel tab) is outside the
    upper and no wall: taken as one, a runner's stripes narrowed its inside by 2 cm."""
    import trimesh
    welded = trimesh.Trimesh(model["points"], model["faces"])
    middle = (model["points"][:, 2].max() + model["points"][:, 2].min()) / 2.0
    return [sheet for sheet in welded.split(only_watertight=False) if sheet.bounds[0][2] < middle < sheet.bounds[1][2]]


def cavity(model):
    """Where a foot may be inside the model: {"origin", "clearance" (each voxel's distance in metres to the shell,
    positive inside the cavity, negative outside)}."""
    import trimesh
    from scipy import ndimage
    origin = model["points"].min(axis=0) - 3 * PITCH_M
    shell = np.zeros(np.floor(np.ptp(model["points"], axis=0) / PITCH_M).astype(int) + 8, dtype=bool)
    for sheet in walls(model):
        points, _ = trimesh.remesh.subdivide_to_size(sheet.vertices, sheet.faces, PITCH_M / 2.0)
        shell[tuple(np.floor((points - origin) / PITCH_M).astype(int).T)] = True
    shell = ndimage.binary_dilation(shell, iterations=1)
    filled = np.stack([ndimage.binary_fill_holes(shell[:, row, :]) for row in range(shell.shape[1])], axis=1)
    inside = filled & ~shell
    # the shell was closed by one voxel: the surface lies a voxel inside the closed shell's edge
    clearance = (np.where(inside, ndimage.distance_transform_edt(inside),
                          -ndimage.distance_transform_edt(~inside)) + 1.0) * PITCH_M
    across = inside.any(axis=1)  # seen from over the shoe: which cells along and across hold any inside
    held = across.any(axis=0)
    columns = np.arange(across.shape[0])[:, None]
    ends = (np.where(held, np.where(across, columns, -1).max(axis=0), -1),
            np.where(held, np.where(across, columns, across.shape[0]).min(axis=0), across.shape[0]))
    return {"origin": origin, "clearance": clearance, "ends": ends}


def room_along(grid, points):
    """How far each point (in the model's frame) is behind the cavity's toe and in front of its heel at its place
    across, seen from over the shoe (the lesser; negative past either, or where no inside is across)."""
    across = np.clip(np.floor((points[:, 2] - grid["origin"][2]) / PITCH_M).astype(int), 0, len(grid["ends"][0]) - 1)
    front = grid["origin"][0] + (grid["ends"][0][across] + 0.5) * PITCH_M
    back = grid["origin"][0] + (grid["ends"][1][across] + 0.5) * PITCH_M
    return np.minimum(front - points[:, 0], points[:, 0] - back)


def clearance_at(grid, points):
    """The cavity's clearance at points in the model's frame (outside the grid: far outside)."""
    cells = np.floor((points - grid["origin"]) / PITCH_M).astype(int)
    shape = np.array(grid["clearance"].shape)
    held = np.all((cells >= 0) & (cells < shape), axis=1)
    found = np.full(len(points), -1.0)
    found[held] = grid["clearance"][tuple(cells[held].T)]
    return found


def moves_at(body, frame):
    """The joints' moves off the bind on one of the body's frames (joints x 4 x 4)."""
    return np.asarray(body["worlds"])[frame] @ np.linalg.inv(np.asarray(body["joints"], dtype=float))


def joint_at(body, name, frame):
    names = [str(each) for each in body["names"]]
    return np.asarray(body["worlds"])[frame][names.index(name)][:3, 3]


def foot_frame(body, side, frame):
    """The foot's frame on one of the body's frames: (ankle, forward along the floor, up, the wearer's right)."""
    ankle, end = joint_at(body, f"{side}Foot", frame), joint_at(body, f"{side}ToeEnd", frame)
    forward = (end - ankle) * np.array([1.0, 0.0, 1.0])
    forward /= np.linalg.norm(forward)
    up = np.array([0.0, 1.0, 0.0])
    return ankle, forward, up, np.cross(forward, up)


def foot_points(body, side, top, frame):
    """This side's skin points under the knee and under `top` (a height over the foot's lowest) on `frame`."""
    points = np.asarray(body["frames"])[frame]
    other = "Right" if side == "Left" else "Left"
    ankle, far = joint_at(body, f"{side}Foot", frame), joint_at(body, f"{other}Foot", frame)
    near = np.abs(points[:, 0] - ankle[0]) < np.abs(points[:, 0] - far[0])
    near &= points[:, 1] < joint_at(body, f"{side}Shin", frame)[1]
    return np.flatnonzero(near & (points[:, 1] < points[near, 1].min() + top))


def planted(body, side):
    """The clip frame the foot stands flattest on the floor: the higher of its heel's and its ball's lowest least
    (the shoe is fitted there, so its sole lies on the floor as the foot stands)."""
    found = []
    frames = range(int(body["clip_start"]), len(body["frames"]))
    for frame in frames:
        _, forward, _, _ = foot_frame(body, side, frame)
        skin = np.asarray(body["frames"])[frame][foot_points(body, side, 0.15, frame)]
        along = skin @ forward
        share = (along - along.min()) / np.ptp(along)
        heel, ball = skin[share < 0.25, 1], skin[(share > 0.6) & (share < 0.8), 1]
        found.append(max(heel.min(), ball.min()) if len(heel) and len(ball) else np.inf)
    return list(frames)[int(np.argmin(found))]


def to_model(points, frame, place):
    """Points at the bind in the model's frame for a shoe placed by `place` ({"shift" (the model's origin in the
    foot's frame: along, up, the wearer's right), "scale" (x, y, z), "mirror" (-1 for the right shoe, mirrored in
    z)})."""
    ankle, forward, up, right = frame
    local = np.stack([(points - ankle) @ forward, (points - ankle) @ up, (points - ankle) @ right], axis=1)
    found = (local - place["shift"]) / place["scale"]
    found[:, 2] *= place["mirror"]
    return found


def from_model(points, frame, place):
    ankle, forward, up, right = frame
    local = points * np.array([1.0, 1.0, place["mirror"]]) * place["scale"] + place["shift"]
    return ankle + np.outer(local[:, 0], forward) + np.outer(local[:, 1], up) + np.outer(local[:, 2], right)


def shifts(model, grid, local, length, height, width, mirror):
    """Every place tried at one length and width scale (ALONG_M x ACROSS_M): its heel's back `along` behind the foot's
    heel's back, its middle `across` off the foot's middle, the foot's lowest INSOLE_M over the insole. (shifts,
    places x 3; the skin in the model's frame at each, places x points x 3)."""
    scale = np.array([length, length * height, length * width])
    model_middle = (model["points"][:, 2].max() + model["points"][:, 2].min()) / 2.0
    foot_middle = (local[:, 2].max() + local[:, 2].min()) / 2.0
    along, across = np.meshgrid(ALONG_M, ACROSS_M, indexing="ij")
    found = np.zeros((along.size, 3))
    found[:, 0] = local[:, 0].min() - along.ravel() - model["points"][:, 0].min() * length
    found[:, 2] = foot_middle + across.ravel() - mirror * model_middle * scale[2]
    inside = (local[None] - found[:, None]) / scale
    inside[..., 2] *= mirror
    floor = np.interp(inside[..., 0], *model["floor"])
    found[:, 1] = (local[None, :, 1] - scale[1] * floor).min(axis=1) - INSOLE_M
    inside[..., 1] = (local[None, :, 1] - found[:, 1, None]) / scale[1]
    return found, inside


def asked(model, grid, inside, height_scale, margin=MARGIN_M):
    """Each skin point's clearance (places x points x 3 in the model's frame, or points x 3), metres, as MARGIN_M asks
    it: the sole of the foot and the skin round its edge (within STANDING_M of the insole) stands on the insole and
    presses into its rounded edge as a foot does in a shoe, so it is asked only not to be out past the shell (within
    SHELL_VOXELS of it, the shell's own voxels, inside the sole's wall round it): read `margin` plus those over its
    clearance."""
    clearance = clearance_at(grid, inside.reshape(-1, 3)).reshape(inside.shape[:-1]) * height_scale
    standing = (inside[..., 1] - np.interp(inside[..., 0], *model["floor"])) * height_scale < STANDING_M
    return np.where(standing, clearance + margin + SHELL_VOXELS * PITCH_M * height_scale, clearance)


def yawed(frame, degrees):
    """The foot's frame turned `degrees` round its up (a foot's long axis is not its ankle-to-toe-end line)."""
    ankle, forward, up, right = frame
    angle = np.radians(degrees)
    return ankle, forward * np.cos(angle) + right * np.sin(angle), up, right * np.cos(angle) - forward * np.sin(angle)


def fit(model, grid, frame, skin, mirror, needed):
    """The smallest place whose skin has `needed` clearance (m; less than nought: the shoe's upper to be stretched
    over it, `stretched`): the shortest length scale with room ahead of the toes and behind the heel at the tallest
    and widest, then at that length the lowest height that gives the clearance at the widest, then the narrowest
    width, each found by halving (more room never takes less of the foot; the tallest or the widest when none gives
    it, the stretch and the fit's checks then saying how far short it is), and the place along, across and turned
    that gives the most. (place, its least clearance m), or (None, the clearance) when no length gives the room."""
    turned = [yawed(frame, degrees) for degrees in YAWS]
    locals_ = [np.stack([(skin - each[0]) @ each[1], (skin - each[0]) @ each[2], (skin - each[0]) @ each[3]], axis=1)
               for each in turned]

    ends = [((local[:, 0] < local[:, 0].min() + ENDS_M) | (local[:, 0] > local[:, 0].max() - ENDS_M))
            & (local[:, 1] < local[:, 1].min() + ENDS_LOW_M) for local in locals_]

    def tried(length, height, width):
        """The best place at one scale: (place, its least clearance, how far it is past `needed` of all the skin,
        how far past MARGIN_M of room along the shoe ahead of the toes' and behind the heel's low ends, seen from
        over the shoe: a stretch across the foot gives no length)."""
        best = None
        for each, local, end in zip(turned, locals_, ends):
            found, inside = shifts(model, grid, local, length, height, width, mirror)
            clearance = asked(model, grid, inside, length * height)
            room = room_along(grid, inside[:, end].reshape(-1, 3)).reshape(len(found), -1).min(axis=1) * length
            past = np.minimum(clearance.min(axis=1) - needed, room - MARGIN_M)
            pick = int(past.argmax())
            if best is None or past[pick] > best[2]:
                best = ({"shift": found[pick], "scale": np.array([length, length * height, length * width]),
                         "mirror": mirror, "frame": each}, float(clearance[pick].min()), float(past[pick]),
                        float(room[pick] - MARGIN_M))
        return best

    def first_taking(values, place_of, measure):
        """The first of `values` whose place's `measure` (2: all asked, 3: the length's room) is met, the last's
        when none is: halving."""
        low, high = 0, len(values) - 1
        while low < high:
            middle = (low + high) // 2
            if place_of(values[middle])[measure] >= 0.0:
                high = middle
            else:
                low = middle + 1
        return values[low]

    length = first_taking(LENGTHS, lambda value: tried(value, HEIGHTS[-1], WIDTHS[-1]), 3)
    height = first_taking(HEIGHTS, lambda value: tried(length, value, WIDTHS[-1]), 2)
    width = first_taking(WIDTHS, lambda value: tried(length, height, value), 2)
    found = tried(length, height, width)
    return (found[0] if found[3] >= 0.0 else None), found[1]


def covered_by(model, frame, place, skin_points):
    """Which of `skin_points` (at the bind) are under the fitted shoe's collar less COVERED_UNDER_M."""
    inside = to_model(skin_points, frame, place)
    collar = np.interp(inside[:, 0], *model["collar"])
    return (inside[:, 1] < collar - COVERED_UNDER_M / place["scale"][1]) & (
        inside[:, 0] > model["points"][:, 0].min()) & (inside[:, 0] < model["points"][:, 0].max())


def stretched(model, grid, place, skin):
    """The model's upper stretched over the skin it is short of MARGIN_M round (a knit upper gives where a toe or a
    bunion presses; a foot wider at its toes than the toe box asked for a shoe 35 cm long, 2026-11-25): each round,
    every model point over the insole moved out from the foot's middle line (across and up at its step along the foot;
    towards the toe and the heel past STRETCH_ENDS_M from the foot's ends) by the most any short skin point asks of
    it, fading over STRETCH_M (a Gaussian), the cavity read again. Out
    from the foot's middle, not along the model's normals: its overlays and inner sheets face every way, and moved
    along them the upper tore 4 cm open (2026-11-25). (model, cavity, least clearance m)."""
    from scipy.spatial import cKDTree
    found, height_scale = dict(model), place["scale"][1]
    inside = to_model(skin, place["frame"], place)
    steps = np.arange(inside[:, 0].min(), inside[:, 0].max() + STEP_M, STEP_M)
    bins = np.clip(np.searchsorted(steps, inside[:, 0]), 0, len(steps) - 1)
    held = np.unique(bins)
    middle = np.array([inside[bins == each, 1:].mean(axis=0) for each in held])
    over = found["points"][:, 1] > np.interp(found["points"][:, 0], *model["floor"]) + PITCH_M  # the insole stays
    for _ in range(STRETCH_ROUNDS):
        clearance = asked(found, grid, inside, height_scale)
        short = clearance < MARGIN_M
        if not short.any():
            break
        need = (MARGIN_M - clearance[short]) / height_scale + PITCH_M
        moved = np.zeros(len(found["points"]))
        for amount, (distances, near) in zip(need, zip(*cKDTree(found["points"]).query(
                inside[short], k=STRETCH_NEAREST, distance_upper_bound=3.0 * STRETCH_M))):
            kept = np.isfinite(distances)
            moved[near[kept]] = np.maximum(moved[near[kept]], amount * np.exp(-(distances[kept] / STRETCH_M) ** 2))
        along = np.clip(found["points"][:, 0], inside[:, 0].min() + STRETCH_ENDS_M, inside[:, 0].max() - STRETCH_ENDS_M)
        centre = np.stack([along, *[np.interp(along, steps[held], middle[:, axis]) for axis in range(2)]], axis=1)
        away = found["points"] - centre
        away /= np.maximum(np.linalg.norm(away, axis=1, keepdims=True), 1e-9)
        points = found["points"] + away * (moved * over)[:, None]
        reach = points - model["points"]  # the stretch so far, at most STRETCH_LIMIT_M at the worn scale
        length = np.linalg.norm(reach, axis=1, keepdims=True)
        found["points"] = model["points"] + reach * np.minimum(1.0, STRETCH_LIMIT_M / height_scale
                                                              / np.maximum(length, 1e-12))
        grid = cavity(found)
    return found, grid, float(asked(found, grid, inside, height_scale).min())


def fitted(body, side, model, grid):
    """The model fitted on the body's `side` foot where it stands flattest (`planted`), level on the floor there,
    stretched where the foot is short of room (`stretched`), and taken back to the bind through the skinning of the
    foot points nearest each of its points: {"points" (at the bind), "faces", "uv", "blend", "weights", "covered" (the
    body's points it covers), "place", "frame", "grid" (its own cavity), "fit moves" (the joints' moves where it was
    fitted), "least clearance mm", "foot length m"}; raises when no shoe in the scales tried takes the foot."""
    from tools.characters.accessories import skin_blend
    at = planted(body, side)
    points = np.asarray(body["frames"])[at]
    frame = foot_frame(body, side, at)
    mirror = 1.0 if side == "Left" else -1.0
    first = foot_points(body, side, FIRST_COVER_M, at)
    place, least = fit(model, grid, frame, points[first], mirror, MARGIN_M - STRETCH_LIMIT_M / 2.0)
    if place is None:
        raise ValueError(f"{side} foot: no shoe scale takes it ({least * 1000.0:.1f} mm least clearance)")
    near = foot_points(body, side, 0.25, at)
    covered = near[covered_by(model, place["frame"], place, points[near])]
    place, least = fit(model, grid, frame, points[covered], mirror, MARGIN_M - STRETCH_LIMIT_M / 2.0)
    if place is None:
        raise ValueError(f"{side} foot: no shoe scale takes its covered skin ({least * 1000.0:.1f} mm)")
    covered = near[covered_by(model, place["frame"], place, points[near])]
    worn, grid, least = stretched(model, grid, place, points[covered])
    made = from_model(worn["points"], place["frame"], place)
    faces = model["faces"] if mirror > 0 else model["faces"][:, ::-1]
    carriers = foot_points(body, side, np.ptp(made[:, 1]) + 0.02, at)
    blend = skin_blend(made, points, carriers, BLEND_NEAREST)
    weights = blend @ np.asarray(body["weights"], dtype=float)
    fit_moves = moves_at(body, at)
    bind = np.einsum("pab,pb->pa", np.linalg.inv(np.einsum("pj,jab->pab", weights, fit_moves)),
                     np.c_[made, np.ones(len(made))])[:, :3]
    _, forward, _, _ = place["frame"]
    return {"points": bind, "faces": faces, "uv": model["uv"], "blend": blend, "weights": weights,
            "covered": covered, "place": place, "frame": place["frame"], "model": worn, "grid": grid,
            "fit moves": fit_moves, "under top": near[under_top(worn, place, points[near])],
            "least clearance mm": round(least * 1000.0, 2), "foot length m": float(np.ptp(points[first] @ forward))}


def under_top(model, place, skin_points, below=0.0):
    """Which of `skin_points` (where the shoe was fitted) lie under the shoe's top less `below` (m) and along it."""
    inside = to_model(skin_points, place["frame"], place)
    top = np.interp(inside[:, 0], *model["top"])
    return (inside[:, 1] < top - below / place["scale"][1]) & (inside[:, 0] > model["points"][:, 0].min()) & (
        inside[:, 0] < model["points"][:, 0].max())


def middle_line(inside):
    """The shoe's middle under points in its frame: each point's step along, clipped STRETCH_ENDS_M in from the
    points' ends, at the mean height and width of the points in its step."""
    steps = np.arange(inside[:, 0].min(), inside[:, 0].max() + STEP_M, STEP_M)
    bins = np.clip(np.searchsorted(steps, inside[:, 0]), 0, len(steps) - 1)
    held = np.unique(bins)
    middle = np.array([inside[bins == each, 1:].mean(axis=0) for each in held])
    along = np.clip(inside[:, 0], inside[:, 0].min() + STRETCH_ENDS_M, inside[:, 0].max() - STRETCH_ENDS_M)
    return np.stack([along, *[np.interp(along, steps[held], middle[:, axis]) for axis in range(2)]], axis=1)


def walls_out(model, inside, middle):
    """How far each point (the model's frame) is out through the shoe's walls (negative: inside them by that much)
    and the unit way in, level, from it to the shoe's middle: no surface of the shoe outwards, the distance to the
    nearest inwards (a surface outwards, any of the model's sheets, covers it from sight); a point with neither is
    neither (0)."""
    import trimesh
    mesh = trimesh.Trimesh(model["points"], model["faces"], process=False)
    way_in = (middle - inside) * np.array([1.0, 0.0, 1.0])
    way_in /= np.maximum(np.linalg.norm(way_in, axis=1, keepdims=True), 1e-12)
    found = np.zeros(len(inside))
    for sign in (-1.0, 1.0):  # outwards, then inwards
        hits, rays, _ = mesh.ray.intersects_location(inside, way_in * sign, multiple_hits=True)
        distance = np.full(len(inside), np.inf)
        np.minimum.at(distance, rays, np.linalg.norm(hits - inside[rays], axis=1))
        if sign < 0:
            covered = np.isfinite(distance)
            found[covered] = -distance[covered]
        else:
            out = ~covered & np.isfinite(distance)
            found[out] = distance[out]
    return found, way_in


def skin_at_fit(made, body):
    """The skin under the shoe's top where the shoe was fitted: each point's skinning there (points x 4 x 4) and its
    place in the model's frame."""
    place = made["place"]
    matrices = np.einsum("pj,jab->pab", np.asarray(body["weights"], float)[made["under top"]], made["fit moves"])
    bind = np.asarray(body["bind"], float)[made["under top"]]
    fitted = np.einsum("pab,pb->pa", matrices, np.c_[bind, np.ones(len(bind))])[:, :3]
    return matrices, to_model(fitted, place["frame"], place)


def bind_moves(made, matrices, inside, steps):
    """Moves of points in the model's frame (`steps`, model metres) as moves at the bind: {"points" (the body's under
    top points), "moves"}, carried by each point's skinning on a frame (`tuck_at`)."""
    place = made["place"]
    moved = from_model(inside + steps, place["frame"], place) - from_model(inside, place["frame"], place)
    return {"points": made["under top"], "moves": np.einsum("pab,pb->pa", np.linalg.inv(matrices[:, :3, :3]), moved)}


def tucked(made, body):
    """The foot's skin under the shoe's top moved in from its walls to MARGIN_M inside them where the shoe was
    fitted, level towards the shoe's middle, then where the cavity is closed up its clearance's slope till it is
    MARGIN_M inside it, fading out over TUCK_FADE_M under the top: each moved point's move at the bind
    (`bind_moves`)."""
    worn, scale = made["model"], made["place"]["scale"][1]
    matrices, inside = skin_at_fit(made, body)
    out, way_in = walls_out(worn, inside, middle_line(inside))
    fade = np.clip((np.interp(inside[:, 0], *worn["top"]) - inside[:, 1]) * scale / TUCK_FADE_M, 0.0, 1.0)
    steps = way_in * (np.clip(out + MARGIN_M / scale, 0.0, None) * fade)[:, None]
    # then into the cavity where it is closed (under the collar): the level way in misses skin pressing up through the
    # tongue (the foot 1.9 mm out of its runner's cavity, #223 round 1)
    gradient = np.stack(np.gradient(made["grid"]["clearance"]), axis=-1)
    closed = inside[:, 1] < np.interp(inside[:, 0], *worn["collar"]) - COVERED_UNDER_M / scale
    for _ in range(TUCK_ROUNDS):
        moved = inside + steps
        short = np.clip(MARGIN_M - asked(worn, made["grid"], moved, scale), 0.0, None) * closed * fade
        if not short.any():
            break
        cells = np.clip(np.floor((moved - made["grid"]["origin"]) / PITCH_M).astype(int), 0,
                        np.array(gradient.shape[:3]) - 1)
        way = gradient[tuple(cells.T)]
        way /= np.maximum(np.linalg.norm(way, axis=1, keepdims=True), 1e-12)
        steps = steps + way * (short / scale + PITCH_M / 2.0 * (short > 0.0))[:, None]
    return bind_moves(made, matrices, inside, steps)


def shell(made, body):
    """The skin under the shoe's top moved out to the shoe's outside and SHELL_CLEAR_M past it where the shoe was
    fitted (`bind_moves`): the shoe as the drape's cloth meets it (a jeans hem breaks over it, not through it). Each
    point moved level out from the shoe's middle to the farthest of the shoe's surfaces that way; one with none, or
    standing on the insole (under the foot, where no cloth comes), stays."""
    import trimesh
    worn, scale = made["model"], made["place"]["scale"][1]
    matrices, inside = skin_at_fit(made, body)
    mesh = trimesh.Trimesh(worn["points"], worn["faces"], process=False)
    way_out = (inside - middle_line(inside)) * np.array([1.0, 0.0, 1.0])
    way_out /= np.maximum(np.linalg.norm(way_out, axis=1, keepdims=True), 1e-12)
    hits, rays, _ = mesh.ray.intersects_location(inside, way_out, multiple_hits=True)
    farthest = np.zeros(len(inside))
    np.maximum.at(farthest, rays, np.linalg.norm(hits - inside[rays], axis=1))
    standing = inside[:, 1] - np.interp(inside[:, 0], *worn["floor"]) < STANDING_M / scale  # the sole: no cloth
    need = np.where((farthest > 0.0) & ~standing, farthest + SHELL_CLEAR_M / scale, 0.0)
    return bind_moves(made, matrices, inside, way_out * need[:, None])


def tuck_at(tuck, body, frame, skin):
    """`skin` (the body's points on `frame`) with the tuck's points moved by their moves turned by their own skinning
    there."""
    turned = np.einsum("pj,jab->pab", np.asarray(body["weights"], float)[tuck["points"]], moves_at(body, frame))
    found = np.array(skin, float)
    found[tuck["points"]] += np.einsum("pab,pb->pa", turned[:, :3, :3], tuck["moves"])
    return found


def at_fit(made, skin, moves):
    """`skin` (posed by `moves`, the joints' moves off the bind this frame) taken to where the shoe was fitted through
    the skinning of the shoe point nearest each, in the model's frame."""
    from scipy.spatial import cKDTree
    weights = made["weights"]
    posed = np.einsum("pj,jab->pab", weights, moves)
    shoe = np.einsum("pab,pb->pa", posed, np.c_[made["points"], np.ones(len(made["points"]))])[:, :3]
    _, nearest = cKDTree(shoe).query(skin)
    there = np.einsum("pj,jab->pab", weights[nearest], made["fit moves"]) @ np.linalg.inv(posed[nearest])
    back = np.einsum("pab,pb->pa", there, np.c_[skin, np.ones(len(skin))])[:, :3]
    return to_model(back, made["frame"], made["place"])


def out_of(made, skin, moves):
    """How far each covered skin point (`skin`, posed) is out of the worn shoe, metres, nought inside: each point
    taken to where the shoe was fitted (`at_fit`, `moves` the joints' moves off the bind this frame, joints x 4 x 4),
    its clearance read there."""
    inside = at_fit(made, skin, moves)
    return np.maximum(-asked(made["model"], made["grid"], inside, made["place"]["scale"][1], 0.0), 0.0)


def top_out(made, skin, moves):
    """How far each of the foot's skin points under the shoe's top (`skin`, posed: the body's `under top` points) is
    out through the shoe's walls (`walls_out`), metres, nought inside or within COVERED_UNDER_M of the top."""
    inside = at_fit(made, skin, moves)
    scale = made["place"]["scale"][1]
    under = inside[:, 1] < np.interp(inside[:, 0], *made["model"]["top"]) - COVERED_UNDER_M / scale
    found = np.zeros(len(skin))
    if under.any():
        found[under] = np.maximum(walls_out(made["model"], inside[under], middle_line(inside)[under])[0], 0.0) * scale
    return found
