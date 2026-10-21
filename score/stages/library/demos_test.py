"""The demos' shape check, and every demo module naming its algorithm (no library, no fetch)."""
from score.stages.library import demos

GOOD = {"example": "the greenhouse's beds", "view": "plan", "bounds": [0, 0, 1, 1],
        "steps": [{"label": "The beds", "shapes": [{"kind": "area", "points": [[0, 0], [1, 0], [1, 1]], "tone": "c1"}]}]}


def test_a_demo_on_the_shape_has_no_problems_and_one_off_it_says_what():
    assert demos.problems(GOOD) == []
    off = {**GOOD, "view": "film", "steps": [{"label": "x", "shapes": [{"kind": "blob", "points": [[0, 0]]},
                                                                       {"kind": "dots", "points": [], "tone": "pink"}]}]}
    assert demos.problems(off) == ["view 'film'", "shape kind 'blob'", "tone 'pink'"]
    assert demos.problems({**GOOD, "view": "relief"}) == ["relief without heights"]


def test_a_module_without_an_example_or_that_fails_is_missing_with_why():
    class Without:
        @staticmethod
        def made(inputs):
            raise demos.NoExample("nothing kept")

    class Broken:
        @staticmethod
        def made(inputs):
            raise KeyError("beds")

    assert demos.made(Without) == {"missing": "nothing kept"}
    assert demos.made(Broken)["missing"].startswith("its demo failed: KeyError")


def test_every_module_names_its_algorithm():
    found = demos.modules()
    assert "surface_recipes" in found and all(module.ALGORITHM == name for name, module in found.items())
