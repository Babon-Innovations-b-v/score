"""The dashboard's view of a world, the same whichever source served it (the store beside it, or a state export):
templates and the API read only these. Pydantic, so the API is typed and an export is plain JSON."""
from pydantic import BaseModel, Field


class FileRef(BaseModel):
    name: str
    kind: str  # image, film, usd, gltf, other
    sha: str
    bytes: int = 0
    url: str
    thumb_url: str | None = None


class Spend(BaseModel):
    spent: float | None = None
    reserved: float | None = None
    ceiling: float | None = None
    as_of: str | None = None
    note: str = ""  # why a number is missing, in words


class GateCounts(BaseModel):
    passed: int = Field(0, alias="pass")
    fail: int = 0
    unknown: int = 0

    model_config = {"populate_by_name": True}


class StepCard(BaseModel):
    node: str
    stage: str
    label: str
    paid: bool
    state: str  # accepted, waiting, stopped, not run
    state_words: str
    gates: GateCounts
    thumb: str | None = None
    output: str | None = None  # the shown output (accepted, else newest), for the owner's seen mark
    mark: str | None = None  # filled by the page from the dashboard's own marks


class LayerGroup(BaseModel):
    name: str
    steps: list[StepCard]


class UsdLayer(BaseModel):
    name: str
    path: str
    present: bool
    bytes: int = 0
    made_by_step: str | None = None


class UsdIndex(BaseModel):
    root: str | None = None
    own_output: str | None = None
    with_neighbours_output: str | None = None
    accepted_at: str | None = None
    layers: list[UsdLayer] = []
    asset_count: int = 0


class PlaceCard(BaseModel):
    place: str
    status: str
    hero: FileRef | None = None
    film: FileRef | None = None
    layers: list[LayerGroup] = []


class StyleGroup(BaseModel):
    look: str
    label: str
    palette: list[str] = []
    picture: FileRef | None = None
    said: str = ""
    places: list[PlaceCard] = []


class EngineGroup(BaseModel):
    name: str
    styles: list[StyleGroup]


class WorldState(BaseModel):
    made_at: str
    source: str  # "store" or "export <made_at>"
    world: str
    engines: list[EngineGroup]
    world_line: list[StepCard] = []
    spend: Spend = Spend()


class GateVerdict(BaseModel):
    name: str
    answer: str
    reason: str = ""
    measures: dict = {}
    waived: str | None = None


class Taken(BaseModel):
    """An output of a node: the accepted one, a waiting one, or an earlier accepted take."""
    output: str
    at: str | None = None
    by: str | None = None
    answer: str | None = None
    thumb: str | None = None


class InputPicture(BaseModel):
    """A step this one reads, pictured: its accepted output's first image."""
    node: str
    label: str
    url: str
    thumb: str | None = None


class StepDetail(BaseModel):
    node: str
    stage: str
    label: str
    place: str | None = None
    paid: bool = False
    euros: float | None = None
    state: str = "not run"
    state_words: str = ""
    accepted: Taken | None = None
    waiting: Taken | None = None  # its newest output, when it is not the accepted one
    waiting_worse: list[str] = []
    waiting_judgement: list[GateVerdict] = []
    waiting_files: list[FileRef] = []
    record: dict = {}  # finished, minutes, carried, machine, commit
    judgement: list[GateVerdict] = []
    files: list[FileRef] = []
    history: list[Taken] = []
    fault: str | None = None
    fault_why: str | None = None  # the report's cause, the node named by its step's words
    log_tail: str | None = None
    readers: list[str] = []
    reads: list[str] = []
    inputs: list[InputPicture] = []
    reference: FileRef | None = None  # the place's concept, what the result is held against
    mark: str | None = None


class PlaceDetail(BaseModel):
    place: str
    status: str
    look: str | None = None
    hero: FileRef | None = None
    film: FileRef | None = None
    usd_index: UsdIndex = UsdIndex()
    layers: list[LayerGroup] = []
    faults: list[str] = []
    gaps: list[str] = []
    concept: FileRef | None = None
    skipped: list[str] = []  # loud: steps of the chain not done for this place, and named gaps
    film_fps: float = 24.0
    web3d: dict | None = None  # the fresh web copy's sidecar facts, or None
