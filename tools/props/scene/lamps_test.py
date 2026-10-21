"""lamps.py: a kit row's light comes from its reading noun's row kind and the library's lamp, never a typed number."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lamps  # noqa: E402

LIBRARY = {"ceiling": {"high": 0.05, "reach_per_height": 2.0, "least_reach": 1.5, "strength_per_reach": 0.05,
                       "shadows": True},
           "wall": {"high": 0.5, "reach_per_height": 1.5, "least_reach": 1.5, "strength_per_reach": 0.04,
                    "shadows": False},
           "stands": {"high": 0.5, "reach_per_height": 1.5, "least_reach": 1.5, "strength_per_reach": 0.03,
                      "shadows": False}}


def laid(*heights):
    return [{"kind": "x_lamp", "at": [0.0, height, 0.0]} for height in heights]


def test_a_ceiling_lamp_read_from_a_new_reading_gets_the_library_s_light_from_how_high_it_hangs():
    """A Gemini row carries no `light`: its noun alone makes it a lamp, its reach from its laid height."""
    row = {"id": "pendant", "noun": "lamp", "anchor": "ceiling", "made": "kit piece"}
    light = lamps.light_of(row, laid(3.0, 3.0, 3.2), library=LIBRARY)
    assert light == {"strength": 0.3, "reach": 6.0, "high": 0.05, "shadows": True}


def test_a_wall_lamp_low_down_keeps_the_least_reach_and_casts_no_shadow():
    row = {"id": "sconce", "noun": "light", "anchor": "wall"}
    assert lamps.light_of(row, laid(0.5), library=LIBRARY) == {"strength": 0.06, "reach": 1.5, "high": 0.5,
                                                              "shadows": False}


def test_a_typed_light_on_a_row_whose_kind_does_not_glow_gives_no_lamp():
    """The row's own numbers decide nothing: a locker with a status light is no lamp."""
    row = {"id": "locker", "noun": "locker", "anchor": "floor", "light": {"strength": 9.0, "reach": 9.0}}
    assert lamps.light_of(row, laid(0.0), library=LIBRARY) is None


def test_a_lens_part_is_not_where_the_lamp_hangs():
    row = {"id": "lamp", "noun": "lamp", "anchor": "ceiling"}
    pieces = laid(3.0) + [{"kind": "x_lamp", "at": [0.0, 0.0, 0.0], "part": "glow"}]
    assert lamps.light_of(row, pieces, library=LIBRARY)["reach"] == 6.0


def test_every_mount_of_the_real_library_has_its_numbers():
    for mount in ("ceiling", "wall", "stands"):
        assert set(lamps.mounts()[mount]) == {"high", "reach_per_height", "least_reach", "strength_per_reach",
                                              "shadows"}, mount
