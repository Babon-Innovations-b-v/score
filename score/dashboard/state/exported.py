"""The hosted source: the state export the store's machine pushed (sync/building.py), read with the same models as
the local source. It never imports score.stages, score.store, numpy or usd-core."""
import datetime
import json
import pathlib

from score.dashboard.state.files import HERO_SIDE, SHA, THUMB_SIDE
from score.dashboard.state.models import PlaceDetail, Spend, StepDetail, WorldState

WORLD_FILE = "_world"


class ExportedSource:
    name = "export"

    def __init__(self, folder):
        self.folder = pathlib.Path(folder)
        self.cache = {}

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

    def world_state(self, spend=None):
        found = self.loaded("state.json", lambda path: WorldState.model_validate_json(path.read_text()))
        return found or WorldState(made_at="", source="no export", world="world1", engines=[])

    def spend(self):
        return self.world_state().spend or Spend(note="no export")

    def places(self):
        return [card.place for engine in self.world_state().engines for style in engine.styles
                for card in style.places]

    def bundle(self, place):
        return self.loaded(f"places/{place or WORLD_FILE}.json", lambda path: json.loads(path.read_text()))

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
        for name in (f"{sha}.mp4", f"{sha}-{HERO_SIDE}.jpg", f"{sha}-{THUMB_SIDE}.jpg"):
            path = self.folder / "files" / name
            if path.is_file():
                return name, path
        return None

    def web3d_file(self, place, name):
        """A file of a place's fresh 3D web copy, or None."""
        path = self.folder / "web3d" / place / name
        return path if place in self.places() and path.is_file() else None

    def thumb_path(self, sha):
        if not SHA.match(sha or ""):
            return None
        for side in (THUMB_SIDE, HERO_SIDE):
            path = self.folder / "files" / f"{sha}-{side}.jpg"
            if path.is_file():
                return path
        return None

    def web3d(self, place):
        detail = self.place_detail(place)
        return detail.web3d if detail else None

    def stage_records(self, names):
        return []

