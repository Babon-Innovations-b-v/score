"""The surface stage's own makes and judges run on the people's line: each people-<step> input handed over under the
name the surface stage reads (surfaces-<step>). A module of its own with no imports of the people stage, so the paid
rows' code version is the surface stage's modules and this one only (functools.wraps: _code hashes the wrapped too)."""
import functools

PEOPLE, SURFACES = "people-", "surfaces-"


def as_surfaces(inputs):
    """{name: path} with each people-<step> named surfaces-<step>; world files keep their names."""
    return {(SURFACES + name[len(PEOPLE):] if name.startswith(PEOPLE) else name): path
            for name, path in inputs.items()}


def make(surface_make):
    @functools.wraps(surface_make)
    def made(inputs, out, seed, params):
        return surface_make(as_surfaces(inputs), out, seed, params)
    return made


def judge(surface_judge):
    @functools.wraps(surface_judge)
    def judged(output, inputs, evidence):
        return surface_judge(output, as_surfaces(inputs), evidence)
    return judged
