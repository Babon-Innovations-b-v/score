"""The people of each place's picked design (#26): every people row of its scene inventory (the reading of its picked
concept, score/review/reading.py) mapped to a look on the shared people line, kept in data/people/rows.json:

    {"places": {<place>: {"concept": <the picked draw's sha256 the reading was read from>,
                          "spots": [[x, y, z], ...] (the plan's people spots in the place's frame), "middle": [x, y, z],
                          "rows": {<row>: {"name", "noun", "count", "size" [wide, deep, tall] metres, "where",
                                           "looks": [<look>, ... one a person]  |  "crowd": <far look>,
                                           "palettes": [[skin, clothes, boots library surfaces], ...]}}}},
     "new": {<look>: {"words", "from"}}}

One look a distinct person; a crowd one far look in a few colour palettes (CONTEXT.md "crowd"). A look is one of the
people line's (data/surfaces/people.json) or a new one, named `<place>_<row>_<n>-new` and listed under `new` until it
has a spec and a take of its own. The cast (score/stages/cast) and the characters layer read who is in a place from
here, never the old game records (data/characters) or the lost concept pictures; the people line's bake entries take
each look's size from the person row that maps it (`size_of`).

    .venv/bin/python -m score.stages.people_rows      # refresh from the store's current readings and plans

A refresh copies each reading's rows again and keeps every hand-made choice (looks, crowd, palettes) of a row read
from the same concept; a row of a newer concept starts from the defaults (new looks, the crowd's far look). Then it
writes the people line's data for its mapped looks (`write_line`).
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
ROWS = REPO / "data/people/rows.json"
LINE = "people"
LINE_FILES = {"props": REPO / "data/props/people.json", "inventory": REPO / "data/inventory/people.json",
              "surfaces": REPO / "data/surfaces/people.json"}
# The people line's one far look (kit_m_avg in the grey coat, the crowd's body since 2026-10-13).
CROWD_LOOK = "kit_m_avg-coat-grey"
# A crowd's colour palettes, library surfaces of the people place (skin, clothes, boots): the grey, navy, charcoal,
# blue and olive coats of the square's first crowd, until the owner picks others.
PALETTES = [["skin_light", "wool_grey", "leather_black"], ["skin_medium", "suit_navy", "leather_black"],
            ["skin_dark", "wool_charcoal", "leather_black"], ["skin_light", "jacket_blue", "rubber"],
            ["skin_medium", "olive_drab", "leather_black"]]
PALETTE_PARTS = ["skin", "clothes", "boots"]
CHOSEN = ("looks", "crowd", "palettes", "why")  # a row's hand-made fields, kept over a refresh of the same concept


def read():
    return json.loads(ROWS.read_text())


def place_entry(place, found=None):
    """The place's entry, or None for a place with no picked design read."""
    return (found or read())["places"].get(place)


def place_part(place):
    """The part of rows.json a place's rows key on (Stage.files' (pattern, part)): its own entry and its new looks."""
    def part(path):
        found = json.loads(pathlib.Path(path).read_text())
        return json.dumps(place_entry(place, found), sort_keys=True)
    return part


def has_people(place):
    """Whether the place's picked design shows anybody."""
    entry = place_entry(place)
    return bool(entry and entry["rows"])


def doing_of(row):
    """A person's clip by the row's words: sitting, walking, else standing."""
    words = f"{row.get('name', '')} {row.get('where', '')}".lower()
    if "sitting" in words or "seated" in words:
        return "sitting"
    return "walking" if "walking" in words else "standing"


def persons(place, found=None):
    """[{name, row, look, doing}] of every person the place's design shows (a crowd is not among them)."""
    entry = place_entry(place, found) or {"rows": {}}
    return [{"name": row if len(fields["looks"]) == 1 else f"{row}_{number}", "row": row, "look": look,
             "doing": doing_of(fields)}
            for row, fields in sorted(entry["rows"].items()) if "looks" in fields
            for number, look in enumerate(fields["looks"], 1)]


def crowd_row(place, found=None):
    """(row, fields) of the place's crowd row, or None."""
    entry = place_entry(place, found) or {"rows": {}}
    return next(((row, fields) for row, fields in sorted(entry["rows"].items()) if "crowd" in fields), None)


def looks_of(place, found=None):
    """Every look the place's design names (its people's and its crowd's)."""
    crowd = crowd_row(place, found)
    return {person["look"] for person in persons(place, found)} | ({crowd[1]["crowd"]} if crowd else set())


def every_look(found=None):
    found = found or read()
    return set().union(*(looks_of(place, found) for place in found["places"]))


def split_look(look):
    """(character, outfit) of a look `<character>-<outfit>`, as the cast names it (`<character>_<outfit>`)."""
    character, _, outfit = look.partition("-")
    return character, outfit


def srgb(colour):
    """A library surface's linear colour as 0 to 255 sRGB (tools/characters/cast.py's palettes)."""
    return [round(255 * (12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055))
            for value in colour]


def palette_colours(palettes):
    """Each palette's library surfaces as sRGB colours."""
    import sys
    folder = str(REPO / "tools/props/library")
    if folder not in sys.path:
        sys.path.append(folder)
    import library
    surfaces = library.resolved(LINE)
    return [[srgb(surfaces[name]["colour"]) for name in palette] for palette in palettes]


def cast_record(place, found=None):
    """The place's cast record in tools/characters/cast.py's form, from its design: each person at the plan's people
    spots in turn (the cast stage stands them clear round it), facing the place's middle; the crowd its far look in
    its palettes, with no ground or count until the design gives one."""
    found = found or read()
    entry = place_entry(place, found)
    spots = entry.get("spots") or [entry.get("middle", [0.0, 0.0, 0.0])]
    people = []
    for number, person in enumerate(persons(place, found)):
        character, outfit = split_look(person["look"])
        people.append({"name": person["name"], "character": character, "look": f"{character}_{outfit}",
                       "doing": person["doing"], "at": spots[number % len(spots)],
                       "facing_to": entry.get("middle", [0.0, 0.0, 1.0]),
                       "why": f"row {person['row']} of the picked design's scene inventory"})
    record = {"place": place, "from": f"the picked design (concept {entry['concept'][:8]}): data/people/rows.json",
              "people": people}
    crowd = crowd_row(place, found)
    if crowd:
        row, fields = crowd
        character, outfit = split_look(fields["crowd"])
        record["crowd"] = {"name": row, "character": character, "look": f"{character}_{outfit}", "body": "far",
                           "count": None, "doing": [doing_of(fields)], "shares": [1.0], "phases": 1,
                           "palettes": palette_colours(fields["palettes"]), "palette_parts": PALETTE_PARTS,
                           "palette_shares": [1.0 / len(fields["palettes"])] * len(fields["palettes"]),
                           "why": f"row {row} of the picked design's scene inventory"}
    return record


def person_sized(size):
    """Whether a row's [wide, deep, tall] is one person's: its tall side the longest (a crowd row's is its extent)."""
    return isinstance(size, list) and len(size) == 3 and size[2] >= max(size[:2])


def size_of(look, found=None):
    """({size [wide, deep, tall] metres}, "<place>/<row>") of the first person-sized row that maps the look, or None."""
    found = found or read()
    for place, entry in sorted(found["places"].items()):
        for row, fields in sorted(entry["rows"].items()):
            if look in fields.get("looks", []) + [fields.get("crowd")] and person_sized(fields.get("size")):
                return fields["size"], f"{place}/{row}"
    return None


# --- the refresh from the store (free) ----------------------------------------------------------------------------

def default_choice(place, row):
    """A new row's looks: a crowd's far look in the palettes, else a new look a person."""
    if row["noun"] == "crowd" or "crowd" in row["name"]:
        return {"crowd": CROWD_LOOK, "palettes": PALETTES}
    return {"looks": [f"{place}_{row['id']}_{number}-new" for number in range(1, row.get("count", 1) + 1)]}


def placed_spots(plan):
    """The plan's people spots and its middle in the place's frame (scene_record.plan.placed)."""
    from score.stages.scene_record.plan import placed
    spots = [placed(plan, spot[0], spot[1]).tolist() for spot in plan.get("people", [])
             if len(spot) >= 2 and all(isinstance(value, (int, float)) for value in spot[:2])]
    return spots, placed(plan, plan.get("w", 0.0) / 2, plan.get("d", 0.0) / 2).tolist()


def refreshed_place(place, inventory, plan, old):
    """One place's entry from its current reading (`inventory`, groups.current's) and plan, keeping `old`'s choices
    where it was read from the same concept."""
    concept = inventory["concept_pick"]["sha256"]
    kept = old["rows"] if old and old["concept"] == concept else {}
    rows = {}
    for row in inventory["rows"]:
        if row["route"] != "people":
            continue
        copied = {key: row.get(key) for key in ("name", "noun", "count", "size", "where")}
        chosen = {key: kept[row["id"]][key] for key in CHOSEN if key in kept.get(row["id"], {})}
        rows[row["id"]] = {**copied, **(chosen or default_choice(place, row))}
    spots, middle = placed_spots(plan) if plan else ([], [0.0, 0.0, 0.0])
    return {"concept": concept, "spots": spots, "middle": middle, "rows": rows}


def new_looks(places, line_looks):
    """{look: {words, from}} of every look the places name that is not on the people line."""
    return {look: {"words": fields["name"], "from": f"{place}/{row}"}
            for place, entry in sorted(places.items()) for row, fields in sorted(entry["rows"].items())
            for look in fields.get("looks", []) if look not in line_looks}


def line_looks():
    """The looks the people line's surface data takes (data/surfaces/people.json)."""
    from score.stages.people_bodies import bodies
    return set(bodies.looks())


def refresh(store):
    """rows.json from every place's current reading and plan (a place with none is left out); written."""
    from score.review import plans
    from score.stages.complete.prepare import groups
    places = sorted(path.stem for path in (REPO / "data/inventory").glob("*.json") if path.stem != LINE)
    inventories, _ = groups.current(store, places)
    old = read() if ROWS.exists() else {"places": {}}
    found = {place: refreshed_place(place, inventory, (plans.current(store, place) or {}).get("plan"),
                                    old["places"].get(place))
             for place, inventory in sorted(inventories.items())}
    record = {"why": old.get("why", ""), "places": found, "new": new_looks(found, line_looks())}
    ROWS.write_text(json.dumps(record, indent=1) + "\n")
    return record


# --- the people line's data for the mapped looks -------------------------------------------------------------------

def line_rows(found, props, inventory, surfaces):
    """The people line's three records narrowed to the looks the designs map, each inventory row and bake entry with
    the look's size (size_of): (props, inventory, surfaces)."""
    from score.stages.props import compare
    details = json.loads((REPO / "data/library/details.json").read_text())
    wanted = every_look(found) & set(props["objects"])
    rows = []
    for row in inventory["rows"]:
        if row["id"] in wanted:
            size, origin = size_of(row["id"], found)
            rows.append({**row, "size": size, "size_from": f"{origin} of data/people/rows.json"})
    takes = {props["objects"][look]["take"] for look in wanted}
    models = {look: take for look, take in surfaces["bake"]["models"].items() if look in wanted}
    entries = {look: compare.bake_entry(LINE, {"id": look, "size": next(row["size"] for row in rows
                                                                        if row["id"] == look)}, details)
               for look in models}
    return ({**props, "objects": {look: entry for look, entry in props["objects"].items() if look in wanted}},
            {**inventory, "rows": rows},
            {**surfaces, "takes": {take: entry for take, entry in surfaces["takes"].items() if take in takes},
             "bake": {**surfaces["bake"], "models": models, "entries": entries}})


def write_line():
    """The people line's data (LINE_FILES) narrowed and sized for the mapped looks, written."""
    records = {name: json.loads(path.read_text()) for name, path in LINE_FILES.items()}
    for name, record in zip(LINE_FILES, line_rows(read(), records["props"], records["inventory"],
                                                  records["surfaces"])):
        LINE_FILES[name].write_text(json.dumps(record, indent=1) + "\n")


def main():
    from score.store import Store
    record = refresh(Store.default())
    write_line()
    print(f"people rows: {len(record['places'])} places, {sum(map(len, (entry['rows'] for entry in record['places'].values())))} "
          f"rows, {len(record['new'])} new looks; {ROWS}")


if __name__ == "__main__":
    main()
