"""Checks for the store's multipart part size: small files keep boto3's 8 MB parts, a large model tar gets parts
large enough to stay within the 1,000 parts an S3-compatible store allows (a 15 GB tar failed at 8 MB parts).

Run: .venv/bin/python tools/cloud/runtime/store_test.py   (make tests runs it)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import store as stores  # noqa: E402

MEGABYTE = 1024 * 1024


def test_a_small_file_keeps_eight_megabyte_parts():
    assert stores.part_size(1) == 8 * MEGABYTE
    assert stores.part_size(5 * 1024 * MEGABYTE) == 8 * MEGABYTE


def test_a_large_file_fits_in_the_parts_allowed():
    for size in (8 * 1024 * MEGABYTE, 16 * 1024 * MEGABYTE, 200 * 1024 * MEGABYTE + 7):
        part = stores.part_size(size)
        assert part % MEGABYTE == 0
        assert -(-size // part) <= stores.MOST_PARTS


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
