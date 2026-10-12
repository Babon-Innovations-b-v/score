"""The prop route's and the surface stage's own makes and judges run on the crops' line: each crops-<row> input handed
over under the name those stages read (crops-closeup as closeup, crops-surfaces-paint as surfaces-paint). A module
of its own with no imports of the crops stage, so the paid rows' code version is those stages' modules and this one
only (functools.wraps: _code hashes the wrapped too), as score/stages/people/renamed.py does for the people's line."""
import functools

CROPS = "crops-"


def as_theirs(inputs):
    """{name: path} with each crops-<row> named <row>; world files keep their names."""
    return {name.removeprefix(CROPS): path for name, path in inputs.items()}


def make(their_make):
    @functools.wraps(their_make)
    def made(inputs, out, seed, params):
        return their_make(as_theirs(inputs), out, seed, params)
    return made


def judge(their_judge):
    @functools.wraps(their_judge)
    def judged(output, inputs, evidence):
        return their_judge(output, as_theirs(inputs), evidence)
    return judged
