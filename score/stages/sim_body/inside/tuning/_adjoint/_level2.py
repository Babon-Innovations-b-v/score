"""Level 2's Body off `fit/_constants.Problem` (#70, case (a): the constants outer to level 3, their derivative from
level 2's own stationarity). The Problem's unknowns are the constants first, then each sampled frame's leading
coordinates; a `Body` reads poses first, then constants, so the unknowns and the gradient are permuted between the two.
The gradient is J^T r of the Problem's rows (`jacobian`, the card's exact `_card._level2.jacobian` in use), the
untold entries and the bound-held ones pinned by `_bodies.Pinned`. Numpy only: the Problem and its Jacobian are given."""
import numpy as np

from . import Body
from ._bodies import Pinned

HELD = 1e-5  # an unknown this far from a finite bound is held there by the solve's active set


def to_problem(inner, held):
    """Body order (poses, then the `held` constants) to the Problem's (constants, then poses)."""
    inner = np.asarray(inner, dtype=float)
    return np.concatenate([inner[inner.size - held:], inner[:inner.size - held]])


def to_body(unknowns, held):
    """The Problem's order (the `held` constants, then poses) to Body order (poses, then constants)."""
    unknowns = np.asarray(unknowns, dtype=float)
    return np.concatenate([unknowns[held:], unknowns[:held]])


def pinned_mask(problem, unknowns, kept):
    """Body-order mask of the entries level 2 does not move: not in `kept` (the told unknowns' indices, Problem
    order, as `fit/_constants.told` gives them) or within HELD of a finite bound."""
    low, high = problem.bounds()
    unknowns = np.asarray(unknowns, dtype=float)
    pinned = np.ones(unknowns.size, dtype=bool)
    pinned[np.asarray(kept, dtype=int)] = False
    pinned |= (np.isfinite(low) & (unknowns - low < HELD)) | (np.isfinite(high) & (high - unknowns < HELD))
    return to_body(pinned, len(problem.slots))


def level2_body(problem_at, jacobian, solved, kept, outer, sited=None):
    """Level 2 as a `Body` at its optimum `solved` (Problem order): `problem_at(outer)` the Problem at level 1's
    point, `jacobian(problem, unknowns)` its rows' Jacobian, `kept` the told unknowns (Problem order); with `sited`
    ((columns, step), `problem_at` a `sited_problem_at`) the Body gets `sited_products` as its `products`."""
    problem = problem_at(outer)
    held = len(problem.slots)
    inner = to_body(solved, held)
    pinned = Pinned(inner, pinned_mask(problem, solved, kept))
    last = {np.asarray(outer, dtype=float).tobytes(): problem}

    def problem_of(at):
        """The Problem at level 1's point `at`, rebuilt only when `at` moved since the last call (H's columns step the
        inner unknowns at one outer point; a real `problem_at` re-reads the body, 0.3 s a call)."""
        key = np.asarray(at, dtype=float).tobytes()
        if key not in last:
            last.clear()
            last[key] = problem_at(at)
        return last[key]

    def gradient(point, at):
        """J^T r at the Body-order point, the pinned entries' springs in place of theirs."""
        moved = problem_of(at)
        unknowns = to_problem(pinned.whole(point), held)
        found = jacobian(moved, unknowns).T @ moved.residuals(unknowns)
        return pinned.gradient(point, to_body(np.asarray(found).ravel(), held))

    frames = len(problem.path)
    body = Body("level 2", None, gradient, inner, frames, problem.width)
    if sited is not None:
        def products(point, at, weights):
            """`weights`^T dg/dtheta at `at` (`sited_products`), the cache moved to `at` first."""
            return sited_products(problem_of(at), problem_at.placed, jacobian, pinned, sited, point, at, weights)
        body.products = products
    return body


def sited_products(problem, placed, jacobian, pinned, sited, inner, outer, weights):
    """`weights`^T dg/dtheta of level 2's pinned gradient off a `sited_problem_at` Problem, dg/dtheta = dg/dmoved @
    columns: the costs' part 2 J^T dr/dc (each row linear in its cost, dr/dc central differences of the rows alone)
    through `goal_weights`' derivative, the sites' part central differences over the site rows `columns` moves; with
    `sited` (columns, step, arrow) a free mark's untold-free site row off H instead (`_free_site_columns`)."""
    columns, step = sited[:2]
    held = len(problem.slots)
    moved = placed.trusted + columns @ np.asarray(outer, dtype=float)
    sites = 3 * len(problem.fitting.mark_sites)
    unknowns = to_problem(pinned.whole(inner), held)

    def gradient_at(point):
        """The pinned gradient's outer-moving part (held entries zero) with the sites and costs at `point`."""
        placed(point)
        found = to_body(_gradient(problem, jacobian, unknowns), held)
        found[pinned.held] = 0.0
        return found

    by_moved = np.zeros((weights.shape[1], columns.shape[0]))
    off_h = _free_site_columns(problem, pinned, sited[2], weights) if len(sited) > 2 else {}
    for row in np.nonzero(np.abs(columns[:sites]).max(axis=1) > 0)[0]:
        if row in off_h:
            by_moved[:, row] = off_h[row]
            continue
        up, down = moved.copy(), moved.copy()
        up[row] += step
        down[row] -= step
        by_moved[:, row] = weights.T @ ((gradient_at(up) - gradient_at(down)) / (2 * step))
    placed(moved)
    by_moved[:, sites:] = weights.T @ _cost_gradients(problem, jacobian, pinned, unknowns) @ _dense(
        _cost_slopes(moved[sites:], placed.ends, step))
    return by_moved @ columns


def _free_site_columns(problem, pinned, arrow, weights):
    """{site row: `weights`^T dg/dsite} for each free mark's site coordinate whose constant is not held: the place rows
    read site + move alike, the prior row (its cost times the move) the move alone, so dg/dsite = H[:, constant] less
    the prior's cost squared on its own diagonal (H `level2_arrow`'s blocks, held rows already zero)."""
    blocks, couplings, corner = arrow
    frames, width = len(problem.path), problem.width
    poses, place = frames * width, problem.costs[1]
    found = {}
    for constant, slot in enumerate(problem.slots[:3 * len(problem.free)]):
        if pinned.held[poses + constant]:
            continue
        column = np.concatenate([couplings[:, :, constant].ravel(), corner[:, constant]])
        column[poses + constant] -= place[slot // 3] ** 2
        found[int(slot)] = weights.T @ column
    return found


def _cost_gradients(problem, jacobian, pinned, unknowns):
    """dg/dc (Body order, held rows zero): 2 J^T dr/dc_m, every row linear in a cost (dr/dc_m exact by differences)."""
    held, (turn, costs) = len(problem.slots), problem.costs
    rows = _dense(jacobian(problem, unknowns))
    slopes = []
    for mark in range(costs.size):
        changed = []
        for sign in (1.0, -1.0):
            moved = np.array(costs, dtype=float)
            moved[mark] += sign
            problem.costs = turn, moved
            changed.append(np.asarray(problem.residuals(unknowns), dtype=float))
        slopes.append(to_body(2 * rows.T @ ((changed[0] - changed[1]) / 2), held))
    problem.costs = turn, costs
    found = np.stack(slopes, axis=1)
    found[pinned.held] = 0.0
    return found


def _cost_slopes(tail, ends, step):
    """`goal_weights`' derivative (costs, tail) at `tail` by central differences."""
    columns = []
    for unknown in range(tail.size):
        up, down = tail.copy(), tail.copy()
        up[unknown] += step
        down[unknown] -= step
        columns.append((goal_weights(up, ends) - goal_weights(down, ends)) / (2 * step))
    return np.stack(columns, axis=1)


def sited_problem_at(problem, columns, trusted, ends):
    """A `problem_at` moving one built Problem in place, no rebuild (B3g): level 1's point `outer` reaches level 2
    only through the Fitting's marker sites and the markers' goal weights (its calibration is theta-free, measured
    2026-10-30), laid by `columns` (`_outer.picked_columns`, theta -> level 3's outer: each site's offset, the
    landmarks' trusts, then end weight and marker goal) about `trusted` (that outer at the base), the last `ends`
    sites the group ends weighed as `TapedSites._weighed` weighs them."""
    fitting = problem.fitting
    body_pos, start = fitting.base
    sites = len(fitting.mark_sites)

    def placed(moved):
        """The Problem with its sites and costs at level 3's outer `moved`."""
        site_pos = start.copy()
        site_pos[fitting.mark_sites] += (moved - trusted)[:3 * sites].reshape(-1, 3)
        fitting.base = body_pos, site_pos
        problem.costs = problem.costs[0], goal_weights(moved[3 * sites:], ends)
        return problem

    def at(outer):
        """The Problem with its sites and costs at level 1's `outer`."""
        return placed(np.asarray(trusted, dtype=float) + columns @ np.asarray(outer, dtype=float))
    placed.trusted, placed.ends = np.asarray(trusted, dtype=float), ends
    at.placed = placed
    return at


def turned_frame_sites(fitting, moves, work):
    """`work()` with each group's calibration site in `moves` ({group: body-side rad}) turned as the recalibrated
    TABLE turns it: the site holds R_cal^T (wxyz), so R_cal -> R_cal exp([w]x) makes it exp(-[w]x) R_cal^T (level 2's
    turn rows read it; `sited_problem_at` moves no site turn); the quats are put back after."""
    from scipy.spatial.transform import Rotation
    quats = fitting.model.site_quat
    kept = quats.copy()
    for group, turn in moves.items():
        site = fitting.frame_sites[fitting.groups.index(group)]
        quats[site] = (Rotation.from_rotvec(-np.asarray(turn)) * Rotation.from_quat(
            kept[site], scalar_first=True)).as_quat(scalar_first=True)
    try:
        return work()
    finally:
        quats[:] = kept


def goal_weights(tail, ends):
    """Each marker's place cost from the landmarks' trusts, end weight and marker goal (`fit._frames.weights` with the
    group ends' trust end weight times the landmarks' mean, as `fit.fitting` lays it)."""
    trusts, end_weight, goal = tail[:-2], tail[-2], tail[-1]
    every = np.concatenate([trusts, np.full(ends, end_weight * trusts.mean())])
    return np.sqrt(goal * every / max(every.sum(), 1e-12))


def level2_arrow(problem, jacobian, solved, kept, differenced, step):
    """`arrow_hessian`'s blocks of level 2's pinned gradient at `solved` (Problem order) in Body order, off J and r in
    place of a gradient call per constant: a frame's rows read only its pose and the constants, so one pose coordinate
    of every frame stepped together gives each frame's couplings (its rows' J_c^T r, differenced); the constants enter
    the rows linearly but for `differenced` (the inside joints' slots), so the corner is J_c^T J_c, its `differenced`
    rows and columns central differences. Held entries (`pinned_mask`) keep a unit row and column, as `Pinned`."""
    held, frames, width = len(problem.slots), len(problem.path), problem.width
    blocks, couplings = _pose_steps(problem, jacobian, solved, step)
    rows = _dense(jacobian(problem, solved))[:, :held]
    corner = rows.T @ rows
    for constant in differenced:
        up, down = np.array(solved, dtype=float), np.array(solved, dtype=float)
        up[constant] += step
        down[constant] -= step
        change = (_gradient(problem, jacobian, up) - _gradient(problem, jacobian, down)) / (2 * step)
        corner[:, constant] = corner[constant, :] = change[:held]
    mask = pinned_mask(problem, solved, kept).astype(bool)
    return _masked(blocks, couplings, 0.5 * (corner + corner.T), mask[:frames * width].reshape(frames, width),
                   mask[frames * width:])


def _pose_steps(problem, jacobian, solved, step):
    """The frame blocks (frames, width, width) and couplings (frames, width, constants) off one pose coordinate of
    every frame stepped together, a frame's couplings its own rows' J_c^T r."""
    held, frames, width = len(problem.slots), len(problem.path), problem.width
    blocks, couplings = np.zeros((frames, width, width)), np.zeros((frames, width, held))
    for coordinate in range(width):
        moved = []
        for sign in (1.0, -1.0):
            point = np.array(solved, dtype=float)
            point[held + np.arange(frames) * width + coordinate] += sign * step
            moved.append(_frame_products(problem, jacobian, point))
        blocks[:, :, coordinate] = (moved[0][0] - moved[1][0]) / (2 * step)
        couplings[:, coordinate, :] = (moved[0][1] - moved[1][1]) / (2 * step)
    return blocks, couplings


def _frame_products(problem, jacobian, point):
    """At `point`: each frame's pose gradient (frames, width) and its own rows' constants gradient (frames, held)."""
    held, frames, width = len(problem.slots), len(problem.path), problem.width
    rows, residuals = _dense(jacobian(problem, point)), np.asarray(problem.residuals(point), dtype=float)
    per = (residuals.size - held) // frames
    framed = rows[:frames * per, :held] * residuals[:frames * per, None]
    whole = rows.T @ residuals
    return whole[held:].reshape(frames, width), framed.reshape(frames, per, held).sum(axis=1)


def _gradient(problem, jacobian, point):
    """J^T r at `point` (Problem order)."""
    return _dense(jacobian(problem, point)).T @ np.asarray(problem.residuals(point), dtype=float)


def _dense(matrix):
    """`matrix` as a dense array (the card's Jacobian is sparse)."""
    return np.asarray(matrix.toarray() if hasattr(matrix, "toarray") else matrix, dtype=float)


def _masked(blocks, couplings, corner, held_poses, held_constants):
    """The blocks with each held entry's row and column zero but a unit diagonal (`Pinned`'s spring)."""
    blocks[held_poses] = 0.0
    blocks.transpose(0, 2, 1)[held_poses] = 0.0
    frame, coordinate = np.nonzero(held_poses)
    blocks[frame, coordinate, coordinate] = 1.0
    couplings[held_poses] = 0.0
    couplings[:, :, held_constants] = 0.0
    corner[held_constants] = 0.0
    corner[:, held_constants] = 0.0
    corner[np.nonzero(held_constants)[0], np.nonzero(held_constants)[0]] = 1.0
    return blocks, couplings, corner
