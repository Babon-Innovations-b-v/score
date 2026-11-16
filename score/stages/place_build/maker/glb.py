"""A GLB's two chunks read and written as they are (the maker edits a made model losslessly: its root's transform and
its base colour picture, never a re-export that would re-encode the rest).

    read(path) -> (document, binary)       write(path, document, binary)
    image(document, binary, index)         with_image(document, binary, index, data) -> binary
    base_colour_image(document)            the image index the first material's base colour reads, or None
"""
import json
import struct

MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def read(path):
    """The GLB at `path` as its JSON document and its binary chunk."""
    data = open(path, "rb").read()
    if data[:4] != MAGIC:
        raise ValueError(f"{path}: not a GLB")
    length, kind = struct.unpack("<II", data[12:20])
    if kind != JSON_CHUNK:
        raise ValueError(f"{path}: its first chunk is not JSON")
    document = json.loads(data[20:20 + length])
    rest = 20 + length
    binary = b""
    if rest < len(data):
        size, kind = struct.unpack("<II", data[rest:rest + 8])
        if kind != BIN_CHUNK:
            raise ValueError(f"{path}: its second chunk is not binary")
        binary = data[rest + 8:rest + 8 + size]
    return document, binary


def padded(data, filler):
    return data + filler * (-len(data) % 4)


def write(path, document, binary):
    """The document and binary chunk written as one GLB at `path`."""
    if document.get("buffers"):
        document["buffers"][0]["byteLength"] = len(binary)
    text = padded(json.dumps(document, separators=(",", ":")).encode(), b" ")
    blob = padded(binary, b"\0")
    total = 12 + 8 + len(text) + (8 + len(blob) if blob else 0)
    with open(path, "wb") as out:
        out.write(MAGIC + struct.pack("<II", 2, total))
        out.write(struct.pack("<II", len(text), JSON_CHUNK) + text)
        if blob:
            out.write(struct.pack("<II", len(blob), BIN_CHUNK) + blob)


def image(document, binary, index):
    """The encoded bytes of image `index` (held in a buffer view)."""
    view = document["bufferViews"][document["images"][index]["bufferView"]]
    start = view.get("byteOffset", 0)
    return binary[start:start + view["byteLength"]]


def with_image(document, binary, index, data):
    """The binary chunk with image `index` replaced by `data`; every later buffer view moved (4-byte aligned) and the
    document's views updated in place."""
    target = document["images"][index]["bufferView"]
    views = document["bufferViews"]
    order = sorted(range(len(views)), key=lambda number: views[number].get("byteOffset", 0))
    rebuilt = bytearray()
    for number in order:
        view = views[number]
        start = view.get("byteOffset", 0)
        piece = data if number == target else binary[start:start + view["byteLength"]]
        rebuilt.extend(b"\0" * (-len(rebuilt) % 4))
        view["byteOffset"] = len(rebuilt)
        view["byteLength"] = len(piece)
        rebuilt.extend(piece)
    return bytes(rebuilt)


def base_colour_image(document):
    """The image the first material's base colour texture reads, or None when it has none."""
    for material in document.get("materials", []):
        found = material.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if found is not None:
            return document["textures"][found["index"]]["source"]
    return None


def with_root_matrix(document, matrix):
    """The scene's root nodes put under one new node carrying `matrix` (4x4, row-major as numpy gives it)."""
    scene = document["scenes"][document.get("scene", 0)]
    document["nodes"].append({"name": "fitted", "children": list(scene["nodes"]),
                              "matrix": [float(value) for value in matrix.T.reshape(-1)]})
    scene["nodes"] = [len(document["nodes"]) - 1]
    return document
