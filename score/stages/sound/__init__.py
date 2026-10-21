"""The sound stage (experimental, PRD #6, until the owner has heard it): a place's sound layer data, every sound the
place plays with its files, its level, where it plays and who made it, for the place's assembly to write into its
OpenUSD stage (tools/usd/sound.py's layout: room tones, objects' sounds, motions' sounds, the surfaces' bank).

    make     every source the place's design names (its bed, beds.py: its room tone, or what the suit lets through
             outside where no air carries sound; each scene inventory row whose row kind sounds
             (data/checks/row-kinds.json `sound`) at that row; a voice (data/sound/voices.json) on its cast's first
             person; its motions'
             `sounds`; the sounds data/sound/moving.json gives its moving things and its silent motions by each one's
             row kind and move, timed off their moves (moving.py); every surface's footstep, impact and scrape in
             data/sound/surfaces.json) answered by
             one sound: the world's file of a sound already picked (a MOSS take, a file tools/sound/made.py makes, or
             a recording the owner chose over the takes), else one MOSS take of its brief (its first prompt, seed 1)
             made in the moss image on a rented card (PAID, takes.py), brought to its category's loudness and judged
             by the picker's rule (its CLAP match to its prompt less its faults, tools/sound/picker); `sound.json` and
             the files under `files/`
    gates    sources   every source has a sound with its files, and every object it plays at stands in the place's
                       scene inventory, plan or cast
             bed       its design decides its bed (beds.py): what the design lacks, or that no library bed fits, fails
             level     every file, measured: its true peak under the ceiling, its loudness within its category's
                       target (tools/sound/loudness), its length within its brief
             likeness  every MOSS-made sound's CLAP match to its prompt at least gates.CLAP_FLOOR
             no freesound  no file is a Freesound recording but those the owner chose over the generated takes and
                       those under CC0 with their row in data/sound/licences.json (the owner, 2026-10-20, #29)
             events    every thing that moves in the place (needs.events: its motion and moving things records) plays a sound
             voices    a place whose cast stands people plays a voice on one of them (#29: voices where people are)

Every designed scene has the row (score/stages/design_layers.py, the stage table's and the assembly's one answer);
its plan and scene inventory are the design's (beds.files: under {home}/design, where the creator's are kept), else
data/'s.
"""
import json
import pathlib
import shutil
import sys

from score import checks, contracts
from score.stages import batch_gaps
from score.stages.sound import beds
from score.stages import row_kinds
from score.stages.sound import gates
from score.stages.sound import moving
from score.stages.sound import needs
from score.stages.sound import takes as moss_takes
from score.stages.sound.gates import FREESOUND, RECORD, read_json

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in ("tools/sound/picker", "tools/sound/loudness", "tools/usd", "tools/library"):
    sys.path.insert(0, str(REPO / folder))
import apply as picker_apply  # noqa: E402
import loudness  # noqa: E402
import takes as picker_takes  # noqa: E402
import page as picker_page  # noqa: E402
import sources as picker_sources  # noqa: E402
import stage_inputs  # noqa: E402
import library_files  # noqa: E402

FILES = "files"
HAPPENINGS = ("footstep", "impact", "scrape")
MADE_BY_MOSS = "MOSS"
# One rented L4 for a place's new briefs (8 takes a brief, about 30 s each): about EUR 0.2 measured on the image's
# proof; the estimate leaves room for a slow card and a second claim.
EUROS = 1.0


def files(place):
    """What the stage reads: the sound data (each file a versioned library reference), the row kinds, the place's
    design (beds.files: its plan and scene inventory, and its bed's setting) and its motion and cast records (where its
    sounds play)."""
    found = {"sounds": "{data}/sound/sounds.json", "catalogue": "{data}/sound/catalogue.json",
             "surfaces": "{data}/sound/surfaces.json", "licences": "{data}/sound/licences.json",
             "voices": "{data}/sound/voices.json"}
    inventory = stage_inputs.inventory_path(place)
    if inventory.exists():
        found["inventory"] = "{data}/inventory/" + inventory.name
    if (REPO / f"data/motion/{place}.json").exists():
        found["motion"] = "{data}/motion/{place}.json"
    if (REPO / f"data/motion/rigid/{place}.json").exists():
        found["moves"] = "{data}/motion/rigid/{place}.json"
    found["moving sounds"] = "{data}/sound/moving.json"
    found["row kinds"] = "{data}/checks/row-kinds.json"
    if (REPO / f"data/characters/{place}.json").exists():
        found["cast"] = "{data}/characters/{place}.json"
    return {**found, **beds.files(place)}


def place_of(inputs):
    """The place, by its design's name (its plan, else its scene inventory: each named for it)."""
    return pathlib.Path(inputs.get("plan") or inputs["scene inventory"]).stem


def inventory_rows(inputs):
    """The place's scene inventory rows: its design's (beds.files' `scene inventory`), else data/inventory's."""
    path = inputs.get("scene inventory") or inputs.get("inventory")
    return read_json(path).get("rows", []) if path else []


# --- the sources ----------------------------------------------------------------------------------------------------

def row_sound(row, kind, kinds):
    """The library sound a row of a sounding kind plays: its kind's one sound, or the one its reading noun names
    (None: a noun the kind leaves silent)."""
    named = kinds[kind].get("sound")
    if isinstance(named, dict):
        return named.get(row_kinds.words(row.get("noun")) or row_kinds.words(row.get("name") or row.get("id"))
                         .rsplit(" ", 1)[-1])
    return named


def object_uses(inputs):
    """The sounds of the scene inventory's objects: each row whose kind sounds (data/checks/row-kinds.json), its
    kind's sound at the row."""
    kinds = row_kinds.table(inputs["row kinds"])
    uses = []
    for row in row_kinds.rows_that({"rows": inventory_rows(inputs)}, "sounds", kinds):
        name = row_sound(row, row["row_kind"], kinds)
        if name:
            uses.append({"sound": name, "role": "object", "on": row["id"],
                         "from": f"scene inventory row {row['id']}, a {row['row_kind']} (data/checks/row-kinds.json)"})
    return uses


def voice_uses(inputs):
    """The voice of the place's people (data/sound/voices.json), on its cast's first person; none with no one."""
    people = needs.people(read_json(inputs["cast"])) if "cast" in inputs else []
    if not people:
        return []
    return [{"sound": read_json(inputs["voices"])["people"], "role": "object", "on": people[0],
             "from": "data/sound/voices.json people, its cast's first person"}]


def uses_of(place, inputs):
    """Every place the place plays a sound from: [{sound, role, on, from}]."""
    uses = [{"sound": name, "role": "room", "on": None, "from": "the scene's design (score/stages/sound/beds.py)"}
            for name in beds.of_place(place, inputs)["sounds"]]
    uses += object_uses(inputs) + voice_uses(inputs)
    if "motion" in inputs:
        uses += [{"sound": sound["name"], "role": "motion", "on": motion.get("prim", ""), "at": sound.get("at"),
                  "loops_until": sound.get("loops_until"), "from": sound.get("from", "")}
                 for motion in read_json(inputs["motion"]).get("motions", []) for sound in motion.get("sounds", [])]
    return uses + moving_uses(inputs) + bank_uses(read_json(inputs["surfaces"]))


def moving_uses(inputs):
    """The sounds of the place's moving things that play none of their own (data/sound/moving.json, by each one's row
    kind and move): one set for each event of its silent game motions and its moving things (needs.events)."""
    if "moving sounds" not in inputs:
        return []
    table, kinds = read_json(inputs["moving sounds"]), row_kinds.table(inputs["row kinds"])
    rows = inventory_rows(inputs)
    moves = read_json(inputs["moves"]) if "moves" in inputs else {}
    motions = read_json(inputs["motion"]).get("motions", []) if "motion" in inputs else []
    renamed = moves.get("renamed", {})
    return [found for event in needs.events(motions, moves.get("moves", []), renamed)
            for found in moving.event_uses(event, rows, kinds, table, renamed)]


def bank_uses(surfaces):
    """Every surface's footstep, impact and scrape as bank sounds."""
    found = {}
    for surface, sounds in surfaces["surfaces"].items():
        for happening in HAPPENINGS:
            if sounds.get(happening):
                found.setdefault(sounds[happening], []).append(f"{surface} {happening}")
    return [{"sound": name, "role": "bank", "on": ", ".join(where), "from": "data/sound/surfaces.json"}
            for name, where in found.items()]


def entry_of(name, inputs):
    """A sound's fields as the game read them: the catalogue's defaults, its entry, the data's over it (its brief
    apart); a sound only the data names takes its loop from its brief."""
    catalogue, sounds = read_json(inputs["catalogue"]), read_json(inputs["sounds"])["sounds"]
    filled = {**catalogue["defaults"], **catalogue["sounds"].get(name, {}),
              **{key: value for key, value in sounds.get(name, {}).items() if key != "pick"}}
    if name not in catalogue["sounds"] and sounds.get(name, {}).get("pick", {}).get("loop"):
        filled["loops"] = True
    filled.pop("note", None)
    return filled


def listed(named):
    if not named:
        return []
    return [named] if isinstance(named, str) else list(named)


# --- a sound picked already -----------------------------------------------------------------------------------------

def levelled(paths, category, loops):
    """The files of a sound brought to its category's loudness (the loudness rule), when any is off it; the dB its
    volume moves by so it plays as loud as before (its loudest file's change, as tools/sound/picker/apply.py levels)."""
    target = loudness.TARGETS[picker_takes.TARGET[category]]
    before = {path: loudness.measure(path) for path in paths}
    if all(loudness.is_kept(measured, target) for measured in before.values()):
        return 0.0
    after = {}
    for path in paths:
        source = path.with_name(f"before-{path.name}")
        path.rename(source)
        after[path] = loudness.normalise(source, path, target, fade_ms=0 if loops else 8)
        source.unlink()
        if after[path] is None:
            raise RuntimeError(f"{path.name} cannot be brought to {target} LUFS under the loudness rule")
    return max(measured["lufs"] for measured in before.values()) - max(measured["lufs"] for measured in after.values())


def picked(name, brief, entry, inputs, out):
    """A sound the world already plays: its files copied from the library (each under its stage name), its credit
    from the licence list; a file the library does not hold (a gap) is left out."""
    licences = {listing["file"]: listing for listing in read_json(inputs["licences"])}
    names = []
    for world_name in listed(entry.get("file")):
        source = library_files.resolve(world_name)
        if source is None:
            library_files.say_gap(world_name, f"the sound {name}")
            continue
        target = out / FILES / library_files.stage_name(world_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        names.append(world_name)
    credits = [licences.get(world_name, {"file": world_name}) for world_name in names]
    volume = float(entry.get("volume_db", 0.0))
    if brief.get("category") and names:
        volume += levelled([out / FILES / library_files.stage_name(world_name) for world_name in names],
                           brief["category"], bool(entry.get("loops")))
    chosen = brief.get("chosen", {})
    made_by = ("gap" if not credits else
               "moss" if all(MADE_BY_MOSS in credit.get("source", "") for credit in credits) else
               "recording" if any(FREESOUND in credit.get("source", "") for credit in credits) else "made")
    prompt, seed = None, None
    if made_by == "moss" and chosen.get("take", "").startswith("moss:"):
        stem = chosen["take"][5:]
        prompt = brief["prompts"][int(stem.split("__p")[1].split("__")[0]) - 1]
        seed = int(stem.rsplit("__s", 1)[1])
    return {"files": [f"{FILES}/{library_files.stage_name(world_name)}" for world_name in names],
            "volume_db": round(volume, 1),
            "made_by": made_by, "credits": credits, "prompt": prompt, "seed": seed, "clap": chosen.get("clap"),
            "chosen_by": chosen.get("by", "the game's catalogue"), "decided": chosen.get("decided")}


# --- a sound made here ----------------------------------------------------------------------------------------------

def need_of(name, brief):
    """The picker's need for a brief (tools/sound/picker/needs.py's shape)."""
    return {"name": name, "category": brief["category"], "where": brief["where"], "loop": bool(brief.get("loop")),
            "seconds": float(brief.get("seconds", 8)), "level": brief.get("level"), "before": name, "now": []}


def candidates(name, jobs, scored, weights):
    """The picker's candidates of a brief's takes that came back, each with its CLAP score."""
    return [picker_sources.Candidate(
        "moss", f"moss:{pathlib.Path(job['file']).stem}", f"Generated, seed {job['seed']}",
        f"generated with MOSS-SoundEffect v2.0 ({weights})", picker_sources.Moss.LICENCE, moss_takes.MODEL_PAGE,
        (moss_takes.TAKES / job["file"]).as_uri(), float(job["seconds"]), prompt=job["prompt"], seed=job["seed"],
        clap=scored[job["file"]]) for job in jobs if job["file"] in scored]


def generated(name, brief, out, weights, scored):
    """A sound made here: its brief's MOSS takes (made, with their CLAP scores in `scored`), each brought to its
    category's loudness and judged, the best one's files into the output at the level its brief asks (or its
    category's)."""
    jobs = moss_takes.jobs_for(name, brief, weights)
    need = need_of(name, brief)
    kept = picker_page.made_safe(need, candidates(name, jobs, scored, weights), out / "work")
    judged = picker_page.page_need(need, kept)
    take = next((take for take in judged["takes"] if take["key"] == judged["chosen"]), None)
    if take is None:
        return None
    files_out = []
    for page_file, world_name in picker_apply.world_files_for(need, take):
        target = out / FILES / world_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / "work" / page_file, target)
        files_out.append(world_name)
    level = float(brief["level"]) if brief.get("level") is not None else picker_apply.LEVELS[brief["category"]]
    loudest = max(take["measures"][page_file]["lufs"] for page_file in take["files"])
    return {"files": [f"{FILES}/{world_name}" for world_name in files_out],
            "volume_db": round(min(level - loudest, 0.0), 1), "made_by": "moss",
            "credits": [{"file": world_name, "source": f"{moss_takes.MODEL_PAGE}; prompt: {take['prompt']}; "
                                                      f"seed {take['seed']}",
                         "author": take["author"], "licence": take["licence"]} for world_name in files_out],
            "prompt": take["prompt"], "seed": take["seed"], "clap": take["clap"], "faults": take["faults"],
            "chosen_by": "scoring", "takes": len(jobs), "kept": len(kept)}


def brief_of(name, inputs):
    return read_json(inputs["sounds"])["sounds"].get(name, {}).get("pick", {})


def to_make(names, inputs):
    """The sounds no world file answers whose brief has prompts: the ones made here."""
    return [name for name in names if not entry_of(name, inputs).get("file") and brief_of(name, inputs).get("prompts")]


def sound_of(name, inputs, out, weights, scored):
    """One sound's record: picked already, made here, or None (no file and no brief)."""
    entry = entry_of(name, inputs)
    brief = brief_of(name, inputs)
    if entry.get("file"):
        found = picked(name, brief, entry, inputs, out)
    elif brief.get("prompts"):
        found = generated(name, brief, out, weights, scored)
    else:
        return None
    if found is None:
        return None
    return {**found, "bus": entry.get("bus", ""), "loops": bool(entry.get("loops")),
            "reach": float(entry.get("reach", 0.0)), "ground_thud": bool(entry.get("ground_thud", False)),
            "category": brief.get("category"), "brief_seconds": brief.get("seconds")}


def moss_weights():
    """The pinned MOSS weights' revision (a take's name hashes it)."""
    from score.adapters import models
    return next(model["revision"] for model in models.record(moss_takes.KIND)["models"]
                if model["name"] == moss_takes.MODELS[0])


def jobs_of(names, inputs, weights):
    """The take jobs of the sounds among `names` made here."""
    return [job for name in to_make(names, inputs) for job in moss_takes.jobs_for(name, brief_of(name, inputs), weights)]


def environment_takes(data, weights):
    """The environment's takes still to make, each once (#29): {take file: (job, [the places that play it])}, in
    beds.places' order. A brief several places play is one take: the first of their lines to reach it
    makes it in its batch (takes.made locks it), the others wait and read it, so it is made and counted once."""
    found = {}
    for place in beds.places(data):
        inputs = {name: pathlib.Path(pattern.format(place=place, data=str(data), home=str(beds.DESIGN.parent)))
                  for name, pattern in files(place).items()}
        names = list(dict.fromkeys(use["sound"] for use in uses_of(place, inputs)))
        for job in moss_takes.missing(jobs_of(names, inputs, weights)):
            found.setdefault(job["file"], (job, []))[1].append(place)
    return found


def make(inputs, out, seed, params):
    """The place's sound layer data: sound.json and every file it names under files/."""
    place = place_of(inputs)
    weights = moss_weights()
    uses = uses_of(place, inputs)
    names = list(dict.fromkeys(use["sound"] for use in uses))
    jobs = jobs_of(names, inputs, weights)
    scored = moss_takes.made(jobs, out / "cloud") if jobs else {}  # every new brief's takes on one card
    sounds = {}
    for name in names:
        found = sound_of(name, inputs, out, weights, scored)
        if found is not None:
            sounds[name] = found
    shutil.rmtree(out / "work", ignore_errors=True)
    shutil.rmtree(out / "cloud", ignore_errors=True)
    made_here = to_make(names, inputs)
    batch_gaps.write(out, take_gaps(made_here, sounds, uses))
    kept = [use for use in uses if use["sound"] in sounds or use["sound"] not in made_here]
    (out / RECORD).write_text(json.dumps({"place": place, "sounds": sounds, "uses": kept}, indent=1))


def take_gaps(made_here, sounds, uses):
    """The batch gaps of the sounds made here (score/stages/batch_gaps.py), each a gap by the creator's yes to the
    batch (a new take is a new batch): a brief whose take did not come back usable has no sound, its uses left out of
    the record (the gap names each, so the assembly plays nothing in its place); a take under gates.CLAP_FLOOR plays,
    its `likeness` fault moved to the gap (stages.BATCH_GATES)."""
    found = []
    for name in made_here:
        if name not in sounds:
            found.append(batch_gaps.gap(
                f"{name}: no MOSS take came back", "sound", "sources", (name,),
                [f"{name}: no sound ({use['role']}, {use['from']})" for use in uses if use["sound"] == name],
                "its MOSS take was asked once in the batch and did not come back usable; its uses left out"))
        elif sounds[name].get("clap") is not None and sounds[name]["clap"] < gates.CLAP_FLOOR:
            found.append(batch_gaps.gap(
                f"{name}: MOSS take under the CLAP floor", "sound", "likeness", (name,),
                [f"{name}: CLAP {sounds[name]['clap']} under {gates.CLAP_FLOOR}"],
                "its one MOSS take of the batch came back under the CLAP floor"))
    return found


def layer_faults(folder):
    """The record is there and every file it names is in the output."""
    folder = pathlib.Path(folder)
    if not (folder / RECORD).exists():
        return [f"no {RECORD}"]
    record = read_json(folder / RECORD)
    return [f"{name}: {path} is missing" for name, sound in record["sounds"].items() for path in sound["files"]
            if not (folder / path).exists()]


LAYER = contracts.Contract("sound-layer", 1, layer_faults, {"time": "second"})
CHECKS = (checks.Check("sources", gates.judge_sources), checks.Check("bed", gates.judge_bed),
          checks.Check("level", gates.judge_level),
          checks.Check("likeness", gates.judge_likeness), checks.Check("no freesound", gates.judge_no_freesound),
          checks.Check("events", gates.judge_events), checks.Check("voices", gates.judge_voices))
