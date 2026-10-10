"""Runs on the rented machine (python3, standard library only): bring a job's inputs down from the object store and
unpack each where it lies on the coordinating machine. The other half of inputs.py.

    python3 /root/lib/input_fetch.py < request.json

The request, on standard input so its signed links never reach a command line or a log:
    {"cache": "/root/inputs", "items": [{"path": "/abs/folder", "key": "inputs/<sha256>.tar", "url": "<signed GET>"}]}

Each input is a tar named for the sha256 of its bytes. It is read in byte ranges side by side (RANGES_AT_ONCE of
RANGE_SIZE, each asked for again on a broken read), checked against its name, kept in the cache (a second job on
the same machine with the same input reads no byte from the store again) and unpacked into the input's parent
folder, over what is there, as rsync would. One JSON line a done input on standard output; any failure exits non-zero
and the coordinator sends what is left directly.
"""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tarfile
import time
import urllib.request

RANGE_SIZE = 16 * 1024 * 1024
RANGES_AT_ONCE = 16
RANGE_ATTEMPTS = 3
TIMEOUT_SECONDS = 120


def ranged(url, first, last):
    """The bytes first..last (both in) of the object, and the object's whole size."""
    request = urllib.request.Request(url, headers={"Range": f"bytes={first}-{last}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as answer:
        data = answer.read()
        total = int(answer.headers["Content-Range"].rsplit("/", 1)[1])
    return data, total


def range_into(url, path, first, last):
    """One range written into its place in the file, asked for again on a broken or short read."""
    for attempt in range(1, RANGE_ATTEMPTS + 1):
        try:
            data, _ = ranged(url, first, last)
        except OSError:
            if attempt == RANGE_ATTEMPTS:
                raise
            continue
        if len(data) == last - first + 1:
            descriptor = os.open(path, os.O_WRONLY)
            try:
                os.pwrite(descriptor, data, first)
            finally:
                os.close(descriptor)
            return
    raise OSError(f"bytes {first}-{last} came short {RANGE_ATTEMPTS} times")


def download(url, path):
    """The object at the signed link into `path`, its ranges side by side; its size."""
    if url.startswith("file://"):
        shutil.copyfile(url[len("file://"):], path)
        return path.stat().st_size
    _, total = ranged(url, 0, 0)
    with open(path, "wb") as target:
        target.truncate(total)
    starts = range(0, total, RANGE_SIZE)
    with concurrent.futures.ThreadPoolExecutor(RANGES_AT_ONCE) as pool:
        for done in [pool.submit(range_into, url, path, start, min(start + RANGE_SIZE, total) - 1) for start in starts]:
            done.result()
    return total


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while chunk := source.read(RANGE_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def cached(cache, item):
    """The input's tar in the machine's cache, downloaded and checked first when it is not there; whether it was."""
    name = item["key"].rsplit("/", 1)[-1]
    tar = cache / name
    if tar.exists():
        return tar, False
    partial = cache / (name + ".partial")
    download(item["url"], partial)
    found = sha256_of(partial)
    if f"{found}.tar" != name:
        partial.unlink()
        raise OSError(f"{item['key']} came down as {found}")
    partial.replace(tar)
    return tar, True


def unpack(tar, path):
    """The tar's one top entry (the input, by its own name) into the input's parent folder."""
    parent = pathlib.Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar) as archive:
        archive.extractall(parent, filter="tar")


def main():
    request = json.load(sys.stdin)
    cache = pathlib.Path(request.get("cache", "/root/inputs"))
    cache.mkdir(parents=True, exist_ok=True)
    for item in request["items"]:
        began = time.time()
        tar, fetched = cached(cache, item)
        unpack(tar, item["path"])
        print(json.dumps({"path": item["path"], "bytes": tar.stat().st_size, "fetched": fetched,
                          "seconds": round(time.time() - began, 1)}), flush=True)


if __name__ == "__main__":
    main()
