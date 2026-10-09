"""Compiled GPU kernel caches, kept per card and driver so that no node pays a first-use compile twice.

A program that compiles GPU code at first use keeps the result in the CUDA compute cache (and OptiX in its own
cache). Cycles in Blender 5.0.1 ships CUDA binaries up to sm_89 and sm_120 but none for the H100's sm_90, so the
driver compiles its PTX there: 218 s before an H100's first render (2026-10-09). A job that names a `kernel_cache`
(job.json, e.g. "blender-5.0.1") gets both caches pointed into the node cache, at
<cache>/kernels/<name>/<card>/{cuda,optix}, which later jobs on the node reuse; a node that has none restores them
first from the store's kernels/<name>/<card>.tar, and a job that leaves them larger than the store's copy uploads
them, so the next new node starts warm. <card> is the card's compute capability and driver (sm90-580.178.04): a
driver compiles for itself, and an H100 PCIe and an H100 SXM share one cache. The caches check their own entries, so
a stale entry is recompiled, never used wrongly.
"""
import fcntl
import os
import pathlib
import re
import subprocess
import tarfile
import time

import weights

# The CUDA compute cache's ceiling (its own default, 256 MB, is smaller than Cycles' kernels for one card).
CACHE_BYTES = 4 << 30
SIZE_SUFFIX = ".bytes"


def card_key():
    """The node's first card's compute capability and driver as one name (sm90-580.178.04), or None on a processor
    node."""
    try:
        answer = subprocess.run(["nvidia-smi", "--query-gpu=compute_cap,driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = answer.stdout.strip().splitlines() if answer.returncode == 0 else []
    if not lines:
        return None
    capability, driver = (part.strip() for part in lines[0].split(","))
    return re.sub(r"[^a-z0-9.-]+", "", f"sm{capability.replace('.', '')}-{driver}".lower())


def folder(cache, name, card):
    return cache / "kernels" / name / card


def store_key(name, card):
    return f"kernels/{name}/{card}.tar"


def environment(cache, name, card):
    """The variables that point the CUDA and OptiX caches into the node cache."""
    root = folder(cache, name, card)
    return {"CUDA_CACHE_PATH": str(root / "cuda"), "CUDA_CACHE_MAXSIZE": str(CACHE_BYTES),
            "OPTIX_CACHE_PATH": str(root / "optix"), "OPTIX_CACHE_MAXSIZE": str(CACHE_BYTES)}


def size_of(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) if root.exists() else 0


def locked(cache, name, card):
    """An open lock file for the card's caches, held exclusively."""
    (cache / "locks").mkdir(parents=True, exist_ok=True)
    lock = open(cache / "locks" / f"kernels-{name}-{card}.lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    return lock


def restore(store, name, card, cache):
    """Bring the card's caches from the store onto a node that has none; True when it did."""
    root = folder(cache, name, card)
    with locked(cache, name, card):
        if size_of(root) or not store.exists(store_key(name, card)):
            root.mkdir(parents=True, exist_ok=True)
            return False
        tar = cache / "partial" / f"kernels-{card}-{os.getpid()}-{time.time_ns()}.tar"
        root.mkdir(parents=True, exist_ok=True)
        store.download(store_key(name, card), tar)
        try:
            with tarfile.open(tar) as archive:
                archive.extractall(root, filter="data")
        finally:
            tar.unlink()
    return True


def stored_size(store, name, card):
    key = store_key(name, card) + SIZE_SUFFIX
    return int(store.read_bytes(key)) if store.exists(key) else 0


def keep(store, name, card, cache):
    """Upload the card's caches when the node's are larger than the store's copy; the bytes uploaded, or 0."""
    root = folder(cache, name, card)
    with locked(cache, name, card):
        size = size_of(root)
        if size <= stored_size(store, name, card):
            return 0
        tar = cache / "partial" / f"kernels-{card}-{os.getpid()}-{time.time_ns()}.tar"
        tar.parent.mkdir(parents=True, exist_ok=True)
        try:
            weights.pack(root, tar)
            store.upload(tar, store_key(name, card))
            store.write_bytes(store_key(name, card) + SIZE_SUFFIX, str(size).encode())
        finally:
            tar.unlink(missing_ok=True)
    return size
