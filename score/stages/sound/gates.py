"""The sound stage's gates, each read off the output's record and its files (measured again, never trusted from the
record): sources, level, likeness and no freesound (the stage's docstring says what each passes on)."""
import json
import pathlib
import sys

from score import checks

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in ("tools/sound/picker", "tools/sound/loudness"):
    sys.path.insert(0, str(REPO / folder))
import choose  # noqa: E402
import loudness  # noqa: E402
import takes as picker_takes  # noqa: E402

RECORD = "sound.json"
# The CLAP floor (cosine of a take's and its prompt's embeddings): the tenth percentile of the 55 MOSS takes the world
# plays (sounds.json `chosen.clap`, measured by moss_generate.py on 2026-10-06: 0.12 to 0.61, median 0.41). Under it
# lie only short clicks CLAP barely hears (a desk lock, a radio's click in and out, a beep, a planting robot).
CLAP_FLOOR = 0.30
# Nothing plays longer than its brief by more than this, in seconds; a loop or room tone keeps at least
# choose.KEPT_SHARE of its brief.
OVER_BRIEF_SECONDS = 0.5
# One step of a walk (a surface's footstep takes) lasts at most this, in seconds.
STEP_SECONDS = 2.0
FREESOUND = "freesound.org"


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def record_of(output):
    return read_json(pathlib.Path(output) / RECORD)


# --- sources --------------------------------------------------------------------------------------------------------

def standing(inputs):
    """What an object sound may play at: the inventory's row ids and the scene record's named objects."""
    names = set()
    if "inventory" in inputs:
        names |= {row["id"] for row in read_json(inputs["inventory"]).get("rows", [])}
    scene = read_json(inputs["scene"])
    for part in ("objects", "structure"):
        names |= {entry["name"] for entry in scene.get(part, []) if isinstance(entry, dict) and entry.get("name")}
    return names


def judge_sources(output, inputs, evidence):
    """Pass when every source the place names has a sound with files, and every object sound plays at a row or object
    that stands in the place."""
    record = record_of(output)
    there = standing(inputs)
    faults = [f"{use['sound']} ({use['role']}, {use['from']}): no sound" for use in record["uses"]
              if not record["sounds"].get(use["sound"], {}).get("files")]
    faults += [f"{use['sound']} plays at {use['on']}, which the place's inventory and scene do not hold"
               for use in record["uses"] if use["role"] == "object" and use["on"] not in there]
    if not record["uses"]:
        return checks.Verdict("sources", checks.UNKNOWN, "the place names no source of sound")
    roles = {role: sum(use["role"] == role for use in record["uses"]) for role in ("room", "object", "motion", "bank")}
    reason = (f"{len(faults)} of {len(record['uses'])} sources lack a sound or a place to play" if faults else
              f"all {len(record['uses'])} sources have a sound ({', '.join(f'{n} {r}' for r, n in roles.items())})")
    return checks.Verdict("sources", checks.FAIL if faults else checks.PASS, reason,
                          {"sources": len(record["uses"]), "without": len(faults)}, {"without": "lower"},
                          tuple(faults))


# --- level ----------------------------------------------------------------------------------------------------------

def length_fault(sound, seconds, file_count):
    """Why a file's length is off its brief, or None."""
    category, brief = sound.get("category"), sound.get("brief_seconds")
    if category == "steps" or (category is None and file_count > 1):
        return None if seconds <= STEP_SECONDS else f"a step of {seconds:.2f} s (over {STEP_SECONDS} s)"
    if not brief:
        return None
    longest = max(float(brief), picker_takes.SHOT_SECONDS if category == "shot" else 0.0) + OVER_BRIEF_SECONDS
    shortest = choose.KEPT_SHARE.get(category, 0.0) * float(brief)
    if seconds > longest:
        return f"{seconds:.2f} s, longer than its brief's {brief} s"
    if seconds < shortest:
        return f"{seconds:.2f} s, under {shortest:.1f} s of its brief's {brief} s"
    return None


def file_faults(name, sound, path):
    """A file's faults against its category's loudness and its brief's length, and its measures."""
    measured = loudness.measure(path)
    seconds = loudness.seconds_of(path)
    faults = []
    if measured["true_peak"] > loudness.CEILING_DBTP:
        faults.append(f"{name}: {path.name} peaks at {measured['true_peak']} dBTP")
    category = sound.get("category")
    if category:
        target = loudness.TARGETS[picker_takes.TARGET[category]]
        if not loudness.is_kept(measured, target):
            faults.append(f"{name}: {path.name} at {measured['lufs']} LUFS, off its {category} target {target}")
    else:
        faults.append(f"{name}: no category, so no loudness target")
    late = length_fault(sound, seconds, len(sound["files"]))
    if late:
        faults.append(f"{name}: {path.name} {late}")
    return faults, {**measured, "seconds": round(seconds, 2)}


def judge_level(output, inputs, evidence):
    """Pass when every file is under the true-peak ceiling, within its category's loudness target and its brief's
    length, each measured here."""
    record = record_of(output)
    faults, loudest, files = [], None, 0
    for name, sound in record["sounds"].items():
        for path in sound["files"]:
            found, measured = file_faults(name, sound, pathlib.Path(output) / path)
            faults += found
            files += 1
            loudest = measured["lufs"] if loudest is None else max(loudest, measured["lufs"])
    if not files:
        return checks.Verdict("level", checks.UNKNOWN, "no file to measure")
    reason = (f"{len(faults)} faults over {files} files" if faults else
              f"all {files} files within their level and length (loudest {loudest} LUFS)")
    return checks.Verdict("level", checks.FAIL if faults else checks.PASS, reason,
                          {"files": files, "faults": len(faults), "loudest lufs": loudest}, {"faults": "lower"},
                          tuple(faults))


# --- likeness -------------------------------------------------------------------------------------------------------

def judge_likeness(output, inputs, evidence):
    """Pass when every MOSS-made sound matches its prompt at least CLAP_FLOOR; one with no score is unknown. A
    recording or a made file has no prompt and is listed, not judged."""
    record = record_of(output)
    made = {name: sound for name, sound in record["sounds"].items() if sound["made_by"] == "moss"}
    unscored = [name for name, sound in made.items() if sound.get("clap") is None]
    low = [f"{name}: CLAP {sound['clap']} under {CLAP_FLOOR}" for name, sound in made.items()
           if sound.get("clap") is not None and sound["clap"] < CLAP_FLOOR]
    others = [f"{name}: {sound['made_by']}, not judged" for name, sound in record["sounds"].items()
              if sound["made_by"] != "moss"]
    scores = [sound["clap"] for sound in made.values() if sound.get("clap") is not None]
    measures = {"made": len(made), "lowest clap": min(scores) if scores else None}
    if low:
        return checks.Verdict("likeness", checks.FAIL, f"{len(low)} of {len(made)} MOSS sounds under {CLAP_FLOOR}",
                              measures, {"lowest clap": "higher"}, tuple(low))
    if unscored or not made:
        return checks.Verdict("likeness", checks.UNKNOWN, f"no CLAP score for {unscored or 'any sound'}", measures)
    return checks.Verdict("likeness", checks.PASS, f"all {len(made)} MOSS sounds at least {CLAP_FLOOR} "
                          f"(lowest {min(scores)})", measures, {"lowest clap": "higher"}, tuple(others))


# --- no freesound ---------------------------------------------------------------------------------------------------

def judge_no_freesound(output, inputs, evidence):
    """Pass when no file is a Freesound recording, but those the owner chose over the generated takes (its brief's
    `chosen.by` is the owner, with his decision), which are listed."""
    record = record_of(output)
    fetched = {name: sound for name, sound in record["sounds"].items()
               if any(FREESOUND in credit.get("source", "") for credit in sound["credits"])}
    owners = {name: sound for name, sound in fetched.items() if sound.get("chosen_by") == "owner" and sound.get("decided")}
    left = sorted(set(fetched) - set(owners))
    kept = tuple(f"{name}: the owner's pick ({sound['decided'][:80]})" for name, sound in owners.items())
    if left:
        return checks.Verdict("no freesound", checks.FAIL, f"{len(left)} sounds are Freesound picks: {left}",
                              {"freesound": len(left)}, {"freesound": "lower"}, tuple(left) + kept)
    return checks.Verdict("no freesound", checks.PASS,
                          "no Freesound pick" + (f" but the owner's {len(owners)} chosen recordings" if owners else ""),
                          {"freesound": 0, "owner's recordings": len(owners)}, {"freesound": "lower"}, kept)
