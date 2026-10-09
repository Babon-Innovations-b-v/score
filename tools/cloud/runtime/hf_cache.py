"""A Hugging Face hub cache made of links to the node cache's model folders, for tools that load a model by its
repository id rather than by a path (MOSS's CLAP scorer, Kimodo's Llama 3 text encoder, SOMA-X's assets): each hf:
model the job was handed (SCORE_MODEL_<NAME>, weights.py) is linked in as that repository's snapshot at its pinned
revision, with `refs/main` (and `refs/<ref>` when its models.json entry names a tag in `ref`) pointing at it, so the
tool finds it offline and nothing is downloaded or copied.

    python3 tools/cloud/runtime/hf_cache.py <models.json> <hub folder>
    HF_HUB_CACHE=<hub folder> HF_HUB_OFFLINE=1 <the tool>

Standard library only: it runs before any of the image's environments.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from weights import environment_name  # noqa: E402


def repo_folder(hub, repo):
    """The hub cache's folder for a model repository (`models--<org>--<name>`)."""
    return pathlib.Path(hub) / ("models--" + repo.replace("/", "--"))


def link_model(hub, repo, revision, folder, ref=None):
    """Link one model folder into the hub cache as `repo`'s snapshot at `revision`, its refs pointing at it."""
    place = repo_folder(hub, repo)
    (place / "snapshots").mkdir(parents=True, exist_ok=True)
    (place / "refs").mkdir(exist_ok=True)
    snapshot = place / "snapshots" / revision
    if snapshot.is_symlink() or snapshot.exists():
        snapshot.unlink()
    snapshot.symlink_to(pathlib.Path(folder).resolve(), target_is_directory=True)
    for name in filter(None, ("main", ref)):
        (place / "refs" / name).write_text(revision)
    return snapshot


def link_all(models_path, hub, environment=os.environ):
    """Every hf: model of the manifest that the job was handed, linked into the hub cache; the links made."""
    made = []
    for entry in json.loads(pathlib.Path(models_path).read_text()):
        kind, _, repo = entry["source"].partition(":")
        folder = environment.get(environment_name(entry["name"]))
        if kind == "hf" and folder:
            made.append(link_model(hub, repo, entry["revision"], folder, entry.get("ref")))
    return made


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    for link in link_all(sys.argv[1], sys.argv[2]):
        print(f"[hf_cache] {link}", flush=True)
