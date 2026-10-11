"""The complete stage (P11): a place's manifest, made from the store and never from file times.

The runner makes it only once every stage before it passed its gates and stands accepted, so its
manifest names, for each of them, the accepted output it read (an earlier stage's input is a checkout named by its
output's hash). Its gate checks the manifest names one for every stage it reads.
"""
import json

from score import checks


def make_manifest(inputs, out, seed, params):
    """Write the manifest: each earlier stage with the accepted output read."""
    (out / "manifest.json").write_text(json.dumps({"stages": {name: path.name for name, path in inputs.items()}},
                                                  indent=1))


def judge_manifest(output, inputs, evidence):
    """Pass when the manifest names the output read for every stage before it."""
    named = json.loads((output / "manifest.json").read_text())["stages"]
    missing = sorted(name for name, path in inputs.items() if named.get(name) != path.name)
    if missing:
        return checks.Verdict("manifest", checks.FAIL, f"the manifest lacks {', '.join(missing)}",
                              {"missing": len(missing)}, {"missing": "lower"})
    return checks.Verdict("manifest", checks.PASS, f"every stage before it passed and was accepted: {', '.join(named)}")


CHECKS = (checks.Check("manifest", judge_manifest),)
