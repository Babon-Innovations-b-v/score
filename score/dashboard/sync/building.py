"""The state export a hosted dashboard reads, built on the store's machine from the local source.

    <out>/manifest.json        {made_at, world, source_commit, bytes, left_out: [{what, why}], cap_mb, written}
    <out>/state.json           WorldState
    <out>/places/<place>.json  {"detail": PlaceDetail, "steps": {stage: StepDetail}}; _world.json the world's steps
    <out>/files/<sha>-1280.jpg hero pictures; <sha>-360.jpg thumbnails (newest 8 a node); <sha>.mp4 accepted films
    <out>/web3d/<place>/       each place's fresh 3D copy (web3d/convert.py): sidecar and preview, then the whole one
    <out>/library/            the creator's library when SCORE_LIB_ROOT is set (state/library.py): entries.json, a
                              sound's first takes in files/; its pictures go in <out>/files/ like the steps' (thumbnails
                              after the steps' own, large ones last)

Filled in priority order (the JSON, heroes, every node's thumbnails with each node's first before any node's second,
films, then the 3D copies) until the cap (owner, 2026-10-18: the step cards' thumbnails go up first); what did not
fit is named in left_out; `written` lists every file but the manifest in the order it was written, which is the order
the sync uploads them in (sync/client.py). The 3D copies go in last: every sidecar and light preview first, then the
whole copies while they fit (owner, 2026-10-18: the hosted cockpit has 3D too). FileRef urls stay /files/<sha>
and /thumbs/<sha>.jpg, so the templates do not know which source served them.
"""
import json
import pathlib
import shutil
import subprocess

from score.dashboard.state import library
from score.dashboard.state.files import HERO_SIDE, THUMB_SIDE, thumbnail

NEWEST_PER_NODE = 8
WORLD_FILE = "_world"


def commit(repo):
    """The repository's commit, or "" when git cannot say."""
    done = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


class Filler:
    """Adds files to the export's folder until the cap, naming what did not fit."""

    def __init__(self, out, cap_bytes, thumbs):
        self.out = out
        self.files = out / "files"
        self.files.mkdir(parents=True, exist_ok=True)
        self.cap = cap_bytes
        self.thumbs = thumbs
        self.used = 0
        self.left_out = []
        self.written = []

    def wrote(self, path, size):
        """Count a file written into the export and keep its place in the upload order."""
        self.used += size
        self.written.append(path.relative_to(self.out).as_posix())

    def room(self, size, what):
        if self.used + size > self.cap:
            self.left_out.append({"what": what, "why": "over the export's cap"})
            return False
        self.used += size
        return True

    def copy(self, source, name, what):
        target = self.files / name
        if target.exists():
            return
        if self.room(pathlib.Path(source).stat().st_size, what):
            shutil.copyfile(source, target)
            self.written.append(target.relative_to(self.out).as_posix())

    def place_copy(self, source, target, what):
        """A file into the export at `target` (relative), when it fits."""
        target = self.files.parent / target
        if target.exists() or not self.room(pathlib.Path(source).stat().st_size, what):
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        self.written.append(target.relative_to(self.out).as_posix())

    def picture(self, source, sha, side, what):
        target = self.files / f"{sha}-{side}.jpg"
        if target.exists():
            return
        made = thumbnail(source, self.thumbs / f"{sha}-{side}.jpg", side)
        if self.room(made.stat().st_size, what):
            shutil.copyfile(made, target)
            self.written.append(target.relative_to(self.out).as_posix())


def write_json(path, model):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(by_alias=True) if hasattr(model, "model_dump_json") else json.dumps(model))
    return path.stat().st_size


def step_details(source, place, rows):
    """{stage: StepDetail} of every row at a place (None: the world's rows)."""
    found = {}
    for row in rows:
        detail = source.step_detail(place, row.name)
        if detail is not None:
            found[row.name] = detail
    return found


def place_bundle(details):
    return {"detail": details[0].model_dump(by_alias=True) if details[0] else None,
            "steps": {stage: step.model_dump(by_alias=True) for stage, step in details[1].items()}}


def heroes(world):
    return [card.hero for engine in world.engines for style in engine.styles for card in style.places if card.hero] + [
        style.picture for engine in world.engines for style in engine.styles if style.picture]


def films(world):
    return [card.film for engine in world.engines for style in engine.styles for card in style.places if card.film]


def pictures_by_node(bundles):
    """[(node, [image FileRef, newest output first])], each node's images: its accepted files, the waiting one's, its
    history's thumbnails as named refs."""
    found = []
    for bundle in bundles:
        for step in bundle["steps"].values():
            images = [ref for ref in step["files"] + step["waiting_files"] if ref["kind"] == "image"]
            found.append((step["node"], images[:NEWEST_PER_NODE]))
    return found


def build(source, out, made_at, cap_mb, spend, repo):
    """Write the export of `source` into `out`; its manifest."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    filler = Filler(out, int(cap_mb * 1024 * 1024), source.home / "thumbs")
    world = source.world_state(spend)
    world.made_at, world.source = made_at, f"export {made_at}"
    filler.wrote(out / "state.json", write_json(out / "state.json", world))
    bundles = [place_bundle((None, step_details(source, None, source.world_rows())))]
    world_file = out / "places" / f"{WORLD_FILE}.json"
    filler.wrote(world_file, write_json(world_file, bundles[0]))
    for place in source.places():
        bundle = place_bundle((source.place_detail(place), step_details(source, place, source.place_rows(place))))
        filler.wrote(out / "places" / f"{place}.json", write_json(out / "places" / f"{place}.json", bundle))
        bundles.append(bundle)
    for hero in heroes(world):
        filler.picture(source.file(hero.sha)[1], hero.sha, HERO_SIDE, f"picture {hero.name}")
    nodes = pictures_by_node(bundles)
    for rank in range(NEWEST_PER_NODE):  # each node's first thumbnail before any node's second
        for node, images in nodes:
            if rank < len(images):
                found = source.file(images[rank]["sha"])
                if found:
                    filler.picture(found[1], images[rank]["sha"], THUMB_SIDE, f"{node}: {images[rank]['name']}")
    shelf = library.for_export()
    shelved = library.export_rows(shelf, out, filler) if shelf else []
    library.export_pictures(shelf, shelved, filler, THUMB_SIDE)
    library.export_takes(shelf, shelved, filler)
    for film in films(world):
        filler.copy(source.file(film.sha)[1], f"{film.sha}.mp4", f"film {film.name}")
    for names in (("{place}.json", "{place}-light.glb"), ("{place}.glb",)):
        for place in source.places():
            for pattern in names:
                name = pattern.format(place=place)
                found = source.web3d_file(place, name)
                if found:
                    filler.place_copy(found, f"web3d/{place}/{name}", f"3D copy {name}")
    library.export_pictures(shelf, shelved, filler, HERO_SIDE)
    manifest = {"made_at": made_at, "world": world.world, "source_commit": commit(repo), "bytes": filler.used,
                "left_out": filler.left_out, "cap_mb": cap_mb, "written": filler.written}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest
