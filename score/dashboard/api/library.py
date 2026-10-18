"""The library's file routes: an entry's picture (thumbnail and large), a sound's takes, a GLB and the facts the 3D
viewer reads for it. Only files an entry lists are served (state/library.py)."""
import json
import struct

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response

from score.dashboard.api.deps import signed_in
from score.dashboard.api.routes import IMMUTABLE, NOT_YET, on_its_way
from score.dashboard.state import library as lib
from score.dashboard.state.files import HERO_SIDE, THUMB_SIDE, content_type

library_files = APIRouter()
AUDIO = {".ogg": "audio/ogg", ".wav": "audio/wav", ".mp3": "audio/mpeg", ".flac": "audio/flac"}
# Drawn where the library lists a picture whose bytes are not in this cockpit's blob folder.
NOT_HERE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200" width="320" height="200">'
    '<rect width="320" height="200" fill="#8a8f98" fill-opacity="0.18"/>'
    '<text x="160" y="106" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#8a8f98">'
    'picture not in the blob folder</text></svg>')
VIEW_LIGHTS = [{"type": "directional", "at": [0, 0, 0], "toward": [-0.4, -1, -0.6], "colour": [1, 1, 1],
                "intensity": 2.5}]


def shown():
    found = lib.library()
    if found is None:
        raise HTTPException(404, "no library here")
    return found


def picture(sha, side):
    path = shown().picture_path(sha, side)
    if path is not None:
        return FileResponse(path, media_type="image/jpeg", headers=IMMUTABLE)
    if isinstance(shown(), lib.ExportedLibrary):
        return on_its_way(sha)
    return Response(NOT_HERE, media_type="image/svg+xml", headers=NOT_YET)


@library_files.get("/library-files/thumbs/{sha}.jpg")
def thumb(sha: str, user=Depends(signed_in)):
    return picture(sha, THUMB_SIDE)


@library_files.get("/library-files/pictures/{sha}.jpg")
def large(sha: str, user=Depends(signed_in)):
    return picture(sha, HERO_SIDE)


def listed_file(sha):
    found = shown().file_path(sha)
    if found is None:
        raise HTTPException(404, "no such library file here")
    return found


@library_files.get("/library-files/files/{sha}")
def file(sha: str, user=Depends(signed_in)):
    """A sound's take or a GLB of an entry."""
    name, path = listed_file(sha)
    suffix = "." + name.rsplit(".", 1)[-1].lower()
    return FileResponse(path, media_type=AUDIO.get(suffix) or content_type(name), headers=IMMUTABLE)


def glb_triangles(path):
    """The triangles a GLB draws, read from its JSON chunk: each triangle primitive's index (or vertex) count / 3."""
    with open(path, "rb") as read:
        read.seek(12)
        length, _ = struct.unpack("<II", read.read(8))
        facts = json.loads(read.read(length))
    accessors = facts.get("accessors", [])
    counted = 0
    for mesh in facts.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            which = primitive.get("indices", primitive.get("attributes", {}).get("POSITION"))
            counted += accessors[which]["count"] // 3 if which is not None else 0
    return counted


@library_files.get("/library-files/view/{sha}.json")
def view_facts(sha: str, user=Depends(signed_in)):
    """What the 3D viewer reads before a model: its size, and a plain sky and light (an entry has no scene)."""
    _, path = listed_file(sha)
    return {"bytes": path.stat().st_size, "triangles": glb_triangles(path), "objects": [], "cameras": [],
            "lights": VIEW_LIGHTS, "sky": {"background": [0.03, 0.035, 0.04], "ambient": [0.6, 0.6, 0.6],
                                            "exposure": 1.0}}


@library_files.get("/library-files/view/{name}.glb")
def view_model(name: str, user=Depends(signed_in)):
    """The GLB the viewer loads whole (`<sha>.glb`); no light preview (`<sha>-light.glb`) is made for an entry."""
    if name.endswith("-light"):
        raise HTTPException(404, "no light preview of a library entry")
    _, path = listed_file(name)
    return FileResponse(path, media_type="model/gltf-binary", headers=IMMUTABLE)
