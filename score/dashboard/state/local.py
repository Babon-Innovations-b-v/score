"""The local source: the store beside the dashboard, read directly and read-only through a cheap index
(state/index.py), with the stage table and the world's data for the groups. Everything shown comes from what the
store holds; what the cheap path cannot say (whether an accepted output is still current) is left to the freshness
snapshot, a background `score status`.

Writes nothing to the store: owner decisions go through score.review.web.decide, called by the pages and the API.
"""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter

from score import review, stages
from score.dashboard.state import accepted_gaps as named, groups, plain
from score.dashboard.state.files import THUMB_SIDE, Known, file_ref, kind_of, packaged, thumbnail
from score.dashboard.state.gaps import kind_of as gap_kind
from score.dashboard.state.index import Fresh, answer_keys
from score.dashboard.state.models import (CheckFinding, ConceptDraw, ConceptWording, EngineGroup, GateCounts, GateVerdict, GapsPrice,
                                          GapsTotal, InputPicture, LayerGroup, PlaceCard, PlaceDetail, Remake, Spend,
                                          StepCard, StepDetail, StoppedStep, StyleGroup, Taken, UsdIndex, UsdLayer, WorldState)
from score.store import Store, stamp_key

REPO = pathlib.Path(__file__).resolve().parents[3]
SUBLAYER = re.compile(r"@\./(layers/[^@]+)@")
FPS = re.compile(r"framesPerSecond = ([0-9.]+)")
LOG_LINES = 40
# Where standalone checks write each place's findings, in the work folder: checks/<check>/<place>/findings.json
# ({"outputs": {node: the output judged}, "findings": [{"rule", "prim", "sentence", "picture"}]}).
CHECKS = "checks"
GAPS = "gaps"  # the gaps check (score/stages/complete/gaps): its findings are the place's gaps, listed apart
GAP_FIELDS = ("id", "row", "gates", "source", "node", "work", "placed", "low", "high")
GAPS_PRICE = "gaps-price"  # every gap's chain priced: checks/gaps-price/<world>.json (score price --gaps)
PER_UNIT = "data/costs/per-unit.json"  # the measured per-unit prices a gaps price record is made on
TIMED = ("accepts/", "rejects/")  # store areas whose keys carry their time: an accept or reject moves what stands
REMAKE = "prepare/remake.json"  # prepare's one-shot figure of the remake (score/stages/complete/prepare)
GAPS_WORLD = "world"  # the gaps check's pseudo-place of the environment's own nodes' lost inputs (gaps/__main__)


def priced_here():
    """{commit, per_unit_sha256} of this checkout: its commit (None when it cannot be read) and the per-unit
    prices' sha256, what a gaps price record made now would carry (score/stages/complete/gaps/price.py
    priced_on)."""
    done = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True)
    return {"commit": done.stdout.strip() if done.returncode == 0 else None,
            "per_unit_sha256": hashlib.sha256((REPO / PER_UNIT).read_bytes()).hexdigest()}


def code_moved(priced_on):
    """Why a gaps price made on `priced_on` (its record's) does not price this checkout's code, or None."""
    if not priced_on:
        return "it was made before the price recorded its code"
    if priced_on.get("uncommitted"):
        return "it was made on code not committed"
    here = priced_here()
    if here["commit"] is None or priced_on.get("commit") != here["commit"]:
        return (f"the code moved since it was made (commit {str(priced_on.get('commit'))[:8]}, "
                f"now {str(here['commit'])[:8]})")
    if priced_on.get("per_unit_sha256") != here["per_unit_sha256"]:
        return f"the per-unit prices ({PER_UNIT}) changed since it was made"
    return None


def take_counts(takes):
    """{takes, bought, made, library, predicted_gaps, blocked} of prepare's takes: each by its status, `blocked` the
    bought ones that wait on a lost input."""
    found = Counter(take["status"] for take in takes)
    return {"takes": len(takes), "bought": found["bought"], "made": found["made"], "library": found["library"],
            "predicted_gaps": found["predicted gap"],
            "blocked": sum(1 for take in takes if take["status"] == "bought" and take.get("inputs"))}


def remake_of(written):
    """A Remake of prepare's record: its figure, ETA and take counts, each place's takes, stale by its code."""
    eta = written.get("eta") or {}
    by_place = {}
    for take in written.get("takes", []):
        by_place.setdefault(take["place"], []).append(take)
    totals = written.get("totals") or {}
    return Remake(made_at=written["made_at"], priced_on=written.get("priced_on") or {},
                  likely_euros=totals.get("likely_euros"), high_euros=totals.get("high_euros"),
                  unpriced=totals.get("unpriced") or [],
                  eta={"likely_minutes": eta.get("likely_minutes"), "high_minutes": eta.get("high_minutes"),
                       "at_least_minutes": eta.get("at_least_minutes"), "untimed": len(eta.get("unknown") or [])},
                  counts=take_counts(written.get("takes", [])),
                  places={place: take_counts(takes) for place, takes in sorted(by_place.items())},
                  layers=layers_of(written), design=written.get("design") or {},
                  stale=code_moved(written.get("priced_on")))


def layers_of(written):
    """{stage: {takes, likely, high, places: {place: takes}, waits: {place: {why: takes}}}} of prepare's layers, its
    price as written (None while the stage has no measured per unit), each place's takes that wait on an input by
    why (WAITS). A layer runs every bought take or only the whole models (no shell piece)."""
    bought = [take for take in written.get("takes", []) if take["status"] == "bought"]
    found = {}
    for stage, layer in (written.get("layers") or {}).items():
        # prepare writes no layer's places: one with fewer takes than bought runs the whole models only (SHELL_ROUTE)
        runs = bought if layer["takes"] == len(bought) else [take for take in bought if not take.get("shell")]
        price = layer.get("price") or {}
        waits = {}
        for take in runs:
            if take.get("inputs"):
                why = waits.setdefault(take["place"], {})
                why[wait_of(take["inputs"][0])] = why.get(wait_of(take["inputs"][0]), 0) + 1
        found[stage] = {"takes": layer["takes"], "likely": price.get("likely_euros"), "high": price.get("high_euros"),
                        "places": dict(Counter(take["place"] for take in runs)), "waits": waits}
    return found


# What a take's first broken input says (prepare's contract.py), in plain words for the Buy screen.
WAITS = (("picture is not in the work folder", "lost concept views"), ("box of four numbers", "no box on its view"),
         ("not one of the plan's views", "a view its plan lacks"), ("size of three sides", "no size measured"))


def wait_of(words):
    return next((plain for phrase, plain in WAITS if phrase in words), "an input missing")


def written_at(path):
    """When a file was last written (its mtime in nanoseconds), None when it is not there."""
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return None


def lost_once(gaps):
    """The gaps with each lost input (`<rule>:lost:...`, its id names the thing) once however many places read it,
    as the gaps check's summary counts them (gaps/inputs.py `distinct`); every other gap as it is."""
    seen, found = set(), []
    for gap in gaps:
        if gap.id.partition(":")[2].startswith("lost:"):
            if gap.id in seen:
                continue
            seen.add(gap.id)
        found.append(gap)
    return found


HISTORY = 6
# Which stage makes each sublayer of a place's OpenUSD stage (score/stages/assembly/record.py ORDER).
LAYER_MAKERS = {"edit": None, "characters": "characters-layer", "sound": "sound", "light": "light",
                "motion": "motion", "effects": "effects-layer", "crops": "crops-layer", "motion-models": "motion-models",
                "settle": "settle", "ground": "terrain", "base": "scene-record"}
LAYER_FILES = tuple(LAYER_MAKERS)
ACCEPTED, WAITING, STOPPED, NOT_RUN = "accepted", "waiting", "stopped", "not run"
STILL_NAME = "still.jpg"
STEP_DRAWING = "preview.png"  # previews.PREVIEW_NAME: a step's picture drawn from its files


def stamp(seconds):
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).isoformat(timespec="seconds")


def tail(path, lines=LOG_LINES):
    """The last lines of a text file, or None when there is none."""
    path = pathlib.Path(path)
    if not path.is_file():
        return None
    with path.open("rb") as source:
        source.seek(max(0, path.stat().st_size - 64 * 1024))
        return "\n".join(source.read().decode(errors="replace").splitlines()[-lines:])


def verdict_list(judgement, waived):
    """Each gate of a judgement as a GateVerdict, a waiver's reason beside the gate it waives."""
    if not judgement:
        return []
    return [GateVerdict(name=name, answer=verdict["answer"], reason=verdict.get("reason", ""),
                        measures=verdict.get("measures") or {},
                        waived=(waived.get(name) or {}).get("reason") if name in waived else None)
            for name, verdict in judgement["verdicts"].items()]


def counts(judgement):
    """GateCounts of a judgement's verdicts."""
    answers = [verdict["answer"] for verdict in (judgement or {}).get("verdicts", {}).values()]
    return GateCounts(**{"pass": answers.count("pass")}, fail=answers.count("fail"),
                      unknown=answers.count("unknown"))


class LocalSource:
    """The store at `props_home/store` and world 1's data, for the pages and the API."""

    name = "store"

    def __init__(self, props_home, home, web_copies, store_root=None, world=None, rows=None):
        """World 1 and the framework's store at props_home/store unless told otherwise (a test's store and world)."""
        self.props_home = pathlib.Path(props_home)
        self.home = pathlib.Path(home)
        self.web_copies = pathlib.Path(web_copies)
        self.store_root = pathlib.Path(store_root or self.props_home / "store")
        self.fresh = Fresh(lambda: Store.in_folder(self.store_root))
        self.rows_at = {}
        answer_keys(type(self.fresh.make_store().objects), self.store_root / "objects", self.fresh)
        self.known = Known()
        self.memo = {}
        self.world = world or stages.world1()
        self.data = pathlib.Path(self.world.roots["data"])
        self.rows = rows or stages.STAGES
        self.by_name = {row.name: row for row in self.rows}
        self.layer_of = groups.layers(self.rows)
        self.readers = groups.readers_of(self.rows)

    # --- the index and what it was read at ---------------------------------------------------------------------

    @property
    def index(self):
        index = self.fresh.get()
        if self.memo.get("built_at") != index.built_at:
            self.memo = {"built_at": index.built_at}
        return index

    @property
    def store(self):
        return self.index.store

    def read_at(self):
        return stamp(self.index.built_at)

    def refresh(self):
        """Read the store again now, and which stages apply to each place."""
        self.fresh.rebuild()
        self.rows_at = {}

    def remembered(self, key, work):
        """`work()` once per index build and key (a key may carry when its files were written, so it is read again
        once they change)."""
        self.index  # noqa: B018  (a new build clears what was remembered)
        if key not in self.memo:
            self.memo[key] = work()
        return self.memo[key]

    # --- places and nodes --------------------------------------------------------------------------------------

    def places(self):
        return stages.places(self.world)

    def looks(self):
        path = self.data / "definitions/place.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def place_rows(self, place):
        """The place stages that apply to a place, in table order."""
        if place not in self.rows_at:
            self.index  # noqa: B018  (applies may read the store: through the index)
            self.rows_at[place] = [row for row in self.rows
                                   if row.grain == "place" and (row.applies is None or row.applies(place))]
        return self.rows_at[place]

    def world_rows(self):
        return [row for row in self.rows if row.grain == "world"]

    @staticmethod
    def node_of(stage, place):
        return stage if place is None else f"{stage}@{place}"

    def fault_time(self, node):
        path = self.store_root / "faults" / f"{node}.txt"
        return path.stat().st_mtime if path.is_file() else None

    def node_state(self, node):
        """(state, words) from the store alone: stopped when its fault report is newer than its accept, else
        accepted, else waiting when it has an output, else not run."""
        return self.remembered(("state", node), lambda: self.worked_state(node))

    def worked_state(self, node):
        accept = self.store.current_accept(node)
        fault = self.fault_time(node)
        accepted_at = datetime.datetime.fromisoformat(accept["at"]).timestamp() if accept else None
        if fault and (accepted_at is None or fault > accepted_at):
            return STOPPED, f"stopped {stamp(fault)[:16].replace('T', ' ')}: its fault report says why"
        if accept:
            return ACCEPTED, accept.get("status") or f"accepted {accept['at'][:10]} by {accept['by']}"
        if self.index.prefixed(f"records/{node}/"):
            return WAITING, "made; its output waits (it did not pass, or it is worse)"
        return NOT_RUN, "not run yet"

    def shown_record(self, node):
        """The record of the accepted output, else the newest record, else None."""
        accepted = self.store.accepted(node)
        return review.record_of(self.store, node, accepted) if accepted else review.record_of(self.store, node)

    def judgement_of(self, record):
        return review.newest_judgement(self.store, record) if record else None

    # --- files -------------------------------------------------------------------------------------------------

    def blob_path(self, sha):
        return self.store_root / "objects" / "blobs" / sha

    def listing(self, output):
        return self.remembered(("listing", output), lambda: self.store.listing(output) if output else {})

    def refs(self, output, kinds=None):
        """FileRefs of an output's files (of `kinds` when given), each known so it may be served."""
        found = []
        for name, sha in sorted(self.listing(output).items()):
            if kinds and kind_of(name) not in kinds:
                continue
            path = self.blob_path(sha)
            self.known.add(sha, name, path)
            found.append(file_ref(sha, name, path.stat().st_size if path.exists() else 0))
        return found

    def first_image(self, output, preferred=()):
        """The output's first image, a preferred name first."""
        images = self.refs(output, ("image",))
        for name in preferred:
            for ref in images:
                if ref.name == name:
                    return ref
        return images[0] if images else None

    def own_image(self, output):
        """The output's first image of its own making: a texture packaged in an assets/ folder is not one."""
        return next((ref for ref in self.refs(output, ("image",)) if not packaged(ref.name)), None)

    def picture_of(self, node, output):
        """The output's first image of its own making, else its preview made from its own files (previews/); None
        for no output."""
        if not output:
            return None
        return self.own_image(output) or self.preview(node, output)

    def preview(self, node, output):
        """A FileRef of the picture previews/ makes from an output that holds no image of its own, served and
        exported like any picture."""
        from score.dashboard import previews
        listing = self.listing(output)
        if not listing:
            return None
        stage, _, place = node.partition("@")
        files = [(name, self.blob_path(sha)) for name, sha in sorted(listing.items())]
        path = previews.picture(files, self.place_plan(place) if place else None, self.surface_library(), self.home,
                                output, groups.label(stage), (self.props_home / "work",))
        sha = previews.preview_id(output)
        self.known.add(sha, previews.PREVIEW_NAME, path)
        return file_ref(sha, previews.PREVIEW_NAME, path.stat().st_size)

    def place_plan(self, place):
        """The place's plan (plan.json of its plan step's shown output), the ground every map is drawn over."""
        def read():
            record = self.shown_record(self.node_of("plan", place))
            sha = self.listing(record["output"]).get("plan.json") if record else None
            return json.loads(self.blob_path(sha).read_text()) if sha else None
        return self.remembered(("plan", place), read)

    def surface_library(self):
        """{surface: (rgb, roughness, metallic)} of the material library, the swatches' and painted takes' colours."""
        from score.dashboard.previews import swatches
        return self.remembered(("surfaces",), lambda: swatches.library(
            self.data / "library" / "materials.json", REPO / "design" / "tokens" / "tokens.json"))

    def work_picture(self, written):
        """A FileRef of a picture place.json names (WORK/ is the work folder); None when it is not there."""
        if not written or not written.startswith("WORK/"):
            return None
        path = self.props_home / "work" / written.removeprefix("WORK/")
        if not path.is_file():
            return None
        from score.store import file_hash
        sha = self.remembered(("picture", str(path), path.stat().st_mtime), lambda: file_hash(path))
        self.known.add(sha, path.name, path)
        return file_ref(sha, path.name, path.stat().st_size)

    def look_picture(self, written, places):
        """A picture place.json names for a look: in the work folder (WORK/), else, when the folder it was written
        from is gone (an old session's TMP/, a job's own folder), the picture of the same name among the views of
        the look's places (the concept picks are kept there); None when none is there."""
        found = self.work_picture(written)
        if found or not written:
            return found
        name = pathlib.PurePosixPath(written).name
        return next((found for found in (self.work_picture(f"WORK/scene/{place}/views/{name}") for place in places)
                     if found), None)

    def file(self, sha):
        return self.known.get(sha)

    def web3d_file(self, place, name):
        """A file of a place's fresh 3D web copy, or None."""
        path = self.web_copies / place / name
        return path if place in self.places() and path.is_file() else None

    def thumb_path(self, sha):
        """A known image's thumbnail, made once into the dashboard's home; None for an unknown sha or a non-image."""
        found = self.known.get(sha)
        if found is None or kind_of(found[0]) != "image" or not found[1].is_file():
            return None
        return thumbnail(found[1], self.home / "thumbs" / f"{sha}-{THUMB_SIDE}.jpg")

    # --- cards -------------------------------------------------------------------------------------------------

    def step_card(self, row, place, with_thumb):
        node = self.node_of(row.name, place)
        state, words = self.node_state(node)
        record = self.shown_record(node) if state != NOT_RUN else None
        thumb = self.picture_of(node, record["output"]) if (with_thumb and record) else None
        return StepCard(node=node, stage=row.name, label=groups.label(row.name), paid=bool(row.paid), state=state,
                        state_words=words, gates=counts(self.judgement_of(record)) if with_thumb else GateCounts(),
                        thumb=thumb.thumb_url if thumb else None, output=record["output"] if record else None,
                        reads=list(row.after), drawn=bool(thumb) and thumb.name == STEP_DRAWING)

    def layer_groups(self, place, with_thumbs=False):
        """The place's steps grouped by layer, in LAYER_ORDER."""
        found = {}
        for row in self.place_rows(place):
            found.setdefault(self.layer_of.get(row.name, groups.STAGE_AND_FILMS), []).append(
                self.step_card(row, place, with_thumbs))
        return [LayerGroup(name=name, steps=found[name]) for name in groups.LAYER_ORDER if name in found]

    def place_status(self, place):
        """complete / complete apart from accepted gaps (N) / stopped at <node> / waits at <node>, from the store."""
        complete = f"complete@{place}"
        accept = self.store.current_accept(complete)
        if accept:
            words = accept.get("status") or "complete"
            if self.node_state(complete)[0] == STOPPED:
                words += "; a later run stopped at completion (its fault report says why)"
            return words
        rows = self.place_rows(place)
        for row in rows:
            node = self.node_of(row.name, place)
            if self.node_state(node)[0] == STOPPED:
                return f"stopped at {groups.label(row.name)}"
        for row in rows:
            node = self.node_of(row.name, place)
            if self.node_state(node)[0] != ACCEPTED:
                return f"waits at {groups.label(row.name)}"
        return "every step accepted"

    def accepted_output(self, node):
        return self.store.accepted(node)

    def hero(self, place):
        """The concept the film was made against, else a still, else the first accepted image of the place."""
        for stage, names in (("demo-film", ("concept.png",)), ("demo-stills", ())):
            output = self.accepted_output(f"{stage}@{place}")
            picture = output and self.first_image(output, names)
            if picture:
                return picture
        for row in self.place_rows(place):
            output = self.accepted_output(self.node_of(row.name, place))
            picture = output and self.first_image(output)
            if picture:
                return picture
        return None

    def film(self, place):
        output = self.accepted_output(f"demo-film@{place}")
        films = self.refs(output, ("film",)) if output else []
        return films[0] if films else None

    def still(self, place):
        """The accepted film's middle frame as a JPEG, cut once on this machine and kept by the film's hash; None
        when there is no film or it cannot be read."""
        from score.dashboard.previews import films
        output = self.accepted_output(f"demo-film@{place}")
        listing = self.listing(output) if output else {}
        if "film.mp4" not in listing:
            return None
        ident = hashlib.sha256(f"score-dashboard-still:{listing['film.mp4']}".encode()).hexdigest()
        views = self.blob_path(listing["views.json"]).read_text() if "views.json" in listing else ""
        path = films.middle_still(self.blob_path(listing["film.mp4"]), views, self.home / "stills" / f"{ident}.jpg")
        if path is None:
            return None
        self.known.add(ident, STILL_NAME, path)
        return file_ref(ident, STILL_NAME, path.stat().st_size)

    def place_card(self, place):
        return self.remembered(("card", place), lambda: PlaceCard(
            place=place, status=self.place_status(place), hero=self.hero(place), film=self.film(place),
            still=self.still(place), layers=self.layer_groups(place)))

    def world_line(self):
        return [self.step_card(row, None, False) for row in self.world_rows()]

    def style_groups(self):
        looks = self.looks()
        found = []
        for look, places in groups.styles(self.places(), looks).items():
            entry = looks.get(look) if isinstance(looks.get(look), dict) else {}
            pictures = (entry.get("pictures") or {}).get("do") or [] if isinstance(entry.get("pictures"), dict) else []
            first = pictures[0] if pictures else {}
            found.append(StyleGroup(look=look, label=entry.get("name") or look.replace("_", " "),
                                    short=entry.get("short") or "",
                                    palette=[colour for colour in (entry.get("palette") or [])
                                             if isinstance(colour, str) and colour.startswith("#")][:8],
                                    picture=self.look_picture(first.get("picture"), places),
                                    said=first.get("said", ""),
                                    places=[self.place_card(place) for place in places]))
        return found

    def world_state(self, spend=None):
        return WorldState(made_at=self.read_at(), source=self.name, world=self.world.name,
                          engines=[EngineGroup(name=groups.ENGINE, styles=self.style_groups())],
                          world_line=self.world_line(), spend=spend or Spend(note="spend not read"),
                          gaps_total=self.gaps_total(), gaps_price=self.gaps_price(),
                          remake=self.remake(), concepts=self.concepts(), **self.concept_review(),
                          **self.hierarchy())

    def concepts(self):
        """{place or shell: FileRef} of each concept picture: the concept review's picked draw, else its newest draw unless all its draws are from an older wording,
        else the one data/places/concepts.json names, where its bytes stand in the store's blobs; a place it lists
        as lost with no draw, or whose blob is not here, has none."""
        path = self.data / "places" / "concepts.json"
        found = json.loads(path.read_text())["concepts"] if path.is_file() else {}
        refs = {}
        for node, concept in found.items():
            blob = self.blob_path(concept["sha256"])
            if blob.is_file():
                self.known.add(concept["sha256"], concept["name"], blob)
                refs[node] = file_ref(concept["sha256"], concept["name"], blob.stat().st_size)
        review = self.concept_review()
        for node, draws in review["concept_draws"].items():
            chosen = review["concept_picked"].get(node)
            if not chosen and node in review["concept_undrawn"]:
                continue  # only draws from an older wording: out of date, kept in its history, never on its card
            refs[node] = next((draw.picture for draw in draws if draw.picture.sha == chosen), draws[-1].picture)
        return refs

    def concept_review(self):
        """{concept_draws, concept_picked, concept_draw_euros, concept_undrawn, concept_unready, concept_wordings,
        inventories} of the concept review (score/review/concepts.py): each place's draws whose bytes stand in the
        store's blobs, oldest first, its picked draw's sha, the places and shells with no draw yet that Draw all draws
        now, why the others wait, and each place's scene inventory with the concept it was read from."""
        from score.review import concepts
        draws, picked = {}, {}
        for node in concepts.placed(self.store):
            found = []
            for record in concepts.draws(self.store, node):
                blob = self.blob_path(record["sha"])
                if blob.is_file():
                    self.known.add(record["sha"], record["name"], blob)
                    found.append(ConceptDraw(picture=file_ref(record["sha"], record["name"], blob.stat().st_size),
                                             **{name: record.get(name) for name in ("at", "by", "euros", "base")},
                                             marks=record.get("marks") or [], note=record.get("note") or ""))
            if found:
                draws[node] = found
            if concepts.picked(self.store, node):
                picked[node] = concepts.picked(self.store, node)
        nodes = [*self.places(), *self.hierarchy()["shells"]]
        reads = {place: concepts.inventory_read(place, self.data / "inventory") for place in self.places()}
        ready, waiting = concepts.undrawn(self.store, nodes)
        return {"concept_draws": draws, "concept_picked": picked, "concept_draw_euros": concepts.draw_euros(),
                "concept_undrawn": ready, "concept_unready": waiting,
                "concept_wordings": {node: self.concept_wording(node) for node in nodes},
                "inventories": {place: read for place, read in reads.items() if read}}

    def concept_wording(self, node):
        """What `node`'s draws send (score/review/concepts.py): its generated first-draw wording, why it cannot be
        drawn now, the creator's own wording, the pictures a first draw sends and what a redraw sends."""
        from score.review import concepts
        return ConceptWording(generated=concepts.generated(self.store, node),
                              own=concepts.own_wording(self.store, node), refused=concepts.waits(self.store, node), redraw=concepts.redraw_preview(),
                              pictures=[words for words, _ in concepts.sent_pictures(self.store, node)])

    def hierarchy(self):
        """{within, shells} of data/places/within.json: what each place or shell sits within (a part of a place's
        outside, `parts`, sits within that place), and the shells that are no place of their own with their short
        names; empty while the file is not there."""
        path = self.data / "places" / "within.json"
        found = json.loads(path.read_text()) if path.is_file() else {}
        parts = {name: {"within": entry["of"]} for name, entry in found.get("parts", {}).items()}
        return {"within": {name: entry["within"] for name, entry in {**found.get("within", {}), **parts}.items()},
                "shells": {name: entry["name"] for name, entry in found.get("shells", {}).items()}}

    # --- one place ---------------------------------------------------------------------------------------------

    def usd_index(self, place):
        """The place's OpenUSD index: the accepted assembly's root, its sublayers in order, sizes and makers."""
        node = f"assembly@{place}"
        accept = self.store.current_accept(node)
        if not accept:
            return UsdIndex()
        listing = self.listing(accept["output"])
        root = f"{place}.usda" if f"{place}.usda" in listing else None
        ordered = SUBLAYER.findall(self.blob_path(listing[root]).read_text()) if root else []
        named = {pathlib.PurePosixPath(path).stem: path for path in ordered}
        layers = []
        for name in LAYER_FILES:
            path = named.get(name) or next((item for item in listing if item.startswith(f"layers/{name}.")),
                                           f"layers/{name}.usda")
            present = path in listing
            maker = LAYER_MAKERS[name]
            layers.append(UsdLayer(name=name, path=path, present=present,
                                   bytes=self.blob_path(listing[path]).stat().st_size if present else 0,
                                   made_by_step=self.node_of(maker, None if maker == "terrain" else place)
                                   if maker else None))
        return UsdIndex(root=root, own_output=accept["output"], accepted_at=accept["at"],
                        with_neighbours_output=self.accepted_output(f"neighbours@{place}"), layers=layers,
                        asset_count=sum(1 for item in listing if item.startswith("assets/") and kind_of(item) == "usd"))

    def accepted_gaps(self, place):
        """The place's accepted gaps, each with its step and a picture of what it names (state/accepted_gaps.py)."""
        return self.remembered(("accepted_gaps", place), lambda: named.accepted_gaps(self, place))

    def current_findings(self, path):
        """A standalone check's findings.json, or None once an output it judged is no longer the accepted one (it is
        run again on the new one)."""
        written = json.loads(path.read_text())
        if any(self.accepted_output(node) != output for node, output in written.get("outputs", {}).items()):
            return None
        return written

    def finding(self, check, place, item):
        """One finding of a check's findings.json, with its picture and, for a gap, its gap fields."""
        return CheckFinding(check=check, rule=item["rule"], prim=item.get("prim"), kind=item.get("kind"),
                            sentence=item["sentence"],
                            picture=self.work_picture(f"WORK/{CHECKS}/{check}/{place}/{item['picture']}")
                            if item.get("picture") else None,
                            **{field: item.get(field) for field in GAP_FIELDS})

    def check_findings(self, place):
        """Every standalone check's findings of the place but the gaps (listed apart), each with its picture,
        while the outputs it judged stay accepted."""
        found = []
        for path in sorted((self.props_home / "work" / CHECKS).glob(f"*/{place}/findings.json")):
            check, written = path.parts[-3], self.current_findings(path)
            if check != GAPS and written:
                found += [self.finding(check, place, item) for item in written.get("findings", [])]
        return found

    def gaps(self, place):
        """What the place's route still needs (the gaps check's findings), while the outputs it stood over stay
        accepted; [] when it has not run."""
        path = self.props_home / "work" / CHECKS / GAPS / place / "findings.json"

        def read():
            written = self.current_findings(path) if path.is_file() else None
            return [self.finding(GAPS, place, item).model_copy(update={"paid": self.paid_node(item.get("node"))})
                    for item in (written or {}).get("findings", [])]
        return self.remembered(("gaps", place, written_at(path)), read)

    def paid_node(self, node):
        """Whether a node's stage is paid; None with no node or for a stage outside the table (the ship kits')."""
        row = self.by_name.get(node.split("@", 1)[0]) if node else None
        return bool(row.paid) if row else None

    def gaps_total(self):
        """Every place's gaps whose scene inventory counts (counted_places) and the environment's own lost inputs
        (GAPS_WORLD) in sum, a lost input once (lost_once): counts by kind (gaps.KINDS: lost, route, missing, gate) and the work no stage does."""
        counted = self.counted_places()

        def read():
            gaps = lost_once([gap for place in [*counted, GAPS_WORLD] for gap in self.gaps(place)])
            return GapsTotal(counts=dict(Counter(gap_kind(gap) for gap in gaps)),
                              unfillable=sorted({gap.work for gap in gaps if gap.node is None}))
        return self.remembered(("gaps total", self.gaps_written(), counted), read)

    def counted_places(self):
        """The places whose scene inventory counts: read from their picked draw (CONTEXT.md "scene inventory"; the
        rule of screens.inventory_current)."""
        from score.review import concepts
        found = []
        for place in self.places():
            read = concepts.inventory_read(place, self.data / "inventory")
            if read and read["concept"] and read["concept"] == concepts.picked(self.store, place):
                found.append(place)
        return tuple(found)

    def gaps_written(self):
        """(place, when its findings were written) of every gaps check's findings, read on each call (a stat each):
        what the gaps read is remembered by, so a gaps check that ran again shows at once, not after the index's
        next build."""
        return tuple(sorted((path.parent.name, written_at(path))
                            for path in (self.props_home / "work" / CHECKS / GAPS).glob("*/findings.json")))

    def gaps_price(self):
        """The runner's price of every gap's chain, with why it is stale; None before `score price --gaps` ran."""
        path = self.props_home / "work" / CHECKS / GAPS_PRICE / f"{self.world.name}.json"

        def read():
            if not path.is_file():
                return None
            written = json.loads(path.read_text())
            fields = {name: written[name] for name in GapsPrice.model_fields if name in written}
            return GapsPrice(**fields, stale=self.price_stale(path, written))
        return self.remembered(("gaps price", written_at(path), self.gaps_written()), read)

    def remake(self):
        """Prepare's one-shot figure of the whole remake (REMAKE, read as written), with why it is stale; None before
        prepare ran."""
        path = self.props_home / "work" / CHECKS / REMAKE

        def read():
            return remake_of(json.loads(path.read_text())) if path.is_file() else None
        return self.remembered(("remake", written_at(path)), read)

    def price_stale(self, path, written):
        """Why a gaps price record no longer stands (made on other code or other per-unit prices than this
        checkout's, an output accepted or rejected after it was made, or a gaps check written after it), or None:
        the rule of current_findings, so a stale record shows no number."""
        moved = code_moved(written.get("priced_on"))
        if moved:
            return moved
        since = stamp_key(written["made_at"])
        moved = [key for area in TIMED for key in self.index.prefixed(area)
                 if key.rsplit("/", 1)[-1].rsplit("-", 1)[0] > since]
        if moved:
            return (f"{len(moved)} output{'' if len(moved) == 1 else 's'} {'was' if len(moved) == 1 else 'were'} "
                    "accepted or rejected since the price was made")
        made = path.stat().st_mtime
        newer = [found for found in (self.props_home / "work" / CHECKS / GAPS).glob("*/findings.json")
                 if found.stat().st_mtime > made]
        return (f"the gaps check ran again at {len(newer)} place{'' if len(newer) == 1 else 's'} since the price "
                "was made") if newer else None

    def faults(self, place):
        """Each step of the place whose fault report is newer than its accept: its cause, in one plain sentence,
        its page and a picture of what it is about."""
        return [self.stopped_step(place, row.name) for row in self.place_rows(place)
                if self.node_state(self.node_of(row.name, place))[0] == STOPPED]

    def stopped_step(self, place, stage):
        """A stopped step: pictured by the image its output made of its own, else by the place in its film."""
        label, why = groups.label(stage), self.fault_why(self.node_of(stage, place), stage)
        picture, words = named.own_picture(self, place, stage), named.STEP_PICTURE
        if picture is None:
            picture, words = self.still(place) or self.hero(place), named.THE_PLACE
        return StoppedStep(label=label, why=why, sentence=plain.stop_sentence(label, why, place, len(
            named.entries(self.data, place))), step_url=f"/place/{place}/step/{stage}/", picture=picture,
                           picture_is=words if picture else "")

    def fault_why(self, node, stage):
        """The cause line of a node's fault report, its node named by the step's words."""
        text = (self.store_root / "faults" / f"{node}.txt").read_text(errors="replace")
        why = next((line for line in text.splitlines() if line.startswith("why its line stopped:")),
                   text.splitlines()[0] if text else "")
        return why.removeprefix("why its line stopped:").replace(node, groups.label(stage)).strip()[:400]

    def web3d(self, place):
        """The fresh web copy's facts (web3d/convert.py's sidecar) and whether the accepted assembly moved since;
        None when none was made."""
        path = self.web_copies / place / f"{place}.json"
        if not path.is_file():
            return None
        sidecar = json.loads(path.read_text())
        layers = sorted({item["layer"] for item in sidecar.get("objects", [])})
        return {"made_at": sidecar.get("made_at"), "bytes": sidecar.get("bytes"),
                "light_bytes": sidecar.get("light_bytes"), "triangles": sidecar.get("triangles"), "layers": layers,
                "from_output": sidecar.get("from_output"),
                "current": sidecar.get("from_output") == self.accepted_output(f"assembly@{place}")}

    def concept(self, place):
        """The place's concept picture: the one its plan was read from (plan.json `concept.picture`, {seeds} the
        work folder), else the work folder's scene/<place>/views/K01.png; None when neither is there."""
        written = ((self.place_plan(place) or {}).get("concept") or {}).get("picture")
        if isinstance(written, str) and written.startswith("{seeds}/"):
            found = self.work_picture("WORK/" + written.removeprefix("{seeds}/"))
            if found:
                return found
        return self.work_picture(f"WORK/scene/{place}/views/K01.png")

    def film_fps(self, place):
        """The frames a second of the place's stage (its root's framesPerSecond), 24 when it does not say."""
        index = self.usd_index(place)
        output = index.own_output
        sha = self.listing(output).get(index.root) if output and index.root else None
        found = FPS.search(self.blob_path(sha).read_text()) if sha else None
        return float(found.group(1)) if found else 24.0

    def film_view(self, place):
        """The accepted film's first frame's camera ({eye, aim, fov} across the width), or None without one."""
        output = self.accepted_output(f"demo-film@{place}")
        sha = self.listing(output).get("views.json") if output else None
        if not sha:
            return None
        written = json.loads(self.blob_path(sha).read_text())
        views = (written.get("views") or []) if isinstance(written, dict) else []
        first = next((view for view in views if "eye" in view and "aim" in view), None)
        return {"eye": first["eye"], "aim": first["aim"], "fov": first.get("fov")} if first else None

    def skipped(self, place):
        """Loud: the steps of the stage table not in this place's line, and its accepted gaps (left out by decision)."""
        rows = {row.name for row in self.place_rows(place)}
        missing = [groups.label(row.name) for row in self.rows if row.grain == "place" and row.name not in rows]
        found = [f"{entry.name}: {entry.reason} (accepted gap)" for entry in self.accepted_gaps(place)]
        if missing:
            found.append(f"not in this place's line: {', '.join(missing)}")
        return found

    def place_detail(self, place):
        look = groups.look_of(place, self.looks())
        return PlaceDetail(place=place, status=self.place_status(place), look=look, hero=self.hero(place),
                           film=self.film(place), usd_index=self.usd_index(place),
                           layers=self.layer_groups(place, with_thumbs=True), faults=self.faults(place),
                           accepted_gaps=self.accepted_gaps(place), checks=self.check_findings(place), gaps=self.gaps(place),
                           concept=self.concept(place),
                           skipped=self.skipped(place),
                           film_fps=self.film_fps(place), film_view=self.film_view(place), web3d=self.web3d(place))

    def reads_of(self, node):
        """The nodes a node reads (its stage's `after`, at its place where that stage applies; world stages by
        name)."""
        stage, _, place = node.partition("@")
        row = self.by_name.get(stage)
        if row is None:
            return []
        found = []
        for read in row.after:
            other = self.by_name.get(read)
            if other is None:
                continue
            if other.grain == "world":
                found.append(read)
            elif place and other in self.place_rows(place):
                found.append(f"{read}@{place}")
        return found

    def input_pictures(self, node):
        """Each node this one reads, pictured by its accepted output's first image."""
        found = []
        for read in self.reads_of(node):
            stage, _, place = read.partition("@")
            output = self.accepted_output(read)
            picture = self.picture_of(read, output)
            found.append(InputPicture(node=read, label=groups.label(stage),
                                      thumb=picture.thumb_url if picture else None, url=f"/place/{place}/step/{stage}/" if place else f"/world/step/{stage}/"))
        return found

    # --- one step ----------------------------------------------------------------------------------------------

    def taken(self, node, output, at=None, by=None):
        record = review.record_of(self.store, node, output)
        judgement = self.judgement_of(record)
        thumb = self.picture_of(node, output)
        return Taken(output=output, at=at, by=by, answer=judgement["answer"] if judgement else None,
                     thumb=thumb.thumb_url if thumb else None)

    def history(self, node, current):
        """Earlier accepted outputs, newest first, at most HISTORY."""
        seen, found = {current}, []
        for accept in reversed(self.store.accepts(node)):
            if accept["output"] in seen:
                continue
            seen.add(accept["output"])
            found.append(self.taken(node, accept["output"], accept["at"], accept["by"]))
            if len(found) == HISTORY:
                break
        return found

    def record_facts(self, record):
        if not record:
            return {}
        keep = ("finished", "minutes", "machine", "commit", "uncommitted", "carried", "key")
        return {name: record[name] for name in keep if name in record}

    def step_detail(self, place, stage):
        """Everything one step's page shows; None for a stage that is not in the table or not at this place."""
        row = self.by_name.get(stage)
        if row is None or (row.grain == "world") != (place is None) or (
                place is not None and row not in self.place_rows(place)):
            return None
        node = self.node_of(stage, place)
        state, words = self.node_state(node)
        accept = self.store.current_accept(node)
        accepted_record = review.record_of(self.store, node, accept["output"]) if accept else None
        newest = review.record_of(self.store, node)
        detail = StepDetail(node=node, stage=stage, label=groups.label(stage), place=place, paid=bool(row.paid),
                            euros=row.euros, state=state, state_words=words,
                            readers=self.readers.get(stage, []), reads=list(row.after))
        shown = accepted_record or newest
        if accept:
            detail.accepted = self.taken(node, accept["output"], accept["at"], accept["by"])
            detail.history = self.history(node, accept["output"])
        if shown:
            detail.record = self.record_facts(shown)
            detail.judgement = verdict_list(self.judgement_of(shown), self.store.waivers(node, shown["key"]))
            detail.files = self.with_preview(node, shown["output"], self.refs(shown["output"]))
            detail.picture = self.picture_of(node, shown["output"])
        if newest and (not accept or newest["output"] != accept["output"]):
            self.add_waiting(detail, node, newest)
        if state == STOPPED:
            detail.fault = (self.store_root / "faults" / f"{node}.txt").read_text(errors="replace")
            detail.fault_why = self.fault_why(node, stage)
        detail.log_tail = tail(self.store_root / "logs" / f"{node}.log")
        detail.inputs = self.input_pictures(node)
        detail.reference = self.concept(place) if place else None
        return detail

    def with_preview(self, node, output, refs):
        """An output's files, its preview added after them when none of them is an image of its own making."""
        if any(ref.kind == "image" and not packaged(ref.name) for ref in refs):
            return refs
        made = self.preview(node, output)
        return [*refs, made] if made else refs

    def add_waiting(self, detail, node, newest):
        """The newest output that is not the accepted one: its answer, gates, files and how it is worse."""
        judgement = self.judgement_of(newest)
        detail.waiting = self.taken(node, newest["output"], newest.get("finished"))
        detail.waiting_judgement = verdict_list(judgement, self.store.waivers(node, newest["key"]))
        detail.waiting_files = self.with_preview(node, newest["output"], self.refs(newest["output"]))
        if judgement:
            detail.waiting_worse = review.worse_than_accepted(self.store, node, judgement)

