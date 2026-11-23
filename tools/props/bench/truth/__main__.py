"""The truth's command line (see `__init__.py`): `pick` writes the set file, `read <address>` prints one summary line,
`picture <png>` keeps a pictured case's close-up as a store object (its blob in the store bucket), printing its hash."""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from score import library
from tools.props.bench import truth
from tools.props.bench.truth import _read


def pick():
    """The rule run on the library checkout SCORE_LIB_ROOT (else score_lib's beside score's), written to SET_FILE."""
    root = library.root_from_environment() or _read.library_files.default_root()
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()
    found = truth.picked(root, commit)
    truth.SET_FILE.write_text(json.dumps(found, indent=1) + "\n")
    splits = [item["split"] for item in found["objects"]]
    print(f"set: {len(splits)} objects ({splits.count('tune')} tune, {splits.count('held-out')} held-out) on "
          f"score_lib {commit[:9]} -> {truth.SET_FILE}")


def summary(address):
    """One line of the object's truth."""
    found = truth.read(address)
    hulls = {key: len(shapes) for key, shapes in found["payloads"].items()}
    surfaces = sum(item["surface"] is not None for item in found["materials"])
    print(f"{found['address']}: {len(found['faces'])} triangles, size {[round(side, 3) for side in found['size']]}"
          f" m, {len(found['materials'])} materials ({surfaces} with a surface), mass {found['mass']} kg in "
          f"{len(found['bodies'])} bodies, colliders {hulls}")


def picture(path):
    """The close-up kept as a store output holding `closeup.png`, its blob sent to the store bucket; its hash."""
    from score.store import Store, offload
    offload.install()
    store, bucket = Store.default(), offload.open_bucket()
    with tempfile.TemporaryDirectory() as folder:
        shutil.copyfile(path, pathlib.Path(folder) / "closeup.png")
        output = store.put_tree(folder)
    for sha in sorted(set(store.listing(output).values())):
        offload.push(store.objects.path(f"blobs/{sha}"), sha, bucket)
    print(output)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m tools.props.bench.truth")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pick")
    one = commands.add_parser("read")
    one.add_argument("address")
    kept = commands.add_parser("picture")
    kept.add_argument("png")
    args = parser.parse_args(argv)
    if args.command == "pick":
        pick()
    elif args.command == "picture":
        picture(args.png)
    else:
        summary(args.address)


if __name__ == "__main__":
    sys.exit(main())
