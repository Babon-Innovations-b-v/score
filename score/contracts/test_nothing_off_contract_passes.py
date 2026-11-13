"""Nothing off its contract passes either way: an output off its contract is refused before it is stored (no stamp
written), a contract in other units than the house's (metres, seconds, degrees, Y up) cannot be declared, and a reader
refuses an input of another schema or version, with no stamp, or stamped in foreign units.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/contracts/test_nothing_off_contract_passes.py

One test: a few output folders are stamped, the sound one's written stamp is what every reader row reads, and a
manifest and a units table are judged beside them. It turns red under each break below (each applied once and seen
red, 2026-10-26; re-proved on the folded file 2026-11-13):
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

HOUSE_STAMP = {"schema": "openusd-stage", "version": 1, "units": {"length": "metre", "up axis": "Y"}}

# output folder: its root stage's (metresPerUnit, upAxis), or None for no root stage -> the fault it is refused for
STAGES = {
    "sound": ((1, "Y"), None),
    "centimetres": ((0.01, "Y"), "metersPerUnit 0.01"),
    "z-up": ((1, "Z"), "upAxis Z"),
    "no root stage": (None, "0 root stages"),
}

# place manifest.json (None: no file) -> whether it is sound
MANIFESTS = [
    (None, False), ({"stages": ["a"]}, False), ({"stages": {"assembly": 3}}, False),
    ({"stages": {"assembly": "abc"}}, True)]

# units a contract declares, none of them the house's
FOREIGN_UNITS = [{"length": "centimetre"}, {"up axis": "Z"}, {"colour": "red"}]

# what a reader wants, what it finds (SOUND: the sound stage's own written stamp) -> why it refuses (None: it takes it)
SOUND = object()
READS = [
    (("openusd-stage", 1), SOUND, None),
    (("openusd-stage", 2), SOUND, "expected openusd-stage v2"),
    (("place-manifest", 1), SOUND, "expected place-manifest v1"),
    (("openusd-stage", 1), None, "no contract stamp"),
    (("openusd-stage", 1), {**HOUSE_STAMP, "units": {"length": "inch"}}, "not the house's"),
]


def an_output(folder, stage):
    folder.mkdir()
    if stage is not None:
        metres, up = stage
        (folder / "hangar.usda").write_text(STAGE.format(metres=metres, up=up))
    return folder


def test_nothing_off_contract_passes(tmp_path):
    stamps = {}
    for name, (stage, fault) in STAGES.items():
        folder = an_output(tmp_path / name.replace(" ", "-"), stage)
        if fault is None:
            contracts.stamp(contracts.OPENUSD_STAGE, folder)
        else:
            with pytest.raises(contracts.Broken, match=fault):
                contracts.stamp(contracts.OPENUSD_STAGE, folder)
        stamp_file = folder / contracts.STAMP
        stamps[name] = json.loads(stamp_file.read_text()) if stamp_file.exists() else None
    assert stamps == {"sound": HOUSE_STAMP, "centimetres": None, "z-up": None, "no root stage": None}

    for manifest, sound in MANIFESTS:
        place = tmp_path / f"place-{len(list(tmp_path.glob('place-*')))}"
        place.mkdir()
        if manifest is not None:
            (place / "manifest.json").write_text(json.dumps(manifest))
        assert (contracts.PLACE_MANIFEST.faults(place) == []) == sound, f"manifest {manifest} should be sound={sound}"

    for units in FOREIGN_UNITS:
        with pytest.raises(ValueError):
            contracts.Contract("scene", 1, lambda folder: [], units)
            pytest.fail(f"a contract in units {units} was declared")

    for wanted, found, why in READS:
        found = stamps["sound"] if found is SOUND else found
        if why is None:
            contracts.expect(wanted, found, "assembly@hangar")
        else:
            with pytest.raises(contracts.Mismatch, match=why):
                contracts.expect(wanted, found, "assembly@hangar")
