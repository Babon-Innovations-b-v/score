"""The finish registry: the world's one shared, append-only list giving each finish group exactly one library surface,
so the same finish is the same surface in every place without a world-wide wait (owner, 2026-10-11). It is a store
item (score/store: registry/finishes/, registry/surfaces/), not a file anywhere else.

    registry = Registry(store, seeded)                 # seeded: the hub picks' groups (seed.py), read first
    registry.surfaces_for([(finish, judge name, origin), ...])   # each part's (group, surface, matched, apart)
    registry.propose_surface(name, spec, origin)       # a new library surface; the first proposal of a name stands

A finish is what a method measures over a part (g-texture: the raw texture's unlit L*, a*, b*, metalness and
roughness over the part's core faces, each feature's median and spread). A part's finish matches a group when the two
lie under SEPARABLE apart (separation: the texture cannot tell them apart); the nearest matching group gives the part
its surface, whatever the judge named for it. With none matching, a new group is appended with the judge's name as its
surface; a part the judge named nothing for and no group matches gets none. The owner's picks seed the registry (the
hub's picked models, round six): their groups are read before every appended one and are never replaced. An entry is
never changed or removed; every read, decide and append holds the store's registry lock.

A paint reads the registry outside its node's key: an appended group never changes a surface already given, and each
painted part records the group it took, so `why` and the page show where every surface came from.
"""
import datetime

FEATURES = ("L*", "a*", "b*", "metal", "rough")
SEPARABLE = 2.0  # measure.SEPARABLE: two finishes closer than this are one finish to the texture


def separation(first, second):
    """How far apart two finishes ((centre, spread) per feature, None where unknown) lie: measure.separation."""
    total, known = 0.0, 0
    for centre_a, spread_a, centre_b, spread_b in zip(first[0], first[1], second[0], second[1]):
        if centre_a is None or centre_b is None:
            continue
        total += ((centre_a - centre_b) / (spread_a ** 2 + spread_b ** 2) ** 0.5) ** 2
        known += 1
    return total ** 0.5 if known else float("inf")


def cleaned(values):
    """Floats rounded for the record, None for an unknown (NaN) feature."""
    return [None if value is None or value != value else round(float(value), 4) for value in values]


def nearest(groups, finish):
    """The nearest group under SEPARABLE from `finish`, and its separation; (None, separation) when none is."""
    best, best_apart = None, float("inf")
    for group in groups:
        apart = separation(finish, (group["centre"], group["spread"]))
        if apart < best_apart:
            best, best_apart = group, apart
    return (best, best_apart) if best_apart < SEPARABLE else (None, best_apart)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Registry:
    def __init__(self, store, seeded=()):
        self.store = store
        self.seeded = list(seeded)

    def groups(self):
        """The seeded groups, then every appended one in order."""
        return [*self.seeded, *self.store.registry("finishes")]

    def surfaces_for(self, asked):
        """For each (finish, judge name or None, origin) in order: (group id, surface, matched an existing group,
        separation), or None for a finish no group matches that the judge named nothing for. One lock for the list:
        a group appended for one part is there for the next."""
        found = []
        with self.store.registry_lock():
            groups = self.groups()
            for finish, judge_name, origin in asked:
                finish = (cleaned(finish[0]), cleaned(finish[1]))
                group, apart = nearest(groups, finish)
                if group is not None:
                    found.append((group["id"], group["surface"], True, round(apart, 3)))
                    continue
                if judge_name is None:
                    found.append(None)
                    continue
                group = {"id": f"F{len(groups) - len(self.seeded) + 1:04d}", "surface": judge_name,
                         "judge": judge_name, "centre": finish[0], "spread": finish[1], "first": origin, "at": now()}
                self.store.write_registry("finishes", group["id"], group)
                groups.append(group)
                found.append((group["id"], judge_name, False, None))
        return found

    def propose_surface(self, name, spec, origin):
        """A new library surface (its spec as data/library writes one) proposed under `name`; the standing entry,
        the first proposal of that name."""
        with self.store.registry_lock():
            standing = next((entry for entry in self.store.registry("surfaces") if entry["name"] == name), None)
            if standing is None:
                standing = {"name": name, "spec": spec, "first": origin, "at": now()}
                self.store.write_registry("surfaces", name, standing)
        return standing
