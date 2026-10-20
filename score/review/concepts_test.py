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
    assert "campgrounds" in wording and "The creator's note: more dust" in wording and sizes == []  # an outside place with no reference


def test_a_redraw_sends_the_base_boxed_and_clean_with_each_marks_note(store, monkeypatch):
    said_yes(store, monkeypatch)
    first = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch)
    asked = []
    marks = [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "a red door"}]
    second = concepts.draw(store, "campgrounds", {"marks": marks, "note": "warmer", "base": first["sha"]}, "joey",
                           caller=stand_in(asked))
    wording, sizes = asked[0]
    assert "Box 1: a red door." in wording and "Overall: warmer" in wording and sizes == [(64, 40), (64, 40)]
    assert second["base"] == first["sha"] and second["marks"][0]["note"] == "a red door"
    with pytest.raises(concepts.Refused, match="outside the picture"):
        concepts.draw(store, "campgrounds", {"marks": [{"x": 0.9, "y": 0, "w": 0.5, "h": 0.1}], "base": first["sha"]},
                      "joey", caller=stand_in([]))
    with pytest.raises(concepts.Refused, match="no draw of"):
        concepts.draw(store, "hub", {"base": first["sha"]}, "joey", caller=stand_in([]))


def test_a_pick_takes_only_a_draw_of_the_place_and_unlocks_again(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    with pytest.raises(concepts.Refused):
        concepts.pick(store, "campgrounds", "0" * 64, "joey")
    concepts.pick(store, "campgrounds", drawn["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == drawn["sha"]
    concepts.pick(store, "campgrounds", None, "joey")
    assert concepts.picked(store, "campgrounds") is None
    assert web.concept_pick(store, "campgrounds", drawn["sha"], "joey")["library"] == "library: stand-in"


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


def test_the_price_is_the_measured_unit_at_the_standard_tier(tmp_path):
    per_unit = tmp_path / "per-unit.json"
    measured = {"high_euros": 0.07048, "basis": "batch price of measured calls"}
    per_unit.write_text(json.dumps({"stages": {"closeup": measured}}))
    assert concepts.draw_euros(per_unit) == 0.15  # 0.07048 / 0.5 = 0.14096, up to the cent
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


def test_an_agents_process_cannot_draw_or_pick_in_the_framework_store(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in([]))
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        concepts.pick(store, "campgrounds", drawn["sha"], "joey")
    assert concepts.picked(store, "campgrounds") is None




def picked_draw(store, monkeypatch, place, colour):
    """A first draw of `place` made and picked; its sha."""
    said_yes(store, monkeypatch, place)
    sha = concepts.draw(store, place, {}, "joey", caller=lambda wording, pictures: a_picture(colour))["sha"]
    concepts.pick(store, place, sha, "joey")
    return sha


def test_a_place_within_another_is_sent_its_picked_picture_first_and_its_wording_as_context(store, monkeypatch):
    base = picked_draw(store, monkeypatch, "base", (200, 10, 10))
    said_yes(store, monkeypatch, "lab")
    asked = []
    record = concepts.draw(store, "lab", {}, "joey", caller=stand_in(asked))
    wording, sizes = asked[0]
    assert sizes == [(64, 40)] and record["above"] == base  # the base's picked draw, the only picture
    assert "This place sits within the base." in wording
    assert "1. the picked concept of the base this place sits within" in wording
    assert concepts.current_draw(store, "lab", concepts.wording_now(store, "lab"))
    picked_draw(store, monkeypatch, "base", (10, 200, 10))  # a new pick above: the lab's draw is out of date
    assert not concepts.current_draw(store, "lab", concepts.wording_now(store, "lab"))
    assert concepts.undrawn(store, ["base", "lab"])[0] == ["lab"]
    assert ("This place sits within the ship: A crew shuttle 46 m long, drawn as large as it truly is, its rooms "
            "along one deck inside; people beside it are small against it.") in concepts.generated("cockpit")


def test_a_place_waits_while_the_one_above_it_is_not_picked(store, monkeypatch):
    ready, waiting = concepts.undrawn(store, ["base", "hub", "street"])
    assert ready == ["base"]
    assert waiting == {"hub": "waits for base's concept to be picked", "street": "waits for square's concept to be picked"}
    said_yes(store, monkeypatch, "hub")
    with pytest.raises(concepts.Refused, match="hub waits for base's concept to be picked"):
        concepts.draw(store, "hub", {}, "joey", caller=stand_in([]))
    assert concepts.draws(store, "hub") == []


def test_a_reference_comes_from_the_places_data_and_waits_while_it_is_not_here(store, tmp_path, monkeypatch):
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    monkeypatch.setattr(concepts, "picked", lambda _store, place: "abc" if place == "ship" else None)
    assert "is not on this machine" in concepts.waits(store, "galley")  # its reference, the owner's quarters picture
    (tmp_path / "references").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "references" / "quarters.png")
    assert concepts.waits(store, "galley") is None
    assert [source for _, source in concepts.sent_pictures("galley")] == ["ship", tmp_path / "references/quarters.png"]
    assert concepts.generated("galley").endswith("The whole environment's style: 2099 space base, moon base, mars "
                                                 "base, SpaceX-type rockets, Chinese and American mixed.")


def test_the_ships_length_and_reference_come_from_its_data_and_reach_the_hangar(monkeypatch):
    assert "the ship (A crew shuttle 46 m long" in concepts.generated("hangar")
    assert concepts.generated("ship").startswith("One concept painting of the ship. A crew shuttle 46 m long")
    assert concepts.sent_pictures("ship")[-1][1].name == "shuttle-screenshot.png"
    given = {"ship": {"says": "A barge 80 m long.", "references": []}}
    monkeypatch.setattr(concepts, "inputs_of", lambda place: given.get(place, {}))
    hangar = concepts.generated("hangar")
    assert "the ship (A barge 80 m long)" in hangar and "46 m" not in hangar
    assert len(concepts.sent_pictures("ship")) == 1  # the hangar's pick only: no reference in its data now


def test_no_measure_is_generated_but_the_creators_own_says():
    found = concepts.tree()
    for place in [*found["within"], *found["shells"], "square", "campgrounds"]:
        wording = concepts.generated(place)
        for name in filter(None, [place, *concepts.inside_of(place), concepts.above(place)]):
            wording = wording.replace(concepts.inputs_of(name).get("says", "").rstrip("."), "")
        assert not re.search(r"\d+(\.\d+)? ?m\b", wording), (place, wording)


def test_an_outside_place_is_drawn_from_above_and_an_inside_place_as_a_cutaway():
    assert concepts.OUTSIDE_VIEW in concepts.generated("base") and concepts.OUTSIDE_VIEW in concepts.generated("ship")
    assert concepts.INSIDE_VIEW in concepts.generated("cockpit") and concepts.INSIDE_VIEW in concepts.generated("hangar")
    assert concepts.EVERY_DRAW in concepts.generated("street") and concepts.OUTSIDE_VIEW in concepts.generated("street")


def test_a_draw_from_an_older_wording_does_not_count_for_draw_all(tmp_path, monkeypatch):
    store = Store.in_folder(tmp_path)
    older = [{"base": None, "wording": "an older wording"}]
    monkeypatch.setattr(concepts, "draws", lambda _store, _place: older)
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]
    older.append({"base": None, "wording": concepts.generated("old_station")})
    assert concepts.undrawn(store, ["old_station"])[0] == []


def test_an_edited_wording_is_sent_word_for_word_and_stays_the_places_own_until_back_to_generated(store, monkeypatch):
    generated = concepts.generated("campgrounds")
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
    concepts.draw(store, "campgrounds", {"base": first["sha"], "wording": "ignored"}, "joey", caller=stand_in(asked))
    assert "Image 1" in asked[-1][0] and concepts.own_wording(store, "campgrounds") == edited  # a redraw keeps it
    said_yes(store, monkeypatch)
    concepts.draw(store, "campgrounds", {}, "joey", caller=stand_in(asked))  # Draw all's request: no wording
    assert asked[-1][0] == edited
    with pytest.raises(review.Refused, match="no wording of its own"):
        web.concept_generated(store, "galley", "joey")
    web.concept_generated(store, "campgrounds", "joey")
    assert concepts.wording_now(store, "campgrounds") == generated
    with pytest.raises(concepts.Refused, match="at most"):
        concepts.draw(store, "campgrounds", {"wording": "x" * 9000}, "joey", caller=stand_in(asked))


def test_an_edited_wording_makes_the_draw_from_the_generated_one_out_of_date(tmp_path, monkeypatch):
    store = Store.in_folder(tmp_path)
    drawn = [{"base": None, "wording": concepts.generated("old_station")}]
    monkeypatch.setattr(concepts, "draws", lambda _store, _place: drawn)
    assert concepts.undrawn(store, ["old_station"])[0] == []
    concepts.worded(store, "old_station", "One concept painting of the old station at night.", "joey")
    assert concepts.undrawn(store, ["old_station"])[0] == ["old_station"]  # its draw is from the older wording
    concepts.worded(store, "old_station", None, "joey")
    assert concepts.undrawn(store, ["old_station"])[0] == []


def test_an_agents_process_cannot_keep_a_wording_in_the_framework_store(store, monkeypatch):
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        concepts.worded(store, "campgrounds", "my words", "joey")
    assert concepts.own_wording(store, "campgrounds") is None
