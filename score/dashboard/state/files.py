"""Files the dashboard may serve: only a sha it saw in a listing it read (or a picture it named from the world's
data), opened read-only, its content type from its listed name; images get a cached JPEG thumbnail."""
import mimetypes
import pathlib
import re
import threading

from score.dashboard.state.models import FileRef

SHA = re.compile(r"^[0-9a-f]{64}$")
THUMB_SIDE = 360
HERO_SIDE = 1280
THUMB_QUALITY = 80
KINDS = {".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".mp4": "film", ".webm": "film",
         ".usda": "usd", ".usdc": "usd", ".usd": "usd", ".usdz": "usd", ".gltf": "gltf", ".glb": "gltf"}
TYPES = {".usda": "text/plain", ".usdc": "application/octet-stream", ".usdz": "model/vnd.usdz+zip",
         ".gltf": "model/gltf+json", ".glb": "model/gltf-binary", ".log": "text/plain", ".mp4": "video/mp4"}


def kind_of(name):
    return KINDS.get(pathlib.PurePosixPath(name).suffix.lower(), "other")


def content_type(name):
    suffix = pathlib.PurePosixPath(name).suffix.lower()
    return TYPES.get(suffix) or mimetypes.guess_type(name)[0] or "application/octet-stream"


class Known:
    """{sha: (listed name, file path)} of every file a page named; nothing else is served."""

    def __init__(self):
        self.files = {}
        self.lock = threading.Lock()

    def add(self, sha, name, path):
        with self.lock:
            self.files[sha] = (name, pathlib.Path(path))

    def get(self, sha):
        """(name, path) of a known sha, or None for an unknown or malformed one."""
        if not SHA.match(sha or ""):
            return None
        return self.files.get(sha)


def file_ref(sha, name, size):
    """A FileRef served at /files/<sha>; an image's thumbnail at /thumbs/<sha>.jpg."""
    kind = kind_of(name)
    return FileRef(name=name, kind=kind, sha=sha, bytes=size, url=f"/files/{sha}",
                   thumb_url=f"/thumbs/{sha}.jpg" if kind == "image" else None)


def thumbnail(source, target, side=THUMB_SIDE):
    """A JPEG of `source` at most `side` px on its long side, written once to `target`; its path."""
    target = pathlib.Path(target)
    if target.exists():
        return target
    from PIL import Image
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as picture:
        picture.thumbnail((side, side))
        partial = target.with_name(target.name + ".partial")
        picture.convert("RGB").save(partial, "JPEG", quality=THUMB_QUALITY)
    partial.replace(target)
    return target
