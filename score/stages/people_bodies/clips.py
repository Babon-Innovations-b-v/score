"""A body judged clip by clip (captain, 2026-10-13): a clip is usable only when it passes every per-clip check; the
body records its passing and failing clips with their numbers, and a cast may use only passing clips. Nothing is
hidden: a failing clip stays on the body's record and its page with what failed and by how much.

Per-clip checks, from the body's records (checks/pokes.json, checks/bodycloth.json):
    tucks               no tuck point over pokes.POKE_MM outside the person's surface in any frame of the clip
    rigid               the hard parts' edges at most RIGID_MOST of their bind length
    cloth through cloth the clip's worst garment crossings no more than the shipped body's same clip
    body through cloth  no part's own edges deeper than the margin through the cloth more often than at the bind
"""
import json
import pathlib

RIGID_MOST = 1.2


def per_clip(output):
    """{clip: {check: (passes, numbers in words)}} of a body's output folder."""
    pokes = json.loads((output / "checks" / "pokes.json").read_text())
    reference = output / "checks" / "pokes_shipped.json"  # absent: no shipped body wears it, held to its own rest
    shipped = json.loads(reference.read_text()) if reference.exists() else {"clips": {}}
    counted = json.loads((output / "checks" / "bodycloth.json").read_text())
    bind = counted["bind"]["deep_by_part"]
    found = {}
    for clip, record in pokes["clips"].items():
        bar = shipped["clips"].get(clip, {}).get("most_crossings", pokes["rest_crossings"])
        deep = counted["clips"].get(clip)
        over = {} if deep is None else {part: count for part, count in deep["deep_by_part"].items()
                                        if count > bind.get(part, 0)}
        found[clip] = {
            "tucks": (record["frames_tuck_over"] == 0, f"worst tuck {record['worst_tuck_out_mm']} mm"),
            "rigid": (record["rigid_stretch"] <= RIGID_MOST, f"hard parts at {record['rigid_stretch']}x"),
            "cloth through cloth": (record["most_crossings"] <= bar,
                                    f"{record['most_crossings']} crossings, the shipped body's {bar}"),
            "body through cloth": (deep is not None and not over,
                                   "not counted" if deep is None else
                                   f"over the bind {over}, deepest {deep['deepest_mm']} mm" if over else
                                   f"deepest {deep['deepest_mm']} mm")}
    return found


def usable(output):
    """(the clips passing every check, {failing clip: [what failed, in words]})."""
    found = per_clip(output)
    failing = {clip: [f"{check}: {words}" for check, (passes, words) in checks.items() if not passes]
               for clip, checks in found.items()}
    return sorted(clip for clip, faults in failing.items() if not faults), \
        {clip: faults for clip, faults in failing.items() if faults}


# --- people-clips: the casts held to the passing clips -------------------------------------------------------------

def bodies_of(inputs):
    """{look: its body output folder} of the row's inputs."""
    return {name[len("people-body-"):]: pathlib.Path(path) for name, path in inputs.items()
            if name.startswith("people-body-")}


def make_usable(inputs, out, seed, params):
    """usable.json: each full body's passing clips and its failing ones with what failed."""
    found = {}
    for look, folder in sorted(bodies_of(inputs).items()):
        passing, failing = usable(folder)
        found[look] = {"usable": passing, "failing": failing}
    (out / "usable.json").write_text(json.dumps(found, indent=1))


def usable_faults(folder):
    return [] if (folder / "usable.json").exists() else ["no usable.json"]


def cast_uses(rows_path):
    """[(place, person, look, clip)] of every person the places' designs show doing a clip (data/people/rows.json;
    a crowd's clips are its far body's, not judged here)."""
    from score.stages import people_rows
    found = json.loads(pathlib.Path(rows_path).read_text())
    return [(place, person["name"], person["look"], person["doing"]) for place in sorted(found["places"])
            for person in people_rows.persons(place, found)]


def judge_casts(output, inputs, evidence):
    """Every person the designs show wearing a full body does only clips that body passes."""
    from score.checks import FAIL, PASS, Verdict
    usable_clips = json.loads((output / "usable.json").read_text())
    failing, judged = [], 0
    for place, person, look, clip in cast_uses(inputs["casts"]):
        if look in usable_clips:
            judged += 1
            if clip not in usable_clips[look]["usable"]:
                faults = usable_clips[look]["failing"].get(clip, ["the body has no such clip"])
                failing.append(f"{place} {person} ({look}) does {clip}: {'; '.join(faults)}")
    return Verdict("casts use passing clips", FAIL if failing else PASS,
                   "; ".join(failing[:4]) or f"all {judged} cast clips pass",
                   {"failing": len(failing), "judged": judged}, {"failing": "lower"}, tuple(failing))
