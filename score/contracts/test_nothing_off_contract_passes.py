"""Nothing off its contract passes either way: an output off its contract is refused before it is stored (no stamp
written), a contract in other units than the house's (metres, seconds, degrees, Y up) cannot be declared, and a reader
refuses an input of another schema or version, with no stamp, or stamped in foreign units.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/contracts/test_nothing_off_contract_passes.py

Each test turns red under the break written beside it (each applied once and seen red, 2026-10-26):
- openusd stage: in openusd_stage_faults drop the metersPerUnit fault, or the upAxis one.
- stamp: in contracts.stamp write the stamp before checking the faults (a broken output then carries one).
- units: drop Contract.__post_init__'s raise.
- reader: in contracts.expect compare the schema only, or drop the foreign-units raise.
- manifest: in place_manifest_faults return [] when stages is not a dict.
"""
import json

import pytest

from score import contracts

STAGE = """#usda 1.0
(
    defaultPrim = "hangar"
    metersPerUnit = {metres}
    upAxis = "{up}"
)

def Xform "hangar"
{{
}}
"""


def a_stage(folder, metres=1, up="Y"):
    folder.mkdir()
    (folder / "hangar.usda").write_text(STAGE.format(metres=metres, up=up))
    return folder


@pytest.mark.parametrize("metres, up, fault", [(0.01, "Y", "metersPerUnit 0.01"), (1, "Z", "upAxis Z")])
def test_an_openusd_stage_off_metres_or_y_up_is_refused_unstamped(tmp_path, metres, up, fault):
    folder = a_stage(tmp_path / "out", metres, up)
    with pytest.raises(contracts.Broken, match=fault):
        contracts.stamp(contracts.OPENUSD_STAGE, folder)
    assert not (folder / contracts.STAMP).exists()


def test_a_folder_with_no_root_stage_is_refused(tmp_path):
    with pytest.raises(contracts.Broken, match="0 root stages"):
        contracts.stamp(contracts.OPENUSD_STAGE, tmp_path)


def test_a_sound_stage_is_stamped_in_house_units(tmp_path):
    folder = a_stage(tmp_path / "out")
    contracts.stamp(contracts.OPENUSD_STAGE, folder)
    assert json.loads((folder / contracts.STAMP).read_text()) == {
        "schema": "openusd-stage", "version": 1, "units": {"length": "metre", "up axis": "Y"}}


@pytest.mark.parametrize("manifest, sound", [
    (None, False), ({"stages": ["a"]}, False), ({"stages": {"assembly": 3}}, False),
    ({"stages": {"assembly": "abc"}}, True)])
def test_a_place_manifest_needs_its_stage_to_output_map(tmp_path, manifest, sound):
    if manifest is not None:
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert (contracts.PLACE_MANIFEST.faults(tmp_path) == []) == sound


@pytest.mark.parametrize("units", [{"length": "centimetre"}, {"up axis": "Z"}, {"colour": "red"}])
def test_a_contract_in_other_units_than_the_house_is_refused(units):
    with pytest.raises(ValueError):
        contracts.Contract("scene", 1, lambda folder: [], units)


STAMPED = {"schema": "openusd-stage", "version": 1, "units": {"length": "metre", "up axis": "Y"}}


def test_a_reader_takes_its_own_schema_and_version():
    contracts.expect(("openusd-stage", 1), STAMPED, "assembly@hangar")


@pytest.mark.parametrize("wanted, found, why", [
    (("openusd-stage", 2), STAMPED, "expected openusd-stage v2"),
    (("place-manifest", 1), STAMPED, "expected place-manifest v1"),
    (("openusd-stage", 1), None, "no contract stamp"),
    (("openusd-stage", 1), {**STAMPED, "units": {"length": "inch"}}, "not the house's"),
])
def test_a_reader_refuses_another_schema_or_version_or_no_stamp_or_foreign_units(wanted, found, why):
    with pytest.raises(contracts.Mismatch, match=why):
        contracts.expect(wanted, found, "assembly@hangar")
