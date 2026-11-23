"""The benchmark's set (#162's rule): which adopted NVIDIA SimReady models the prop pipeline is scored against.

A kind takes an adopted model (`model/simready_*`, in force) when the first of its Wikidata classes is one of the kind's
classes and its id holds one of the kind's words at a word start (`(^|_)<word>`). Within a kind the ids are sorted by
`sha256("r162:" + id)`, the overlap targets left out, and the first `PER_KIND` taken, skipping an id whose stem (the
id without its trailing `_<letter><two digits>`) an earlier pick or an overlap target already holds. The first
`TUNE` picks are tune, the rest held out. The overlap targets are the adopted models a withdrawn model's replacement
chain ends at (#155, #157): each is tune and carries its withdrawn models.

Two groups follow, named rather than drawn, the earlier picks unchanged (#159): `DETAILED`, the owner's detailed
models (2026-11-23: "the more in depth models, like some where full on tools, or stuff like a coffee machine"), each
under its kind, all tune, an id the rule already took not repeated; and `PICTURED`, the 2099 cockpit cases with no
NVIDIA model, whose truth is their close-up (a store object, `picture`) and their target size alone (measures'
`pictured`): each row {id, kind "cockpit", split tune, withdrawn [], material, picture: {closeup, size (wide, deep,
tall, metres), size_from, words, labels, classes, never}, made_before: the 2099 session's own makes of it in score_lib}.
"""
import hashlib
import re

from score import library

SALT = "r162:"
PER_KIND = 5
TUNE = 3
PREFIX = "simready_"
STEM = re.compile(r"_[a-z]\d\d$")
# kind: (Wikidata classes its first class must be one of, words its id must hold at a word start). #162's table.
KINDS = {
    "box": (("cardboard box", "box", "carton"), ("box",)),
    "crate": (("crate",), ("crate",)),
    "shelf / rack": (("rack with shelves", "shelf"), ("rack", "shelf", "shelving")),
    "cabinet / locker": (("cabinet", "kitchen cabinet", "storage cabinets & locker", "tool cabinets & chest",
                          "Tool cabinet"), ("cabinet", "locker")),
    "desk / table / bench": (("table", "workbench", "coffee table", "desk"), ("table", "workbench", "desk", "bench")),
    "chair / stool": (("chair", "office chair", "stool"), ("chair", "stool")),
    "monitor / keyboard": (("computer monitor", "computer terminal", "computer keyboard"),
                           ("monitor", "keyboard", "terminal")),
    "lamp body": (("lamp", "LED lamp", "task lighting", "light fixture"), ("lamp", "light")),
    "bin": (("waste container", "recycling bin"), ("bin", "trash", "recycle", "waste")),
    "ladder": (("ladder",), ("ladder",)),
    "sign (flat)": (("signage", "safety sign", "wet floor sign"), ("sign",)),
    "toolbox / tool cart": (("toolbox", "tool cart"), ("toolbox", "tool", "cart")),
    "fridge / stove / sink": (("refrigerator", "gas stove", "sink"), ("fridge", "refrigerator", "stove", "sink")),
    "hose / pipe (slender)": (("hose", "plastic pipe", "pipe"), ("hose", "pipe")),
    "tray (flat)": (("tray", "serving tray"), ("tray",)),
}
# The owner's detailed models (#159), each id's kind: the kind names what most of it is made of (bench KIND_CLASS).
DETAILED = {
    "simready_power_tool_drill_a01": "power tool", "simready_power_tool_drill_b01": "power tool",
    "simready_power_tool_grinder_a01": "power tool", "simready_power_tool_heat_gun_cordless_a01": "power tool",
    "simready_power_tool_cutting_tool_a01": "power tool", "simready_hand_tool_air_ratchet_a01": "hand tool",
    "simready_hand_tool_hammer_dead_blow_a01": "hand tool", "simready_instrument_hand_drill_b01": "hand tool",
    "simready_machine_coffee_vending_a01": "machine", "simready_furniture_counter_coffee_station_a01": "machine",
    "simready_anesthesia_machine_a01": "machine"}
# The 2099 cockpit cases (#159; the 2099 session's TRELLIS cockpit hardware, owner: "messy meshes"), each (the
# material class the route is given, the 2099 session's own makes of it, its picture). `closeup`: the
# store output holding closeup.png, the picture the 2099 session made it from (`python3 -m tools.props.bench.truth
# picture <png>`). `size`: wide, deep, tall in metres; the small parts' from their reference solids (drawn in Blender
# at their real size; their bounds), the screen's from the owner's target, the panel's and the console's as the
# capsule laid them (its round 6). `labels`: the words printed in the close-up; `classes`: the material classes its
# finishes show (sim.py's); `never`: library recipes it does not show (the palette's wrong picks: cloth on a toggle
# lever, rust on screen bezels).
NEVER = ["cloth", "beta_cloth", "rusted_metal"]
PICTURED = {
    "screen_flight": ("metal", [], {
        "closeup": "9a030c43fe6fe4ca6df7469bacd825e1b2370cc75e55aaced2375ef39bb1c039", "size": [0.51, 0.2, 0.55],
        "size_from": "the owner's target for the flight screen (#159)",
        "words": "Flight screen: a cockpit display, a painted metal bezel round a dark glass screen showing flight "
                 "lines, two round gauges and small buttons below it", "labels": [],
        "classes": ["metal", "aluminium", "glass", "plastic"]}),
    "readout_window": ("aluminium", ["model/readout_window_trellis.capsule@1"], {
        "closeup": "156166f40d1c18e0b8e61f43758e9cee6b3369badaa30db8588497d546236cb7", "size": [0.094, 0.0115, 0.04],
        "size_from": "its reference solids' bounds (Blender, the 2099 session's refs_blender.py)",
        "words": "Readout window: a dark metal frame with four screws round a dark glass window of lit green "
                 "seven-segment digits, a white caption above", "labels": ["ALT M", "-0128"],
        "classes": ["metal", "aluminium", "glass", "plastic"]}),
    "toggle_switch": ("aluminium", ["model/toggle_switch_trellis.capsule@1"], {
        "closeup": "d5775bbb0960b53a9fa5faa2cfca83819587ea85a7a1785c6bd975f2d4802d30", "size": [0.03, 0.0318, 0.036],
        "size_from": "its reference solids' bounds (Blender, the 2099 session's refs_blender.py)",
        "words": "Toggle switch: a grey metal plate with four screws, a chrome bat lever in a hex nut, white ON and "
                 "OFF",
        "labels": ["ON", "OFF"], "classes": ["metal", "aluminium"]}),
    "guarded_switch": ("aluminium", ["model/guarded_switch_trellis.capsule@1"], {
        "closeup": "5d67b387478d7e4c7399ad2184a32963da34ec184be82fbc52c4ee6416f5a6fb", "size": [0.04, 0.0379, 0.0693],
        "size_from": "its reference solids' bounds (Blender, the 2099 session's refs_blender.py)",
        "words": "Guarded switch: a grey metal plate, a chrome bat toggle under a red plastic guard swung up on a "
                 "hinge, white ARM below", "labels": ["ARM"], "classes": ["metal", "aluminium", "plastic"]}),
    "push_button": ("plastic", ["model/push_button_trellis.capsule@1"], {
        "closeup": "ed8ef0726f70064826c0b3dfe685a14809899a5af663f300afef69a4b22ec71a", "size": [0.03, 0.0135, 0.03],
        "size_from": "its reference solids' bounds (Blender, the 2099 session's refs_blender.py)",
        "words": "Push button: a lit amber square plastic cap in a dark metal bezel, IGN over ARMED split by a line",
        "labels": ["IGN", "ARMED"], "classes": ["plastic", "metal", "aluminium"]}),
    "panel_attitude": ("metal", ["model/panel_attitude_trellis.capsule@1"], {
        "closeup": "9d168abea145325b6ae175de355cdf1d82ba1c3b3dd98cbd9f70c5afad79e050", "size": [0.72, 0.332, 0.354],
        "size_from": "as the 2099 capsule laid it (its round 6: the make at scale 0.8417)",
        "words": "Attitude hold panel: a worn beige metal panel, a round-cornered screen of green lines in the middle, "
                 "four small green gauges round it, three red buttons below, ATTITUDE HOLD printed across the top",
        "labels": ["ATTITUDE HOLD"], "classes": ["metal", "aluminium", "glass", "plastic"]}),
    "pilot_console": ("metal", ["model/pilot_console_trellis.capsule@1"], {
        "closeup": "d4524ebb87b5e161872209591c11ed16390c9d1f6ccf64ce44182c628cc8eea8", "size": [1.6, 0.62, 0.85],
        "size_from": "as the 2099 capsule laid it (its round 6: 2.3516 x 1.3529 x 0.6875 m at 0.6804, 0.4583, 1.2364)",
        "words": "Pilot console: a long dark grey metal console, a beige top rail, a vent of slots at its end and a "
                 "sloped panel of round knobs and switches", "labels": [],
        "classes": ["metal", "aluminium", "plastic"]}),
}
RULE = ("A kind takes an adopted model (model/simready_*, in force, its newest version) when the first of its Wikidata "
        "classes is one of the kind's classes and its id holds one of the kind's words at a word start ((^|_)word). "
        "Within a kind the ids are sorted by sha256('r162:' + id), the overlap targets left out, and the first 5 "
        "taken, skipping an id whose stem (the id without its trailing _<letter><two digits>) an earlier pick or an "
        "overlap target already holds; the first 3 are tune, the rest held out. The overlap targets are the adopted "
        "models a withdrawn model's replacement chain ends at (#155, #157), all tune, each with its withdrawn models. "
        "Then the owner's detailed models (#159), each named with its kind, all tune, at its newest version, one the "
        "rule already took not repeated; then the 2099 cockpit cases (#159), no NVIDIA model: each held to its "
        "close-up and target size alone, all tune.")


def stem(entry_id):
    """The id without its trailing variant (`_<letter><two digits>`)."""
    return STEM.sub("", entry_id)


def newest(records):
    """{id: its newest version's record} of the given entry records."""
    found = {}
    for record in records:
        if record["id"] not in found or record["version"] > found[record["id"]]["version"]:
            found[record["id"]] = record
    return found


def adopted(records):
    """{id: record} of the adopted NVIDIA models in force, each at its newest version."""
    models = newest(record for record in records if record["kind"] == "model" and record["id"].startswith(PREFIX))
    return {entry_id: record for entry_id, record in models.items() if record.get("state") != "withdrawn"}


def overlaps(root, records):
    """{target address: [withdrawn model addresses]} for each adopted model a withdrawn model's chain ends at."""
    found = {}
    for record in records:
        if record["kind"] != "model" or library.replacement(record) is None:
            continue
        end = library.replaced_end(root, record["address"])
        if end.split("/", 1)[1].startswith(PREFIX):
            found.setdefault(end, []).append(record["address"])
    return {target: sorted(found[target]) for target in sorted(found)}


def matches(record, classes, words):
    """Whether the record's first Wikidata class is one of `classes` and its id holds one of `words` at a word start."""
    named = (record.get("tags") or {}).get("wikidata_class") or []
    return bool(named) and named[0] in classes and any(re.search(r"(^|_)" + word, record["id"]) for word in words)


def kind_picks(models, classes, words, taken_stems):
    """(matching ids, the picks) of one kind: its ids in salted-hash order, a stem already taken skipped."""
    ids = sorted((entry_id for entry_id, record in models.items() if matches(record, classes, words)),
                 key=lambda entry_id: hashlib.sha256((SALT + entry_id).encode()).hexdigest())
    stems, picks = set(taken_stems), []
    for entry_id in ids:
        if stem(entry_id) in stems:
            continue
        stems.add(stem(entry_id))
        picks.append(entry_id)
        if len(picks) == PER_KIND:
            break
    return ids, picks


def detailed(models, taken):
    """The owner's detailed models (DETAILED) as set objects, each at its newest version in force; one already
    `taken` (an address the rule picked) not repeated. A named id not adopted and in force raises KeyError."""
    found = []
    for entry_id, kind in DETAILED.items():
        if entry_id not in models:
            raise KeyError(f"{entry_id}: named in DETAILED but not an adopted model in force")
        if models[entry_id]["address"] not in taken:
            found.append({"address": models[entry_id]["address"], "kind": kind, "split": "tune", "withdrawn": []})
    return found


def pictured():
    """The 2099 cockpit cases (PICTURED) as set objects: no address, their picture the truth."""
    return [{"id": f"cockpit_{name}", "kind": "cockpit", "split": "tune", "withdrawn": [], "material": material,
             "made_before": made_before, "picture": {**picture, "never": list(NEVER)}}
            for name, (material, made_before, picture) in PICTURED.items()]


def picked(root, commit):
    """The set the rule gives on the library at `root` (its checkout at `commit`): {rule, score_lib_commit, kinds,
    objects}, each object {address, kind, split, withdrawn}."""
    records = library.entries(root)
    models = adopted(records)
    targets = overlaps(root, records)
    target_ids = {address.split("/", 1)[1].split("@")[0] for address in targets}
    pool = {entry_id: record for entry_id, record in models.items() if entry_id not in target_ids}
    target_stems = {stem(entry_id) for entry_id in target_ids}
    objects, kinds = [], {}
    for kind, (classes, words) in KINDS.items():
        ids, picks = kind_picks(pool, classes, words, target_stems)
        kinds[kind] = {"classes": list(classes), "words": list(words), "matching": len(ids)}
        objects += [{"address": models[entry_id]["address"], "kind": kind,
                     "split": "tune" if rank < TUNE else "held-out", "withdrawn": []}
                    for rank, entry_id in enumerate(picks)]
    objects += [{"address": target, "kind": "overlap", "split": "tune", "withdrawn": withdrawn}
                for target, withdrawn in targets.items()]
    objects += detailed(models, {item["address"] for item in objects})
    objects += pictured()
    return {"rule": RULE, "score_lib_commit": commit, "kinds": kinds, "objects": objects}
