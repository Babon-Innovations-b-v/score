"""Room layout: no real example. Its input was a room's measured boxes from the room-from-picture experiment of
2026-10-02 (WORK/scene/<room>/boxes.json), which no store, cache or library entry kept, and score pruned its code on
2026-10-18 (commit 9c5930b1); the entry holds only the code and its tests' made-up boxes."""
from score.stages.library.demos import NoExample

ALGORITHM = "room_layout"


def made(inputs):
    raise NoExample("its measured boxes (the room-from-picture experiment of 2026-10-02) were never kept, and score "
                    "pruned the experiment on 2026-10-18; only its tests' made-up boxes remain")
