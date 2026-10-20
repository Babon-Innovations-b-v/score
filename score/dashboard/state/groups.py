"""How the dashboard groups an environment, synthesised from what the framework holds (no new framework level): each place's
style from data/definitions/place.json, each stage's layer from the stage table's reads, and words for the stages.

Environment -> engine -> style -> place -> layer -> step (node). The stored id and the runner's grain keep the word
world (`world1`, grain "world"): renaming them would make every accepted node again.
"""
ENGINE = "Blender (headless)"  # the only engine (score/adapters/engines); a level so a second one slots in
UNASSIGNED = "unassigned"
DOORS = "doors"
STAGE_AND_FILMS = "stage and films"
# The assembly input each layer is read through (score/stages/assembly/record.py ORDER, in words).
LAYER_OF_INPUT = {"scene-record": "base", "terrain": "ground", "surfaces-bake": "pieces", "surfaces-paint": "pieces",
                  "sound": "sound", "effects-layer": "effects", "motion": "motion", "light": "light",
                  "motion-models": "motion", "crops-layer": "crops", "settle": "settle",
                  "characters-layer": "characters"}
LAYER_ORDER = ("base", "ground", "pieces", "settle", "light", "motion", "effects", "sound", "crops",
               "characters", STAGE_AND_FILMS)
# Display words for a stage; any other stage shows its own name.
LABELS = {"plan": "plan", "scene-record": "scene record", "props-inputs": "prop list", "closeup": "close-ups",
          "pixal": "models", "likeness-calibration": "likeness calibration", "likeness": "likeness",
          "surfaces-parts": "parts", "surfaces-paint": "paint", "surfaces-bake": "bake",
          "surfaces-check": "surface check", "finish-route-views": "finish views", "finish-route-list": "finish lists",
          "finish-route-split": "finish split", "finish-route-recheck": "finish recheck", "light-layer": "lamps", "light-passes": "light renders",
          "light-haze": "haze", "light": "light sweep", "effects-layer": "effects", "effects-look": "effects renders",
          "motion-models": "motion models", "motion-models-boxes": "motion model boxes", "characters-layer": "people layer",
          "cast": "cast", "assembly": "OpenUSD stage", "neighbours": "with neighbours", "complete": "completion",
          "complete-boxes": "completion boxes", "demo-film": "film", "demo-film-extra": "extra film",
          "demo-stills": "stills", "terrain": "ground", "settle": "settle",
          "sound": "sound", "motion": "motion", "physics-layer": "physics", "physics-trial": "physics trial",
          "surface-tiles": "surface tiles", "ship_kit": "ship kit", "concept_people": "people concepts",
          "concept-views": "concept views", "library": "library handover", "library-world": "library handover",
          "demo-turntables": "turntable films", "partition-proposals": "partition proposals",
          "people-route-views": "people finish views", "people-route-list": "people finish lists",
          "people-route-split": "people finish split", "people-parts": "people parts", "people-paint": "people paint",
          "people-clips": "people clips"}
# The crops' own rows: their models are the place's own prop and surface rows (2026-10-20, #26).
LABELS.update({"crops-boxes": "crop boxes", "crops-concept": "crop patches on the concept", "crops-layer": "crops",
               "crops-look": "crop renders"})
# A person's rows, one a look: the step's words, then the look.
PEOPLE = {"people-body-": "body", "people-dress-": "dressed body", "people-take-": "model"}
# Door kits: places whose kit is a door, shown together, each by its title (data/checks/contents.json: the garage's
# big door leaves, the hangar's roof leaves).
DOOR_TITLES = {"gdoor": "garage door", "hdoor": "hangar door"}
DOOR_KITS = tuple(DOOR_TITLES)


def label(stage):
    """A stage in words: LABELS, a person's row by its step and look, else the stage's own name."""
    if stage in LABELS:
        return LABELS[stage]
    prefix = next((prefix for prefix in PEOPLE if stage.startswith(prefix)), None)
    if prefix:
        return f"{PEOPLE[prefix]} of the {stage.removeprefix(prefix).replace('_', ' ')} look"
    return stage


def place_title(place):
    """A place's key in words: a door kit by its title, any other with its underscores as spaces."""
    return DOOR_TITLES.get(place, place.replace("_", " "))


def short_name(place, style):
    """A place's short name: its own look's `short` (place.json), else its title from its key, first letter capital."""
    if style is not None and style.short and len(style.places) == 1:
        return style.short
    title = place_title(place)
    return title[:1].upper() + title[1:]


def short_names(world):
    """{place: its short name} of every place of a WorldState."""
    return {card.place: short_name(card.place, style)
            for engine in world.engines for style in engine.styles for card in style.places}


def look_of(place, looks):
    """The look in place.json a place takes: one whose `scenes` lists it, else `prologue_<place>`, else `<place>`;
    DOORS for a door kit; else UNASSIGNED."""
    for name, look in looks.items():
        if isinstance(look, dict) and place in (look.get("scenes") or []):
            return name
    for name in (f"prologue_{place}", place):
        if isinstance(looks.get(name), dict) and "style" in looks[name]:
            return name
    return DOORS if place in DOOR_KITS else UNASSIGNED


def styles(places, looks):
    """{look: [place]} in the order of place.json, then doors, then unassigned; every place once."""
    found = {}
    for place in places:
        found.setdefault(look_of(place, looks), []).append(place)
    order = [name for name in looks if name in found] + [name for name in (DOORS, UNASSIGNED) if name in found]
    return {name: found[name] for name in order}


def readers_of(rows):
    """{stage: [stages that read it, in table order]} over `after` and `beside`."""
    found = {row.name: [] for row in rows}
    for row in rows:
        for read in {**row.after, **row.beside}:
            found.setdefault(read, []).append(row.name)
    return found


def reads_assembly(name, by_name, seen=None):
    """True when a stage reads the assembly, directly or through what it reads."""
    seen = seen if seen is not None else set()
    if name in seen or name not in by_name:
        return False
    seen.add(name)
    return any(read == "assembly" or reads_assembly(read, by_name, seen) for read in by_name[name].after)


def forward_layer(name, readers, seen=None):
    """The layer of the first assembly input reached walking a stage's readers forward, in table order, or None."""
    if name in LAYER_OF_INPUT:
        return LAYER_OF_INPUT[name]
    seen = seen if seen is not None else set()
    seen.add(name)
    for reader in readers.get(name, []):
        if reader in seen:
            continue
        found = forward_layer(reader, readers, seen)
        if found:
            return found
    return None


def layers(rows):
    """{stage: layer} of every place stage: the assembly and what reads it is STAGE_AND_FILMS; else the first
    assembly input its readers reach; else the first one it reads; else STAGE_AND_FILMS."""
    by_name = {row.name: row for row in rows}
    readers = readers_of(rows)
    found = {}
    for row in rows:
        if row.grain != "place":
            continue
        if row.name == "assembly" or reads_assembly(row.name, by_name):
            found[row.name] = STAGE_AND_FILMS
            continue
        found[row.name] = (forward_layer(row.name, readers)
                           or next((LAYER_OF_INPUT[read] for read in row.after if read in LAYER_OF_INPUT), None)
                           or STAGE_AND_FILMS)
    return found
