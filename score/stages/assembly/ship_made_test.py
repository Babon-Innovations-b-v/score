"""A ship place's made pieces, both ways (2026-10-15): the assembly lays a prop-route row its kit-built base has no
object of where the ship kit lays it (complete@quarters failed "no object of this row on the stage" for its bunks)
and leaves a laid one alone; the surfaces check of a ship place gets a view distance for its made models (every one
was none) where a place with an old record is checked as before.

Run: .venv/bin/python score/stages/assembly/ship_made_test.py
"""
import dataclasses
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
from score import stages  # noqa: E402
from score.stages.assembly import BASE_LAYER, ship_made  # noqa: E402
from score.stages.surfaces import bake_check  # noqa: E402
import complete  # noqa: E402
from score.stages.assembly import assembly_test  # noqa: E402
import export_test  # noqa: E402

PLACE = "quarters"  # the bunk is its own take (bunk_1), every other made row another place's
DATA = REPO / "data"


def a_base(out, rows):
    """A base layer laying one object of each row, as the ship's kit export lays its code pieces, and the bunk's
    asset as the assembly's take of its bake writes it."""
    from pxr import Sdf, Usd, UsdGeom
    (out / "layers").mkdir(parents=True)
    (out / "assets").mkdir()
    assembly_test.a_cube_asset(out / "assets/bunk_1.usdc", 1.0)
    stage = Usd.Stage.CreateNew(str(out / BASE_LAYER))
    UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects")
    for row in rows:
        prim = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{row}_1").GetPrim()
        prim.CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(row)
    stage.GetRootLayer().Save()


def own_inputs(folder):
    """The node's inputs for the place's own bake (bunk_1, a 1 m box), the other places' bakes not read."""
    bake = folder / "bake"
    (bake / "made").mkdir(parents=True)
    export_test.box_gltf(bake / "made", "bunk_1")
    return {"inventories": DATA / "inventory", "plan": DATA / "plans" / f"{PLACE}.json",
            "surfaces": DATA / "surfaces" / f"{PLACE}.json", "surfaces-bake": bake}


def bunks(out):
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(out / BASE_LAYER))
    return {prim.GetName(): UsdGeom.Xformable(prim).GetLocalTransformation().ExtractTranslation()
            for prim in stage.Traverse() if prim.GetAttribute("score:row").Get() == "bunk"}


def test_made_rows_are_laid_on_a_kit_base():
    """Both ways: a base of code pieces fails the rows check on the bunk and passes it once the bunks are laid, each
    at its kit spot; the rows no given bake makes stay unlaid and named."""
    inventory = json.loads((DATA / "inventory" / f"{PLACE}.json").read_text())
    spots = [spot for row in inventory["rows"] if row["id"] == "bunk" for spot in row["at"]]
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        out = folder / "out"
        a_base(out, ["wall_upper_plain"])
        assert "bunk" in {fault["row"] for fault in complete.rows_faults(out / BASE_LAYER, inventory)}
        laid, unlaid = ship_made.lay(own_inputs(folder), out, PLACE)
        assert laid == {"bunk": "bunk_1"} and "locker" in unlaid and "bunk" not in unlaid, (laid, unlaid)
        found = bunks(out)
        assert sorted(found) == [f"bunk_{number}" for number in range(1, len(spots) + 1)], found
        for name, spot in zip(sorted(found), spots):  # a 1 m box's foot is its origin: the piece stands at its spot
            assert all(abs(found[name][axis] - spot[key]) < 1e-6 for axis, key in enumerate("xyz")), (name, spot)
        assert "bunk" not in {fault["row"] for fault in complete.rows_faults(out / BASE_LAYER, inventory)}


def test_a_laid_row_is_left_alone():
    """The other way: a base that already lays a bunk (an old room's seed) gets no second one."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        out = folder / "out"
        a_base(out, ["bunk"])
        laid, _ = ship_made.lay(own_inputs(folder), out, PLACE)
        assert laid == {} and list(bunks(out)) == ["bunk_1"]


def test_the_owner_of_a_taken_row_is_read_beside():
    """The quarters' lockers are the shiplock's take, its console the cockpit's: their bakes are read beside, and
    each place's surface data declared."""
    owners = ship_made.owners(PLACE)
    assert owners["bunk"] == PLACE and owners["locker"] == "shiplock" and owners["side_console"] == "cockpit"
    assert {"shiplock", "cockpit"} <= set(ship_made.neighbours(PLACE)) and PLACE not in ship_made.neighbours(PLACE)
    assert "surfaces shiplock" in ship_made.files(PLACE)


def checked_inputs(place, views):
    """The surfaces check's make as the table hands it over, for `place`: the inputs it was given, seen through
    bake_check.seen_degrees while the seen kit stands."""
    seen = {}

    def make(inputs, out, seed, params):
        seen.update(degrees=bake_check.seen_degrees({name: pathlib.Path(path) for name, path in inputs.items()}))
    row = next(row for row in stages.STAGES if row.name == "surfaces-check")
    wrapped = stages.ship_seen(dataclasses.replace(row, make=make))
    inputs = {"surfaces": DATA / "surfaces" / f"{place}.json",
              f"inventory {place}": DATA / "inventory" / f"{place}.json",
              "kit": DATA / "kit" / f"{place}.json", "plan": DATA / "plans" / f"{place}.json", "views": views}
    with tempfile.TemporaryDirectory() as temporary:
        wrapped.make(inputs, pathlib.Path(temporary), 0, {})
        assert not list(pathlib.Path(temporary).iterdir()), "the seen kit is the check's input, not its output"
    return seen["degrees"]


def test_a_ship_place_s_made_models_get_a_view_distance():
    """Both ways: the installed kit alone (code pieces) gives the bunk no spot, so no view distance; the table's
    surfaces check lays the made pieces beside it and reads the views, so the bunk has one."""
    if not stages.ship_place(PLACE):
        raise SystemExit(f"{PLACE} has no ship base stage on this machine (usd-ship/{PLACE}): cannot test the table")
    with tempfile.TemporaryDirectory() as temporary:
        views = pathlib.Path(temporary) / "views.json"
        views.write_text(json.dumps({"views": [{"name": "door", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.0, 1.0]}]}))
        alone = bake_check.seen_degrees({"kit": DATA / "kit" / f"{PLACE}.json", "scene record": views})
        assert "bunk_1" not in alone and alone, alone
        degrees = checked_inputs(PLACE, views)
        assert degrees.get("bunk_1", 0) > 0, degrees


def test_an_old_place_s_check_is_handed_over_as_before():
    """The other way: a place with a round-three seed gets its inputs untouched (no seen kit, no views read)."""
    row = next(row for row in stages.STAGES if row.name == "surfaces-check")
    given = {}
    wrapped = stages.ship_seen(dataclasses.replace(row, make=lambda inputs, *rest: given.update(inputs)))
    inputs = {"surfaces": DATA / "surfaces/hub.json", "kit": DATA / "kit/hub.json"}
    wrapped.make(inputs, pathlib.Path(tempfile.gettempdir()), 0, {})
    assert given == inputs
    assert "views" not in wrapped.files("hub") and "views" in wrapped.files(PLACE)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
