# Copyright (c) 2025-2026, The Isaac Lab Arena Project Developers (https://github.com/isaac-sim/IsaacLab-Arena/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
# Modified for SCORE, 2026-10-26: a numpy port of IsaacLab-Arena's relation solver, from
# isaac-sim/IsaacLab-Arena commit 38b200cdb4b506ee8329e89480c6479cae5bc2dc, files
# isaaclab_arena/relations/loss_primitives.py (single_boundary_linear_loss, linear_band_loss,
# single_point_linear_loss, interval_overlap_axis_loss), relation_loss_strategies.py (OnLossStrategy's band,
# AtPositionLossStrategy, NoCollisionLossStrategy.compute_loss_batched), no_overlap_aabb.py
# (compute_no_overlap_loss_aabb's directed pairs), relation_solver.py (RelationSolver.solve's Adam loop) and
# object_placer.py with relation_solver_params.py and object_placer_params.py (seeded candidates ranked valid first,
# then by loss, and their defaults). Changed: torch autograd replaced by the losses' own gradients (a tie in a
# min or max split evenly, as torch's), the floor plan's two axes only (no z, no yaw, no mesh collision), every
# candidate solved side by side as one array, and the anchor's On relation given as a box to stay inside.
"""The relation solver (IsaacLab-Arena's, ported to numpy): boxes on a floor parted by gradient descent on a loss of
their overlaps (each with the others and with fixed obstacles, NoCollision), their staying inside a box (On's band)
and their distance from their own spots (AtPosition, soft), from several seeded starts; the best start's boxes."""
import numpy

NO_COLLISION_SLOPE = 10000.0  # RelationSolver: overlap avoidance dominates every relation
ON_SLOPE = 100.0  # _default_strategies: On
MAX_ITERS = 600  # RelationSolverParams
LEARNING_RATE = 0.01  # RelationSolverParams: Adam's
BETAS = (0.9, 0.999)  # torch.optim.Adam's defaults
EPSILON = 1e-8
ATTEMPTS = 10  # ObjectPlacerParams.max_placement_attempts
TOLERANCE = 1e-3  # metres a validated box may still overlap or stand outside


def tie_split(first, second):
    """d min(first, second) / d first: 1 where first is smaller, 0.5 at a tie, else 0 (torch's minimum)."""
    return numpy.where(first < second, 1.0, numpy.where(first == second, 0.5, 0.0))


def axis_overlaps(low, high, other_low, other_high):
    """(overlap length, its gradient by the subject's position) per axis of each subject box [low, high] with each
    obstacle box [other_low, other_high], broadcast: interval_overlap_axis_loss before its ReLU, and d/d position of
    min(high, other_high) - max(low, other_low) (the obstacle held still: detached)."""
    length = numpy.minimum(high, other_high) - numpy.maximum(low, other_low)
    slope = tie_split(high, other_high) - tie_split(other_low, low)
    return length, slope


def overlap_loss(low, high, other_low, other_high, mask, clearance):
    """(loss per candidate, its gradient by each subject's position): NoCollision's slope times the overlap area of
    each subject box with each obstacle box grown by `clearance`, summed over the pairs `mask` allows.
    low, high: (C, N, 2); other_low, other_high: (C, M, 2); mask: (N, M)."""
    length, slope = axis_overlaps(low[:, :, None, :], high[:, :, None, :], other_low[:, None, :, :] - clearance,
                                  other_high[:, None, :, :] + clearance)
    positive = numpy.maximum(length, 0.0)
    area = positive[..., 0] * positive[..., 1] * mask
    across = numpy.stack([positive[..., 1], positive[..., 0]], axis=-1)  # the other axis' length
    gradient = slope * (length > 0) * across * mask[..., None]
    return NO_COLLISION_SLOPE * area.sum(axis=(1, 2)), NO_COLLISION_SLOPE * gradient.sum(axis=2)


def band_loss(spots, lower, upper, slope):
    """(loss per candidate, gradient): linear_band_loss, zero for a spot inside [lower, upper], `slope` a metre out."""
    loss = slope * (numpy.maximum(lower - spots, 0.0) + numpy.maximum(spots - upper, 0.0))
    gradient = slope * (numpy.where(spots < lower, -1.0, 0.0) + numpy.where(spots > upper, 1.0, 0.0))
    return loss.sum(axis=(1, 2)), gradient


def point_loss(spots, targets, slope):
    """(loss per candidate, gradient): single_point_linear_loss, `slope` a metre from the target each way."""
    return (slope * numpy.abs(spots - targets)).sum(axis=(1, 2)), slope * numpy.sign(spots - targets)


class Problem:
    """Boxes to place: their sizes (N, 2), targets (N, 2: their low corners' spots), the target's slope (one, or one
    a box), the box they stay inside [low x, low y, high x, high y], the fixed obstacles (M, 4) as [low x, low y,
    high x, high y], which obstacles each box avoids (N, M), which box pairs avoid each other (N, N), the clearance."""

    def __init__(self, sizes, targets, soft, inside, obstacles, avoids, apart, clearance):
        self.sizes, self.targets = numpy.asarray(sizes, dtype=float), numpy.asarray(targets, dtype=float)
        self.soft = numpy.broadcast_to(numpy.asarray(soft, dtype=float), (len(self.sizes),))[:, None]
        self.inside = numpy.asarray(inside, dtype=float)
        self.obstacles = numpy.asarray(obstacles, dtype=float).reshape(-1, 4)
        self.avoids = numpy.asarray(avoids, dtype=float).reshape(len(self.sizes), len(self.obstacles))
        self.apart = numpy.asarray(apart, dtype=float) * (1.0 - numpy.eye(len(self.sizes)))
        self.clearance = float(clearance)


def loss_and_gradient(problem, spots):
    """(total loss per candidate, its gradient by every box's spot) of `spots` (C, N, 2): the boxes' overlaps with
    each other (each pair both ways, the other held still), with the obstacles, the band and the soft targets."""
    low, high = spots, spots + problem.sizes
    loss, gradient = overlap_loss(low, high, low, high, problem.apart, problem.clearance)
    fixed_low = numpy.broadcast_to(problem.obstacles[None, :, :2], (len(spots), len(problem.obstacles), 2))
    fixed_high = numpy.broadcast_to(problem.obstacles[None, :, 2:], fixed_low.shape)
    more, more_gradient = overlap_loss(low, high, fixed_low, fixed_high, problem.avoids, problem.clearance)
    band, band_gradient = band_loss(spots, problem.inside[:2], problem.inside[2:] - problem.sizes, ON_SLOPE)
    pull, pull_gradient = point_loss(spots, problem.targets, problem.soft)
    return loss + more + band + pull, gradient + more_gradient + band_gradient + pull_gradient


def starts(problem, seed, attempts, spread):
    """The candidates' starting spots (C, N, 2): the targets, each candidate shaken by a seeded uniform draw up to
    `spread` metres times its number over the attempts (the first by a millimetre, so boxes on one spot part)."""
    generator = numpy.random.default_rng(seed)
    scale = numpy.maximum(spread * numpy.arange(attempts) / attempts, 0.001)
    shake = generator.uniform(-1.0, 1.0, (attempts, len(problem.sizes), 2)) * scale[:, None, None]
    return problem.targets[None] + shake


def descended(problem, spots):
    """`spots` after RelationSolver.solve's loop: Adam on the total loss for MAX_ITERS steps, stopping early once
    every candidate's loss is below the convergence threshold; (the spots, their losses)."""
    first, second = numpy.zeros_like(spots), numpy.zeros_like(spots)
    for step in range(1, MAX_ITERS + 1):
        loss, gradient = loss_and_gradient(problem, spots)
        if loss.max() < 1e-4:
            break
        first = BETAS[0] * first + (1 - BETAS[0]) * gradient
        second = BETAS[1] * second + (1 - BETAS[1]) * gradient ** 2
        unbiased = first / (1 - BETAS[0] ** step)
        spots = spots - LEARNING_RATE * unbiased / (numpy.sqrt(second / (1 - BETAS[1] ** step)) + EPSILON)
    return spots, loss_and_gradient(problem, spots)[0]


def valid(problem, spots):
    """Which candidates (C,) part every box from the others and from the obstacles it avoids, inside the band, each
    within TOLERANCE (the placement validation's no-overlap and On checks)."""
    low, high = spots, spots + problem.sizes
    clear = numpy.where(problem.apart > 0, 0.0, -numpy.inf)  # pairs left out never fail
    length, _ = axis_overlaps(low[:, :, None, :], high[:, :, None, :], low[:, None, :, :], high[:, None, :, :])
    apart = (length.min(axis=-1) + clear <= TOLERANCE).all(axis=(1, 2))
    blocked = numpy.where(problem.avoids > 0, 0.0, -numpy.inf)
    length, _ = axis_overlaps(low[:, :, None, :], high[:, :, None, :], problem.obstacles[None, None, :, :2],
                              problem.obstacles[None, None, :, 2:])
    free = (length.min(axis=-1) + blocked <= TOLERANCE).all(axis=(1, 2))  # all of nothing: True
    inside = ((low >= problem.inside[:2] - TOLERANCE) & (high <= problem.inside[2:] + TOLERANCE)).all(axis=(1, 2))
    return apart & free & inside


def solved(problem, seed=0, attempts=ATTEMPTS, spread=0.5):
    """(the best candidate's spots (N, 2), whether it is valid): ObjectPlacer.place's ranking, valid candidates
    first, then the lowest loss, the first of equals."""
    spots, losses = descended(problem, starts(problem, seed, attempts, spread))
    passing = valid(problem, spots)
    best = min(range(attempts), key=lambda number: (not passing[number], losses[number], number))
    return spots[best], bool(passing[best])
