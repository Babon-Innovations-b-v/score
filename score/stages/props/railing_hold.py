"""A thin straight railing's build held across to its row's height (thin_straight.held_across, as this module's
`held` puts in its place): the greenhouse's 9.4 m railing (count 5, its row 9.435 by 0.1 by 1 m), curving round a
floor drawn from above, showed the floor's depth as its picture's height and stood 4.5 m tall, while held_across left
every railing at its picture's height (2026-11-11). Held, its reach across (`made` measured whole, as a straight
build's is) is its row's tall side at most; the likeness row sees it unheld (thin_straight.view undoes as_built), so
its outline is its picture's still (0.679 both ways). A railing that climbs a flight (`climbs`) keeps its rise: the
stairwell's stair railing, on the staircase, held to its 1 m row from its 3.1 m rise strayed 0.062 from its swept fit
(likeness_row.SWEPT_LIMIT 0.04).

Apart from thin_straight.py so that only the rows that build or see a code build take it into their keys: pixal
and likeness declare it as a file of theirs (FILES, added in the framework's table, score/stages/__init__.py, which
imports it and so installs it in every process that runs a row), and prepare's predict imports it. thin_straight
is read by the scene record's writer and the surface parts too, and an edit there moved 13 paid rows (body faces,
sim body, settle, peels, ...) that never build a railing; pixal_row is read by the crops' look through the prop
route's table, and the table's make wrappers keep a row's code version as it was. Importing this module puts
`held` in thin_straight's place (`install`), once a process."""
import re

import numpy as np

import score.stages.props.thin_straight as thin_straight

# What a railing climbs along, a word of its name, noun or anchor: its picture's rise is its flight's.
CLIMBED = frozenset(("stair", "stairs", "staircase", "stairway", "steps", "ramp"))
# The rows that build or see a code build, and the file each declares so its key takes this module in.
ROWS = ("pixal", "likeness")
FILES = {"railing hold": "{repo}/score/stages/props/railing_hold.py"}
UNHELD = thin_straight.held_across  # thin_straight's own: every railing left at its picture's height


def climbs(row):
    """Whether a row climbs a flight (CLIMBED): a word of its name, noun or anchor (`on:<id>`) names one."""
    words = re.findall(r"[a-z]+", f"{row.get('name') or ''} {row.get('noun') or ''} {row.get('anchor') or ''}".lower())
    return bool(CLIMBED & set(words))


def held(row, alpha, made=None):
    """thin_straight.held_across, but a slender railing that does not climb is held across whole to its row's height
    (the inventory's tall side): its build (`made`, its path_build, built here when not given), laid along its row
    (`slanted` undone), measured across its run (y, or z where axis_turn stands it), at most one."""
    if (thin_straight.profile(row) != "railing" or climbs(row) or alpha is None or not alpha.any()
            or not thin_straight.slender(row["size"])):
        return UNHELD(row, alpha, made)
    kept = thin_straight.pieces(alpha)
    turn = thin_straight.axis_turn(row, alpha)
    across = 2 if turn != thin_straight.slant(kept) else 1  # stood upright by axis_turn's quarter turn: across is z
    made = thin_straight.path_build(row, alpha, turn) if made is None else made
    laid = made.vertices @ np.linalg.inv(thin_straight.slanted(row, alpha))[:3, :3].T
    hold = np.eye(4)
    hold[across, across] = min(1.0, float(row["size"][2]) / max(float(np.ptp(laid[:, across])), 1e-9))
    return hold


def install():
    """`held` in thin_straight's place (its build, as_built and view call held_across by name)."""
    thin_straight.held_across = held


install()
