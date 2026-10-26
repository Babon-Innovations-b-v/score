"""The sound picker puts in only clean, safe takes: every source yields its sounds with their credits, a take is cut,
trimmed and looped without a jump, every file it makes passes the loudness rule (the owner was blasted by loud takes,
2026-10-06), a faulty take scores under a clean one and a recording under a generated one, and the owner's swap
applies only a take of that sound. All without a network or a card; reading the game's catalogue and a pick going into
the game are checked in the game 2099.

The break that turns each test red (applied once each, seen red, reverted):

- test_every_source_yields_its_sounds_with_their_credits: parse_search_page keeps the `-lq.ogg` preview.
- test_a_take_is_cut_trimmed_and_looped_without_a_jump: looped's crossfade `share = frame / join` made `0.0`.
- test_every_file_a_take_makes_passes_the_loudness_rule: _prepare_whole copies the raw take instead of levelling it.
- test_a_faulty_take_scores_under_a_clean_one_and_a_recording_under_both: NO_PROMPT_SCORE made 0.0.
- test_a_swap_applies_only_a_take_of_its_sound: chosen_with_swaps drops `if key in known.get(name, set())`.
- test_every_layer_the_data_names_is_listed: layer_names drops "footstep" from the happenings it reads.

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest tools/sound/picker/test_picker_puts_in_only_clean_safe_takes.py
"""
import array
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import apply as applying  # noqa: E402
import choose  # noqa: E402
import needs  # noqa: E402
import page  # noqa: E402
import sources  # noqa: E402
import takes  # noqa: E402

CEILING = -3.0  # dBTP, the loudness rule's ceiling
LOUDEST = -19.0  # LUFS, the loudest any file may be

SEARCH_PAGE = """
<div class="bw-player" data-sound-id="562195" data-username="gristi"
    data-ogg="https://cdn.freesound.org/previews/562/562195_12618935-lq.ogg"
    data-title="snd_footsteps_metal_floor_inside.wav" data-duration="3.10308" tabindex="0"></div>
<div class="bw-player" data-sound-id="7" data-username="nobody" tabindex="0"></div>
"""


def tone(seconds, level=0.5, frequency=220.0):
    return array.array("h", (int(32767 * level * math.sin(2 * math.pi * frequency * index / takes.RATE))
                             for index in range(int(seconds * takes.RATE))))


def silence(seconds):
    return array.array("h", bytes(int(seconds * takes.RATE) * 2))


def test_every_source_yields_its_sounds_with_their_credits(tmp_path, monkeypatch):
    found = sources.parse_search_page(SEARCH_PAGE)
    assert len(found) == 1  # the player with no preview is left out
    assert (found[0].key, found[0].author) == ("freesound:562195", "gristi")
    assert found[0].audio == "https://cdn.freesound.org/previews/562/562195_12618935-hq.ogg"  # the good preview
    assert found[0].page.endswith("/people/gristi/sounds/562195/")
    assert sources.words_of("impactMetal_heavy_003") == ["impact", "metal", "heavy"]
    made = tmp_path / "moss" / "game"
    made.mkdir(parents=True)
    (made / "manifest.json").write_text(json.dumps([
        {"file": "lamp_buzz__p1__s2.wav", "sound": "lamp_buzz", "prompt": "a buzz", "seconds": 15, "seed": 2,
         "model": "MOSS-SoundEffect v2.0", "model_page": "https://huggingface.co/x", "weights": "x@1"}]))
    (made / "scores.json").write_text(json.dumps({"lamp_buzz__p1__s2.wav": 0.42}))
    monkeypatch.setattr(sources.Moss, "FOLDER", tmp_path / "moss")
    found = sources.Moss("game").search({"name": "lamp_buzz"}, 8)
    assert [(take.prompt, take.seed, take.clap) for take in found] == [("a buzz", 2, 0.42)]
    assert sources.Moss("game").search({"name": "vent_air"}, 8) == []  # another sound's take is not offered
    assert page.slug("kenney:impact-sounds/footstep_concrete_000.ogg") == "kenney_impact-sounds_footstep_concrete_000_ogg"


def test_a_take_is_cut_trimmed_and_looped_without_a_jump():
    walk = array.array("h")
    for _ in range(5):
        walk.extend(tone(0.15))
        walk.extend(silence(0.35))
    assert len(takes.steps_in(walk)) == 5
    kept = takes.trimmed(silence(0.5) + tone(0.3) + silence(0.5), 1)
    assert 0.25 * takes.RATE <= len(kept) <= 0.4 * takes.RATE  # the 0.3 s tone, to a 10 ms window
    assert len(takes.trimmed(silence(1.0), 1)) == 0
    joined = takes.looped(tone(20.0, frequency=97.3), 1)  # 97.3 Hz: no whole number of cycles fits the loop
    # the tone's steepest step between samples is 32767 * 0.5 * 2 pi * 97.3 / 48000, about 209: played round and
    # round (the last sample before the first), no step may jump much past that, at the join or inside the crossfade
    played_round = list(joined) + [joined[0]]
    assert max(abs(after - before) for before, after in zip(played_round, played_round[1:])) < 2 * 209
    assert len(joined) == int((16.0 - 1.5) * takes.RATE)  # 16 s kept, its 1.5 s join folded onto its start


def test_every_file_a_take_makes_passes_the_loudness_rule(tmp_path):
    made = takes.prepare(takes.write_wav(tone(3.0, level=1.0), tmp_path / "loud.wav"), tmp_path / "made", "shot")
    assert made is not None
    for name in made["takes"]:
        measured = takes.loudness.measure(tmp_path / "made" / name)  # measured again here, not taken from `made`
        assert measured["true_peak"] <= CEILING and measured["lufs"] <= LOUDEST, measured
    hum = tone(12.0, level=0.4, frequency=93.7)
    for index in range(len(hum)):  # a slow swell, so the loop's ends differ unless the join is made
        hum[index] = int(hum[index] * (0.8 + 0.2 * math.sin(index / 9000.0)))
    made = takes.prepare(takes.write_wav(hum, tmp_path / "hum.wav"), tmp_path / "hum", "loop", 12.0)
    assert made is not None
    played = takes.decode(tmp_path / "hum" / "take.wav")
    measured = takes.loudness.measure(tmp_path / "hum" / "take.wav")
    assert measured["true_peak"] <= CEILING and measured["lufs"] <= LOUDEST, measured
    steps = [abs(played[index + 1] - played[index]) for index in range(len(played) - 1)]
    assert abs(played[0] - played[-1]) <= max(steps)  # the levelled loop still joins itself


def test_a_faulty_take_scores_under_a_clean_one_and_a_recording_under_both():
    hum = tone(12.0, level=0.3, frequency=110.0)
    assert choose.faults(hum, hum, "loop", 12.0, 0) == {}
    loud = array.array("h", (max(-32767, min(32767, value * 2)) for value in tone(0.3, level=1.0)))
    assert set(choose.faults(loud, loud[:100], "shot", 3.0, 0)) == {"clipping", "too short"}
    clank = tone(6.0, level=0.02) + tone(1.0, level=0.9) + tone(6.0, level=0.02)
    assert "unsteady" in choose.faults(clank, clank, "loop", 12.0, 0)
    assert "few steps" in choose.faults(hum, hum, "steps", 12.0, 3)
    scored = [{"key": "a", "score": choose.score_take(0.31, {})},
              {"key": "b", "score": choose.score_take(0.45, {"clipping": 0.15})},
              {"key": "c", "score": choose.score_take(None, {})}]
    assert choose.best(scored) == "a" and choose.best([]) is None
    weak = [{"key": "generated", "score": choose.score_take(0.05, {"clipping": 0.15})},  # 0.05 - 0.15 = -0.1
            {"key": "recording", "score": choose.score_take(None, {})}]
    assert choose.best(weak) == "generated"


def test_a_swap_applies_only_a_take_of_its_sound(tmp_path):
    record = {"needs": [{"name": "lamp_buzz", "chosen": "moss:a", "takes": [{"key": "moss:a"}, {"key": "moss:b"}]},
                        {"name": "vent_air", "chosen": "moss:c", "takes": [{"key": "moss:c"}]}]}
    assert applying.chosen_with_swaps(record, {"lamp_buzz": "moss:b", "vent_air": "moss:gone"}) == {
        "lamp_buzz": "moss:b", "vent_air": "moss:c"}
    documents = [{"id": "lamp_buzz", "data": {"take": "freesound:1", "more": ""}}, {"id": "vent_air", "data": {"take": ""}}]
    assert applying.picks_from(documents) == {"lamp_buzz": "freesound:1"}
    assert applying.picks_from({"lamp_buzz": {"take": "freesound:2"}}) == {"lamp_buzz": "freesound:2"}
    page_folder = tmp_path / "page_game"  # a swap back to the recording before takes the data off
    page_folder.mkdir()
    (page_folder / "candidates.json").write_text(json.dumps(
        {"needs": [{"name": "habitat", "category": "room", "takes": [{"key": "game:habitat", "source": "game"}]}]}))
    sounds_path, licences_path = tmp_path / "sounds_game.json", tmp_path / "licences_game.json"
    sounds_path.write_text(json.dumps({"sounds": {"habitat": {"file": "sound/x.ogg", "volume_db": -9.0, "pick": {}}}}))
    licences_path.write_text("[]")
    assert applying.apply(page_folder, {"habitat": "game:habitat"}, sounds_path, licences_path, tmp_path,
                          swapped={"habitat"}) == ["habitat"]
    assert json.loads(sounds_path.read_text())["sounds"]["habitat"] == {
        "pick": {"chosen": {"take": "game:habitat", "by": "owner"}}}


def test_every_layer_the_data_names_is_listed():
    named = needs.layer_names()
    assert "footsteps_grating" in named["surface"] and "lamp_buzz" in named["thing"], named
