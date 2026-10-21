"""An environment's default film (the owner, 2026-10-21: "just do my script as the default setup u can then change"):
the structure of his script for environment 1 (data/films/env1_demo.json), filled in from the environment's own
setting and scenes. The app's own steps in its own windows (the setting, its animation, the environment concept, a
room's concept review, the top scene's inventory and plan), then one unbroken shot from the setting down into the top
scene's rooms, then a walk through each of those rooms, then on through the whole environment (owner, 2026-10-21: "its
needs to show all of env 1"): every other top scene, the rest of its body's first, then body by body, each reached
from the one before over the ground or out to orbit and in again (the environment plan's sites, metres and the true
distances its skies give), its concept in the corner, round it from outside and into its first rooms. The top scene
is the site holding the most scenes; its rooms, like every scene's, the first three it holds. Every segment long enough to read what it shows (owner, 2026-10-21: the physics animation
long enough for a body to go a clear way round its orbit), the target the film's own length. The FILM page opens on
it until he saves his own; plain Python, the hosted process reads it too.

    facts  {"world", "title" (the environment's name), "bodies" [body] (the setting's, in its order), "shining"
            [body] (those that shine: drawn by their light, no surface),
            "body" (the top scene's site's body), "top", "top_name", "rooms" [[place, name]],
            "stops" [{place, name, body, rooms, metres (from the site before on its body), km (from the site
            before, on another body)}] (every top scene in the journey's order, the top scene first),
            "surfaces" {body: library surface} (each body's, as earlier scripts drew it; a body with none waits)}
"""
import math

from score.dashboard.films import script

# The physics animation: 12 s at 30 days a second, so a year-long orbit (Earth round the Sun) goes nearly once round.
DAYS_PER_SECOND = 30
ANIMATION_SECONDS = 12.0
SITE_SECONDS = 2.5  # a journey's site leg, where the next scene's concept comes into the corner


def titled(word):
    return word[:1].upper() + word[1:]


def caption(start, end, line, text):
    return {"from": start, "to": end, "line": line, "text": text}


def segment(cut, shows, seconds, captions, **rest):
    return {"cut": cut, "shows": shows, "transition": "cross-fade", "sound": "bed", "seconds": seconds,
            "captions": captions, **rest}


def setting_take(facts):
    """1: the setting on the environment concept page, the top scene's body boxed."""
    body, card = titled(facts["body"]), f".sp-card:nth-child({facts['bodies'].index(facts['body']) + 1})"
    return segment("screen-take", {"page": f"/environments/{facts['world']}/"}, 6.0, [caption(
        0.4, 5.8, "1 · Physics", "What everything stands on: " + ", ".join(map(titled, facts["bodies"])))],
        transition="fade-through-black", take=[
            {"at": 0.3, "do": "scroll", "on": "section[aria-label=physics]", "over": 1.1},
            {"at": 1.6, "do": "box", "on": "section[aria-label=physics] svg", "for": 2.0, "words": "The physics"},
            {"at": 2.0, "do": "move", "on": card, "over": 0.9},
            {"at": 3.5, "do": "box", "on": card, "for": 2.4, "words": f"{body}: where {facts['top_name']} stands"}])


def concept_take(facts):
    """2: the environment concept's style line and references."""
    pictures = "section[aria-label='reference pictures']"
    return segment("screen-take", {"page": f"/environments/{facts['world']}/"}, 7.0, [caption(
        0.4, 6.8, "2 · Environment concept", "One style line and the creator's own reference pictures")], take=[
        {"at": 0.6, "do": "box", "on": "section[aria-label=style]", "for": 2.4, "words": "Style line"},
        {"at": 0.9, "do": "move", "on": "section[aria-label=style]", "to": [0.4, 0.62], "over": 0.9},
        {"at": 3.1, "do": "scroll", "on": pictures, "over": 1.0},
        {"at": 4.3, "do": "move", "on": f"{pictures} img", "over": 0.8},
        {"at": 4.4, "do": "box", "on": f"{pictures} img", "for": 2.5, "words": "A reference"}])


def review_take(facts):
    """3: the first room's concept review, its draws stepped through newest last."""
    room, name = facts["rooms"][0]
    history = ".concept-history a:nth-child({})"
    return segment("screen-take", {"page": f"/concept/{room}/"}, 14.0, [
        caption(0.4, 4.4, "3 · Concept review", f"{name}, inside {facts['top_name']}: its first draw"),
        caption(4.8, 9.0, "Redraw with notes", "The creator's notes, drawn again"),
        caption(9.4, 13.8, "One image model call a draw",  # its provider named only by its cost line (overlay)
                "Every draw is one call to the image model, locked by the creator")], view=1800, take=[
        {"at": 1.4, "do": "move", "on": history.format(3), "over": 0.8},
        {"at": 2.4, "do": "click", "on": history.format(3)},
        {"at": 3.2, "do": "move", "on": history.format(2), "over": 0.8},
        {"at": 3.3, "do": "box", "on": history.format(2), "for": 1.6, "words": "Redraw with notes"},
        {"at": 4.8, "do": "click", "on": history.format(2)},
        {"at": 5.4, "do": "box", "on": "#concept-picture", "for": 3.2, "words": "Redrawn from the notes"},
        {"at": 8.6, "do": "move", "on": history.format(1), "over": 0.8},
        {"at": 9.6, "do": "click", "on": history.format(1)},
        {"at": 10.2, "do": "box", "on": history.format(1), "for": 3.4, "words": "Locked"}])


def plan_take(facts):
    """4: the top scene's inventory, then the environment plan's map of its body with its blockout."""
    top, body = facts["top_name"], titled(facts["body"])
    section, blockout = f"section[aria-label={body}]", f"img[alt='{top} blockout']"
    return segment("screen-take", {"page": f"/concept/{facts['top']}/"}, 10.0, [
        caption(0.4, 3.6, "4 · Inventory and plan", f"Read from the locked concept: what {top} holds"),
        caption(4.0, 9.8, "Environment plan", f"Every site on {body}, true metres apart, each with its blockout")],
        take=[{"at": 0.6, "do": "move", "on": "#inventory-part", "over": 0.9},
              {"at": 0.8, "do": "box", "on": "#inventory-part", "for": 2.4, "words": "Scene inventory"},
              {"at": 3.4, "do": "goto", "page": f"/environments/{facts['world']}/plan/"},
              {"at": 3.6, "do": "scroll", "on": section, "over": 1.0},
              {"at": 4.8, "do": "box", "on": f"{section} svg", "for": 2.4, "words": f"{body}'s sites"},
              {"at": 5.0, "do": "move", "on": f"{section} svg", "to": [0.2, 0.6], "over": 0.9},
              {"at": 7.3, "do": "move", "on": blockout, "over": 0.7},
              {"at": 7.4, "do": "box", "on": blockout, "for": 2.4, "words": f"{top}'s blockout"}])


def surfaces_of(facts):
    """{body: surface} the setting's drawings need, the ground its site's body's; (that, the bodies with none)."""
    known = facts["surfaces"]
    found = {body: known[body] for body in facts["bodies"] if body in known}
    if facts["body"] in known:
        found["ground"] = known[facts["body"]]
    return found, [body for body in facts["bodies"] if body not in known and body not in facts["shining"]]


def zoom(facts):
    """5: one unbroken shot from the setting down into the top scene's rooms."""
    top, body, rooms = facts["top_name"], titled(facts["body"]), facts["rooms"]
    surfaces, bare = surfaces_of(facts)
    waits = "Blockout · the finished scene waits on the batch"
    found = segment("scale-zoom", {"place": facts["top"]}, 22.0, [
        caption(0.3, 3.3, "5 · One shot, every scale", "The physics"), caption(3.7, 7.3, "World", body),
        caption(7.7, 11.3, "Site", f"{top}'s site, from the environment plan"),
        caption(11.7, 16.2, "Place", f"{top} from outside, its concept beside it"),
        caption(16.6, 21.8, "Rooms", "Inside: " + ", ".join(name for _, name in rooms))],
        surfaces=surfaces, legs=[
            {"layer": "setting", "seconds": 3.5, "days_per_second": 1.0}, {"layer": "world", "seconds": 4.0},
            {"layer": "site", "seconds": 4.0, "tag": waits},
            {"layer": "place", "seconds": 5.0, "into": rooms[0][0], "tag": waits},
            {"layer": "room", "seconds": 5.5, "rooms": [room for room, _ in rooms],
             "tag": "Concepts · the finished rooms wait on the batch"}],
        pip={"concept": facts["top"], "corner": "top-left", "label": "Concept", "from": 11.8, "to": 16.4},
        waiting=waiting_words(top, bare))
    return found


def waiting_words(name, bare, rooms=True):
    return (f"the finished {name}{' and its rooms' if rooms else ''} (the batch): until then the site and place legs "
            "show the environment plan's blockout" + (" and the room leg the rooms' locked concepts" if rooms else "")
            + (f"; no library surface drawn for {', '.join(bare)} yet" if bare else ""))


def distance_words(km):
    """A distance between bodies to three figures: "401,000 km", "63.7 million km"."""
    return f"{round(km, -3):,.0f} km" if km < 1e6 else f"{km / 1e6:.3g} million km"


def legs_captioned(legs, words):
    """Each leg's caption ([line, text], None for none) on the segment's clock."""
    found, start = [], 0.0
    for leg, said in zip(legs, words):
        if said:
            found.append(caption(round(start + 0.2, 2), round(start + leg["seconds"] - 0.2, 2), *said))
        start += leg["seconds"]
    return found


def stop_zoom(facts, before, stop):
    """One leg of the journey after the top scene: from the site before, over the ground to the next site on the same
    body, else out to orbit, through the setting to the next body and down to its site; then round the scene from
    outside, its concept in the corner, and into a few of its rooms."""
    name, rooms = stop["name"], stop["rooms"]
    surfaces, bare = surfaces_of({**facts, "body": stop["body"]})
    waits = "Blockout · the finished scene waits on the batch"
    if stop["body"] == before["body"]:
        apart = f", {stop['metres']:g} m from {before['name']}" if stop.get("metres") else ""
        legs = [{"layer": "site", "seconds": SITE_SECONDS, "from_place": before["place"], "tag": waits}]
        words = [["Site", f"{name}{apart}"]]
    else:
        body, away = titled(stop["body"]), stop.get("km")
        legs = [{"layer": "world", "place": before["place"], "seconds": 2.0, "from": 1.05, "to": 4.2},
                {"layer": "setting", "seconds": 4.0, "from_body": before["body"], "days_per_second": 1.0},
                {"layer": "world", "seconds": 3.0}, {"layer": "site", "seconds": SITE_SECONDS, "tag": waits}]
        words = [["Leaving", titled(before["body"])],
                 ["Across the physics", body + (f", {distance_words(away)} away" if away else "")],
                 ["World", body], ["Site", f"Where {name} stands, from the environment plan"]]
    reached = sum(leg["seconds"] for leg in legs)
    legs.append({"layer": "place", "seconds": 3.0, "tag": waits, **({"into": rooms[0][0]} if rooms else {})})
    words.append(["Place", f"{name} from outside, its concept beside it"])
    if rooms:
        legs.append({"layer": "room", "seconds": max(2.5, 1.8 * len(rooms)), "rooms": [room for room, _ in rooms],
                     "tag": "Concepts · the finished rooms wait on the batch"})
        words.append(["Rooms", "Inside: " + ", ".join(room_name for _, room_name in rooms)])
    return segment("scale-zoom", {"place": stop["place"]}, round(sum(leg["seconds"] for leg in legs), 2),
                   legs_captioned(legs, words), surfaces=surfaces, legs=legs, waiting=waiting_words(name, bare, bool(rooms)),
                   pip={"concept": stop["place"], "corner": "top-left", "label": "Concept",
                        "from": round(reached - SITE_SECONDS, 2), "to": round(reached + 3.0, 2)})


def journey(facts):
    """The rest of the environment after the top scene's rooms: every other top scene, body by body (see facts)."""
    stops = facts["stops"]
    return [stop_zoom(facts, before, stop) for before, stop in zip(stops, stops[1:])]


def walk(room, name):
    """6 on: a walk through one of the top scene's rooms, on its own sound."""
    return {**segment("walk-through", {"place": room}, script.WALK_SECONDS, []), "sound": "place", "line": "Inside",
            "text": name,
            "waiting": "the finished room and its film (the batch): until then the preview shows its name"}


def built(film, facts):
    """The environment's default script, named `film`: its target the film's length, rounded up to 5 s."""
    surfaces, _ = surfaces_of(facts)
    days = round(DAYS_PER_SECOND * ANIMATION_SECONDS)
    animation = segment("setting-animation", {"world": facts["world"]}, ANIMATION_SECONDS, [caption(
        0.5, ANIMATION_SECONDS - 0.3, "Physics animation",
        f"Their real orbits: {days} days in {ANIMATION_SECONDS:g} s")],
        days_per_second=DAYS_PER_SECOND, surfaces={body: surface for body, surface in surfaces.items()
                                                    if body != "ground"},
        note="sizes and orbits enlarged to read")
    title = {"cut": "title", "shows": {"world": facts["world"]}, "transition": "fade-through-black", "sound": "bed",
             "text": "SCORE", "line": facts["title"], "seconds": 4.0}
    made = {"format": script.FORMAT, "version": script.VERSION, "film": film, "title": f"SCORE: {facts['title']}",
            "world": facts["world"], "default": True, "size": [1280, 720], "rate": 24,
            "bed": "sound/base_hum", "defaults": {},
            "why": "The default film: the app's own steps in its own windows, then one unbroken shot from the "
                   "setting down into the top scene's rooms and a walk through each, then on to every other top "
                   "scene, body by body (the owner's script for environment 1, filled in from this environment's "
                   "scenes)",
            "segments": [title, setting_take(facts), animation, concept_take(facts), review_take(facts),
                         plan_take(facts), zoom(facts), *(walk(room, name) for room, name in facts["rooms"]),
                         *journey(facts)]}
    return {**made, "target_seconds": 5 * math.ceil(script.total_seconds(made) / 5)}


def named(place, names):
    return names.get(place) or titled(place.replace("_", " "))


def body_km(sky, body, radius_km):
    """How far `body` is from a site, from its true size in the site's sky (the environment plan's); None unknown."""
    seen = next((world for world in sky.get("worlds", []) if world["world"] == body), None)
    return radius_km / math.tan(math.radians(seen["across"]) / 2) if seen and radius_km and seen["across"] else None


def stops_of(plan, within, names, radii, top):
    """Every top scene in the journey's order: the top scene, the other sites on its body, then each other body's
    sites, all in the environment plan's order; each with its rooms (the first three it holds), the metres from the
    site before on the same body and the km from the site before to a new body."""
    maps = plan["maps"]
    first = next(found for found in maps if any(site["place"] == top for site in found["sites"]))
    ordered = [(first, next(site for site in first["sites"] if site["place"] == top))]
    ordered += [(first, site) for site in first["sites"] if site["place"] != top]
    ordered += [(found, site) for found in maps if found is not first for site in found["sites"]]
    stops = []
    for found, site in ordered:
        stop = {"place": site["place"], "name": named(site["place"], {site["place"]: site["name"], **names}),
                "body": found["on"], "sky": site.get("sky") or {},
                "rooms": [[room, named(room, names)] for room, holder in within.items() if holder == site["place"]][:3]}
        before = stops[-1] if stops else None
        if before and before["body"] == stop["body"]:
            stop["metres"] = next((entry["metres"] for entry in found.get("distances", [])
                                   if {entry["from"], entry["to"]} == {before["place"], stop["place"]}), None)
        elif before:
            stop["km"] = body_km(before["sky"], stop["body"], radii.get(stop["body"]))
        stops.append(stop)
    return [{key: value for key, value in stop.items() if key != "sky"} for stop in stops]


def top_scene(sites, within):
    """The site holding the most scenes (the first on a tie), and the scenes it holds in order."""
    held = {site: [place for place, holder in within.items() if holder == site] for site in sites}
    top = max(sites, key=lambda site: len(held[site]))
    return top, held[top]


def facts_of(world, title, setting, plan, within, names, surfaces):
    """The facts `built` fills in, from the environment's setting ({bodies}), its plan ({maps [{on, sites, distances}]}),
    what each scene sits within (no part of a scene's outside, nothing removed), {place or shell: its short name} and
    the library surfaces earlier scripts drew each body with; None when the plan places no scene or its top scene
    holds none."""
    sites = {site["place"]: found["on"] for found in (plan or {}).get("maps", []) for site in found["sites"]}
    if not sites:
        return None
    top, rooms = top_scene(list(sites), within)
    if not rooms:
        return None
    bodies = setting.get("bodies", [])
    stops = stops_of(plan, within, names, {body["body"]: body.get("radius_km") for body in bodies}, top)
    return {"world": world, "title": title, "bodies": [body["body"] for body in bodies],
            "shining": [body["body"] for body in bodies if body.get("kelvin")],
            "body": sites[top], "top": top, "top_name": stops[0]["name"], "rooms": stops[0]["rooms"],
            "stops": stops, "surfaces": surfaces}


def drawn_surfaces(scripts):
    """{body: library surface} as the given scripts' segments draw each body (a later script's over an earlier)."""
    found = {}
    for given in scripts:
        for shown in given.get("segments", []):
            found.update({body: surface for body, surface in (shown.get("surfaces") or {}).items()
                          if body != "ground"})
    return found
