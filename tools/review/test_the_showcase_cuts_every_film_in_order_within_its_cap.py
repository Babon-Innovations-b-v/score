"""Check the showcase's measured numbers and its figure on pieces made here: each surface's share of a model's parts is
its share of their area, a film is shown by its first walking shot (else its second), and the figure lays one inked
frame of every film in story order, its frame list beside it; the world video shows the framework's chain once, then
the hero's film and the store's other films made here in the order given, stops on a missing one and, as a draft,
names it; world 1's timeline stays within its cap. The whole cut needs the films and their stills; no
Blender, no cloud.

Breaks (each applied once, seen red, reverted), in tools/review/showcase.py:
- the legend: surfaces_legend gives every part an even share.
- the figure: shown_shot always takes the second shot.
- the chain: chain_cards lets steps out of order through.
- the credit: credited never draws a credit.
- the timeline: timeline leaves the ending out.
- the world: world keeps the films' given order, the hero not first.
- many clips in groups: joined_in_groups counts each group as long as its clips without their cross-fades.
- picture outlasting sound: joined_apart lays the picture down without its sound (no `-map 1:a`). (Joining them all
  in one graph, the 2026-10-18 stall, does not stall on clips this small, so this test cannot show that one.)

One test: the pure judges (the chain's cards, the credit) are rows of their tables, the joins rows of clip kinds fed
through joined_in_groups, and one folder holds the films' frames, the store's films and the cut made from them.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_the_showcase_cuts_every_film_in_order_within_its_cap.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import showcase  # noqa: E402

STEPS = [{"step": "References and style", "pictures": ["r.png"]}, {"step": "Concept", "pictures": ["c.png"]},
         {"step": "Plan", "pictures": ["p.png"]}, {"step": "Pieces", "pictures": ["a.png", "b.png"]},
         {"step": "Pieces", "pictures": ["d.png"]}]
# The chain's steps -> the cards' steps in order, or None where the cut must stop (a step may take two cards).
CHAIN_ROWS = [("the whole chain", STEPS, ["References and style", "Concept", "Plan", "Pieces", "Pieces"]),
              ("out of order", [STEPS[2], STEPS[1]], None),
              ("a step it does not have", [{"step": "Place", "pictures": ["f.png"]}], None),
              ("more than CHAIN_MOST", [STEPS[0]] * (showcase.CHAIN_MOST + 1), None)]
# A credit -> whether the picture's bottom right is drawn on (its top left never is).
CREDIT_ROWS = [("uncredited", None, False), ("credited", "Generated using World Labs", True)]
# Clips joined in groups (57 clips in one graph stalled, 2026-10-18; 8 clips whose picture outlasts their sound wrote
# nothing): (case, clips, picture seconds, sound seconds or None, the streams out, tolerance); every cross-fade kept.
JOIN_ROWS = [("many silent clips", 10, 1.0, None, ["video"], 0.1),
             ("picture outlasting sound", 8, 3.5417, 3.5, ["audio", "video"], 0.2)]


def probe(video, entries):
    """ffprobe's answer for one of a video's entries (format=duration, stream=codec_type), its lines split."""
    return subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "csv=p=0", str(video)],
                          capture_output=True, text=True, check=True).stdout.split()


def parts_of_area(folder):
    """Two parts' shots, the hull's area three times the steel's, both in linear red."""
    files = []
    for name, extents, area in (("hull", (3.0, 1.0, 1.0), 14.0), ("steel", (1.0, 1.0, 1.0), 14.0 / 3.0)):
        mesh = trimesh.creation.box(extents=extents)
        mesh.apply_scale(np.sqrt(area / mesh.area))
        mesh.export(folder / f"{name}.ply")
        files.append({"path": str(folder / f"{name}.ply"), "colour": [1.0, 0.0, 0.0]})
    return {"groups": [{"name": "aft_section-parts", "members": [{"files": files}]}]}


def films_folder(folder):
    """A films' out folder with every film's views and the middle frame of its shown shot, its lines drawn alone."""
    (folder / "views").mkdir(parents=True)
    for number, (film, *_) in enumerate(showcase.PLACES):
        moves = [{"move": "stand"}, {"move": "walk" if number % 2 else "stand"}, {"move": "walk"}]
        (folder / "views" / f"{film}.json").write_text(json.dumps({"moves": moves}))
        frames = folder / "frames" / film
        frames.mkdir(parents=True)
        name = f"shot{showcase.shown_shot(folder, film)}-096"
        Image.new("RGB", (64, 36), (number * 10, 100, 100)).save(frames / f"{name}-look.png")
        Image.new("RGBA", (64, 36), (10, 9, 8, 255)).save(frames / f"{name}-lines.png")
    return folder


def store_film(path, shade):
    """A film as the runner keeps it: 5.5 s at 1280x720 with a sound track."""
    path.parent.mkdir(parents=True)
    showcase.demo.ffmpeg("-f", "lavfi", "-i", f"color=c=0x{shade:02x}6464:s=1280x720:d=5.5:r=24", "-f", "lavfi", "-i",
                         "sine=frequency=440:duration=5.5", "-c:a", "aac", "-shortest", *showcase.demo.encode(path))
    return path


def world_assets(folder):
    """The world's assets: the hero flat, an opening, a credited concept card and a two-picture pieces card."""
    for number in range(4):
        Image.new("RGB", (300, 200), (60 * number, 90, 90)).save(folder / f"{number}.png")
    steps = [{"step": "Concept", "line": "a concept", "pictures": [str(folder / "0.png")]},
             {"step": "Pieces", "line": "pieces", "pictures": [str(folder / "2.png"), str(folder / "3.png")]}]
    assets = folder / "assets.json"
    assets.write_text(json.dumps({"hero": "flat", "opening": str(folder / "1.png"), "steps": steps,
                                  "credits": {str(folder / "0.png"): "Generated using World Labs"}}))
    return assets


def joined_clips(folder, case, count, picture, sound):
    """`count` grey clips of `picture` seconds, with a `sound`-second tone where it is given, joined in groups."""
    clips = []
    for index in range(count):
        clip = folder / f"{case}-{index}.mp4"
        tone = ["-f", "lavfi", "-i", f"sine=f=440:d={sound}"] if sound else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s=64x36:d={picture}:r=24",
                        *tone, "-pix_fmt", "yuv420p", *(["-c:a", "aac"] if sound else []), str(clip)], check=True)
        clips.append(clip)
    out = folder / f"{case}.mp4"
    showcase.joined_in_groups(clips, [picture] * count, out, folder)
    return out


def test_the_showcase_cuts_every_film_in_order_within_its_cap():
    """The showcase's numbers, its figure and its world video, all on pieces made here."""
    folder = pathlib.Path(tempfile.mkdtemp())

    # Each surface's share of a model's parts is its share of their area, its library colour in sRGB.
    legend = showcase.surfaces_legend(parts_of_area(folder))
    assert legend == [("hull", (255, 0, 0), "75%"), ("steel", (255, 0, 0), "25%")], legend

    for case, steps, cards in CHAIN_ROWS:
        try:
            got = [step for step, _, _ in showcase.chain_cards({"steps": steps})]
        except SystemExit:
            got = None
        assert got == cards, (case, got)

    plain = Image.new("RGB", (showcase.W, showcase.H), (200, 200, 200))
    for case, credit, drawn in CREDIT_ROWS:
        marked = np.asarray(showcase.credited(plain.copy(), credit))
        assert (marked[-60, -60] != 200).any() == drawn and (marked[60, 60] == 200).all(), case
        assert drawn or np.array_equal(marked, np.asarray(plain)), case

    for case, count, picture, sound, streams, tolerance in JOIN_ROWS:
        out = joined_clips(folder, case.replace(" ", "-"), count, picture, sound)
        seconds = float(probe(out, "format=duration")[0])
        assert sorted(probe(out, "stream=codec_type")) == streams, case
        assert abs(seconds - (count * picture - (count - 1) * showcase.demo.FADE_SECONDS)) < tolerance, (case, seconds)

    # World 1 as cut on 18 Oct (four chain cards, 27 films, the two ending clips joined): every place PLACE_MOST, the
    # places most of the time, and the whole within WORLD_MOST.
    shown = [(film, showcase.PLACE_MOST) for film, *_ in showcase.PLACES] + [("hull", showcase.PLACE_MOST)]
    parts = showcase.timeline(4, shown, 14.0 + 20.0 - showcase.FADE)
    assert [name for name, _ in parts][:2] == ["chain", "flat"] and parts[-1][0] == "ending", parts
    whole = showcase.total(parts)
    assert whole <= showcase.WORLD_MOST and sum(seconds for _, seconds in shown) / whole > 0.75, whole

    # The figure: a film is shown by its first walking shot (else its second), one inked frame of every film in story
    # order, its frame list beside it.
    films = films_folder(folder / "films")
    assert showcase.shown_shot(films, "flat") == 2 and showcase.shown_shot(films, "stairwell") == 1
    showcase.figure(films, films / "figure.jpg")
    used = json.loads((films / "figure.json").read_text())
    assert [film for film, _, _ in used] == [film for film, *_ in showcase.PLACES], used
    assert all(path.endswith("-ink.png") and pathlib.Path(path).exists() for _, _, path in used), used
    assert used[-1][1] == "Mars camp grounds", used[-1]
    with Image.open(films / "figure.jpg") as sheet:
        assert sheet.size == (4 * showcase.TILE[0] + 24, 7 * showcase.TILE[1] + 48), sheet.size

    # The world video: the hero's film right after the chain whatever its story place; a missing film stops the cut
    # but not a draft, which names it; the video as long as its timeline, its sound never below a whisper.
    store = [("stairwell", "Stairwell", store_film(folder / "a/film.mp4", 40), "a"), ("street", "Street", None, None),
             ("flat", "Flat", store_film(folder / "b/film.mp4", 200), "b")]
    assets = world_assets(folder)
    showcase.ENDING = folder / "ending"
    try:
        showcase.world(folder / "out", folder / "fig.jpg", store, assets)
        raise AssertionError("a missing film was cut")
    except SystemExit as stop:
        assert "street" in str(stop), stop
    kept = showcase.OPENING_SECONDS, showcase.STEP_SECONDS
    # A shorter opening and cards (each still longer than its move in, MOVE_SECONDS): the chain's frames are drawn one
    # by one at the video's size, and its 16.5 s at the real lengths took 24 of this file's 60 s budget alone.
    showcase.OPENING_SECONDS, showcase.STEP_SECONDS = 1.5, 2.0
    try:
        showcase.world(folder / "out", folder / "fig.jpg", store, assets, draft=True)
        expected = showcase.total(showcase.timeline(
            2, [(name, 5.5 - showcase.demo.TITLE_SECONDS) for name in ("flat", "stairwell")], 0))
    finally:
        showcase.OPENING_SECONDS, showcase.STEP_SECONDS = kept
    record = json.loads((folder / "out/world1.json").read_text())
    assert [film["film"] for film in record["films"]] == ["flat", "stairwell"] and record["missing"] == ["street"]
    assert record["steps"] == ["Concept", "Pieces"], record
    measured = showcase.length(folder / "out/world1.mp4")
    assert abs(measured - expected) < 0.2, (measured, expected)
    quiet = subprocess.run(["ffmpeg", "-v", "info", "-i", str(folder / "out/world1.mp4"), "-ss", "0.5", "-af",
                            "silencedetect=n=-60dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert "silence_start" not in quiet, quiet
    with Image.open(folder / "fig.jpg") as sheet:
        assert sheet.size == (4 * showcase.TILE[0] + 24, showcase.TILE[1]), sheet.size


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_showcase_cuts_every_film_in_order_within_its_cap()
    print("ok")
