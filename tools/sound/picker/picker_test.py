"""Check the sound picker's parts that need no network: reading Freesound's page, matching names, cutting steps,
joining loops, the needs the data names, and a pick going into the game with its credit and a safe level.

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


def check_the_data_names_every_layer():
    named = needs.layer_names()
    assert "footstep_grating" in named["surface"] and "lamp_buzz" in named["thing"], named


def check_the_hub_page_asks_for_what_the_owner_listed():
    wanted = {need["name"] for need in needs.needs_for("hub")}
    for name in ("habitat", "footstep_steel_plate", "console_hum", "lamp_buzz", "junction_hum",
                 "airlock_hatch_seal_clunk"):
        assert name in wanted, name


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
    take = {"key": "freesound:1", "source": "freesound", "author": "someone", "licence": sources.CC0,
            "page": "https://freesound.org/people/someone/sounds/1/", "files": ["takes/lamp_buzz/freesound_1/take.ogg"],
            "measures": {"takes/lamp_buzz/freesound_1/take.ogg": {"lufs": -24.0, "true_peak": -6.0}}}
    record = {"needs": [{"name": "lamp_buzz", "category": "loop", "takes": [take]}]}
    (page_folder / "candidates.json").write_text(json.dumps(record))
    sounds_path, licences_path = folder / "sounds.json", folder / "licences.json"
    sounds_path.write_text(json.dumps({"sounds": {"lamp_buzz": {"file": [], "pick": {"level": -60.0}}}}))
    licences_path.write_text("[]")
    changed = applying.apply(page_folder, {"lamp_buzz": "freesound:1"}, sounds_path, licences_path, repo)
    assert changed == ["lamp_buzz"]
    entry = json.loads(sounds_path.read_text())["sounds"]["lamp_buzz"]
    assert entry["file"] == "res://game/sound/recordings/machines/lamp_buzz.ogg"
    assert entry["volume_db"] == -36.0, entry
    assert (repo / "game/sound/recordings/machines/lamp_buzz.ogg").exists()
    listed = json.loads(licences_path.read_text())
    assert listed == [{"file": entry["file"], "source": take["page"], "author": "someone", "licence": sources.CC0}]


def check_a_pick_of_the_game_take_changes_nothing(folder):
    page_folder = folder / "page_game"
    page_folder.mkdir()
    record = {"needs": [{"name": "habitat", "category": "room", "takes": [{"key": "game:habitat", "source": "game"}]}]}
    (page_folder / "candidates.json").write_text(json.dumps(record))
    sounds_path, licences_path = folder / "sounds_game.json", folder / "licences_game.json"
    sounds_path.write_text(json.dumps({"sounds": {}}))
    licences_path.write_text("[]")
    assert applying.apply(page_folder, {"habitat": "game:habitat"}, sounds_path, licences_path, folder) == []


def check_a_page_slug_is_a_plain_folder_name():
    assert page.slug("kenney:impact-sounds/footstep_concrete_000.ogg") == "kenney_impact-sounds_footstep_concrete_000_ogg"


def main():
    check_a_search_page_gives_its_sounds_with_their_good_previews()
    check_names_split_into_words()
    check_a_run_of_steps_is_cut_at_its_gaps()
    check_a_loop_joins_itself_without_a_jump()
    check_silence_is_trimmed_off_both_ends()
    check_the_data_names_every_layer()
    check_the_hub_page_asks_for_what_the_owner_listed()
    check_the_catalogue_script_is_read_for_what_plays_now()
    check_picks_read_from_the_store_or_a_map()
    check_a_page_slug_is_a_plain_folder_name()
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        check_a_whole_take_is_made_safe(folder)
        check_a_pick_goes_into_the_game_with_its_credit_and_level(folder)
        check_a_pick_of_the_game_take_changes_nothing(folder)
    print("picker: all checks passed")


if __name__ == "__main__":
    main()
