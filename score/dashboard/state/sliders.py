"""The breakdown's before and after pictures: where a step changes a picture taken from the same camera, the two
pictures a slider wipes between (`wipe`); where the two are of one thing from views that do not line up (a close-up
picture and the model made from it, the concept and the film), the two side by side. Read from the steps' own
files, so the local and the hosted source give the same pairs, and the export carries their large pictures
(sync/building.py)."""
import re

SHOT = re.compile(r"/(shot\d+)-\d+-look\.png$")
CLOSEUP = re.compile(r"^closeups/(.+)\.png$")
MODEL = re.compile(r"^cut/(.+)\.png$")
LIKENESS_SHOWN = 4  # the things whose close-up and model are shown side by side, at most


def slider(section, before, after, words, wipe=True):
    """One pair: the section it sits in, the two FileRefs, what it shows in words, and whether the two line up so a
    slider wipes between them (else they stand side by side)."""
    return {"section": section, "before": before, "after": after, "before_words": words[0],
            "after_words": words[1], "words": words[2], "wipe": wipe}


def shots(files):
    """{shot name: the shot's look picture} of a light step's files."""
    found = {}
    for ref in files:
        matched = SHOT.search(ref.name)
        if matched and ref.kind == "image":
            found.setdefault(matched.group(1), ref)
    return found


def light_pair(passes, swept):
    """The first shot both light steps drew: before the sweep (the lamps as placed) and after it."""
    before, after = shots(passes.files if passes else []), shots(swept.files if swept else [])
    common = sorted(set(before) & set(after))
    if not common:
        return []
    return [slider("light", before[common[0]], after[common[0]],
                   ("lamps as placed", "after the light sweep", "The light before and after the sweep"))]


def named(files, pattern):
    """{name: FileRef} of the files whose name the pattern matches, by its first group."""
    found = {}
    for ref in files:
        matched = pattern.match(ref.name)
        if matched:
            found[matched.group(1)] = ref
    return found


def likeness_pairs(closeup, likeness):
    """Each thing's close-up picture beside the model made from it, at most LIKENESS_SHOWN."""
    pictures = named(closeup.files if closeup else [], CLOSEUP)
    models = named(likeness.files if likeness else [], MODEL)
    things = sorted(set(pictures) & set(models))[:LIKENESS_SHOWN]
    return [slider("pieces", pictures[thing], models[thing],
                   ("its close-up picture", "the model made", thing.replace("_", " ").capitalize()), wipe=False)
            for thing in things]


def result_pair(concept, film):
    """The concept beside the film's first frame (its camera is the one nearest the concept)."""
    first = next((ref for ref in (film.files if film else []) if ref.name == "concept.png"), None)
    if not concept or not first:
        return []
    return [slider("result", concept, first, ("the concept", "the film's first frame",
                                              "What it was meant to be, and what was made"), wipe=False)]


def pairs(detail, step_of):
    """Every pair of a place: `step_of(stage)` gives a step's StepDetail or None."""
    return (likeness_pairs(step_of("closeup"), step_of("likeness"))
            + light_pair(step_of("light-passes"), step_of("light"))
            + result_pair(detail.concept, step_of("demo-film")))
