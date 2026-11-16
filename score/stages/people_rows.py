"""The people of each place's picked design (#26): every people row of its scene inventory (the reading of its picked
concept, score/review/reading.py) mapped to a look on the shared people line, kept in data/people/rows.json:

    {"places": {<place>: {"concept": <the picked draw's sha256 the reading was read from>,
                          "spots": [[x, y, z(, row)], ...] (the plan's people spots in the place's frame, each one
                                    stood for a people row tagged with its id), "middle": [x, y, z],
                          "rows": {<row>: {"name", "noun", "count", "size" [wide, deep, tall] metres, "where",
                                           "anchor" (what its reading stands it on: "floor", "on:<row>", ...),
                                           "share" (its tallest box's share of the concept's frame height, or null),
                                           "looks": [<look>, ... one a person]  |  "crowd": <far look>,
                                           "ground": [[left, near, wide, long], ...] (a crowd's: the plan items
                                                     its row makes, in the place's frame),
                                           "dress": {"surface": <library fabric> | null, ...}}}}}}

A row's `dress` is what its people wear (`{"surface": <library fabric> | null}`), each person of a row with a surface
dressed by `people-dress-<look>-in-<surface>`. Each person its own variant (owner, 2026-10-25: "Each one looks
different"): the people of one look in a place are numbered 0, 1, ... (`persons`), the first the look's plain dress row,
each other `-v<n>`, the same body finished in other library surfaces (score/stages/people/dress.py's `varied`), so no
two people of a place look the same and the bodies are not made again. One body a look (owner, 2026-10-22: "make
bodies one per look"): people rows are grouped into looks by what they say they are and wear (`look_of`: the row's
words before where it stands or what it holds, its pose and colour words left out, so a seated astronaut and five
standing ones in another scene are one `astronaut-made`); a named person (a capitalised word in its row's name) or the
player is a look of its own, `<place>_<row>-made`. A crowd is one far look in a few palettes of clothes (CONTEXT.md
"crowd"), its palettes that look's first `crowd_variants` variants. The cast (score/stages/cast) and the characters
layer read who is in a place from here, each person on its row's plan people spot (`placed_spots`, `dealt_spots`).

rows.json is kept data: the refresh that wrote it again from each concept's reading (people_refresh.py, the dress
picked off the concept's pixels by people_clothes.py, the line's specs and takes written from the rows) was wiped with
the per-picture pipeline (owner, #128, 2026-11-16); the line's records (data/props, data/inventory, data/surfaces
people.json, data/people/specs) stand as last written.
"""
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
ROWS = REPO / "data/people/rows.json"
# A look written from its person rows wears the clothes its concept draws it in, on the route's made body and face.
OUTFIT = "made"
# A crowd wears this many variants of its look's body at most (CONTEXT.md "crowd": a few palettes of clothes; the
# square's first crowd wore five, 2026-10-12), never more than the people SAM 3 counted in it.
CROWD_VARIANTS = 5
# A crowd's draws in cast.py (tools/characters/cast.py's crowd_copies): each copy turned up to TURN_JITTER radians off
# facing the place's middle and HEIGHT_JITTER of its height taller or shorter (the square's first crowd's, 2026-10-12).
TURN_JITTER, HEIGHT_JITTER = 0.35, 0.06
# The words that say a row is a crowd, not who is in it: they count only between looks that share no other word.
CROWD_WORDS = {"crowd", "people", "person", "group"}
# A look is what its people are and wear: a row's words from one of these on say where it stands or what it holds.
CLAUSE_WORDS = {"on", "at", "by", "near", "under", "behind", "beside", "next", "inside", "outside", "beneath", "above",
                "against", "around", "along", "across", "holding", "carrying", "pushing", "pulling", "looking", "from"}
# How a person stands (its clip, doing_of) and its colours (its dress) vary a look; they make none.
POSE_WORDS = {"seated", "sitting", "standing", "walking", "kneeling", "lying", "distant", "far"}
# The words of an anchor's row id that name a seat (a row anchored `on:<id>` sits on it: doing_of): camp's dining
# stool and office chair, the cockpit's pilot seat, the quarters' bunk bed and chair (8 people sat on the floor in a
# ground-sit, 2026-11-04, their anchors lost in rows.json).
SEAT_WORDS = {"chair", "stool", "seat", "bench", "bed", "bunk", "sofa", "couch", "armchair", "pew", "saddle"}
COLOUR_WORDS = {"white", "black", "grey", "gray", "blue", "red", "green", "yellow", "orange", "brown", "purple",
                "pink", "beige", "navy", "dark", "light", "pale", "bright"}
# A garment that says who wears it (owner, 2026-10-22: one body a look, by what its people are and wear): a person in
# a spacesuit is an astronaut, so the lab's "person in spacesuit" is the astronaut look, not a look of its own that no
# batch dresses (audit 2026-11-04: astronaut_suit, astronaut_spacesuit and person_spacesuit, 10 people, never laid).
WORN_BY = {"spacesuit": "astronaut"}
# The garments a who already wears, which name no other look ("astronaut in white suit" is the astronaut look; the
# suit's colour is its dress); and the words for anyone, which a garment's wearer replaces.
IMPLIED = {"astronaut": {"suit", "spacesuit", "helmet"}}
ANYONE = {"person", "man", "woman"}
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
    """A person's clip by the row's words: sitting (seated on a seat its anchor `on:<id>` names, seat_of), walking,
    else standing."""
    words = f"{row.get('name', '')} {row.get('where', '')}".lower()
    if "sitting" in words or "seated" in words:
        return "seated" if seat_of(row) else "sitting"
    return "walking" if "walking" in words else "standing"


def seat_of(row):
    """The row id a row's anchor puts it on when that row is a seat (its id's words name one: SEAT_WORDS), or None."""
    anchor = str(row.get("anchor") or "")
    held = anchor.removeprefix("on:") if anchor.startswith("on:") else ""
    return held if SEAT_WORDS & set(re.split(r"[^a-z]+", held.lower())) else None


def surface_of(fields):
    """The library fabric a row's people wear (its `dress`), or None: the look's own paint."""
    return (fields.get("dress") or {}).get("surface")


def persons(place, found=None):
    """[{name, row, look, doing, surface, variant}] of every person the place's design shows (a crowd is not among
    them); the people of one look numbered 0, 1, ... in order, each its own variant of the look's body (the dress
    row `-v<n>`)."""
    entry = place_entry(place, found) or {"rows": {}}
    found = [{"name": row if len(fields["looks"]) == 1 else f"{row}_{number}", "row": row, "look": look,
              "doing": doing_of(fields), "surface": surface_of(fields), "anchor": fields.get("anchor")}
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


def dealt_spots(entry, people):
    """The spot [x, y, z] each of `people` (persons') stands at: the next of the spots tagged with its own row (in
    turn), and for a row with no tagged spot the next of the untagged ones (a view's), else the place's middle. Dealt
    in turn over persons sorted by row id, the cockpit's pilot stood on the officer's spot and the street's diner on
    the pavement (2026-11-04)."""
    spots = entry.get("spots") or []
    tagged = {}
    for spot in spots:
        if len(spot) >= 4:
            tagged.setdefault(spot[3], []).append(spot[:3])
    untagged = [spot[:3] for spot in spots if len(spot) < 4] or [entry.get("middle", [0.0, 0.0, 0.0])]
    taken, found = {}, []
    for person in people:
        own = tagged.get(person["row"]) or untagged
        key = person["row"] if person["row"] in tagged else None
        found.append(own[taken.get(key, 0) % len(own)])
        taken[key] = taken.get(key, 0) + 1
    return found


def cast_record(place, found=None):
    """The place's cast record in tools/characters/cast.py's form, from its design: each person at its row's own plan
    people spot (dealt_spots; the cast stage stands them clear round it), facing the place's middle; the crowd its
    far look in its variants on its ground (crowd_record)."""
    found = found or read()
    entry = place_entry(place, found)
    people, shown = [], persons(place, found)
    for person, spot in zip(shown, dealt_spots(entry, shown)):
        character, outfit = split_look(person["look"])
        people.append({"name": person["name"], "character": character, "look": f"{character}_{outfit}",
                       "doing": person["doing"], "surface": person["surface"], "variant": person["variant"],
                       "anchor": person["anchor"], "at": spot,
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


# --- a row's look by its words ------------------------------------------------------------------------------------

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


def look_of(place, row, crowd=False, folded=True):
    """A row's look by what its people are and wear: its name's words before where it stands or what it holds
    (CLAUSE_WORDS), its pose and colour words left out, a crowd's crowd words too, a garment read as who wears it
    (worn_by; not when `folded` is False: the look its words alone name); `<words>-made`. A named person is its own,
    `<place>_<row>-made`."""
    if named(row):
        return f"{place}_{row['id']}-{OUTFIT}"
    said = re.findall(r"[a-z]+", row["name"].lower())
    said = said[:next((number for number, word in enumerate(said) if word in CLAUSE_WORDS), len(said))]
    words = [PLURALS.get(word, word) for word in word_list(" ".join(said)) if word not in POSE_WORDS | COLOUR_WORDS]
    words = [word for word in dict.fromkeys(words) if not (crowd and word in CROWD_WORDS)]
    return f"{'_'.join(worn_by(words) if folded else words) or ('crowd' if crowd else 'person')}-{OUTFIT}"


def worn_by(words):
    """A look's words with each garment that says who wears it (WORN_BY) put as its wearer in place of the words for
    anyone (ANYONE), and every garment its who already wears (IMPLIED) left out."""
    wearers = [WORN_BY[word] for word in words if word in WORN_BY]
    words = list(dict.fromkeys(wearers + [word for word in words if not (wearers and word in ANYONE)]))
    return [word for word in words if not any(word in IMPLIED.get(who, ()) for who in words)]


def placed_spots(plan):
    """The plan's people spots and its middle in the place's frame (scene_record.plan.placed), each spot the plan
    stood for a people row keeping that row's id as its fourth value ([x, y, z, row]; a view's spot only [x, y, z])."""
    from score.stages.scene_record.plan import placed
    spots = [placed(plan, spot[0], spot[1]).tolist() + ([spot[3]] if len(spot) >= 4 and isinstance(spot[3], str)
                                                        else [])
             for spot in plan.get("people", [])
             if len(spot) >= 2 and all(isinstance(value, (int, float)) for value in spot[:2])]
    return spots, placed(plan, plan.get("w", 0.0) / 2, plan.get("d", 0.0) / 2).tolist()
