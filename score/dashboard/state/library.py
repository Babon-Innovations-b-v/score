"""The library the cockpit shows: a creator's library of locked, reusable parts, read through one small interface.

    library()   # local: the library folder SCORE_LIB_ROOT (its blob folder SCORE_LIB_BLOBS_DIR); hosted: the export's
                # library/ part; None when there is no library

An entry is `<kind>/<id>@<version>` with `entries/<kind>/<id>/<version>/entry.json` (title, picture, files, provenance,
tags, state draft/locked/withdrawn), read through `score.library` (ADR-0007); file bytes live in a blob folder as
blobs/<sha[:2]>/<sha>. Nothing of the library's
own code is imported here and no entry data is kept in this repository: the folder is the creator's, read only.
"""
import json
import pathlib
import posixpath
import re
from urllib.parse import quote

from pydantic import BaseModel

from score.dashboard.state.files import HERO_SIDE, SHA, THUMB_SIDE, thumbnail
from score.dashboard.state.names import plain

# The Library's shelves follow the framework's layers (#47): a kind, (lamp) a place's light layer (owner, 2026-10-20:
# a sky is no light; the lamps are), the motion layer's people, and a place with its own layers under it (a layer is a
# part of its place, no shelf of its own). Ground is retired: a terrain piece is a model, a ground finish a surface.
# The kind ids stay; only what the owner reads changes. The algorithm kind's shelf is Physics: only physics setups
# (CONTEXT.md "physics setup", owner 2026-10-20). The one other code entry is the surface recipes, on Surfaces marked
# made by code (CODE_SHELF); a layer's placement, layout, terrain, sky, light, sound and film code is the framework's
# own steps, withdrawn from the library (owner, 2026-10-21).
KINDS = [("model", "Models"), ("surface", "Surfaces"), ("kit", "Kits"), ("character", "Motion"), ("effect", "Effects"),
         ("light", "Skies"), ("lamp", "Lamps"), ("sound", "Sound"), ("algorithm", "Physics"), ("place", "Places")]
CODE_SHELF = {"surface_recipes": "surface"}  # an algorithm entry that is no physics setup: the shelf of what it makes
MADE_BY_CODE = "made_by_code"  # the folder a shelf's code entries sit in (state/library_tree.py)
WHAT = {"model": "a model made through the prop pipeline (a terrain piece too)",
        "surface": "a surface and the material a place writes for it (a ground finish too)",
        "effect": "a particle emitter with its settings and one baked clip",
        "light": "a sky dome or a planet's backdrop, seen from inside", "lamp": "a place's lamps and their strengths",
        "sound": "a sound source with its takes and levels",
        "character": "the motion layer's people: a body look or a dress", "kit": "a set of shell-piece variants",
        "algorithm": "a physics setup with its settings, preset, tests and run line: a body's weight, a hinge and its "
                     "motor, a drop, a push, settling, snapping, a planet's gravity",
        "place": "a place's root with its own layers, plan and cast"}
SCORE_MEANS = {  # what a kind's score measures, said as its hover text; a kind not here shows no score
    "model": "how sound its mesh is: holes, crowded edges, seams", "kit": "the mean score of its pieces",
    "character": "how well its clothes fit its body and are painted", "place": "how many of its steps' checks pass",
    "layer": "how many checks of the step that made it pass", "effect": "how its particles look in its place's film",
    "light": "how sharp and well exposed its sky picture is", "surface": "how close its colours are to its palette",
    "sound": "its loudness, peaks and clipping against the target"}
LAMPS = "light."  # a layer entry whose id starts so is a place's lamps: the Lamps shelf
STATES = ("draft", "locked", "withdrawn")
ADDRESS = re.compile(r"^(?P<kind>[a-z]+)/(?P<id>[a-z0-9_]+(\.[a-z0-9_]+)?)@(?P<version>[1-9][0-9]*)$")
MAX_TAKES = 4  # a sound's takes sent to the hosted cockpit
MAX_FILES = 8  # an entry's files listed in the export (its count and bytes always go)
EXPORT_ROWS = "library/entries.json"
EXPORT_PALETTE = "library/palette.json"
EXPORT_DEMOS = "library/demos.json"
DEMOS = "demos.json"  # in the library cache, beside score_lib/: each algorithm's demo (score.stages.library.demos)
LOST = ".lost"  # beside a file in the library cache: the blob store answered 404 for it (score.stages.library.pictures)
CHOSEN = {}  # the library made for the current settings


class FileOf(BaseModel):
    name: str
    sha: str
    bytes: int = 0


class Listed(BaseModel):
    """One file of an entry as its page lists it."""
    name: str
    bytes: int = 0


class LibraryEntry(BaseModel):
    """One entry as the pages show it."""
    address: str
    kind: str
    entry_id: str
    version: int
    title: str  # the name the owner sees (state/names.py)
    about: str = ""  # the library's own title when it differs: the name's hover text
    shelf: str = ""  # the Library shelf it sits on: its kind, lamp, or what its code makes (CODE_SHELF)
    state: str
    locked: str | None = None
    picture: str | None = None  # the picture's sha
    picture_file: str | None = None  # the picture's name in the entry (where the library cache keeps it)
    world: str | None = None
    place: str | None = None  # the place it came from
    node: str | None = None  # the step that made it, `stage@place` or an environment stage
    source: str = ""  # where it was read from, in words, when no step made it
    commit: str | None = None
    seen_in: list[str] = []
    tags: dict[str, list] = {}
    requires: list[str] = []
    takes: list[FileOf] = []  # a sound's recordings
    glb: FileOf | None = None
    web3d: FileOf | None = None  # the web GLB copy the viewer opens (the record's `web3d`, or a file of role web3d)
    web3d_light: FileOf | None = None  # its light preview copy: what the item page loads first and the export carries
    closeup: FileOf | None = None  # a model's close-up, the picture it was made from (role closeup in score_lib)
    clip: FileOf | None = None  # its preview clip, rendered as the films render at its handover (the record's `clip`)
    finish: dict | None = None  # a surface's own finish: colour, metallic, roughness, glow, see-through, its print
    score: int | float | None = None  # the entry's quality, 0 to 100 (or a fraction 0 to 1), its kind's own scoring
    score_parts: list[dict] = []  # what the score is made of: [{name, value (None: not measured), how, measured, unit}]
    refine_options: list[dict] = []  # [{id, label}] the ways it can be made better
    files: list[Listed] = []  # its files by name (the export sends the first MAX_FILES)
    file_count: int = 0
    file_bytes: int = 0
    facts: dict = {}  # what its kind's viewer plays and the few numbers it shows (kind_facts, viewer_facts)
    missing: list[str] = []  # its files the library's blob store does not hold (hosted: as the export found them)


def shelf_of(record):
    """The Library shelf of an entry record: a place's light layer is a lamp, any other layer sits under its place,
    code that makes something on the shelf of what it makes, a place's locked concept under its place, any other entry
    on its kind's shelf."""
    if record["kind"] == "concept":
        return "place"
    if record["kind"] == "layer":
        return "lamp" if record["id"].startswith(LAMPS) else "place"
    if record["kind"] == "algorithm":
        return CODE_SHELF.get(record["id"], "algorithm")
    return record["kind"]


def made_by_code(entry):
    """Whether an entry is code that makes what its shelf holds: an algorithm off the Physics shelf."""
    return entry.kind == "algorithm" and entry.shelf not in ("", "algorithm")


def score_meaning(entry):
    """What an entry's score measures, or None when its kind's score means nothing to show (an algorithm's measures
    its code snapshot, not what it does) or none of its parts was measured."""
    measured = not entry.score_parts or any(part["value"] is not None for part in entry.score_parts)
    return SCORE_MEANS.get(entry.kind) if entry.score is not None and measured else None


def kind_label(kind):
    return dict(KINDS).get(kind, kind.capitalize())


def entry_url(entry):
    """The entry's own page."""
    return f"/library/{entry.kind}/{quote(entry.entry_id)}/{entry.version}/"


def viewer_url(entry):
    """The entry's GLB full screen in the cockpit's 3D viewer."""
    return f"/library/{entry.kind}/{entry.entry_id}/{entry.version}/3d/"


def percent(score):
    """A score as a whole percent: a whole number is one already (the library's parts run 0 to 100), a fraction from
    0 to 1 is scaled; None stays."""
    if score is None:
        return None
    return round(score * 100 if isinstance(score, float) and score <= 1 else score)


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


def named_file(record, name):
    described = record.get("files", {}).get(name or "")
    return FileOf(name=name, sha=described["sha256"], bytes=described.get("bytes", 0)) if described else None


def web_copy(record):
    """The web GLB copy of an entry: the file its `web3d` names (a name, or {"file": name}), else a file of role
    web3d; None while the copy is on its way."""
    said = record.get("web3d")
    named = named_file(record, said.get("file") if isinstance(said, dict) else said)
    if named:
        return named
    found = files_of_role(record, "web3d", (".glb",))
    return found[0] if found else None


def quality(record):
    """(score, score_parts, refine_options) from the record's top level, or from its `quality` object."""
    held = record if "score" in record else (record.get("quality") or {})
    score = held.get("score")
    return (score if isinstance(score, (int, float)) else None), score_parts(held.get("score_parts")), \
        refine_choices(held.get("refine_options"))


def number_or_none(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def score_parts(given):
    """Score parts as [{name, value, how}], from {name: value} or from [{name, value, how, ...}] (a part with no value
    was not measured)."""
    if isinstance(given, dict):
        return [{"name": str(name), "value": number_or_none(value), "how": ""} for name, value in given.items()]
    return [{"name": str(part["name"]), "value": number_or_none(part.get("value")), "how": str(part.get("how") or ""),
             "measured": number_or_none(part.get("measured")), "unit": str(part.get("unit") or "")}
            for part in given or [] if isinstance(part, dict) and part.get("name")]


def refine_choices(given):
    """Refine options as [{id, label}], from names or {id, label} objects."""
    found = []
    for option in given or []:
        if isinstance(option, str):
            found.append({"id": option, "label": option.replace("_", " ")})
        elif isinstance(option, dict) and option.get("id"):
            found.append({"id": str(option["id"]), "label": str(option.get("label") or option["id"])})
    return found


def preview_clip(record):
    """The preview clip the record's `clip` names (score/stages/library/clips), or None."""
    said = record.get("clip")
    return named_file(record, said.get("file")) if isinstance(said, dict) else None


def light_copy(record):
    """The light preview web copy the record's `web3d` names (its `light`), or None."""
    said = record.get("web3d")
    return named_file(record, said.get("light")) if isinstance(said, dict) else None


# --- what an item page's viewer shows, by kind ----------------------------------------------------------------

COPIED = ("model", "kit", "character", "place")  # the kinds the library gives a web copy
LUFS = re.compile(r"(-?\d+(?:\.\d+)?) LUFS")


def part_of(parts, name):
    return next((part for part in parts if part["name"] == name), {})


def kind_facts(record, parts):
    """The numbers an item page shows from the record alone: a copy's parts and triangles; a sound's length and
    integrated loudness (its quality parts); an algorithm's stage, the steps it runs in and the entries it reads."""
    kind, copy = record["kind"], record.get("web3d") if isinstance(record.get("web3d"), dict) else {}
    if kind in COPIED:
        return {"parts": number_or_none(copy.get("objects")), "triangles": number_or_none(copy.get("triangles"))}
    if kind == "sound":
        loud = LUFS.search(part_of(parts, "loudness").get("how", ""))
        return {"seconds": part_of(parts, "length").get("measured"), "lufs": float(loud.group(1)) if loud else None}
    if kind == "algorithm":
        provenance = record.get("provenance") or {}
        return {"stage": provenance.get("stage"), "steps": len(provenance.get("nodes") or []),
                "reads": preset_folders(record)}
    return {}


PRESET = re.compile(r"^presets/[^/]+/(?:data/)?(?P<folder>.+)/[^/]+$")


def preset_folders(record):
    """The data an algorithm reads, in words: its preset's folders ("demo films", "crops"), in order."""
    found = []
    for name in sorted(record.get("files", {})):
        matched = PRESET.match(name)
        words = matched["folder"].replace("definitions/", "").replace("/", " ").replace("_", " ") if matched else None
        if words and words not in found:
            found.append(words)
    return found


def entry_of(record):
    """A LibraryEntry from one entry.json record."""
    provenance = record.get("provenance") or {}
    glbs = files_of_role(record, "gltf", (".glb",))
    score, parts, options = quality(record)
    listed = [Listed(name=name, bytes=described.get("bytes", 0))
              for name, described in sorted(record.get("files", {}).items())]
    title, about = plain(record["kind"], record["id"], record.get("title") or record["id"])
    return LibraryEntry(
        address=record["address"], kind=record["kind"], entry_id=record["id"], version=record["version"],
        title=title, about=about, shelf=shelf_of(record), state=record["state"], locked=record.get("locked"),
        picture=picture_sha(record), picture_file=(record.get("picture") or {}).get("file"),
        world=provenance.get("world"), place=provenance.get("place"),
        node=made_by_node(provenance), source=provenance.get("source") or "", commit=provenance.get("commit"),
        seen_in=record.get("seen_in") or [], tags=record.get("tags") or {}, requires=record.get("requires") or [],
        takes=files_of_role(record, "audio", (".ogg", ".wav", ".mp3", ".flac")), glb=glbs[0] if glbs else None,
        web3d=web_copy(record), web3d_light=light_copy(record), closeup=next(iter(files_of_role(
            record, "closeup", (".png", ".jpg", ".jpeg", ".webp"))), None), clip=preview_clip(record),
        finish=finish_print(record), score=score,
        score_parts=parts, refine_options=options, files=listed, file_count=len(listed),
        file_bytes=sum(each.bytes for each in listed), facts=kind_facts(record, parts))


# --- a surface's finish ----------------------------------------------------------------------------------------

USD_INPUT = re.compile(r"(?:color3f|float)\s+inputs:(\w+)\s*=\s*(\([^)]*\)|[-0-9.e]+)")
FINISH_INPUTS = {"diffuseColor": "colour", "metallic": "metallic", "roughness": "roughness",
                 "emissiveColor": "glow", "opacity": "opacity"}


def finish_print(record):
    """A surface's print texture, the start of its finish; None for any other entry."""
    if record.get("kind") != "surface":
        return None
    prints = files_of_role(record, "texture", (".png", ".jpg", ".jpeg"))
    return {"print": prints[0].model_dump()} if prints else {}


def usd_value(text):
    """A UsdPreviewSurface input's value: a number, or a list of three for a colour."""
    if text.startswith("("):
        return [float(part) for part in text.strip("()").split(",")]
    return float(text)


def finish_of(material_text):
    """The finish a surface's material.usda sets: {colour, metallic, roughness, glow, opacity} as it gives them."""
    return {FINISH_INPUTS[name]: usd_value(value) for name, value in USD_INPUT.findall(material_text)
            if name in FINISH_INPUTS}


USD_TOKEN = re.compile(r'score:token\s*=\s*"([^"]*)"')


def first_usda(record):
    """The name of a record's first OpenUSD text file (a surface's material, a light's sky), or None."""
    return next((name for name, described in sorted(record.get("files", {}).items())
                 if described.get("role") == "usd" and name.endswith(".usda")), None)


# --- a light's lamps, an effect's settings ----------------------------------------------------------------------

LAMP = re.compile(r'def (DomeLight|DistantLight|SphereLight|RectLight|DiskLight|CylinderLight) "(\w+)"')
LAMP_INPUT = re.compile(r"(?:color3f|float|bool)\s+inputs:(color|intensity|exposure|colorTemperature|"
                        r"enableColorTemperature)\s*=\s*(\([^)]*\)|[-0-9.e]+|true|false)")
LAMP_TYPES = {"DomeLight": "dome", "DistantLight": "sun", "SphereLight": "point", "RectLight": "area",
              "DiskLight": "area", "CylinderLight": "area"}


def kelvin_of(colour):
    """A linear sRGB colour's correlated colour temperature in kelvin (McCamy's formula over its CIE xy)."""
    red, green, blue = colour
    x_sum = 0.4124 * red + 0.3576 * green + 0.1805 * blue
    y_sum = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    total = x_sum + y_sum + 0.0193 * red + 0.1192 * green + 0.9505 * blue
    if total <= 0:
        return None
    slope = (x_sum / total - 0.3320) / (0.1858 - y_sum / total)
    return round(449 * slope ** 3 + 3525 * slope ** 2 + 6823.3 * slope + 5520.33)


def lamp_of(kind, name, block):
    """One lamp from its OpenUSD block: {type, name, colour, power (intensity times two to its exposure), kelvin}."""
    given = dict(LAMP_INPUT.findall(block))
    colour = usd_value(given["color"]) if "color" in given else [1.0, 1.0, 1.0]
    power = float(given.get("intensity", 1)) * 2 ** float(given.get("exposure", 0))
    kelvin = float(given["colorTemperature"]) if given.get("enableColorTemperature") in ("1", "true") \
        and "colorTemperature" in given else kelvin_of(colour)
    return {"type": LAMP_TYPES[kind], "name": name, "colour": colour, "power": round(power, 4), "kelvin": kelvin}


def lamps_of(usda_text):
    """Every lamp an OpenUSD text defines, in its order."""
    found = list(LAMP.finditer(usda_text))
    ends = [match.start() for match in found[1:]] + [len(usda_text)]
    return [lamp_of(match.group(1), match.group(2), usda_text[match.end():end]) for match, end in zip(found, ends)]


VIEWER_FILE = {"effect": "settings.json", "lamp": "lamps.json"}


def placed_lamps(record):
    """A light layer's lamps (its lamps.json): {type (sun or point), name, colour (white: the layer sets none),
    power (its strength after the sweep), kelvin (None: not set), spot (where it stands, metres, or None)}."""
    return [{"type": "sun" if lamp.get("sun") else "point", "name": lamp["path"].rsplit("/", 1)[-1],
             "colour": [1.0, 1.0, 1.0], "power": round(lamp["intensity"] * lamp.get("scale", 1.0), 4), "kelvin": None,
             "spot": lamp.get("spot")} for lamp in record.get("lamps", [])]


SKY_DOME = 'def Mesh "Dome"'  # a sky's OpenUSD draws a dome round the place; else a planet's backdrop
SETTING_WORDS = 40  # an effect setting longer than this (its sources in words) stays in the library


def effect_settings(text):
    """An effect's emitter settings the item page plays: its numbers, lists and short words."""
    return {key: value for key, value in json.loads(text).items()
            if not isinstance(value, (str, dict)) or (isinstance(value, str) and len(value) <= SETTING_WORDS)}


def viewer_facts(record, text_of):
    """What an item page plays that a small file of the entry holds (`text_of(name)`: its text, or None): a
    surface's finish and palette token, a light's lamps, an effect's settings. {} when the file is not here."""
    kind = shelf_of(record)
    named = first_usda(record) if kind in ("surface", "light") else VIEWER_FILE.get(kind)
    text = text_of(named) if named and named in record.get("files", {}) else None
    if text is None:
        return {}
    if kind == "surface":
        token = USD_TOKEN.search(text)
        return {"finish": finish_of(text), "facts": {"token": token.group(1) if token else None}}
    if kind == "light":
        return {"facts": {"sky": "dome" if SKY_DOME in text else "planet"}}
    if kind == "lamp":
        return {"facts": {"lamps": placed_lamps(json.loads(text))}}
    return {"facts": {"settings": effect_settings(text)}}


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

    def folders(self):
        """The Library's folders of these entries (state/library_tree.py), made again when the entries change."""
        from score.dashboard.state.library_tree import folders
        entries = self.entries()
        if self.kept.get("folders_of") is not entries:
            self.kept.update(folders_of=entries, folders=folders(entries))
        return self.kept["folders"]

    def demo(self, entry_id):
        """An algorithm's demo ({"missing": why} when it has none), or None when no demos are here."""
        path = self.demos_path()
        if path is None or not path.is_file():
            return None
        stamp = path.stat().st_mtime_ns
        if self.kept.get("demos_at") != stamp:
            self.kept.update(demos_at=stamp, demos=json.loads(path.read_text()))
        return self.kept["demos"].get(entry_id)

    def listed_files(self):
        """{sha: listed name} of every file the pages may serve: pictures, takes, GLBs."""
        found = {}
        for entry in self.entries():
            if entry.picture:
                found[entry.picture] = "picture.png"
            for each in shown_files(entry):
                found[each.sha] = each.name
        return found


def shown_files(entry):
    """An entry's files a page shows besides its picture: a sound's takes, its 3D files, a model's close-up and its
    preview clip."""
    return [*entry.takes, *three_d_files(entry), *(each for each in (entry.closeup, entry.clip) if each)]


def three_d_files(entry):
    """An entry's files for 3D: its GLB, its web copy and light preview, a surface's print."""
    printed = (entry.finish or {}).get("print")
    return [each for each in (entry.glb, entry.web3d, entry.web3d_light,
                              FileOf.model_validate(printed) if printed else None) if each]


class LocalLibrary(Library):
    """A library folder beside the cockpit, read only; entries re-read when its index changes. A file's bytes come
    from the blob folder, else from the library cache the store's machine fills (`cache`,
    score/stages/library/pictures.py: <kind>/<id>/<version>/<file>)."""

    name = "local"

    def __init__(self, root, blobs, thumbs, cache=None):
        self.root = pathlib.Path(root).expanduser()
        self.blobs = pathlib.Path(blobs).expanduser() if blobs else None
        self.thumbs = pathlib.Path(thumbs)
        self.cache = pathlib.Path(cache) if cache else None
        self.kept = {"signature": None, "entries": [], "files": {}}  # demos kept beside, by their file's time

    def demos_path(self):
        return self.cache.parent / DEMOS if self.cache else None

    def signature(self):
        """When the library's index was last written: a lock or an export rebuilds it."""
        folder = self.root / "index"
        return tuple(sorted((path.name, path.stat().st_mtime_ns) for path in folder.glob("*.json"))) \
            if folder.is_dir() else ()

    def entries(self):
        signature = self.signature()
        if self.kept["signature"] != signature:
            from score import library as score_library  # here: the hosted image holds score/dashboard alone
            found = sorted((self.read_entry(record) for record in score_library.entries(self.root)), key=kind_order)
            self.kept.update(signature=signature, entries=found, files=None)
        return self.kept["entries"]

    def read_entry(self, record):
        """An entry with what its viewer plays from its small files here: a surface's finish, a light's lamps, an
        effect's settings."""
        entry = entry_of(record)
        found = viewer_facts(record, lambda name: self.text_of(record, name))
        if not found:
            return entry
        update = {"facts": {**entry.facts, **found["facts"]}}
        if "finish" in found:
            update["finish"] = {**(entry.finish or {}), **found["finish"]}
        return entry.model_copy(update=update)

    def text_of(self, record, name):
        """One file of an entry as text: its blob, else its copy in the library cache; None when neither is here."""
        sha = record["files"][name].get("sha256") or ""
        found = [self.blobs / "blobs" / sha[:2] / sha] if self.blobs and SHA.match(sha) else []
        found += [self.cache / record["kind"] / record["id"] / str(record["version"]) / name] if self.cache else []
        path = next((path for path in found if path.is_file()), None)
        return path.read_text() if path else None

    def known(self):
        self.entries()
        if self.kept["files"] is None:
            self.kept["files"] = self.listed_files()
        return self.kept["files"]

    def blob(self, sha):
        """The bytes of a listed file: its blob, else its copy in the library cache; None when neither is here."""
        if not SHA.match(sha or "") or sha not in self.known():
            return None
        found = [self.blobs / "blobs" / sha[:2] / sha] if self.blobs else []
        found += [self.cache / name for name in self.cached_names().get(sha, [])] if self.cache else []
        return next((path for path in found if path.is_file()), None)

    def cached_names(self):
        """{sha: [<kind>/<id>/<version>/<file>, ...]} of every listed picture, take and GLB: where the cache keeps it
        (one sha may be listed by several entries, a place and its layer)."""
        if self.kept.get("cached_of") is not self.entries():
            found = {}
            for entry in self.entries():
                folder = f"{entry.kind}/{entry.entry_id}/{entry.version}"
                if entry.picture and entry.picture_file:
                    found.setdefault(entry.picture, []).append(f"{folder}/{entry.picture_file}")
                for each in shown_files(entry):
                    found.setdefault(each.sha, []).append(f"{folder}/{each.name}")
            self.kept.update(cached_of=self.entries(), cached=found)
        return self.kept["cached"]

    def picture_path(self, sha, side):
        """A JPEG of a listed picture at most `side` px, made once into the cockpit's thumbs folder; or None."""
        found = self.blob(sha)
        return thumbnail(found, self.thumbs / f"{sha}-{side}.jpg", side) if found else None

    def file_path(self, sha):
        """(listed name, path) of a listed take or GLB; or None."""
        found = self.blob(sha)
        return (self.known()[sha], found) if found else None

    def missing(self, entry):
        """The names of an entry's files the library's blob store answered 404 for: marked lost in the library cache
        (score/stages/library/pictures.py), the mark naming the bytes the entry still records where it knows them."""
        if self.cache is None:
            return []
        folder = self.cache / entry.kind / entry.entry_id / str(entry.version)
        known = known_shas(entry)
        return [listed.name for listed in entry.files if (folder / f"{listed.name}{LOST}").is_file()
                and (listed.name not in known or (folder / f"{listed.name}{LOST}").read_text() == known[listed.name])]


def known_shas(entry):
    """{file name: sha} of the files whose bytes an entry names: its picture, takes, copies, print and close-up."""
    found = {each.name: each.sha for each in shown_files(entry)}
    if entry.picture and entry.picture_file:
        found[entry.picture_file] = entry.picture
    return found


class ExportedLibrary(Library):
    """The library part of a pushed state export (built by `export_rows` and the pictures beside it)."""

    name = "export"

    def __init__(self, folder):
        self.folder = pathlib.Path(folder)
        self.kept = {"made": None, "entries": []}

    def demos_path(self):
        return self.folder / EXPORT_DEMOS

    def made(self):
        path = self.folder / EXPORT_ROWS
        return path.stat().st_mtime_ns if path.is_file() else None

    def entries(self):
        made = self.made()
        if self.kept["made"] != made:
            rows = json.loads((self.folder / EXPORT_ROWS).read_text()) if made else []
            self.kept.update(made=made, entries=[LibraryEntry.model_validate(row) for row in rows])
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

    def missing(self, entry):
        """The names of an entry's files the library's blob store did not hold when the export was made."""
        return entry.missing


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
    return LocalLibrary(settings.SCORE_LIB_ROOT, settings.SCORE_LIB_BLOBS_DIR, settings.SCORE_HOME / "thumbs",
                        settings.SCORE_PROPS_HOME / "cache" / "library" / "score_lib")


def for_export():
    """The library the state export carries: the local one (a hosted cockpit sends none on)."""
    from django.conf import settings
    shown = library()
    return shown if isinstance(shown, LocalLibrary) else local_library(settings)


# --- into the state export (sync/building.py) ------------------------------------------------------------------

def exported_rows(entries, missing):
    """The rows the hosted cockpit reads: each entry with a sound's first takes, its first files, no raw GLB and
    the names of its files the library lost (`missing(entry)`); the light copies and a surface's print go as files
    while they fit (export_three_d)."""
    return [entry.model_copy(update={"takes": entry.takes[:MAX_TAKES], "glb": None, "files": entry.files[:MAX_FILES],
                                     "missing": missing(entry)}).model_dump() for entry in entries]


def export_rows(local, out, filler):
    """Write library/entries.json and the palette a surface's page offers into the export first; the entries."""
    entries = local.entries()
    for name, rows in ((EXPORT_ROWS, exported_rows(entries, local.missing)), (EXPORT_PALETTE, palette())):
        path = pathlib.Path(out) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, separators=(",", ":"), sort_keys=True))
        filler.wrote(path, path.stat().st_size)
    return entries


# --- the palette a surface's page offers --------------------------------------------------------------------------

def palette_of(tokens):
    """{name: colour} of the palette tokens (design/tokens/tokens.json's colours with one value, not a theme's)."""
    return {token["name"]: token["value"] for token in tokens["color"]["tokens"] if isinstance(token["value"], str)}


def palette():
    """The palette tokens a surface's page offers: hosted, the export's copy; local, this checkout's tokens."""
    from django.conf import settings
    shown = library()
    path = shown.folder / EXPORT_PALETTE if isinstance(shown, ExportedLibrary) else None
    if path is not None:
        return json.loads(path.read_text()) if path.is_file() else {}
    return palette_of(json.loads((settings.SCORE_REPO / "design/tokens/tokens.json").read_text()))


def export_demos(local, out, filler):
    """The algorithms' demos into the export, when the store's machine has made them."""
    found = local.demos_path()
    if found is None or not found.is_file():
        return
    path = pathlib.Path(out) / EXPORT_DEMOS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(found.read_bytes())
    filler.wrote(path, path.stat().st_size)


def export_pictures(local, entries, filler, side):
    """Every entry's picture and close-up at `side` into the export's files/, as the step pictures are, while they
    fit."""
    for entry in entries:
        for sha in (entry.picture, entry.closeup.sha if entry.closeup else None):
            found = local.blob(sha) if sha else None
            if found:
                filler.picture(found, sha, side, f"library picture {entry.address}")


def export_takes(local, entries, filler):
    """Each sound's first takes into the export's library/files/, while they fit."""
    for entry in entries:
        for take in entry.takes[:MAX_TAKES]:
            found = local.blob(take.sha)
            if found:
                filler.place_copy(found, exported_file(take.sha, take.name), f"library take {take.name}")


def export_three_d(local, entries, filler):
    """Each entry's preview clip, light web copy and each surface's print into the export's library/files/, last,
    while they fit; a whole copy stays on the store's machine."""
    for entry in entries:
        printed = (entry.finish or {}).get("print")
        for each in [entry.clip, entry.web3d_light, FileOf.model_validate(printed) if printed else None]:
            found = local.blob(each.sha) if each else None
            if found:
                filler.place_copy(found, exported_file(each.sha, each.name), f"library 3D {each.name}")
