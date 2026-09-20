"""Write a glTF binary file, which is how a rigged, animated body gets into Godot.

glTF is the format the game already brings meshes in through, and Godot imports it with the
skeleton and the animation intact. This writes one by hand rather than through a modelling
program, because the numbers come out of the body model already correct and every step between
here and the file is a step that can silently turn them into something else. That is not a
worry from nowhere: the first attempt at this work on #36 passed every measurement while
producing twisted wreckage.

The file's own words are kept: a *buffer* is the one blob of numbers, a *buffer view* is a slice
of it, and an *accessor* says how to read a slice (how many, of what shape). Renaming them here
would only make the format's documentation harder to follow.

Nothing in this module knows what a body is. It takes numbers and a document and writes a file.
"""
import json
import pathlib
import struct
import sys
from array import array

FLOAT = 5126
UNSIGNED_BYTE = 5121
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125

ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963

_PACK_AS = {FLOAT: "f", UNSIGNED_BYTE: "B", UNSIGNED_SHORT: "H", UNSIGNED_INT: "I"}
_HOW_MANY = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

_MAGIC = 0x46546C67
_VERSION = 2
_JSON_CHUNK = 0x4E4F534A
_BINARY_CHUNK = 0x004E4942


class Contents:
    """The numbers a glTF file carries, and the slices and readings that point into them."""

    def __init__(self):
        self._blob = bytearray()
        self.views = []
        self.accessors = []

    def _pad(self):
        """Every slice starts on a four-byte boundary, which the format requires."""
        while len(self._blob) % 4:
            self._blob.append(0)

    def _slice(self, values, component, target):
        """Put a flat list of numbers in the blob and return the index of the slice holding it."""
        self._pad()
        start = len(self._blob)
        packed = array(_PACK_AS[component], values)
        if sys.byteorder != "little":
            packed.byteswap()
        self._blob.extend(packed.tobytes())
        view = {"buffer": 0, "byteOffset": start, "byteLength": len(self._blob) - start}
        if target is not None:
            view["target"] = target
        self.views.append(view)
        return len(self.views) - 1

    def reading(self, values, shape, component, target=None, with_bounds=False):
        """Add a way to read one run of numbers, and return the index of it.

        `values` is flat however many dimensions the numbers have; `shape` is the format's name
        for one item, such as VEC3 or MAT4. `with_bounds` writes the smallest and largest of
        each column, which the format requires for vertex positions.
        """
        each = _HOW_MANY[shape]
        if len(values) % each:
            raise ValueError(f"{len(values)} numbers do not divide into {shape}")
        accessor = {
            "bufferView": self._slice(values, component, target),
            "componentType": component,
            "count": len(values) // each,
            "type": shape,
        }
        if with_bounds:
            columns = [values[start::each] for start in range(each)]
            accessor["min"] = [min(column) for column in columns]
            accessor["max"] = [max(column) for column in columns]
        self.accessors.append(accessor)
        return len(self.accessors) - 1

    def blob(self):
        self._pad()
        return bytes(self._blob)


def refuse_a_tangled_graph(document):
    """Stop a file whose nodes are not a tree from being written at all.

    A node listed as its own child, or as two nodes' child, reads as a skeleton with no end:
    Godot walks it for ever, at full tilt, on a file of half a megabyte. Nothing else catches it,
    because every pose and every bone length in such a file is still perfectly correct.
    """
    parent_of = {}
    for index, node in enumerate(document.get("nodes", [])):
        for child in node.get("children", []):
            if child == index:
                raise ValueError(f"node {index} is its own child")
            if child in parent_of:
                raise ValueError(f"node {child} is the child of {parent_of[child]} and {index}")
            parent_of[child] = index
    for start in range(len(document.get("nodes", []))):
        seen, walk = set(), start
        while walk in parent_of:
            if walk in seen:
                raise ValueError(f"node {start} is inside a loop of nodes")
            seen.add(walk)
            walk = parent_of[walk]


def write(path, document, contents):
    """Write the document and its numbers out as one .glb file."""
    refuse_a_tangled_graph(document)
    blob = contents.blob()
    document = dict(document)
    document["bufferViews"] = contents.views
    document["accessors"] = contents.accessors
    document["buffers"] = [{"byteLength": len(blob)}]

    text = json.dumps(document, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)

    body = (struct.pack("<II", len(text), _JSON_CHUNK) + text
            + struct.pack("<II", len(blob), _BINARY_CHUNK) + blob)
    header = struct.pack("<III", _MAGIC, _VERSION, len(body) + 12)

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + body)
    return path


def read_document(path):
    """The document out of a written file, so a test can check what was written."""
    raw = pathlib.Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<III", raw, 0)
    if magic != _MAGIC:
        raise ValueError("not a glTF binary file")
    if version != _VERSION:
        raise ValueError(f"glTF version {version}, expected {_VERSION}")
    if total != len(raw):
        raise ValueError(f"header says {total} bytes, file is {len(raw)}")
    length, kind = struct.unpack_from("<II", raw, 12)
    if kind != _JSON_CHUNK:
        raise ValueError("the first chunk is not the document")
    return json.loads(raw[20:20 + length])
