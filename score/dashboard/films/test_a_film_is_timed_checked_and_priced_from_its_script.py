"""Invariant: a film is its script: timed on the script's own clock, checked in words, its render items priced from
measured frames only (reused, free, the basket's place film row, or new), saved and locked in the cockpit's home by the
owner only, its lock what the film rows and Buy wait for; the free preview cut on the same clock with the design's
sound bed and the setting drawn from its own physics; environment 1's starters sound and complete, and every other
environment's default built from its own scenes.

One test, test_a_film_is_timed_checked_and_priced_from_its_script: the clock table (CLOCK), the fault table (rows
built in the body from the starters and the default films), the priced film (PRICED), one cockpit world driven
through its pages (film step, Buy, editor, save, basket, lock, preview, new film), the default film of an environment
of its own (with and without people) and the preview's drawn setting and bed. Each break names the part it turns red.

Breaks that turn this red (each applied once and seen red, then reverted):
- script.OVERLAPPING without "push" -> the clock table's "overlaps" row
- script.segment_faults: the step-card check -> `if False:` -> the fault table's "words" row
- script.film_file: the name check -> `if False:` (or NAME back to `$`) -> the film file names refused
- render.walk_item: reuse without the film shot's length check -> PRICED's 3.5 s and 7 s walks of alpha
- render.FILM_FRAMES = 120 -> the film shot against the demo-film rows
- script.faults: every named place counted unknown -> the fault table's starter rows
- render.segment_item: an unrendered cut priced as "film" -> the editor's priced answer, PRICED's exploded row
- pages/films.film_save: the owner check -> `if False:` -> the cockpit world's save by another
- render.walk_item: the basket row for any place film -> the cockpit world's basket
- pages/films.film_new: `script.blank(film, film)` -> the cockpit world's new film
- takes.step_faults: the spending-click check -> `if False:` -> the fault table's "screen take" row
- render.FILMED_LAYERS without "room" -> PRICED's zoom into the hub's rooms
- preview/make.XFADES push -> "slideright" -> the clock table's "joined" row
- preview/make.bed_sound: `if beds.get(place)` -> `if place in beds` -> the bed table
- preview/scenes.scales: a moon's ring `+ 22.0` -> `+ 30.0` -> the setting drawn to the picture's scale
- api/routes.film_preview: a plain Response in place of the FileResponse (no ranges) -> the cockpit world's preview
- pages/films.bought_since: `return ""` -> the cockpit world's Unlock after a checkout
- script.films_node: `return False` -> the cockpit world's Buy before and after the lock
- default.sim_bodies: the CLIPS_TRUE_ON scenes not put first -> the sim bodies part's order
- default.sim_bodies: `entry[0] in walked and entry[0] not in people` -> `False` -> the place peels, the env1 starter
- default.people_of: a crowd-only place's `else None` dropped (its walks given) -> the people rows read
- default.walks: Outside and Inside swapped -> the default film's lines
- default.walks: a held scene said "Inside" whatever its record says -> the default film's lines
- default.stops_of: a shell walked never, its plan or not (`planned` dropped) -> the planned default film's shots
- default.walks: no still from a designed eye (`facts["eyes"]` unread) -> the planned default film's shots
- script.design_faults: each of its checks (record, rooms_faults, finished stage, eye, apart_faults) -> `if False:` ->
  the frozen default film's design faults
- default.refreshed: zoom_refreshed, shot_refreshed or tops_shot skipped (as it is) -> the refreshed default film
- script.default_name: the saved scripts read before the starters -> the cockpit world's film step
- preview/make.beat_offset: rounded to 1 place -> the beat table
- preview/scenes.LIT_DEGREES = -90 -> the zoom's arrival in daylight
- preview/scenes.face_colour: hex pairs read (3, 1, 5) -> the body's face colour
- state/local.DESIGNED_BED: "the scene's design" -> the sound stage's designed bed
- preview/make.node_used: without the version -> the recorder's node
"""
import json
import math
import re
import shutil
import types

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from score.dashboard.films import render, script, takes
from score.dashboard.pages.models import BasketItem
from score.dashboard.tests.fixture import api

# The preview's player is served by the FastAPI app in its own thread, so the world is committed, not rolled back.
pytestmark = pytest.mark.django_db(transaction=True)


def signed_in(name="joey"):
    user, made = get_user_model().objects.get_or_create(username=name)
    if made:
        user.set_password("a long enough password")
        user.save()
    client = Client(enforce_csrf_checks=False)
    client.force_login(user)
    return client


def a_script(segments, **more):
    return {**script.blank("trailer", "A trailer"), "segments": segments, **more}


def outside_ids_fold(html):
    """The page's visible text outside <details class=\"ids\">, its tags and scripts dropped."""
    html = re.sub(r'<details class="ids">.*?</details>', "", html, flags=re.S)
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def editor_of(html):
    return json.loads(re.search(r'<script id="film-data" type="application/json">(.*?)</script>', html, re.S).group(1))


def design_scenes(repo):
    """Environment 1's scenes as its data names them (data/places/within.json's tree and shells, each look's scenes in
    data/definitions/place.json): the test's store holds no design, so no scene of it is a place of the build here."""
    within = json.loads((repo / "data/places/within.json").read_text())
    looks = json.loads((repo / "data/definitions/place.json").read_text())
    return ({*within["within"], *(entry["within"] for entry in within["within"].values()), *within["shells"]}
            | {scene for look in looks.values() if isinstance(look, dict) for scene in look.get("scenes", [])})


# The clock: each row's segments (and defaults) timed, its total, where its cuts fall and how the preview joins them.
OVERLAPS = [{"cut": "title", "transition": "fade-through-black"},
            {"cut": "walk-through", "shows": {"place": "alpha"}, "transition": "cross-fade"},
            {"cut": "step-card", "shows": {"place": "alpha", "step": "plan"}, "transition": "push", "seconds": 2},
            {"cut": "text", "transition": "cut"}]
CLOCK = [
    ("overlaps", OVERLAPS, None, {"timeline": [(0.0, 4.0), (3.5, 7.0), (10.0, 2.0), (12.0, 4.0)], "total": 16.0}),
    ("overlaps, walks of 5 s", OVERLAPS, {"walk-through": 5.0}, {"total": 14.0}),
    ("joined", [{"cut": "title", "transition": "fade-through-black", "seconds": 4},
                {"cut": "text", "transition": "fade-through-black", "seconds": 3},
                {"cut": "text", "transition": "cross-fade", "seconds": 3},
                {"cut": "text", "transition": "push", "seconds": 2}], None,
     {"total": 11.0, "made": "j3", "joined": ["transition=fade:duration=0.5:offset=6.500", "transition=slideleft",
                                              "concat=n=2", "fade=t=out:st=3.750"]}),
    ("beats", [{"cut": "title", "transition": "fade-through-black", "seconds": 4},
               {"cut": "text", "transition": "cross-fade", "seconds": 3},
               {"cut": "text", "transition": "fade-through-black", "seconds": 3}], None, {"cuts": [3.75, 6.5]}),
]

# One film priced segment by segment: (segment, how it is made, the item's fields that must be so). The media: alpha
# has its film and hero, beta neither (its film is the basket's row), the hub its film and runs of its own.
MEDIA = {"alpha": {"film": {"url": "/files/a"}, "hero": {"url": "/files/h"}, "extras": {}},
         "beta": {"film": None, "hero": None, "extras": {}},
         "hub": {"film": {"url": "/files/b"}, "hero": None, "extras": {}}}
PRICED = [
    ({"cut": "title"}, "free", {}),
    ({"cut": "walk-through", "shows": {"place": "alpha"}, "seconds": 3.5}, "reuse", {}),
    ({"cut": "walk-through", "shows": {"place": "alpha"}}, "new",  # no runs of its own: the median
     {"frames": 168, "kind": "film", "euros": round(168 * render.MEASURED["film"]["euros"], 2)}),
    ({"cut": "walk-through", "shows": {"place": "beta"}}, "basket",
     {"node": "demo-film@beta", "frames": render.FILM_FRAMES}),
    ({"cut": "hero-still", "shows": {"place": "alpha"}}, "reuse", {}),
    ({"cut": "exploded", "shows": {"place": "alpha"}}, "new",  # an exploded view was never rendered on a card
     {"frames": 144, "euros": None}),
    ({"cut": "step-card", "shows": {"place": "alpha", "step": "plan"}}, "free", {}),
    ({"cut": "walk-through", "shows": {"place": "hub"}}, "new",  # the hub's own runs
     {"euros": round(168 * render.FILM_FRAME_EUROS["hub"], 2)}),
    ({"cut": "hero-still", "shows": {"place": "alpha"}, "camera": "wide"}, "new",
     {"kind": "look", "euros": round(render.MEASURED["look"]["euros"], 2)}),
    ({"cut": "screen-take", "shows": {"page": "/"}}, "free", {}),
    ({"cut": "setting-animation", "shows": {"world": "world1"}}, "free", {}),
    ({"cut": "scale-zoom", "shows": {"place": "hub"}, "seconds": 10,  # its place and room legs: film frames
      "legs": [{"layer": "setting", "seconds": 3}, {"layer": "world", "seconds": 2}, {"layer": "place", "seconds": 2},
               {"layer": "room", "seconds": 3}]}, "new",
     {"frames": 120, "euros": round(120 * render.FILM_FRAME_EUROS["hub"], 2)}),
    ({"cut": "scale-zoom", "shows": {"place": "hub"}, "seconds": 5,
      "legs": [{"layer": "setting", "seconds": 3}, {"layer": "world", "seconds": 2}]}, "free", {}),
    ({"cut": "body-peel", "shows": {"place": "square"}}, "new", {"euros": None}),  # no row draws a peel yet
]

SETTING = {"bodies": [{"body": "sun", "kelvin": 5772}, {"body": "kepler", "reference": "kepler", "radius_km": 2000.0},
                      {"body": "tess", "reference": "tess", "radius_km": 1000.0}]}
# Its plan: the body without the top scene first, so the journey's order (the top scene's body first) is the film's.
PLAN = {"maps": [{"on": "kepler", "sites": [{"place": "camp", "name": "Camp"}]},
                 {"on": "tess", "distances": [{"from": "pier", "to": "port", "metres": 80.0}],
                  "sites": [{"place": "port", "name": "Port"}, {"place": "pier", "name": "Pier",
                            "sky": {"worlds": [{"world": "kepler", "across": 2 * math.degrees(math.atan(0.02))}]}}]}]}
WITHIN = {"dock": "port", "bar": "port", "bunk": "deck", "hold": "port", "deck": "port", "tent": "camp"}
# each scene record's own inside: the bar is open to the sky though the port holds it
INSIDE = {"port": False, "pier": False, "camp": False, "dock": True, "bar": False, "hold": True, "deck": True,
          "bunk": True, "tent": True}
WORLD7 = {"port", "pier", "camp", "dock", "bar", "hold", "deck", "bunk", "tent"}
SHOWN = [("base", "Base", "moon"), ("hub", "Hub", "moon"), ("square", "Square", "earth"), ("street", "Street", "earth"),
         ("camp", "Camp", "mars")]

# A click is refused when its words would spend.
SPENDING = [("Draw fresh", True), ("Pick", True), ("Buy", True), ("Keep", True), ("Make plan", True), ("Unlock", True),
            ("EUR 0.15", True), ("hub, picked", False), ("Places", False)]

# The bed: the sound stage's output for the first place the film shows, else the first place with one, else silence.
BEDS = {"base": [{"sha": "b1"}], "hub": [], "lab": [{"sha": "l1"}]}
BED_FILM = {"segments": [{"shows": {"world": "w"}}, {"shows": {"place": "hub"}}, {"shows": {"place": "base"}}]}
BEDDED = [("first shown with one", BED_FILM, BEDS, ("base", "blobs/b1")),
          ("none shown", {"segments": []}, BEDS, ("base", "blobs/b1")),
          ("none made", BED_FILM, {}, (None, None))]


def fault_found(wanted, found):
    """A wanted fault is in the list: a string word for word, a pattern somewhere in one."""
    if isinstance(wanted, str):
        return wanted in found
    return any(wanted.search(fault) for fault in found)


def test_a_film_is_timed_checked_and_priced_from_its_script(world, tmp_path, monkeypatch):
    """A film's script judged on its clock, its words and its prices, the cockpit's pages that save, lock and buy it,
    and the default films and preview built from an environment's own design."""
    import numpy
    from score import review
    from score.dashboard import state as dashboard_state
    from score.dashboard.checkout import flow
    from score.dashboard.films import default
    from score.dashboard.films.preview import make, scenes
    from score.dashboard.pages.models import Checkout
    from score.dashboard.state import local, screens
    from score.dashboard.tests.fixture import FakeBackend
    from score.review import setting
    from score.stages import demo_film, people_rows, sound
    repo = settings.SCORE_REPO
    home = settings.SCORE_HOME

    # The clock: a cross-fade overlaps, a push does not, a cut does not; the preview joins and fades on it.
    for name, segments, defaults, wanted in CLOCK:
        film = a_script(segments, **({"defaults": defaults} if defaults else {}))
        if "timeline" in wanted:
            assert script.timeline(film) == wanted["timeline"], name
        if "total" in wanted:
            assert script.total_seconds(film) == wanted["total"], name
        if "cuts" in wanted:
            assert make.cut_moments(film) == wanted["cuts"], name
        if "joined" in wanted:
            joined, made, total = make.joined_filter(film, [script.seconds_of(film, shot) for shot in segments])
            assert (made, total) == (wanted["made"], wanted["total"]), name
            assert all(part in joined for part in wanted["joined"]), (name, joined)
    rises = numpy.zeros(240)
    rises[[10, 58, 106, 154, 202]] = 5.0  # a beat every 2 s at 24 a second, the first 10 frames in
    for beats, offset in ((rises, round(10 / 24, 3)), (numpy.full(240, 0.1), 0.0)):
        assert make.beat_offset(beats, [4.0, 6.0], 24) == offset

    # The starters (environment 1's own, read from the repository) and the default films they set the pattern for.
    world1, world1_origin = script.read(repo, "/nonexistent", "k9")
    env1, env1_origin = script.read(repo, "/nonexistent", "env1_demo")
    assert (world1_origin, env1_origin, env1["default"]) == ("starter", "starter", True)
    facts = default.facts_of("world7", "Environment 7", SETTING, PLAN, WITHIN, {"port": "The Port"},
                             {"tess": "tess_dust"}, {}, {}, INSIDE)
    film7 = default.built("world7-film", facts)
    part = default.sim_bodies(SHOWN, {"street": True, "hub": False, "camp": True, "square": False, "nowhere": True})
    # the base walked with no people: its place itself peeled (owner, 2026-11-05)
    tail = default.sim_bodies(SHOWN, {"hub": False, "square": False}, {"base", "hub", "square"})[3:]

    # The words: every fault said, and a sound script (each starter, each built default) says none.
    words = a_script([{"cut": "spin"}, {"cut": "isolate", "shows": {"place": "alpha"}},
                      {"cut": "step-card", "shows": {"place": "alpha", "step": "paint"}},
                      {"cut": "orbit", "shows": {"place": "gamma"}, "seconds": 99, "transition": "wipe"}])
    take = {"cut": "screen-take", "shows": {"page": "/concept/hub/"}, "take": [
        {"at": 0.5, "do": "click", "on": "#concept-draw", "words": "Redraw with notes EUR 0.30"},
        {"at": 1.0, "do": "type", "on": "#concept-note", "text": "taller\n"},
        {"at": 1.5, "do": "spin", "on": "#x"},
        {"at": 2.0, "do": "move"}]}
    zoom_up = {"cut": "scale-zoom", "shows": {"place": "alpha"}, "seconds": 9.0,
               "legs": [{"layer": "world", "seconds": 4}, {"layer": "setting", "seconds": 4},
                        {"layer": "attic", "seconds": 1}]}
    faults = [  # (row, script, the scenes it may name, the faults wanted, whether they are all of them)
        ("words", words, {"alpha", "beta"},
         ["segment 1: no cut type 'spin'", "segment 2 (Isolate a part) names no part",
          "segment 3: no framework step 'paint'", "segment 4: no transition 'wipe'", re.compile("99"),
          "segment 4: no scene 'gamma'"], False),
        ("bad name", a_script([{"cut": "title"}], film="Bad Name"), None,
         ["the film's name 'Bad Name' is not lower-case letters, digits and dashes"], True),
        ("other format", {"format": "other"}, None, [f"not a {script.FORMAT} version {script.VERSION}"], True),
        ("screen take", a_script([take, zoom_up, {"cut": "title", "pip": {"corner": "middle"}}]), None,
         [re.compile("segment 1 step 1: refused"), "segment 1 step 2: typing never presses Enter (it could send a form)",
          "segment 1 step 3: no step 'spin'", "segment 1 step 4: move names the element it is `on`",
          re.compile("^segment 2: a scale zoom goes down through the layers"), "segment 2: no layer 'attic'",
          re.compile("^segment 3: a picture-in-picture")], False),
        ("sitter", a_script([dict(part[1], close="sitter")]), None,
         ["segment 1: a layer peel follows only a walker, not 'sitter'"], True),
        ("world1 starter", world1, design_scenes(repo), [], True),
        # the docking airlock: a scene added in the app on his kept Hangar plan, which the test's store does not hold
        ("env1 starter", env1, design_scenes(repo) | {"docking_airlock"}, [], True),
        ("sim bodies", a_script(part), {"square", "street", "hub", "camp"}, [], True),
        ("place peel", a_script(tail), {"base"}, [], True),
        ("default film", film7, WORLD7, [], True),
    ]
    for row, film, known, wanted, whole in faults:
        found = script.faults(film, known)
        if whole:
            assert found == wanted, row
        else:
            assert all(fault_found(fault, found) for fault in wanted), (row, found)
    for word, spends in SPENDING:
        assert bool(takes.SPEND.search(word)) is spends, word
    for film in (world1, env1, film7):
        assert script.total_seconds(film) <= film["target_seconds"], film["film"]

    # The film file: one name check builds every path, refusing a path, a dot name or a trailing newline.
    assert script.saved_path(tmp_path, "tour-1") == tmp_path / script.SAVED_FOLDER / "tour-1.json"
    for name in ("../accepts/x", "a/b", "..", "tour\n", ""):
        for build in (script.saved_path, script.locked_path, script.seed_path):
            with pytest.raises(ValueError):
                build(tmp_path, name)

    # The prices: every segment's item, and the film's totals of them; the film shot the demo-film rows' own.
    assert script.FILM_SHOT_SECONDS == demo_film.SECONDS - script.TRANSITION_SECONDS
    assert render.FILM_FRAMES == round(demo_film.SECONDS * 24)
    items = render.items(a_script([segment for segment, _, _ in PRICED]), MEDIA)
    for number, (item, (segment, how, fields)) in enumerate(zip(items, PRICED), 1):
        assert item["how"] == how and {key: item[key] for key in fields} == fields, (number, segment["cut"], item)
    totals = render.totals(items)
    assert totals["unmeasured"] == ["body-peel", "exploded"] and totals["unmeasured_frames"] == 144 + items[13]["frames"]
    assert totals["basket"] == ["demo-film@beta"] and totals["reused"] == 2 and totals["free"] == 5
    assert totals["euros"] == round(sum(items[number]["euros"] for number in (2, 3, 7, 8, 11)), 2)

    # Environment 1's world1 starter gives the places the time: walks over half of it, each place once and long
    # enough, the chain of steps once, on one place.
    lengths = script.timeline(world1)
    walks = [number for number, segment in enumerate(world1["segments"]) if segment["cut"] == "walk-through"]
    assert sum(lengths[number][1] for number in walks) > script.total_seconds(world1) / 2
    places = [world1["segments"][number]["shows"]["place"] for number in walks
              if not world1["segments"][number]["shows"].get("film")]
    assert len(places) == len(set(places))
    assert all(script.seconds_of(world1, world1["segments"][number]) >= 7 for number in walks)
    cards = [segment for segment in world1["segments"] if segment["cut"] == "step-card"]
    assert [card["shows"]["step"] for card in cards] == list(script.STEPS)  # the chain once
    assert len({card["shows"]["place"] for card in cards}) == 1
    # env1_demo is environment 1's default film, complete (owner, 2026-10-21): the physics animation long enough to
    # see an orbit, every zoom followed by a shot of its scene (owner, 2026-10-24: "scale zoom after scale zoom and no
    # walkthroughs in between"): a walk, or a still where its plan names its eye (the Square's); every scene it walks
    # through peeled one way (owner, 2026-11-05: "every scene needs the peel"; asked whether that meant adding people
    # or peeling the place itself: "2"): a layer peel where its design has people, else a place peel.
    animation = next(segment for segment in env1["segments"] if segment["cut"] == "setting-animation")
    assert animation["seconds"] * animation["days_per_second"] >= 300  # Earth goes most of the way round the Sun
    cuts = [segment["cut"] for segment in env1["segments"]]
    assert all(cuts[number + 1] in ("walk-through", "hero-still") for number, cut in enumerate(cuts) if cut == "scale-zoom")
    shot = {segment["shows"]["place"] for segment in env1["segments"] if segment["cut"] in ("walk-through", "hero-still")}
    assert set(next(segment for segment in env1["segments"] if segment["cut"] == "scale-zoom")["legs"][-1]["rooms"]) < shot
    peels = {}
    for segment in env1["segments"]:
        if segment["cut"] in ("body-peel", "place-peel"):
            peels.setdefault(segment["shows"]["place"], set()).add(segment["cut"])
    assert all(len(peels.get(place, ())) == 1 for place in shot) and "place-peel" in peels["hub"]
    assert peels["square"] == {"place-peel"}  # its cast a crowd alone: no sim body to peel (data/people/rows.json)

    # An environment's default film: the owner's script for environment 1 as every environment's default
    # (2026-10-21): the app's steps, then one shot from the setting down into the top scene's rooms, then on to every
    # other top scene, body by body, every zoom followed by a walk through its scene (not a shell) and every scene it
    # holds, parent before child (2026-10-24), here an environment that shares no name with his.
    assert facts["top"] == "port" and [room for room, _ in facts["rooms"]] == ["dock", "bar", "hold"]
    assert [stop["place"] for stop in facts["stops"]] == ["port", "pier", "camp"]
    # no scene has people: each walked one's place itself peeled last, after its card (owner, 2026-11-05)
    peeled7 = film7["segments"][-9:]
    assert [segment["shows"].get("place") for segment in peeled7] == [
        None, "dock", "bar", "hold", "deck", "bunk", "pier", "camp", "tent"] and peeled7[0]["text"] == "Physics bodies"
    walked = film7["segments"][:-9]
    assert [segment["cut"] for segment in walked] == [
        "title", "screen-take", "setting-animation", "screen-take", "screen-take", "screen-take", "scale-zoom",
        *["walk-through"] * 5, "scale-zoom", "walk-through", "scale-zoom", "walk-through", "walk-through"]
    assert [segment["shows"]["place"] for segment in walked[7:]] == [
        "dock", "bar", "hold", "deck", "bunk", "pier", "pier", "camp", "camp", "tent"]
    assert [segment["line"] for segment in walked[-4::2]] == ["Outside", "Outside"]
    assert walked[-1]["line"] == "Inside"
    assert [segment["line"] for segment in walked[7:9]] == ["Inside", "Outside"]  # dock, bar: their records
    assert walked[6]["captions"][-1]["text"] == "Inside: Dock, Hold; Outside: Bar"
    assert film7["target_seconds"] < script.total_seconds(film7) + 5 and film7["segments"][2]["seconds"] == 12.0
    pages = [segment["shows"].get("page") for segment in film7["segments"] if segment["cut"] == "screen-take"]
    assert pages == ["/environments/world7/", "/environments/world7/", "/concept/dock/", "/concept/port/"]
    zoom = film7["segments"][6]
    assert zoom["legs"][-1]["rooms"] == ["dock", "bar", "hold"] and zoom["legs"][3]["into"] == "dock"
    assert zoom["surfaces"] == {"tess": "tess_dust", "ground": "tess_dust"} and "kepler" in zoom["waiting"]
    pier, camp = walked[-5], walked[-3]
    assert [leg["layer"] for leg in pier["legs"]] == ["site", "place"] and pier["legs"][0]["from_place"] == "port"
    assert "Pier, 80 m from The Port" in json.dumps(pier) and pier["pip"]["concept"] == "pier"
    assert [leg["layer"] for leg in camp["legs"]] == ["world", "setting", "world", "site", "place", "room"]
    assert camp["legs"][0]["place"] == "pier" and camp["legs"][1]["from_body"] == "tess"
    assert "Kepler, 100,000 km away" in json.dumps(camp) and camp["legs"][-1]["rooms"] == ["tent"]
    assert camp["pip"]["to"] - camp["pip"]["from"] >= 3 and all(3 <= shown["seconds"] <= 20 for shown in (pier, camp))
    assert ".sp-card:nth-child(3)" in json.dumps(film7["segments"][1]) and "world1" not in json.dumps(film7)
    assert default.facts_of("world7", "E", {"bodies": []}, {"maps": []}, WITHIN, {}, {}, {}) is None
    design = default.design_of(facts)
    assert script.design_faults(film7, design) == []
    # a film that froze what has moved since: a record now outside said inside, a top scene with no shot of its own,
    # a site's metres from an older plan, a scene with a designed eye walked
    frozen = json.loads(json.dumps(film7))
    frozen["segments"][8]["line"] = "Inside"
    frozen["segments"][6]["captions"][-1]["text"] = "Inside: Dock, Bar, Hold"
    frozen["segments"] = [segment for segment in frozen["segments"]
                          if (segment["shows"].get("place"), segment["cut"]) != ("camp", "walk-through")]
    next(segment for segment in frozen["segments"] if segment["cut"] == "scale-zoom"
         and segment["shows"]["place"] == "pier")["captions"][0]["text"] = "Pier, 56.7 m from The Port"
    eyed = {**design, "eyes": {"pier": {"from": "deck", "metres": 4.0}}}
    assert script.design_faults(frozen, eyed) == [
        "segment 7: Bar is said inside, its scene record says outside",
        "segment 9: Bar is said Inside, its scene record says outside",
        'segment 13: "Pier, 56.7 m from The Port" says 56.7 m, the design 80 m',
        "segment 14: Pier is designed seen from its deck eye at 4 m, not a Walk-through walked",
        "Camp (a top scene) has no shot of its finished stage"]
    # the frozen script said again from the design now (default.refreshed): its design-derived words and shots
    # follow the design, the top scene with no shot of its own walked after its zoom, everything else as it was
    redone = default.refreshed(frozen, {**facts, "eyes": eyed["eyes"]})
    assert script.design_faults(redone, eyed) == []
    assert len(redone["segments"]) == len(frozen["segments"]) + 1 and redone["segments"][8]["line"] == "Outside"
    assert redone["segments"][6]["captions"][-1]["text"] == "Inside: Dock, Hold; Outside: Bar"
    assert [(again["cut"], again["seconds"]) for again in redone["segments"][12:14]] == [
        ("scale-zoom", frozen["segments"][12]["seconds"]), ("hero-still", 7.0)]
    assert redone["segments"][12]["captions"][0]["text"] == "Pier, 80 m from The Port"
    camp_cuts = [again["cut"] for again in redone["segments"] if again["shows"].get("place") == "camp"]
    assert camp_cuts[:2] == ["scale-zoom", "walk-through"] and redone["target_seconds"] >= script.total_seconds(redone)
    kept = [again for again in redone["segments"]
            if not (again["shows"].get("place"), again["cut"]) == ("camp", "walk-through")]
    assert [again for number, again in enumerate(kept) if number not in (6, 8, 12, 13)] == [
        again for number, again in enumerate(frozen["segments"]) if number not in (6, 8, 12, 13)]
    # a shell with a plan of its own is walked, and a plan naming its eye is filmed as a still from there
    planned = default.facts_of("world7", "Environment 7", SETTING, PLAN, WITHIN, {"port": "The Port"},
                               {"tess": "tess_dust"}, {}, {"port": {}, "pier": {
                                   "height": "deck eye 4 m; mast 9 m", "levels": [{"name": "deck"}]}}, INSIDE)
    shots = default.built("world7-film", planned)["segments"]
    assert [(again["cut"], again["line"]) for again in shots if again["shows"].get("place") in ("port", "pier")
            and again["cut"] not in ("scale-zoom", "place-peel")] == [("walk-through", "Outside"),
                                                                      ("hero-still", "Seen from the deck")]
    assert script.design_faults({"segments": shots}, default.design_of(planned)) == []
    assert default.designed_eye({"height": "balcony eye 10.6 m", "levels": [{"name": "plaza"}]}) is None

    # The sim bodies part (owner, 2026-10-27): every scene the film shows whose design has people, peeled the same
    # way, a close-up after it where one walks, those on the body the clips were recorded on first, every other one
    # carrying the low-gravity note; a walked scene with no people its place itself peeled; the hosted side's walking
    # rule the people rows' own.
    assert [segment["cut"] for segment in part] == ["text", *["body-peel"] * 6]
    assert [(segment["shows"]["place"], segment.get("close")) for segment in part[1:]] == [
        ("square", None), ("street", None), ("street", "walker"), ("hub", None), ("camp", None), ("camp", "walker")]
    notes = [segment["captions"][0]["text"] == default.LOW_GRAVITY_NOTE for segment in part[1:]]
    assert notes == [False, False, False, True, True, True] and part[4]["captions"][0]["line"] == "Moon · Hub"
    assert all(segment["seconds"] == default.PEEL_SECONDS for segment in part[1:])
    assert default.sim_bodies(SHOWN, {}) == []
    assert [(segment["cut"], segment.get("text"), segment["shows"].get("place")) for segment in tail] == [
        ("text", "Physics bodies", None), ("place-peel", None, "base")]
    assert tail[1]["captions"][0] == {"from": 0.3, "to": 4.7, "line": "Moon · Base",
                                      "text": "Base: finished, bare models, physics bodies"} and tail[1]["waiting"]
    assert [segment["cut"] for segment in default.sim_bodies(SHOWN, {}, {"hub"})] == ["text", "place-peel"]
    crowd = default.sim_bodies(SHOWN, {"square": None, "street": False})  # a crowd alone: its place peeled, walked or not
    assert [(segment["cut"], segment["shows"].get("place")) for segment in crowd] == [
        ("text", None), ("body-peel", "street"), ("text", None), ("place-peel", "square")]
    rows = json.loads((repo / "data/people/rows.json").read_text())
    assert [default.row_walks(row) for entry in rows["places"].values() for row in entry["rows"].values()] == [
        people_rows.doing_of(row) == "walking" for entry in rows["places"].values() for row in entry["rows"].values()]
    people = default.people_of({"places": {"tent": {"rows": {"a": {"where": "walking"}}}, "bar": {"rows": {"b": {}}},
                                           "deck": {"rows": {}}, "plaza": {"rows": {"c": {"crowd": "far"}}}}})
    assert people == {"bar": False, "plaza": None, "tent": True}
    people.pop("plaza")
    peopled = default.built("world7-film", default.facts_of("world7", "Environment 7", SETTING, PLAN, WITHIN,
                                                            {"port": "The Port"}, {"tess": "tess_dust"}, people))
    body_peels = [segment for segment in peopled["segments"] if segment["cut"] != "place-peel"][:-1]  # less its card
    assert [(segment["shows"].get("place"), segment.get("close")) for segment in body_peels[-4:]] == [
        (None, None), ("bar", None), ("tent", None), ("tent", "walker")]

    # The setting drawn from its own physics to the picture's scale, a zoom arriving where its site is lit (#51: the
    # Square's site at its scene time is on Earth's night side; the zoom lands at the first lit hour) unless the
    # script names a time, and a body in the face its row made, else a plain colour of its own said waiting.
    bodies = setting.now()["bodies"]
    scale = scenes.scales(bodies)
    placed = scenes.placed(bodies, 0.0, scale)
    assert placed["sun"] == [0.0, 0.0, 0.0]
    mars_far = max(sum(value * value for value in scenes.placed(bodies, day, scale)["mars"]) ** 0.5
                   for day in range(0, 700, 10))
    mars = next(body for body in bodies if body["body"] == "mars")
    assert abs(mars_far - scenes.UNITS * (1 + mars["eccentricity"])) < 0.5  # its orbit's size the scene's 100 units
    moon = [a - b for a, b in zip(placed["moon"], placed["earth"])]
    earth = next(body for body in bodies if body["body"] == "earth")
    ring = (scenes.disc_size(earth) + 22.0) * scenes.UNITS / scenes.REACH
    assert 0.9 * ring < sum(value * value for value in moon) ** 0.5 < 1.1 * ring  # enlarged as the picture draws it
    night = "2099-10-01T14:00:00Z"
    site = {"place": "square", "name": "Square", "latitude": 22.28, "longitude": 114.16, "time": night}
    sky_state = {"environment_concept": {"concept": {"setting": setting.now()}}, "body_faces": {"earth": {"hex": "#336699"}},
                 "environment_plan": {"plan": {"time": night, "maps": [{"on": "earth", "name": "Earth", "sites": [site]}]}}}
    dark = scenes.day_of(night)
    assert scenes.sky_at(sky_state, "square", dark)["sun"]["altitude"] < 0
    day, sky = scenes.arrival(sky_state, "square")
    assert sky["sun"]["altitude"] >= scenes.LIT_DEGREES and 0 < day - dark < 1
    assert scenes.arrival(sky_state, "square", night) == (dark, scenes.sky_at(sky_state, "square", dark))
    assert scenes.face_colour(sky_state, "earth") == [0.2, 0.4, 0.6]
    assert scenes.face_colour(sky_state, "moon") == scenes.face_colour({}, "moon") != scenes.face_colour({}, "mars")
    zoom_in = {"cut": "scale-zoom", "shows": {"place": "square"}, "seconds": 8,
               "legs": [{"layer": "setting", "seconds": 4}, {"layer": "world", "seconds": 4, "tag": "Plan"}]}
    setting_leg, world_leg = scenes.scene_for(sky_state, zoom_in, 2)["legs"]
    assert setting_leg["tag"] == f"Moon, Mars: {scenes.WAITING}" and "waits" not in setting_leg
    assert world_leg["tag"] == "Plan" and world_leg["color"] == [0.2, 0.4, 0.6]

    # The preview's bed: the sound stage's output (the state's sound_beds), never a library name; none made, none,
    # its record saying it waits; the state knows a designed bed by the word the sound stage writes on it.
    with monkeypatch.context() as patched:
        patched.setattr(dashboard_state, "source", lambda: types.SimpleNamespace(blob_path=lambda sha: f"blobs/{sha}"))
        for row, film, beds, bed in BEDDED:
            assert make.bed_sound(film, {"sound_beds": beds}) == bed, row
        patched.setattr(sound, "beds", types.SimpleNamespace(
            of_place=lambda place, inputs: {"facts": {}, "sounds": ["hum"]}))
        for name in ("object_uses", "moving_uses", "bank_uses", "voice_uses"):
            patched.setattr(sound, name, lambda *_: [])
        patched.setattr(sound, "read_json", lambda path: {})
        (designed,) = sound.uses_of("alpha", {"surfaces": None})
        assert (designed["sound"], designed["role"], designed["from"]) == ("hum", "room", local.DESIGNED_BED)
    assert make.record_of({"film": "f", "segments": []}, 1.0, None, 0.0)["bed"] == make.WAITING_BED
    # a recorder failure names the node the path found, with the version the sync line lacked
    (tmp_path / "node").write_text("#!/bin/sh\necho v18.19.1\n")
    (tmp_path / "node").chmod(0o755)
    assert make.node_used(str(tmp_path)) == f"node {tmp_path / 'node'} v18.19.1"
    assert make.node_used(str(tmp_path / "none")) == "no node on the PATH"

    # The cockpit's world: the pages that open, save, price, buy, lock and play a film, in the owner's order.
    monkeypatch.setattr(settings, "SCORE_REPO", tmp_path / "repo")
    player = api()
    owner, other = signed_in(), signed_in("other")
    # the Film step opens on the environment's own film: nothing saved, its world's
    assert owner.get("/film/")["Location"] == "/film/world1-film/"
    # Buy waits for the Film step as it waits for a scene's design: an item holding a film row is not bought, and the
    # checkout refuses one, while no film script is locked
    shutil.rmtree(home / script.LOCKED_FOLDER, ignore_errors=True)  # the home is the session's
    price = {"likely_euros": 1.0, "high_euros": 2.0, "runs": 1}
    buyable = [{"id": f"alpha-{layer}", "place": "alpha", "layers": [layer], "places": ["alpha"],
                "nodes": {node: price}, "missing": []}
               for layer, node in (("stage", "assembly@alpha"), ("films", "demo-film@alpha"))]
    assert screens.film_waits() == "film script not locked"
    assert [item["id"] for item in screens.now_items(buyable, ["alpha"])] == ["alpha-stage"]
    assert any("film script not locked" in refusal for refusal in flow.item_refusals(buyable))
    html = owner.get("/buy/").content.decode()
    assert "film script not locked" in html and 'href="/film/"' in html
    # the editor: the saved script, its places' media, every cut, its items priced; node ids only inside the ids
    # fold (owner rule #42, wording)
    script.save(home, a_script([{"cut": "title", "text": "A trailer"},
                                {"cut": "walk-through", "shows": {"place": "alpha"}, "text": "Alpha", "seconds": 3.5},
                                {"cut": "layer-split", "shows": {"place": "alpha"}}]))
    listing = owner.get("/film/all/").content.decode()
    assert "/film/trailer/" in listing and "A trailer" in listing
    html = owner.get("/film/trailer/").content.decode()
    editor = editor_of(html)
    assert editor["origin"] == "saved" and editor["places"]["alpha"]["film"]["url"].startswith("/files/")
    assert set(editor["cuts"]) >= {"walk-through", "orbit", "hero-still", "exploded", "isolate", "layer-focus",
                                   "layer-split", "step-card", "before-after", "title", "text"}
    assert [item["how"] for item in editor["answer"]["items"]] == ["free", "reuse", "new"]
    assert editor["answer"]["totals"]["unmeasured"] == ["layer-split"]
    assert re.search(r"\b[a-z][a-z-]+@(alpha|beta)\b", outside_ids_fold(html)) is None
    assert owner.get("/film/nothing/").status_code == 404
    # saving writes the cockpit's home only, refuses a script with faults, and only the owner saves
    changed = a_script([{"cut": "orbit", "shows": {"place": "alpha"}}, {"cut": "text", "text": "the end"}])
    answer = owner.post("/film/trailer/save/", json.dumps(changed), content_type="application/json")
    assert answer.status_code == 200 and answer.json()["saved"] and answer.json()["totals"]["frames"] == 144
    assert json.loads(script.saved_path(home, "trailer").read_text())["segments"][-1]["text"] == "the end"
    assert not (tmp_path / "repo").exists()
    wrong = a_script([{"cut": "orbit", "shows": {"place": "nowhere"}}])
    refused = owner.post("/film/trailer/save/", json.dumps(wrong), content_type="application/json")
    assert refused.status_code == 400 and "segment 1: no scene 'nowhere'" in refused.json()["faults"]
    assert other.post("/film/trailer/save/", json.dumps(changed), content_type="application/json").status_code == 403
    assert other.post("/film/trailer/compile/", json.dumps(changed), content_type="application/json").status_code == 200
    # the basket takes only a place film row, and launches nothing
    review.reject(world.store, "demo-film@beta", world.outputs["demo-film@beta"], by="joey", reason="test")
    world.source.refresh()
    script.save(home, a_script([{"cut": "walk-through", "shows": {"place": "alpha"}},
                                {"cut": "walk-through", "shows": {"place": "beta"}},
                                {"cut": "exploded", "shows": {"place": "alpha"}}]))
    assert other.post("/film/trailer/basket/").status_code == 403
    owner.post("/film/trailer/basket/")
    assert [(item.place, item.stage) for item in BasketItem.objects.all()] == [("beta", "demo-film")]
    assert not [call for call in FakeBackend.calls if call[0] == "launch"]
    # the Lock: the script as the editor shows it saved and locked in the cockpit's home (what the environment-film
    # row reads, and what Buy waits for), nothing saved over it while locked, Unlock until a batch buys a film row on it
    locked = a_script([{"cut": "walk-through", "shows": {"place": "alpha"}}])

    def locking(client, body):
        return client.post("/film/trailer/lock/", json.dumps(body), content_type="application/json")

    assert locking(other, locked).status_code == 403
    assert locking(owner, {**locked, "film": "other"}).status_code == 409
    answer = locking(owner, locked)
    assert answer.status_code == 200 and answer.json() == {"said": "locked trailer", "locked": True}
    assert script.locked(home, "trailer") == locked == script.read(tmp_path / "repo", home, "trailer")[0]
    assert script.locked_films(home, "world1") == ["trailer"]
    assert screens.film_waits() == ""
    assert [item["id"] for item in screens.now_items(buyable, ["alpha"])] == ["alpha-stage", "alpha-films"]
    assert not any("film" in refusal for refusal in flow.item_refusals(buyable))
    refused = owner.post("/film/trailer/save/", json.dumps(locked), content_type="application/json")
    assert refused.status_code == 409 and refused.json()["faults"] == ["it is locked: unlock it to change it"]
    assert editor_of(owner.get("/film/trailer/").text)["locked"] is True
    assert locking(owner, {}).json() == {"said": "unlocked trailer", "locked": False}
    assert script.locked(home, "trailer") is None
    locking(owner, locked)
    Checkout.objects.create(key="k" * 32, by="joey", state="launched",
                            items=[{"id": "beta-films", "nodes": {"demo-film@beta": {}}}])
    stands = locking(owner, {})
    assert stands.status_code == 409 and "bought its film rows on this lock" in stands.json()["faults"][0]
    assert script.locked(home, "trailer") == locked
    # the film page plays its rendered preview and seeks in it
    video, record = script.preview_files(home, False, "trailer")
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(bytes(range(256)) * 40)
    record.write_text(json.dumps({"made_at": "2026-10-21T12:00:00+00:00", "seconds": 5.5, "script": locked,
                                  "segments": [{"index": 1, "start": 0.0}, {"index": 2, "start": 3.5}]}))
    editor = editor_of(player.get("/film/trailer/").text)
    assert editor["preview"]["url"].startswith("/film-preview/trailer.mp4") and "screen-take" in editor["recorded"]
    played = player.get("/film-preview/trailer.mp4", headers={"Range": "bytes=100-199"})
    assert played.status_code == 206 and played.content == (bytes(range(256)) * 40)[100:200]
    assert player.get("/film-preview/other.mp4").status_code == 404
    # a new film starts with its title card; a film named "new" is refused
    assert owner.post("/film/new/", {"film": "teaser", "title": "A teaser"}).status_code == 302
    teaser, origin = script.read(tmp_path / "repo", home, "teaser")
    assert origin == "saved" and teaser["segments"][0]["cut"] == "title" and teaser["title"] == "A teaser"
    owner.post("/film/new/", {"film": "new", "title": "x"})
    assert script.read(tmp_path / "repo", home, "new")[0] is None
    # the Film step opens on a saved script marked default; then on a starter marked default even where a saved
    # copy lost the mark (the hosted home of 2026-10-21)
    script.save(home, {**a_script([]), "film": "mine", "default": True})
    assert other.get("/film/")["Location"] == "/film/mine/"
    (tmp_path / "repo/data/films").mkdir(parents=True)
    (tmp_path / "repo/data/films/zz_demo.json").write_text(json.dumps({**a_script([]), "film": "zz_demo",
                                                                        "default": True}))
    script.save(home, {**a_script([]), "film": "zz_demo"})
    assert signed_in("third").get("/film/")["Location"] == "/film/zz_demo/"
