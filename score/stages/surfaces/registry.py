"""The finish registry: the world's one shared, append-only list of the new library surfaces a method proposed
(the finish-map method: a finish Gemini found no library surface for), each standing as first proposed, for the owner
to accept into the library or not. It is a store item (score/store: registry/surfaces/), not a file anywhere else.
Until the owner accepts a proposal, the part keeps the nearest library surface the method named (`stands_in`).

    registry = Registry(store)
    registry.propose_surface(name, spec, origin)       # the standing entry: the first proposal of a name

An entry is never changed or removed; every read, decide and append holds the store's registry lock. The paint
writes it outside its node's key: a proposal never changes a surface a part was given.
"""
import datetime
import re


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Registry:
    def __init__(self, store):
        self.store = store

    def propose_surface(self, name, spec, origin):
        """A new library surface (its spec: what the method said of it, its status and the surface standing in)
        proposed under `name`; the standing entry, the first proposal of that name (names alike but for case and
        punctuation are one: "Polished Chrome" and "polished chrome" share one entry id)."""
        with self.store.registry_lock():
            standing = next((entry for entry in self.store.registry("surfaces")
                             if entry_id(entry["name"]) == entry_id(name)), None)
            if standing is None:
                standing = {"name": name, "spec": spec, "first": origin, "at": now()}
                self.store.write_registry("surfaces", entry_id(name), standing)
        return standing


def entry_id(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
