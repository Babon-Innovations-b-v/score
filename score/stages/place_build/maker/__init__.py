"""The model maker (#128, owner 2026-11-16; TRELLIS.2 was better than our picture-made models on 5 of 6 camp props):
place_build's `make`, one prop's model from its picture, made ready for the place and taken into the library.

    make(folder, name, source, material, like=None, height=None) -> the made entry's address and its measures

1. The picture (`picture_of`): `take/<take>` (a Pixal3D take's close-up, work/pixal/<take>.svviews/input.png, put
   back from the library when it is not on this PC), `concept/<n>` (the place's concept cut by its n-th SAM 3 mask,
   objects.json), `like` (the close-up the `like` entry was made from) or a cut-out PNG's path.
2. TRELLIS.2 (generate.py in its own Python, setup.sh) on this PC's card through the card queue, in a memory-capped
   scope; kept under <folder>/made/<name>/, so a second `make` of the same picture is not made again. Its decoded
   mesh before the remesh is kept beside it and set in the place with it (`decoded_placed`): the shape its seams are
   shaded from (bake.seamed, #159).
3. Set in the place's frame (fit.py): over the library model it replaces (`like`, its turn, scale and spot found by
   covering it best), or `height` metres tall on the floor. Its mesh repaired, its shape kept (repair.py: collapsed,
   repeated and membrane faces out, two solids touching along an edge parted, hidden crumbs out, wound outward).
4. Its own paint graded toward the place's palette (grade.py, palette.json's tokens); a group still far from every
   token is named a mismatch. A graded paint is still not a library surface: `put` lays the made model's paint parts
   (grade.parts) each as the palette variant nearest its colour (place_build/finished).
5. Sim-ready (sim.py, #161's rules): CoACD hulls (`<id>-hulls.glb`), friction and restitution its material class's
   row (NVIDIA's table), and a real-world mass Claude gives from its picture, words and size, held to NVIDIA's bulk
   density band, in its record (`<id>.json`). A finished model's parts are weighed and classed each (sim.py).
6. Taken into score_lib as a draft `model/<name>_trellis.<place>` entry (score-lib take-in --save), its picture and
   TRELLIS.2's commit and weights in its record and provenance; `put` then lays it as any made model. With
   `take_in=False` (the prop benchmark, #163) nothing goes into score_lib: the made files stay in the work folder and
   the address is None.

The size it is set at: `like`'s, `height` metres tall, or `size` (wide, deep, tall metres: each side the model's,
each axis at most fit.STRETCH off the uniform scale, fit.size_matrix, #170), first turned to the heading its picture,
the row's close-up, shows (fit.headed, #166).
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
from score.stages.place_build.maker import fit, front, glb, grade, repair, sim

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENV = "envs/trellis2"  # under PROPS_HOME: setup.sh's
SAMPLES = 20000  # surface points a fit and a grade read
CARD_GB = 13.5  # TRELLIS.2's card share: the queue's whole card (card_queue.BUDGET_GB). generate.py's allocator may
# take the card's free memory (generate.capped); a printer box measured 13.15 GB with the lean decoders (#169)
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
    if not found.get("mask") or not mask_path(folder, found["mask"]).is_file():
        raise place_build.Refused(f"concept/{number}: no SAM 3 mask on this PC ({found.get('mask')}); a crop not cut "
                                  "out of the concept is made as its background too (`split --nouns`)")
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


BOX_FILL = 0.995  # a picture whose opaque pixels fill this share of their own box is a crop, not a cut-out


def cut_out(picture):
    """The picture's path when it is cut out of its background (transparent round a shape that is not its own box);
    refused otherwise: TRELLIS.2 makes an uncut crop's background as part of the model (#156: the capsule's throttle,
    levers on a console top, came out a cube)."""
    from PIL import Image
    image = Image.open(picture)
    if "A" not in image.getbands():
        raise place_build.Refused(f"{picture}: no transparency, a crop never cut out; cut it by a SAM 3 mask "
                                  "(`split --nouns`, then concept/<n>)")
    opaque = np.asarray(image.getchannel("A")) > 127
    rows, columns = np.nonzero(opaque)
    if not len(rows):
        raise place_build.Refused(f"{picture}: wholly transparent")
    box = (np.ptp(rows) + 1) * (np.ptp(columns) + 1)
    if opaque.all() or len(rows) >= BOX_FILL * box:
        raise place_build.Refused(f"{picture}: its opaque part is a rectangle, a crop never cut out; cut it by a SAM 3 "
                                  "mask (`split --nouns`, then concept/<n>)")
    return picture


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
        return cut_out(concept_picture(folder, source[8:], work / "picture.png")), source
    if pathlib.Path(source).is_file():  # said by its name only: a record is public, a path on this PC is not
        return cut_out(pathlib.Path(source)), f"the picture {pathlib.Path(source).name}"
    raise place_build.Refused(f"{source}: not take/<take>, concept/<n>, like or a picture's path")


FLAT_SIDE = 0.005  # metres: a made model whose thinnest side is under this and FLAT_SHARE of its longest is a card
FLAT_SHARE = 0.02
FULL_SIZE = 2.0  # metres: a model this big or bigger (its longest side) is made at generate.FACES
LEAST_FACES = 20000  # faces no made model goes under, however small


def flat_card(size):
    """Whether a made model's sides (m) are a flat card's, not a solid's (#154: the capsule's stick came out 1 mm
    thick and was taken in)."""
    sides = sorted(float(side) for side in size)
    return sides[0] < FLAT_SIDE and sides[0] < FLAT_SHARE * sides[-1]


def faces_for(size):
    """The faces a model `size` metres across (its longest side) is made at: generate.FACES at FULL_SIZE and over,
    else the same faces a square metre of its surface (FACES times its size over FULL_SIZE, squared), never under
    LEAST_FACES; a model of unknown size at FACES."""
    from score.stages.place_build.maker import generate
    if not size:
        return generate.FACES
    return int(max(LEAST_FACES, min(generate.FACES, generate.FACES * (float(size) / FULL_SIZE) ** 2)))


def size_of(folder, like, height, size=None):
    """The longest side (m) the model will stand at in the place: `like`'s box, else `height`, else `size`'s longest
    side; None when none is given."""
    if like:
        points = np.asarray(like_points(folder, like))
        return float(np.ptp(points, axis=0).max()) if len(points) else None
    if height:
        return float(height)
    return max(float(side) for side in size) if size else None


def generated(picture, out, faces=None):
    """TRELLIS.2's model of `picture` at `out` (kept when made before) at `faces` (faces_for); its stats."""
    stats = out.with_suffix(".json")
    if out.is_file() and stats.is_file():
        return json.loads(stats.read_text())
    env = env_folder()
    command = ["systemd-run", "--user", "--scope", "-q", "-p", f"MemoryMax={MEMORY}", "-p", "MemorySwapMax=0",
               sys.executable, str(REPO / "tools/cloud/backends/card_queue.py"), "run", "--job", f"make-{out.parent.name}",
               "--card-gb", str(CARD_GB), "--memory-gb", MEMORY.rstrip("G"), "--priority", "other", "--",
               str(env / "venv/bin/python"), "-I", str(HERE / "generate.py"), str(env), str(picture), str(out),
               str(faces or faces_for(None))]
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


def close_up_view(size):
    """The camera turn and look-down (degrees) the prop route's close-up of a row of `size` is drawn from
    (tools/props/closeup/check.py: turned TURN_DEGREES, looking down look_down; a row that lies flat from straight
    above, unturned)."""
    from score.stages.props import prop_data
    with prop_data.tools("props/closeup"):
        import check
    return (0.0 if check.lies_flat(size) else check.TURN_DEGREES), check.look_down(size)


def sized_matrix(points, picture, size, raw, words):
    """`points` (the raw model `raw`'s) turned to the heading `picture` (the row's close-up, cut out) shows, the turns
    its outline leaves open decided by its content (front.picked, #192: the object's `words` given), then scaled to
    `size` (fit.headed, fit.size_matrix); how it was set."""
    from PIL import Image
    image = Image.open(picture)
    if "A" not in image.getbands():
        raise place_build.Refused(f"{picture}: no transparency, so no outline to turn the model by (a close-up cut "
                                  "out of its background)")
    cut = np.asarray(image.getchannel("A")) > 127
    turn, down = close_up_view(size)
    heading, how = fit.headed(points, cut, turn, down,
                              lambda matrices: front.picked(words, raw, picture, cut, turn, down, matrices))
    matrix, stretched = fit.size_matrix(fit.applied(heading, points), size)
    return matrix @ heading, {**how, **stretched}


def placed(raw, folder, like, height, size=None, picture=None, words=None):
    """The raw model's GLB document and binary set in the place's frame (at a `size`, turned as its close-up
    `picture` of the object's `words` shows it); how it was set."""
    document, binary = glb.read(raw)
    points = surface_points(raw)[0]
    if like:
        matrix, how = fit.fitted_matrix(points, like_points(folder, like))
        how["like"] = like
    elif height:
        matrix, how = fit.height_matrix(points, float(height)), {"height_m": float(height)}
    elif size:
        matrix, how = sized_matrix(points, picture, size, raw, words)
        how["size_m"] = [float(side) for side in size]
    else:
        raise place_build.Refused("give --like (the library model it replaces), --height (metres) or --size "
                                  "(wide,deep,tall metres)")
    return glb.with_root_matrix(document, matrix), binary, how


def decoded_file(work):
    """Where make keeps a model's decoded mesh as set in the place: <work>/<entry>-decoded.glb, `work` the model's
    made/<entry> folder (scene_package.shade_of reads it there, #209)."""
    return pathlib.Path(work) / f"{pathlib.Path(work).name}-decoded.glb"


def decoded_placed(raw, document, out):
    """The raw model's decoded mesh (generate.decoded_path, kept when it was made) set in the place as the placed
    model's `document` is, under its root matrix, written at `out` (bake.seamed shades the model's seams from it,
    #159); False where the raw model kept none (made before it was kept)."""
    from score.stages.place_build.maker import generate
    found = generate.decoded_path(pathlib.Path(raw))
    if not found.is_file():
        return False
    shape, data = glb.read(found)
    glb.write(out, glb.with_root_matrix(shape, glb.root_matrix(document)), data)
    return True


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
    with open(lock_file(root), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # makes side by side take in one at a time (one checkout, one push each)
        return saved(values, root, entry, files, title, made_with, work)


def lock_file(root):
    """The take-in lock of the library checkout at `root`, in its repository's shared git folder, so a checkout that
    is a git worktree (its .git a file) locks with every other checkout of that repository."""
    found = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True)
    if found.returncode != 0:
        raise place_build.Refused(f"the library at {root} is no git checkout: {found.stderr[-300:]}")
    return pathlib.Path(found.stdout.strip()) / "score-make.lock"


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


def make(folder, name, source, material, like=None, height=None, size=None, take_in=True):
    """One prop's model made with TRELLIS.2 from `source`'s picture, set in the place (over `like`, `height` metres
    tall, or at `size`), graded to its palette, made sim-ready and taken into score_lib unless not `take_in`; its
    address (None when not taken in) and measures."""
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
    stats = generated(picture, raw, faces_for(size_of(folder, like, height, size)))
    words = name.replace("_", " ")
    document, binary, how = placed(raw, folder, like, height, size, picture, words)
    document, binary, mended = repair.repaired_glb(document, binary)
    final = work / f"{entry}-final.glb"
    glb.write(final, document, binary)
    decoded_placed(raw, document, decoded_file(work))
    palette = folder / place_build.PALETTE
    tokens = json.loads(palette.read_text()).get("tokens", {}) if palette.is_file() else {}
    binary, groups = painted(document, binary, final, tokens)
    glb.write(final, document, binary)
    hulls, size = hulls_written(final, work / f"{entry}-hulls.glb")
    if flat_card(size):
        raise place_build.Refused(f"{name}: TRELLIS.2 made a flat card {', '.join(f'{side:.3f}' for side in size)} m, "
                                  "not a solid; nothing taken in (a sharper cut-out or another picture)")
    mass = sim.weighed(words, size, [{"words": words, "class": material, "share": 1.0}], picture)
    physics = sim.physical(hulls, [material] * len(hulls),
                           [{"words": words, "class": material, "share": 1.0, "kg": round(mass[0], 4)}], size)
    record = {"maker": SOURCE, "picture": {"source": said, "sha256": sha256(picture)}, "trellis2": stats,
              "fit": how, "repair": mended, "size_m": [round(float(side), 3) for side in size], "grade": groups,
              "mismatch": [group for group in groups if group["mismatch"]], "physics": physics,
              "hulls_file": f"{entry}-hulls.glb"}
    (work / f"{entry}.json").write_text(json.dumps(record, indent=1))
    files = {path.name: path for path in (final, work / f"{entry}-hulls.glb", work / f"{entry}.json")}
    made_with = [{"what": f"{name}: its shape and paint, TRELLIS.2 (1024 cascade, seed {stats['seed']}) from {said}",
                  "source": SOURCE},
                 {"what": "set in the place, its paint graded to the place's palette, CoACD hulls and mass by score "
                          "place_build make", "source": "score"}]
    title = f"{name.replace('_', ' ').capitalize()} (TRELLIS.2, {place})"
    address = taken_in(entry, files, title, made_with, work) if take_in else None
    return {"address": address, "fit": how, "mass_kg": physics["mass_kg"], "hulls": physics["hulls"],
            "mismatch": record["mismatch"], "size_m": record["size_m"], "folder": str(work)}
