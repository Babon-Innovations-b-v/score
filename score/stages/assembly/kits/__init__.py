"""Kit pieces laid by their connectors (issue #93, under #55): score_lib's pipe, duct and rail pieces each carry
connector frames and a fit tolerance, the assembly lays two pieces joined at their connectors, and a check fails a
joint outside its tolerance. The method is marso-skills' (Apache-2.0): `marso-blender-kit`'s kit contract (connector
frames +Z out and +Y up, allowed mates and twists, a fit tolerance starting at 0.1 mm and 0.1 degree) and
`marso-blender-compose`'s snap_component.py (lay a piece by its connector frame, measure the position and angle error,
rigid unit-scale frames only, a loop's closure checked); reimplemented here on plain matrices, nothing copied.

A kit piece is the `piece.json` record of a score_lib kit entry (PIECE_SCHEMA), in the piece's own frame and the
house units (metres, degrees, Y up):

    {"schema": "score-kit-piece/1", "piece": "pipe_elbow_50",
     "connectors": {"a": {"at": [0, 0, 0], "out": [-1, 0, 0], "up": [0, 1, 0], "size": 0.05, "kind": "pipe",
                          "twists": [0, 90, 180, 270]}, "b": {...}},
     "fit": {"metres": 0.0001, "degrees": 0.1}}

A connector is a frame: `at` its seating point, `out` its outward mating normal (the frame's +z), `up` its alignment
way (+y, square to `out`), +x = up x out completing it right-handed; `size` its mating size across (a pipe's outside
diameter), `kind` its interface, `twists` the turns about `out` it may be mated at (degrees, [0] when not given).
`fit` is how far and how many degrees off a joint of the piece may be (FIT when not given). Two connectors mate when
their kinds are the same, their sizes the same within the tighter fit's metres and the twist one both allow: their
seating points coincide, their outs opposed and their ups aligned turned by that twist about the fixed one's out.

    piece(record)                                 the record checked: a Piece, or Unfit naming what is wrong
    joined(fixed, pose, at, moving, to, twist)    the 4x4 pose laying `moving` with its connector `to` mated to the
                                                  connector `at` of `fixed` laid at `pose`; Unfit when they cannot mate
    lay(pieces, joints, root, pose)               {instance: pose}: `root` at `pose`, every other instance laid by the
                                                  first joint reaching it from what is laid; a joint between two laid
                                                  instances closes a loop and is only checked
    joint_faults(pieces, laid, joints)            [(joint, what is wrong, measure or None)]: the joint check

`pieces` is {instance: Piece}, a `joint` (instance, connector, instance, connector, twist degrees). Pure numpy.
"""
from dataclasses import dataclass

import numpy as np

PIECE_SCHEMA = "score-kit-piece/1"
# Marso's starting tolerance for a metre-scale visual kit: scene alignment, never a manufacturing claim.
FIT = {"metres": 0.0001, "degrees": 0.1}
# How far a record's `up` may lean off square to its `out` (cosine), and a laid pose off rigid (its basis's Gram
# matrix off identity, its determinant off 1): a scaled, sheared or mirrored pose has no connector frame.
SQUARE = 1e-6
RIGID = 1e-5
# Turning a fixed connector's frame half round its +y: the mating frame, its out opposed and its up kept.
FLIP = np.diag([-1.0, 1.0, -1.0, 1.0])


class Unfit(ValueError):
    """A piece record off its schema, or two connectors that cannot mate."""


@dataclass(frozen=True, eq=False)
class Connector:
    """One connector: its 4x4 frame in the piece's own frame, its mating size, interface kind and allowed twists."""
    frame: np.ndarray
    size: float
    kind: str
    twists: tuple


@dataclass(frozen=True, eq=False)
class Piece:
    """One kit piece: its name, {connector name: Connector} and its fit (metres, degrees)."""
    name: str
    connectors: dict
    metres: float
    degrees: float


def way(values, what):
    """`values` as a unit 3-vector; Unfit when it is not three finite numbers or has no length."""
    vector = np.asarray(values, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
        raise Unfit(f"{what}: {values!r} is not a 3-vector with a length")
    return vector / np.linalg.norm(vector)


def frame(at, out, up, what):
    """The connector frame: +z its out, +y its up, +x = up x out, its origin at `at`."""
    origin = np.asarray(at, dtype=float)
    if origin.shape != (3,) or not np.isfinite(origin).all():
        raise Unfit(f"{what}: at {at!r} is not a 3-vector")
    out_way, up_way = way(out, f"{what} out"), way(up, f"{what} up")
    if abs(out_way @ up_way) > SQUARE:
        raise Unfit(f"{what}: up {up!r} is not square to out {out!r}")
    matrix = np.eye(4)
    matrix[:3, 0], matrix[:3, 1], matrix[:3, 2], matrix[:3, 3] = np.cross(up_way, out_way), up_way, out_way, origin
    return matrix


def positive(value, what):
    """`value` as a float above 0; Unfit otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
        raise Unfit(f"{what}: {value!r} is not a number above 0")
    return float(value)


def connector(name, record):
    """One connector record checked."""
    what = f"connector {name}"
    if not isinstance(record.get("kind"), str) or not record["kind"]:
        raise Unfit(f"{what}: no interface kind")
    twists = record.get("twists", [0.0])
    if not twists or not all(isinstance(turn, (int, float)) and np.isfinite(turn) for turn in twists):
        raise Unfit(f"{what}: twists {twists!r} are not degrees")
    return Connector(frame=frame(record.get("at"), record.get("out"), record.get("up"), what),
                     size=positive(record.get("size"), f"{what} size"), kind=record["kind"],
                     twists=tuple(float(turn) % 360.0 for turn in twists))


def piece(record):
    """A kit piece record checked: a Piece, or Unfit naming the first thing off PIECE_SCHEMA."""
    if record.get("schema") != PIECE_SCHEMA:
        raise Unfit(f"schema {record.get('schema')!r}, this reader knows {PIECE_SCHEMA!r}")
    if not isinstance(record.get("piece"), str) or not record["piece"]:
        raise Unfit("no piece name")
    connectors = record.get("connectors") or {}
    if not connectors:
        raise Unfit(f"{record['piece']}: no connectors")
    fit = {**FIT, **(record.get("fit") or {})}
    return Piece(name=record["piece"], connectors={name: connector(name, held) for name, held in connectors.items()},
                 metres=positive(fit["metres"], "fit metres"), degrees=positive(fit["degrees"], "fit degrees"))


def turn_about_out(degrees):
    """The 4x4 turn of `degrees` about a frame's own +z."""
    angle = np.radians(degrees)
    matrix = np.eye(4)
    matrix[:2, :2] = [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    return matrix


def off_twist(degrees, allowed):
    """Degrees from `degrees` to the nearest of `allowed`, round the circle."""
    return min(abs((degrees - turn + 180.0) % 360.0 - 180.0) for turn in allowed)


def mismatch(first, second, twist, metres, degrees):
    """Why two connectors cannot mate at `twist`, or None: another kind, another size, a twist either refuses."""
    if first.kind != second.kind:
        return f"kinds {first.kind} and {second.kind}"
    if abs(first.size - second.size) > metres:
        return f"sizes {first.size:g} and {second.size:g} m"
    if off_twist(twist, first.twists) > degrees or off_twist(twist, second.twists) > degrees:
        return f"twist {twist:g} degrees not allowed"
    return None


def joined(fixed, pose, at, moving, to, twist=0.0):
    """The pose laying `moving` with its connector `to` mated to connector `at` of `fixed` laid at `pose`, turned
    `twist` degrees about the fixed connector's out; Unfit when the two connectors cannot mate."""
    first, second = fixed.connectors[at], moving.connectors[to]
    why = mismatch(first, second, twist, min(fixed.metres, moving.metres), min(fixed.degrees, moving.degrees))
    if why:
        raise Unfit(f"{fixed.name}.{at} and {moving.name}.{to}: {why}")
    return pose @ first.frame @ turn_about_out(twist) @ FLIP @ np.linalg.inv(second.frame)


def lay(pieces, joints, root, pose=None):
    """{instance: pose}: `root` at `pose` (identity when None), then each instance a joint reaches from one laid,
    laid by that joint, until no joint lays another; an instance no joint reaches is not laid."""
    laid = {root: np.eye(4) if pose is None else np.asarray(pose, dtype=float)}
    grew = True
    while grew:
        grew = False
        for first, at, second, to, twist in joints:
            for fixed, held, moving, mates in ((first, at, second, to), (second, to, first, at)):
                if fixed in laid and moving not in laid:
                    laid[moving] = joined(pieces[fixed], laid[fixed], held, pieces[moving], mates, twist)
                    grew = True
    return laid


def rigid(pose):
    """Whether a laid pose turns and moves only: its basis orthonormal, not mirrored, unit scale."""
    basis = np.asarray(pose, dtype=float)[:3, :3]
    return (abs(np.linalg.det(basis) - 1.0) < RIGID and np.allclose(basis.T @ basis, np.eye(3), atol=RIGID)
            and np.allclose(np.asarray(pose)[3], [0.0, 0.0, 0.0, 1.0], atol=RIGID))


def frames_apart(first, second):
    """Degrees between two rigid frames' turns."""
    cosine = (np.trace(first[:3, :3].T @ second[:3, :3]) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def joint_faults(pieces, laid, joints):
    """[(joint, what is wrong, measure or None)] over every joint, laid by it or closing a loop: an end not laid, a
    pose not rigid, connectors that cannot mate, seating points apart by more than the tighter fit's metres, or the
    mated frame off the fixed one's mating frame by more than its degrees (the measure metres, degrees or None)."""
    faults = []
    for first, at, second, to, twist in joints:
        name = f"{first}.{at}-{second}.{to}"
        missing = [instance for instance in (first, second) if instance not in laid]
        if missing:
            faults.append((name, f"{', '.join(missing)} not laid", None))
            continue
        bent = [instance for instance in (first, second) if not rigid(laid[instance])]
        if bent:
            faults.append((name, f"{', '.join(bent)} laid scaled, sheared or mirrored", None))
            continue
        fixed, moving = pieces[first], pieces[second]
        metres, degrees = min(fixed.metres, moving.metres), min(fixed.degrees, moving.degrees)
        why = mismatch(fixed.connectors[at], moving.connectors[to], twist, metres, degrees)
        if why:
            faults.append((name, why, None))
            continue
        seat = laid[first] @ fixed.connectors[at].frame
        mated = laid[second] @ moving.connectors[to].frame
        apart = float(np.linalg.norm(mated[:3, 3] - seat[:3, 3]))
        if apart > metres:
            faults.append((name, f"seats {apart * 1000:.3f} mm apart, fit {metres * 1000:g} mm", apart))
        turned = frames_apart(seat @ turn_about_out(twist) @ FLIP, mated)
        if turned > degrees:
            faults.append((name, f"frames {turned:.3f} degrees off, fit {degrees:g}", turned))
    return faults
