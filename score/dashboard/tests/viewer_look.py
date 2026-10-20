"""The 3D viewer against the films, by hand (not in `make tests`; free, reads the real store, writes nothing there):

    .venv/bin/python -m score.dashboard.tests.viewer_look [place ...] [--cameras film|look]
        [--web DIR | --hosted EXPORT] [--out DIR]

For each place (default SAMPLE) it takes the pictures the place was accepted with, each with the camera and the
moment it was drawn from: each shot of its accepted demo film once faded in (film.mp4, the camera in views.json) and
every look of its accepted light step (the scene record's cameras, in light-passes' views.json). It opens the real
viewer page once a place (the dashboard's own template and view3d.js, the web copies in --web, default
$SCORE_DASHBOARD_HOME/web3d; with --hosted, as the hosted site renders the page and serves the copies from that
export) in headless Chromium with software WebGL (llvmpipe), moves it to each camera through its
#view= link (the moving things held at the picture's moment) at the picture's shape, and measures each pair on small copies
of both pictures:

- difference: the mean absolute difference of the two in sRGB, 0 to 255;
- structure: their likeness of shapes and edges (SSIM of the luminance), 1 the same;
- brightness: the viewer's mean luminance over the picture's;
- pink: the share of the viewer's pixels in the pink and salmon of a missing finish or a stand-in box (red high,
  green well below both red and blue's mean), never in the film;
- black: the share of the viewer's pixels that are near black beyond the picture's own share.

A pair passes inside THRESHOLDS; a place passes when every pair of its film does. The light looks are reported
beside them but do not decide: the light step draws them from the stage before its assembly (the flat's balcony look
holds a crowd since gone, and its missing pictures in magenta). Out (default
$SCORE_DASHBOARD_HOME/viewer-look/): <place>-<camera>.jpg (the film's picture left, the viewer's right), report.json,
and one summary line on stdout.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
from PIL import Image

SAMPLE = ("flat", "launch", "street", "hub", "hangar", "campgrounds")
PLAYWRIGHT = "playwright@1.62.1"  # the version whose Chromium (1234) is installed in ~/.cache/ms-playwright
WIDTH = 960
PANEL = 300  # the viewer's side panel (dash.css body.view3d)
SMALL = (160, 90)
THRESHOLDS = {"difference": 40.0, "structure": 0.5, "brightness": (0.6, 1.6), "pink": 0.005, "black": 0.15}
WINDOW = 7
TIMEOUT_MS = 900_000
# How tools/review/demo.py cuts a film (RATE, TITLE_SECONDS, FADE_SECONDS; read here, never imported: the dashboard
# imports nothing of tools/): a frame half a second into a shot is past the fade.
RATE, TITLE_SECONDS, FADE_SECONDS = 24, 2.0, 0.5
FADE_FRAMES = 12
HERE = pathlib.Path(__file__).resolve().parent
STATIC = HERE.parent / "pages" / "static"
DESIGN = HERE.parents[2] / "design"


def store_objects():
    props = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
    return props / "store" / "objects"


def accepted_files(objects, node):
    """{name: blob path} of the node's standing accepted output, or {}."""
    from score.dashboard.web3d.convert import standing_accept
    accept = standing_accept(objects.parent, node)
    if accept is None:
        return {}
    listing = json.loads((objects / "outputs" / f"{accept['output']}.json").read_text())
    return {name: objects / "blobs" / sha for name, sha in listing.items()}


def film_frame(film, number, out):
    """Frame `number` of the film as a PNG at `out`."""
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(film), "-vf", f"select=eq(n\\,{number})",
                    "-frames:v", "1", str(out)], check=True)
    return out


def film_pictures(objects, place, folder):
    """Each shot of the place's accepted film once faded in (FADE_FRAMES into the shot), with that frame's camera:
    the film is its title card, then its shots, each joined to the last by a cross-fade (tools/review/demo.py)."""
    files = accepted_files(objects, f"demo-film@{place}")
    if "views.json" not in files:
        return []
    planned = json.loads(files["views.json"].read_text())
    by_name = {view["name"]: view for view in planned["views"]}
    shots = sorted({name.split("-")[0] for name in by_name}, key=lambda shot: int(shot[4:]))
    found = []
    for number, shot in enumerate(shots):
        view = by_name.get(f"{shot}-{FADE_FRAMES:03d}")
        if view is None:
            continue
        start = TITLE_SECONDS - FADE_SECONDS + number * (planned["seconds"] - FADE_SECONDS)
        frame = round(start * RATE) + FADE_FRAMES
        found.append({"camera": f"film-{shot}", "eye": view["eye"], "aim": view["aim"],
                      "fov": float(view.get("fov", 75.0)), "frame": view.get("frame"),
                      "picture": film_frame(files["film.mp4"], frame, folder / f"{place}-film-{shot}.png")})
    return found


def look_pictures(objects, place):
    """Each look of the place's accepted light step (the scene record's cameras), with its camera."""
    looks = accepted_files(objects, f"light@{place}")
    passes = accepted_files(objects, f"light-passes@{place}")
    views_file = passes.get(f"passes/{place}-0.views.json")
    if not views_file:
        return []
    found = []
    for view in json.loads(views_file.read_text())["views"]:
        picture = looks.get(f"looks/{place}/{view['name']}-look.png")
        if picture:
            found.append({"camera": f"look-{view['name'].split('-')[0]}", "eye": view["eye"], "aim": view["aim"],
                          "fov": float(view.get("fov", 75.0)), "frame": view.get("frame"),
                          "picture": picture})
    return found


def page_html(client, place):
    """The real viewer page of the place, as the dashboard renders it to its owner."""
    return client.get(f"/view/{place}").content.decode()


def view_link(camera):
    """The viewer's #view= link to a camera (view3d.js linkedView), its moving things held at the picture's moment."""
    numbers = [*camera["eye"], *camera["aim"], camera["fov"]]
    moment = f"&t={float(camera['frame']):.3f}" if camera.get("frame") is not None else ""
    return "view=" + ",".join(f"{float(number):.6f}" for number in numbers) + moment


class Pages(SimpleHTTPRequestHandler):
    """/page/<n> the prepared pages, /static/ the dashboard's static files (/static/design/ its tokens and font),
    /web/ the web copies."""

    pages, web = [], None

    def translate_path(self, path):
        path = path.split("?")[0]
        if path.startswith("/static/design/"):
            return str(DESIGN / path[len("/static/design/"):])
        if path.startswith("/static/"):
            return str(STATIC / path[len("/static/"):])
        if path.startswith("/web/"):
            return str(self.web / path[len("/web/"):])
        return str(pathlib.Path("/nonexistent"))

    def do_GET(self):
        if self.path.startswith("/page/"):
            body = self.pages[int(self.path.split("/")[2])].encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *unused):
        pass


Pages.extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript",
                        ".glb": "model/gltf-binary", ".json": "application/json"}


def serve(pages, web):
    """A local server of the pages and the files they load; its base URL."""
    Pages.pages, Pages.web = pages, web
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Pages))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"


def rendered(jobs, folder):
    """Run the browser over the jobs: one result a picture, in the jobs' order."""
    listing = folder / "jobs.json"
    listing.write_text(json.dumps(jobs))
    done = subprocess.run(["npx", "-y", "-p", PLAYWRIGHT, "node", str(HERE / "viewer_look.mjs"), str(listing)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"the browser failed:\n{done.stderr[-3000:]}")
    return [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]


def luminance(pixels):
    return pixels @ np.array([0.2126, 0.7152, 0.0722])


def pink_share(pixels):
    red, green, blue = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    return float(np.mean((red > 140) & (blue > 70) & (green < 0.72 * (red + blue) / 2) & (red > 1.15 * green + 30)))


def window_means(plane):
    """Each pixel's mean over the WINDOW x WINDOW square it starts (a box filter from running sums)."""
    sums = np.pad(plane, ((1, 0), (1, 0))).cumsum(axis=0).cumsum(axis=1)
    return (sums[WINDOW:, WINDOW:] - sums[:-WINDOW, WINDOW:] - sums[WINDOW:, :-WINDOW]
            + sums[:-WINDOW, :-WINDOW]) / WINDOW ** 2


def structure(film, seen):
    """The two luminance planes' structural likeness (SSIM over WINDOW-pixel squares, its usual constants for
    0..255): 1 the same picture, about 0 none alike."""
    first, second = luminance(film), luminance(seen)
    mean_first, mean_second = window_means(first), window_means(second)
    spread_first = window_means(first * first) - mean_first ** 2
    spread_second = window_means(second * second) - mean_second ** 2
    shared = window_means(first * second) - mean_first * mean_second
    low, high = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    alike = ((2 * mean_first * mean_second + low) * (2 * shared + high)
             / ((mean_first ** 2 + mean_second ** 2 + low) * (spread_first + spread_second + high)))
    return float(alike.mean())


def measures(reference, viewer):
    """The pair's measures on small copies of both pictures."""
    film = np.asarray(Image.open(reference).convert("RGB").resize(SMALL, Image.BOX), dtype=float)
    seen = np.asarray(Image.open(viewer).convert("RGB").resize(SMALL, Image.BOX), dtype=float)
    dark = lambda pixels: float(np.mean(luminance(pixels) < 10))
    return {"difference": round(float(np.mean(np.abs(film - seen))), 2),
            "structure": round(structure(film, seen), 3),
            "brightness": round(float(luminance(seen).mean() / max(luminance(film).mean(), 1e-3)), 3),
            "pink": round(max(pink_share(seen) - pink_share(film), 0.0), 4),
            "black": round(max(dark(seen) - dark(film), 0.0), 3)}


def passes(measured):
    low, high = THRESHOLDS["brightness"]
    return (measured["difference"] <= THRESHOLDS["difference"] and measured["structure"] >= THRESHOLDS["structure"]
            and low <= measured["brightness"] <= high and measured["pink"] <= THRESHOLDS["pink"]
            and measured["black"] <= THRESHOLDS["black"])


def side_by_side(reference, viewer, out):
    film = Image.open(reference).convert("RGB")
    seen = Image.open(viewer).convert("RGB").resize(film.size)
    joined = Image.new("RGB", (film.width * 2, film.height))
    joined.paste(film, (0, 0))
    joined.paste(seen, (film.width, 0))
    joined.thumbnail((1920, 1080))
    joined.save(out, quality=85)
    return out


def setup_django(web, export=None):
    """Django with a throwaway dashboard home whose web3d is `web` (in hosted mode on `export`, as the hosted site
    serves that export), an owner signed in: the test client."""
    home = pathlib.Path(tempfile.mkdtemp(prefix="viewer-look-home-"))
    (home / "web3d").symlink_to(web)
    if export:
        (home / "export").mkdir()
        (home / "export" / "current").symlink_to(export)
        os.environ["SCORE_DASHBOARD_MODE"] = "hosted"
    os.environ["SCORE_DASHBOARD_HOME"] = str(home)
    os.environ["SCORE_STORE_WRITABLE"] = "0"
    os.environ.setdefault("SCORE_OWNER", "viewer-look")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")
    import django
    django.setup()
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=0)
    from score.dashboard.tests.real_store_smoke import owner_client
    return owner_client()


def references(objects, places, cameras, out):
    """{place: [its pictures with their cameras]}, only the cameras whose name holds `cameras`."""
    found = {}
    for place in places:
        pictures = [*film_pictures(objects, place, out), *look_pictures(objects, place)]
        found[place] = [picture for picture in pictures if cameras in picture["camera"]]
    return {place: pictures for place, pictures in found.items() if pictures}


def browser_jobs(client, chosen, web, out):
    """One browser job a place: its page served, opened once, a picture from each of its cameras."""
    places = list(chosen)
    base = serve([page_html(client, place) for place in places], web)
    jobs = []
    for number, place in enumerate(places):
        with Image.open(chosen[place][0]["picture"]) as picture:
            height = round(WIDTH * picture.height / picture.width)
        shots = [{"hash": view_link(camera), "out": str(out / f"{place}-{camera['camera']}-viewer.png")}
                 for camera in chosen[place]]
        jobs.append({"url": f"{base}/page/{number}", "shots": shots, "width": WIDTH, "height": height,
                     "panel": PANEL, "timeout_ms": TIMEOUT_MS})
    return jobs


def judged(place, camera, result, out):
    """One pair's entry in the report: its measures, whether it passes, its side-by-side picture."""
    entry = {"place": place, "camera": camera["camera"], "passes": False, "said": result["said"],
             "seconds": result["seconds"], "frame_ms": result.get("frame_ms"), "errors": result["errors"],
             "reference": str(camera["picture"])}
    if result["shot"]:
        measured = measures(camera["picture"], result["out"])
        joined = side_by_side(camera["picture"], result["out"], out / f"{place}-{camera['camera']}.jpg")
        entry.update(measured, passes=passes(measured) and "triangles." in result["said"], side_by_side=str(joined))
    return entry


def main(argv=None):
    parser = argparse.ArgumentParser(prog="viewer_look", description=__doc__.split("\n")[0])
    parser.add_argument("places", nargs="*", default=list(SAMPLE))
    parser.add_argument("--cameras", default="", help="only the cameras whose name holds this (film, look)")
    parser.add_argument("--web", type=pathlib.Path, help="the web copies (default $SCORE_DASHBOARD_HOME/web3d)")
    parser.add_argument("--out", type=pathlib.Path, help="default $SCORE_DASHBOARD_HOME/viewer-look")
    parser.add_argument("--hosted", type=pathlib.Path, help="an export folder: the pages and copies served from it")
    options = parser.parse_args(argv)
    props = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
    home = pathlib.Path(os.environ.get("SCORE_DASHBOARD_HOME", props / "dashboard"))
    web = (options.hosted / "web3d" if options.hosted else options.web or home / "web3d").resolve()
    out = (options.out or home / "viewer-look").resolve()
    out.mkdir(parents=True, exist_ok=True)
    client = setup_django(web, options.hosted and options.hosted.resolve())
    chosen = references(store_objects(), options.places, options.cameras, out)
    results = iter(rendered(browser_jobs(client, chosen, web, out), out))
    report = [judged(place, camera, next(results), out) for place in chosen for camera in chosen[place]]
    (out / "report.json").write_text(json.dumps({"thresholds": THRESHOLDS, "pairs": report}, indent=1))
    failed = sorted({item["place"] for item in report if not item["passes"] and item["camera"].startswith("film")})
    films = [item for item in report if item["camera"].startswith("film")]
    looks = [item for item in report if not item["camera"].startswith("film")]
    print(f"viewer look: {len(chosen) - len(failed)} of {len(chosen)} places pass "
          f"({sum(item['passes'] for item in films)} of {len(films)} film pictures; looks, not deciding, "
          f"{sum(item['passes'] for item in looks)} of {len(looks)}); failing {', '.join(failed) or 'none'}; "
          f"{out / 'report.json'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
