"""Copy the library's blobs from the cloud backend's object store into its public Hugging Face dataset repository
(score #141), by the library's own command `score-lib hub-mirror` with the object store's variables in its
environment only (library_files.cloud_store), never written or printed.

    python tools/library/hub_mirror.py <owner/name> [score-lib hub-mirror options: --public --deep N --check-only
                                                     --report <file>]

The write needs the standard Hugging Face login first (`hf auth login`, or HF_TOKEN). Each blob goes from the bucket
to the repository through memory; nothing is staged on this disk. A second run copies only what is missing.
"""
import os
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.library import library_files  # noqa: E402


def main(arguments):
    values = library_files.settings()
    if not values.get("SCORE_LIB_ROOT"):
        raise SystemExit("no library is configured (SCORE_LIB_ROOT, and no score_lib checkout beside score's)")
    environment = {**values, **library_files.cloud_store()}
    environment.pop("SCORE_LIB_BLOBS_DIR", None)
    environment.pop("SCORE_LIB_HUB_REPO", None)
    words = shlex.split(values.get("SCORE_LIB_COMMAND") or library_files.DEFAULT_COMMAND) + [
        "--root", values["SCORE_LIB_ROOT"], "hub-mirror", *arguments]
    os.chdir(values["SCORE_LIB_ROOT"])
    os.execvpe(words[0], words, environment)


if __name__ == "__main__":
    main(sys.argv[1:])
