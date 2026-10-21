"""A cheap index of the store for the dashboard: the keys of its small areas walked once with os.scandir, answered by
prefix with bisect, kept fresh by rebuilding when older than MAX_AGE (one rebuild at a time; the old one serves
meanwhile). `answer_keys` makes every folder store of that root in this process read its keys from the current index
(the trick of Runner.still, for the process), so Store.accepted, records, judgements and waivers keep their exact
meaning without walking the whole store each call, a Store.default() a stage's `applies` makes included (the
neighbours stage's walked 14 s a call). The dashboard writes nothing there but through score.review.web.decide,
which rebuilds the index after."""
import bisect
import os
import threading
import time

AREAS = ("accepts", "rejects", "records", "judgements", "waivers")
MAX_AGE = 60.0


def walk(root, area):
    """Every key under one area of a folder store, as `<area>/...`, .partial files left out."""
    found = []
    stack = [(os.path.join(root, area), area)]
    while stack:
        folder, prefix = stack.pop()
        try:
            entries = list(os.scandir(folder))
        except FileNotFoundError:
            continue
        for entry in entries:
            key = f"{prefix}/{entry.name}"
            if entry.is_dir(follow_symlinks=False):
                stack.append((entry.path, key))
            elif not entry.name.endswith(".partial"):
                found.append(key)
    return found


class StoreIndex:
    """The sorted keys of AREAS at one moment, and the store that reads through them."""

    def __init__(self, store, keys, built_at, seconds):
        self.store = store
        self.keys = keys
        self.built_at = built_at
        self.seconds = seconds

    @classmethod
    def build(cls, store):
        """Walk the areas of a folder store and wrap it; the store's own `keys` answers other prefixes."""
        started = time.monotonic()
        root = str(store.objects.root)
        keys = sorted(key for area in AREAS for key in walk(root, area))
        return cls(store, keys, time.time(), time.monotonic() - started)

    def prefixed(self, prefix):
        """Every key starting with `prefix`, sorted."""
        start = bisect.bisect_left(self.keys, prefix)
        end = bisect.bisect_left(self.keys, prefix + "￿")
        return self.keys[start:end]

    def nodes(self, area):
        """The node folders one area holds."""
        return sorted({key.split("/")[1] for key in self.prefixed(f"{area}/")})


def answer_keys(folder_store_class, root, fresh):
    """Answer `keys` of every `folder_store_class` at `root` from `fresh`'s current index for AREAS prefixes; other
    roots and prefixes walk as before."""
    root = os.path.realpath(root)
    whole = folder_store_class.keys

    def keys(self, prefix):
        if os.path.realpath(self.root) != root:
            return whole(self, prefix)
        if fresh.current is not None and prefix.split("/")[0] in AREAS:
            return fresh.current.prefixed(prefix)
        return scoped(root, prefix) if "/" in prefix else whole(self, prefix)
    folder_store_class.keys = keys


def scoped(root, prefix):
    """The keys starting with `prefix`, walking only the folder it names (a draw's checks asked `concepts/<place>/`
    hundreds of times, each a walk of the whole store: 44 s a draw, 2026-10-21)."""
    folder = prefix.rsplit("/", 1)[0]
    return sorted(key for key in walk(root, folder) if key.startswith(prefix))


class Fresh:
    """The current index of a store, rebuilt in a background thread when older than MAX_AGE or when asked."""

    def __init__(self, make_store):
        self.make_store = make_store
        self.current = None
        self.lock = threading.Lock()
        self.building = False

    def rebuild(self):
        """Build a new index now and serve it from then on."""
        built = StoreIndex.build(self.make_store())
        self.current = built
        return built

    def rebuild_soon(self):
        """Start one background rebuild unless one is running."""
        with self.lock:
            if self.building:
                return
            self.building = True

        def work():
            try:
                self.rebuild()
            finally:
                self.building = False
        threading.Thread(target=work, daemon=True).start()

    def get(self):
        """The index to read: built now the first time, else the current one (a stale one starts a rebuild)."""
        if self.current is None:
            with self.lock:
                if self.current is None:
                    self.rebuild()
        elif time.time() - self.current.built_at > MAX_AGE:
            self.rebuild_soon()
        return self.current
