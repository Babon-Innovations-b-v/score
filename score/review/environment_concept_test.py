"""The environment concept (score/review/environment_concept.py), with stand-ins for the model and the bucket (no call
is made, nothing is spent): environment 1's is today's data, locked, so no draw moves; a locked version is what
every place's draw reads; unlocking puts every draw and pick made under the old version out of date and stops new
ones; an ask runs only inside the owner's yes and proposes checked fields; a reference goes to the bucket, never the
repository."""
import io
import json
import subprocess

import pytest
from PIL import Image

from score import review
from score.adapters import compute
from score.review import concepts, environment_concept as ec, web
from score.store import Store, runtime_store

WORLD = "world1"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)
    monkeypatch.setattr(concepts, "offsite_store", lambda: runtime_store.FolderStore(tmp_path / "bucket"))
    return Store.in_folder(tmp_path / "store")


def a_picture(colour=(40, 90, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), colour).save(buffer, "PNG")
    return buffer.getvalue()


def said_yes(store, monkeypatch, key="test-yes"):
    review.spend(store, "override", key, 0.05, "joey", purpose="test")
    monkeypatch.setenv("SCORE_SPEND_TICKET", f"override {key}")
    return key


def drawn(store, monkeypatch, place="campgrounds"):
    said_yes(store, monkeypatch, concepts.yes_key(place, review.now()))
    return concepts.draw(store, place, {}, "joey", caller=lambda wording, pictures: a_picture((len(concepts.draws(store, place)) * 30, 9, 9)))


def test_environment_1s_concept_is_todays_data_shown_locked(store):
    shown = ec.current(store, WORLD, ["campgrounds", "hangar", "cockpit", "hub"])
    concept = shown["concept"]
    assert shown["locked"] and shown["prefilled"] and shown["versions"] == 0
    assert concept["style"] == ec.style_now() and concept["style"].startswith("2099 space base")
    assert {(ref["place"], ref["picture"].rsplit("/", 1)[-1]) for ref in concept["references"]} == {
        ("hangar", "shuttle-screenshot.png"), ("cockpit", "cockpit.png"), ("quarters", "quarters.png")}
    pulls = {row["world"]: row for row in concept["physics"]}
    assert pulls["moon"]["gravity"] == 1.62 and pulls["earth"]["gravity"] == 9.81
    assert pulls["moon"]["moves"] == ["earth"] and "habitat" in pulls["moon"]["places"]
    places = {row["name"]: row for row in concept["places"]}
    assert places["Base"]["place"] == "base" and "Hangar" in places["Base"]["holds"]
    assert "Campgrounds" in [row["name"] for row in concept["places"]] or any(
        row["place"] == "campgrounds" for row in concept["places"])
    assert len(places[next(name for name in places if places[name].get("place") == "hangar")]["holds"]) >= 6
    assert ec.in_force(store) is None and ec.version(store) is None and not ec.unlocked(store)


def test_with_no_version_kept_the_draws_read_todays_data_word_for_word(store):
    assert concepts.style(store) == f"Style: {ec.style_now()}"
    assert concepts.references_of(store, "cockpit") == concepts.inputs_of("cockpit")["references"]


def test_a_locked_version_is_what_every_draw_reads(store):
    concept = ec.prefilled(["campgrounds"])
    concept["style"] = "Cold steel and ice, a frontier mine."
    concept["references"].append({"picture": "{home}/references/mine.png", "shows": "the pit's look",
                                  "place": "campgrounds"})
    ec.saved(store, WORLD, concept, True, "joey")
    assert concepts.style(store) == "Style: Cold steel and ice, a frontier mine."
    assert "Cold steel and ice" in concepts.generated(store, "campgrounds")
    assert concepts.references_of(store, "campgrounds") == [{"picture": "{home}/references/mine.png",
                                                             "shows": "the pit's look"}]
    assert concepts.references_of(store, "street") == []
    assert concepts.waits(store, "campgrounds").startswith("its reference")  # not on this machine


def test_unlocking_puts_every_draw_and_pick_out_of_date_and_stops_new_ones(store, monkeypatch):
    first = drawn(store, monkeypatch)
    assert first["environment"] is None
    concepts.pick(store, "campgrounds", first["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == first["sha"]
    assert concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    ec.saved(store, WORLD, ec.prefilled(["campgrounds"]), False, "joey")  # his Unlock
    assert ec.unlocked(store) and concepts.picked(store, "campgrounds") is None
    assert not concepts.current_draw(store, "campgrounds", concepts.wording_now(store, "campgrounds"))
    assert concepts.waits(store, "campgrounds") == "waits for the environment concept to be locked"
    with pytest.raises(concepts.Refused, match="unlocked"):
        drawn(store, monkeypatch)
    with pytest.raises(concepts.Refused, match="unlocked"):
        concepts.pick(store, "campgrounds", first["sha"], "joey")
    ec.saved(store, WORLD, ec.prefilled(["campgrounds"]), True, "joey")  # locked again: a new version
    with pytest.raises(concepts.Refused, match="another environment concept"):
        concepts.pick(store, "campgrounds", first["sha"], "joey")
    again = drawn(store, monkeypatch)
    assert again["environment"] == ec.version(store)
    concepts.pick(store, "campgrounds", again["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == again["sha"]


def test_a_concept_out_of_shape_is_refused(store):
    with pytest.raises(ec.Refused):
        ec.saved(store, WORLD, {"style": "x" * (ec.LONGEST_LINE + 1)}, True, "joey")
    with pytest.raises(ec.Refused):
        ec.saved(store, WORLD, {"physics": [{"world": "moon", "gravity": "heavy"}]}, True, "joey")
    kept = ec.saved(store, WORLD, {"places": [{"name": " Dock ", "holds": "Bay, Office ,"}]}, False, "joey")
    assert kept["concept"]["places"] == [{"name": "Dock", "holds": ["Bay", "Office"]}]


def test_an_ask_runs_only_inside_the_owners_yes_and_proposes_checked_fields(store, monkeypatch):
    concept = ec.prefilled(["campgrounds"])
    request = {"topic": "physics", "answer": "Mars too, 3.71, moved by nothing", "concept": concept}
    asked = []

    def model(question, pictures):
        asked.append((question, pictures))
        return '```json\n{"physics": [{"world": "mars", "gravity": 3.71, "moves": [], "places": []}]}\n```'

    with pytest.raises(compute.Refused):
        ec.ask(store, WORLD, request, "joey", reviser=model)
    key = said_yes(store, monkeypatch)
    record = ec.ask(store, WORLD, request, "joey", reviser=model)
    assert record["yes"] == key and record["proposed"] == {
        "physics": [{"world": "mars", "gravity": 3.71, "moves": [], "places": []}]}
    assert "Mars too" in asked[0][0] and ec.question_of("physics") in asked[0][0]
    assert ec.asks(store, WORLD) == [record]
    with pytest.raises(ec.Refused, match="no JSON"):
        ec.ask(store, WORLD, request, "joey", reviser=lambda question, pictures: "I think Mars.")


def test_the_send_writes_its_yes_at_the_price_shown_then_asks_inside_it(store, monkeypatch):
    monkeypatch.setattr(ec, "ask_euros", lambda: 0.05)

    def run(argv, env, **kwargs):  # the ask's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record = ec.ask(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                        reviser=lambda question, pictures: '{"style": "Bright and clean"}')
        return subprocess.CompletedProcess(argv, 0, json.dumps(record) + "\n", "")

    request = {"topic": "style", "answer": "brighter", "concept": ec.prefilled([])}
    record = web.environment_ask(store, WORLD, request, 0.05, "joey", run=run)
    yes = store.spend_yes("override", record["yes"])
    assert yes["by"] == "joey" and yes["euros"] == 0.05 and "environment concept" in yes["purpose"]
    assert record["proposed"] == {"style": "Bright and clean"}
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.environment_ask(store, WORLD, request, 0.04, "joey", run=run)
    with pytest.raises(review.Refused):
        web.environment_ask(store, WORLD, request, 0.05, "runner", run=run)


def test_a_new_reference_goes_to_the_bucket_and_its_local_copy_only_while_unlocked(store, tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "PROPS_HOME", tmp_path / "home")
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    with pytest.raises(ec.Refused, match="locked"):
        ec.referenced(store, WORLD, a_picture(), "dock.png", "the dock's look", "hangar", "joey", offsite=bucket)
    ec.saved(store, WORLD, ec.prefilled([]), False, "joey")
    kept = ec.referenced(store, WORLD, a_picture(), "my dock!.png", "the dock's look", "hangar", "joey",
                         offsite=bucket)
    assert kept["concept"]["references"][-1] == {"picture": "{home}/references/my-dock-.png",
                                                 "shows": "the dock's look", "place": "hangar"}
    index = json.loads(bucket.read_bytes("references/index.json"))
    assert bucket.exists(index["my-dock-.png"]["key"]) and (tmp_path / "home/references/my-dock-.png").is_file()
    with pytest.raises(ec.Refused, match="no picture"):
        ec.referenced(store, WORLD, b"not a picture", "x.png", "", None, "joey", offsite=bucket)
    with pytest.raises(ec.Refused, match="already named"):
        ec.referenced(store, WORLD, a_picture((1, 2, 3)), "my dock!.png", "", None, "joey", offsite=bucket)


def test_an_agents_process_cannot_keep_a_version_or_a_reference(store, monkeypatch):
    monkeypatch.setattr(store, "is_framework_store", lambda: True)
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    monkeypatch.setattr(ec, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        ec.saved(store, WORLD, ec.prefilled([]), False, "joey")
    with pytest.raises(PermissionError):
        ec.kept_reference(a_picture(), "dock.png")
