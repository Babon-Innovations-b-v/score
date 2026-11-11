"""Wall things kept clear of the built pieces and the rows the fitting's own rules left them in (fitting.fitted calls
each; settle@habitat and settle@stairwell failed their resting gates on them, 2026-11-11).

    face_walls(stage, place)                        the built walls a slanted wall's thing finds its face on, no roof
    climbing(stage, place, entries)                 the turned boxes of the stair railings, kept clear of
    under_roofs(stage, place, entries, fits)        each wall thing up through a roof moved down or shrunk under it

Habitat's pipes laid 2.6 m up on its slanted walls, 0.44 m tall, cast their face rays at their middle, 2.82 m, over
the walls' 2.8 m tops: the rays met its dome's rim 0.3 m behind wall_3's face, the pipes were laid there and moved in
0.15 m off the dome (fitting.moved_in), 0.09 m inside wall_3 and wall_5, pipe_5 into pipe_15 laid under it. A stair
railing (a climbing row) is never parted, so stairwell's electrical box and wall lamp laid along its walls stood in
railings 5 and 2 reaching the wall. Its four conduit runs, read under the 11.8 m walls' tops and built 11.97 m tall from
the floor, stood 0.17 m up through its roof slab, which no move into the room clears.
"""
import numpy as np

# The least share of its built size a wall thing up through a roof is shrunk to, standing on the floor under it; one
# that would need more is left for the held gate to name.
SHRINK_MOST = 0.9


def face_walls(stage, place):
    """The place's built walls (its Structure and Shell pieces) without its roofs, as one mesh; None with none: a roof
    standing over a wall's top is no face a thing on that wall stands on (fitting.on_built_face)."""
    import trimesh
    from score.stages.assembly import fitting
    found = [mesh for scope in ("Structure", "Shell") for name, _ in fitting.walls_in(stage, place, scope)
             if not name.startswith(fitting.ROOF)
             and (mesh := fitting.surface_mesh(stage, f"/{place}/{scope}/{name}")) is not None]
    return trimesh.util.concatenate(found) if found else None


def climbing(stage, place, entries):
    """[corners [8, 3]] of each laid thing of a climbing row's part (fitting.climbs, the row no climbing row itself: a
    stair railing, never the stair, whose box holds the room over its flight; its turned box, oriented_corners), which
    the parting never moves, so a wall or face thing keeps clear of it as it keeps clear of a door's swing."""
    from score.stages.assembly import fitting
    paths = [f"/{place}/Objects/{entry['name']}" for entry in entries
             if fitting.climbs(entry) and str(entry.get("row") or "") not in fitting.CLIMBING]
    return [fitting.oriented_corners(stage, path) for path in paths
            if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsActive()]


def under_roofs(stage, place, entries, fits):
    """Each wall thing (`entries`, their `on` how "wall"; a passage aside) whose built surface passes up through a
    roof's (fitting.through_roofs, after fitting.moved_in) by more than HELD_MOST moved straight down so its top stands
    ROOF_CLEAR under it, where its foot stays over the floor and it sinks into no static it was not in; else, standing
    on the floor (a run from the floor to the roof), shrunk about its foot to that height, its back kept on its wall,
    where that keeps SHRINK_MOST of its size; one neither clears is left for the held gate to name. Its fit (`fits`,
    changed in place, one added where it has none) takes its box and turned corners as laid after."""
    from score.stages.assembly import fitting
    built = fitting.roofs(stage, place)
    if not built:
        return
    statics = fitting.statics(fitting.walls(stage, place))
    by_fit = {fit["name"]: fit for fit in fits}
    for entry in entries:
        name, path = entry["name"], f"/{place}/Objects/{entry['name']}"
        if fitting.passes(entry):  # a passage meets its place from outside, through its wall (passages.py)
            continue
        through = fitting.through_roofs(stage, place, [name], built)
        if not through:
            continue
        drop = max(found["metres"] for found in through) + fitting.ROOF_CLEAR
        low, high = fitting.world_box(stage, path)
        before = {found for found, _ in fitting.inside_of(low, high, statics)}
        lowered = (low - [0.0, drop, 0.0], high - [0.0, drop, 0.0])
        foot = fitting.foot_middle(low, high)
        roofs = ", ".join(found["roof"] for found in through)
        if float(lowered[0][1]) >= 0.0 and not {found for found, _ in fitting.inside_of(*lowered, statics)} - before:
            fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot - [0.0, drop, 0.0])
            moved, scale, words = drop, 1.0, f"moved {drop:.2f} m down under {roofs}: laid up through it"
        else:
            scale = (float(high[1] - low[1]) - drop) / max(float(high[1] - low[1]), 1e-9)
            if scale < SHRINK_MOST:
                continue
            out = np.array([float(entry["on"]["out"][0]), 0.0, float(entry["on"]["out"][1])])
            deep = float(np.ptp(fitting.oriented_corners(stage, path) @ out))
            fitting.moved_by(stage.GetPrimAtPath(path), foot, scale, foot - out * deep * (1.0 - scale) / 2)
            moved, words = 0.0, (f"shrunk to {scale:.0%} under {roofs}: built taller than the room from the floor, "
                                 "up through it")
        fit = by_fit.get(name)
        if fit is None:
            fits.append(fitting.laid_fit(stage, path, entry, "wall", None, moved, scale, words))
            continue
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(
            f"{fit.get('words', '')}; {words}")
        after = fitting.world_box(stage, path)
        fit.update({"moved": round(float(fit["moved"]) + moved, 3), "scale": round(float(fit["scale"]) * scale, 4),
                    "words": f"{fit.get('words', '')}; {words}",
                    "low": [round(float(value), 4) for value in after[0]],
                    "high": [round(float(value), 4) for value in after[1]],
                    **({"corners": fitting.laid_face(entry["on"], fitting.oriented_corners(stage, path))["corners"]}
                       if "corners" in fit else {})})
