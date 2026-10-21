"""people-clips-made (world, paid; #26): the Kimodo clips every body row plays, made on the people line's batch with
the fixed seed (tools/characters/people/clips.py CLIP_SEED), and SOMA-X's mean rig holding them (prop_skeleton.py),
on one rented characters machine (tools/characters/maker/prop_person.py clips_rig: prop_chain.py clips then rig).
Its output is `rig.npz` (the mean skeleton, the weights' source and each clip, every look's: prop_rig.py fits it into
each take), `motions/` (each clip's npz and record) and `make.json` (the machine's minutes); the body rows read it
(`after`), so the clips lost on 2026-10-19 are made again inside the batch, never read from a work folder.

Gate `clips made` (unknown blocks): every clip of CLIPS is in the rig and its record names its seed.
"""
import json
import pathlib
import sys

import numpy as np

from score import contracts, graph
from score.checks import FAIL, PASS, UNKNOWN, Check, Verdict

REPO = pathlib.Path(__file__).resolve().parents[3]
MAKER = REPO / "tools/characters/maker"
ROW = "people-clips-made"
# The clips the places' people do (people_rows.doing_of: standing, walking, sitting) and one working clip (bench, a
# person at a workbench using both hands), which the people benchmark judges (#26). A cast's clip outside these is
# no clip of its body, and people-clips fails that cast by name.
CLIPS = ("standing", "walking", "bench", "sitting")
# Not measured: four Kimodo clips and the rig on one L4 with its set-up (about 14 minutes) and the chain's minutes,
# about 40 minutes at EUR 0.79 an hour, rounded up.
EUROS = 0.6


def make_clips(inputs, out, seed, params):
    sys.path.insert(0, str(MAKER))
    import prop_person
    prop_person.clips_rig(params["clips"], out, ROW, False)


def clips_faults(folder):
    return [f"no {name}" for name in ("rig.npz", "motions") if not (pathlib.Path(folder) / name).exists()]


def judge_clips_made(output, inputs, evidence):
    """Every wanted clip in the rig, its record naming its seed."""
    with np.load(output / "rig.npz") as rig:
        held = set(rig.files)
    failing = []
    for clip in CLIPS:
        record = output / "motions" / f"{clip}.record.json"
        if f"clip_{clip}" not in held:
            failing.append(f"{clip}: not in the rig")
        elif not record.exists():
            failing.append(f"{clip}: no record")
        elif json.loads(record.read_text()).get("seed") is None:
            failing.append(f"{clip}: its record names no seed")
    return Verdict("clips made", FAIL if failing else PASS, "; ".join(failing) or f"{len(CLIPS)} clips in the rig",
                   {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


def judged(output, inputs, evidence):
    """judge_clips_made, a missing or unreadable record answering unknown, never pass."""
    try:
        return judge_clips_made(output, inputs, evidence)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as missing:
        return Verdict("clips made", UNKNOWN, f"cannot tell: {type(missing).__name__}: {missing}")


ROW_STAGE = graph.Stage(ROW, "world", make_clips, contracts.Contract(ROW, 1, clips_faults),
                        (Check("clips made", judged),),
                        files={"maker": "{repo}/tools/characters/maker", "people tools": "{repo}/tools/characters/people"},
                        params={"clips": list(CLIPS)}, paid=True, euros=EUROS)
