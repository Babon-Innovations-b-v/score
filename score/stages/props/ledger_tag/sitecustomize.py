"""Every ledger line a process writes, tagged with SCORE_LEDGER_TAG: the cloud ledger's (tools/props/cloud/ledger.py
`record`) and Google's (google_spend.py `write`), so a run's euros count apart from every other line's.

Python imports `sitecustomize` at start-up from the path, so a process started with this folder on PYTHONPATH and the
tag set tags whatever it and its children write, the rented-machine runners included; `install()` does the same in a
process already running. The ledgers' own files are not edited: their code is in other stages' code versions.
"""
import importlib.abc
import importlib.machinery
import os
import sys

TAG = "SCORE_LEDGER_TAG"


def tag_cloud(module):
    """ledger.record with the tag on each batch's line."""
    if hasattr(module, "entries") and not getattr(module.record, "tagged", False):
        original = module.record

        def record(entry):
            return original({**entry, "tag": os.environ[TAG]})
        record.tagged = True
        module.record = record


def tag_google(module):
    """google_spend.write with the tag on each call's line."""
    if hasattr(module, "write") and not getattr(module.write, "tagged", False):
        original = module.write

        def write(entry):
            return original({**entry, "tag": os.environ[TAG]})
        write.tagged = True
        module.write = write


WRAP = {"ledger": tag_cloud, "google_spend": tag_google}


class Tagging(importlib.abc.MetaPathFinder):
    """Wraps the ledgers as they are imported."""

    def find_spec(self, name, path, target=None):
        if name not in WRAP:
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or spec.loader is None:
            return spec
        run = spec.loader.exec_module

        def exec_module(module):
            run(module)
            WRAP[name](module)
        spec.loader.exec_module = exec_module
        return spec


def install():
    """Tag from here on in this process: the ledgers already imported, and every later import."""
    for name, wrap in WRAP.items():
        if name in sys.modules:
            wrap(sys.modules[name])
    if not any(isinstance(finder, Tagging) for finder in sys.meta_path):
        sys.meta_path.insert(0, Tagging())


if os.environ.get(TAG):
    install()
