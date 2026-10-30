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
