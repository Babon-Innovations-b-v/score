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

One test: the pure judges (the legend, the chain's cards, the credit, the timeline) are rows of their tables, the
joins rows of clip kinds fed through joined_in_groups, and one films world (every film's views and frames, the store's
films, the assets) is cut once by figure() and by world(); both sheets go through one sheet judge, and the cut world's
video is the draft row of the timeline table.

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

RED, BLACK, WHITE = (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
# A model's parts, (name, box extents, area, linear colour) -> the legend: its sRGB colour and its share of the area.
LEGEND_ROWS = [("the hull three times the steel's area",
                [("hull", (3.0, 1.0, 1.0), 14.0, RED), ("steel", (1.0, 1.0, 1.0), 14.0 / 3.0, RED)],
                [("hull", (255, 0, 0), "75%"), ("steel", (255, 0, 0), "25%")]),
               ("an even split, black and white",
                [("deck", (1.0, 1.0, 1.0), 6.0, BLACK), ("rail", (2.0, 1.0, 1.0), 6.0, WHITE)],
                [("deck", (0, 0, 0), "50%"), ("rail", (255, 255, 255), "50%")])]
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

# The films world. Each film's shots' moves -> the shot it is shown by; film number N takes row N mod 3 (the hero,
# flat, is film 0 and stairwell film 1, so each of the first two rows is a film the world video cuts).
MOVES_ROWS = [("stands, then a walk", ["stand", "stand", "walk"], 2),
              ("a walk after one stand", ["stand", "walk", "walk"], 1),
              ("no walk", ["stand", "stand"], 1)]
# The store's films in the order it gives them: (film, its picture's shade, or None where it is not in the store).
STORE_ROWS = [("stairwell", 40), ("street", None), ("flat", 200)]
HERO = "flat"
# The world video as a draft cuts it: the hero first whatever its store place, the missing film named.
CUT_FILMS, MISSING = ["flat", "stairwell"], ["street"]
STORE_SECONDS = 5.5
# The draft cut's opening and cards (each still longer than its move in, MOVE_SECONDS): the chain's frames are drawn
# one by one at the video's size, and its 16.5 s at the real lengths took 24 of this file's 60 s budget alone.
DRAFT_OPENING, DRAFT_STEP = 1.5, 2.0
# The timeline: (case, opening seconds, card seconds, cards, [(film, shown seconds)], ending seconds, the parts' names
# in order, the films' share of the whole above it, whether it is the cut world video's own timeline). Every row stays
# within WORLD_MOST; the cut world's video is as long as its row's timeline.
TIMELINE_ROWS = [
    ("world 1 as cut on 18 Oct: four chain cards, 27 films and the hull at PLACE_MOST, the two ending clips joined",
     showcase.OPENING_SECONDS, showcase.STEP_SECONDS, 4,
     [(film, showcase.PLACE_MOST) for film, *_ in showcase.PLACES] + [("hull", showcase.PLACE_MOST)],
     14.0 + 20.0 - showcase.FADE, ["chain"] + [film for film, *_ in showcase.PLACES] + ["hull", "ending"], 0.75,
     False),
    ("the draft world cut here: two cards, its two films, no ending", DRAFT_OPENING, DRAFT_STEP, 2,
     [(film, STORE_SECONDS - showcase.demo.TITLE_SECONDS) for film in CUT_FILMS], 0, ["chain"] + CUT_FILMS, 0.0,
     True)]
TITLES = {film: title for film, *_, title in showcase.PLACES}


def probe(video, entries):
    """ffprobe's answer for one of a video's entries (format=duration, stream=codec_type), its lines split."""
    return subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "csv=p=0", str(video)],
                          capture_output=True, text=True, check=True).stdout.split()


def parts_shots(folder, parts):
    """A review page's shots of a model's parts, each part a box scaled to its area, in its linear colour."""
    files = []
    for name, extents, area, colour in parts:
        mesh = trimesh.creation.box(extents=extents)
        mesh.apply_scale(np.sqrt(area / mesh.area))
        mesh.export(folder / f"{name}.ply")
        files.append({"path": str(folder / f"{name}.ply"), "colour": list(colour)})
    return {"groups": [{"name": "aft_section-parts", "members": [{"files": files}]}]}


def store_film(path, shade):
    """A film as the runner keeps it: STORE_SECONDS at 1280x720 with a sound track."""
    path.parent.mkdir(parents=True, exist_ok=True)
    showcase.demo.ffmpeg("-f", "lavfi", "-i", f"color=c=0x{shade:02x}6464:s=1280x720:d={STORE_SECONDS}:r=24",
                         "-f", "lavfi", "-i", f"sine=frequency=440:duration={STORE_SECONDS}", "-c:a", "aac",
                         "-shortest", *showcase.demo.encode(path))
    return path


def films_world(folder):
    """One films world: every film's views (its MOVES_ROWS moves) and the middle frame of the shot that row says it is
    shown by, its lines drawn alone; the store's films in STORE_ROWS order; the assets (the hero, an opening, a credited
    concept card and a two-picture pieces card). Returns the store list and the assets file."""
    (folder / "views").mkdir(parents=True)
    for number, (film, *_) in enumerate(showcase.PLACES):
        _, moves, shot = MOVES_ROWS[number % len(MOVES_ROWS)]
        (folder / "views" / f"{film}.json").write_text(json.dumps({"moves": [{"move": move} for move in moves]}))
        frames = folder / "frames" / film
        frames.mkdir(parents=True)
        Image.new("RGB", (64, 36), (number * 9, 100, 100)).save(frames / f"shot{shot}-096-look.png")
        Image.new("RGBA", (64, 36), (10, 9, 8, 255)).save(frames / f"shot{shot}-096-lines.png")
    store = [(film, TITLES[film], shade and store_film(folder / "videos" / f"{film}.mp4", shade), shade and film)
             for film, shade in STORE_ROWS]
    for number in range(4):
        Image.new("RGB", (300, 200), (60 * number, 90, 90)).save(folder / f"asset-{number}.png")
    steps = [{"step": "Concept", "line": "a concept", "pictures": [str(folder / "asset-0.png")]},
             {"step": "Pieces", "line": "pieces", "pictures": [str(folder / f"asset-{number}.png") for number in (2, 3)]}]
    assets = folder / "assets.json"
    assets.write_text(json.dumps({"hero": HERO, "opening": str(folder / "asset-1.png"), "steps": steps,
                                  "credits": {str(folder / "asset-0.png"): "Generated using World Labs"}}))
    return store, assets


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

    for number, (case, parts, legend) in enumerate(LEGEND_ROWS):
        (folder / f"legend-{number}").mkdir()
        got = showcase.surfaces_legend(parts_shots(folder / f"legend-{number}", parts))
        assert got == legend, (case, got)

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

    # The films world, cut once into the figure and once into the world video (a missing film stops the cut, but not
    # a draft, which names it).
    films = folder / "films"
    store, assets = films_world(films)
    for number, (film, *_) in enumerate(showcase.PLACES):
        case, _, shot = MOVES_ROWS[number % len(MOVES_ROWS)]
        assert showcase.shown_shot(films, film) == shot, (film, case)
    showcase.figure(films, films / "figure.jpg")
    showcase.ENDING = folder / "no-ending"
    kept = showcase.OPENING_SECONDS, showcase.STEP_SECONDS
    try:
        showcase.OPENING_SECONDS, showcase.STEP_SECONDS = DRAFT_OPENING, DRAFT_STEP
        try:
            showcase.world(films / "out", films / "world-figure.jpg", store, assets)
            raise AssertionError("a missing film was cut")
        except SystemExit as stop:
            assert all(film in str(stop) for film in MISSING), stop
        showcase.world(films / "out", films / "world-figure.jpg", store, assets, draft=True)
        video = films / "out/world1.mp4"

        # Every timeline row: its parts in order, within WORLD_MOST, the films most of it; the cut world's video as
        # long as its own row.
        for case, opening, step, cards, shown, ending, names, share, cut in TIMELINE_ROWS:
            showcase.OPENING_SECONDS, showcase.STEP_SECONDS = opening, step
            parts = showcase.timeline(cards, shown, ending)
            whole = showcase.total(parts)
            assert [name for name, _ in parts] == names, (case, parts)
            assert whole <= showcase.WORLD_MOST and sum(seconds for _, seconds in shown) / whole > share, (case, whole)
            assert not cut or abs(showcase.length(video) - whole) < 0.2, (case, showcase.length(video), whole)
    finally:
        showcase.OPENING_SECONDS, showcase.STEP_SECONDS = kept

    record = json.loads((films / "out/world1.json").read_text())
    assert [film["film"] for film in record["films"]] == CUT_FILMS and record["missing"] == MISSING, record
    assert record["hero"] == HERO and record["steps"] == ["Concept", "Pieces"], record
    quiet = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-ss", "0.5", "-af",
                            "silencedetect=n=-60dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert "silence_start" not in quiet, quiet

    # Both sheets of the one world: a tile of every film it shows, in order with its title, COLUMNS a row, its frame
    # list beside it naming frames that exist.
    for sheet, order, frame in ((films / "figure.jpg", [film for film, *_ in showcase.PLACES], "-ink.png"),
                                (films / "world-figure.jpg", CUT_FILMS, ".png")):
        used = json.loads(sheet.with_suffix(".json").read_text())
        assert [(film, title) for film, title, _ in used] == [(film, TITLES[film]) for film in order], (sheet, used)
        assert all(path.endswith(frame) and pathlib.Path(path).exists() for _, _, path in used), (sheet, used)
        rows = -(-len(order) // showcase.COLUMNS)
        with Image.open(sheet) as picture:
            assert picture.size == (showcase.COLUMNS * showcase.TILE[0] + 24,
                                    rows * showcase.TILE[1] + (rows - 1) * 8), (sheet, picture.size)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_showcase_cuts_every_film_in_order_within_its_cap()
    print("ok")
