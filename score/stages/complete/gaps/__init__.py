"""Gaps: what each place still needs over its accepted stage (its __main__ docstring has the files and the
contract). Where the gaps check writes, kept here so its readers (price.py, `score price --gaps`) import no pxr."""
from score.store import PROPS_HOME

OUT = PROPS_HOME / "work/checks/gaps"  # <place>/findings.json, where the cockpit and the price read them
FINDINGS = "findings.json"
WORLD = "world"  # the pseudo-place of the environment's own nodes' lost inputs (inputs.lost over place None)
MISSING, GATE, PLACE = "missing", "gate", "place"  # a finding's rule, its id's prefix (`<rule>:<gap id>`)
