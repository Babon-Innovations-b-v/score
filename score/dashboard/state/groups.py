"""How the dashboard groups a world, synthesised from what the framework holds (no new framework level): each place's
style from data/definitions/place.json, each stage's layer from the stage table's reads, and words for the stages.

World -> environment engine -> style -> environment (place) -> layer -> step (node).
"""
ENGINE = "Blender (headless)"  # the only engine (score/adapters/engines); a level so a second one slots in
UNASSIGNED = "unassigned"
DOORS = "doors"
STAGE_AND_FILMS = "stage and films"
# The assembly input each layer is read through (score/stages/assembly/record.py ORDER, in words).
LAYER_OF_INPUT = {"scene-record": "base", "terrain": "ground", "surfaces-bake": "pieces", "surfaces-paint": "pieces",
                  "sound": "sound", "effects-layer": "effects", "motion": "motion", "light": "light",
                  "machines-layer": "machines", "crops-layer": "crops", "settle": "settle",
                  "characters-layer": "characters"}
LAYER_ORDER = ("base", "ground", "pieces", "settle", "machines", "light", "motion", "effects", "sound", "crops",
               "characters", STAGE_AND_FILMS)
# Display words for a stage; any other stage shows its own name.
LABELS = {"plan": "plan", "scene-record": "scene record", "props-inputs": "prop list", "closeup": "close-ups",
          "pixal": "models", "likeness-calibration": "likeness calibration", "likeness": "likeness",
          "surfaces-inputs": "surface list", "surfaces-turntable": "turntables", "surfaces-lists": "finish lists",
          "surfaces-maps": "finish maps", "surfaces-names": "finish names", "surfaces-segvigen": "segmentation",
          "surfaces-parts": "parts", "surfaces-paint": "paint", "surfaces-bake": "bake",
          "surfaces-check": "surface check", "light-layer": "lamps", "light-passes": "light renders",
          "light-haze": "haze", "light": "light sweep", "effects-layer": "effects", "effects-look": "effects renders",
          "machines-layer": "machines", "machines-boxes": "machine boxes", "characters-layer": "people layer",
          "cast": "cast", "assembly": "OpenUSD stage", "neighbours": "with neighbours", "complete": "completion",
          "complete-boxes": "completion boxes", "demo-film": "film", "demo-film-extra": "extra film",
          "demo-stills": "stills", "terrain": "ground", "terrain-look": "ground renders", "settle": "settle",
          "sound": "sound", "motion": "motion", "physics-layer": "physics", "physics-trial": "physics trial"}
# Door kits: places whose kit is a door, shown together.
DOOR_KITS = ("gdoor", "hdoor")


def label(stage):
    return LABELS.get(stage, stage)


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
