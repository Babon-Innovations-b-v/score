"""Check the sound picker's parts that need no network or card: reading Freesound's page, matching names, cutting
steps, joining loops, scoring and choosing takes, MOSS's takes as a source, every sound the game needs briefed, and
a chosen take or a swap going into the game with its credit and a safe level.

Plain python and ffmpeg, run by the gate: python3 tools/sound/picker/picker_test.py
"""
import array
import json
import math
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import apply as applying  # noqa: E402
import choose  # noqa: E402
import needs  # noqa: E402
import page  # noqa: E402
import sources  # noqa: E402
import takes  # noqa: E402

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


def check_a_search_page_gives_its_sounds_with_their_good_previews():
    found = sources.parse_search_page(SEARCH_PAGE)
    assert len(found) == 1, found
    assert found[0].key == "freesound:562195" and found[0].author == "gristi"
    assert found[0].audio.endswith("-hq.ogg") and found[0].page.endswith("/people/gristi/sounds/562195/")


def check_names_split_into_words():
    assert sources.words_of("impactMetal_heavy_003") == ["impact", "metal", "heavy"]


def check_a_run_of_steps_is_cut_at_its_gaps():
    walk = array.array("h")
    for _ in range(5):
        walk.extend(tone(0.15))
        walk.extend(silence(0.35))
    steps = takes.steps_in(walk)
    assert len(steps) == 5, len(steps)


def check_a_loop_joins_itself_without_a_jump():
    long = tone(20.0, frequency=97.3)
    joined = takes.looped(long, 1)
    jump = abs(joined[-1] - joined[0])
    assert jump < 32767 * 0.05, jump
    assert len(joined) == int((takes.LOOP_SECONDS - takes.LOOP_JOIN_SECONDS) * takes.RATE)


def check_silence_is_trimmed_off_both_ends():
    padded = silence(0.5) + tone(0.3) + silence(0.5)
    kept = takes.trimmed(padded, 1)
    assert 0.25 * takes.RATE <= len(kept) <= 0.4 * takes.RATE, len(kept)


def check_a_whole_take_is_made_safe(folder):
    loud = tone(3.0, level=1.0)
    source = takes.write_wav(loud, folder / "loud.wav")
    made = takes.prepare(source, folder / "made", "shot")
    assert made is not None
    measure = made["measures"]["take.ogg"]
    assert measure["true_peak"] <= takes.loudness.CEILING_DBTP and measure["lufs"] <= takes.loudness.LIMIT_LUFS


def check_a_levelled_loop_file_still_joins_itself(folder):
    hum = tone(12.0, level=0.4, frequency=93.7)
    for index in range(len(hum)):
        hum[index] = int(hum[index] * (0.8 + 0.2 * math.sin(index / 9000.0)))
    made = takes.prepare(takes.write_wav(hum, folder / "hum.wav"), folder / "hum", "loop", 12.0)
    assert made is not None
    played = takes.decode(folder / "hum" / "take.wav")
    steps = [abs(played[index + 1] - played[index]) for index in range(len(played) - 1)]
    assert abs(played[0] - played[-1]) <= max(steps), (abs(played[0] - played[-1]), max(steps))


def check_the_data_names_every_layer():
    named = needs.layer_names()
    assert "footstep_grating" in named["surface"] and "lamp_buzz" in named["thing"], named


def check_every_sound_the_game_needs_is_briefed():
    assert needs.unbriefed() == {"surface": [], "thing": [], "catalogue": []}, needs.unbriefed()
    wanted = {need["name"]: need for need in needs.needs_for("game")}
    for name in ("habitat", "footstep_steel_plate", "console_hum", "lamp_buzz", "rocket_launch", "door_slide_open"):
        assert name in wanted, name
    for name in needs.MADE_ONLY:
        assert name not in wanted, name


def check_a_clean_steady_loop_has_no_faults():
    hum = tone(12.0, level=0.3, frequency=110.0)
    assert choose.faults(hum, hum, "loop", 12.0, 0) == {}


def check_a_clipped_short_take_is_marked_down():
    loud = array.array("h", (max(-32767, min(32767, value * 2)) for value in tone(0.3, level=1.0)))
    found = choose.faults(loud, loud[:100], "shot", 3.0, 0)
    assert "clipping" in found and "too short" in found, found


def check_a_loop_with_a_clank_in_it_is_unsteady():
    hum = tone(6.0, level=0.02) + tone(1.0, level=0.9) + tone(6.0, level=0.02)
    assert "unsteady" in choose.faults(hum, hum, "loop", 12.0, 0)


def check_the_best_score_is_chosen_and_a_recording_ranks_under_a_generated_take():
    takes_ = [{"key": "a", "score": choose.score_take(0.31, {})}, {"key": "b", "score": choose.score_take(0.45, {"clipping": 0.15})},
              {"key": "c", "score": choose.score_take(None, {})}]
    assert choose.best(takes_) == "a"
    assert choose.best([]) is None


def check_a_swap_wins_over_the_chosen_take_only_when_it_is_one_of_its_takes():
    record = {"needs": [{"name": "lamp_buzz", "chosen": "moss:a", "takes": [{"key": "moss:a"}, {"key": "moss:b"}]},
                        {"name": "vent_air", "chosen": "moss:c", "takes": [{"key": "moss:c"}]}]}
    picks = applying.chosen_with_swaps(record, {"lamp_buzz": "moss:b", "vent_air": "moss:gone"})
    assert picks == {"lamp_buzz": "moss:b", "vent_air": "moss:c"}, picks


def check_moss_takes_come_with_their_prompt_seed_and_score(folder):
    made = folder / "moss" / "game"
    made.mkdir(parents=True)
    (made / "manifest.json").write_text(json.dumps([
        {"file": "lamp_buzz__p1__s2.wav", "sound": "lamp_buzz", "prompt": "a buzz", "seconds": 15, "seed": 2,
         "model": "MOSS-SoundEffect v2.0", "model_page": "https://huggingface.co/x", "weights": "x@1"}]))
    (made / "scores.json").write_text(json.dumps({"lamp_buzz__p1__s2.wav": 0.42}))
    sources.Moss.FOLDER = folder / "moss"
    found = sources.Moss("game").search({"name": "lamp_buzz"}, 8)
    assert len(found) == 1 and found[0].prompt == "a buzz" and found[0].seed == 2 and found[0].clap == 0.42
    assert sources.Moss("game").search({"name": "vent_air"}, 8) == []


def check_the_catalogue_script_is_read_for_what_plays_now():
    written = needs.written_files()
    assert written["habitat"] == ["res://game/sound/recordings/places/habitat.ogg"], written.get("habitat")
    assert written["footsteps_metal"][0].endswith("footsteps_metal_1.ogg")


def check_picks_read_from_the_store_or_a_map():
    documents = [{"id": "lamp_buzz", "data": {"take": "freesound:1", "more": ""}}, {"id": "vent_air", "data": {"take": ""}}]
    assert applying.picks_from(documents) == {"lamp_buzz": "freesound:1"}
    assert applying.picks_from({"lamp_buzz": {"take": "freesound:2"}}) == {"lamp_buzz": "freesound:2"}


def check_a_pick_goes_into_the_game_with_its_credit_and_level(folder):
    repo = folder / "repo"
    page_folder = folder / "page"
    take_folder = page_folder / "takes" / "lamp_buzz" / "freesound_1"
    take_folder.mkdir(parents=True)
    shutil.copyfile(needs.REPO / "game/sound/made/base_hum.wav", take_folder / "take.ogg")
    take = {"key": "moss:1", "source": "moss", "author": "Farm Factory, generated", "licence": sources.Moss.LICENCE,
            "page": "https://huggingface.co/x", "prompt": "a buzz", "seed": 3,
            "files": ["takes/lamp_buzz/freesound_1/take.ogg"],
            "measures": {"takes/lamp_buzz/freesound_1/take.ogg": {"lufs": -24.0, "true_peak": -6.0}}}
    record = {"needs": [{"name": "lamp_buzz", "category": "loop", "takes": [take]}]}
    (page_folder / "candidates.json").write_text(json.dumps(record))
    sounds_path, licences_path = folder / "sounds.json", folder / "licences.json"
    sounds_path.write_text(json.dumps({"sounds": {"lamp_buzz": {"file": [], "pick": {"level": -60.0}}}}))
    licences_path.write_text("[]")
    changed = applying.apply(page_folder, {"lamp_buzz": "moss:1"}, sounds_path, licences_path, repo)
    assert changed == ["lamp_buzz"]
    entry = json.loads(sounds_path.read_text())["sounds"]["lamp_buzz"]
    assert entry["file"] == "res://game/sound/generated/machines/lamp_buzz.ogg"
    assert entry["volume_db"] == -36.0, entry
    assert (repo / "game/sound/generated/machines/lamp_buzz.ogg").exists()
    listed = json.loads(licences_path.read_text())
    assert listed == [{"file": entry["file"], "source": "https://huggingface.co/x; prompt: a buzz; seed 3",
                       "author": "Farm Factory, generated", "licence": sources.Moss.LICENCE}], listed
    applying.apply(page_folder, {"lamp_buzz": "moss:1"}, sounds_path, licences_path, repo)
    assert len(json.loads(licences_path.read_text())) == 1, "a second apply replaces, never adds"


def check_a_swap_back_to_the_recording_before_takes_the_data_off(folder):
    page_folder = folder / "page_game"
    page_folder.mkdir()
    record = {"needs": [{"name": "habitat", "category": "room", "takes": [{"key": "game:habitat", "source": "game"}]}]}
    (page_folder / "candidates.json").write_text(json.dumps(record))
    sounds_path, licences_path = folder / "sounds_game.json", folder / "licences_game.json"
    sounds_path.write_text(json.dumps({"sounds": {"habitat": {"file": "res://x.ogg", "volume_db": -9.0, "pick": {}}}}))
    licences_path.write_text("[]")
    assert applying.apply(page_folder, {"habitat": "game:habitat"}, sounds_path, licences_path, folder) == ["habitat"]
    assert json.loads(sounds_path.read_text())["sounds"]["habitat"] == {"pick": {}}


def check_a_page_slug_is_a_plain_folder_name():
    assert page.slug("kenney:impact-sounds/footstep_concrete_000.ogg") == "kenney_impact-sounds_footstep_concrete_000_ogg"


def main():
    check_a_search_page_gives_its_sounds_with_their_good_previews()
    check_names_split_into_words()
    check_a_run_of_steps_is_cut_at_its_gaps()
    check_a_loop_joins_itself_without_a_jump()
    check_silence_is_trimmed_off_both_ends()
    check_the_data_names_every_layer()
    check_every_sound_the_game_needs_is_briefed()
    check_a_clean_steady_loop_has_no_faults()
    check_a_clipped_short_take_is_marked_down()
    check_a_loop_with_a_clank_in_it_is_unsteady()
    check_the_best_score_is_chosen_and_a_recording_ranks_under_a_generated_take()
    check_a_swap_wins_over_the_chosen_take_only_when_it_is_one_of_its_takes()
    check_the_catalogue_script_is_read_for_what_plays_now()
    check_picks_read_from_the_store_or_a_map()
    check_a_page_slug_is_a_plain_folder_name()
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        check_a_whole_take_is_made_safe(folder)
        check_a_levelled_loop_file_still_joins_itself(folder)
        check_a_pick_goes_into_the_game_with_its_credit_and_level(folder)
        check_a_swap_back_to_the_recording_before_takes_the_data_off(folder)
        check_moss_takes_come_with_their_prompt_seed_and_score(folder)
    print("picker: all checks passed")


if __name__ == "__main__":
    main()
