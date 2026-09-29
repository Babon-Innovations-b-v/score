"""Cut a batch's pictures out of their backgrounds in one process, so the model loads once.

    <image-to-3dlab>/.venv/bin/python cut_outs.py <picture> <destination> [<picture> <destination> ...]

Run with image-to-3dlab's Python from its own folder; batch.py does. It uses the same cut-out as
pixal.py (BiRefNet-lite, on the processor) and prints each destination the moment it is written, so
the runner can send that picture to a machine while the rest are still being cut.
"""
import pathlib
import sys

sys.path.insert(0, "scripts")
from pixal3d_generate import matte  # noqa: E402


def main():
    pairs = sys.argv[1:]
    for picture, destination in zip(pairs[::2], pairs[1::2]):
        matte(pathlib.Path(picture), pathlib.Path(destination))
        print(destination, flush=True)


if __name__ == "__main__":
    main()
