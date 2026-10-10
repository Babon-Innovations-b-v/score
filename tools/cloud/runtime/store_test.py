"""Checks for the store's multipart part size: small files keep boto3's 8 MB parts, a large model tar gets parts
large enough to stay within the 1,000 parts an S3-compatible store allows (a 15 GB tar failed at 8 MB parts); an
object read in ranges side by side comes out whole and in order, a broken range asked for again.

Run: .venv/bin/python tools/cloud/runtime/store_test.py   (make tests runs it)
"""
import io
import os
import pathlib
import sys
import tempfile

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


class Body:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FlakyBucket:
    """A bucket client whose object breaks off the first read of every range."""

    def __init__(self, data):
        self.data = data
        self.broken = set()

    def get_object(self, Bucket, Key, Range):  # noqa: N803 - boto3's names
        first, last = (int(number) for number in Range.removeprefix("bytes=").split("-"))
        if first not in self.broken:
            self.broken.add(first)
            return {"Body": Body(self.data[first:last])}
        return {"Body": Body(self.data[first:last + 1])}


def test_ranges_read_side_by_side_give_the_object_in_order():
    data = os.urandom(5 * 1024 * 1024 + 3)
    real = stores.RANGE_SIZE
    stores.RANGE_SIZE = 64 * 1024
    try:
        reader = io.BufferedReader(stores.RangeReader(FlakyBucket(data), "bucket", "key", len(data)), 1 << 20)
        assert reader.read() == data
        reader.close()
    finally:
        stores.RANGE_SIZE = real


def test_a_folder_store_reads_its_files_whole():
    folder = pathlib.Path(tempfile.mkdtemp())
    store = stores.FolderStore(folder)
    store.write_bytes("weights/a.tar", b"abc")
    assert store.size("weights/a.tar") == 3
    with store.reader("weights/a.tar") as reader:
        assert reader.read() == b"abc"


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
