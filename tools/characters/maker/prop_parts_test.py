"""Check the prop route's part questions and answers: every part is asked with each of the three seeds, most of a
part's usable answers decide its material, an answer with no JSON (the judge thinking past its limit) is not counted,
and each outfit has its own palette.

Run: .venv/bin/python tools/characters/maker/prop_parts_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prop_parts  # noqa: E402

NAMES = ["skin", "hair", "navy fabric"]


def answer(folder, part, seed, text):
    (folder / f"take-part{part:02d}-s{seed}.txt").write_text(text)


def test_each_part_is_asked_with_every_seed():
    with tempfile.TemporaryDirectory() as place:
        listing = pathlib.Path(place) / "questions.json"
        listing.write_text(json.dumps([{"name": "take-part00", "text": "?", "images": []},
                                       {"name": "other-part00", "text": "?", "images": []}]))
        asked = prop_parts.seeded(listing, ["take-part00"])
        jobs = json.loads(listing.read_text())
        assert asked == [f"take-part00-s{seed}" for seed in prop_parts.SEEDS]
        assert sorted(job["seed"] for job in jobs if job["name"].startswith("take")) == list(prop_parts.SEEDS)
        assert any(job["name"] == "other-part00" for job in jobs)


def test_most_usable_answers_decide():
    with tempfile.TemporaryDirectory() as place:
        folder = pathlib.Path(place)
        answer(folder, 0, 7, 'thinking... {"part": "pocket", "material": "M3"}')
        answer(folder, 0, 8, '{"part": "buckle", "material": "M1"}')
        answer(folder, 0, 9, '{"part": "pocket", "material": "M3"}')
        answer(folder, 1, 7, "thinking that never ends")
        answer(folder, 1, 8, '{"part": "hand", "material": "M1"}')
        found = prop_parts.judged_by_most(folder, "take", 3, NAMES)
        assert found == {0: "navy fabric", 1: "skin"}


def test_each_outfit_has_its_palette():
    work, space = prop_parts.person_materials({}, "work"), prop_parts.person_materials({}, "space")
    assert "navy fabric" in work and "white suit fabric" in space and "skin" in work and "hair" in space
    assert all(prop_parts.ROLES[entry["family"]] for entry in space.values())


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
