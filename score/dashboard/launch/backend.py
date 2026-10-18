"""The compute backend: how the dashboard plans, prices and launches queued steps, swappable by configuration.

    class ComputeBackend(Protocol):
        name: str
        def plan(self, group: RunGroup) -> GroupPlan: ...      # missing inputs, nodes to run, buys with estimates, refusal
        def spend(self) -> Spend: ...                          # the environment against its stop, the month by source
        def measured(self) -> Iterable[MeasuredRun]: ...       # stage, euros, minutes of earlier paid runs
        def launch(self, group: RunGroup, jobs: int, rebuy_reason: str | None) -> LaunchHandle: ...
        def poll(self, handle: LaunchHandle) -> LaunchState: ...
        def price(self, world: str, nodes: list) -> dict: ...  # {node: Price fields, or {error}}: the runner's numbers
        def ledgered(self, nodes, since: str) -> list: ...     # [Billed] of these nodes' paid runs started since

SCORE_COMPUTE_BACKEND names the class as `module:Class` (imported with importlib); the shipped one is
score.dashboard.launch.localrun:LocalBackend, which runs the `score` command line. A private deployment installs its
own module and sets the variable; no code for one is in this repository.
"""
import dataclasses
import importlib
from typing import Iterable, Protocol

from score.dashboard.state.models import Spend


@dataclasses.dataclass(frozen=True)
class RunGroup:
    """Places that queued the same stages: one runner command. No places: environment stages only."""
    places: tuple
    stages: tuple
    world: str = "world1"


@dataclasses.dataclass
class GroupPlan:
    missing: list
    buys: list  # [{node, euros, why, again}]
    refusal: str | None
    to_run: dict  # {node: why}
    blocked: dict  # {node: why}


@dataclasses.dataclass
class MeasuredRun:
    stage: str
    euros: float | None
    minutes: float | None


@dataclasses.dataclass
class LaunchHandle:
    command: list
    pid: int | None = None
    log: str | None = None
    refused: str | None = None  # the runner's own refusal, printed before it detached


@dataclasses.dataclass
class LaunchState:
    state: str  # starting, running, done, failed, stopped, refused
    result: str = ""
    log_tail: str = ""


@dataclasses.dataclass
class Billed:
    """One ledger line a node's paid run wrote: what it really cost and how long its batch took."""
    node: str
    euros: float
    minutes: float | None
    started: str


class ComputeBackend(Protocol):
    name: str

    def plan(self, group: RunGroup) -> GroupPlan: ...

    def spend(self) -> Spend: ...

    def measured(self) -> Iterable[MeasuredRun]: ...

    def launch(self, group: RunGroup, jobs: int, rebuy_reason: str | None) -> LaunchHandle: ...

    def poll(self, handle: LaunchHandle) -> LaunchState: ...

    def price(self, world: str, nodes: list) -> dict: ...

    def ledgered(self, nodes, since: str) -> list: ...


def load(dotted):
    """An instance of the backend `module:Class` names."""
    module, _, name = dotted.partition(":")
    if not module or not name:
        raise ValueError(f"SCORE_COMPUTE_BACKEND is module:Class, not {dotted!r}")
    return getattr(importlib.import_module(module), name)()
