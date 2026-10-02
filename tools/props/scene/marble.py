"""Send a room's target picture to World Labs Marble and bring back its world as a layout reference.

    ~/.farm-factory-props/env/bin/python tools/props/scene/marble.py <room> generate \
        [--model marble-1.1-plus] [--text "<words to guide it>"]
    ~/.farm-factory-props/env/bin/python tools/props/scene/marble.py <room> fetch
    ~/.farm-factory-props/env/bin/python tools/props/scene/marble.py <room> depth
    ~/.farm-factory-props/env/bin/python tools/props/scene/marble.py <room> paint \
        --depth-png <spot>-depth.png --z-max 26 --text "<the look>" --seed 7
    ~/.farm-factory-props/env/bin/python tools/props/scene/marble.py <room> generate --pano --seed 7 --text "<the look>"
    ~/.farm-factory-props/env/bin/python tools/props/scene/marble.py <room> splats

`paint` turns a depth panorama of one of our own rooms (depth_pano.tscn, pano.py) into a colour
panorama with pano:depth_to_rgb and makes it the room's target; `generate --pano` then builds the
world from that panorama with its words as given (no recaption). `splats` downloads the world's
Gaussian splats as PLY (free, 500k).

`generate` sends WORK/scene/<room>/<room>-target.png as an image prompt (model marble-1.1, about
1,580 credits: 80 for the panorama, 1,500 for the world; marble-1.1-plus up to 3,080), waits for the world and writes
marble/world.json. `fetch` downloads what came free with it: the collider mesh (GLB, 100-200k
triangles), the panorama, the thumbnail and the metric scale (`metric_scale_factor`,
`ground_plane_offset`), into marble/. The high-quality mesh export costs another 3,500 credits per
world and is not asked for here. `depth` sees the collider from the target's camera and writes
depth-marble.npz in depth.py's form, so `boxes.py <room> --depth depth-marble.npz` measures the
same masks on Marble's room instead of MoGe-2's.

The world is a reference for where things stand and how big the room is, never a model to ship:
the shipped models stay our own Pixal3D ones. The API key is read at run time from
~/.config/worldlabs/api_key (WORLDLABS_KEY_FILE) and never written anywhere.
"""
import argparse
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from target import folder  # noqa: E402

API = "https://api.worldlabs.ai/marble/v1"
KEY_FILE = pathlib.Path(os.environ.get("WORLDLABS_KEY_FILE", pathlib.Path.home() / ".config/worldlabs/api_key"))
MODEL = "marble-1.1"
# marble-1.1-plus sizes the world to what the picture shows, for a whole base rather than a room:
# 1,500 to 3,000 credits for the world.
MODELS = ("marble-1.1", "marble-1.1-plus")
# A world takes minutes; look again this often, and give up after this long.
LOOK_AGAIN_SECONDS = 15
GIVE_UP_SECONDS = 3600
NOT_FOUND_GRACE_SECONDS = 120
# Asked to slow down, wait this long and ask again, this many times.
RETRY_SECONDS = 60
RETRIES = 30
# The collider is sampled this densely and seen at this fraction of the target's size: about
# 5 mm between samples on a 3 m room, finer than a pixel at 672 wide.
SAMPLES = 3_000_000
# The near end of a depth panorama's scale, as pano.py writes it.
DEPTH_Z_MIN_M = 0.1
DEPTH_SHRINK = 2


def call(method, path, body=None):
    """One call to the World API, answered as JSON. Told to slow down (429: four worlds at once
    was the most it took on 2026-10-02), it waits and asks again."""
    for attempt in range(RETRIES):
        request = urllib.request.Request(
            f"{API}{path}", method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"WLT-Api-Key": KEY_FILE.read_text().strip(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=120) as answer:
                return json.loads(answer.read())
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == RETRIES - 1:
                raise
            print(f"marble: busy, asking again in {RETRY_SECONDS} s", file=sys.stderr, flush=True)
            time.sleep(RETRY_SECONDS)


def finished(operation_id):
    """The operation once it is done, waiting for it; raises when it failed or never finished."""
    waited = 0
    while waited < GIVE_UP_SECONDS:
        try:
            operation = call("GET", f"/operations/{operation_id}")
        except urllib.error.HTTPError as error:
            # A panorama job is not found for a moment after it starts (404, 2026-10-02).
            if error.code != 404 or waited > NOT_FOUND_GRACE_SECONDS:
                raise
            time.sleep(LOOK_AGAIN_SECONDS)
            waited += LOOK_AGAIN_SECONDS
            continue
        if operation.get("done"):
            if operation.get("error"):
                raise SystemExit(f"marble: {operation['error']}")
            return operation
        print(f"marble: waiting ({waited} s) {operation.get('metadata') or ''}", file=sys.stderr, flush=True)
        time.sleep(LOOK_AGAIN_SECONDS)
        waited += LOOK_AGAIN_SECONDS
    raise SystemExit(f"marble: {operation_id} still not done after {GIVE_UP_SECONDS} s")


def inline_png(path):
    """A PNG file as the API's inline picture."""
    return {"source": "data_base64", "extension": "png", "data_base64": base64.b64encode(path.read_bytes()).decode()}


def paint(room, out, depth_png, z_max, text, seed):
    """Paint a depth panorama (pano.py) into a colour one (pano:depth_to_rgb), saved as the room's
    target picture, so `generate --pano` builds the world from it; what it cost is kept."""
    started = call("POST", "/pano:depth_to_rgb", {
        "depth_pano_image": inline_png(depth_png), "z_min": DEPTH_Z_MIN_M, "z_max": z_max,
        "text_prompt": text, "seed": seed})
    operation = finished(started["operation_id"])
    (out / "paint.json").write_text(json.dumps({"cost": operation.get("cost"), "seed": seed, "z_max": z_max,
                                                "text": text, "operation": operation}, indent=1))
    # The schema puts it at response.pano_url; the API answered with it under assets.imagery
    # (2026-10-02, 80 credits a painting).
    answer = operation["response"]
    url = answer.get("pano_url") or answer["assets"]["imagery"]["pano_url"]
    download(url, folder(room) / f"{room}-target.png")
    print(f"painted, cost {operation.get('cost')}")


def generate(room, out, model, text, pano=False, seed=None):
    """Generate the world from the room's target picture, with words of guidance when given;
    the world as the API returns it. A panorama (`pano`) is taken as one, with its words as given."""
    prompt = {"type": "image", "is_pano": pano, "image_prompt": inline_png(folder(room) / f"{room}-target.png")}
    if text:
        prompt["text_prompt"] = text
    if pano:
        prompt["disable_recaption"] = True
    request = {"display_name": f"farm-factory {room} target", "model": model, "world_prompt": prompt}
    if seed is not None:
        request["seed"] = seed
    started = call("POST", "/worlds:generate", request)
    operation = finished(started["operation_id"])
    world = operation["response"]
    (out / "world.json").write_text(json.dumps({"world": world, "cost": operation.get("cost")}, indent=1))
    return world


def download(url, path):
    """One file from a URL to a path."""
    with urllib.request.urlopen(url, timeout=600) as answer:
        path.write_bytes(answer.read())


def fetch(out):
    """The free parts of the world (collider mesh, panorama, thumbnail, metric scale) into `out`."""
    kept = json.loads((out / "world.json").read_text())
    world = call("GET", f"/worlds/{kept['world']['world_id']}")
    (out / "world.json").write_text(json.dumps({**kept, "world": world}, indent=1))
    assets = world.get("assets") or {}
    wanted = {"collider.glb": (assets.get("mesh") or {}).get("collider_mesh_url"),
              "pano.png": (assets.get("imagery") or {}).get("pano_url"),
              "thumbnail.png": assets.get("thumbnail_url")}
    for name, url in wanted.items():
        if url:
            download(url, out / name)
            print(out / name)
    metric = ((assets.get("splats") or {}).get("semantics_metadata")) or {}
    (out / "metric.json").write_text(json.dumps(metric, indent=1))
    print(f"metric: {metric}")


def splats(out):
    """The world's Gaussian splats as PLY (free), 500k of them, into `out`."""
    world_id = json.loads((out / "world.json").read_text())["world"]["world_id"]
    started = call("POST", f"/worlds/{world_id}:export", {"asset_type": "splats", "format": "ply", "resolution": "500k"})
    operation = started if started.get("done") else finished(started["operation_id"])
    download(operation["response"]["url"], out / "splats.ply")
    print(out / "splats.ply")


def collider_samples(out):
    """Points spread evenly over the collider mesh, in metres, in the world's own camera frame
    (x right, y down, z ahead, the target's camera at the origin), which is MoGe-2's too."""
    import numpy as np
    import trimesh
    metric = json.loads((out / "metric.json").read_text())
    mesh = trimesh.load(out / "collider.glb", force="mesh")
    samples, _ = trimesh.sample.sample_surface_even(mesh, SAMPLES, seed=0)
    return np.asarray(samples) * metric["metric_scale_factor"]


def seen(samples, focal, size):
    """The nearest sample under each pixel of a camera at the origin looking along +z, with focal
    lengths given as shares of the width and height: (points, which pixels saw one)."""
    import numpy as np
    width, height = size
    ahead = samples[samples[:, 2] > 0.05]
    column = (ahead[:, 0] / ahead[:, 2] * focal[0] + 0.5) * width
    row = (ahead[:, 1] / ahead[:, 2] * focal[1] + 0.5) * height
    inside = (column >= 0) & (column < width) & (row >= 0) & (row < height)
    ahead, pixel = ahead[inside], row[inside].astype(int) * width + column[inside].astype(int)
    nearest = np.full(width * height, np.inf)
    np.minimum.at(nearest, pixel, ahead[:, 2])
    winner = ahead[:, 2] <= nearest[pixel]
    points = np.full((width * height, 3), np.nan)
    points[pixel[winner]] = ahead[winner]
    return points.reshape(height, width, 3), np.isfinite(nearest).reshape(height, width)


def depth(room, out):
    """The collider seen from the target's camera, written as depth-marble.npz in depth.py's form.
    The lens is MoGe-2's (depth.npz): Marble keeps its own camera's but does not return it."""
    import numpy as np
    moge = np.load(folder(room) / "depth.npz")
    height, width = moge["points"].shape[:2]
    size = (width // DEPTH_SHRINK, height // DEPTH_SHRINK)
    intrinsics = moge["intrinsics"]
    points, valid = seen(collider_samples(out), (intrinsics[0, 0], intrinsics[1, 1]), size)
    np.savez_compressed(folder(room) / "depth-marble.npz", points=points, valid=valid, intrinsics=intrinsics)
    print(f"depth-marble.npz: {valid.mean():.0%} of {size[0]}x{size[1]} pixels see the collider")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("step", choices=("paint", "generate", "fetch", "depth", "splats"))
    parser.add_argument("--model", default=MODEL, choices=MODELS)
    parser.add_argument("--text", help="words to guide the world beside the picture")
    parser.add_argument("--pano", action="store_true", help="the target picture is a 360° panorama")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--depth-png", type=pathlib.Path, help="paint: pano.py's depth panorama")
    parser.add_argument("--z-max", type=float, help="paint: the depth panorama's far end (pano.py's scales.json)")
    options = parser.parse_args()
    out = folder(options.room) / "marble"
    out.mkdir(exist_ok=True)
    if options.step in ("depth", "splats", "paint"):
        {"depth": lambda: depth(options.room, out), "splats": lambda: splats(out),
         "paint": lambda: paint(options.room, out, options.depth_png, options.z_max, options.text, options.seed)}[options.step]()
        return
    if options.step == "generate":
        world = generate(options.room, out, options.model, options.text, options.pano, options.seed)
        print(world.get("world_id"), world.get("world_marble_url"))
    fetch(out)


if __name__ == "__main__":
    main()
