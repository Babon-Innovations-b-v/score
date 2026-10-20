"""The state export a hosted dashboard reads, built on the store's machine from the local source.

    <out>/manifest.json        {made_at, world, source_commit, format, code_version, bytes, left_out: [{what, why}],
                               cap_mb, written}
    <out>/state.json           WorldState
    <out>/places/<place>.json  {"detail": PlaceDetail, "steps": {stage: StepDetail}, format, code_version};
                               _world.json the world's steps
    <out>/files/<sha>-1280.jpg hero and concept pictures; <sha>-360.jpg thumbnails (the concepts' first, newest 8 a
                               node); <sha>.mp4 accepted films
    <out>/web3d/<place>/       each place's fresh 3D copy (web3d/convert.py): sidecar and preview, then the whole one
    <out>/proposals/           the basket (proposals/exporting.py): its index, each place's details, inputs and 3D copies
                               right after the heroes, the whole 3D copies after the places' own
    <out>/library/            the creator's library when SCORE_LIB_ROOT is set (state/library.py): entries.json, a
                              sound's first takes in files/; its pictures go in <out>/files/ like the steps' (thumbnails
                              after the steps' own, large ones last), then its web 3D copies and prints in files/

Filled in priority order (the JSON, heroes, every node's thumbnails with each node's first before any node's second,
films, then the 3D copies) until the cap (owner, 2026-10-18: the step cards' thumbnails go up first); what did not
fit is named in left_out; `written` lists every file but the manifest in the order it was written, which is the order
the sync uploads them in (sync/client.py). The 3D copies go in last: every sidecar and light preview first, then the
whole copies while they fit (owner, 2026-10-18: the hosted cockpit has 3D too); between the two, every step's own
picture and the breakdown sliders' pictures large, so a place's breakdown is judged without clicking. FileRef urls
stay /files/<sha> and /thumbs/<sha>.jpg, so the templates do not know which source served them.

Every piece is keyed on the exporting code's version (state/versions.py): the bundles and the manifest carry it, so a
code change gives them a new sha the content-addressed sync sends, and the pictures made for the export are kept per
version, so a change to the code drawing them makes them again. `format` is what the hosted side checks on commit.
"""
import json
import pathlib
import shutil
import subprocess

from score.dashboard.proposals import exporting as proposals
from score.dashboard.state import library, sliders, versions
from score.dashboard.state.files import HERO_SIDE, THUMB_SIDE, thumbnail
from score.dashboard.state.models import PlaceDetail, StepDetail

NEWEST_PER_NODE = 8
WORLD_FILE = "_world"
PICTURES = "export-pictures"


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
            "steps": {stage: step.model_dump(by_alias=True) for stage, step in details[1].items()},
            "format": versions.FORMAT, "code_version": versions.exporting()}


def pictures_folder(home):
    """The folder of the pictures made for the export by this code version; older versions' folders deleted."""
    root = pathlib.Path(home) / PICTURES
    current = root / versions.exporting()
    if root.is_dir():
        for old in root.iterdir():
            if old.is_dir() and old != current:
                shutil.rmtree(old)
    current.mkdir(parents=True, exist_ok=True)
    return current


def heroes(world):
    cards = [card for engine in world.engines for style in engine.styles for card in style.places]
    return [*world.concepts.values()] + [card.hero for card in cards if card.hero] + [
        card.still for card in cards if card.still] + [
        style.picture for engine in world.engines for style in engine.styles if style.picture]


def place_pictures(bundles):
    """Each place's concept and its named gaps' pictures, as FileRef dicts."""
    details = [bundle["detail"] for bundle in bundles if bundle["detail"]]
    return [detail["concept"] for detail in details if detail.get("concept")] + [
        gap["picture"] for detail in details for gap in detail.get("gaps") or [] if gap.get("picture")]


def check_pictures(bundles):
    """The picture of every standalone check finding of the places, as FileRef dicts."""
    return [finding["picture"] for bundle in bundles if bundle["detail"]
            for finding in bundle["detail"].get("checks", []) if finding.get("picture")]


def bundle_step(bundle, stage):
    """A place bundle's StepDetail of a stage, or None."""
    found = bundle["steps"].get(stage)
    return StepDetail.model_validate(found) if found else None


def large_step_pictures(bundles):
    """[(what, FileRef dict)] the place pages' breakdowns show large: every step's own picture, then the pictures
    each before and after slider wipes between (state/sliders.py)."""
    found = [(step["node"], step["picture"]) for bundle in bundles for step in bundle["steps"].values()
             if step.get("picture")]
    for bundle in bundles:
        if not bundle["detail"]:
            continue
        detail = PlaceDetail.model_validate(bundle["detail"])
        for pair in sliders.pairs(detail, lambda stage, within=bundle: bundle_step(within, stage)):
            found += [(f"{detail.place}: {pair['words']}", pair[side].model_dump()) for side in ("before", "after")]
    return found


def web3d_copies(source, filler, names):
    """Each place's 3D web copy files of the `names` patterns into the export, while they fit."""
    for place in source.places():
        for pattern in names:
            name = pattern.format(place=place)
            found = source.web3d_file(place, name)
            if found:
                filler.place_copy(found, f"web3d/{place}/{name}", f"3D copy {name}")


def films(world):
    return [card.film for engine in world.engines for style in engine.styles for card in style.places if card.film]


def pictures_by_node(bundles):
    """[(node, [image FileRef, newest output first])], each node's images: its accepted files, the waiting one's, its
    history's thumbnails as named refs."""
    found = []
    for bundle in bundles:
        for step in bundle["steps"].values():
            own = [step["picture"]] if step.get("picture") else []
            images = own + [ref for ref in step["files"] + step["waiting_files"]
                            if ref["kind"] == "image" and ref not in own]
            found.append((step["node"], images[:NEWEST_PER_NODE]))
    return found


def build(source, out, made_at, cap_mb, spend, repo):
    """Write the export of `source` into `out`; its manifest."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    filler = Filler(out, int(cap_mb * 1024 * 1024), pictures_folder(source.home))
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
    for concept in world.concepts.values():  # the tiles' pictures, small, before anything else
        filler.picture(source.file(concept.sha)[1], concept.sha, THUMB_SIDE, f"concept {concept.name}")
    for hero in heroes(world):
        filler.picture(source.file(hero.sha)[1], hero.sha, HERO_SIDE, f"picture {hero.name}")
    proposals.in_export(source.home / "proposals", filler, wholes=False)  # the basket's items, pictures and all
    for picture in place_pictures(bundles):
        filler.picture(source.file(picture["sha"])[1], picture["sha"], HERO_SIDE, f"picture {picture['name']}")
    for found in check_pictures(bundles):
        filler.picture(source.file(found["sha"])[1], found["sha"], HERO_SIDE, f"check {found['name']}")
    nodes = pictures_by_node(bundles)
    for rank in range(NEWEST_PER_NODE):  # each node's first thumbnail before any node's second
        for node, images in nodes:
            if rank < len(images):
                found = source.file(images[rank]["sha"])
                if found:
                    filler.picture(found[1], images[rank]["sha"], THUMB_SIDE, f"{node}: {images[rank]['name']}")
    shelf = library.for_export()
    shelved = library.export_rows(shelf, out, filler) if shelf else []
    if shelf:
        library.export_demos(shelf, out, filler)
    library.export_pictures(shelf, shelved, filler, THUMB_SIDE)
    library.export_takes(shelf, shelved, filler)
    for film in films(world):
        filler.copy(source.file(film.sha)[1], f"{film.sha}.mp4", f"film {film.name}")
    web3d_copies(source, filler, ("{place}.json", "{place}-light.glb"))
    for what, picture in large_step_pictures(bundles):  # the breakdowns' pictures before the whole copies
        found = source.file(picture["sha"])
        if found:
            filler.picture(found[1], picture["sha"], HERO_SIDE, f"{what}: {picture['name']} large")
    web3d_copies(source, filler, ("{place}.glb", "{place}-around.glb"))
    proposals.in_export(source.home / "proposals", filler, wholes=True)
    library.export_pictures(shelf, shelved, filler, HERO_SIDE)
    library.export_three_d(shelf, shelved, filler)
    manifest = {"made_at": made_at, "world": world.world, "source_commit": commit(repo), "format": versions.FORMAT,
                "code_version": versions.exporting(), "bytes": filler.used,
                "left_out": filler.left_out, "cap_mb": cap_mb, "written": filler.written}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest
