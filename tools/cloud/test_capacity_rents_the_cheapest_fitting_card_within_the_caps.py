r"""Invariant of capacity.py (with the provider interface it reads): every job kind runs on capability classes only;
the next machine is the kind's cheapest card per job that fits, a card out of stock last and a never-class never,
spread over the zones; a batch gets enough machines to end in about its set-up and one job, never more than its jobs
nor than the caps (each class's quota, the run's cap, SCORE_MAX_MACHINES); all the processes of one `score run` hold
the run's cap together, parked machines counted, a slot whose rent gave no machine freed; and the capacity report
groups the ledger's machines by kind and card in one printed line (owner, 2026-10-12: the cheapest card that fits;
2026-10-17: every node held a cap of its own).

One test: a table of answers (each call of the code under test, the settings it runs under, the answer worked out by
hand from the offers and the rule) and one home of real `score run` processes against their shared counts. The break
that turns it red (each applied once, seen red, reverted):

- classes: in `classes_for`, the unknown kind's `raise SystemExit(...)` -> `return ()`; or in provider.py `cards`, the
  last `raise SystemExit(...)` -> `return 0`; or drop `(?:-(\d+)c)?` from provider.GPU -> a class naming its cores is
  no class.
- the next machine: in `next_offer`'s key, drop `offer.stock_word == "shortage", `; or `in_zone[offer.zone]` -> `0`;
  or `and offer.machine_class not in NEVER.get(kind, ())` -> ``.
- a late class: in batch.py `claim_round`, `first = [offer for offer in offers if offer.machine_class not in late]` ->
  `first = list(offers)`.
- jobs at once: in `runs_at_once`, `// 24` -> `// 48`; or `if kind in measured:` -> `if False:`.
- secrets: in secret_store.py `secret`, `if os.environ.get(environment_name(name)):` -> `if False:`.
- a batch's machines: in `machines_for`, `span = max(setup_minutes, unit_minutes)` -> `span = unit_minutes`.
- the caps: in `caps`, `found[name] = int(number)` -> `pass`.
- a machine's row: in ledger.py `machine_row`, `((ready or ended) - began) / 60` -> `(ended - began) / 60`.
- the report: in `summarise`, `"failed_starts": len(group) - len(ran)` -> `"failed_starts": 0`.
- the run's cap held together: in `reserve_run_slot`, `room = elsewhere + live < run_cap()` -> `room = live <
  run_cap()`.
- parked machines: in `held_elsewhere`, `held += sum(json.loads(` -> `held += 0 * sum(json.loads(`.
- the cap said once: in `say_at_cap`, `if at_cap and not AT_CAP:` -> `if at_cap:`.
- a slot that gave no machine: in `renting_elsewhere`, `if time.time() - count["at"] < RESERVE_SECONDS:` -> `if
  True:`; or in `held_elsewhere`, `sum(parent != os.getpid() for parent in watchdogs.values())` -> `0`.
"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
import secret_store  # noqa: E402

HERE = str(pathlib.Path(capacity.__file__).parent)
L4, L40S, H100 = 0.013125, 0.024498, 0.047775
STOCK_WORDS = ("available", "scarce", "shortage")


def offer(per_card, stock, machine_class, zone, order=0):
    return provider.Offer(per_card, stock, f"{machine_class}-type{order}", zone,
                          per_card * max(1, provider.cards(machine_class)), machine_class, order, STOCK_WORDS[stock])


class Refuses:
    """The expected answer of a call that must refuse: its SystemExit names `words`."""

    def __init__(self, words):
        self.words = words

    def __repr__(self):
        return f"Refuses({self.words!r})"


class Fields:
    """The expected answer of a call giving a dict: these of its fields, each equal."""

    def __init__(self, **fields):
        self.fields = fields

    def __eq__(self, other):
        return isinstance(other, dict) and all(name in other and other[name] == value
                                               for name, value in self.fields.items())

    def __repr__(self):
        return f"Fields({self.fields!r})"


# The offers the next machine is chosen from. Stock 0 is in stock, 1 scarce, 2 out of stock (shortage).
L4_A, L4_B, L4_C = (offer(L4, 2, "gpu-24gb", zone) for zone in ("zone-a", "zone-b", "zone-c"))
H100_B = offer(H100, 2, "gpu-80gb", "zone-b")
SPREAD = [L4_A, L4_B, L4_C, H100_B]
H100_IN_STOCK, L4_SCARCE = offer(H100, 0, "gpu-80gb", "zone-a"), offer(L4, 1, "gpu-24gb", "zone-a")
X2_LATER, X2_FIRST = offer(H100, 2, "gpu-80gb-x2", "zone-a", 1), offer(H100, 2, "gpu-80gb-x2", "zone-b", 0)
CARDS = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a"), offer(L40S, 2, "gpu-48gb", "zone-a")]
L40S_SCARCE = offer(L40S, 1, "gpu-48gb", "zone-b")
TWO_H100S = [{"zone": "zone-a", "class": "gpu-80gb"}] * 2
LATE_OFFERS = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a")]

# One machine of a run as batch.py records it: 150 s to answer, 600 s of work, 12.5 min billed as 13 started
# minutes; the same machine never answering, deleted after 5 min; and an offer that gave no machine.
MACHINE = {"type": "L40S-1-48G", "zone": "fr-par-2", "cards": 1, "price": L40S, "created": 1000.0, "ready": 1150.0,
           "deleted": 1750.0, "unit_seconds": [200.0, 210.0]}
SILENT = ledger.machine_row(dict(MACHINE, ready=None, deleted=1300.0))
REFUSED = batch.refused_row(offer(L4, 2, "gpu-24gb", "zone-a"), "out of stock")

# The ledger the capacity report reads: September's line has no kind (Pixal3D, the only kind then); October's ran an
# L40S and had a failed L4 start.
ENTRIES = [{"started": "2026-09-30T10:00:00Z", "machines": [{"type": "L4-1-24G", "zone": "pl-waw-2", "minutes": 30.0,
                                                             "euros": 0.4}]},
           {"started": "2026-10-08T10:00:00Z", "kind": "pixal",
            "machines": [{"type": "L40S-1-48G", "zone": "fr-par-2", "started": True, "start_wait_minutes": 2.0,
                          "work_minutes": 20.0, "minutes": 22.0, "euros": 0.54, "unit_seconds": [300.0, 320.0, 340.0]}],
            "attempts": [{"type": "L4-1-24G", "zone": "pl-waw-2", "started": False, "minutes": 0.0, "euros": 0.1}]}]

QUOTAS = provider.cloud.QUOTAS
RUN_CAP = max(capacity.RUN_MACHINES, *QUOTAS.values())
CAPPED = {"SCORE_MAX_MACHINES": "gpu-80gb=2, all=3"}
TAKEN = []


def claim_from(run, account, offers, number, kind, disk_gb=batch.DISK_GB):
    """A claim that gives a machine only from an offer set holding an 80 GB card, noting each set's classes."""
    TAKEN.append(sorted({item.machine_class for item in offers}))
    return None if "gpu-80gb" not in TAKEN[-1] else "machine"


def claim_rounds(kind):
    """What batch.claim_round gives a kind from LATE_OFFERS, and the classes each of its rounds was offered."""
    TAKEN.clear()
    return batch.claim_round(None, None, LATE_OFFERS, 1, kind), list(TAKEN)


# (row, settings, call, arguments, expected): settings are environment variables, and RUNS_AT_ONCE the backend's
# measured counts; a Refuses answer is a SystemExit naming its words.
ANSWERS = [
    # every job kind runs on capability classes, never a provider's machine type
    ("a processor class has no card", {}, provider.cards, ("cpu-32c-128gb",), 0),
    ("a two-card class has two", {}, provider.cards, ("gpu-80gb-x2",), 2),
    ("a class's card size", {}, provider.card_gb, ("gpu-48gb",), 48),
    ("a class naming its cores has its cards", {}, provider.cards, ("gpu-80gb-x2-48c",), 2),
    ("a class naming its cores has its card size", {}, provider.card_gb, ("gpu-80gb-x2-48c",), 80),
    ("a provider's type is no class", {}, provider.cards, ("L4-1-24G",), Refuses("capability class")),
    ("a bare word is no class", {}, provider.cards, ("gpu",), Refuses("capability class")),
    ("an unknown kind has no classes", {}, capacity.classes_for, ("nothing",), Refuses("no capability classes")),
    # the next machine: the kind's cheapest card per job, out of stock last, spread over the zones
    ("the cheapest card, the backend's first zone", {}, capacity.next_offer, (SPREAD, []), L4_A),
    ("a zone holding a machine goes after", {}, capacity.next_offer, (SPREAD, [{"zone": "zone-c"}]), L4_A),
    ("the zone holding none", {}, capacity.next_offer, (SPREAD, [{"zone": "zone-c"}, {"zone": "zone-a"}]), L4_B),
    ("a bigger card in stock before a 24 GB card out of stock", {}, capacity.next_offer,
     (SPREAD + [H100_IN_STOCK], []), H100_IN_STOCK),
    ("a scarce 24 GB card before a bigger one in stock", {}, capacity.next_offer, ([H100_IN_STOCK, L4_SCARCE], []),
     L4_SCARCE),
    ("within a class, the backend's own order", {}, capacity.next_offer, ([X2_LATER, X2_FIRST], []), X2_FIRST),
    ("nothing offered, no machine", {}, capacity.next_offer, ([], []), None),
    ("Pixal3D on an L4", {}, capacity.next_offer, (CARDS, [], "pixal"), CARDS[0]),
    ("the mesh splitting on an L4", {}, capacity.next_offer, (CARDS, [], "meshparts"), CARDS[0]),
    ("the judge on an L40S", {}, capacity.next_offer, (CARDS, [], "judge"), CARDS[2]),
    ("the 20B picture model on an H100", {}, capacity.next_offer, (CARDS, [], "pictures-20b"), CARDS[1]),
    ("the library bakes on an L4", {}, capacity.next_offer, (CARDS, [], "library"), CARDS[0]),
    ("the parts on an L4", {}, capacity.next_offer, (CARDS, [], "parts"), CARDS[0]),
    ("Blender passes the H100 for the L40S", {}, capacity.next_offer, (CARDS[1:], [], "blender"), CARDS[2]),
    ("Blender with only an H100 has no machine", {}, capacity.next_offer, (CARDS[1:2], [], "blender"), None),
    # a late class only after the wait; a kind given none takes every class at once
    ("a late class after the first round gave nothing", {}, claim_rounds, ("library",),
     ("machine", [["gpu-24gb"], ["gpu-80gb"]])),
    ("a kind with no late class takes all at once", {}, claim_rounds, ("pixal",), ("machine", [["gpu-24gb", "gpu-80gb"]])),
    # jobs at once on one card: three Pixal3D for every 24 GB (six on an L4 ran out of memory), a backend's measure
    # over that (this PC's 16 GB card answers for gpu-24gb), one for a kind never measured
    ("Pixal3D on 24 GB", {}, capacity.runs_at_once, ("pixal", "gpu-24gb"), 3),
    ("Pixal3D on 48 GB", {}, capacity.runs_at_once, ("pixal", "gpu-48gb"), 6),
    ("Pixal3D on 80 GB", {}, capacity.runs_at_once, ("pixal", "gpu-80gb"), 10),
    ("an unmeasured kind on 80 GB", {}, capacity.runs_at_once, ("parts", "gpu-80gb"), 1),
    ("the backend's measure over the class", {"RUNS_AT_ONCE": {"pixal": 1}}, capacity.runs_at_once,
     ("pixal", "gpu-24gb"), 1),
    ("the backend's measure leaves other kinds at one", {"RUNS_AT_ONCE": {"pixal": 1}}, capacity.runs_at_once,
     ("parts", "gpu-24gb"), 1),
    # a secret from the environment before the backend
    ("a secret from the environment", {"SCORE_SECRET_SOME_API_KEY": "from-the-environment"}, secret_store.secret,
     ("some-api-key",), "from-the-environment"),
    ("a secret from the backend", {}, secret_store.secret, ("some-api-key",), "from-the-backend"),
    # a batch ends in about its set-up and one job
    ("one job", {}, capacity.machines_for, (1, 10, 8), 1),
    ("30 pictures of 9 s: less work than one set-up", {}, capacity.machines_for, (30, 0.15, 8), 1),
    ("no jobs", {}, capacity.machines_for, (0, 1, 8), 1),
    ("ten 15-minute Blender jobs: one a machine", {}, capacity.machines_for, (10, 15, 8), 10),
    ("60 close-ups of 82 s on a 10 min set-up: 9 machines", {}, capacity.machines_for, (60, 82 / 60, 10), 9),
    ("their 7 rounds over the 9", {}, capacity.spread_minutes, (60, 82 / 60, 10, 9), 10 + 7 * 82 / 60),
    ("ten at once: a tenth as many", {}, capacity.machines_for, (100, 5, 5, 10), 10),
    ("never more machines than jobs", {}, capacity.machines_for, (3, 60, 8), 3),
    # the caps: each class's quota, the run's cap (#20: its largest class's quota, at least RUN_MACHINES), and
    # SCORE_MAX_MACHINES over both
    ("a class's quota", {}, capacity.max_machines, ("gpu-80gb",), QUOTAS["gpu-80gb"]),
    ("a class with no quota", {}, capacity.max_machines, ("cpu-32c-128gb",), capacity.OTHER_MACHINES),
    ("the run's cap", {}, capacity.run_cap, (), RUN_CAP),
    ("a big batch at the run's cap", {}, capacity.machines_for, (500, 60, 8), RUN_CAP),
    ("a class capped by the environment", CAPPED, capacity.max_machines, ("gpu-80gb",), 2),
    ("the run capped by the environment", CAPPED, capacity.run_cap, (), 3),
    ("a big batch at the environment's cap", CAPPED, capacity.machines_for, (500, 60, 8), 3),
    ("the H100s at their cap of 2", CAPPED, capacity.next_offer, ([H100_IN_STOCK, L40S_SCARCE], TWO_H100S, "judge"),
     L40S_SCARCE),
    ("the run at its cap of 3", CAPPED, capacity.next_offer,
     ([H100_IN_STOCK, L40S_SCARCE], TWO_H100S + [{"zone": "zone-b", "class": "gpu-48gb"}], "judge"), None),
    ("a cap with no number", {"SCORE_MAX_MACHINES": "gpu-80gb"}, capacity.caps, (), Refuses("SCORE_MAX_MACHINES")),
    # a machine's ledger row: how long it waited, worked and cost
    ("a machine that answered", {}, ledger.machine_row, (MACHINE,),
     Fields(started=True, start_wait_minutes=2.5, work_minutes=10.0, minutes=12.5, euros=13 * L40S,
            unit_seconds=[200.0, 210.0])),
    ("a machine that never answered: 5 min billed", {}, ledger.machine_row, (dict(MACHINE, ready=None, deleted=1300.0),),
     Fields(started=False, start_wait_minutes=5.0, work_minutes=0.0, euros=5 * L40S)),
    ("an hourly machine by the started hour", {}, ledger.cost, (61, 1.221 / 60, 60), pytest.approx(2 * 1.221, abs=1e-9,
                                                                                                      rel=0)),
    ("a run's machines, its failed starts and its wait from 900 to its 1150", {}, ledger.machines_record,
     ([MACHINE], [SILENT, REFUSED], 900.0),
     Fields(attempts=[SILENT, REFUSED], start_wait_minutes=250 / 60, euros=pytest.approx(18 * L40S, abs=1e-12, rel=0))),
    # the report groups the ledger's machines by kind and card: September's L4 and October's failed L4 start together
    ("by kind and card", {}, capacity.summarise, (capacity.machine_rows(ENTRIES),),
     [Fields(kind="pixal", type="L4-1-24G", machines=1, failed_starts=1),
      Fields(kind="pixal", type="L40S-1-48G", machines=1, failed_starts=0, units=3, seconds_a_unit=320.0,
             euros_a_unit=pytest.approx(0.18, abs=1e-9, rel=0))]),
    ("since October", {}, capacity.summarise, (capacity.machine_rows(ENTRIES, since="2026-10-01"),),
     [Fields(type="L4-1-24G", machines=0, failed_starts=1), Fields(type="L40S-1-48G", machines=1)]),
]


def answer(call, arguments):
    """What `call` gives, or Refuses with its SystemExit's message."""
    try:
        return call(*arguments)
    except SystemExit as refusal:
        return Refuses(str(refusal))


def report_output(arguments, entries, report_path, monkeypatch):
    """What `capacity.py report <arguments>` prints over `entries`, its table written to `report_path`."""
    monkeypatch.setattr(sys, "argv", ["capacity.py", "report", *arguments])
    monkeypatch.setattr(capacity.ledger, "entries", lambda: entries)
    monkeypatch.setattr(capacity, "REPORT", report_path)
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        capacity.main()
    return printed.getvalue()


def in_a_run(home, cap, run):
    """The environment of a process of the `score run` `run` with a cap of `cap` machines, its home `home`."""
    return {**os.environ, "PROPS_HOME": str(home), "PROPS_WORK": str(home / "work"), "SCORE_RUN_ID": run,
            "SCORE_MAX_MACHINES": f"all={cap}"}


# A process of the run "parked", cap 4, whose park records hold two of its machines (a third is another run's): it
# asks for slots as its machines come and go, and forgets the run's counts at its end.
PARKED_RUN = """
import json, sys
sys.path.insert(0, sys.argv[1])
import capacity, park
park.PARKED.mkdir(parents=True, exist_ok=True)
for number, run in enumerate(("parked", "parked", "another-run")):
    (park.PARKED / f"m{number}.json").write_text(json.dumps({"id": f"m{number}", "run": run}))
assert capacity.reserve_run_slot(1)          # 2 parked + 1 held < 4: counted
assert not capacity.reserve_run_slot(2)      # 2 parked + 2 held: the cap, said
assert not capacity.reserve_run_slot(2)      # still at it: not said again
assert capacity.reserve_run_slot(0)          # room again
assert not capacity.reserve_run_slot(2)      # filled again: said again
assert (capacity.RUNS / "parked").exists()
capacity.forget_run("parked")
assert not (capacity.RUNS / "parked").exists()
"""

# A batch process of a `score run`: it rents fake machines as fast as next_offer gives offers and lets some go,
# writing how many the run's processes hold together into one file. It runs a number of asks, never a span of time
# (a 4 s span on a loaded gate pod gave a few asks, too few to reach the cap): it starts once every renter has, asks
# until the run has held its cap and it has asked AT_CAP_ASKS times since, and lets its machines go at its end, so a
# renter that ends first leaves no machines on the count that the others no longer see.
RENTER = """
import fcntl, json, pathlib, random, sys, time
sys.path.insert(0, sys.argv[1])
import capacity, provider
held, renters, cap = pathlib.Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
offers = [provider.Offer(0.01, 2, "gpu-24gb-type0", "zone-a", 0.01, "gpu-24gb", 0, "available")]
AT_CAP_ASKS = 30

def together(change, started=0):
    with held.open("r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        counts = json.loads(handle.read() or '{"now": 0, "most": 0, "started": 0}')
        counts["now"] += change
        counts["most"] = max(counts["most"], counts["now"])
        counts["started"] += started
        handle.seek(0), handle.truncate(), handle.write(json.dumps(counts))
        return counts

together(0, started=1)
while together(0)["started"] < renters:
    time.sleep(0.01)
machines, asked_at_cap = [], 0
while asked_at_cap < AT_CAP_ASKS:
    if capacity.next_offer(offers, machines, "pixal") is not None:
        machines.append({"zone": "zone-a", "class": "gpu-24gb", "deleted": None})
        together(1)
    live = [machine for machine in machines if not machine["deleted"]]
    if live and random.random() < 0.3:
        live[0]["deleted"] = time.time()
        together(-1)  # off the count first: the process's count lets it go at its next ask
    asked_at_cap += together(0)["most"] >= cap
    time.sleep(random.random() * 0.02)
together(-sum(not machine["deleted"] for machine in machines))
"""

# A process of a run given a slot that rents nothing with it ("fails") or rents a machine whose watchdog it starts as
# batch.rent does ("rents"); it says "<run>.ready" and lives on.
SLOT_TAKER = """
import pathlib, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
import capacity
folder = pathlib.Path(sys.argv[2])
assert capacity.reserve_run_slot(0)
if sys.argv[3] == "rents":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", str(pathlib.Path(sys.argv[1]) / "batch.py"),
                      "--watchdog", "machine-1", "zone-a", "0"])
(folder / f"{sys.argv[3]}.ready").write_text("ready")
time.sleep(60)
"""
# Another process of the run asking for a slot at once, and again once a slot given 1 s ago has lapsed. The 1 s
# window is set after the first ask: set before it, a start-up slower than 1 s (a loaded gate pod) saw the slot lapsed.
SLOT_ASKER = """
import sys, time
sys.path.insert(0, sys.argv[1])
import capacity
first = capacity.reserve_run_slot(0)
capacity.RESERVE_SECONDS = 1.0
time.sleep(2.5)
print(first, capacity.reserve_run_slot(0))
"""


def test_capacity_rents_the_cheapest_fitting_card_within_the_caps(tmp_path, monkeypatch):
    for name in ("SCORE_RUN_ID", "SCORE_MAX_MACHINES", "SCORE_SPEND_TICKET", "SCORE_SECRET_SOME_API_KEY"):
        monkeypatch.delenv(name, raising=False)  # the table holds one process's caps; the runs below their own
    monkeypatch.setattr(provider.cloud, "secret", lambda name: "from-the-backend")
    monkeypatch.setattr(batch, "claim_from", claim_from)
    monkeypatch.setattr(batch.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(batch, "say", lambda line: None)
    monkeypatch.setattr(capacity, "LATE_MINUTES", 0)
    monkeypatch.setitem(capacity.LATE, "library", ("gpu-80gb",))  # the rule, on a kind given a late class

    # One home holds the runs, each its own run id: "parked" first, as its park records are written unlocked; then
    # two renters of "renters" (cap 4), and a slot taker of "fails" and of "rents" (cap 1), side by side.
    home = tmp_path / "home"
    home.mkdir()
    parked = subprocess.run([sys.executable, "-c", PARKED_RUN, HERE], env=in_a_run(home, 4, "parked"),
                            capture_output=True, text=True, timeout=60)
    held = home / "held.json"
    held.write_text("")
    renters = [subprocess.Popen([sys.executable, "-c", RENTER, HERE, str(held), "2", "4"],
                                env=in_a_run(home, 4, "renters")) for _ in range(2)]
    takers = {run: subprocess.Popen([sys.executable, "-c", SLOT_TAKER, HERE, str(home), run],
                                    env=in_a_run(home, 1, run), start_new_session=True) for run in ("fails", "rents")}
    try:
        for machine_class in provider.cloud.CLASSES:
            provider.cards(machine_class)  # every backend class reads as one, never refused
        for kind, classes in capacity.KINDS.items():
            assert classes and all(provider.cards(machine_class) for machine_class in classes), kind
        for row, settings, call, arguments, expected in ANSWERS:
            with monkeypatch.context() as setting:
                for name, value in settings.items():
                    if name == "RUNS_AT_ONCE":
                        setting.setattr(provider.cloud, name, value, raising=False)
                    else:
                        setting.setenv(name, value)
                got = answer(call, arguments)
            if isinstance(expected, Refuses):
                assert isinstance(got, Refuses) and expected.words in got.words, (row, got)
            else:
                assert got == expected, (row, got)

        # the report prints one line and writes its table, a header and a line a card type; --verbose prints it
        path = tmp_path / "report.txt"
        assert report_output([], ENTRIES[1:], path, monkeypatch) == (
            "capacity report: 1 job kinds on 2 card types, 1 machines, 1 failed starts, €0.64; "
            f"table: {path}\n")
        assert len(path.read_text().splitlines()) == 3
        assert report_output(["--verbose"], ENTRIES[1:], tmp_path / "unused.txt", monkeypatch) == path.read_text()
        assert not (tmp_path / "unused.txt").exists()

        # a run counts its parked machines (another run's not), says once each time its cap fills that the cap holds
        # it back (it said only "no machine ... in stock"; review of C7, 2026-10-17), and forgets its counts at its end
        assert parked.returncode == 0, parked.stderr[-2000:]
        said = [line for line in parked.stderr.splitlines() if "cap" in line]
        assert len(said) == 2 and "the run holds its cap of 4 machines (2 in its other processes and parked, 2 here)" \
            in said[0], parked.stderr

        # a slot whose rent gave no machine is freed once it lapses; one that gave a machine stays counted (a slot
        # that gave none held the run's other processes back for a machine that did not exist; review of C7)
        deadline = time.time() + 60
        while not all((home / f"{run}.ready").exists() for run in takers) and time.time() < deadline:
            time.sleep(0.05)
        askers = {run: subprocess.Popen([sys.executable, "-c", SLOT_ASKER, HERE], env=in_a_run(home, 1, run),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for run in takers}
        answers = {run: asker.communicate(timeout=60) for run, asker in askers.items()}
        assert all(asker.returncode == 0 for asker in askers.values()), answers
        assert {run: printed.split() for run, (printed, _) in answers.items()} == {
            "fails": ["False", "True"], "rents": ["False", "False"]}

        # two batches of one run hold its cap together: reached, never passed (8 with a cap each; fault 2026-10-17)
        assert [renter.wait(timeout=60) for renter in renters] == [0, 0]
        assert json.loads(held.read_text())["most"] == 4
    finally:
        for taker in takers.values():
            os.killpg(taker.pid, 9)
        for renter in renters:
            renter.kill()
