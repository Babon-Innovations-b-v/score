"""The library the cockpit shows: a creator's library of locked, reusable parts, read through one small interface.

    library()   # local: the library folder SCORE_LIB_ROOT (its blob folder SCORE_LIB_BLOBS_DIR); hosted: the export's
                # library/ part; None when there is no library

An entry is `<kind>/<id>@<version>` with `entries/<kind>/<id>/<version>/entry.json` (title, picture, files, provenance,
tags, state draft/locked/withdrawn); file bytes live in a blob folder as blobs/<sha[:2]>/<sha>. Nothing of the library's
own code is imported here and no entry data is kept in this repository: the folder is the creator's, read only.
"""
import json
import pathlib
import posixpath
import re

from pydantic import BaseModel

from score.dashboard.state.files import HERO_SIDE, SHA, THUMB_SIDE, thumbnail

KINDS = [("model", "Models"), ("surface", "Surfaces"), ("effect", "Effects"), ("light", "Lights"),
         ("sound", "Sound"), ("character", "Characters"), ("ground", "Ground"), ("kit", "Kits"),
         ("algorithm", "Algorithms"), ("layer", "Layers"), ("place", "Places")]
WHAT = {"model": "a model", "surface": "a surface and the material a place writes for it",
        "effect": "a particle emitter with its settings and one baked clip",
        "light": "a sky with the lights that draw it",
        "sound": "a sound source with its takes and levels", "character": "a body look or a dress",
        "ground": "a planet's terrain or one place's ground cut from it", "kit": "a place's kit of pieces",
        "algorithm": "an engine algorithm with its settings, preset, tests and run line",
        "layer": "one layer of one place", "place": "a place's root, its layers, plan and cast"}
STATES = ("draft", "locked", "withdrawn")
ADDRESS = re.compile(r"^(?P<kind>[a-z]+)/(?P<id>[a-z0-9_]+(\.[a-z0-9_]+)?)@(?P<version>[1-9][0-9]*)$")
MAX_TAKES = 4  # a sound's takes sent to the hosted cockpit
EXPORT_ROWS = "library/entries.json"
CHOSEN = {}  # the library made for the current settings


class FileOf(BaseModel):
    name: str
    sha: str
    bytes: int = 0


class LibraryEntry(BaseModel):
    """One entry as the pages show it."""
    address: str
    kind: str
    entry_id: str
    version: int
    title: str
    state: str
    locked: str | None = None
    picture: str | None = None  # the picture's sha
    world: str | None = None
    place: str | None = None  # the place it came from
    node: str | None = None  # the step that made it, `stage@place` or a world stage
    source: str = ""  # where it was read from, in words, when no step made it
    commit: str | None = None
    seen_in: list[str] = []
    tags: dict[str, list] = {}
    requires: list[str] = []
    takes: list[FileOf] = []  # a sound's recordings
    glb: FileOf | None = None


def kind_label(kind):
    return dict(KINDS).get(kind, kind.capitalize())


def sentence(entry):
    """What the entry is, in one sentence."""
    said = WHAT.get(entry.kind, f"a {entry.kind}")
    said = said[0].upper() + said[1:]
    if entry.place:
        said += f", made for {entry.place.replace('_', ' ')}"
    others = [place for place in entry.seen_in if place != entry.place]
    if others:
        said += f", used in {len(others)} other place{'s' if len(others) > 1 else ''}"
    return said + "."


def step_of(node):
    """(place or None, stage) of a step node `stage@place` or a world stage."""
    stage, _, place = node.partition("@")
    return (place or None), stage


def step_url(node):
    place, stage = step_of(node)
    return f"/place/{place}/step/{stage}/" if place else f"/world/step/{stage}/"


def entry_url(entry):
    return f"/library/{entry.kind}/{entry.entry_id}/{entry.version}/"


# --- reading one entry.json ------------------------------------------------------------------------------------

def picture_sha(record):
    named = (record.get("picture") or {}).get("file") or ""
    return (record.get("files", {}).get(named) or {}).get("sha256")


def files_of_role(record, role, suffixes):
    return [FileOf(name=name, sha=described["sha256"], bytes=described.get("bytes", 0))
            for name, described in sorted(record.get("files", {}).items())
            if described.get("role") == role and posixpath.splitext(name)[1].lower() in suffixes]


def made_by_node(provenance):
    """The step that made an entry: its node, or an algorithm's first node."""
    return provenance.get("node") or next(iter(provenance.get("nodes") or []), None)


def entry_of(record):
    """A LibraryEntry from one entry.json record."""
    provenance = record.get("provenance") or {}
    glbs = files_of_role(record, "gltf", (".glb",))
    return LibraryEntry(
        address=record["address"], kind=record["kind"], entry_id=record["id"], version=record["version"],
        title=record.get("title") or record["id"], state=record["state"], locked=record.get("locked"),
        picture=picture_sha(record), world=provenance.get("world"), place=provenance.get("place"),
        node=made_by_node(provenance), source=provenance.get("source") or "", commit=provenance.get("commit"),
        seen_in=record.get("seen_in") or [], tags=record.get("tags") or {}, requires=record.get("requires") or [],
        takes=files_of_role(record, "audio", (".ogg", ".wav", ".mp3", ".flac")), glb=glbs[0] if glbs else None)


def kind_order(entry):
    return ([kind for kind, _ in KINDS].index(entry.kind) if entry.kind in dict(KINDS) else len(KINDS),
            entry.entry_id, entry.version)


# --- the two sources -------------------------------------------------------------------------------------------

class Library:
    """What both sources share: the entries, one entry by address, and which files a page may serve."""

    def entries(self):
        raise NotImplementedError

    def entry(self, address):
        return self.by_address().get(address)

    def by_address(self):
        return {entry.address: entry for entry in self.entries()}

    def listed_files(self):
        """{sha: listed name} of every file the pages may serve: pictures, takes, GLBs."""
        found = {}
        for entry in self.entries():
            if entry.picture:
                found[entry.picture] = "picture.png"
            for each in [*entry.takes, *([entry.glb] if entry.glb else [])]:
                found[each.sha] = each.name
        return found


class LocalLibrary(Library):
    """A library folder beside the cockpit, read only; entries re-read when its index changes."""

    name = "local"

    def __init__(self, root, blobs, thumbs):
        self.root = pathlib.Path(root).expanduser()
        self.blobs = pathlib.Path(blobs).expanduser() if blobs else None
        self.thumbs = pathlib.Path(thumbs)
        self.kept = {"signature": None, "entries": [], "files": {}}

    def signature(self):
        """When the library's index was last written: a lock or an export rebuilds it."""
        folder = self.root / "index"
        return tuple(sorted((path.name, path.stat().st_mtime_ns) for path in folder.glob("*.json"))) \
            if folder.is_dir() else ()

    def entries(self):
        signature = self.signature()
        if self.kept["signature"] != signature:
            paths = (self.root / "entries").glob("*/*/*/entry.json")
            found = sorted((entry_of(json.loads(path.read_text())) for path in paths), key=kind_order)
            self.kept = {"signature": signature, "entries": found, "files": None}
        return self.kept["entries"]

    def known(self):
        self.entries()
        if self.kept["files"] is None:
            self.kept["files"] = self.listed_files()
        return self.kept["files"]

    def blob(self, sha):
        """The blob of a listed file, or None."""
        if not self.blobs or not SHA.match(sha or "") or sha not in self.known():
            return None
        path = self.blobs / "blobs" / sha[:2] / sha
        return path if path.is_file() else None

    def picture_path(self, sha, side):
        """A JPEG of a listed picture at most `side` px, made once into the cockpit's thumbs folder; or None."""
        found = self.blob(sha)
        return thumbnail(found, self.thumbs / f"{sha}-{side}.jpg", side) if found else None

    def file_path(self, sha):
        """(listed name, path) of a listed take or GLB; or None."""
        found = self.blob(sha)
        return (self.known()[sha], found) if found else None


class ExportedLibrary(Library):
    """The library part of a pushed state export (built by `export_rows` and the pictures beside it)."""

    name = "export"

    def __init__(self, folder):
        self.folder = pathlib.Path(folder)
        self.kept = {"made": None, "entries": []}

    def made(self):
        path = self.folder / EXPORT_ROWS
        return path.stat().st_mtime_ns if path.is_file() else None

    def entries(self):
        made = self.made()
        if self.kept["made"] != made:
            rows = json.loads((self.folder / EXPORT_ROWS).read_text()) if made else []
            self.kept = {"made": made, "entries": [LibraryEntry.model_validate(row) for row in rows]}
        return self.kept["entries"]

    def picture_path(self, sha, side):
        if not SHA.match(sha or ""):
            return None
        for each in (side, THUMB_SIDE if side == HERO_SIDE else HERO_SIDE):
            path = self.folder / "files" / f"{sha}-{each}.jpg"
            if path.is_file():
                return path
        return None

    def file_path(self, sha):
        if not SHA.match(sha or ""):
            return None
        name = self.listed_files().get(sha)
        path = self.folder / exported_file(sha, name or "")
        return (name, path) if name and path.is_file() else None


def exported_file(sha, name):
    """Where a take or a GLB sits in the export."""
    return f"library/files/{sha}{posixpath.splitext(name)[1].lower()}"


def library():
    """The library this cockpit shows, made once per settings: local from SCORE_LIB_ROOT, hosted from the export."""
    from django.conf import settings
    key = (settings.SCORE_MODE, str(settings.SCORE_LIB_ROOT), str(settings.SCORE_HOME))
    if CHOSEN.get("key") != key:
        CHOSEN.update(key=key, library=chosen_library(settings))
    return CHOSEN["library"]


def chosen_library(settings):
    if settings.SCORE_MODE == settings.HOSTED:
        return ExportedLibrary(settings.SCORE_HOME / "export" / "current")
    return local_library(settings)


def local_library(settings):
    """The library folder beside this cockpit, or None when SCORE_LIB_ROOT is not set."""
    if not settings.SCORE_LIB_ROOT:
        return None
    return LocalLibrary(settings.SCORE_LIB_ROOT, settings.SCORE_LIB_BLOBS_DIR, settings.SCORE_HOME / "thumbs")


def for_export():
    """The library the state export carries: the local one (a hosted cockpit sends none on)."""
    from django.conf import settings
    shown = library()
    return shown if isinstance(shown, LocalLibrary) else local_library(settings)


# --- finding entries -------------------------------------------------------------------------------------------

def matches(entry, kind, place, state, words):
    """True when an entry passes the page's filters: its kind, the place it came from, its state, words in its name."""
    if (kind and entry.kind != kind) or (place and entry.place != place) or (state and entry.state != state):
        return False
    return not words or all(word in f"{entry.title} {entry.entry_id}".lower() for word in words.lower().split())


def filtered(entries, kind="", place="", state="", words=""):
    return [entry for entry in entries if matches(entry, kind, place, state, words)]


def places_of(entries):
    return sorted({entry.place for entry in entries if entry.place})


def from_place(entries, place):
    """The entries that came from one place, newest version of each id."""
    newest = {}
    for entry in entries:
        if entry.place == place and entry.state != "withdrawn":
            newest[(entry.kind, entry.entry_id)] = entry
    return sorted(newest.values(), key=kind_order)


def kinds_mixed(entries):
    """Entries taken a kind at a time in turn, so a short row shows every kind the place has."""
    by_kind = {}
    for entry in entries:
        by_kind.setdefault(entry.kind, []).append(entry)
    rows = list(by_kind.values())
    return [row[rank] for rank in range(max(map(len, rows), default=0)) for row in rows if rank < len(row)]


def counted_kind(kind, count):
    """"3 models", "1 model", "2 sound"."""
    label = kind_label(kind).lower()
    return f"{count} {label[:-1] if count == 1 and label.endswith('s') else label}"


# --- into the state export (sync/building.py) ------------------------------------------------------------------

def exported_rows(entries):
    """The rows the hosted cockpit reads: each entry with a sound's first takes and no GLB (too large to send)."""
    return [entry.model_copy(update={"takes": entry.takes[:MAX_TAKES], "glb": None}).model_dump() for entry in entries]


def export_rows(local, out, filler):
    """Write library/entries.json into the export first; the entries."""
    entries = local.entries()
    path = pathlib.Path(out) / EXPORT_ROWS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exported_rows(entries), separators=(",", ":"), sort_keys=True))
    filler.wrote(path, path.stat().st_size)
    return entries


def export_pictures(local, entries, filler, side):
    """Every entry's picture at `side` into the export's files/, as the step pictures are, while they fit."""
    for entry in entries:
        found = local.blob(entry.picture) if entry.picture else None
        if found:
            filler.picture(found, entry.picture, side, f"library picture {entry.address}")


def export_takes(local, entries, filler):
    """Each sound's first takes into the export's library/files/, while they fit."""
    for entry in entries:
        for take in entry.takes[:MAX_TAKES]:
            found = local.blob(take.sha)
            if found:
                filler.place_copy(found, exported_file(take.sha, take.name), f"library take {take.name}")
