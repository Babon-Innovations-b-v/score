"""A four-legged skeleton's legs and its walk, worked out in plain numpy (job characters-full, 2026-10-09). UniRig
names no bone, so the legs are found from the skeleton's shape: the chains that end lowest.

    chains = leg_chains(heads, parents, up)               # the four legs, each its joints from the hip down
    named = name_legs(chains, heads, forward, side)       # front_left, front_right, back_left, back_right
    forward_offset, lift = foot_path(phase, stride, lift) # one foot's place in its cycle

The walk is the four-beat walk of a dog (back left, front left, back right, front right, a quarter of a cycle apart),
each foot on the ground for DUTY of the cycle; the body stays over its node and the feet move under it (the travel is
taken off, as the people's clips do).
"""
import numpy as np

import spine

# How much of each end of the body is looked at to tell the head from the tail: the head end reaches higher.
END_SHARE = 0.25
# A leg's foot ends no higher than this share of the skeleton's height above its lowest joint.
FOOT_SHARE = 0.2
# The four-beat walk: when in the cycle each foot lands, and how much of the cycle it stands.
PHASES = {"back_left": 0.0, "front_left": 0.25, "back_right": 0.5, "front_right": 0.75}
DUTY = 0.7


def forward_axis(points, up=(0.0, 0.0, 1.0)):
    """The standing body's level long axis pointing to the head, as a unit vector: of its two ends, the head's reaches
    higher (a head held up against a tail held out)."""
    points = np.asarray(points, np.float64)
    up = np.asarray(up, np.float64)
    centre, along = spine.horizontal_axis(points, up)
    position = (points - centre) @ along
    low, high = position.min(), position.max()
    reach = (high - low) * END_SHARE
    height = points @ up
    if height[position <= low + reach].max() > height[position >= high - reach].max():
        along = -along
    return along


def children(parents):
    """Each joint's children, by index; a root's parent is -1."""
    found = {joint: [] for joint in range(len(parents))}
    for joint, parent in enumerate(parents):
        if parent >= 0:
            found[parent].append(joint)
    return found


def chain_to(leaf, parents, below):
    """The joints from the first one below a branch down to `leaf`: the limb that ends there."""
    chain = [leaf]
    while parents[chain[-1]] >= 0 and len(below[parents[chain[-1]]]) == 1:
        chain.append(parents[chain[-1]])
    return list(reversed(chain))


def leg_chains(heads, parents, up=(0.0, 0.0, 1.0), count=4):
    """The `count` limbs whose last joint is lowest, each at least two joints long and ending within FOOT_SHARE of
    the skeleton's height above its lowest joint; fewer when the skeleton has fewer."""
    heads = np.asarray(heads, np.float64)
    height = heads @ np.asarray(up, np.float64)
    reach = height.min() + FOOT_SHARE * (height.max() - height.min())
    below = children(parents)
    leaves = [joint for joint in range(len(parents)) if not below[joint] and height[joint] <= reach]
    chains = [chain_to(leaf, parents, below) for leaf in sorted(leaves, key=lambda joint: height[joint])]
    return [chain for chain in chains if len(chain) >= 2][:count]


def name_legs(chains, heads, forward, side):
    """The legs by name: the two nearer the head are the front, and of each pair the one on +`side` is the left."""
    heads = np.asarray(heads, np.float64)
    if len(chains) != 4:
        raise ValueError(f"a walk needs four legs, the skeleton has {len(chains)}")
    ahead = sorted(chains, key=lambda chain: -heads[chain[0]] @ np.asarray(forward, np.float64))
    named = {}
    for end, pair in (("front", ahead[:2]), ("back", ahead[2:])):
        left, right = sorted(pair, key=lambda chain: -heads[chain[0]] @ np.asarray(side, np.float64))
        named[f"{end}_left"], named[f"{end}_right"] = left, right
    return named


def foot_path(phase, stride, lift, duty=DUTY):
    """One foot's place at `phase` (0 to 1, from when it lands) of its cycle: how far ahead of its rest place and how
    high. On the ground it slides back under the body at an even pace, from half a stride ahead to half behind; in the
    air it swings forward on an eased path and rises to `lift` at the middle of the swing."""
    phase = phase % 1.0
    if phase < duty:
        return stride * (0.5 - phase / duty), 0.0
    swing = (phase - duty) / (1.0 - duty)
    eased = 0.5 - 0.5 * np.cos(np.pi * swing)
    return stride * (eased - 0.5), lift * np.sin(np.pi * swing)
