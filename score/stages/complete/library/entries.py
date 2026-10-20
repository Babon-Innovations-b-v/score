"""The library the check traces to, read through one small interface: the score_lib folder SCORE_LIB_ROOT, read only.

    shelf = entries.from_environment()     # None when SCORE_LIB_ROOT is not set
    shelf.of_sha(sha, kinds)               # the address of an entry of those kinds holding a file of that content
    shelf.of_model(model_sha)              # the model entry made from that gltf (score:model_sha256)
    shelf.of_prim(place, path, kinds)      # the entry whose provenance names that prim of that place
    shelf.surface(name, place)             # the surface entry of that name (the place's own one first)

An entry is `<kind>/<id>@<version>` with `entries/<kind>/<id>/<version>/entry.json` (files with their sha256,
provenance), read through `score.library` (ADR-0007), as the cockpit reads it. Nothing of the library's own code is
imported and no entry data is kept in this repository: score is public, the library is the creator's. A withdrawn
entry traces nothing.
"""
import dataclasses
import pathlib
import re

from score import library

WITHDRAWN = "withdrawn"
VARIANT = re.compile(r"\{[^}]*\}")


@dataclasses.dataclass
class Shelf:
    root: pathlib.Path
    shas: dict = dataclasses.field(default_factory=dict)  # sha256: {address: kind}
    models: dict = dataclasses.field(default_factory=dict)  # model gltf sha256: address
    prims: dict = dataclasses.field(default_factory=dict)  # (place, prim path): {address: kind}
    ids: dict = dataclasses.field(default_factory=dict)  # (kind, id): address
    addresses: set = dataclasses.field(default_factory=set)

    def of_sha(self, sha, kinds):
        return next((address for address, kind in sorted(self.shas.get(sha, {}).items()) if kind in kinds), None)

    def of_model(self, model_sha):
        return self.models.get(model_sha)

    def of_prim(self, place, path, kinds):
        found = self.prims.get((place, unvarianted(path)), {})
        return next((address for address, kind in sorted(found.items()) if kind in kinds), None)

    def surface(self, name, place):
        """The surface entry of that name: the place's own (`<name>.<place>`) first, else the shared one."""
        return self.ids.get(("surface", f"{name}.{place}")) or self.ids.get(("surface", name))

    def of_id(self, kind, entry_id):
        return self.ids.get((kind, entry_id))

    def has(self, address):
        return address in self.addresses


def unvarianted(path):
    """A prim path with its variant selections taken out: `/camp/Effects{weather=storm}grains` is
    `/camp/Effects/grains`."""
    return VARIANT.sub("/", path).replace("//", "/")


def file_shas(record):
    """Every content hash an entry holds: its files, the files they were taken from, and its aliases (a place's own
    copy of a model's bytes)."""
    provenance = record.get("provenance") or {}
    found = {described["sha256"] for described in (record.get("files") or {}).values() if described.get("sha256")}
    found |= {described["sha256"] for described in (provenance.get("files_from") or {}).values()
              if isinstance(described, dict) and described.get("sha256")}
    found |= {alias[0] for alias in provenance.get("aliases") or [] if alias}
    return found


def prim_paths(record):
    """(place, prim path) of every prim an entry's provenance names."""
    provenance = record.get("provenance") or {}
    place = provenance.get("place")
    named = list(provenance.get("prims") or []) + ([provenance["prim"]] if provenance.get("prim") else [])
    return [(place, unvarianted(path)) for path in named] if place else []


def shelve(shelf, record):
    """Put one entry.json record on the shelf."""
    address, kind = record["address"], record["kind"]
    shelf.addresses.add(address)
    shelf.ids.setdefault((kind, record["id"]), address)
    for sha in file_shas(record):
        shelf.shas.setdefault(sha, {})[address] = kind
    model_sha = (record.get("provenance") or {}).get("model_sha256")
    if kind == "model" and model_sha:
        shelf.models.setdefault(model_sha, address)
    for key in prim_paths(record):
        shelf.prims.setdefault(key, {})[address] = kind


def read(root):
    """The shelf of a library folder: every entry not withdrawn, the newest version of an id first."""
    shelf = Shelf(root=pathlib.Path(root).expanduser())
    records = sorted(library.entries(shelf.root), key=lambda record: (record["kind"], record["id"], -record["version"]))
    for record in records:
        if record.get("state") != WITHDRAWN:
            shelve(shelf, record)
    return shelf


def from_environment():
    """The library SCORE_LIB_ROOT names, or None when it is not set."""
    root = library.root_from_environment()
    return read(root) if root else None
