"""A place's breakdown, "How it was made", in the paper's order: the reference and concept, the plan, the pieces, each
OpenUSD layer (ground, base, settle, light, motion, effects, sound, characters, machines, crops), then the result.
Each step large, beside the pictures of what it read; a "show in 3D" per layer; a before and after slider where a
step changes a picture from the same camera; each problem beside the step it belongs to. Presentation only: it reads
the models of state/models.py."""
from score.dashboard.pages import present, seen
from score.dashboard.state import groups

# The sections in the paper's order: (key, title, what it adds, in a few plain words).
REFERENCE, PLAN, PIECES, RESULT = "reference", "plan", "pieces", "result"
LAYERS = (("ground", "Ground", "The ground under and around the place."),
          ("base", "Base", "The room itself, and where each thing stands."),
          ("settle", "Settle", "Things dropped to rest, so nothing floats or sinks."),
          ("light", "Light", "The lamps, and how the place is lit."),
          ("motion", "Motion", "What moves: doors, cranes, fans."),
          ("effects", "Effects", "Fog, steam, dust and sparks."),
          ("sound", "Sound", "What the place sounds like."),
          ("characters", "People", "The people in the place."),
          ("machines", "Machines", "The machines and their working parts."),
          ("crops", "Crops", "What grows here."))
SECTIONS = ((REFERENCE, "Reference and concept", "The look it is made in, and the picture of this place."),
            (PLAN, "Plan", "Where everything stands, read from the concept."),
            (PIECES, "Pieces", "Each thing in the place: its picture, its model, its finishes."),
            *LAYERS,
            (RESULT, "Result", "The whole place put together, checked against the concept, and filmed."))
LAYER_KEYS = {key for key, _, _ in LAYERS}
# The step groups of state/groups.py in the breakdown's sections; the plan is its own section ahead of the pieces.
GROUP_SECTION = {"base": "base", groups.STAGE_AND_FILMS: RESULT}
PLAN_STAGES = ("plan",)
# What a standalone check's finding is on, in the section that made it.
FINDING_SECTION = {"model": PIECES, "geometry": "base", "structure": "base", "place": "base", "light": "light",
                   "sound": "sound", "sky": "ground", "effect": "effects", "character": "characters",
                   "machine": "machines", "crop": "crops"}
FROM_SHOWN = 4
GROUP_PICTURES = 6  # the pictures a group of one check's findings shows
WORST = ("stopped", "waiting", "not run", "accepted")
NONE_HERE = "no steps here"  # a section with no step of this place's own


def section_of(group, stage):
    """The breakdown section a step of a layer group is shown in."""
    if stage in PLAN_STAGES:
        return PLAN
    return GROUP_SECTION.get(group, group)


def large(thumb):
    """The large picture behind a step card's thumbnail URL, or None."""
    return present.full_picture(thumb)


def card(step, place, step_url, pictured, wide):
    """One step as the breakdown shows it: its picture large, its state, and the pictures of what it read; `wide`
    a map drawn over the plan, shown at its own size so its words can be read."""
    sources = [pictured[read] for read in step.reads if read in pictured]
    return {"label": step.label, "url": step_url(place, step.stage), "thumb": step.thumb, "full": large(step.thumb),
            "state": step.state, "words": present.STATE_WORDS.get(step.state, step.state),
            "unseen": step.mark == seen.NOT_SEEN, "drawn": step.drawn and wide, "made_from": sources[:FROM_SHOWN],
            "more_from": max(0, len(sources) - FROM_SHOWN)}


def pictured_steps(detail, step_url):
    """{stage: {label, thumb, url}} of every step of the place with a picture, and the concept, for "made from"."""
    found = {step.stage: {"label": step.label, "thumb": step.thumb, "url": step_url(detail.place, step.stage)}
             for layer in detail.layers for step in layer.steps if step.thumb}
    if detail.concept:
        found["_concept"] = {"label": "the concept", "thumb": detail.concept.thumb_url, "url": detail.concept.url}
    return found


def plan_reads(card_found, pictured):
    """The plan reads the concept: shown as what it was made from."""
    if "_concept" in pictured and not card_found["made_from"]:
        card_found["made_from"] = [pictured["_concept"]]
    return card_found


def finding_groups(findings):
    """A standalone check's findings in one section, one group a rule: {rule, count, pictures, sentences}."""
    found = {}
    for finding in findings:
        found.setdefault(finding.rule, []).append(finding)
    return [{"rule": present.sentence(rule), "count": len(items),
             "pictures": [item.picture.thumb_url for item in items if item.picture][:GROUP_PICTURES],
             "sentences": [present.sentence(item.sentence) for item in items]} for rule, items in found.items()]


def problems_by_section(detail, sections_of_stage):
    """{section: [problem]} of every stopped step and named gap, each beside the step it belongs to; those without
    one go under the result."""
    found = {}
    for fault in detail.faults:
        stage = (fault.step_url or "").rstrip("/").rsplit("/", 1)[-1]
        found.setdefault(sections_of_stage.get(stage, RESULT), []).append(present.fault_problem(fault))
    for gap in detail.gaps:
        found.setdefault(sections_of_stage.get(gap.step, RESULT), []).append(present.gap_problem(gap, detail.place))
    return found


def findings_by_section(detail):
    """{section: [finding group]} of the standalone checks' findings, in the section that made what they are on."""
    found = {}
    for finding in detail.checks:
        found.setdefault(FINDING_SECTION.get(finding.kind or "", RESULT), []).append(finding)
    return {key: finding_groups(items) for key, items in found.items()}


def worst_state(cards):
    """The section's one state: stopped before waiting before not run; done when every step is done."""
    states = {item["state"] for item in cards}
    return next((state for state in WORST if state in states), "not run")


def layer_in_3d(detail, key):
    """The viewer at the film's camera with only this layer (and the base) switched on; None without a 3D copy or
    when the place's stage holds no such layer."""
    present_layers = {layer.name for layer in detail.usd_index.layers if layer.present}
    if not detail.web3d or key not in present_layers:
        return None
    return f"/view/{detail.place}?only={key}&at=film"


def reference_cards(detail, style):
    """The look's reference picture and the place's concept, as cards with no step of their own."""
    return [present.picture_tile("the look's reference", style.picture if style else None, "the look"),
            present.picture_tile("the concept", detail.concept, "this place")]


def section(key, title, words, cards, extra):
    """One section: its cards, sliders, problems, 3D link and one state; `extra` the rest of its fields."""
    state = worst_state(cards) if cards else NONE_HERE
    return {"key": key, "title": title, "words": words, "cards": cards, "layer": key in LAYER_KEYS, "state": state,
            "state_words": present.STATE_WORDS.get(state, state), **extra}


def ground_card(ground):
    """The world's ground step (made once for every place), pictured: a breakdown card, or None."""
    if ground is None:
        return None
    thumb = ground.picture.thumb_url if ground.picture else None
    return {"label": f"{ground.label} (one for the whole environment)", "url": f"/world/step/{ground.stage}/",
            "thumb": thumb, "full": large(thumb), "state": ground.state,
            "words": present.STATE_WORDS.get(ground.state, ground.state), "unseen": False, "drawn": False,
            "made_from": [], "more_from": 0}


def breakdown(detail, style, step_url, sliders, ground=None):
    """The place's breakdown: [section] in the paper's order, each {key, title, words, cards, sliders, problems,
    findings, show3d, layer, state, absent}; `ground` the world's ground step's StepDetail, shown under the ground."""
    pictured = pictured_steps(detail, step_url)
    cards, sections_of_stage = {}, {}
    for layer in detail.layers:
        for step in layer.steps:
            key = section_of(layer.name, step.stage)
            sections_of_stage[step.stage] = key
            made = card(step, detail.place, step_url, pictured, key != PIECES)
            cards.setdefault(key, []).append(plan_reads(made, pictured) if key == PLAN else made)
    cards[REFERENCE] = reference_cards(detail, style)
    present_layers = {layer.name for layer in detail.usd_index.layers if layer.present}
    if ground_card(ground) and "ground" in present_layers:
        cards.setdefault("ground", []).insert(0, ground_card(ground))
    problems = problems_by_section(detail, sections_of_stage)
    findings = findings_by_section(detail)
    found = []
    for key, title, words in SECTIONS:
        found.append(section(key, title, words, cards.get(key, []), {
            "sliders": [item for item in sliders if item["section"] == key], "problems": problems.get(key, []),
            "findings": findings.get(key, []), "problem_count": len(problems.get(key, [])) + sum(
                group["count"] for group in findings.get(key, [])),
            "show3d": layer_in_3d(detail, key) if key in LAYER_KEYS else None,
            "absent": key in LAYER_KEYS and not cards.get(key) and key not in present_layers}))
    return found

