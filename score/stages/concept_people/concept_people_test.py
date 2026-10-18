"""The concept-people stage's counting and gate on two small pictures, without SAM 3 or a card."""
import json
import pathlib
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score import checks  # noqa: E402
from score.stages import concept_people  # noqa: E402


def test_counts_and_gate():
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        for name in ("a.png", "b.png"):
            Image.new("RGB", (40, 30)).save(root / name)
        inputs = {"inventory": root, "lab.v1": root / "a.png", "greenhouse.v1": root / "b.png"}
        jobs = concept_people.jobs_of(inputs)
        assert [job["rows"][0]["box"] for job in jobs] == [[0, 0, 40, 30], [0, 0, 40, 30]]
        instances = {"greenhouse.v1": [{"box": [1, 1, 5, 9], "score": 0.9}] * 3}
        judged = {"greenhouse.v1.0": [("person", "working")] * 3,
                  "greenhouse.v1.1": [("picture", None), ("picture", None), ("person", "standing")],
                  "greenhouse.v1.2": [("person", "standing"), ("suit", None), (None, None)]}
        concept_people.write_counts(jobs, instances, root / "people.json", judged)
        counts = json.loads((root / "people.json").read_text())
        figures = counts["greenhouse"]["v1"]["instances"]
        assert counts["greenhouse"]["v1"]["people"] == 1 and list(counts) == ["greenhouse"]
        assert [figure["judged"] for figure in figures] == ["person", "picture", None]
        assert [figure["doing"] for figure in figures] == ["working", None, None]
        unknown = concept_people.judge_measured(root, inputs, None)
        assert unknown.answer == checks.UNKNOWN and "lab.v1" in unknown.reason
        assert concept_people.judge_judged(root, inputs, None).answer == checks.UNKNOWN
        instances["lab.v1"] = []
        judged["greenhouse.v1.2"] = [("suit", None), ("suit", None), (None, None)]
        concept_people.write_counts(jobs, instances, root / "people.json", judged)
        assert concept_people.judge_measured(root, inputs, None).answer == checks.PASS
        assert concept_people.judge_judged(root, inputs, None).answer == checks.PASS


def test_verdicts():
    assert concept_people.verdict_of("thinking...\nVERDICT: Picture.") == "picture"
    assert concept_people.doing_of("VERDICT: person\nDOING: Walking") == "walking"
    assert concept_people.verdict_of("no answer") is None
    assert concept_people.majority(["person", "person", "suit"]) == "person"
    assert concept_people.majority(["person", "suit"]) is None


def test_figure_pictures():
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        Image.new("RGB", (100, 80)).save(root / "a.png")
        concept_people.figure_pictures(root / "a.png", [40, 30, 50, 60], root / "f")
        assert Image.open(root / "f-close.jpg").size == (10, 30)
        assert Image.open(root / "f-around.jpg").size == (30, 80)


def test_every_place_has_views():
    assert all(concept_people.VIEWS.values()), concept_people.VIEWS


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    test_counts_and_gate()
    test_every_place_has_views()
    test_verdicts()
    test_figure_pictures()
    print("concept_people: 4 tests pass")
