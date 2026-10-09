"""The world's heavy files, the made models and the sounds its places name, kept as a release of this repository
rather than in git (about 290 MB; the repository's own history stays small).

`data/assets/world1.json` is the manifest: the release (repository and tag), its archives (name, bytes, sha256) and
every file in them (its name, bytes, sha256, and where it came from and under what licence). A record names such a
file by its name in the manifest (`models/hub_kit/console_1.gltf`, `sound/generated/places/habitat.ogg`), and a
file kept in git by its path from the repository's root (`data/ground/moon_scan_wide_shade.jpg`). `resolve(name)`
gives the file on disk either way, fetching and checking the release the first time it is needed.

    python3 tools/assets/world.py fetch                         # the release into the local folder, checked
    python3 tools/assets/world.py check                         # every local file against the manifest
    python3 tools/assets/world.py pack <tree> <tag> [<licences>]  # a new release from a folder: archives, manifest
    python3 tools/assets/world.py publish                       # the packed archives uploaded as the release (gh)

The local folder is `SCORE_WORLD_ASSETS` when set, else `~/.cache/score/world-assets/<tag>/`; it is also where the
tools that make the world's files write them (route.py install, the sound tools), so a pack of it is the next release.
`<licences>` is a JSON list of {"match": a name or a folder ending in "/", "licence", "source", "author"} (the
manifest's own list when left out); a sound's terms are its entry in data/sound/licences.json, the list the sound
tools keep. The longest match names each file's terms, and a file no entry matches stops the pack.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = REPO / "data/assets/world1.json"
SOUND_LICENCES = REPO / "data/sound/licences.json"
# The top folders of the tree, one archive each.
ARCHIVES = ("models", "sound")
PACKED = pathlib.Path.home() / ".cache/score/world-assets/packed"
ABOUT = ("the first world's heavy files (made models and sounds), kept as a release of this repository and named by "
         "the records with the names below; tools/assets/world.py fetches, checks and packs them")


def manifest():
    """The manifest as written."""
    return json.loads(MANIFEST.read_text())


def root(found=None):
    """The local folder holding the release's files, fetched and checked when it is not there yet."""
    found = found or manifest()
    folder = local_folder(found)
    if not (folder / ".checked").exists():
        fetch(found, folder)
    return folder


def local_folder(found):
    """Where the release's files are kept on this machine."""
    configured = os.environ.get("SCORE_WORLD_ASSETS")
    if configured:
        return pathlib.Path(configured)
    return pathlib.Path.home() / ".cache/score/world-assets" / found["release"]["tag"]


def resolve(name, folder=None):
    """A file a record names: a path from the repository's root for a file kept in git (`data/...`), else a file of
    the release, in `folder` when given (a test's own), else in the fetched release."""
    if name.startswith("data/"):
        path = REPO / name
    else:
        path = pathlib.Path(folder or root()) / name
    if not path.exists():
        raise FileNotFoundError(f"{name}: not in the repository nor in the world's release ({path})")
    return path


def sha256(path):
    """A file's sha256, read in blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(found, folder):
    """Every archive of the release downloaded, its sha256 checked, unpacked into `folder`, then every file checked."""
    folder.mkdir(parents=True, exist_ok=True)
    release = found["release"]
    for archive in found["archives"]:
        url = f"https://github.com/{release['repository']}/releases/download/{release['tag']}/{archive['name']}"
        target = folder / archive["name"]
        print(f"fetching {url}", file=sys.stderr)
        with urllib.request.urlopen(url) as answer, open(target, "wb") as stream:
            shutil.copyfileobj(answer, stream)
        if sha256(target) != archive["sha256"]:
            raise SystemExit(f"{archive['name']}: its sha256 is not the manifest's")
        with tarfile.open(target) as packed:
            packed.extractall(folder, filter="data")
        target.unlink()
    faults = check(found, folder)
    if faults:
        raise SystemExit("the fetched release does not match the manifest:\n  " + "\n  ".join(faults))
    (folder / ".checked").write_text(release["tag"] + "\n")


def check(found, folder):
    """Every manifest file present in `folder` with its sha256; the faults, empty when all match."""
    faults = []
    for name, about in found["files"].items():
        path = folder / name
        if not path.exists():
            faults.append(f"{name}: missing")
        elif sha256(path) != about["sha256"]:
            faults.append(f"{name}: changed")
    return faults


def terms_of(name, licences):
    """The licence entry with the longest match for a file's name, or None."""
    matches = [entry for entry in licences
               if name == entry["match"] or (entry["match"].endswith("/") and name.startswith(entry["match"]))]
    return max(matches, key=lambda entry: len(entry["match"]), default=None)


def file_entries(tree, licences):
    """Every file under the tree's archive folders with its bytes, sha256 and terms; stops on a file without terms."""
    files, unlicensed = {}, []
    for top in ARCHIVES:
        for path in sorted((tree / top).rglob("*")):
            if not path.is_file():
                continue
            name = path.relative_to(tree).as_posix()
            terms = terms_of(name, licences)
            if terms is None:
                unlicensed.append(name)
                continue
            files[name] = {"bytes": path.stat().st_size, "sha256": sha256(path),
                           **{key: terms[key] for key in ("licence", "source", "author") if key in terms}}
    if unlicensed:
        raise SystemExit("files with no licence entry:\n  " + "\n  ".join(unlicensed))
    return files


def write_archives(tree, out):
    """One gzip tar for each archive folder, members in name order with no owner or time, so a pack is repeatable."""
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for top in ARCHIVES:
        target = out / f"{top}.tar.gz"
        with tarfile.open(target, "w:gz", compresslevel=6) as packed:
            for path in sorted((tree / top).rglob("*")):
                info = packed.gettarinfo(path, arcname=path.relative_to(tree).as_posix())
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                if path.is_file():
                    with open(path, "rb") as stream:
                        packed.addfile(info, stream)
                else:
                    packed.addfile(info)
        written.append({"name": target.name, "bytes": target.stat().st_size, "sha256": sha256(target)})
    return written


def sound_terms():
    """The sound tools' licence list as licence entries, one exact match a file."""
    return [{"match": entry["file"], **{key: entry[key] for key in ("licence", "source", "author") if key in entry}}
            for entry in json.loads(SOUND_LICENCES.read_text())]


def pack(tree, tag, licences_path=None, out=PACKED):
    """A new release's archives in `out` and the manifest naming them (written to data/assets/world1.json)."""
    licences = json.loads(pathlib.Path(licences_path).read_text()) if licences_path else manifest()["licences"]
    files = file_entries(tree, licences + sound_terms())
    archives = write_archives(tree, out / tag)
    found = {"is": ABOUT,
             "release": {"repository": "Babon-Innovations-b-v/score", "tag": tag},
             "archives": archives, "licences": licences, "files": files}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(found, indent="\t") + "\n")
    return found


def publish(found, out=PACKED):
    """The packed archives uploaded as the manifest's release with gh (made when it does not exist yet)."""
    release = found["release"]
    paths = [str(out / release["tag"] / archive["name"]) for archive in found["archives"]]
    exists = subprocess.run(["gh", "release", "view", release["tag"], "-R", release["repository"]],
                            capture_output=True).returncode == 0
    if not exists:
        subprocess.run(["gh", "release", "create", release["tag"], "-R", release["repository"], "--title",
                        f"World assets {release['tag']}", "--notes",
                        "The first world's made models and sounds, named by data/assets/world1.json."], check=True)
    subprocess.run(["gh", "release", "upload", release["tag"], "-R", release["repository"], "--clobber", *paths],
                   check=True)


def main():
    arguments = sys.argv[1:]
    if arguments[:1] == ["fetch"]:
        print(root())
    elif arguments[:1] == ["check"]:
        found = manifest()
        faults = check(found, local_folder(found))
        print("\n".join(faults) or f"all {len(found['files'])} files match")
        raise SystemExit(1 if faults else 0)
    elif arguments[:1] == ["pack"] and len(arguments) in (3, 4):
        found = pack(pathlib.Path(arguments[1]), arguments[2], arguments[3] if len(arguments) == 4 else None)
        print(f"{len(found['files'])} files, archives " + ", ".join(
            f"{archive['name']} {archive['bytes'] / 1e6:.0f} MB" for archive in found["archives"]))
    elif arguments[:1] == ["publish"]:
        publish(manifest())
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
