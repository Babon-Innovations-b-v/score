"""Kit pieces laid by their connectors (kits/__init__.py): a straight pipe and a 90 degree elbow joined at their
connectors land where the frames put them (worked out by hand), a square loop of four of each closes, and the joint
check fails a joint outside the tighter piece's fit, both ways round the 0.1 mm and 0.1 degree limit.

Breaks (applied once, seen red, reverted): joined leaving out the mating flip (`@ FLIP` dropped) turns it red (the
elbow laid inside the straight, its far end at (0.9, 0, -0.1)); joint_faults taking the looser fit (`min(fixed.metres,
moving.metres)` -> `max(...)` in joint_faults) turns it red (the 0.2 mm loop passes the elbow's 0.1 mm); frames_apart
measuring nothing (`return 0.0`) turns it red (the joint turned 0.2 degrees passes); mismatch ignoring sizes (its
size test -> `if False:`) turns it red (a 50 mm pipe mates a 60 mm one); rigid passing every pose (`return True`)
turns it red (a pose scaled by 1.01 is checked as laid); frame accepting a lean (`> SQUARE` -> `> 1.0`) turns it red
(an up 45 degrees off its out is read).
"""
import numpy as np
import pytest

from score.stages.assembly import kits

STRAIGHT = 1.0
RADIUS = 0.1
EVERY_QUARTER = [0, 90, 180, 270]


def pipe(name, length=STRAIGHT, size=0.05, fit=None):
    """A straight pipe along its own +x, its ends a (out -x) and b (out +x)."""
    end = {"up": [0, 1, 0], "size": size, "kind": "pipe", "twists": EVERY_QUARTER}
    record = {"schema": kits.PIECE_SCHEMA, "piece": name,
              "connectors": {"a": {**end, "at": [0, 0, 0], "out": [-1, 0, 0]},
                             "b": {**end, "at": [length, 0, 0], "out": [1, 0, 0]}}}
    if fit:
        record["fit"] = fit
    return kits.piece(record)


def elbow():
    """A 90 degree elbow: in at its origin heading +x (a, out -x), out at (RADIUS, 0, RADIUS) heading +z (b)."""
    end = {"up": [0, 1, 0], "size": 0.05, "kind": "pipe", "twists": EVERY_QUARTER}
    return kits.piece({"schema": kits.PIECE_SCHEMA, "piece": "elbow_50", "fit": {"metres": 0.0001, "degrees": 0.1},
                       "connectors": {"a": {**end, "at": [0, 0, 0], "out": [-1, 0, 0]},
                                      "b": {**end, "at": [RADIUS, 0, RADIUS], "out": [0, 0, 1]}}})


def square(first_length):
    """Four straights and four elbows round a square, the first straight `first_length` long, every joint laid in
    order and the last elbow's b closing on the first straight's a."""
    pieces, joints, before = {}, [], None
    for corner in range(4):
        pieces[f"s{corner}"] = pipe("pipe_50", first_length if corner == 0 else STRAIGHT,
                                    fit={"metres": 0.001, "degrees": 1.0})
        pieces[f"e{corner}"] = elbow()
        if before:
            joints.append((before, "b", f"s{corner}", "a", 0.0))
        joints.append((f"s{corner}", "b", f"e{corner}", "a", 0.0))
        before = f"e{corner}"
    joints.append(("e3", "b", "s0", "a", 0.0))
    return pieces, joints


def far_end(pieces, laid, instance, connector):
    """The connector's world frame."""
    return laid[instance] @ pieces[instance].connectors[connector].frame


def test_two_pieces_join_only_within_their_fit():
    # Laid by hand: the elbow on the straight's b at (1, 0, 0) turns +x to +z, so the second straight starts at
    # (1.1, 0, 0.1) and its far end stands at (1.1, 0, 1.1) heading +z.
    pieces = {"s0": pipe("pipe_50"), "e0": elbow(), "s1": pipe("pipe_50")}
    joints = [("s0", "b", "e0", "a", 0.0), ("e0", "b", "s1", "a", 0.0)]
    laid = kits.lay(pieces, joints, "s0")
    end = far_end(pieces, laid, "s1", "b")
    assert np.allclose(end[:3, 3], [1.1, 0, 1.1]) and np.allclose(end[:3, 2], [0, 0, 1])
    assert kits.joint_faults(pieces, laid, joints) == []

    # A square loop closes; its first straight 0.05 mm long passes the elbows' 0.1 mm, 0.2 mm long fails it, though
    # the straights' own fit is 1 mm (the tighter piece's fit holds), measured at the closing joint.
    for extra, closes in ((0.00005, True), (0.0002, False)):
        pieces, joints = square(STRAIGHT + extra)
        faults = kits.joint_faults(pieces, kits.lay(pieces, joints, "s0"), joints)
        assert (faults == []) is closes, faults
        if not closes:
            assert faults[0][0] == "e3.b-s0.a" and faults[0][2] == pytest.approx(0.0002, abs=1e-9)

    # A joint turned about its out by 0.05 degrees passes, by 0.2 degrees fails on its frames.
    pieces = {"s0": pipe("pipe_50"), "e0": elbow()}
    joints = [("s0", "b", "e0", "a", 0.0)]
    for degrees, passes in ((0.05, True), (0.2, False)):
        laid = kits.lay(pieces, joints, "s0")
        laid["e0"] = laid["e0"] @ kits.turn_about_out(degrees)
        faults = kits.joint_faults(pieces, laid, joints)
        assert (faults == []) is passes, faults
        if not passes:
            assert faults[0][2] == pytest.approx(0.2, abs=1e-6)

    # Twisted 90 degrees, which both allow, the joint passes; a 50 mm pipe never mates a 60 mm one, nor at a twist of
    # 45 degrees; a pose scaled 1 % is no frame.
    laid = kits.lay(pieces, [("s0", "b", "e0", "a", 90.0)], "s0")
    assert kits.joint_faults(pieces, laid, [("s0", "b", "e0", "a", 90.0)]) == []
    wide = {"s0": pipe("pipe_50"), "w": pipe("pipe_60", size=0.06)}
    with pytest.raises(kits.Unfit, match="sizes"):
        kits.joined(wide["s0"], np.eye(4), "b", wide["w"], "a")
    laid = {"s0": np.eye(4), "w": kits.joined(wide["s0"], np.eye(4), "b", pipe("pipe_50"), "a")}
    assert "sizes" in kits.joint_faults(wide, laid, [("s0", "b", "w", "a", 0.0)])[0][1]
    with pytest.raises(kits.Unfit, match="twist"):
        kits.joined(pieces["s0"], np.eye(4), "b", pieces["e0"], "a", 45.0)
    laid = kits.lay(pieces, joints, "s0")
    laid["e0"] = laid["e0"] @ np.diag([1.01, 1.01, 1.01, 1.0])
    assert "scaled" in kits.joint_faults(pieces, laid, joints)[0][1]

    # A record off its schema is refused: an up leaning off its out, no size, another schema.
    leaning = {"schema": kits.PIECE_SCHEMA, "piece": "bad", "connectors": {
        "a": {"at": [0, 0, 0], "out": [1, 0, 0], "up": [1, 1, 0], "size": 0.05, "kind": "pipe"}}}
    with pytest.raises(kits.Unfit, match="square"):
        kits.piece(leaning)
    with pytest.raises(kits.Unfit, match="size"):
        kits.piece({**leaning, "connectors": {"a": {**leaning["connectors"]["a"], "up": [0, 1, 0], "size": 0}}})
    with pytest.raises(kits.Unfit, match="schema"):
        kits.piece({**leaning, "schema": "score-kit-piece/0"})
