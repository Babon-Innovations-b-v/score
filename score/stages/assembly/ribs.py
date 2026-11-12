"""Things kept off a curved hull's ribs: the place's structure laid from an inventory row (its Structure prims with a
`score:row`: tube's arched structural ribs, design_shell.arched) whose box holds the room across, so no box rule sees
where they stand (fitting.stood_off leaves a piece out reaching more than STAND_OFF_MOST from a wall's face).

    kept_clear(stage, place, path, on, clear, mounted, built)   a wall thing's clear and built boxes with the ribs'
                                                                 parts beside its wall at its height (fitting.fitted)
    kept_off(stage, place, loose, entries)                      each hung thing let down under the ribs over it and
                                                                 each one within a rib drawn out of it (fitting.fitted)

Tube's eight ribs are arches 3.2 m across and high, 0.2 m thick, standing in front of its walls' faces from 0.85 m up
(0.25 m out at 1.2 m, 0.41 m at 1.83 m): its left screens, wall panels and pipe bundles laid flat on the walls stood
0.05 to 0.10 m in the ribs they crossed; its ceiling lights, hung from the vault's 3.2 m top, 0.05 to 0.07 m in the
ribs' undersides at 3.0 m; its wall lamps laid within a rib's box, all of the room, stood inside the rib's 0.2 m leg
(settle@tube, 2026-11-12).
"""
import numpy as np

# A thing drawn out of a rib is laid this far clear of its face, metres: touching, not inside.
DRAWN_CLEAR = 0.001
# Rays read a rib's face over a thing's height and across it on a grid this many points a side.
FACE_RAYS = 5
# Rays read a rib's front and a wall thing's back this far apart in height, metres: tube's round pipe bundles, read
# 0.14 m apart, were stood 0.04 m off the ribs, touching nothing.
HEIGHT_STEP = 0.01
# Rays read a wall thing's back from this far behind its wall's face, metres.
OWN_BEHIND = 1.0


def pieces(stage, place):
    """[(name, mesh)] of the place's row structure: each Structure prim laid from an inventory row (`score:row`) that
    is no deck, level, wall or roof the shell builds (tube's deck and walls carry their floor's and panels' rows), its
    world surface (fitting.surface_mesh)."""
    from score.stages.assembly import fitting
    root = stage.GetPrimAtPath(f"/{place}/Structure")
    found = [(child.GetName(), fitting.surface_mesh(stage, child.GetPath())) for child in
             (root.GetChildren() if root else []) if child.GetAttribute("score:row").IsValid()
             and child.GetAttribute("score:row").Get()
             and child.GetName().split("_")[0] not in (*fitting.STATICS, fitting.ROOF)]
    return [(name, mesh) for name, mesh in found if mesh is not None]


def beside(mesh, start, run, out, band, own=None):
    """(low, high) the box of a piece's (`mesh`) part beside a wall's face (`start` [x, z], `run` the way along it,
    `out` its way into the room) within the height `band` (low, high): from the face out to where a wall thing whose
    surface is `own` (its mesh, None for its box) touches the piece's front standing out of the face; None where the
    piece has no front there. Its front is where rays from its middle cast back at the face meet it, every HEIGHT_STEP
    over the band and FACE_RAYS over its run along the face; where rays cast out from behind the face at the same
    spots meet `own`, its surface's depth behind its box's back there is taken off (else, the thing not over the piece
    as laid, its least depth at that height anywhere along it): tube's pipe bundles, round pipes stood by their box's
    back corner on a rib's curved front, touched nothing."""
    reach = float((mesh.bounds.mean(axis=0)[[0, 2]] - start) @ out)
    alongs, heights = grid(mesh, start, run, band)
    spots = start + np.outer(alongs, run) + out * reach
    fronts = met(mesh, np.c_[spots[:, 0], heights, spots[:, 1]], -out, start, out)
    if not np.isfinite(fronts).any():
        return None
    front = float(np.nanmax(fronts))
    if own is not None:
        box_back = float(((np.array([[x, z] for x in own.bounds[:, 0] for z in own.bounds[:, 2]]) - start)
                          @ out).min())
        behind = start + np.outer(alongs, run) - out * OWN_BEHIND
        backs = met(own, np.c_[behind[:, 0], heights, behind[:, 1]], out, start, out)  # at the piece's own spots
        both = np.isfinite(fronts) & np.isfinite(backs)
        if not both.any():  # the thing not over the piece as laid: its least depth at each height, anywhere along it
            others, _ = grid(own, start, run, band)
            behind = start + np.outer(others, run) - out * OWN_BEHIND
            backs = met(own, np.c_[behind[:, 0], heights, behind[:, 1]], out, start, out).reshape(-1, FACE_RAYS)
            backs = np.repeat(np.nanmin(np.where(np.isfinite(backs), backs, np.inf), axis=1), FACE_RAYS)
            both = np.isfinite(fronts) & np.isfinite(backs)
        if both.any():
            front = float((fronts[both] - (backs[both] - box_back)).max())
    ends = [start + run * along + out * off for along in span_of(mesh, start, run) for off in (0.0, front)]
    low = np.array([min(end[0] for end in ends), band[0], min(end[1] for end in ends)])
    high = np.array([max(end[0] for end in ends), band[1], max(end[1] for end in ends)])
    return low, high


def span_of(mesh, start, run):
    """(from, to) metres along a wall's face (`start`, `run`) a mesh's box reaches."""
    corners = np.array([[x, z] for x in mesh.bounds[:, 0] for z in mesh.bounds[:, 2]]) - start
    return float((corners @ run).min()), float((corners @ run).max())


def levels(band):
    """The heights every HEIGHT_STEP over a `band` (low, high), its ends among them."""
    return np.linspace(band[0], band[1], max(2, int(np.ceil((band[1] - band[0]) / HEIGHT_STEP)) + 1))


def grid(mesh, start, run, band):
    """(alongs, heights) of a grid over a mesh's run along a wall's face (FACE_RAYS) and a height `band` (levels), one
    row a height."""
    heights, alongs = (values.ravel() for values in np.meshgrid(levels(band),
                                                                 np.linspace(*span_of(mesh, start, run), FACE_RAYS),
                                                                 indexing="ij"))
    return alongs, heights


def met(mesh, origins, way, start, out):
    """[n] how far out of a wall's face (`start`, `out`) the first point of `mesh` a ray from each of `origins` [n, 3]
    along `way` [x, z] meets stands; NaN where a ray meets none."""
    found = np.full(len(origins), np.nan)
    hits, rays, _ = mesh.ray.intersects_location(origins, np.tile([way[0], 0.0, way[1]], (len(origins), 1)),
                                                 multiple_hits=False)
    if len(rays):
        found[np.asarray(rays, int)] = (np.asarray(hits, float)[:, [0, 2]] - start) @ out
    return found


def kept_clear(stage, place, path, on, clear, mounted, built):
    """(clear, built) for a wall thing (its prim at `path`, laid by `on`) on a wall the row structure stands in front
    of: each row piece reaching across the room more than STAND_OFF_MOST from the wall's face given by its part
    beside the wall at the thing's height (beside), kept clear of (`clear`) where a stretch of the face clear of them,
    `clear` and the things laid before it (`mounted`) holds the thing whole (it slides there, on_wall), else stood on
    (`built`: on their front where the thing's surface touches it, fitting.stood_off); both as given on a slanted
    wall or with no such piece."""
    from score.stages.assembly import fitting
    if fitting.slanted_wall(on):
        return clear, built
    low, high = fitting.world_box(stage, path)
    start, run, out, length = fitting.wall_line(on)
    band = (float(low[1]), float(high[1]))
    found = [mesh for _, mesh in pieces(stage, place)
             if float(((fitting.box_corners(mesh.bounds)[:, [0, 2]] - start) @ out).max()) > fitting.STAND_OFF_MOST]
    parts = [part for mesh in found if (part := beside(mesh, start, run, out, band)) is not None]
    if not parts:
        return clear, built
    reach, deep = fitting.wall_reach(low, high, run, out, fitting.oriented_corners(stage, path))
    free = fitting.free_stretches(start, run, out, length, deep, band, [*clear, *mounted, *parts])
    if any(end - begin >= reach for begin, end in free):
        return [*clear, *parts], built
    along = float((fitting.foot_middle(low, high)[[0, 2]] - start) @ run)
    begin, end = fitting.stretch_for(fitting.stretches(start, run, out, length, deep, band, [*clear, *mounted]),
                                     along, reach)
    middle = fitting.kept_within(along, begin, end, min(reach, end - begin) / 2)  # where on_wall lays it
    begin, end = middle - min(reach, end - begin) / 2, middle + min(reach, end - begin) / 2
    own = fitting.surface_mesh(stage, path)
    stood = [part for mesh in found if span_of(mesh, start, run)[0] < end and span_of(mesh, start, run)[1] > begin
             and (part := beside(mesh, start, run, out, band, own)) is not None]  # the pieces it crosses there
    return clear, [*built, *(along_all(part, start, run, length) for part in stood)]


def along_all(part, start, run, length):
    """A piece's part (low, high) beside a wall's face reaching its whole `length` along it, so the wall thing laid
    anywhere in the stretch it lands in stands on its front (fitting.stood_off reads the thing's own spot before
    on_wall moves it)."""
    low, high = (np.asarray(end, float).copy() for end in part)
    ends = [start + run * along for along in (0.0, length)]
    for axis, way in ((0, 0), (2, 1)):
        if abs(run[way]) > 1e-9:
            low[axis], high[axis] = min(end[way] for end in ends), max(end[way] for end in ends)
    return low, high


def kept_off(stage, place, loose, entries):
    """The fits of the hung things (`loose`, their `under roof`) let down under the row structure over them
    (let_down) and of the things laid within a row piece drawn out of it (drawn_out, `entries` their `on`)."""
    return let_down(stage, place, loose) + drawn_out(stage, place, entries)


def let_down(stage, place, loose):
    """The fits of each thing hung from the roof (`under roof`) whose box's top (topped) stands up in a row
    piece's underside over it: moved straight down so its top stands ROOF_CLEAR under the lowest such, where that is
    OUT_MOST at most and its foot stays over the floor; tube's ceiling lights hung from the vault's top 0.05 to 0.07 m
    in its ribs' undersides."""
    from score.stages.assembly import fitting
    built = [(name, np.asarray(mesh.triangles, float)) for name, mesh in pieces(stage, place)]
    fits = []
    for entry in loose if built else []:
        path = f"/{place}/Objects/{entry['name']}"
        if not entry.get("under roof") or not stage.GetPrimAtPath(path).IsActive():
            continue
        top = topped(*fitting.world_box(stage, path))
        over = [(name, float(np.nanmin(gaps))) for name, triangles in built
                if len(gaps := fitting.roof_under(top, triangles) - top[:, 1]) and np.isfinite(gaps).any()]
        under = [(name, gap) for name, gap in over if gap < fitting.ROOF_CLEAR - fitting.MOVE_LEAST]
        if not under:
            continue
        drop = fitting.ROOF_CLEAR - min(gap for _, gap in under)
        low, high = fitting.world_box(stage, path)
        if drop > fitting.OUT_MOST or float(low[1]) - drop < 0.0:
            continue
        foot = fitting.foot_middle(low, high)
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot - [0.0, drop, 0.0])
        names = [name for name, _ in under]
        fits.append(fitting.laid_fit(stage, path, entry, "down", names, drop, 1.0,
                                     f"moved {drop:.2f} m down under {', '.join(names)}: hung up into its underside"))
    return fits


def topped(low, high):
    """[n, 3] points every RAY_STEP over a box's (low, high) top: a long thin light has corners only at its ends, so
    none of its own points stood under the ribs it crossed."""
    from score.stages.assembly import fitting
    xs, zs = (np.linspace(low[axis], high[axis],
                          max(2, int(np.ceil((high[axis] - low[axis]) / fitting.RAY_STEP)) + 1)) for axis in (0, 2))
    return np.array([[x, float(high[1]), z] for x in xs for z in zs])


def drawn_out(stage, place, entries):
    """The fits of each thing laid within a row piece (`on` how "within", its holder in the Structure) standing in it:
    moved along the piece's long way on the floor toward its middle until its back stands DRAWN_CLEAR in front of the
    piece's face there, the face read by rays from the piece's middle out at the thing's heights and across it; tube's
    wall lamps laid within a rib's box stood inside its 0.2 m leg."""
    from score.stages.assembly import fitting
    meshes = dict(pieces(stage, place))
    fits = []
    for entry in entries:
        on, path = entry.get("on") or {}, f"/{place}/Objects/{entry['name']}"
        held = [meshes[name] for name in on.get("holder") or [] if name in meshes]
        if on.get("how") != "within" or on.get("holder scope") != "Structure" or not held \
                or not stage.GetPrimAtPath(path).IsActive():
            continue
        low, high = fitting.world_box(stage, path)
        shift = max((drawn(mesh, low, high) for mesh in held), key=lambda move: float(np.linalg.norm(move)))
        moved = float(np.linalg.norm(shift))
        if moved < fitting.MOVE_LEAST or moved > fitting.OUT_MOST:
            continue
        foot = fitting.foot_middle(low, high)
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + shift)
        fits.append(fitting.laid_fit(stage, path, entry, "within", on.get("holder"), moved, 1.0,
                                     f"moved {moved:.2f} m out of {', '.join(on.get('holder'))} toward its middle: "
                                     "laid within its box, inside its built leg"))
    return fits


def drawn(mesh, low, high):
    """[x, y, z] the move along a piece's (`mesh`) long way on the floor toward its middle that sets a thing's box
    (low, high) DRAWN_CLEAR in front of the face the piece shows its middle there (the first a ray from the middle
    out meets, at the box's heights and across it); zero where the box already stands so or no ray meets it."""
    lowest, highest = mesh.bounds
    axis = 0 if highest[0] - lowest[0] >= highest[2] - lowest[2] else 2
    across = 2 - axis
    middle = float(lowest[axis] + highest[axis]) / 2
    centre = (low[axis] + high[axis]) / 2
    sign = 1.0 if middle > centre else -1.0  # the way toward the middle
    heights, sides = np.meshgrid(np.linspace(low[1], high[1], FACE_RAYS), np.linspace(low[across], high[across],
                                                                                      FACE_RAYS))
    origins = np.zeros((heights.size, 3))
    origins[:, axis], origins[:, 1], origins[:, across] = middle, heights.ravel(), sides.ravel()
    ways = np.zeros_like(origins)
    ways[:, axis] = -sign
    hits, _, _ = mesh.ray.intersects_location(origins, ways, multiple_hits=False)
    if not len(hits):
        return np.zeros(3)
    face = float((np.asarray(hits, float)[:, axis] * sign).max())  # the face standing furthest toward the middle
    back = float(low[axis] if sign > 0 else -high[axis])
    need = face + DRAWN_CLEAR - back
    move = np.zeros(3)
    move[axis] = sign * need if need > 0.0 else 0.0
    return move
