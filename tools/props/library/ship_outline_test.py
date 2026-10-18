"""Check the hangar ship's numbers read off the owner's locked plan v7 (inside/ship_outline.py): built at the plan's
length, its snout as wide as the plan draws it (the image-to-3D take's came back 3.7 m where v7 has 5.0 m at 3.9 m from
the tip, 2026-10-18), two fins each side, two leg pairs, the side ring a door a person walks through, every thruster on
the hull's own surface. Plain Python: runs with the system python.
Run: python3 tools/props/library/ship_outline_test.py
"""
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "inside"))
import ship_outline  # noqa: E402

PLAN = ship_outline.read_plan()
SCALE = ship_outline.scale_of(PLAN)


def test_the_ship_is_built_at_its_length_from_the_drawing():
    stations = ship_outline.stations(PLAN)
    assert PLAN["length"] == 46.0 and PLAN["drawn_length"] == 31.0
    assert abs(stations[-1]["y"] - 30.976 * SCALE) < 0.01, stations[-1]["y"]
    assert ship_outline.extents(PLAN)[2] == 46.0


def test_the_snout_is_as_wide_as_the_plan_draws_it():
    """v7: 5.0 m across at 3.9 m from the spike's tip, drawn; not the pointed nose the owner turned down twice."""
    here = ship_outline.station_at(PLAN, 3.884 * SCALE)
    assert abs(2 * here["half"] / SCALE - 5.0) < 0.1, 2 * here["half"] / SCALE


def test_a_section_is_closed_and_square_to_the_middle_line():
    for station in ship_outline.stations(PLAN)[::10]:
        corners = ship_outline.section(station)
        assert len(corners) == 10
        for (x, z), (mirror_x, mirror_z) in zip(corners, reversed(corners)):
            assert abs(x + mirror_x) < 1e-9 and abs(z - mirror_z) < 1e-9
        assert math.isclose(min(z for _, z in corners), station["keel"], abs_tol=1e-9)
        assert math.isclose(max(z for _, z in corners), station["top"], abs_tol=1e-9)


def test_two_fins_each_side_reach_as_far_as_the_outline():
    fins = ship_outline.fins(PLAN)
    assert len(fins) == 2, [len(fin) for fin in fins]
    front, rear = sorted(fins, key=lambda fin: fin[0][1])
    assert front[0][1] < 10 * SCALE < rear[0][1], "a front fin ahead of the cockpit's end, a rear fin aft"
    widest = max(span for _, span in ship_outline.fin_spans(PLAN))
    assert abs(widest / SCALE - 5.52) < 0.1, widest / SCALE


def test_two_leg_pairs_stand_under_the_keel():
    legs = ship_outline.legs(PLAN)
    assert sorted({round(leg["y"] / SCALE, 1) for leg in legs}) == [11.0, 22.3]
    for leg in legs:
        here = ship_outline.station_at(PLAN, leg["y"])
        assert abs(leg["x"]) < here["half"] * ship_outline.SECTION[0][0], "a leg under the keel's flat"
        assert leg["keel"] > 0.9, "the belly stands clear of the ground on its legs"


def test_the_side_ring_is_a_door_a_person_walks_through():
    ring = ship_outline.side_ring(PLAN)
    assert 2 * ring["opening"] >= 1.9, ring
    deck = PLAN["deck"] * SCALE
    assert ring["z"] - ring["opening"] >= deck, "its sill is at or over the deck"
    assert ring["x"] > 0, "on the starboard side"


def test_every_thruster_sits_on_the_hull():
    for mount in ship_outline.mounts(PLAN):
        x, y, z = mount["at"]
        here = ship_outline.station_at(PLAN, y)
        if mount["row"] == "lift_thruster":
            (_, belly), _ = ship_outline.under(here, x)
            assert abs(z - belly) < 1e-6, mount
        assert here["keel"] - 1e-6 <= z + (mount["size"][1] if mount["row"] == "main_engine" else 0.0), mount
        assert math.isclose(math.hypot(*mount["out"]), 1.0, abs_tol=1e-6), mount


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print("ok", name)
