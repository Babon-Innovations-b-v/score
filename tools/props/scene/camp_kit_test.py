"""Checks of the expedition camp habitat's kit layout (camp_kit.py), plain python: its numbers are the game's own
(read back out of the GDScript, so the kit and the lining's collision never drift apart), every lining panel has its
piece inside and its gore outside, and the installed layout is the one the tool lays."""
import json
import pathlib
import re
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

GAME = camp_kit.REPO / "game/world/mars/expedition_camp"


def constant(path, name):
    found = re.search(rf"^const {name} := (.+)$", (GAME / path).read_text(), flags=re.MULTILINE)
    assert found, f"{name} in {path}"
    return found.group(1).strip()


def numbers(text):
    return [float(value) for value in re.findall(r"(?<![\w.])-?\d+\.?\d*", text)]


def test_the_numbers_are_the_game_s():
    habitat = "camp_habitat/camp_habitat.gd"
    assert numbers(constant(habitat, "DOOR_MIDDLE")) == list(camp_kit.DOOR_DOME["middle"])
    assert numbers(constant(habitat, "FAR_MIDDLE")) == list(camp_kit.FAR_DOME["middle"])
    assert numbers(constant(habitat, "DOORWAY_DEGREES")) == [camp_kit.DOORWAY]
    assert numbers(constant(habitat, "OPENING_WIDE_M")) == [camp_kit.OPENING_WIDE]
    assert numbers(constant(habitat, "OPENING_TALL_M")) == [camp_kit.OPENING_TALL]
    assert numbers(constant(habitat, "SHELL_OUT_M")) == [camp_kit.SHELL_OUT]
    assert numbers(constant(habitat, "SHELL_SHOULDER_M")) == [camp_kit.SHELL_SHOULDER]
    assert numbers(constant(habitat, "SHELL_RISE_M")) == [camp_kit.SHELL_RISE]
    text = (GAME / habitat).read_text()
    for dome in (camp_kit.DOOR_DOME, camp_kit.FAR_DOME):
        assert f'"radius": {dome["radius"]}' in text
        for low, high in dome["windows"]:
            assert f"Vector2({low}, {high})" in text, (low, high)
    lining = "camp_lining/camp_lining.gd"
    for name, value in (("WALL_TALL", camp_kit.WALL_TALL), ("CEILING_RISE", camp_kit.CEILING_RISE),
                        ("CEILING_IN", camp_kit.CEILING_IN), ("PANEL_WIDE", camp_kit.PANEL_WIDE),
                        ("SKIN", camp_kit.SKIN)):
        assert numbers(constant(lining, name)) == [value], name
    rooms = "camp_rooms/camp_rooms.gd"
    assert numbers(constant(rooms, "PARTITION_DOOR_AT")) == [camp_kit.PARTITION_DOOR_AT]
    assert numbers(constant(rooms, "LAMP_HEIGHT")) == [camp_kit.LAMP_HEIGHT]


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
