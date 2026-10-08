"""Checks of the expedition camp habitat's kit layout (camp_kit.py), plain python: every lining panel has its piece
inside and its gore outside, and the installed layout is the one the tool lays. (That its numbers are the game's own,
read back out of the GDScript, is checked in the game 2099, which has the GDScript.)"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import numpy  # noqa: F401
except ImportError:  # the gate's system python has no numpy: hand over to the prop environment
    import os
    import subprocess
    prop = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not prop.exists():
        print("skipped: no prop environment")
        sys.exit(0)
    sys.exit(subprocess.call([str(prop), __file__] + sys.argv[1:], env=dict(os.environ)))
import camp_kit  # noqa: E402

def test_every_panel_has_its_piece_inside_and_its_gore_outside():
    found = camp_kit.laid_out()
    kinds = [laid["kind"] for laid in found]
    every = [panel for dome in (camp_kit.DOOR_DOME, camp_kit.FAR_DOME) for panel in camp_kit.panels(dome)]
    inside = sum(kinds.count(f"camp_{kind}") for kind in ("dome_wall_panel", "dome_window_panel", "dome_opening_frame"))
    outside = sum(kinds.count(f"camp_{kind}") for kind in ("shell_gore", "shell_gore_window", "shell_gore_open"))
    assert inside == outside == len(every)
    assert kinds.count("camp_dome_ceiling_gore") == kinds.count("camp_dome_deck_wedge") == len(every)
    assert kinds.count("camp_dome_window_panel") == kinds.count("camp_shell_gore_window")
    assert kinds.count("camp_rod_lamp") == len(camp_kit.LAMPS)
    assert kinds.count("camp_floor_cable") == len(camp_kit.CABLE_RUNS)


def test_the_installed_layout_is_the_tool_s():
    installed = camp_kit.REPO / "data/kit/camp.json"
    if not installed.exists():
        return
    laid = json.loads(installed.read_text())
    wanted = {}
    for found in camp_kit.laid_out():
        wanted[found["kind"]] = wanted.get(found["kind"], 0) + 1
    assert laid["counts"] == wanted, (laid["counts"], wanted)


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
