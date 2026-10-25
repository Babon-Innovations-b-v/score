"""likeness-calibration@<place>: DINOv2's least likeness, set on the place's accepted models (paid, one rented machine).

The place's prop data names its accepted models and their close-ups (`accepted`: {model: {"model", "closeup"}}, the
models the owner accepted, as patterns). Each is scored as the likeness row scores a made model (likeness.py: the best
of eight ways round by outline, that way's silhouette beside the close-up's), and every pair by DINOv2 on a rented
machine (similar.py). The least likeness is the least accepted score less MARGIN, so every accepted model passes with
that margin, as likeness.OUTLINE_LEAST was set; the likeness row reads it from this row's calibration.json.
"""
import json

import score.stages.props.likeness as likeness
import score.stages.props.prop_data as prop_data
from score.stages.surfaces.surface_gates import verdict

MARGIN = 0.05
# 12 pairs on one processor machine, priced by similar.py --dry-run at about EUR 0.43 (2026-10-12), rounded up.
EUROS = 1.0


def make_calibration(inputs, out, seed, params):
    """outline.json (each accepted model's best way), the DINOv2 scores and calibration.json (the least likeness)."""
    accepted = prop_data.record_at(inputs["props"])["accepted"]
    scored, pairs = {}, {}
    for model in sorted(accepted):
        made, closeup = inputs[f"accepted model {model}"], inputs[f"accepted close-up {model}"]
        scored[model] = likeness.best_way(made, closeup)
        pairs[model] = likeness.write_pair(made, closeup, scored[model]["way"], out / "pairs", model,
                                           scored[model]["look_down"])
    (out / "outline.json").write_text(json.dumps(scored, indent=1))
    with prop_data.tools("cloud", "props"):
        import similar
        scores = similar.likeness(pairs, out / "likeness.json", "score likeness calibration")
    least = round(min(scores.values()) - MARGIN, 4) if len(scores) == len(pairs) and scores else None
    (out / "calibration.json").write_text(json.dumps({"scores": scores, "margin": MARGIN, "least": least}, indent=1))


def calibration_faults(folder):
    return [] if (folder / "calibration.json").exists() else ["no calibration.json"]


def judge_calibration(output, inputs, evidence):
    """Every accepted model scored, so the least likeness is set."""
    found = json.loads((output / "calibration.json").read_text())
    accepted = prop_data.record_at(inputs["props"])["accepted"]
    failing = [f"{model}: no DINOv2 score" for model in sorted(accepted) if model not in found["scores"]]
    return verdict("calibrated", failing, len(accepted), "accepted models",
                   {"least": found["least"] if found["least"] is not None else -1.0})


def least(folder):
    """The least likeness a calibration output set, or None."""
    return json.loads((folder / "calibration.json").read_text())["least"] if folder else None
