"""The hosted source: the state export the store's machine pushed (sync/building.py), read with the same models as
the local source. It never imports score.stages, score.store, numpy or usd-core."""
import datetime
import json
import pathlib

from score.dashboard.state.files import HERO_SIDE, SHA, THUMB_SIDE
from score.dashboard.state.models import PlaceDetail, Spend, StepDetail, WorldState

WORLD_FILE = "_world"
# The format before the 2026-10-20 rename (CONTEXT.md "gap"): its `holes` are today's gaps and a place's `gaps` its
# accepted gaps. The hosted side reads its last such export in today's words until the next one is swapped in.
RENAMED_FORMAT = 2


def in_todays_words(value):
    """A record of a RENAMED_FORMAT export with its keys in today's words, at every depth."""
    if isinstance(value, list):
        return [in_todays_words(item) for item in value]
    if not isinstance(value, dict):
        return value
    accepted = "holes" in value
    return {("accepted_gaps" if accepted and key == "gaps" else key.replace("hole", "gap")): in_todays_words(item)
            for key, item in value.items()}


class ExportedSource:
    name = "export"

    def __init__(self, folder, results=None):
        """The export in `folder`; `results` the folder of the pictures the owner's requests brought back since
        (a concept review's draws, sync/endpoints.py), served beside the export's own."""
        self.folder = pathlib.Path(folder)
        self.results = pathlib.Path(results) if results else None
        self.cache = {}

    def picture_folders(self):
        return [self.folder / "files"] + ([self.results] if self.results else [])

    def manifest(self):
        path = self.folder / "manifest.json"
        return json.loads(path.read_text()) if path.is_file() else None

    def loaded(self, name, read):
        """`read(path)` of an export file, kept until the export is swapped (its made_at changes)."""
        manifest = self.manifest() or {}
        if self.cache.get("made_at") != manifest.get("made_at"):
            self.cache = {"made_at": manifest.get("made_at")}
        if name not in self.cache:
            path = self.folder / name
            self.cache[name] = read(path) if path.is_file() else None
        return self.cache[name]

    def read_json(self, path):
        """An export file's JSON, in today's words when the export is of RENAMED_FORMAT."""
        found = json.loads(path.read_text())
        return in_todays_words(found) if (self.manifest() or {}).get("format") == RENAMED_FORMAT else found

    def read_at(self):
        manifest = self.manifest()
        return manifest["made_at"] if manifest else "no export yet"

    def age_words(self):
        """"state from <made_at> (N minutes ago)", or that no export has arrived."""
        manifest = self.manifest()
        if not manifest:
            return "no state export has arrived yet"
        made = datetime.datetime.fromisoformat(manifest["made_at"])
        minutes = int((datetime.datetime.now(datetime.timezone.utc) - made).total_seconds() // 60)
        return f"state from {manifest['made_at'][:16].replace('T', ' ')} ({minutes} minutes ago)"

    def refresh(self):
        self.cache = {}

    def machine(self):
        """The store's machine as the export carries it (machine.json, state/machine.py), or None before one."""
        return self.loaded("machine.json", lambda path: json.loads(path.read_text()))

    def batch_run(self):
        """The newest Buy's batch (batch-run.json, state/batch_run.py), only the store's machine's (store_batch):
        the export's, or the one the listener sent since (sync/endpoints.batch_run, in `results`) when read later;
        None before one."""
        from score.dashboard.state import batch_run
        from score.dashboard.sync import one_store
        manifest = self.manifest() or {}
        exported = self.loaded(batch_run.RUN_FILE, lambda path: json.loads(path.read_text()))
        sent = self.results / batch_run.RUN_FILE if self.results else None
        pushed = json.loads(sent.read_text()) if sent and sent.is_file() else None
        return store_batch(manifest, exported, pushed, one_store.record().get("name") or manifest.get("machine"))

    def export_made_at(self):
        """When the store's machine made the export shown, or None before one arrived."""
        return (self.manifest() or {}).get("made_at")

    def world_state(self, spend=None):
        found = self.loaded("state.json", lambda path: WorldState.model_validate(self.read_json(path)))
        return found or WorldState(made_at="", source="no export", world="world1", engines=[])

    def spend(self):
        return self.world_state().spend or Spend(note="no export")

    def places(self):
        return [card.place for engine in self.world_state().engines for style in engine.styles
                for card in style.places]

    def bundle(self, place):
        return self.loaded(f"places/{place or WORLD_FILE}.json", self.read_json)

    def place_detail(self, place):
        bundle = self.bundle(place)
        return PlaceDetail.model_validate(bundle["detail"]) if bundle and bundle.get("detail") else None

    def place_card(self, place):
        return next((card for engine in self.world_state().engines for style in engine.styles
                     for card in style.places if card.place == place), None)

    def step_detail(self, place, stage):
        bundle = self.bundle(place)
        found = (bundle or {}).get("steps", {}).get(stage)
        return StepDetail.model_validate(found) if found else None

    def file(self, sha):
        """(name, path) of an exported file: a film, else the largest picture of it."""
        if not SHA.match(sha or ""):
            return None
        for folder in self.picture_folders():
            for name in (f"{sha}.mp4", f"{sha}-{HERO_SIDE}.jpg", f"{sha}-{THUMB_SIDE}.jpg"):
                if (folder / name).is_file():
                    return name, folder / name
        return None

    def web3d_file(self, place, name):
        """A file of a place's fresh 3D web copy, or None."""
        path = self.folder / "web3d" / place / name
        return path if place in self.places() and path.is_file() else None

    def thumb_path(self, sha):
        if not SHA.match(sha or ""):
            return None
        for folder in self.picture_folders():
            for side in (THUMB_SIDE, HERO_SIDE):
                if (folder / f"{sha}-{side}.jpg").is_file():
                    return folder / f"{sha}-{side}.jpg"
        return None

    def web3d(self, place):
        detail = self.place_detail(place)
        return detail.web3d if detail else None


    def gaps(self, place):
        """The place's gaps as its exported detail carries them; [] for a place the export lacks."""
        detail = self.place_detail(place)
        return detail.gaps if detail else []


def store_batch(manifest, exported, pushed, store):
    """The batch record to show (owner 2026-10-24: a moved or reset store kept showing an old batch): none when the
    export is not the store's machine's (`store`, sync/one_store.py); else the export's or the listener's
    (pushed_current), whichever was read later."""
    if (manifest.get("machine") or "") != (store or ""):
        return None
    found = [run for run in (exported, pushed if pushed_current(manifest, exported, pushed, store) else None) if run]
    return max(found, key=lambda run: moment(run["read_at"])) if found else None


def pushed_current(manifest, exported, pushed, store):
    """Whether the listener's record still holds: sent by the store's machine, and of the newest checkout the
    export names (none after a reset) or read after the export (a Buy since)."""
    if not pushed or (pushed.get("machine") or "") != (store or ""):
        return False
    made = manifest.get("made_at")
    return (not made or pushed.get("checkout") == (exported or {}).get("checkout")
            or moment(pushed["read_at"]) > moment(made))


def moment(stamp):
    """An ISO time as an aware time (a time without a zone read as UTC)."""
    found = datetime.datetime.fromisoformat(stamp)
    return found if found.tzinfo else found.replace(tzinfo=datetime.timezone.utc)
