"""A screen's picture is drawn from its seed alone (the same seed the same picture, another seed another), the seed
choosing the place's plan or a dashboard, only its glass, a frame's faint ink and its content's ink, the glass mostly
bare, and the screen recipe's mix: glass where nothing is lit, ink where it is, only the content glowing.

Breaks that turn it red (each applied once, seen red, reverted, 2026-11-06):
- content.levels: `rng = np.random.default_rng(int(seed))` -> `rng = np.random.default_rng(0)` (every seed one picture)
- content.levels: `if planned and chooses < 0.5:` -> `if False:` (no plan ever drawn)
- content.plan_drawing: the walls' loop dropped (a plan with no walls)
- content.channels: `return glass + lit * (ink - glass), lit * ink` -> `..., ink + 0 * lit` (the glass glowing)
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import content  # noqa: E402

# A square room 6 m on a side with one door in its south wall and one table: the picture's plan.
PLAN = {"outline": [[0, 0], [6, 0], [6, 6], [0, 6]],
        "walls": [{"from": [0, 0], "to": [6, 0]}, {"from": [6, 0], "to": [6, 6]}, {"from": [6, 6], "to": [0, 6]},
                  {"from": [0, 6], "to": [0, 0]}],
        "openings": [{"at": [3, 0], "wide": 1.0, "angle": 0.0}], "items": [["TABLE 1", 2.0, 2.0, 1.0, 1.0, "N"]]}
SIZE = (320, 200)


def test_a_screen_picture_is_drawn_from_its_seed_and_plan():
    one, again = content.levels(11, SIZE, PLAN), content.levels(11, SIZE, PLAN)
    assert np.array_equal(one, again)
    assert np.mean(one != content.levels(12, SIZE, PLAN)) > 0.02
    # the seed chooses: the plan drawn for some seeds (the picture differs from the same seed's without a plan), the
    # dashboard for others (the same)
    planned = [not np.array_equal(content.levels(seed, SIZE, PLAN), content.levels(seed, SIZE)) for seed in range(12)]
    assert any(planned) and not all(planned), planned
    seed = planned.index(True)
    drawn = content.levels(seed, SIZE, PLAN)
    # the plan sits in the box (0.01, TITLE + 0.01) to (0.66, 0.99), the room's 6 m fitted to 0.9 of its height:
    # the west wall's middle (x 0, y 3 m) at the box's middle height, 0.45 of its height left of its middle
    left, top, right, bottom = 0.01 * SIZE[0], (content.TITLE + 0.01) * SIZE[1], 0.66 * SIZE[0], 0.99 * SIZE[1]
    scale = 0.9 * (bottom - top) / 6
    wall = (int((left + right) / 2 - 3 * scale), int((top + bottom) / 2))
    assert drawn[wall[1], wall[0]] == 1.0, drawn[wall[1] - 2:wall[1] + 3, wall[0] - 2:wall[0] + 3]
    for found in (one, drawn, content.levels(5, SIZE)):
        assert set(np.unique(found).round(2)) <= {0.0, content.FAINT, content.ITEM_LIT, 1.0}
        assert 0.05 < float((found > 0).mean()) < 0.6, float((found > 0).mean())
    base, glow = content.channels([0.01, 0.02, 0.03], [0.2, 0.6, 0.8], one)
    bare, full = one == 0, one == 1
    assert np.allclose(base[bare], [0.01, 0.02, 0.03]) and np.allclose(base[full], [0.2, 0.6, 0.8])
    assert np.allclose(glow[bare], 0.0) and np.allclose(glow[full], [0.2, 0.6, 0.8])
