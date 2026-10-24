"""Which layers a scene has, read off its design alone (design_layers.py), on designs and row-kind rules written here,
and the stage table and the assembly's layers gate giving one answer for a design kept where the plan stage keeps it.

Run: .venv/bin/python score/stages/design_layers_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.stages import design_layers  # noqa: E402

KINDS = {"person": {"nouns": ["astronaut", "crowd"], "does": ["acts"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "door": {"nouns": ["door"], "does": ["moves"]}, "vehicle": {"nouns": ["rover"], "does": ["moves"]},
         "plant": {"nouns": ["plant", "plants", "planter"], "does": ["grows"]},
         "loose": {"nouns": ["chair"], "does": ["loose"]}}


def row(row_id, noun, kind="generate", anchor="floor"):
    return {"id": row_id, "noun": noun, "kind": kind, "anchor": anchor}


def test_each_row_shows_the_layer_its_kind_does():
    # a kettle emits and is loose; a rover and a door built as code both move
    assert design_layers.kinds_of({"rows": [row("kettle", "kettle")]}, KINDS) == {"effects", "physics", "light",
                                                                                   "sound"}
    assert design_layers.kinds_of({"rows": [row("rover", "rover")]}, KINDS) == {"motion", "light", "sound"}
    assert design_layers.kinds_of({"rows": [row("door", "door", kind="code")]}, KINDS) == {"motion", "light", "sound"}
    # a crowd acts; a bare room still has its light and sound
    assert design_layers.kinds_of({"rows": [row("crowd", "crowd")]}, KINDS) == {"people", "light", "sound"}
    assert design_layers.kinds_of({"rows": [row("wall", "wall", kind="code")]}, KINDS) == {"light", "sound"}


def test_crops_are_plants_on_a_bed_never_a_potted_plant():
    # plants on a raised planter (a row that grows itself) or on a bed by its noun are crops; a potted plant on the
    # floor or on a desk is not
    beds = [row("planter", "planter"), row("greens", "plants", anchor="on:planter")]
    assert "crops" in design_layers.kinds_of({"rows": beds}, KINDS)
    plot = [row("bed", "bed", kind="code"), row("greens", "plants", anchor="on:bed")]
    assert "crops" in design_layers.kinds_of({"rows": plot}, KINDS)
    potted = [row("desk", "desk"), row("pot", "plant", anchor="on:desk"), row("fern", "plant")]
    assert "crops" not in design_layers.kinds_of({"rows": potted}, KINDS)


def test_plants_are_every_growing_row_and_the_planter_under_crops_is_their_bed():
    design = {"rows": [row("planter", "planter") | {"count": 11}, row("greens", "plants", anchor="on:planter") | {"count": 5},
                       row("pot", "plant") | {"count": 2}, row("desk", "desk")]}
    assert design_layers.plants_of(design, KINDS) == {"rows": 2, "objects": 7, "crops": 1, "beds": 11}
    assert design_layers.plants_of({"rows": [row("desk", "desk")]}, KINDS)["rows"] == 0


def test_the_house_rules_call_trees_and_shrubs_plants():
    from score.stages import row_kinds
    rules = row_kinds.table()
    for noun in ("tree", "palm", "shrub", "bush", "moss", "fern", "flower"):
        assert design_layers.plants_of({"rows": [row("green", noun)]}, rules)["rows"] == 1, noun


def test_a_place_has_a_layer_only_by_its_kept_design():
    with tempfile.TemporaryDirectory() as folder:
        kept, design_layers.KEPT = design_layers.KEPT, pathlib.Path(folder)
        try:
            (pathlib.Path(folder) / "shed.json").write_text(json.dumps({"rows": [row("pilot", "astronaut")]}))
            assert design_layers.has_layer("shed", "people") and design_layers.has_layer("shed", "light")
            assert not design_layers.has_layer("shed", "effects")
            # a place with no design has no layer at all, light and sound included
            assert not design_layers.has_layer("barn", "light") and not design_layers.has_layer(None, "sound")
        finally:
            design_layers.KEPT = kept


def test_the_table_has_a_row_for_every_layer_the_gate_waits_on():
    """For a design kept where the plan stage keeps it, every layer stage the assembly's layers gate needs is a row
    the table holds for the place, and no layer row the assembly reads applies beyond them, by the house's rules."""
    import score.stages as stages
    from score.stages import assembly, row_kinds
    design = {"rows": [row("pilot", "astronaut"), row("kettle", "kettle"), row("hatch", "door", kind="code"),
                       row("planter", "planter"), row("greens", "plants", anchor="on:planter")]}
    with tempfile.TemporaryDirectory() as folder:
        kept, design_layers.KEPT = design_layers.KEPT, pathlib.Path(folder)
        try:
            (pathlib.Path(folder) / "shed.json").write_text(json.dumps(design))
            needed = assembly.needed_layers(design, row_kinds.table())
            rows = {stage.name for stage in stages.STAGES if stage.grain == "place"
                    and stage.name in assembly.NEEDS.values() and stage.applies is not None
                    and stage.applies("shed")}
        finally:
            design_layers.KEPT = kept
    assert needed == ["characters-layer", "crops-layer", "effects-layer", "motion", "settle", "light", "sound"]
    assert rows == set(needed), rows


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
