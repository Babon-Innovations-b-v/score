"""A passage (fitting.passes: a tunnel, a tube laid against its wall) meets its place from outside through that wall,
so it is laid touching it. One left touching no built wall once the walls are laid and it is moved out past the ones
it stood in (fitting.moved_past) is moved back along its `out` until its surface stands GAP off the first built wall
it meets (by FCL's distance between the two surfaces, so it never goes into one), where that is fitting.OUT_MOST at
most. Workshop's glass tunnels stood outside its twelve built walls on its plan's eight facets, 0.06 to 0.19 m off
the nearest, touching nothing (settle@workshop, 2026-11-11).

    drawn_in(stage, place, entries)   the fits [{name, how "drawn", ...}] of the passages moved back onto their walls
    drawn_back(own, walls, way, most) metres `own` moves along `way` until it stands GAP off `walls`, never into them
"""
import numpy as np

# A passage drawn back onto its wall stops this far off it at most, metres: within the resting check's touch (3 cm),
# never into it.
GAP = 0.005
# The most steps a passage is drawn back in (drawn_back), each by its surface's distance from the walls less half GAP.
STEPS = 200


def tree(mesh):
    """A mesh in the world frame as an FCL collision object."""
    import fcl
    model = fcl.BVHModel()
    model.beginModel(len(mesh.vertices), len(mesh.faces))
    model.addSubModel(np.asarray(mesh.vertices, np.float64), np.asarray(mesh.faces, np.int64))
    model.endModel()
    return model


def apart(own, walls, shift):
    """Metres between the surfaces of the FCL model `own` moved by `shift` [x, y, z] and the collision object
    `walls`; 0 or less where they meet."""
    import fcl
    moved = fcl.CollisionObject(own, fcl.Transform(np.asarray(shift, np.float64)))
    return float(fcl.distance(moved, walls, fcl.DistanceRequest(), fcl.DistanceResult()))


def drawn_back(own, walls, way, most):
    """Metres the mesh `own` moves along the unit `way` [x, y, z] until its surface stands GAP off the mesh `walls` at
    most, never meeting them: each step by its distance from them less half GAP, so no step reaches them; None where it
    stands within GAP already or meets none within `most` metres."""
    import fcl
    model, against, moved = tree(own), fcl.CollisionObject(tree(walls), fcl.Transform()), 0.0
    if apart(model, against, np.zeros(3)) <= GAP:
        return None
    for _ in range(STEPS):
        distance = apart(model, against, way * moved)
        if distance <= GAP:
            return moved
        moved += distance - GAP / 2
        if moved > most:
            return None
    return None


def built_walls(stage, place):
    """The place's built walls (its Structure and Shell prims named wall...) as one mesh; None with none."""
    import trimesh
    from score.stages.assembly import fitting
    found = [mesh for scope in ("Structure", "Shell") for name, _ in fitting.walls_in(stage, place, scope)
             if name.split("_")[0] == "wall" and (mesh := fitting.surface_mesh(stage, f"/{place}/{scope}/{name}"))
             is not None]
    return trimesh.util.concatenate(found) if found else None


def drawn_in(stage, place, entries):
    """Each passage of `entries` (fitting.passes) standing more than GAP off every built wall moved back along its
    `out` until its surface stands GAP off the first it meets (drawn_back), where that is fitting.OUT_MOST at most;
    the fits [{name, how "drawn", ...}]."""
    from score.stages.assembly import fitting
    passages = [entry for entry in entries if fitting.passes(entry)]
    walls = built_walls(stage, place) if passages else None
    fits = []
    for entry in passages if walls is not None else []:
        path = f"/{place}/Objects/{entry['name']}"
        own = fitting.surface_mesh(stage, path)
        way = -np.array([float(entry["on"]["out"][0]), 0.0, float(entry["on"]["out"][1])])
        way /= max(float(np.linalg.norm(way)), 1e-9)
        moved = drawn_back(own, walls, way, fitting.OUT_MOST) if own is not None else None
        if moved is None or moved < fitting.MOVE_LEAST:
            continue
        low, high = fitting.world_box(stage, path)
        middle = fitting.foot_middle(low, high)
        fitting.moved_by(stage.GetPrimAtPath(path), middle, 1.0, middle + way * moved)
        words = f"moved {moved:.2f} m back onto its wall: a passage meets its place through it"
        fits.append({**fitting.laid_fit(stage, path, entry, "drawn", entry["on"].get("holder"), moved, 1.0, words),
                     **stood_on(entry["on"], fitting.oriented_corners(stage, path))})
    return fits


def stood_on(on, corners):
    """The fit's words for the held gate (fitting.laid_face) of a passage drawn back: its relation's face moved along
    its `out` onto its turned box's back (`corners`, oriented_corners), the face it now stands on."""
    from score.stages.assembly import fitting
    start, _, out, _ = fitting.wall_line(on)
    back = float(((np.asarray(corners, float)[:, [0, 2]] - start) @ out).min())
    return fitting.laid_face({**on, "span": [np.asarray(point, float) + out * back for point in on["span"]]}, corners)
