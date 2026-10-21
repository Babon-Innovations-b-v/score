"""The concept review's draws and picks (score/review/concepts.py), with a stand-in for the model (no call is made,
nothing is spent): a draw runs only inside the owner's yes for it and keeps its picture and record; a redraw sends
the base boxed and clean with each mark's note; a pick takes only a draw of the place; the click's yes is written with
its price and purpose, and refused when the price shown is not today's; the price is the measured unit at the
standard tier."""
import io
import json
import re
import subprocess

import pytest
from PIL import Image

from score import review
from score.adapters import compute
from score.review import concepts, web
from score.store import Store, runtime_store


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(compute, "require_books", lambda what: None)  # the books are the ledger's own test's
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)
    monkeypatch.setattr(concepts, "offsite_store", lambda: runtime_store.FolderStore(tmp_path / "bucket"))
    monkeypatch.setattr(concepts, "handed_over", lambda store, place: "library: stand-in")
    return Store.in_folder(tmp_path / "store")


def a_picture(colour=(40, 90, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), colour).save(buffer, "PNG")
    return buffer.getvalue()


def stand_in(asked):
    """A model that keeps what it was asked and answers a picture."""
    def answer(wording, pictures):
        asked.append((wording, [picture.size for picture in pictures]))
        return a_picture((len(asked) * 40, 80, 120))
    return answer


def prompt_stand_in(asked, answer="The corrected prompt."):
    """A prompt model that keeps what it was asked and answers `answer`."""
    def corrected(question, pictures):
        asked.append((question, [picture.size for picture in pictures]))
        return answer
    return corrected


def ready_above(monkeypatch, box=(0, 0, 32, 20)):
    """Stand-ins for the layer above's scene inventory reading, its made plan and the box of the row holding a place
    (reading.py's and the plan's own tests own those)."""
    from score.review import reading
    monkeypatch.setattr(reading, "reading_of", lambda store, place: {"stand-in": place})
    monkeypatch.setattr(concepts, "plan_made", lambda store, place: True)
    monkeypatch.setattr(concepts, "holding_row", lambda store, place: "holder")
    monkeypatch.setattr(concepts, "holder_words", lambda store, place: "the black angular spaceship")
    monkeypatch.setattr(concepts, "outlined", lambda store, place: True)
    monkeypatch.setattr(reading, "row_boxes", lambda store, place, row: [list(box)])


def said_yes(store, monkeypatch, place="campgrounds"):
    key = concepts.yes_key(place, review.now())
    review.spend(store, "override", key, 0.15, "joey", purpose="test")
    monkeypatch.setenv("SCORE_SPEND_TICKET", f"override {key}")
    return key


def test_a_draw_runs_only_inside_the_owners_yes(store, monkeypatch):
    with pytest.raises(compute.Refused):
        concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    assert concepts.draws(store, "campgrounds") == []


def test_a_first_draw_is_worded_from_the_places_data_and_kept(store, monkeypatch):
    key = said_yes(store, monkeypatch)
    asked = []
    record = concepts.draw(store, "campgrounds", {"note": "more dust"}, "joey", caller=stand_in(asked))
    assert record["yes"] == key and record["euros"] == 0.15 and record["base"] is None
    assert store.objects.exists(f"blobs/{record['sha']}")
    assert concepts.draws(store, "campgrounds") == [record] and concepts.placed(store) == ["campgrounds"]
    wording, sizes = asked[0]
    assert "campgrounds" in wording and "The creator's note: more dust" in wording
    assert sizes == [(1280, 720)]  # an outside place with no reference: its site's blockout only
    assert record["blockout"] and store.objects.exists(f"blobs/{record['blockout']}")


def test_a_redraw_sends_the_base_boxed_and_clean_with_each_marks_note(store, monkeypatch):
    said_yes(store, monkeypatch)
    first = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch)
    asked = []
    marks = [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "a red door"}]
    prompted = []
    second = concepts.draw(store, "campgrounds", {"marks": marks, "note": "warmer", "base": first["sha"]}, "joey",
                           caller=stand_in(asked), reviser=prompt_stand_in(prompted))
    question, seen = prompted[0]  # Gemini: the boxed and clean picture, the prompt it was drawn from, each note
    assert "Box 1 (middle left): a red door." in question and "Overall: warmer" in question
    assert first["wording"] in question and seen == [(64, 40), (64, 40)]
    wording, sizes = asked[0]  # the draw: the corrected prompt, the box's note, the boxed and the clean picture
    assert wording.startswith("The corrected prompt.") and "Box 1 (middle left): a red door." in wording
    assert sizes == [(64, 40), (64, 40)] and "Overall: warmer" in wording
    assert second["base"] == first["sha"] and second["marks"][0]["note"] == "a red door"
    assert [call["model"] for call in second["calls"]] == [concepts.PROMPT_MODEL, "gemini-3-pro-image"]
    assert second["corrected"] == "The corrected prompt." == concepts.own_wording(store, "campgrounds")
    assert concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    with pytest.raises(concepts.Refused, match="outside the picture"):
        concepts.draw(store, "campgrounds", {"marks": [{"x": 0.9, "y": 0, "w": 0.5, "h": 0.1}], "base": first["sha"]},
                      "joey", caller=stand_in([]), reviser=prompt_stand_in([]))
    with pytest.raises(concepts.Refused, match="no draw of"):
        concepts.draw(store, "hub", {"base": first["sha"]}, "joey", caller=stand_in([]), reviser=prompt_stand_in([]))


def test_a_pick_takes_only_a_draw_of_the_place_and_unlocks_again(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    with pytest.raises(concepts.Refused):
        concepts.pick(store, "campgrounds", "0" * 64, "joey")
    concepts.pick(store, "campgrounds", drawn["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == drawn["sha"]
    concepts.pick(store, "campgrounds", None, "joey")
    assert concepts.picked(store, "campgrounds") is None
    started = []
    monkeypatch.setattr(web, "reading_started", lambda store, place, by: started.append((place, by)) or "log")
    assert web.concept_pick(store, "campgrounds", drawn["sha"], "joey")["library"] == "library: stand-in"
    assert started == [("campgrounds", "joey")]  # the pick starts its scene inventory reading, no yes asked
    assert "reading" not in web.concept_pick(store, "campgrounds", None, "joey") and len(started) == 1


def test_a_reading_runs_as_a_process_of_its_own_in_the_picks_store(store):
    started = []
    log = web.reading_started(store, "campgrounds", "joey", start=lambda argv, **named: started.append((argv, named)))
    [(argv, named)] = started
    assert argv[-5:] == ["-m", "score.review.reading", "campgrounds", "--by", "joey"] and named["start_new_session"]
    assert named["env"]["SCORE_SPEND_STORE"] == str(store.cache.parent) and log.endswith(".log")


def test_every_draw_is_copied_off_this_pc_by_its_sha_and_a_failed_copy_keeps_the_draw_and_says_why(
        store, monkeypatch, tmp_path):
    said_yes(store, monkeypatch)
    record = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    assert record["offsite"] == f"concept-draws/{record['sha']}.png"
    assert bucket.read_bytes(record["offsite"]) == store.objects.read_bytes(f"blobs/{record['sha']}")
    assert json.loads(bucket.read_bytes(f"concept-draws/{record['sha']}.json"))["wording"] == record["wording"]

    class Down:
        def exists(self, key):
            raise ConnectionError("the bucket did not answer")
    said_yes(store, monkeypatch)
    failed = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([1]), offsite=Down())
    assert failed["offsite"] is None and "did not answer" in failed["offsite_refused"]
    assert concepts.draws(store, "campgrounds") == [record, failed]


def test_a_pick_is_handed_to_the_library_by_its_own_concept_command(store, monkeypatch, tmp_path):
    monkeypatch.undo()
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    from score.stages.library import backend
    monkeypatch.setattr(backend, "settings", lambda: {"SCORE_LIB_ROOT": str(tmp_path / "lib"),
                                                      "SCORE_LIB_COMMAND": "score-lib",
                                                      "SCORE_LIB_BLOBS_DIR": str(tmp_path / "blobs")})
    ran = []

    def run(words, **named):
        ran.append((words, named))
        said = {"place": "campgrounds", "did": "locked", "address": "concept/campgrounds@1",
                "saved": {"committed": "c" * 40, "pushed": True, "why": ""}}
        return subprocess.CompletedProcess(words, 0, json.dumps(said) + "\n", "")
    assert concepts.handed_over(store, "campgrounds", run=run) == "library: locked concept/campgrounds@1"
    words, named = ran[0]
    assert words[:4] == ["score-lib", "--root", str(tmp_path / "lib"), "concept"]
    assert words[words.index("--place") + 1] == "campgrounds" and words[words.index("--world") + 1] == "world1"
    assert words[words.index("--store") + 1] == str(store.objects.root)
    assert named["env"]["SCORE_LIB_BLOBS_DIR"] == str(tmp_path / "blobs") and named["cwd"] == str(tmp_path / "lib")

    refused = lambda words, **named: subprocess.CompletedProcess(words, 1, "", "no SCORE store\n")  # noqa: E731
    assert concepts.handed_over(store, "campgrounds", run=refused) == "not in the library: no SCORE store"
    monkeypatch.setattr(backend, "settings", lambda: {"SCORE_LIB_BACKEND": "none"})
    assert concepts.handed_over(store, "campgrounds", run=run).startswith("not in the library: no library")


def test_the_draw_and_redraw_prices_are_the_measured_calls_at_the_standard_tier(tmp_path):
    per_unit = tmp_path / "per-unit.json"
    measured = {"high_euros": 0.07048, "basis": "batch price of measured calls"}
    per_unit.write_text(json.dumps({"stages": {"closeup": measured}}))
    assert concepts.draw_euros(per_unit) == 0.15  # 0.07048 / 0.5 = 0.14096, up to the cent
    per_unit.write_text(json.dumps({"stages": {
        "closeup": measured, "finish-route-list": {"high_euros": 0.01665, "basis": "batch price of measured calls"}}}))
    assert concepts.redraw_euros(per_unit) == 0.18  # (0.07048 + 0.01665) / 0.5 = 0.17426, up to the cent
    per_unit.write_text(json.dumps({"stages": {}}))
    assert concepts.draw_euros(per_unit) is None


def test_the_click_writes_its_yes_at_the_price_shown_then_draws_inside_it(store, monkeypatch):
    monkeypatch.setattr(concepts, "draw_euros", lambda: 0.15)

    def run(argv, env, **kwargs):  # the draw's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record = concepts.draw(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], caller=stand_in([]))
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")

    record = web.concept_draw(store, "campgrounds", {"note": ""}, 0.15, "joey", run=run)
    yes = store.spend_yes("override", record["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.15 and "campgrounds" in yes["purpose"]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_draw(store, "campgrounds", {}, 0.10, "joey", run=run)
    with pytest.raises(review.Refused):
        web.concept_draw(store, "campgrounds", {}, 0.15, "runner", run=run)
    monkeypatch.setattr(concepts, "redraw_euros", lambda: 0.19)
    redraw = {"marks": [], "note": "warmer", "base": record["sha"]}
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_draw(store, "campgrounds", redraw, 0.15, "joey", run=run)  # a redraw is two calls: its own price


def test_an_agents_process_cannot_pick_or_keep_a_wording_in_the_framework_store(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        concepts.pick(store, "campgrounds", drawn["sha"], "joey")
    assert concepts.picked(store, "campgrounds") is None
    with pytest.raises(PermissionError):
        concepts.worded(store, "campgrounds", "my words", "joey")
    assert concepts.own_wording(store, "campgrounds") is None


def picked_draw(store, monkeypatch, place, colour):
    """A first draw of `place` made and picked; its sha."""
    said_yes(store, monkeypatch, place)
    sha = concepts.draw(store, place, {}, "joey", caller=lambda wording, pictures: a_picture(colour))["sha"]
    concepts.pick(store, place, sha, "joey")
    return sha


def test_a_place_within_another_is_sent_its_picked_picture_first_and_its_wording_as_context(store, monkeypatch):
    base = picked_draw(store, monkeypatch, "base", (200, 10, 10))
    ready_above(monkeypatch)
    said_yes(store, monkeypatch, "lab")
    asked = []
    record = concepts.draw(store, "lab", {}, "joey", caller=stand_in(asked))
    wording, sizes = asked[0]
    assert sizes == [(32, 20)] and record["picks"] == {"base": base}  # only the crop of what holds it
    assert wording.startswith("The black angular spaceship (picture 1) is divided into these compartments: 1. hub, ")
    assert "This concept is number 8: lab. " + concepts.INSIDE_ONLY in wording
    assert "1. a crop of the base's picked concept: the black angular spaceship, which holds it" in wording
    assert concepts.current_draw(store, "lab", concepts.wording_now(store, "lab"))
    picked_draw(store, monkeypatch, "base", (10, 200, 10))  # a new pick above: the lab's draw is out of date
    assert not concepts.current_draw(store, "lab", concepts.wording_now(store, "lab"))
    assert concepts.undrawn(store, ["base", "lab"])[0] == ["lab"]
    assert "In the ship; for flying and navigating the ship, one room: the cockpit at the nose" in concepts.generated(store, "cockpit")


def test_a_reference_comes_from_the_places_data_and_waits_while_it_is_not_here(store, tmp_path, monkeypatch):
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    monkeypatch.setattr(concepts, "picked", lambda _store, place: "abc" if place == "hangar" else None)
    monkeypatch.setattr(concepts, "inputs_of", lambda place: {"references": [
        {"picture": "{home}/references/quarters.png", "shows": "its look only"}]} if place == "quarters" else {})
    ready_above(monkeypatch)
    assert "is not on this machine" in concepts.waits(store, "quarters")  # its reference, the owner's quarters picture
    (tmp_path / "references").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "references" / "quarters.png")
    assert concepts.waits(store, "quarters") is None
    sources = [source for _, source in concepts.sent_pictures(store, "quarters")]
    assert sources == [("crop", "hangar", [0, 0, 32, 20]), tmp_path / "references/quarters.png"]
    assert concepts.generated(store, "quarters").endswith("Style: 2099 space base, moon base, mars "
                                                 "base, SpaceX-type rockets, Chinese and American mixed.")


def test_the_ships_length_and_reference_come_from_the_hangars_data_and_reach_its_rooms(store, monkeypatch):
    assert "It holds the ship, a crew shuttle 46 m long" in concepts.generated(store, "hangar")
    assert concepts.sent_pictures(store, "hangar")[-1][1].name == "shuttle-screenshot.png"
    assert "ship" not in concepts.tree()["within"] and "ship" not in concepts.tree()["shells"]  # no layer of its own
    assert concepts.above("cockpit") == "hangar"
    given = {"hangar": {"says": "It holds a barge 80 m long.", "references": []}}
    monkeypatch.setattr(concepts, "inputs_of", lambda place: given.get(place, {}))
    hangar = concepts.generated(store, "hangar")
    assert "It holds a barge 80 m long." in hangar and "46 m" not in hangar
    assert concepts.sent_pictures(store, "hangar") == []  # no crop while the base is not ready, no reference now


def test_no_measure_is_generated_but_the_creators_own_says(store):
    # owner's rule (2026-10-20): a generated wording sizes in relative words; only the creator's own says carry metres
    found = concepts.tree()
    for place in [*found["within"], *found["shells"], "square", "campgrounds"]:
        wording = concepts.generated(store, place)
        for name in filter(None, [place, *concepts.inside_of(place), concepts.above(place)]):
            said = [concepts.inputs_of(name).get("says", ""), *concepts.inputs_of(name).get("holds", {}).values()]
            for words in said:
                wording = wording.replace(words.rstrip("."), "")
        assert not re.search(r"\d+(\.\d+)? ?m\b", wording), (place, wording)


def test_an_outside_place_is_drawn_from_above_and_an_inside_place_as_a_cutaway(store):
    assert concepts.OUTSIDE_VIEW in concepts.generated(store, "base")
    assert concepts.OUTSIDE_VIEW in concepts.generated(store, "campgrounds")
    assert concepts.INSIDE_VIEW in concepts.generated(store, "cockpit")
    assert concepts.INSIDE_VIEW in concepts.generated(store, "hangar")
    street = concepts.generated(store, "street")
    assert concepts.EVERY_DRAW in street and concepts.OUTSIDE_VIEW in street


def test_people_are_drawn_only_where_the_places_data_has_them(store, monkeypatch):
    assert f"{concepts.EVERY_DRAW}, {concepts.WITH_PEOPLE}." in concepts.generated(store, "street")  # its design: people
    hub = concepts.generated(store, "hub")  # its design shows none and its look names none
    assert f"{concepts.EVERY_DRAW}, {concepts.NO_PEOPLE}." in hub and concepts.WITH_PEOPLE not in hub
    monkeypatch.setattr(concepts, "inputs_of", lambda place: {"people": True} if place == "hub" else {})
    assert concepts.WITH_PEOPLE in concepts.generated(store, "hub")  # the creator's say goes over the design


def test_a_draw_from_an_older_wording_does_not_count_for_draw_all(tmp_path, monkeypatch):
    store = Store.in_folder(tmp_path)
    older = [{"base": None, "wording": "an older wording", "blockout": "b"}]
    monkeypatch.setattr(concepts, "draws", lambda _store, _place: older)
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]
    older.append({"base": None, "wording": concepts.generated(store, "old_station")})
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]  # drawn without its blockout: out of date
    older.append({"base": None, "wording": concepts.generated(store, "old_station"), "blockout": "b"})
    assert concepts.undrawn(store, ["old_station"])[0] == []
    concepts.worded(store, "old_station", "One concept painting of the old station at night.", "joey")
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]  # its draw is from the generated wording
    concepts.worded(store, "old_station", None, "joey")
    assert concepts.undrawn(store, ["old_station"])[0] == []


def test_an_edited_wording_is_sent_word_for_word_and_stays_the_places_own_until_back_to_generated(store, monkeypatch):
    generated = concepts.generated(store, "campgrounds")
    asked = []
    said_yes(store, monkeypatch)
    first = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in(asked))
    assert asked[-1][0] == generated and concepts.own_wording(store, "campgrounds") is None
    said_yes(store, monkeypatch)
    edited = "One concept painting of the camp grounds, dusty."
    concepts.draw(store, "campgrounds", {"wording": f"  {edited}\n"}, "joey", caller=stand_in(asked))
    assert asked[-1][0] == edited and concepts.own_wording(store, "campgrounds") == edited
    assert concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    assert not concepts.current_draw(store, "campgrounds", "One concept painting of the camp grounds, clean.")
    said_yes(store, monkeypatch)
    concepts.draw(store, "campgrounds", {"base": first["sha"], "wording": "ignored"}, "joey", caller=stand_in(asked),
                  reviser=prompt_stand_in([], "The camp grounds, dusty, the tents red."))
    corrected = "The camp grounds, dusty, the tents red."  # a redraw's corrected prompt becomes its own wording
    assert "Image 1" in asked[-1][0] and concepts.own_wording(store, "campgrounds") == corrected
    said_yes(store, monkeypatch)
    concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in(asked))  # Draw all's request: no wording
    assert asked[-1][0] == corrected
    with pytest.raises(review.Refused, match="no wording of its own"):
        web.concept_generated(store, "galley", "joey")
    web.concept_generated(store, "campgrounds", "joey")
    assert concepts.wording_now(store, "campgrounds") == generated
    with pytest.raises(concepts.Refused, match="at most"):
        concepts.draw(store, "campgrounds", {"wording": "x" * 9000}, "joey", caller=stand_in(asked))


def test_a_places_wording_names_its_own_doors_and_openings_and_no_others(store):
    flat = concepts.generated(store, "flat")
    # owner, 2026-10-21: doors drawn lettered with room names; where a door leads is never written on it
    assert ("Its unlabelled doors: balcony door (glass) onto the outside, over the square and the harbour; front door "
            "to the stair landing into the stairwell; no other doors or openings.") in flat
    assert "no text or signs" in flat
    assert "neighbour's door behind its gate (1st floor) (shut)" in concepts.generated(store, "stairwell")


def test_a_picked_place_it_opens_into_is_sent_after_the_one_above_and_its_new_pick_puts_the_draw_out_of_date(
        store, monkeypatch):
    square = picked_draw(store, monkeypatch, "square", (200, 10, 10))
    ready_above(monkeypatch)
    assert concepts.sent_picks(store, "flat") == {"square": square}  # the stairwell is not picked yet: not sent
    said_yes(store, monkeypatch, "stairwell")
    concepts.pick(store, "stairwell", concepts.draw(store, "stairwell", {}, "joey", caller=stand_in([]))["sha"],
                  "joey")
    words = [words for words, _ in concepts.sent_pictures(store, "flat")]
    assert words[0] == "a crop of the square's picked concept: the black angular spaceship, which holds it"
    assert words[1] == "the stairwell, picked: match the door they share"  # no view through its balcony door
    said_yes(store, monkeypatch, "flat")
    asked = []
    record = concepts.draw(store, "flat", {}, "joey", caller=stand_in(asked))
    assert len(asked[0][1]) == 2 and set(record["picks"]) == {"square", "stairwell"}
    assert "2. the stairwell, picked: match the door they share" in asked[0][0]
    assert concepts.current_draw(store, "flat", concepts.wording_now(store, "flat"))
    said_yes(store, monkeypatch, "stairwell")
    concepts.pick(store, "stairwell", concepts.draw(store, "stairwell", {}, "joey", caller=stand_in([1]))["sha"],
                  "joey")
    assert not concepts.current_draw(store, "flat", concepts.wording_now(store, "flat"))


def test_a_place_is_sized_against_the_places_beside_it_in_words_only(store, tmp_path, monkeypatch):
    """Ranked by the floor of each kept plan beside it (the design's, concepts.plan_of), its walls against a person."""
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path / "home")
    sizes = {"hangar": (15.0, 14.0, "walls 12 m"), "hub": (5.0, 6.0, ""), "lab": (4.0, 3.0, ""), "tube": (3.0, 2.0, "")}
    (tmp_path / "home/design/plans").mkdir(parents=True)
    for place in concepts.inside_of("base", store):
        wide, deep, height = sizes.get(place, (4.0, 4.0, ""))
        (tmp_path / "home/design/plans" / f"{place}.json").write_text(json.dumps({"w": wide, "d": deep,
                                                                                  "height": height}))
    hangar = concepts.generated(store, "hangar")
    assert "Size: the largest in the base, floor about seven times any other's, walls towering over people." in hangar
    assert concepts.ROOF_KEPT in hangar and concepts.ROOF_KEPT not in concepts.generated(store, "base")
    assert "Size: one of the smaller in the base" in concepts.generated(store, "lab")


def test_every_generated_wording_is_short(store):
    # owner's word budget: a generated wording stays under LONGEST_GENERATED characters
    found = concepts.tree()
    for place in [*found["within"], *found["shells"], "square", "campgrounds", "old_station", "wreck"]:
        assert len(concepts.generated(store, place)) <= concepts.LONGEST_GENERATED, place


def test_a_mark_on_the_picture_above_reaches_both_calls_with_that_picture_boxed(store, monkeypatch):
    picked_draw(store, monkeypatch, "base", (200, 10, 10))
    ready_above(monkeypatch)
    said_yes(store, monkeypatch, "lab")
    first = concepts.draw(store, "lab", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch, "lab")
    asked, prompted = [], []
    above = [{"on": "base", "x": 0.7, "y": 0.0, "w": 0.3, "h": 0.3, "note": "this is the lab: its dome"}]
    record = concepts.draw(store, "lab", {"base": first["sha"], "context_marks": above, "note": ""}, "joey",
                           caller=stand_in(asked), reviser=prompt_stand_in(prompted))
    said = "Box P1 (top right of the picked concept of the base): this is the lab: its dome."
    assert said in prompted[0][0] and said in asked[0][0]
    assert len(prompted[0][1]) == len(asked[0][1]) == 3  # the draw boxed and clean, the base's pick boxed
    assert "image 3 is the picked concept of the base" in asked[0][0]
    assert record["context_marks"][0]["on"] == "base"
    said_yes(store, monkeypatch, "lab")
    with pytest.raises(concepts.Refused, match="no locked concept"):
        concepts.draw(store, "lab", {"base": first["sha"], "context_marks": [{**above[0], "on": "square"}]}, "joey",
                      caller=stand_in([]), reviser=prompt_stand_in([]))


SHIP_ROOMS = ("cockpit", "quarters", "storage", "galley", "shiplock", "engineroom", "walkway")


def test_no_two_ship_rooms_get_the_same_wording_or_references(store):
    wordings = {room: concepts.generated(store, room) for room in SHIP_ROOMS}
    assert len(set(wordings.values())) == len(SHIP_ROOMS)
    assert "for food: eat and prepare meals (counter, food stores, a table with fold-down seats)" in wordings["galley"]
    assert "pilot seats" in wordings["cockpit"] and "pilot seats" not in wordings["galley"]  # no copied look
    assert "on the port side" in wordings["quarters"] and "four bunks in two stacks" in wordings["quarters"]
    references = {room: [source.name for _, source in concepts.sent_pictures(store, room) if not isinstance(source, str)]
                  for room in SHIP_ROOMS}
    assert references == {room: [] for room in SHIP_ROOMS}  # the owner, 2026-10-21: no room has a picture of its own


def test_a_place_is_drawn_only_once_the_layer_above_is_picked_read_and_planned_and_holds_it(store, monkeypatch):
    from score.review import reading
    ready, waiting = concepts.undrawn(store, ["base", "hub", "street"])
    assert ready == ["base"]
    assert waiting == {"hub": "waits for base's concept to be locked", "street": "waits for square's concept to be locked"}
    said_yes(store, monkeypatch, "hub")
    with pytest.raises(concepts.Refused, match="hub waits for base's concept to be locked"):
        concepts.draw(store, "hub", {}, "joey", caller=stand_in([]))
    assert concepts.draws(store, "hub") == []
    picked_draw(store, monkeypatch, "base", (200, 10, 10))
    assert concepts.waits(store, "hub") == "waits for base's scene inventory to be read"
    monkeypatch.setattr(reading, "reading_of", lambda store, place: {"stand-in": place})
    assert concepts.waits(store, "hub") == "waits for base's plan to be made"
    monkeypatch.setattr(concepts, "plan_made", lambda store, place: True)
    assert concepts.waits(store, "hub") == "waits for base's plan to lay it out"
    ready_above(monkeypatch)
    assert concepts.waits(store, "hub") is None and "hub" in concepts.undrawn(store, ["hub"])[0]
    said_yes(store, monkeypatch, "hub")
    drawn = concepts.draw(store, "hub", {}, "joey", caller=stand_in([]))
    monkeypatch.setattr(concepts, "plan_made", lambda store, place: False)  # the plan above is made again
    with pytest.raises(concepts.Refused, match="hub waits for base's plan to be made"):
        concepts.pick(store, "hub", drawn["sha"], "joey")
    said_yes(store, monkeypatch, "hub")
    with pytest.raises(concepts.Refused, match="hub waits for base's plan to be made"):
        concepts.draw(store, "hub", {"base": drawn["sha"], "note": "x"}, "joey", caller=stand_in([]),
                      reviser=prompt_stand_in([]))
    assert concepts.step_refusal(store, "hub", "read") == "its concept is not locked"
    assert concepts.step_refusal(store, "base", "read") is None
    monkeypatch.setattr(reading, "reading_of", lambda store, place: None)
    assert concepts.step_refusal(store, "base", "plan") == "its scene inventory is not read"


def test_a_part_of_a_places_outside_has_no_concept_of_its_own(store):
    assert concepts.waits(store, "launch") == "is part of the square's concept, with none of its own"
    assert "launch" not in concepts.undrawn(store, ["square", "launch"])[0]
    assert "launch" not in concepts.undrawn(store, ["square", "launch"])[1]
    assert "part of it: across the water in the distance, the rocket launch" in concepts.generated(store, "square")

def test_ship_rooms_share_one_compartment_block_and_are_sent_only_the_crop_of_the_ship(store, monkeypatch, tmp_path):
    # the hangar's reference is the owner's private picture: a stand-in in this test's home, never the machine's copy
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    for ref in concepts.references_of(store, "hangar"):
        concepts.resolved(ref["picture"]).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8)).save(concepts.resolved(ref["picture"]))
    from score.review import reading
    named = concepts.holder_words
    picked_draw(store, monkeypatch, "base", (200, 10, 10))
    ready_above(monkeypatch, box=(16, 10, 32, 20))
    picked_draw(store, monkeypatch, "hangar", (90, 90, 90))
    with monkeypatch.context() as inventory:  # the holding row's name on the reading above
        inventory.setattr(reading, "reading_of", lambda store, place: {"inventory": {"rows": [
            {"id": "holder", "name": "black angular spaceship"}]}})
        assert named(store, "cockpit") == "the black angular spaceship"
    for room in SHIP_ROOMS:  # the owner, 2026-10-21: no window view, only the crop of what holds it
        sources = [source for _, source in concepts.sent_pictures(store, room)]
        assert sources == [("crop", "hangar", [16, 10, 32, 20])], room
    assert concepts.sent_picture(store, ("crop", "hangar", [16, 10, 32, 20])).size == (16, 10)
    blocks = {room: concepts.generated(store, room).split(" This concept is number ")[0] for room in SHIP_ROOMS}
    assert len(set(blocks.values())) == 1  # every sibling the identical block
    assert blocks["cockpit"].startswith("The black angular spaceship (picture 1) is divided into these compartments: "
                                        "1. cockpit and nav (flying and navigating the ship), 2. ")
    assert "7. walkway (the corridor joining every room" in blocks["cockpit"]
    galley = concepts.generated(store, "galley")
    assert "This concept is number 4: galley. " + concepts.INSIDE_ONLY in galley
    assert "window" not in galley.replace(concepts.INSIDE_ONLY, "")
