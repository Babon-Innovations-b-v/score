"""Contracts: every stage output carries its schema and version, in the house's units, checked both ways.

    contracts.stamp(contract, out)          # the making side: the output's faults against its contract raise Broken,
                                            # else contract.json (schema, version, units) is written into it
    contracts.expect(wanted, found, node)   # the reading side: an input's stamp must be the schema and version the
                                            # reading stage was written for, else Mismatch

A stage names its own output's contract (`Stage.contract`) and, for each earlier stage it reads, the schema and version
it expects (`Stage.after`). The runner stamps every output before it is stored, so nothing off its contract is kept,
and checks each input's stamp before a stage reads it, so a schema change upstream stops the stages written for the
old one instead of feeding them something they misread.

Units are the house's, one set for every stage (the design of 2026-10-11, rules for every stage): metres, seconds,
degrees, Y up (the OpenUSD stages' convention, tools/usd/export.py). A contract names the units its output uses; one
naming any other value is refused when it is declared.
"""
import json
from dataclasses import dataclass, field
from typing import Callable

STAMP = "contract.json"
HOUSE_UNITS = {"length": "metre", "time": "second", "angle": "degree", "up axis": "Y"}


class Broken(Exception):
    """A stage's output is off its own contract: it is not stored."""


class Mismatch(Exception):
    """An input's stamp is not the schema and version the reading stage expects."""


@dataclass(frozen=True)
class Contract:
    """One output schema: its name, version, the house units it uses and its check, `faults(folder) -> [why, ...]`
    (empty when the folder holds a sound output of this schema)."""
    schema: str
    version: int
    faults: Callable
    units: dict = field(default_factory=dict)

    def __post_init__(self):
        foreign = {name: value for name, value in self.units.items() if HOUSE_UNITS.get(name) != value}
        if foreign:
            raise ValueError(f"contract {self.schema} v{self.version}: units {foreign} are not the house's "
                             f"{HOUSE_UNITS}")

    def stamp_of(self):
        """What the output's contract.json says."""
        return {"schema": self.schema, "version": self.version, "units": dict(self.units)}


def stamp(contract, out):
    """Check an output against its contract and write its stamp into it; Broken with every fault when it is off."""
    faults = contract.faults(out)
    if faults:
        raise Broken(f"off its contract {contract.schema} v{contract.version}: " + "; ".join(faults))
    (out / STAMP).write_text(json.dumps(contract.stamp_of(), indent=1))


def expect(wanted, found, node):
    """Refuse an input whose stamp (`found`, contract.json's content or None) is not `wanted`, (schema, version)."""
    schema, version = wanted
    if found is None:
        raise Mismatch(f"{node}'s output carries no contract stamp; expected {schema} v{version}")
    if (found["schema"], found["version"]) != (schema, version):
        raise Mismatch(f"{node}'s output is {found['schema']} v{found['version']}; expected {schema} v{version}")
    foreign = {name: value for name, value in found.get("units", {}).items() if HOUSE_UNITS.get(name) != value}
    if foreign:
        raise Mismatch(f"{node}'s output is in units {foreign}, not the house's")


# --- the schemas the stage table uses ----------------------------------------------------------------------------

def openusd_stage_faults(folder):
    """Why a folder is not one OpenUSD stage in metres with Y up and a default prim, or [] when it is."""
    from pxr import Usd, UsdGeom
    roots = sorted(folder.glob("*.usda"))
    if len(roots) != 1:
        return [f"{len(roots)} root stages (*.usda), not one"]
    stage = Usd.Stage.Open(str(roots[0]))
    faults = []
    if UsdGeom.GetStageMetersPerUnit(stage) != 1.0:
        faults.append(f"metersPerUnit {UsdGeom.GetStageMetersPerUnit(stage)}, not 1 (metres)")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.y:
        faults.append(f"upAxis {UsdGeom.GetStageUpAxis(stage)}, not Y")
    if not stage.GetDefaultPrim():
        faults.append("no default prim (the place)")
    return faults


def place_manifest_faults(folder):
    """Why a folder is not a place's manifest ({"stages": {stage: output}}), or [] when it is."""
    path = folder / "manifest.json"
    if not path.exists():
        return ["no manifest.json"]
    stages = json.loads(path.read_text()).get("stages")
    if not isinstance(stages, dict) or not all(isinstance(output, str) for output in stages.values()):
        return ["manifest.json has no {stage: output} map under stages"]
    return []


OPENUSD_STAGE = Contract("openusd-stage", 1, openusd_stage_faults, {"length": "metre", "up axis": "Y"})
PLACE_MANIFEST = Contract("place-manifest", 1, place_manifest_faults)
