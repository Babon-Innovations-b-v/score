"""One real tuning body on the card for the adjoint (#70, Newton's Python only, never imported by `__init__.py`): its
`fit/_card/_clip.Clip` built as `evaluation/_card_batch.body_run` builds it (the module state `_case.prepared` lays,
the sizing, level 2's constants, `_clip.for_fitting`) and its clips' level 3 rows solved in one
`fit/_card/_sets.Sets([clip])` batch, each frame from its own seed, the rows in Newton's order (the free root's turn
x, y, z, w): the solved point `_bodies.copied_couplings` and `TapedSites` start from. `per_frame_model` is the body
copied once per frame for `TapedSites`, `frame_couplings` its `couplings=` off the clip's projection."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from evaluation import _card_batch, _case  # noqa: E402
from fit._card import _clip, _seeds  # noqa: E402
from _bodies import copied_couplings  # noqa: E402
from fit._card._sets import Sets  # noqa: E402


def set_up(table, weights, root, cases, saved):
    """One body's `Clip`, its `Fitting`, its clips' targets ({case: (turns, points)}) and the person's file for the set whose table.json,
    weights.json and rest.json are `table`, `weights` and `root`'s (`cases` {case: job path}, one body); `saved`
    (`_card_batch.Saved`) puts the module state back first, so a body never lays on top of another."""
    saved.restore()
    recordings = _case.prepared(table, weights, root, cases)
    clips, rig, path, targets = _card_batch.laid_clips(root, cases, recordings)
    _, (job, person, _, worlds) = next(iter(clips.items()))
    _, _, fitting = _card_batch.cached_set_up(job, person, rig, worlds, path,
                                             _card_batch.recorded_targets(clips, targets))
    return _clip.for_fitting(fitting, path), fitting, targets, path


def soma_of(table, weights, root, cases, saved):
    """SOMA's side of the measures for the body `set_up` laid: (MyoFullBody's scales, SOMA's segments, every clip's
    worlds (frames, segments, 4, 4) clip after clip in `targets`' order, SOMA's rig); run after `set_up`, so the sizing
    is cached."""
    saved.restore()
    clips, rig, path, _ = _card_batch.laid_clips(root, cases, _case.prepared(table, weights, root, cases))
    job, person, _, _ = next(iter(clips.values()))
    _, scales = _card_batch.cached_sized(job, person, rig, path)
    return scales, person["segments"], np.concatenate([np.asarray(clip[3]) for clip in clips.values()]), rig


def joint_parts(clip, scales, segments, worlds):
    """`TapedMeasures`' joints on `per_frame_model`: {segment: (parts per frame [[(link, local point scaled, share)]],
    SOMA's joint per frame (frames, 3) in SOMA's frame)}, each joint's centre as `evaluation._measure.centre` reads it
    (CENTRES' bone and local point times its scale, a MIDDLE one the mean of its parts), link shifted copy by copy."""
    from evaluation import _measure as cpu
    bodies = clip.model.body_count
    joints = {}
    for segment in [segment for segment in cpu.JOINTS if segment in segments]:
        names = cpu.MIDDLE.get(cpu.JOINTS[segment], (cpu.JOINTS[segment],))
        parts = [(clip.body[cpu.CENTRES[name][0].replace("-", "_").replace(" ", "_")],
                  np.asarray(cpu.CENTRES[name][1], dtype=float) * scales[cpu.CENTRES[name][0]], 1 / len(names))
                 for name in names]
        joints[segment] = ([[(link + frame * bodies, local, share) for link, local, share in parts]
                            for frame in range(len(worlds))], worlds[:, segments.index(segment), :3, 3])
    return joints


def skin_parts(clip, rig, segments, worlds):
    """`TapedMeasures`' skins on `per_frame_model`: {scored region: (bone points per skin frame [[(link, local point in
    the link frame)]], SOMA's posed skin per skin frame [(verts, faces)])}, as `fit/_card/_measure` measures them (every
    EVERY-th frame of `worlds` taken as one clip, `fit/_skin.bone_meshes`' kept vertices, the hand's parts as "hand",
    `posed_skins`' points), each kept vertex moved off its geom into its body's frame, the link shifted copy by copy."""
    from scipy.spatial.transform import Rotation
    from fit._card._measure import posed_skins, scored_labels
    from fit._skin import EVERY, bone_meshes
    mjm, bodies, frames = clip.mjm, clip.model.body_count, np.arange(0, len(worlds), EVERY)
    links, locals_, bones = [], [], []
    for geom, kept, label in bone_meshes(mjm):
        start = mjm.mesh_vertadr[mjm.geom_dataid[geom]]
        turn = Rotation.from_quat(mjm.geom_quat[geom], scalar_first=True).as_matrix()
        locals_.append(mjm.mesh_vert[start + kept] @ turn.T + mjm.geom_pos[geom])
        links += [clip.body[label]] * len(kept)
        bones += [label] * len(kept)
    links, locals_, labels = np.array(links), np.concatenate(locals_), scored_labels(bones)
    skins = [(verts, rig["faces"]) for verts in posed_skins(rig, segments, worlds, frames)]
    return {name: ([[(link + frame * bodies, local) for link, local in zip(links[labels == name], locals_[labels == name])]
                    for frame in frames], skins) for name in sorted(set(labels))}


def turn_groups(clip, segments, worlds):
    """`TapedMeasures`' turns on `per_frame_model`: {segment: (FRAME_BODY's link per frame, identity offset, SOMA's
    turn per frame x y z w)}, the frozen table folded into SOMA's side (TO_OWN.T @ the world's turn @ frozen_turn), so
    each degree is `fit/_card/_measure.turn_errors`' angle between the link's turn and that one."""
    from scipy.spatial.transform import Rotation
    from evaluation import _measure as cpu
    from fit._frozen import frozen_turn
    from model import TO_OWN
    frames = np.arange(len(worlds)) * clip.model.body_count
    return {segment: (frames + clip.body[cpu.FRAME_BODY[segment]], np.array([0, 0, 0, 1.0]),
                      Rotation.from_matrix(TO_OWN.T @ worlds[:, segments.index(segment), :3, :3]
                                           @ frozen_turn(segment)).as_quat())
            for segment in segments if segment in cpu.FRAME_BODY}

def solved_rows(clip, targets, seeds):
    """Every clip's level 3 rows (frames x nq, Newton's order, clip after clip in `targets`' order) and steps from
    one `Sets([clip]).angles` batch; `seeds` {case: qpos [frames, nq], MuJoCo's layout}."""
    for case, (turns, _) in targets.items():
        if len(seeds[case]) != len(turns):
            raise ValueError(f"{case}: {len(seeds[case])} seeds for {len(turns)} frames")
    ((qpos, steps),) = Sets([clip]).angles([np.concatenate([turns for turns, _ in targets.values()])],
                                           [np.concatenate([points for _, points in targets.values()])],
                                           [np.concatenate([seeds[case] for case in targets])])
    return _seeds.newton_order(qpos), steps


def per_frame_model(fitting, path, frames):
    """Newton's model of the person's file at `path` (its inside joints moved as `fitting` holds them, as
    `_clip.for_fitting` builds it) copied `frames` times, joint_q copy by copy, built with requires_grad for the tape."""
    import newton
    one = newton.ModelBuilder(up_axis=newton.Axis.Z)
    one.add_mjcf(str(path), convert_mjc_equality_constraints=False, parse_meshes=False)
    _clip.moved_inside(one, fitting)
    copied = newton.ModelBuilder(up_axis=newton.Axis.Z)
    for _ in range(frames):
        copied.add_builder(one)
    return copied.finalize(device=_clip.DEVICE, requires_grad=True)


def frame_couplings(clip, rows):
    """`TapedSites`' couplings for `per_frame_model` at the solved `rows` (frames x nq, Newton's order) from the
    clip's projection (its one set's polynomials)."""
    projection = clip.projection
    return copied_couplings(projection.follower_coord.numpy(), projection.leader_coord.numpy(),
                            projection.follower_rest.numpy(), projection.leader_rest.numpy(),
                            projection.poly.numpy()[0], projection.frozen_coord.numpy(), rows)


def taped_sites(clip, model, rows, targets):
    """`TapedSites` on `per_frame_model`'s `model` holding level 3's whole cost as the card's `Clip.optimizer_for`
    lays it: each frame's marker sites (link, site_pos, its place cost, its target point) and turn rows (link,
    site_quat x y z w, the turn cost, its target turn), copy by copy, with `frame_couplings` at the solved `rows`."""
    from scipy.spatial.transform import Rotation
    from _taped import TapedSites
    turns = np.concatenate([turned for turned, _ in targets.values()])
    points = np.concatenate([placed for _, placed in targets.values()])
    frames, bodies = len(rows), clip.model.body_count
    shift = np.repeat(np.arange(frames) * bodies, len(clip.place_sites))
    links = np.tile([clip.link(site) for site in clip.place_sites], frames) + shift
    weights = np.tile(clip.place_costs, frames)
    offsets = np.array([clip.mjm.site_pos[site] for site in clip.place_sites]).ravel()
    turn_links = (np.tile([clip.link(site) for site in clip.frame_sites], frames)
                  + np.repeat(np.arange(frames) * bodies, len(clip.frame_sites)))
    turn_offsets = np.tile([clip.mjm.site_quat[site][[1, 2, 3, 0]] for site in clip.frame_sites], (frames, 1))
    wanted = Rotation.from_matrix(turns.reshape(-1, 3, 3)).as_quat()
    sites = TapedSites(model, links, weights, points.reshape(-1, 3),
                       turns=(turn_links, np.full(len(turn_links), clip.turn_cost), wanted, turn_offsets),
                       couplings=frame_couplings(clip, rows), copies=frames)
    return sites, offsets


HELD = 1e-5  # rad or m: a coordinate this close to its bound is held there by the card's active set


def bound_held(clip, couplings, rows):
    """A mask over `RootTurns`' reduced pose (frames x (per copy - 1)): True where the solved row holds that
    coordinate at its limited range's bound (`clip.reduction`), so the inner optimum fixes it there and the pose
    drops it; the root's turn chart (3 tangent entries) is never held."""
    frames, size = rows.shape
    free = np.asarray(couplings[0][:len(couplings[0]) // frames]) % size
    reduced = np.concatenate([free[:3], [-1, -1, -1], free[7:]])
    lower, upper = np.full(size, -np.inf), np.full(size, np.inf)
    coordinates = clip.reduction.free_coord.numpy()
    lower[coordinates], upper[coordinates] = clip.reduction.lower.numpy(), clip.reduction.upper.numpy()
    held = np.zeros((frames, len(reduced)), dtype=bool)
    chosen = reduced >= 0
    values = rows[:, reduced[chosen]]
    held[:, chosen] = (values <= lower[reduced[chosen]] + HELD) | (values >= upper[reduced[chosen]] - HELD)
    return held.ravel()
