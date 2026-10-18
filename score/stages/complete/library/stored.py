"""What the check reads from the store, read only: a place's accepted assembly laid out as links to the stored bytes
(never a checkout: a checkout writes into the store's cache), and the finish records of the bakes that paint every
part from the library.

    folder = stored.laid_out(store, output, folder)   # the output's files as links into the store's blobs
    baked = stored.baked(store, places)               # {model gltf sha256: the bake node that painted it}
    store = stored.reading()                          # the framework's store, its keys read a node's folder only
"""
import os
import pathlib

from score.store import PROPS_HOME, Store, runtime_store

ASSEMBLY = "assembly@{place}"
# The bakes that paint every part of a model from the library surfaces: the surface stage's, the crops' and the ship
# kits' (score/stages/ship_kits: every slot a library surface) and the late bake's; each lists its models as
# made/<name>.gltf.
BAKES = ("surfaces-bake", "crops-surfaces-bake", "ship_kit", "late_bake")


class NodeFolders(runtime_store.FolderStore):
    """The store's folder, its `keys` walking only the prefix's own folder: the whole store's walk (every blob) took
    minutes a node."""

    def keys(self, prefix):
        folder = self.root / prefix.rsplit("/", 1)[0]
        if not folder.is_dir():
            return []
        found = (str(path.relative_to(self.root)) for path in folder.rglob("*")
                 if path.is_file() and not path.name.endswith(".partial"))
        return sorted(key for key in found if key.startswith(prefix))


def reading():
    """The framework's store, read only by this check (it never checks out or writes)."""
    root = PROPS_HOME / "store"
    return Store(NodeFolders(root / "objects"), root / "cache")


def blobs(store):
    """The folder of the store's blobs, each file named by its sha256."""
    return os.path.realpath(store.objects.path("blobs"))


def laid_out(store, output, folder):
    """The stored output's files at their names under a folder of the check's own, each a link to its stored blob."""
    folder = pathlib.Path(folder)
    for name, sha in store.listing(output).items():
        link = folder / name
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(store.objects.path(f"blobs/{sha}"))
    return folder


def made_models(store, node):
    """{gltf sha256: node} of the models one accepted bake made."""
    output = store.accepted(node)
    if not output:
        return {}
    return {sha: node for name, sha in store.listing(output).items()
            if name.startswith("made/") and name.endswith(".gltf") and name.count("/") == 1}


def baked(store, places):
    """{model gltf sha256: the bake node that painted it} over every bake of the places."""
    found = {}
    for stage in BAKES:
        for place in places:
            for sha, node in made_models(store, f"{stage}@{place}").items():
                found.setdefault(sha, node)
    return found
