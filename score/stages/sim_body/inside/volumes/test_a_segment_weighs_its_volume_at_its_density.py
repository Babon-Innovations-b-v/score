"""volumes: a closed box 0.2 x 1 x 0.1 m is filled to its volume (0.02 m3), cut between two bone lines into halves
of 0.01 m3 centred a quarter up and down, each with a solid's spread V (a2 + b2 + c2) / 12, and the halves weighed
at their densities share the mass as density times volume, each inertia's trace m (a2 + b2 + c2) / 6, and each half's
girth for its length is its 0.2 x 0.1 m section's width, sqrt(0.02) m, over 0.5 m (all worked out by hand). Pure: the
score venv runs it.

Breaks (each applied once, seen red, reverted), 2026-10-28:
- filled's `np.searchsorted(crossings, ys) % 2 == 1` made `== 0`: the outside filled, not the inside.
- shares' `nearer = away < best` made `nearer = away > best`: every cell to the farthest line.
- measured's `+ volume * cell ** 2 / 4` dropped: the cells' own spread lost (6.25e-8 m5 under a solid's).
- weighed's `2.0 * density(group)` made `density(group)`: half the inertia.
- (2026-11-01) slenderness's `/ length` at its end dropped: the width, not the width over the length.
- (2026-11-01) slenderness's `(GIRTH_MIDDLE[1] - GIRTH_MIDDLE[0]) * length` made `length`: the section read over the
  whole stretch while the cells are counted in its middle.

One box, filled, cut and weighed once; each half is a row (its line, its bone group at its density, its centre
height, its hand-worked mass), every measure of that half asserted on the one result.

Run: make tests TESTS=score/stages/sim_body/inside/volumes/test_a_segment_weighs_its_volume_at_its_density.py
"""
import pathlib
import sys

import numpy as np
import pytest

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import volumes  # noqa: E402

# A box from (0, 0, 0) to (0.2, 1, 0.1), its 12 faces.
CORNERS = np.array([[x, y, z] for x in (0, 0.2) for y in (0, 1.0) for z in (0, 0.1)])
FACES = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6],
                  [0, 6, 4], [1, 5, 7], [1, 7, 3]])
# Two bone lines up the box's middle: the lower half's (y 0 to 0.5) and the upper half's (0.5 to 1).
LINES = [[((0.1, 0.0, 0.05), (0.1, 0.5, 0.05))], [((0.1, 0.5, 0.05), (0.1, 1.0, 0.05))]]


# Each half: its line's index in LINES, its bone group (a thigh at 1.05 kg/l, a shin at 1.09), its centre's height,
# and its share of 21.4 kg by density times its 0.01 m3: 10.5 and 10.9 kg.
HALVES = [(0, "LeftLeg", 0.25, 10.5), (1, "LeftShin", 0.75, 10.9)]
# A solid's spread V (a2 + b2 + c2) / 12 at 0.01 m3, its trace per kg (a2 + b2 + c2) / 6, its girth for its length.
SPREAD = 2.5e-4  # 0.01 (0.04 + 0.25 + 0.01) / 12
TRACE_PER_KG = 0.05  # (0.04 + 0.25 + 0.01) / 6
GIRTH = np.sqrt(0.02) / 0.5


@pytest.fixture(scope="module")
def box():
    """The box filled, its cells shared between the two lines, each half measured and the halves weighed at 21.4 kg."""
    cells = volumes.filled(CORNERS, FACES)
    owner = volumes.shares(cells, LINES)
    found = volumes.measured(cells, owner, 2)
    return cells, owner, found, volumes.weighed([group for _, group, _, _ in HALVES], found, 21.4)


@pytest.mark.parametrize("line, group, height, kg", HALVES, ids=[group for _, group, _, _ in HALVES])
def test_a_segment_weighs_its_volume_at_its_density(box, line, group, height, kg):
    """The box fills to 0.02 m3 within one cell layer (1%); the half is 0.01 m3 centred at (0.1, height, 0.05), its
    spread 2.5e-4 m5 within 1e-9 (the cells fill the box exactly); weighed, its mass is kg within 1% and its trace
    0.05 m per kg within 0.2%; its girth for its length sqrt(0.2 x 0.1) / 0.5 = 0.2828 within 1%."""
    cells, owner, found, weighed = box
    volume, centre, spread = found[line]
    mass, _, trace = weighed[group]
    (start, end), = LINES[line]
    girth = volumes.slenderness(cells, owner, line, start, end)
    assert abs(len(cells) * volumes.CELL ** 3 - 0.02) < 2e-4, f"{len(cells)} cells"
    assert abs(volume - 0.01) <= 1e-4 and np.allclose(centre, [0.1, height, 0.05], atol=1e-3), \
        f"{group}: {volume} m3 at {centre}"
    assert abs(spread - SPREAD) <= 1e-9, f"{group}: spread {spread}"
    assert abs(mass - kg) <= 0.01 * kg and abs(trace - TRACE_PER_KG * mass) <= 0.002 * TRACE_PER_KG * mass, \
        f"{group}: {mass:.3f} kg, trace {trace:.5f}"
    assert abs(girth - GIRTH) <= 0.01 * GIRTH, f"{group}: girth for its length {girth:.4f}"
