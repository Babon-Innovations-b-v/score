"""The pictures a place's look is judged on, from the store's accepted outputs (read only): each film's first frame
(its concept.png, kept whole) and frames taken from its film.mp4 at FILM_SECONDS, each with the camera it was drawn
from (views.json), and each demo still with its view (stills.json). Each picture names the OpenUSD stage output it
was drawn from: its row's record's `after` (the neighbours output where the place shows others, else its assembly).

    outputs = frames.read_outputs(store, place)  # {node: accepted output} of its film and still rows
    pictures = frames.of_place(store, outputs)   # [Picture], empty when the place has no film and no still

A film is its title card and its shot joined by a fade (tools/review/demo.py: TITLE_SECONDS, FADE_SECONDS), so its
shot's frame n is shown at SHOT_START + n / RATE seconds.
"""
import dataclasses
import io
import json
import pathlib
import subprocess
import tempfile

from PIL import Image

FILMS = ("demo-film", "demo-film-extra")
STILLS = "demo-stills"
SIZE = (320, 180)  # every picture is judged at this size
RATE = 24
SHOT_START = 2.0 - 0.5  # demo.py's TITLE_SECONDS less its FADE_SECONDS
FILM_SECONDS = (2.25, 3.0, 3.75, 4.5, 5.25)  # past the fade, inside the 4 s shot


@dataclasses.dataclass
class Picture:
    name: str  # "film 0.0 s", "film hull 3.0 s", "still tool_board"
    image: Image.Image  # RGB at SIZE
    view: dict  # eye, aim, up, fov
    stage: str  # the stage output it was drawn from


def drawn_from(store, node, output):
    """The stage output a row's output was drawn from: its record's neighbours input, else its assembly's."""
    for record in reversed(store.records(node)):
        if record.get("output") == output:
            after = record.get("after", {})
            return after.get("neighbours") or after.get("assembly")
    return None


def blob_bytes(store, output, name):
    """One stored file's bytes, read without a checkout."""
    return store.objects.read_bytes(f"blobs/{store.listing(output)[name]}")


def judged_size(image):
    """The picture as judged: RGB at SIZE."""
    return image.convert("RGB").resize(SIZE, Image.LANCZOS)


def film_frame(film, seconds):
    """One frame of a film file at a time, as an image."""
    done = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{seconds:.3f}", "-i", str(film), "-frames:v", "1",
                           "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True)
    return Image.open(io.BytesIO(done.stdout))


def film_folders(listing):
    """The folders of an output holding a film ("" the root)."""
    return sorted({name.rpartition("/")[0] for name in listing if name.endswith("film.mp4")})


def film_pictures(store, output, folder, stage):
    """A film's first frame and its frames at FILM_SECONDS, each with its view."""
    prefix = f"{folder}/" if folder else ""
    label = f"film {folder} " if folder else "film "
    views = json.loads(blob_bytes(store, output, f"{prefix}views.json"))["views"]
    found = [Picture(f"{label}0.0 s", judged_size(Image.open(io.BytesIO(blob_bytes(store, output,
                                                                                   f"{prefix}concept.png")))),
                     views[0], stage)]
    with tempfile.TemporaryDirectory() as temporary:
        film = pathlib.Path(temporary) / "film.mp4"
        film.write_bytes(blob_bytes(store, output, f"{prefix}film.mp4"))
        for seconds in FILM_SECONDS:
            frame = min(len(views) - 1, round((seconds - SHOT_START) * RATE))
            found.append(Picture(f"{label}{seconds:.1f} s", judged_size(film_frame(film, seconds)), views[frame],
                                 stage))
    return found


def still_pictures(store, output, stage):
    """Each demo still with its view."""
    stills = json.loads(blob_bytes(store, output, "stills.json"))["stills"]
    return [Picture(f"still {view['name']}", judged_size(Image.open(io.BytesIO(
        blob_bytes(store, output, f"{view['name']}.png")))), view, stage) for view in stills]


def read_outputs(store, place):
    """{node: accepted output} of the place's film and still rows that have one: what its pictures come from."""
    nodes = [f"{row}@{place}" for row in (*FILMS, STILLS)]
    return {node: store.accepted(node) for node in nodes if store.accepted(node)}


def of_place(store, outputs):
    """Every picture of the outputs read_outputs gave: their films' frames, then their stills."""
    found = []
    for node, output in outputs.items():
        stage = drawn_from(store, node, output)
        if node.startswith(f"{STILLS}@"):
            found += still_pictures(store, output, stage)
            continue
        for folder in film_folders(store.listing(output)):
            found += film_pictures(store, output, folder, stage)
    return found
