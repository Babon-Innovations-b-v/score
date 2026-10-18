"""The dashboard's view of a world, the same whichever source served it (the store beside it, or a state export):
templates and the API read only these. Pydantic, so the API is typed and an export is plain JSON."""
from pydantic import BaseModel, Field, field_validator


class FileRef(BaseModel):
    name: str
    kind: str  # image, film, usd, gltf, other
    sha: str
    bytes: int = 0
    url: str
    thumb_url: str | None = None


class CostLine(BaseModel):
    """One source of this month's cost: its euros, where the number comes from and when it was read; `partial` when
    the source is known to miss some of the cost."""
    source: str
    label: str
    euros: float | None = None
    partial: bool = False
    origin: str = ""
    read_at: str | None = None


class Spend(BaseModel):
    """The world's money (spent since its first stop line, still in flight, its stop) and this month's measured cost
    lines. The shared cloud account's monthly credit is only a note (`credit_note`)."""
    spent: float | None = None
    reserved: float | None = None
    ceiling: float | None = None
    as_of: str | None = None
    note: str = ""  # why a number is missing, in words
    world: str | None = None
    stop_at: str | None = None
    month: str | None = None
    lines: list[CostLine] = []
    credit_note: str = ""  # the shared cloud account's credit, a note only, never SCORE's budget


class MonthTotal(BaseModel):
    euros: float
    whole: bool  # False while any line is partial or missing: the page says "at least"
    gaps: list[str] = []


class MoneyView(BaseModel):
    """The month's cost by source and its total (state/money.py), and the world against its stop line; `stop` None:
    no stop set, paid launches refused."""
    month: str
    lines: list[CostLine]
    total: MonthTotal
    world: str | None = None
    stop: float | None = None
    stop_at: str | None = None
    world_spent: float | None = None
    in_flight: float | None = None
    note: str = ""
    credit_note: str = ""


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
    reads: list[str] = []  # the stages it reads, for the breakdown's "made from"
    drawn: bool = False  # its picture is a map drawn from its files (previews/), shown at its own size
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
    still: FileRef | None = None  # the accepted film's middle frame as a JPEG, so the board seeks no video
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
    picture: FileRef | None = None  # the step's own picture: its output's own image, else one drawn from its files
    mark: str | None = None


class NamedGap(BaseModel):
    """A gap the owner named (data/checks/gaps/<place>.json): its words, one plain sentence of what is wrong and
    where, its step, and a picture of what it names (state/gaps.py)."""
    name: str
    sentence: str = ""
    reason: str = ""
    step: str | None = None  # the stage it was named at
    step_label: str | None = None
    step_url: str | None = None  # its step's page, when the step is in this place's line
    objects: list[str] = []
    picture: FileRef | None = None
    picture_is: str = ""  # what the picture shows, in words


class StoppedStep(BaseModel):
    """A step of a place whose run stopped after its last accept: what its fault report says, in one plain
    sentence, its step's page and a picture of what it is about."""
    label: str
    why: str
    sentence: str = ""
    step_url: str | None = None
    picture: FileRef | None = None
    picture_is: str = ""


class CheckFinding(BaseModel):
    """What a standalone check (one not a gate of any step: the library check, score/stages/complete/library) found
    in a place, with its picture."""
    check: str
    rule: str
    prim: str | None = None
    kind: str | None = None  # what the finding is on (model, geometry, light, sound, sky...), for its step
    sentence: str
    picture: FileRef | None = None


class PlaceDetail(BaseModel):
    place: str
    status: str
    look: str | None = None
    hero: FileRef | None = None
    film: FileRef | None = None
    usd_index: UsdIndex = UsdIndex()
    layers: list[LayerGroup] = []
    faults: list[StoppedStep] = []
    gaps: list[NamedGap] = []

    @field_validator("faults", mode="before")
    @classmethod
    def faults_from_words(cls, faults):
        """An export made before faults were records carries each as one line of words; read it as a stopped step."""
        return [{"label": fault, "why": fault, "sentence": fault} if isinstance(fault, str) else fault for fault in faults or []]

    @field_validator("gaps", mode="before")
    @classmethod
    def gaps_from_words(cls, gaps):
        """An export made before gaps were records carries each as one line of words; read it as a named gap."""
        return [{"name": gap, "sentence": gap} if isinstance(gap, str) else gap for gap in gaps or []]
    checks: list[CheckFinding] = []  # the standalone checks' findings on the outputs they judged
    concept: FileRef | None = None
    skipped: list[str] = []  # loud: steps of the chain not done for this place, and named gaps
    film_fps: float = 24.0
    film_view: dict | None = None  # the film's first frame's camera (eye, aim, fov across), for the 3D viewer
    web3d: dict | None = None  # the fresh web copy's sidecar facts, or None
