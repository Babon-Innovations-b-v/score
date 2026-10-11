"""An output off its contract is refused before it is stored, a contract in other units than the house's cannot be
declared, and a reader refuses an input of another schema or version or with no stamp.

Run: .venv/bin/python score/contracts/contracts_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import contracts  # noqa: E402

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


def a_stage(metres=1, up="Y"):
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "hangar.usda").write_text(STAGE.format(metres=metres, up=up))
    return folder


def broken(contract, folder):
    try:
        contracts.stamp(contract, folder)
    except contracts.Broken as fault:
        return str(fault)
    raise AssertionError("stamped")


def test_an_openusd_stage_off_metres_or_y_up_is_refused_and_a_sound_one_is_stamped():
    assert "metersPerUnit 0.01" in broken(contracts.OPENUSD_STAGE, a_stage(metres=0.01))
    assert "upAxis Z" in broken(contracts.OPENUSD_STAGE, a_stage(up="Z"))
    assert "0 root stages" in broken(contracts.OPENUSD_STAGE, pathlib.Path(tempfile.mkdtemp()))
    sound = a_stage()
    contracts.stamp(contracts.OPENUSD_STAGE, sound)
    assert json.loads((sound / contracts.STAMP).read_text()) == {
        "schema": "openusd-stage", "version": 1, "units": {"length": "metre", "up axis": "Y"}}


def test_a_contract_in_other_units_than_the_house_is_refused():
    try:
        contracts.Contract("scene", 1, lambda folder: [], {"length": "centimetre"})
    except ValueError as refusal:
        assert "centimetre" in str(refusal)
        return
    raise AssertionError("a contract in centimetres was declared")


def mismatch(wanted, found):
    try:
        contracts.expect(wanted, found, "assembly@hangar")
    except contracts.Mismatch as refusal:
        return str(refusal)
    raise AssertionError("taken")


def test_a_reader_refuses_another_schema_or_version_or_no_stamp():
    stamp = contracts.OPENUSD_STAGE.stamp_of()
    contracts.expect(("openusd-stage", 1), stamp, "assembly@hangar")
    assert "expected openusd-stage v2" in mismatch(("openusd-stage", 2), stamp)
    assert "expected place-manifest v1" in mismatch(("place-manifest", 1), stamp)
    assert "no contract stamp" in mismatch(("openusd-stage", 1), None)
    assert "not the house's" in mismatch(("openusd-stage", 1), {**stamp, "units": {"length": "inch"}})


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
