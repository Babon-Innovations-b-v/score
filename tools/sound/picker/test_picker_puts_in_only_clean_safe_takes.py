"""The sound picker puts in only clean, safe takes: every source yields its sounds with their credits, a take is cut,
trimmed and looped without a jump, every file it makes passes the loudness rule (the owner was blasted by loud takes,
2026-10-06), a faulty take scores under a clean one and a recording under a generated one, and the owner's swap
applies only a take of that sound. One page world is built through the picker's own steps (candidates, made safe,
scored, written, checked, chosen, swapped, put in), all without a network or a card; reading the game's catalogue
and a pick going into the game are checked in the game 2099.

The break that turns the test red (each applied once, seen red, reverted):

- parse_search_page keeps the `-lq.ogg` preview.
- looped's crossfade `share = frame / join` made `0.0`.
- _prepare_whole copies the raw take instead of levelling it.
- NO_PROMPT_SCORE made 0.0.
- chosen_with_swaps drops `if key in known.get(name, set())`.
- layer_names drops "footstep" from the happenings it reads.

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest tools/sound/picker/test_picker_puts_in_only_clean_safe_takes.py
"""
import array
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import apply as applying  # noqa: E402
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
HQ_PREVIEW = "https://cdn.freesound.org/previews/562/562195_12618935-hq.ogg"


def tone(seconds, level=0.5, frequency=220.0):
    return array.array("h", (int(32767 * level * math.sin(2 * math.pi * frequency * index / takes.RATE))
                             for index in range(int(seconds * takes.RATE))))


def silence(seconds):
    return array.array("h", bytes(int(seconds * takes.RATE) * 2))


def overdriven(samples):
    return array.array("h", (max(-32767, min(32767, value * 2)) for value in samples))


def swelling_hum(seconds, frequency):
    """A hum with a slow swell, so a loop's ends differ unless the join is made."""
    hum = tone(seconds, level=0.4, frequency=frequency)
    for index in range(len(hum)):
        hum[index] = int(hum[index] * (0.8 + 0.2 * math.sin(index / 9000.0)))
    return hum


def walk(steps):
    found = array.array("h")
    for _ in range(steps):
        found.extend(tone(0.15))
        found.extend(silence(0.35))
    return found


def need(name, category, seconds):
    return {"name": name, "category": category, "where": "the hall", "search": [], "loop": category == "loop",
            "level": None, "seconds": seconds, "before": name, "now": []}


## The takes MOSS made for the world's sounds: (file, its sound, its samples, its CLAP score, the faults it must be
## found to have once made safe; None: nothing safe comes of it, so it is left out).
MOSS_TAKES = [
    ("lamp_buzz__p1__s2.wav", "lamp_buzz", lambda: swelling_hum(20.0, 97.3), 0.31, set()),
    ("lamp_buzz__p1__s3.wav", "lamp_buzz", lambda: overdriven(tone(14.0, level=1.0, frequency=110.0)), 0.45,
     {"clipping"}),  # 0.45 - 0.15 = 0.30, under the clean take's 0.31
    ("lamp_buzz__p1__s4.wav", "lamp_buzz", lambda: tone(6.0, level=0.02) + tone(1.0, level=0.9) + tone(6.0, level=0.02),
     0.4, {"unsteady"}),  # a clank in a hum
    ("lamp_buzz__p1__s5.wav", "lamp_buzz", lambda: overdriven(tone(3.0, level=1.0, frequency=110.0)), 0.05,
     {"clipping", "too short"}),  # 0.05 - 0.35 = -0.3, still over the recording
    ("door_shut__p1__s1.wav", "door_shut", lambda: silence(0.5) + tone(0.3) + silence(0.5), 0.2, set()),
    ("door_shut__p1__s2.wav", "door_shut", lambda: silence(1.0), 0.6, None),  # nothing left once trimmed
    ("footsteps_grating__p1__s1.wav", "footsteps_grating", lambda: walk(5), 0.3, set()),
    ("footsteps_grating__p1__s2.wav", "footsteps_grating", lambda: walk(3), 0.4, {"few steps"}),
]


def test_picker_puts_in_only_clean_safe_takes(tmp_path, monkeypatch):
    named = needs.layer_names()  # the world's sounds are ones the layers' data names
    assert "footsteps_grating" in named["surface"] and "lamp_buzz" in named["thing"], named
    wanted = [need("lamp_buzz", "loop", 12.0), need("door_shut", "shot", 3.0),
              need("footsteps_grating", "steps", 4.0), need("vent_air", "shot", 3.0)]
    moss = tmp_path / "moss" / "game"
    moss.mkdir(parents=True)
    for file, _sound, made, _clap, _faults in MOSS_TAKES:
        takes.write_wav(made(), moss / file)
    (moss / "manifest.json").write_text(json.dumps([
        {"file": file, "sound": sound, "prompt": f"a {sound}", "seconds": 15, "seed": int(file[-5]),
         "model": "MOSS-SoundEffect v2.0", "model_page": "https://huggingface.co/x", "weights": "x@1"}
        for file, sound, _made, _clap, _faults in MOSS_TAKES]))
    (moss / "scores.json").write_text(json.dumps({file: clap for file, _sound, _made, clap, _faults in MOSS_TAKES}))
    monkeypatch.setattr(sources.Moss, "FOLDER", tmp_path / "moss")
    monkeypatch.setattr(sources, "CACHE", tmp_path / "cache")
    # Freesound's search page: its one player with a preview, that preview already in the cache (no network)
    from_freesound = sources.parse_search_page(SEARCH_PAGE)
    assert [(found.key, found.author, found.audio) for found in from_freesound] == [
        ("freesound:562195", "gristi", HQ_PREVIEW)], from_freesound
    assert from_freesound[0].page.endswith("/people/gristi/sounds/562195/")
    assert sources.words_of("impactMetal_heavy_003") == ["impact", "metal", "heavy"]
    (tmp_path / "cache" / "fetched").mkdir(parents=True)
    takes.write_wav(silence(0.2) + tone(0.4) + silence(0.2), tmp_path / "cache" / "fetched" / "freesound_562195.ogg")
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    takes.write_wav(tone(12.0, level=0.3, frequency=110.0), recordings / "lamp_buzz.wav")
    takes.write_wav(walk(5), recordings / "footstep_concrete_000.wav")
    recorded = {
        "lamp_buzz": [sources.Candidate("game", "game:lamp_buzz", "The recording before", "someone", "CC0 1.0", "",
                                        (recordings / "lamp_buzz.wav").as_uri())],
        "door_shut": from_freesound,
        "footsteps_grating": [sources.Candidate(
            "kenney", "kenney:impact-sounds/footstep_concrete_000.ogg", "footstep", "Kenney", "CC0 1.0", "",
            (recordings / "footstep_concrete_000.wav").as_uri())],
        "vent_air": [],
    }

    out = tmp_path / "page_game"
    built = []
    for wanted_need in wanted:
        offered = page.candidates_for(wanted_need, [sources.Moss("game")])
        assert all(candidate.key.startswith(f"moss:{wanted_need['name']}__") for candidate in offered), offered
        kept = page.made_safe(wanted_need, offered + recorded[wanted_need["name"]], out)
        built.append(page.page_need(wanted_need, kept))
    page.write(out, "Game Sounds", "", built)
    assert page.check_safe(out) == []
    by_name = {built_need["name"]: built_need for built_need in built}
    on_page = {take["key"]: take for built_need in built for take in built_need["takes"]}

    # every file a take makes passes the loudness rule, measured again here and not taken from the page
    made_files = sorted(path for path in (out / "takes").rglob("*") if path.suffix in (".ogg", ".wav"))
    assert len(made_files) > 10, made_files
    for path in made_files:
        measured = takes.loudness.measure(path)
        assert measured["true_peak"] <= CEILING and measured["lufs"] <= LOUDEST, (path, measured)

    # each MOSS take carries its credits and exactly its faults; a take with nothing safe in it is left out
    for file, sound, _made, clap, faults in MOSS_TAKES:
        key = f"moss:{pathlib.Path(file).stem}"
        if faults is None:
            assert key not in on_page, key
            continue
        take = on_page[key]
        assert (take["prompt"], take["seed"], take["clap"]) == (f"a {sound}", int(file[-5]), clap), take
        assert take["preview"].startswith(f"takes/{sound}/moss_{pathlib.Path(file).stem}/"), take["preview"]
        assert set(take["faults"]) == faults, (key, take["faults"])
    assert on_page["freesound:562195"]["audio"] == HQ_PREVIEW

    # a faulty take scores under a clean one, and the recording under every generated take, however faulty
    assert [take["key"] for take in by_name["lamp_buzz"]["takes"]][:2] == [
        "moss:lamp_buzz__p1__s2", "moss:lamp_buzz__p1__s3"], by_name["lamp_buzz"]["takes"]
    assert by_name["lamp_buzz"]["takes"][-1]["key"] == "game:lamp_buzz", by_name["lamp_buzz"]["takes"]
    assert by_name["lamp_buzz"]["chosen"] == "moss:lamp_buzz__p1__s2"
    assert by_name["door_shut"]["chosen"] == "moss:door_shut__p1__s1"
    assert by_name["footsteps_grating"]["chosen"] == "moss:footsteps_grating__p1__s1"
    assert by_name["vent_air"]["takes"] == [] and by_name["vent_air"]["chosen"] is None

    # a take is cut into its steps, trimmed of its silence and looped without a jump
    assert on_page["moss:footsteps_grating__p1__s1"]["steps"] == 5
    kenney = on_page["kenney:impact-sounds/footstep_concrete_000.ogg"]
    assert kenney["preview"].startswith("takes/footsteps_grating/kenney_impact-sounds_footstep_concrete_000_ogg/")
    shut = takes.decode(out / on_page["moss:door_shut__p1__s1"]["files"][0])
    assert 0.25 * takes.RATE <= len(shut) <= 0.4 * takes.RATE, len(shut)  # the 0.3 s tone, to a 10 ms window
    hum = takes.decode(out / on_page["moss:lamp_buzz__p1__s2"]["files"][0])
    assert len(hum) == int((16.0 - 1.5) * takes.RATE)  # 16 s kept, its 1.5 s join folded onto its start
    # 97.3 Hz: no whole number of cycles fits the loop. Its steepest step between samples is its peak times
    # 2 pi * 97.3 / 48000: played round and round (the last sample before the first), no step may jump much past
    # that, at the join or inside the crossfade
    steepest = max(abs(value) for value in hum) * 2 * math.pi * 97.3 / takes.RATE
    played_round = list(hum) + [hum[0]]
    assert max(abs(after - before) for before, after in zip(played_round, played_round[1:])) < 2 * steepest

    # the owner's swaps, read from the page's store: only a take of that sound goes in over the chosen one
    documents = [{"id": "door_shut", "data": {"take": "freesound:562195", "more": ""}},
                 {"id": "lamp_buzz", "data": {"take": "moss:gone"}},
                 {"id": "vent_air", "data": {"take": "game:vent_air"}},
                 {"id": "footsteps_grating", "data": {"take": ""}}]
    swaps = applying.picks_from(documents)
    assert swaps == {"door_shut": "freesound:562195", "lamp_buzz": "moss:gone", "vent_air": "game:vent_air"}, swaps
    assert applying.picks_from({name: {"take": key} for name, key in swaps.items()}) == swaps
    picks = applying.chosen_with_swaps(json.loads((out / "candidates.json").read_text()), swaps)
    assert picks == {"lamp_buzz": "moss:lamp_buzz__p1__s2", "door_shut": "freesound:562195",
                     "footsteps_grating": "moss:footsteps_grating__p1__s1", "vent_air": "game:vent_air"}, picks
    sounds_path, licences_path, world = tmp_path / "sounds.json", tmp_path / "licences.json", tmp_path / "world"
    sounds_path.write_text(json.dumps({"sounds": {"vent_air": {"file": "sound/x.ogg", "volume_db": -9.0, "pick": {}}}}))
    licences_path.write_text("[]")
    changed = applying.apply(out, picks, sounds_path, licences_path, world, swapped=set(swaps))
    assert sorted(changed) == ["door_shut", "footsteps_grating", "lamp_buzz", "vent_air"], changed
    sounds = json.loads(sounds_path.read_text())["sounds"]
    assert sounds["vent_air"] == {"pick": {"chosen": {"take": "game:vent_air", "by": "owner"}}}  # the recording again
    assert sounds["door_shut"]["pick"]["chosen"] == {"take": "freesound:562195", "by": "owner"}
    assert sounds["lamp_buzz"]["pick"]["chosen"]["take"] == "moss:lamp_buzz__p1__s2"  # its swap named no take of it
    assert sounds["footsteps_grating"]["pick"]["chosen"] == {"take": "moss:footsteps_grating__p1__s1", "by": "scoring"}
    assert len(sounds["footsteps_grating"]["file"]) == 5, sounds["footsteps_grating"]
    credits = {listing["file"]: listing for listing in json.loads(licences_path.read_text())}
    assert credits["sound/generated/doors/door_shut.ogg"]["author"] == "gristi", credits
    assert credits["sound/generated/doors/door_shut.ogg"]["source"].endswith("/people/gristi/sounds/562195/")
    assert credits["sound/generated/machines/lamp_buzz.wav"]["source"].endswith("; prompt: a lamp_buzz; seed 2")
    assert all((world / name).exists() for name in credits), credits
