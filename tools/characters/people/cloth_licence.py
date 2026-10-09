"""Which simulator hung each drape a body wears, and whether its licence lets the body ship.

SCORE's rule is that every model and tool it uses allows commercial use. GarmentCode's simulation ran in its NVIDIA
Warp fork (NvidiaWarp-GarmentCode, NVIDIA Source Code License: non-commercial research and evaluation only), and every
look kept before 2026-10-09 was draped by it; drapes from then on are Newton's (Apache-2.0) or Blender's cloth (GPL;
what it simulates is ours). A drape folder names its simulator in a record beside the cloth (any JSON there with a
`simulator` key); a folder with GarmentCode's `sim_props.yaml` and no such record is the Warp fork's.

body.py writes `drapes_of(look)` into each built body's report (`<person>.json` beside its `.glb`), and `faults` reads
it back: a body whose report names no drapes, or a drape from a simulator not in COMMERCIAL, is a fault. The cast
writer (../cast.py) refuses a cast with a fault, and `python cloth_licence.py` checks every person's body in a bodies folder.
Plain Python only, so the gate can run it.
"""
import json
import pathlib
import sys

WARP_FORK = {"name": "GarmentCode NVIDIA Warp fork (NvidiaWarp-GarmentCode)",
             "licence": "NVIDIA Source Code License (non-commercial)"}
# Simulators whose output may ship, by the start of the name their record gives, with the licence that allows it.
COMMERCIAL = {"Newton": "Apache-2.0", "Blender": "GPL-3.0-or-later (output is ours)"}
UNKNOWN = {"name": "unknown", "licence": "unknown"}


def simulator_of(folder):
    """The simulator a drape folder's record names, as {name, licence}; the Warp fork for GarmentCode's own folders."""
    folder = pathlib.Path(folder)
    for record in sorted(folder.glob("*.json")):
        try:
            data = json.loads(record.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        simulator = data.get("simulator") if isinstance(data, dict) else None
        if isinstance(simulator, str):
            return {"name": simulator, "licence": licence_of(simulator)}
        if isinstance(simulator, dict) and "name" in simulator:
            return {"name": simulator["name"], "licence": simulator.get("licence") or licence_of(simulator["name"])}
    if (folder / "sim_props.yaml").exists():
        return dict(WARP_FORK)
    return dict(UNKNOWN)


def licence_of(name):
    """The licence a known commercial-OK simulator's name carries, else unknown."""
    for start, licence in COMMERCIAL.items():
        if name.startswith(start):
            return licence
    return "unknown"


def drapes_of(look):
    """Every drape folder of a look (<kind>_drape) and the simulator that hung it."""
    return {folder.name: simulator_of(folder) for folder in sorted(pathlib.Path(look).glob("*_drape"))
            if folder.is_dir()}


def allowed(simulator):
    """Whether a drape's simulator is one whose output may ship."""
    return any(simulator.get("name", "").startswith(start) for start in COMMERCIAL)


def faults(character, report):
    """What is wrong with one built body's drapes, from its report (empty when it may ship)."""
    drapes = report.get("drapes")
    if not drapes:
        return [f"{character}: its body's report names no drapes (built before the licence record; rebuild it)"]
    return [f"{character}: {kind} was draped by {simulator.get('name')} ({simulator.get('licence')}), not "
            "commercial-OK" for kind, simulator in sorted(drapes.items()) if not allowed(simulator)]


def body_faults(characters, bodies):
    """The faults of every named character's built body in a bodies folder."""
    found = []
    for character in sorted(set(characters)):
        report = pathlib.Path(bodies) / f"{character}.json"
        if not report.exists():
            found.append(f"{character}: no body report at {report}")
            continue
        found.extend(faults(character, json.loads(report.read_text())))
    return found


def main():
    """Check every person's built body (paths.PEOPLE) in a bodies folder, the work folder's by default."""
    import paths
    bodies = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else paths.BODIES
    found = body_faults(paths.PEOPLE, bodies)
    print("\n".join(found) if found else f"every body in {bodies} wears commercial-OK drapes")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
