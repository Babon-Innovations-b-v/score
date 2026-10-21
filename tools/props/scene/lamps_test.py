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


# A reading's rows as the creator's kept scene inventories carry them: each anchored on the row it rests on.
READING = [{"id": "floor_plates", "noun": "floor plates", "anchor": "ground"},
           {"id": "left_wall", "noun": "wall", "anchor": "on:floor_plates"},
           {"id": "roof_dome", "noun": "roof", "anchor": "on:left_wall"},
           {"id": "ceiling_beam", "name": "ceiling beam", "noun": "beam", "anchor": "roof"},
           {"id": "ribs", "noun": "ribs", "anchor": "on:left_wall"},
           {"id": "desk", "noun": "desk", "anchor": "floor"},
           {"id": "loop_a", "noun": "frame", "anchor": "on:loop_b"},
           {"id": "loop_b", "noun": "frame", "anchor": "on:loop_a"}]
WORDS = {"ceiling": ["ceiling", "roof"], "wall": ["wall", "walls"]}


def test_a_reading_s_lamp_is_mounted_as_the_row_it_is_on():
    """`on:<row>`: the held row's noun, else its own anchor, else what it is on in turn; a desk lamp stands."""
    def mount(on):
        return lamps.mount_of({"id": "lamp", "noun": "lamp", "anchor": on}, READING, WORDS)
    assert [mount(on) for on in ("on:roof_dome", "on:left_wall", "on:ceiling_beam", "on:ribs", "on:desk",
                                 "on:loop_a", "on:nothing", "floor")] == \
        ["ceiling", "wall", "ceiling", "wall", "stands", "stands", "stands", "stands"]


def test_a_reading_s_lamp_on_its_roof_gets_the_ceiling_lamp_with_its_shadows():
    row = {"id": "roof_light", "noun": "light", "anchor": "on:roof_dome"}
    assert lamps.light_of(row, laid(2.5), READING, library=LIBRARY, words=WORDS) == \
        {"strength": 0.25, "reach": 5.0, "high": 0.05, "shadows": True}


def test_a_lens_part_is_not_where_the_lamp_hangs():
    row = {"id": "lamp", "noun": "lamp", "anchor": "ceiling"}
    pieces = laid(3.0) + [{"kind": "x_lamp", "at": [0.0, 0.0, 0.0], "part": "glow"}]
    assert lamps.light_of(row, pieces, library=LIBRARY)["reach"] == 6.0


def test_every_installed_kit_s_lamps_are_the_rule_s_and_no_other_kind_shines():
    """data/kit/<place>.json, as the scene record and the light layer read it: each kind's light is exactly what its
    inventory row's kind and the library's lamp give for the pieces laid there, and a kind no glowing row names has
    none (a typed number put back on a kit, or a kit left from before the rule, fails here)."""
    import json
    lit = 0
    for kit_path in sorted((lamps.REPO / "data/kit").glob("*.json")):
        kit = json.loads(kit_path.read_text())
        inventory_path = lamps.REPO / "data/inventory" / kit_path.name
        if "kinds" not in kit or not inventory_path.exists():
            continue
        rows = {f"{kit['room']}_{row['id']}": row for row in json.loads(inventory_path.read_text())["rows"]
                if row.get("made") == "kit piece"}
        for kind, about in kit["kinds"].items():
            wanted = lamps.light_of(rows[kind], [laid for laid in kit["pieces"] if laid["kind"] == kind],
                                    list(rows.values())) if kind in rows else None
            assert about.get("light") == wanted, (kit_path.name, kind, about.get("light"), wanted)
            lit += wanted is not None
    assert lit >= 40, lit


def test_the_real_library_names_the_words_of_a_ceiling_and_a_wall():
    assert {"ceiling", "roof"} <= set(lamps.mount_words()["ceiling"]) and "wall" in lamps.mount_words()["wall"]


def test_every_mount_of_the_real_library_has_its_numbers():
    for mount in ("ceiling", "wall", "stands"):
        assert set(lamps.mounts()[mount]) == {"high", "reach_per_height", "least_reach", "strength_per_reach",
                                              "shadows"}, mount
