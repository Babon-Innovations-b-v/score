"""The pieces of one real tuning body for `_taped.TapedSites` (#70, numpy only): MyoFullBody batched per frame is one
Newton model holding a copy of the body per frame, its joint_q every copy's coordinates in turn. `copied_couplings`
turns the card's projection (`fit/_card/_project.Projection`'s fields, MuJoCo coordinates) into `TapedSites`'
`couplings=` for that model."""
import numpy as np

ROOT_COORDS = 7  # a free root's coordinates (place, turn): MuJoCo's and Newton's differ only in the turn's order


def copied_couplings(follower_coord, leader_coord, follower_rest, leader_rest, poly, frozen_coord, solved_rows):
    """`TapedSites`' couplings (free_coord, follower_coord, leader_free, follower_rest, leader_rest, poly, base) for
    a body copied once per row of `solved_rows` (frames, nq: the card's solved joint_q, Newton's order, laid copy
    by copy). The pose is every copy's free coordinates in turn: not a follower, not frozen. A follower of a frozen
    leader is constant, so it stays at its solved value; a follower led by another follower is refused (the tape
    reads a leader off the pose only)."""
    rows = np.asarray(solved_rows, dtype=float)
    frames, size = rows.shape
    followers = [int(coord) for coord in follower_coord]
    frozen = {int(coord) for coord in frozen_coord}
    if any(0 <= int(leader) and int(leader) in followers for leader in leader_coord):
        raise ValueError("a follower led by another follower: the tape reads leaders off the pose only")
    if any(coord < ROOT_COORDS for coord in followers + sorted(frozen)):
        raise ValueError("a root coordinate coupled or frozen: MuJoCo's and Newton's root orders differ there")
    kept = [index for index, leader in enumerate(leader_coord) if int(leader) not in frozen]
    free = [coord for coord in range(size) if coord not in set(followers) | frozen]
    place = {coord: index for index, coord in enumerate(free)}
    copied = lambda values, step: np.concatenate([np.asarray(values) + copy * step for copy in range(frames)])
    leaders = [place[int(leader_coord[index])] if int(leader_coord[index]) >= 0 else -1 for index in kept]
    return (copied(free, size).astype(int),
            copied([followers[index] for index in kept], size).astype(int),
            np.concatenate([[lead + copy * len(free) if lead >= 0 else -1 for lead in leaders]
                            for copy in range(frames)]).astype(int),
            np.tile(np.asarray(follower_rest, dtype=float)[kept], frames),
            np.tile(np.asarray(leader_rest, dtype=float)[kept], frames),
            np.tile(np.asarray(poly, dtype=float).reshape(-1, 5)[kept], (frames, 1)),
            rows.reshape(-1))


def pose_of(couplings, solved_rows):
    """The free pose (every copy's free coordinates in turn) of `solved_rows` under `copied_couplings`' map."""
    return np.asarray(solved_rows, dtype=float).reshape(-1)[couplings[0]]


TURN = slice(3, 7)  # a copy's root turn (Newton's x, y, z, w) inside its free coordinates


def tangent_basis(quat):
    """Three orthonormal columns (4, 3) spanning the directions perpendicular to the unit quaternion `quat`."""
    unit = np.asarray(quat, dtype=float) / np.linalg.norm(quat)
    spans, _, _ = np.linalg.svd(np.eye(4) - np.outer(unit, unit))
    return spans[:, :3]


class RootTurns:
    """The inner pose with each copy's root turn as 3 tangent dofs instead of its 4 coordinates, so the inner Hessian
    has no direction along the quaternion's norm: a copy's turn is (q0 + E w) / |q0 + E w|, q0 the solved turn, E its
    `tangent_basis`, w = 0 at the solved pose. `per_copy` is one copy's free-coordinate count (`copied_couplings`)."""

    def __init__(self, pose, per_copy):
        self.full_pose = np.asarray(pose, dtype=float).copy()
        self.per_copy = int(per_copy)
        self.copies = self.full_pose.size // self.per_copy
        turns = self.full_pose.reshape(self.copies, self.per_copy)[:, TURN]
        self.anchors = turns / np.linalg.norm(turns, axis=1, keepdims=True)
        self.bases = np.stack([tangent_basis(turn) for turn in self.anchors])

    def reduced(self):
        """The solved pose in the chart: each copy's free coordinates with its turn's 4 replaced by w = 0's 3."""
        rows = self.full_pose.reshape(self.copies, self.per_copy)
        return np.concatenate([rows[:, :TURN.start], np.zeros((self.copies, 3)), rows[:, TURN.stop:]], axis=1).ravel()

    def _split(self, reduced):
        rows = np.asarray(reduced, dtype=float).reshape(self.copies, self.per_copy - 1)
        return rows[:, :TURN.start], rows[:, TURN.start:TURN.start + 3], rows[:, TURN.start + 3:]

    def full(self, reduced):
        """The pose `TapedSites` takes (every copy's 4 turn coordinates, unit) at a chart point."""
        head, tangents, tail = self._split(reduced)
        raw = self.anchors + np.einsum("cij,cj->ci", self.bases, tangents)
        return np.concatenate([head, raw / np.linalg.norm(raw, axis=1, keepdims=True), tail], axis=1).ravel()

    def pulled(self, reduced, gradient):
        """The chart's gradient at `reduced` from the full pose's `gradient` there (the chain rule through the
        normalised turn: (I - n n^T) / |raw| E per copy)."""
        head, tangents, tail = self._split(reduced)
        rows = np.asarray(gradient, dtype=float).reshape(self.copies, self.per_copy)
        raw = self.anchors + np.einsum("cij,cj->ci", self.bases, tangents)
        length = np.linalg.norm(raw, axis=1, keepdims=True)
        unit = raw / length
        along = rows[:, TURN] - unit * np.sum(unit * rows[:, TURN], axis=1, keepdims=True)
        turned = np.einsum("cij,ci->cj", self.bases, along / length)
        return np.concatenate([rows[:, :TURN.start], turned, rows[:, TURN.stop:]], axis=1).ravel()


class Pinned:
    """The inner unknowns with the bound-held entries kept in place, so every frame's block keeps one size: a held
    entry is read at its solved value whatever the inner point says (`whole`), and its gradient is the unit spring
    inner - solved (`gradient`), zero at the optimum with a unit row in H and no outer mix, so its derivative is zero
    and the free entries' is the one of the pose with it dropped. `held` a mask over `solved` (the inner point)."""

    def __init__(self, solved, held):
        self.solved = np.asarray(solved, dtype=float).copy()
        self.held = np.asarray(held, dtype=bool)

    def whole(self, inner):
        """`inner` with every held entry back at its solved value."""
        whole = np.array(inner, dtype=float)
        whole[self.held] = self.solved[self.held]
        return whole

    def gradient(self, inner, found):
        """`found` (the gradient at `whole(inner)`) with each held entry replaced by its spring inner - solved."""
        pinned = np.array(found, dtype=float)
        pinned[self.held] = np.asarray(inner, dtype=float)[self.held] - self.solved[self.held]
        return pinned
