"""Checks for the judge runner's list and the cards it may take, without renting anything.

Plain python: python3 tools/props/cloud/judge_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import capacity  # noqa: E402
import judge  # noqa: E402
import provider  # noqa: E402


def test_an_answered_question_is_not_asked_again():
    folder = pathlib.Path(tempfile.mkdtemp())
    listing = folder / "questions.json"
    listing.write_text(json.dumps([{"name": "a", "text": "?", "images": []}, {"name": "b", "text": "?", "images": []}]))
    (folder / "a.txt").write_text("{}")
    assert [job["name"] for job in judge.to_ask(listing, folder)] == ["b"]


def test_the_judge_runs_only_on_cards_that_hold_its_weights():
    assert min(provider.card_gb(machine_class) for machine_class in capacity.classes_for(judge.KIND)) >= 48


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("judge_test: ok")
