"""The model maker (#128, owner 2026-11-16; TRELLIS.2 was better than our picture-made models on 5 of 6 camp props):
place_build's `make`, one prop's model from its picture, made ready for the place and taken into the library.

    make(folder, name, source, material, like=None, height=None) -> the made entry's address and its measures

1. The picture (`picture_of`): `take/<take>` (a Pixal3D take's close-up, work/pixal/<take>.svviews/input.png, put
   back from the library when it is not on this PC), `concept/<n>` (the place's concept cut by its n-th SAM 3 mask,
   objects.json), `like` (the close-up the `like` entry was made from) or a cut-out PNG's path.
2. TRELLIS.2 (generate.py in its own Python, setup.sh) on this PC's card through the card queue, in a memory-capped
   scope; kept under <folder>/made/<name>/, so a second `make` of the same picture is not made again.
3. Set in the place's frame (fit.py): over the library model it replaces (`like`, its turn, scale and spot found by
   covering it best), or `height` metres tall on the floor.
4. Its own paint graded toward the place's palette (grade.py, palette.json's tokens); a group still far from every
   token is named a mismatch, for `surface` to repaint from the library.
5. Sim-ready (sim.py): CoACD hulls (`<id>-hulls.glb`), mass from the hulls and the material class, friction and
   restitution from the class, in its record (`<id>.json`).
6. Taken into score_lib as a draft `model/<name>_trellis.<place>` entry (score-lib take-in --save), its picture and
   TRELLIS.2's commit and weights in its record and provenance; `put` then lays it as any made model.
"""
import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import sys

import numpy as np

from score.stages import place_build
from score.stages.place_build.maker import fit, glb, grade, sim

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENV = "envs/trellis2"  # under PROPS_HOME: setup.sh's
SAMPLES = 20000  # surface points a fit and a grade read
CARD_GB = 10  # TRELLIS.2's card share at the 1024 cascade: 8.6 GB measured with the attention stand-in (2026-11-16)
MEMORY = "20G"  # its RAM cap (the test: 16.2 GB at the most)
SOURCE = "trellis2"  # score_lib config/sources.toml


def props_home():
    return pathlib.Path(os.environ.get("PROPS_HOME") or pathlib.Path.home() / ".score-this-pc")


def env_folder():
    folder = props_home() / ENV
    if not (folder / "ready.json").is_file():
        raise place_build.Refused(f"no model maker at {folder}: run score/stages/place_build/maker/setup.sh")
    return folder


def entry_id(name, place):
    """The made entry's id: `<name>_trellis.<place>`, in the library's id letters."""
    clean = "".join(letter if letter.isalnum() else "_" for letter in name.lower()).strip("_")
    return f"{clean}_trellis.{''.join(letter for letter in place.lower() if letter.isalnum() or letter == '_')}"


def take_picture(take):
    """A Pixal3D take's close-up, put back from the library when this PC lacks it."""
    pixal = props_home() / "work/pixal"
    picture = pixal / f"{take}.svviews/input.png"
    if not picture.is_file():
        sys.path.insert(0, str(REPO / "tools/library"))
        import pixal_takes
        pixal_takes.take_back(take, pixal)
    if not picture.is_file():
        raise place_build.Refused(f"take {take}: no close-up on this PC or in the library")
    return picture


def mask_path(folder, written):
    """A SAM 3 mask's file: as objects.json names it from the place folder, else under the folder's own split/ (the
    split writes its path through the folder's name, `../scene/split/...`, which a copied folder does not have)."""
    named = (folder / written).resolve()
    if named.is_file() or "split/" not in written:
        return named
    return folder / "split" / written.split("split/", 1)[1]


def concept_picture(folder, number, out):
    """The place's concept cut by its `number`-th object's SAM 3 mask, cropped to its box with a margin, as RGBA."""
    from PIL import Image
    folder = pathlib.Path(folder)
    objects = json.loads((folder / "objects.json").read_text())
    found = objects[int(number)]
    concept = Image.open(folder / "concept.png").convert("RGB")
    mask = Image.open(mask_path(folder, found["mask"])).convert("L").resize(concept.size)
    left, top, right, bottom = found["box"]
    margin = int(0.08 * max(right - left, bottom - top))
    box = (max(0, left - margin), max(0, top - margin), min(concept.width, right + margin),
           min(concept.height, bottom + margin))
    cut = concept.crop(box)
    cut.putalpha(mask.crop(box))
    cut.save(out)
    return out


def like_take(like):
    """The take a library model was made from (its provenance's Pixal3D step, or a take entry's own name)."""
    record = place_build.entry_of(place_build.resolved_address(like, place_build.library_root()))
    if record["kind"] == "take":
        return record["title"]
    for step in record["provenance"].get("made_with", []):
        if step.get("by") == "pixal3d":
            return step["what"].split(":")[0].strip()
    raise place_build.Refused(f"{like}: its record names no picture it was made from; give the source")


def picture_of(folder, source, like, work):
    """The cut-out picture `source` names (see the module's step 1) and what it is, in words."""
    if source == "like":
        if not like:
            raise place_build.Refused("source `like` needs --like")
        source = f"take/{like_take(like)}"
    if source.startswith("take/"):
        return take_picture(source[5:]), source
    if source.startswith("concept/"):
        return concept_picture(folder, source[8:], work / "picture.png"), source
    if pathlib.Path(source).is_file():
        return pathlib.Path(source), source
    raise place_build.Refused(f"{source}: not take/<take>, concept/<n>, like or a picture's path")


def generated(picture, out):
    """TRELLIS.2's model of `picture` at `out` (kept when made before); its stats."""
    stats = out.with_suffix(".json")
    if out.is_file() and stats.is_file():
        return json.loads(stats.read_text())
    env = env_folder()
    command = ["systemd-run", "--user", "--scope", "-q", "-p", f"MemoryMax={MEMORY}", "-p", "MemorySwapMax=0",
               sys.executable, str(REPO / "tools/cloud/backends/card_queue.py"), "run", "--job", f"make-{out.parent.name}",
               "--card-gb", str(CARD_GB), "--memory-gb", MEMORY.rstrip("G"), "--priority", "other", "--",
               str(env / "venv/bin/python"), "-I", str(HERE / "generate.py"), str(env), str(picture), str(out)]
    done = subprocess.run(command, capture_output=True, text=True, env={**os.environ, "MALLOC_ARENA_MAX": "2"})
    (out.parent / "generate.log").write_text(done.stdout + done.stderr)
    if done.returncode != 0 or not stats.is_file():
        raise place_build.Refused(f"TRELLIS.2 failed (exit {done.returncode}): {(done.stderr or done.stdout)[-400:]}")
    return json.loads(stats.read_text())


def surface_points(path):
    """Points spread evenly over a GLB's surface (its node transforms applied), with their texture coordinates."""
    import trimesh
    mesh = trimesh.load(str(path), force="mesh")
    points, faces = trimesh.sample.sample_surface_even(mesh, SAMPLES, seed=7)
    if len(points) < SAMPLES // 4:
        points, faces = trimesh.sample.sample_surface(mesh, SAMPLES, seed=7)
    uv = getattr(mesh.visual, "uv", None)
    if uv is None:
        return np.asarray(points), None
    corners = mesh.triangles[faces]
    weights = trimesh.triangles.points_to_barycentric(corners, points)
    return np.asarray(points), np.einsum("ij,ijk->ik", weights, uv[mesh.faces[faces]])


def like_points(folder, like):
    """Surface points of the library model `like`, in its own frame, from its glTF (fetched into the place's assets)."""
    _, record, copied = place_build.fetch(folder, like)
    models = [name for name, info in record["files"].items()
              if info.get("role") in place_build.GLTF_ROLES and pathlib.Path(name).suffix in (".glb", ".gltf")]
    if not models:
        raise place_build.Refused(f"{like}: no glTF model to fit over")
    return surface_points(copied[min(models, key=place_build.finished_first)])[0]


def placed(raw, folder, like, height):
    """The raw model's GLB document and binary set in the place's frame; how it was set."""
    document, binary = glb.read(raw)
    points = surface_points(raw)[0]
    if like:
        matrix, how = fit.fitted_matrix(points, like_points(folder, like))
        how["like"] = like
    elif height:
        matrix, how = fit.height_matrix(points, float(height)), {"height_m": float(height)}
    else:
        raise place_build.Refused("give --like (the library model it replaces) or --height (metres)")
    return glb.with_root_matrix(document, matrix), binary, how


def painted(document, binary, path, tokens):
    """The binary with its base colour picture graded toward `tokens`; each group's move. `path` is the placed GLB
    (its texture coordinates are read from it)."""
    import io
    from PIL import Image
    index = glb.base_colour_image(document)
    if index is None or not tokens:
        return binary, []
    picture = Image.open(io.BytesIO(glb.image(document, binary, index)))
    mode = picture.mode
    rgba = np.asarray(picture.convert("RGBA"), dtype=np.float64) / 255
    _, uv = surface_points(path)
    height, width = rgba.shape[:2]
    columns = np.clip(np.round((uv[:, 0] % 1.0) * (width - 1)), 0, width - 1).astype(int)
    rows = np.clip(np.round((1 - uv[:, 1] % 1.0) * (height - 1)), 0, height - 1).astype(int)
    moved, report = grade.graded(rgba[..., :3], rgba[rows, columns, :3], tokens)
    out = np.concatenate([moved, rgba[..., 3:]], -1)
    encoded = io.BytesIO()
    Image.fromarray(np.round(out * 255).astype(np.uint8), "RGBA").convert(mode).save(encoded, "PNG")
    document["images"][index]["mimeType"] = "image/png"
    return glb.with_image(document, binary, index, encoded.getvalue()), report


def hulls_written(final, out):
    """CoACD's hulls of the final model written as one GLB of hull meshes (the model's frame); the hulls."""
    import trimesh
    mesh = trimesh.load(str(final), force="mesh")
    hulls = sim.hulls_of(mesh.vertices, mesh.faces)
    scene = trimesh.Scene()
    for number, (points, triangles) in enumerate(hulls):
        scene.add_geometry(trimesh.Trimesh(points, triangles, process=False), geom_name=f"hull_{number}")
    scene.export(str(out))
    return hulls, np.ptp(mesh.vertices, 0)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def taken_in(entry, files, title, made_with, work):
    """The made files committed to score_lib as a draft model entry (score-lib take-in --save); its address."""
    sys.path.insert(0, str(REPO / "tools/library"))
    import library_files
    values = library_files.settings()
    root = values.get("SCORE_LIB_ROOT")
    if not root:
        raise place_build.Refused("no library is configured (SCORE_LIB_ROOT)")
    with open(pathlib.Path(root) / ".git" / "score-make.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # makes side by side take in one at a time (one checkout, one push each)
        return saved(values, root, entry, files, title, made_with, work)


def saved(values, root, entry, files, title, made_with, work):
    """The take-in itself, under the caller's lock; the entry's address."""
    import pixal_takes
    pulled = subprocess.run(["git", "-C", root, "pull", "-q", "--ff-only"], capture_output=True, text=True)
    if pulled.returncode != 0:
        raise place_build.Refused(f"the library's checkout could not be brought forward: {pulled.stderr[-300:]}")
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    listing = {"world": "world1", "commit": commit, "taken_from": "score place_build make (TRELLIS.2 on this PC)",
               "entries": [{"kind": "model", "id": entry, "title": title,
                            "files": {name: {"path": str(path), "from": f"made/{path.name}"}
                                      for name, path in files.items()},
                            "made_with": made_with, "tags": {"maker": ["trellis2"]}}]}
    asked, report = work / "take-in.json", work / "take-in-report.json"
    asked.write_text(json.dumps(listing, indent=1))
    report.unlink(missing_ok=True)
    done = pixal_takes.library_command(values, "take-in", str(asked), "--save", "--report", str(report))
    if not report.is_file():
        raise place_build.Refused(f"score-lib take-in exited {done.returncode}: {(done.stderr or done.stdout)[-400:]}")
    answer = json.loads(report.read_text())
    if answer.get("refused"):
        raise place_build.Refused(f"score-lib refused the entry: {answer['refused']}")
    if answer.get("saved") and not answer["saved"].get("pushed"):
        raise place_build.Refused(f"score-lib wrote the entry but did not push it: {answer['saved']}")
    return place_build.resolved_address(f"model/{entry}", root)


def make(folder, name, source, material, like=None, height=None):
    """One prop's model made with TRELLIS.2 from `source`'s picture, set in the place (over `like`, or `height`
    metres tall), graded to its palette, made sim-ready and taken into score_lib; its address and measures."""
    try:
        sim.material(material)
    except ValueError as why:
        raise place_build.Refused(str(why)) from why
    folder = pathlib.Path(folder)
    place = place_build.record_of(folder)["place"]
    entry = entry_id(name, place)
    work = folder / "made" / entry
    work.mkdir(parents=True, exist_ok=True)
    picture, said = picture_of(folder, source, like, work)
    raw = work / "trellis.glb"
    stats = generated(picture, raw)
    document, binary, how = placed(raw, folder, like, height)
    final = work / f"{entry}-final.glb"
    glb.write(final, document, binary)
    palette = folder / place_build.PALETTE
    tokens = json.loads(palette.read_text()).get("tokens", {}) if palette.is_file() else {}
    binary, groups = painted(document, binary, final, tokens)
    glb.write(final, document, binary)
    hulls, size = hulls_written(final, work / f"{entry}-hulls.glb")
    physics = sim.physical(hulls, material)
    record = {"maker": SOURCE, "picture": {"source": said, "sha256": sha256(picture)}, "trellis2": stats,
              "fit": how, "size_m": [round(float(side), 3) for side in size], "grade": groups,
              "mismatch": [group for group in groups if group["mismatch"]], "physics": physics,
              "hulls_file": f"{entry}-hulls.glb"}
    (work / f"{entry}.json").write_text(json.dumps(record, indent=1))
    files = {path.name: path for path in (final, work / f"{entry}-hulls.glb", work / f"{entry}.json")}
    made_with = [{"what": f"{name}: its shape and paint, TRELLIS.2 (1024 cascade, seed {stats['seed']}) from {said}",
                  "source": SOURCE},
                 {"what": "set in the place, its paint graded to the place's palette, CoACD hulls and mass by score "
                          "place_build make", "source": "score"}]
    title = f"{name.replace('_', ' ').capitalize()} (TRELLIS.2, {place})"
    address = taken_in(entry, files, title, made_with, work)
    return {"address": address, "fit": how, "mass_kg": physics["mass_kg"], "hulls": physics["hulls"],
            "mismatch": record["mismatch"], "size_m": record["size_m"], "folder": str(work)}
