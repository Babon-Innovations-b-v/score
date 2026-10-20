"""The concept review's draws and picks (score/review/concepts.py), with a stand-in for the model (no call is made,
nothing is spent): a draw runs only inside the owner's yes for it and keeps its picture and record; a redraw sends
the base boxed and clean with each mark's note; a pick takes only a draw of the place; the click's yes is written with
its price and purpose, and refused when the price shown is not today's; the price is the measured unit at the
standard tier."""
import io
import json
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


def said_yes(store, monkeypatch, place="airlock"):
    key = concepts.yes_key(place, review.now())
    review.spend(store, "override", key, 0.15, "joey", purpose="test")
    monkeypatch.setenv("SCORE_SPEND_TICKET", f"override {key}")
    return key


def test_a_draw_runs_only_inside_the_owners_yes(store, monkeypatch):
    with pytest.raises(compute.Refused):
        concepts.draw(store, "airlock", {}, "joey", caller=stand_in([]))
    assert concepts.draws(store, "airlock") == []


def test_a_first_draw_is_worded_from_the_places_data_and_kept(store, monkeypatch):
    key = said_yes(store, monkeypatch)
    asked = []
    record = concepts.draw(store, "airlock", {"note": "more dust"}, "joey", caller=stand_in(asked))
    assert record["yes"] == key and record["euros"] == 0.15 and record["base"] is None
    assert store.objects.exists(f"blobs/{record['sha']}")
    assert concepts.draws(store, "airlock") == [record] and concepts.placed(store) == ["airlock"]
    wording, sizes = asked[0]
    assert "airlock" in wording and "The creator's note: more dust" in wording and sizes == []  # its reference is lost


def test_a_redraw_sends_the_base_boxed_and_clean_with_each_marks_note(store, monkeypatch):
    said_yes(store, monkeypatch)
    first = concepts.draw(store, "airlock", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch)
    asked = []
    marks = [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "a red door"}]
    second = concepts.draw(store, "airlock", {"marks": marks, "note": "warmer", "base": first["sha"]}, "joey",
                           caller=stand_in(asked))
    wording, sizes = asked[0]
    assert "Box 1: a red door." in wording and "Overall: warmer" in wording and sizes == [(64, 40), (64, 40)]
    assert second["base"] == first["sha"] and second["marks"][0]["note"] == "a red door"
    with pytest.raises(concepts.Refused, match="outside the picture"):
        concepts.draw(store, "airlock", {"marks": [{"x": 0.9, "y": 0, "w": 0.5, "h": 0.1}], "base": first["sha"]},
                      "joey", caller=stand_in([]))
    with pytest.raises(concepts.Refused, match="no draw of"):
        concepts.draw(store, "hub", {"base": first["sha"]}, "joey", caller=stand_in([]))


def test_a_pick_takes_only_a_draw_of_the_place_and_unlocks_again(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "airlock", {}, "joey", caller=stand_in([]))
    with pytest.raises(concepts.Refused):
        concepts.pick(store, "airlock", "0" * 64, "joey")
    concepts.pick(store, "airlock", drawn["sha"], "joey")
    assert concepts.picked(store, "airlock") == drawn["sha"]
    concepts.pick(store, "airlock", None, "joey")
    assert concepts.picked(store, "airlock") is None
    assert web.concept_pick(store, "airlock", drawn["sha"], "joey")["library"] == "library: stand-in"


def test_every_draw_is_copied_off_this_pc_by_its_sha_and_a_failed_copy_keeps_the_draw_and_says_why(
        store, monkeypatch, tmp_path):
    said_yes(store, monkeypatch)
    record = concepts.draw(store, "airlock", {}, "joey", caller=stand_in([]))
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    assert record["offsite"] == f"concept-draws/{record['sha']}.png"
    assert bucket.read_bytes(record["offsite"]) == store.objects.read_bytes(f"blobs/{record['sha']}")
    assert json.loads(bucket.read_bytes(f"concept-draws/{record['sha']}.json"))["wording"] == record["wording"]

    class Down:
        def exists(self, key):
            raise ConnectionError("the bucket did not answer")
    said_yes(store, monkeypatch)
    failed = concepts.draw(store, "airlock", {}, "joey", caller=stand_in([1]), offsite=Down())
    assert failed["offsite"] is None and "did not answer" in failed["offsite_refused"]
    assert concepts.draws(store, "airlock") == [record, failed]


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
        said = {"place": "airlock", "did": "locked", "address": "concept/airlock@1",
                "saved": {"committed": "c" * 40, "pushed": True, "why": ""}}
        return subprocess.CompletedProcess(words, 0, json.dumps(said) + "\n", "")
    assert concepts.handed_over(store, "airlock", run=run) == "library: locked concept/airlock@1"
    words, named = ran[0]
    assert words[:4] == ["score-lib", "--root", str(tmp_path / "lib"), "concept"]
    assert words[words.index("--place") + 1] == "airlock" and words[words.index("--world") + 1] == "world1"
    assert words[words.index("--store") + 1] == str(store.objects.root)
    assert named["env"]["SCORE_LIB_BLOBS_DIR"] == str(tmp_path / "blobs") and named["cwd"] == str(tmp_path / "lib")

    refused = lambda words, **named: subprocess.CompletedProcess(words, 1, "", "no SCORE store\n")  # noqa: E731
    assert concepts.handed_over(store, "airlock", run=refused) == "not in the library: no SCORE store"
    monkeypatch.setattr(backend, "settings", lambda: {"SCORE_LIB_BACKEND": "none"})
    assert concepts.handed_over(store, "airlock", run=run).startswith("not in the library: no library")


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

    record = web.concept_draw(store, "airlock", {"note": ""}, 0.15, "joey", run=run)
    yes = store.spend_yes("override", record["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.15 and "airlock" in yes["purpose"]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.concept_draw(store, "airlock", {}, 0.10, "joey", run=run)
    with pytest.raises(review.Refused):
        web.concept_draw(store, "airlock", {}, 0.15, "runner", run=run)


def test_an_agents_process_cannot_draw_or_pick_in_the_framework_store(store, monkeypatch):
    said_yes(store, monkeypatch)
    drawn = concepts.draw(store, "airlock", {}, "joey", caller=stand_in([]))
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        concepts.pick(store, "airlock", drawn["sha"], "joey")
    assert concepts.picked(store, "airlock") is None


def test_a_first_draw_carries_the_environments_style_and_its_reference_or_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    with pytest.raises(concepts.Refused, match="not on this machine"):
        concepts.first_wording("galley")  # its view's reference, the owner's quarters picture, is not here
    (tmp_path / "references").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "references" / "quarters.png")
    wording, reference = concepts.first_wording("galley")
    assert reference == tmp_path / "references" / "quarters.png"
    assert wording.endswith("The whole environment's style: 2099 space base, moon base, mars base, SpaceX-type "
                            "rockets, Chinese and American mixed.")


def test_the_ships_first_draw_is_its_true_length_holding_its_rooms_the_reference_its_look_only(tmp_path, monkeypatch):
    monkeypatch.setattr(concepts, "PROPS_HOME", tmp_path)
    (tmp_path / "references").mkdir()
    Image.new("RGB", (8, 8)).save(tmp_path / "references" / "shuttle-screenshot.png")
    wording, reference = concepts.first_wording("ship")
    assert reference.name == "shuttle-screenshot.png"
    assert "46 m long" in wording and "galley" in wording and "people and a vehicle" in wording
    assert "look only" in wording and "never its size or proportions" in wording


def test_a_shells_first_draw_holds_every_inside_place_listed_at_its_size_joined_as_laid_out():
    wording, reference = concepts.first_wording("base")
    assert reference is None and "seen from outside" in wording
    for inside in ("hub", "airlock", "habitat", "greenhouse", "garage", "hangar", "lab", "workshop", "walkway tube"):
        assert f"the {inside}" in wording
    assert "16 m by 18 m, walls 2.8 m under a glass dome" in wording  # the greenhouse, from its plan
    assert "the big door is in the roof" in wording and "holding the ship (46 m long)" in wording
    assert "the hub: a walkway tube to the lab" in wording and "the hub: opens straight into the airlock" in wording
    assert "the garage: its big door, outer, 5 x 4 m opens onto the outside" in wording
    assert "recognisable from outside" in wording and wording.endswith("Chinese and American mixed.")
    street = concepts.first_wording("street")[0]
    assert "the stairwell (four storeys" in street and "the flat (third floor" in street and "6 m by 5 m" in street
    assert "Night in a narrow street" in street  # its own look and plan stay
    assert "a crowd of people on the square" in street and "the rocket launch" in street  # its outside's parts
    assert "the square" not in concepts.holding_words("street")  # a part of its outside, no inside place
    assert not concepts.holds_inside("hangar") and concepts.holds_inside("ship")  # an inside place is drawn inside


def test_a_shells_redraw_still_holds_its_inside_places(store, monkeypatch):
    said_yes(store, monkeypatch, "base")
    first = concepts.draw(store, "base", {}, "joey", caller=stand_in([]))
    said_yes(store, monkeypatch, "base")
    asked = []
    concepts.draw(store, "base", {"note": "bigger hangar", "base": first["sha"]}, "joey", caller=stand_in(asked))
    assert "Overall: bigger hangar" in asked[0][0] and "It must still hold, as described:" in asked[0][0]
    assert "the greenhouse, 16 m by 18 m" in asked[0][0]
