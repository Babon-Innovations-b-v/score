"""The people of each place's picked design (#26): every people row of its scene inventory (the reading of its picked
concept, score/review/reading.py) mapped to a look on the shared people line, kept in data/people/rows.json:

    {"places": {<place>: {"concept": <the picked draw's sha256 the reading was read from>,
                          "spots": [[x, y, z], ...] (the plan's people spots in the place's frame), "middle": [x, y, z],
                          "rows": {<row>: {"name", "noun", "count", "size" [wide, deep, tall] metres, "where",
                                           "share" (its tallest box's share of the concept's frame height, or null),
                                           "looks": [<look>, ... one a person]  |  "crowd": <far look>,
                                           "ground": [[left, near, wide, long], ...] (a crowd's: the plan items
                                                     its row makes, in the place's frame),
                                           "dress": {"surface": <library fabric> | null, ...}}}}}}

A row's `dress` is what its people wear, read off the design (score/stages/people_clothes.py: of the people place's
fabrics its words name, the nearest its measured torso), each person of a row with a surface dressed by
`people-dress-<look>-in-<surface>`. Each person its own variant (owner, 2026-10-25: "Each one looks different"): the
people of one look in a place are numbered 0, 1, ... (`persons`), the first the look's plain dress row, each other
`-v<n>`, the same body finished in other library surfaces (score/stages/people/dress.py's `varied`), so no two people of
a place look the same and the bodies are not made again. One body a look (owner, 2026-10-22: "make bodies one per
look"): people rows are grouped into looks by what the reading says they are and wear (`look_of`: the row's words before
where it stands or what it holds, its pose and colour words left out, so a seated astronaut and five standing ones in
another scene are one `astronaut-made`), each person of a row standing as its row's look on its person spot, its colour
its row's dress (the rule above); a named person (a capitalised word in its row's name) or the player is a look of its
own, `<place>_<row>-made`. A crowd one far look in a few palettes of clothes (CONTEXT.md "crowd"): the line's look its
row's words match (`crowd_look`), else its own words' look, its palettes that look's first `crowd_variants` variants
(the dress rows `-v<n>`, as a place's people of one look: other surfaces of the line's scene library on the same body,
baked, never a flat colour). The outfit `made` is the clothes as the concept draws them on the
body the people route makes, its face the made one (tools/characters/maker/route_head.py FACE; `drawn` there is the
owner's open choice, never what a row asks for). Each look's maker spec (data/people/specs/<character>.json: who from
its row's words, the build from the row's metres, face, hair and clothes as the locked concept draws them, which the
close-up is drawn from: drawn_from; the row that draws a look is its largest standing person, `origin_of`) and its take
on the people line are written on every refresh (`designed_specs`, `with_designed`); no hand-written character file
stands before a design's person. Which looks get a full body and which a far one follows from
each person row's `share` (score/stages/people_bodies/full.py: under FAR_SHARE far, a crowd far always). The cast
(score/stages/cast) and the characters layer read who is in a place from here, never the old game records
(data/characters) or the lost concept pictures; the people line's bake entries take each look's size from the person row
that maps it (`size_of`).

    .venv/bin/python -m score.stages.people_refresh   # refresh from the store's current readings and plans

A refresh copies each reading's people rows again, but those its plan shows beyond the place (`beyond`, as
groups.current routes them), and keeps
every hand-made choice (looks, crowd: a row's fields recorded with its `why`) of a row read from the same concept; any
other row is read again from its design (its drawn looks, the crowd's look by its words). A crowd's ground is taken
from the plan again on every refresh. Then it writes the people line's data for its mapped looks (`write_line`).
"""
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
ROWS = REPO / "data/people/rows.json"
LINE = "people"
LINE_FILES = {"props": REPO / "data/props/people.json", "inventory": REPO / "data/inventory/people.json",
              "surfaces": REPO / "data/surfaces/people.json"}
SPECS = REPO / "data/people/specs"
# A look written from its person rows wears the clothes its concept draws it in, on the route's made body and face.
OUTFIT = "made"
TAKE = "{look}-s1"  # a look's take on the line, as pixal@people names it
# A body's build by its row's shoulders (the wider side of a standing row's footprint, the narrower of a seated one's,
# whose legs run forward), metres: under SLIM slim, over BROAD broad, else average. Bounds of a person's box as the
# readings size them (0.3 to 0.8 m), not of the bare body: a suit or a coat is inside the box.
SLIM, BROAD = 0.45, 0.65
# A crowd wears this many variants of its look's body at most (CONTEXT.md "crowd": a few palettes of clothes; the
# square's first crowd wore five, 2026-10-12), never more than the people SAM 3 counted in it.
CROWD_VARIANTS = 5
# A crowd's draws in cast.py (tools/characters/cast.py's crowd_copies): each copy turned up to TURN_JITTER radians off
# facing the place's middle and HEIGHT_JITTER of its height taller or shorter (the square's first crowd's, 2026-10-12).
TURN_JITTER, HEIGHT_JITTER = 0.35, 0.06
# A row's hand-made fields, kept over a refresh of the same concept when recorded with their `why`.
CHOSEN = ("looks", "crowd", "why")
# The words that say a row is a crowd, not who is in it: they count only between looks that share no other word.
CROWD_WORDS = {"crowd", "people", "person", "group"}
# A look is what its people are and wear: a row's words from one of these on say where it stands or what it holds.
CLAUSE_WORDS = {"on", "at", "by", "near", "under", "behind", "beside", "next", "inside", "outside", "beneath", "above",
                "against", "around", "along", "across", "holding", "carrying", "pushing", "pulling", "looking", "from"}
# How a person stands (its clip, doing_of) and its colours (its dress, people_clothes.py) vary a look; they make none.
POSE_WORDS = {"seated", "sitting", "standing", "walking", "kneeling", "lying", "distant", "far"}
COLOUR_WORDS = {"white", "black", "grey", "gray", "blue", "red", "green", "yellow", "orange", "brown", "purple",
                "pink", "beige", "navy", "dark", "light", "pale", "bright"}
PLURALS = {"people": "person", "men": "man", "women": "woman", "children": "child"}
FUNCTION_WORDS = {"the", "and", "with", "his", "her", "their", "its", "from", "into", "onto", "over", "down", "for",
                  "who", "one", "two", "some", "many"}


def read():
    return json.loads(ROWS.read_text())


def place_entry(place, found=None):
    """The place's entry, or None for a place with no picked design read."""
    return (found or read())["places"].get(place)


def place_part(place):
    """The part of rows.json a place's rows key on (Stage.files' (pattern, part)): its own entry."""
    def part(path):
        found = json.loads(pathlib.Path(path).read_text())
        return json.dumps(place_entry(place, found), sort_keys=True)
    return part


def doing_of(row):
    """A person's clip by the row's words: sitting, walking, else standing."""
    words = f"{row.get('name', '')} {row.get('where', '')}".lower()
    if "sitting" in words or "seated" in words:
        return "sitting"
    return "walking" if "walking" in words else "standing"


def surface_of(fields):
    """The library fabric a row's people wear (its `dress`, people_clothes.py), or None: the look's own paint."""
    return (fields.get("dress") or {}).get("surface")


def persons(place, found=None):
    """[{name, row, look, doing, surface, variant}] of every person the place's design shows (a crowd is not among
    them); the people of one look numbered 0, 1, ... in order, each its own variant of the look's body (the dress
    row `-v<n>`)."""
    entry = place_entry(place, found) or {"rows": {}}
    found = [{"name": row if len(fields["looks"]) == 1 else f"{row}_{number}", "row": row, "look": look,
              "doing": doing_of(fields), "surface": surface_of(fields)}
             for row, fields in sorted(entry["rows"].items()) if "looks" in fields
             for number, look in enumerate(fields["looks"], 1)]
    counted = {}
    for person in found:
        person["variant"] = counted[person["look"]] = counted.get(person["look"], -1) + 1
    return found


def crowd_row(place, found=None):
    """(row, fields) of the place's crowd row, or None."""
    entry = place_entry(place, found) or {"rows": {}}
    return next(((row, fields) for row, fields in sorted(entry["rows"].items()) if "crowd" in fields), None)


def looks_of(place, found=None):
    """Every look the place's design names (its people's and its crowd's)."""
    crowd = crowd_row(place, found)
    return {person["look"] for person in persons(place, found)} | ({crowd[1]["crowd"]} if crowd else set())


def dressed_looks(place, found=None):
    """{(look, surface or None, variant)} of every person and the crowd the place's design shows: the dress row each
    wears."""
    crowd = crowd_row(place, found)
    return {(person["look"], person["surface"], person["variant"]) for person in persons(place, found)} | (
        {(crowd[1]["crowd"], None, variant) for variant in range(crowd_variants(crowd[1]))} if crowd else set())


def every_dressed(found=None):
    """{(look, surface, variant)} of every person a place's design dresses in a fabric of its own or a variant of its
    look's body (beyond the look's plain dress row)."""
    found = found or read()
    return {dressed for place in found["places"] for dressed in dressed_looks(place, found) if any(dressed[1:])}


def every_look(found=None):
    found = found or read()
    return set().union(*(looks_of(place, found) for place in found["places"]))


def split_look(look):
    """(character, outfit) of a look `<character>-<outfit>`, as the cast names it (`<character>_<outfit>`)."""
    character, _, outfit = look.partition("-")
    return character, outfit


def cast_record(place, found=None):
    """The place's cast record in tools/characters/cast.py's form, from its design: each person at the plan's people
    spots in turn (the cast stage stands them clear round it), facing the place's middle; the crowd its far look in
    its variants on its ground (crowd_record)."""
    found = found or read()
    entry = place_entry(place, found)
    spots = entry.get("spots") or [entry.get("middle", [0.0, 0.0, 0.0])]
    people = []
    for number, person in enumerate(persons(place, found)):
        character, outfit = split_look(person["look"])
        people.append({"name": person["name"], "character": character, "look": f"{character}_{outfit}",
                       "doing": person["doing"], "surface": person["surface"], "variant": person["variant"],
                       "at": spots[number % len(spots)],
                       "facing_to": entry.get("middle", [0.0, 0.0, 1.0]),
                       "why": f"row {person['row']} of the picked design's scene inventory"})
    record = {"place": place, "from": f"the picked design (concept {entry['concept'][:8]}): data/people/rows.json",
              "people": people}
    crowd = crowd_row(place, found)
    if crowd:
        record["crowd"] = crowd_record(*crowd, entry)
    return record


def crowd_count(fields):
    """How many the crowd row shows: SAM 3's instances when it told them apart, else None (one mass of bodies it
    could not part: the cast stands as many as its ground holds packed)."""
    count = fields.get("count")
    return count if isinstance(count, int) and count > 1 else None


def crowd_variants(fields):
    """How many variants of its look's body a crowd wears (its palettes): CROWD_VARIANTS, fewer for a crowd SAM 3
    counted fewer people in."""
    return min(crowd_count(fields) or CROWD_VARIANTS, CROWD_VARIANTS)


def spread_of(grounds):
    """The [left, near, wide, long] box round a crowd's grounds, or None when it has none."""
    if not grounds:
        return None
    left, near = min(ground[0] for ground in grounds), min(ground[1] for ground in grounds)
    return [left, near, max(ground[0] + ground[2] for ground in grounds) - left,
            max(ground[1] + ground[3] for ground in grounds) - near]


def crowd_record(row, fields, entry):
    """A crowd row in cast.py's form: its far look, facing the place's middle, on its ground (the plan items its row
    makes; `spread` the box round them, `grounds` each), its count crowd_count's, seeded by its concept; its
    `palettes` the variants of its look's body it wears (crowd_variants: 0 the look's plain dress row, n its `-v<n>`),
    which cast.py's draw deals its copies in equal shares."""
    character, outfit = split_look(fields["crowd"])
    grounds = fields.get("ground")  # None: not read from a plan yet (a row of before 2026-10-21's refresh)
    variants = list(range(crowd_variants(fields)))
    return {"name": row, "character": character, "look": f"{character}_{outfit}", "body": "far",
            "count": crowd_count(fields), "spread": spread_of(grounds), "grounds": grounds,
            "seed": int(entry["concept"][:8], 16),
            "facing_to": entry.get("middle", [0.0, 0.0, 0.0]), "turn_jitter": TURN_JITTER,
            "height_jitter": HEIGHT_JITTER, "doing": [doing_of(fields)], "shares": [1.0], "phases": 1,
            "palettes": variants, "palette_shares": [1.0 / len(variants) for _ in variants],
            "why": f"row {row} of the picked design's scene inventory"}


def person_sized(size):
    """Whether a row's [wide, deep, tall] is one person's: its tall side the longest (a crowd row's is its extent)."""
    return isinstance(size, list) and len(size) == 3 and size[2] >= max(size[:2])


def size_of(look, found=None):
    """({size [wide, deep, tall] metres}, "<place>/<row>") of the row that draws the look (origin_of) when it is one
    person's size, else one member's (member_size); None when no row maps the look."""
    found = found or read()
    origin = origin_of(look, found)
    if origin and person_sized(origin[2].get("size")):
        return origin[2]["size"], f"{origin[0]}/{origin[1]}"
    return member_size(look, found)


def member_size(look, found):
    """(size, "<place>/<row>") of one member of the row that draws the look when its size is the row's extent (a
    crowd's, or a row of several people standing apart: the stairwell's walkway people): an average build's box
    (between SLIM and BROAD) as tall as the row; None with no such row."""
    origin = origin_of(look, found)
    if not origin or not (isinstance(origin[2].get("size"), list) and len(origin[2]["size"]) == 3):
        return None
    side = round((SLIM + BROAD) / 2, 3)
    return [side, side, origin[2]["size"][2]], f"{origin[0]}/{origin[1]}"


# --- the refresh from the store (free) ----------------------------------------------------------------------------

def word_list(text):
    """A text's content words in order, once each, lower case, a plural's s dropped (astronauts, astronaut)."""
    words = [word for word in re.findall(r"[a-z]+", text.lower()) if len(word) > 2 and word not in FUNCTION_WORDS]
    return list(dict.fromkeys(word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word
                              for word in words))


def words_of(text):
    """A text's content words, lower case, a plural's s dropped (astronauts, astronaut)."""
    return set(word_list(text))


def named(row):
    """Whether a row names a distinct person: the player, or a name (a capitalised word in its reading's name)."""
    return "player" in words_of(row["name"]) or bool(re.search(r"\b[A-Z][a-z]+", row["name"]))


def look_of(place, row, crowd=False):
    """A row's look by what its people are and wear: its name's words before where it stands or what it holds
    (CLAUSE_WORDS), its pose and colour words left out, a crowd's crowd words too; `<words>-made`. A named person
    is its own, `<place>_<row>-made`."""
    if named(row):
        return f"{place}_{row['id']}-{OUTFIT}"
    said = re.findall(r"[a-z]+", row["name"].lower())
    said = said[:next((number for number, word in enumerate(said) if word in CLAUSE_WORDS), len(said))]
    words = [PLURALS.get(word, word) for word in word_list(" ".join(said)) if word not in POSE_WORDS | COLOUR_WORDS]
    words = [word for word in dict.fromkeys(words) if not (crowd and word in CROWD_WORDS)]
    return f"{'_'.join(words) or ('crowd' if crowd else 'person')}-{OUTFIT}"


def look_words(look, entry):
    """A line look's words: its spec's description (the file its take entry names) and its take's clothes
    (`object`)."""
    description = json.loads((REPO / entry["spec"]).read_text())["description"]
    return words_of(f"{description} {entry.get('object', '')}")


def crowd_look(place, row, line=None):
    """A crowd row's far look, from its words (its name and noun): the people line's look (`line`, {look: take entry},
    bodies.looks()) sharing the most of them, a crowd word (CROWD_WORDS) counting only between looks that share no
    other, a far-only look first on a tie; its own words' look (look_of: `crowd-made`, `alien-made`) when no look
    shares a word, or when the row names who is in it (a word beyond the crowd words: aliens, colonists) and no look
    shares one of those. A look written from design rows (`-made`, or its spec in SPECS) is never matched by words:
    its spec repeats its row's words, so matching it would give every "crowd of people" whichever such look the last
    refresh wrote, and a second refresh would not give the first one's answer."""
    if line is None:
        from score.stages.people_bodies import bodies
        line = bodies.looks()
    line = {look: entry for look, entry in line.items()
            if not look.endswith(f"-{OUTFIT}") and not (REPO / entry["spec"]).is_relative_to(SPECS)}
    said = words_of(f"{row['name']} {row['noun']}")

    def score(look):
        shared = said & look_words(look, line[look])
        return len(shared - CROWD_WORDS), len(shared & CROWD_WORDS), bool(line[look].get("far_only"))
    best = max(sorted(line), key=score, default=None)
    needed = 1 if said - CROWD_WORDS else 0  # who the row names must be matched, not just that it is a crowd
    return best if best and score(best)[0] >= needed and score(best)[:2] != (0, 0) else look_of(place, row, crowd=True)


def default_choice(place, row):
    """A row's looks read from its design: a crowd's far look by its words, else each of its people its row's look
    (look_of)."""
    if row["noun"] == "crowd" or "crowd" in row["name"]:
        return {"crowd": crowd_look(place, row)}
    return {"looks": [look_of(place, row)] * row.get("count", 1)}


def crowd_ground(plan, row_id):
    """[[left, near, wide, long], ...] in the place's frame of each plan item the row makes (the plan's `rows`)."""
    from score.stages.scene_record.plan import items_of
    if not plan or not plan.get("items"):
        return []
    return [[item["box"][0], item["box"][1], round(item["box"][2] - item["box"][0], 4),
             round(item["box"][3] - item["box"][1], 4)]
            for item in items_of(plan) if row_id in (item["rows"] or [])]


def placed_spots(plan):
    """The plan's people spots and its middle in the place's frame (scene_record.plan.placed)."""
    from score.stages.scene_record.plan import placed
    spots = [placed(plan, spot[0], spot[1]).tolist() for spot in plan.get("people", [])
             if len(spot) >= 2 and all(isinstance(value, (int, float)) for value in spot[:2])]
    return spots, placed(plan, plan.get("w", 0.0) / 2, plan.get("d", 0.0) / 2).tolist()


def concept_share(row, picture):
    """The share of the concept's frame height the row's tallest box fills (its SAM 3 instance boxes, [x0, y0, x1, y1]
    pixels, else its one box; `picture` the concept's [wide, high] pixels: a kept inventory's `picture`, a current
    reading's `size`), or None with no box or picture size."""
    boxes = row.get("boxes") or ([row["box"]] if row.get("box") else [])
    if not boxes or not (isinstance(picture, list) and len(picture) == 2 and picture[1]):
        return None
    return round(max(box[3] - box[1] for box in boxes) / picture[1], 4)


def refreshed_place(place, inventory, plan, old, picture=None, fabrics=None):
    """One place's entry from its current reading (`inventory`, groups.current's) and plan, keeping `old`'s hand-made
    choices (a row's recorded with its `why`) where it was read from the same concept; each row's dress read off its
    words and the concept (`picture` H x W x 3, 0..255, or None; `fabrics` {fabric: CIELAB}, people_clothes.fabrics()
    by default). A people row the plan says the painting shows beyond the place (its `beyond`: through a window, past
    its edge, far off) is left out: it belongs to the place it stands in, never stood here (the stairwell's and the
    street's crowds are the square's, seen in the background: Batch 1, 2026-10-25). groups.current routes it so
    (route "skyline"), unless it stands on a row laid here (groups.stood_beyond: the stairwell's man on its stairs)."""
    from score.stages import people_clothes
    fabrics = people_clothes.fabrics() if fabrics is None else fabrics
    concept = inventory["concept_pick"]["sha256"]
    kept = old["rows"] if old and old["concept"] == concept else {}
    rows = {}
    for row in inventory["rows"]:
        if row["route"] != "people":
            continue
        copied = {**{key: row.get(key) for key in ("name", "noun", "count", "size", "where")},
                  "share": concept_share(row, inventory.get("picture") or inventory.get("size"))}
        held = kept.get(row["id"], {})
        chosen = {key: held[key] for key in CHOSEN if key in held} if "why" in held else {}
        rows[row["id"]] = {**copied, **(chosen or default_choice(place, row)),
                           "dress": people_clothes.worn(row, picture, fabrics)}
        if "crowd" in rows[row["id"]]:
            rows[row["id"]]["ground"] = crowd_ground(plan, row["id"])
    spots, middle = placed_spots(plan) if plan else ([], [0.0, 0.0, 0.0])
    return {"concept": concept, "spots": spots, "middle": middle, "rows": rows}


def line_looks():
    """The looks the people line's surface data takes (data/surfaces/people.json)."""
    from score.stages.people_bodies import bodies
    return set(bodies.looks())


# --- the people line's data for the mapped looks -------------------------------------------------------------------

def build_of(fields):
    """A person row's build from its metres: its shoulders (the wider side of its footprint, the narrower when it
    sits) against SLIM and BROAD."""
    wide, deep = fields["size"][:2]
    shoulders = min(wide, deep) if doing_of(fields) == "sitting" else max(wide, deep)
    return "slim" if shoulders < SLIM else "broad" if shoulders > BROAD else "average"


def mapping_rows(found):
    """{look: (place, row, fields, concept)} of the row that draws each look: of the rows that map it, the largest
    (its `share` of its concept's frame) of those whose people stand one person's size, the first (places and rows in
    order) on a tie; a look's spec, size and close-up all come from it."""
    def rank(fields):
        standing = person_sized(fields.get("size")) and doing_of(fields) != "sitting"
        return standing, fields.get("share") or 0.0
    mapped = {}
    for place, entry in sorted(found["places"].items()):
        for row, fields in sorted(entry["rows"].items()):
            for look in dict.fromkeys(fields.get("looks", []) + ([fields["crowd"]] if fields.get("crowd") else [])):
                if look not in mapped or rank(fields) > rank(mapped[look][2]):
                    mapped[look] = (place, row, fields, entry["concept"])
    return mapped


def origin_of(look, found):
    """(place, row, fields, concept) of the row that draws the look (mapping_rows), or None."""
    return mapping_rows(found).get(look)


def designed_spec(look, place, row, fields, concept):
    """The maker's spec (tools/characters/maker/spec.py, the prop route) of a look written from the person row that
    maps it: who by the row's words and where the concept draws it, the build by its metres (build_of), face, hair
    and clothes as drawn in the locked concept, which the line's close-up is drawn from (drawn_from); asked for by
    the creator's pick of that concept."""
    character, outfit = split_look(look)
    member = "one person of the " if "crowd" in fields else ""
    build = build_of(fields) if person_sized(fields.get("size")) else "average"
    drawn = f"as drawn in the {place} concept"
    return {"name": character, "kind": "person", "route": "prop",
            "approved": f"the creator's pick of the {place} concept ({concept[:8]}): its scene inventory's people row "
                        f"{row} (data/people/rows.json), this spec written from it by score/stages/people_rows.py",
            "why": f"{member}{fields['name']} of the {place} concept, {fields.get('where') or 'in the place'}",
            "references": [], "description": f"{member}{fields['name']}, {'an' if build == 'average' else 'a'} "
                                             f"{build} build, {drawn}",
            "outfit_words": {outfit: f"the clothes {drawn}"}, "outfits": [outfit],
            "hair": f"the hair {drawn}", "face": f"the face {drawn}"}


def designed_specs(found, surfaces):
    """{look: spec} of every look the designs map that no hand-written spec on the line makes (its take's `spec` out
    of SPECS), each written from its row (designed_spec)."""
    handmade = {look for look, take in surfaces["bake"]["models"].items()
                if take in surfaces["takes"] and not (REPO / surfaces["takes"][take]["spec"]).is_relative_to(SPECS)}
    return {look: designed_spec(look, *origin) for look, origin in sorted(mapping_rows(found).items())
            if look not in handmade}


def spec_path(spec):
    return SPECS / f"{spec['name']}.json"


def with_designed(specs, props, inventory, surfaces):
    """The people line's three records with each designed look's object, row and take (its spec at spec_path), in
    place of any it had: (props, inventory, surfaces)."""
    takes = {look: TAKE.format(look=look) for look in specs}
    objects = {look: {"route": "prop", "take": take, "layer": LINE, "failures": {
        "parts": f"split a second time by people-look-parts-{look} (SAM 2.1, GeoSAM2, the judge's materials) for the "
                 "garments the route binds by limb, beside the loop's finish-route split",
        "body": f"people-body-{look} builds from the raw Pixal3D take, not the loop's baked model handed on in "
                "made.json"}} for look, take in takes.items()}
    rows = [{"id": look, "name": spec["outfit_words"][split_look(look)[1]], "prop": look}
            for look, spec in specs.items()]
    entries = {take: {"places": [LINE], "library_places": [LINE], "place": LINE, "kind": "person",
                      "object": specs[look]["outfit_words"][split_look(look)[1]],
                      "spec": str(spec_path(specs[look]).relative_to(REPO)), "outfit": split_look(look)[1]}
               for look, take in takes.items()}
    return ({**props, "objects": {**props["objects"], **objects}},
            {**inventory, "rows": [row for row in inventory["rows"] if row["id"] not in specs] + rows},
            {**surfaces, "takes": {**surfaces["takes"], **entries},
             "bake": {**surfaces["bake"], "models": {**surfaces["bake"]["models"], **takes}}})


def spec_of(look, surfaces):
    """A look's spec as the line's take of it names it."""
    return json.loads((REPO / surfaces["takes"][surfaces["bake"]["models"][look]]["spec"]).read_text())


def description_of(look, specs=None, surfaces=None):
    """Who a look is, from its spec (a designed one in `specs`, else the file its take names; the prop route the
    people are made by): "a Chinese man in his thirties, ..." or "seated astronaut, an average build, as drawn in the
    airlock concept", which the reading's words, the clothes alone, lack."""
    if specs and look in specs:
        return specs[look]["description"]
    surfaces = surfaces or json.loads(LINE_FILES["surfaces"].read_text())
    return spec_of(look, surfaces)["description"]


def described(look, row, specs, surfaces):
    """A line row's words, the close-up's (score/stages/props/closeup_row.py reads `name`): its spec's description,
    then the clothes as read (`clothes`, kept on the row so a second write does not describe it twice)."""
    clothes = row.get("clothes", row["name"])
    return {"name": f"{description_of(look, specs, surfaces)}; {clothes}", "clothes": clothes}
