"""The truth's command line (see `__init__.py`): `pick` writes the set file, `read <address>` prints one summary line."""
import argparse
import json
import subprocess
import sys

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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m tools.props.bench.truth")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pick")
    one = commands.add_parser("read")
    one.add_argument("address")
    args = parser.parse_args(argv)
    if args.command == "pick":
        pick()
    else:
        summary(args.address)


if __name__ == "__main__":
    sys.exit(main())
