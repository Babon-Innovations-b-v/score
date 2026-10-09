"""Check cloth_licence: GarmentCode's own drape folders are the Warp fork's and fail, Newton's and Blender's records
pass, an unknown simulator fails, and a body report with no drapes fails.

Run: python3 tools/characters/people/cloth_licence_test.py   (plain Python, as the gate runs it)
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cloth_licence  # noqa: E402


def look_with(folder, drapes):
    """A look folder holding one drape folder per (kind, file name, text)."""
    for kind, name, text in drapes:
        (folder / kind).mkdir(parents=True)
        (folder / kind / name).write_text(text)
    return folder


def test_warp_fork_newton_and_blender():
    with tempfile.TemporaryDirectory() as temporary:
        look = look_with(pathlib.Path(temporary), [
            ("work_drape", "sim_props.yaml", "sim: {}\n"),
            ("space_drape", "newton_cloth.json", json.dumps({"simulator": {"name": "Newton 1.6.1 SolverVBD"}})),
            ("coat_drape", "blender_cloth.json", json.dumps({"simulator": "Blender 4.2.23 LTS cloth"})),
            ("jacket_drape", "other.json", json.dumps({"simulator": "SomeCloth 2"}))])
        drapes = cloth_licence.drapes_of(look)
        assert drapes["work_drape"] == cloth_licence.WARP_FORK
        assert drapes["space_drape"]["licence"] == "Apache-2.0"
        faults = cloth_licence.faults("someone", {"drapes": drapes})
        assert len(faults) == 2 and "work_drape" in faults[1] and "jacket_drape" in faults[0]


def test_report_without_drapes_fails():
    assert cloth_licence.faults("someone", {"joints": 27})
    assert not cloth_licence.faults("someone", {"drapes": {"work_drape": {"name": "Newton 1.6.1"}}})


def test_missing_body_report_fails():
    with tempfile.TemporaryDirectory() as temporary:
        assert cloth_licence.body_faults(["nobody"], temporary)


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
