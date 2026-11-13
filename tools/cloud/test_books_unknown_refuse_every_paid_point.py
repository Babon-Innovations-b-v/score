"""The month's books (ledger.books_refusal, compute's books check, google_bill's read-back): paid work is refused
while this month's books are unknown, at every paid point (the month check, require_cleared, compute.submit, rent),
before anything is ordered or written; the books open only when they say this month is `known`, or the cloud ledger
and the Google ledger each hold a line from before the month began; a read-back opens them only once Google's bill
was read, and keeps a known month when it fails; the owner's Google figure is a finite figure of at least zero, counted
once; the runner's keys are never made here; and no machine is rented with a self-delete key the provider refuses.
No cloud: the ledgers, the books and the keys are temp files, the provider a recorder.

One table of worlds (the ledgers, the books, Google's billing export as bq answers it, the figure the owner enters,
a free-only process, the runner's keys), each asked at every paid point (the month check, require_cleared, submit,
batch.rent through the backend's own order) and then read for its books, its Google month and its Google bill.

Fault (2026-10-19, #13): the old WSL disk went with the cloud ledger, the Google ledger and the runner's keys. A
missing ledger read as EUR 0; the first refused rent would have written a ledger line; and batch.ssh_key would have
made a new key for the account beside the stale one. Review of #13: `--google-month nan` was taken.

Break that turns it red: in ledger.books_refusal accept one ledger from before the month (`or` for `and`); in
compute.read_back_books make the books `known` from the Scaleway bill alone; or in batch.rent order before checking
the self-delete key, or in scaleway.create skip self_delete_key_refusal (a key the provider answers 401 rents a
machine that cannot delete itself: 2026-11-02, an H100 idle 12.8 h); or in compute.cloud_bill_all drop `OSError`
(a box with no scw, the gate's pod, fails every read-back instead of leaving the whole bill unread: be04aa4f's gate).
"""
import io
import json
import pathlib
import sys
import time
import types
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import batch  # noqa: E402
import google_bill  # noqa: E402
import google_spend  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
import scaleway  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

OFFER = provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")
# A store whose ticket names a yes, so require_cleared reaches its books check (no owner area is written).
NAMED = types.SimpleNamespace(clearances=lambda node, key: [], spend_yes=lambda node, key: {"euros": 1.0})
EXPORT = "p.d.gcp_billing_export_v1_*"
WORKS = '{"secret_key": "works"}'  # the one self-delete key the provider takes


class Ordered(Exception):
    """The backend's order was reached: its ledger line, written just before the order is sent."""


def this_month():
    return ledger.this_month()


def last_month():
    """The month before this one, YYYY-MM."""
    year, month = map(int, this_month().split("-"))
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def cloud_line(month, euros=0.0):
    return {"started": f"{month}-02T10:00:00Z", "batch": "pixal-1", "euros": euros}


def google_line(month, euros=0.0):
    return {"time": f"{month}-02T10:00:00+02:00", "call": "one", "state": "finished", "model": "gemini-3.1-pro-preview",
            "euros": euros}


def eur(euros):
    """A billing export row of `euros`, as bq gives it (strings)."""
    return {"currency": "EUR", "euros": str(euros), "lines": "3"}


def world(cloud=(), google=(), books=None, export=None, owner=None, free_only=False, ssh=True, self_delete=WORKS):
    """A world: the ledgers' lines, the books, Google's billing export (None: no table set; a list: its rows; a str:
    bq's refusal), the figure the owner enters first, a free-only process, the runner's ssh key (its private half
    alone) and its self-delete key (None: missing)."""
    return {"cloud": cloud, "google": google, "books": books, "export": export, "owner": owner,
            "free_only": free_only, "ssh": ssh, "self_delete": self_delete}


def known(**books):
    return {"month": this_month(), "state": "known", **books}


BEFORE = ([cloud_line(last_month())], [google_line(last_month())])  # both ledgers run from before the month
UNKNOWN = "spend is unknown"
NO_TABLE = "does not match any table"
OPEN = None
ORDERED = ("ordered",)
KEY_OWNER = ("could not delete itself", "owner")
NONE = (0.0, 0.0)
NOT_SET = google_bill.TABLE  # the Google bill read with no export table set says which setting names it

# id: (world, the words every paid point refuses with (OPEN: none refuses), what rent says (None: the refusal's
#      words), the self-delete key reads, the books after (a subset), (google_before, the Google month) or the words
#      both refuse with, Google's bill as read now (a figure or its unread words), the owner's figure refused for)
CASES = {
    "no-ledgers": (world(), UNKNOWN, None, 0, {}, NONE, NOT_SET, None),
    "ledger-begun-again": (world([{**cloud_line(this_month()), "kind": ledger.RENT_REFUSED}],
                                 [google_line(this_month())]), UNKNOWN, None, 0, {}, NONE, NOT_SET, None),
    "one-ledger-before": (world([cloud_line(last_month())], [google_line(this_month())]),
                          UNKNOWN, None, 0, {}, NONE, NOT_SET, None),
    "read-back-lost": (world(*BEFORE, {"month": this_month(), "state": "lost", "bill": 1200.0}), "books are lost",
                       None, 0, {"state": "lost", "bill": 1200.0}, NONE, NOT_SET, None),
    "nan-google-month": (world(*BEFORE, known(google_before=float("nan"))), "no usable Google figure", None, 0,
                         {"state": "known"}, "not a figure of euros", NOT_SET, None),
    "ledgers-from-before": (world(*BEFORE), OPEN, ORDERED, 1, {}, NONE, NOT_SET, None),
    "owners-google-counted-once": (world([cloud_line(this_month(), 10.0)], [google_line(this_month(), 5.0)],
                                         known(bill=0.0, google_before=400.0)),
                                   OPEN, ORDERED, 1, {"google_before": 400.0}, (400.0, 405.0), NOT_SET, None),
    "books-of-an-earlier-month": (world(*BEFORE, {"month": last_month(), "state": "known", "google_before": 400.0}),
                                  OPEN, ORDERED, 1, {"month": last_month()}, NONE, NOT_SET, None),
    "free-only": (world(*BEFORE, free_only=True), "FreeOnly", None, 0, {}, NONE, NOT_SET, None),
    "read-back-google-unread": (world(*BEFORE, export=f"bq: {EXPORT} {NO_TABLE}"), NO_TABLE, None, 0,
                                {"state": "lost", "bill": 1234.5, "vat_in_bill": "unknown", "bill_all": None},
                                NONE, NO_TABLE, None),
    "read-back-both-bills": (world(google=[google_line(this_month(), 20.0)], export=[eur(321.456)]), OPEN, ORDERED, 1,
                             {"state": "known", "google_bill": 321.46, "google_unread": None, "bill": 1234.5},
                             (0.0, 321.46), 321.46, None),  # the higher of the bill and the Google ledger's EUR 20
    "lost-books-read-back": (world(books={"month": this_month(), "state": "lost"}, export=[eur(99.0)]), OPEN, ORDERED,
                             1, {"state": "known", "google_bill": 99.0}, (0.0, 99.0), 99.0, None),
    "owners-figure-overrides-bill": (world(google=[google_line(this_month(), 20.0)], books=known(google_before=400.0),
                                           export=[eur(50.0)]),
                                     OPEN, ORDERED, 1, {"state": "known", "google_before": 400.0, "google_bill": 50.0},
                                     (400.0, 420.0), 50.0, None),
    "failed-read-back-keeps-known": (world(books=known(google_bill=80.0, google_before=400.0), export=NO_TABLE),
                                     OPEN, ORDERED, 1, {"state": "known", "google_bill": 80.0, "google_before": 400.0},
                                     (400.0, 400.0), NO_TABLE, None),
    "export-holds-no-rows": (world(export=[]), "no rows", None, 0, {"state": "lost"}, NONE, "no rows", None),
    "export-bills-usd": (world(export=[{"currency": "USD", "euros": "1"}]), "not EUR alone", None, 0,
                         {"state": "lost"}, NONE, "not EUR", None),
    "owner-gives-nan": (world(owner=float("nan")), UNKNOWN, None, 0, {}, NONE, NOT_SET, "finite figure"),
    "owner-gives-inf": (world(owner=float("inf")), UNKNOWN, None, 0, {}, NONE, NOT_SET, "finite figure"),
    "owner-gives-negative": (world(owner=-5.0), UNKNOWN, None, 0, {}, NONE, NOT_SET, "finite figure"),
    "owner-gives-a-figure": (world(owner=12.5), OPEN, ORDERED, 1, {"state": "known", "google_before": 12.5},
                             (12.5, 12.5), NOT_SET, None),
    "no-self-delete-key": (world(*BEFORE, self_delete=None), OPEN, ("self_delete_key.json", "owner"), 0, {}, NONE,
                           NOT_SET, None),
    "no-runner-keys": (world(*BEFORE, ssh=False, self_delete=None), OPEN, ("ssh_key", "self_delete_key.json", "owner"),
                       0, {}, NONE, NOT_SET, None),
    "self-delete-key-empty": (world(*BEFORE, self_delete='{"secret_key": "", "for": "this PC: never used"}'), OPEN,
                              (*KEY_OWNER, "holds no secret_key"), 0, {}, NONE, NOT_SET, None),
    "self-delete-key-revoked": (world(*BEFORE, self_delete='{"secret_key": "revoked"}'), OPEN, (*KEY_OWNER, "401"), 1,
                                {}, NONE, NOT_SET, None),
    "self-delete-key-unreadable": (world(*BEFORE, self_delete="not json"), OPEN, (*KEY_OWNER, "unreadable"), 0, {},
                                   NONE, NOT_SET, None),
}


def said(call):
    """What a paid point says: None when it lets the work through, else its refusal's class and words."""
    try:
        call()
    except (compute.Refused, ledger.FreeOnly) as refused:
        return f"{type(refused).__name__}: {refused}"
    except Ordered:
        return "ordered"
    return None


def month_check():
    """compute.books_refusal as a paid point: Refused with its reason when it gives one."""
    why = compute.books_refusal()
    if why:
        raise compute.Refused(why)


def books_figure(call):
    """A figure the books give, or the words of their refusal (ledger.BooksUnknown)."""
    try:
        return round(call(), 6)
    except ledger.BooksUnknown as unknown:
        return str(unknown)


def enter(monkeypatch, tmp_path, shape):
    """Lay `shape` out in the test's folder, with the provider, bq and every order a recorder; (bq's queries, the
    self-delete key reads, the processes started)."""

    def no_scw(*words):  # no scw, as in the gate's pod: the whole bill reads as unread
        raise FileNotFoundError(2, "No such file or directory", "scw")
    monkeypatch.setattr(provider.billing(), "scw", no_scw)
    monkeypatch.setattr(compute, "cloud_bill", lambda: 1234.5)
    for name in (google_bill.TABLE, compute.TICKET, ledger.FREE_ONLY):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(google_bill, "SETTINGS", tmp_path / "google-billing-table")
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(ledger, "BOOKS", tmp_path / "books.json")
    for path, lines in ((ledger.LEDGER, shape["cloud"]), (google_spend.LEDGER, shape["google"])):
        if lines:
            path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    if shape["books"] is not None:
        ledger.BOOKS.write_text(json.dumps(shape["books"]))
    queries, asked, ran = [], [], []

    def bq(name, sql):
        queries.append((name, sql))
        if isinstance(shape["export"], str):
            raise google_bill.Unread(shape["export"])
        return shape["export"]
    if shape["export"] is not None:
        monkeypatch.setenv(google_bill.TABLE, EXPORT)
    monkeypatch.setattr(google_bill, "run_query", bq)
    monkeypatch.setattr(batch, "KEY", tmp_path / "ssh_key")
    monkeypatch.setattr(batch, "SELF_DELETE_KEY", tmp_path / "self_delete_key.json")
    if shape["ssh"]:
        batch.KEY.write_text("private")
    if shape["self_delete"] is not None:
        batch.SELF_DELETE_KEY.write_text(shape["self_delete"])

    def answered(request, timeout):  # the provider takes the key "works" alone, 401 to any other
        asked.append(request.full_url)
        if request.get_header("X-auth-token") != "works":
            raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        return io.BytesIO(b'{"servers": []}')
    monkeypatch.setattr(urllib.request, "urlopen", answered)
    monkeypatch.setattr(batch.subprocess, "run", lambda *arguments, **options: ran.append(arguments))

    def order_reached(*arguments):  # the backend's ledger line, written just before its order is sent
        raise Ordered(arguments)
    monkeypatch.setattr(ledger, "rent_started", order_reached)
    monkeypatch.setattr(compute, "cap_check", lambda what: None)  # the env1 cap: not this file's question
    monkeypatch.setattr(compute, "ticket_store", lambda store=None: store or NAMED)
    monkeypatch.setattr(compute, "clearance", lambda runner, node, euros: {"key": "k" * 64})
    monkeypatch.setattr(compute, "running_under_agent", lambda: False)
    return queries, asked, ran


@pytest.mark.parametrize("case", CASES.values(), ids=CASES.keys())
def test_unknown_books_refuse_every_paid_point(tmp_path, monkeypatch, case):
    shape, why, rent_says, key_reads, books_after, google, google_read, owner_refused = case
    queries, asked, ran = enter(monkeypatch, tmp_path, shape)
    if shape["owner"] is not None:  # the owner enters his Google month first
        figure = shape["owner"]
        try:
            compute.owners_google_month(figure)
        except compute.Refused as refused:
            entered = str(refused)
        else:
            entered = None
        assert (entered is None) == (owner_refused is None) and (owner_refused or "") in (entered or ""), entered
    if shape["free_only"]:
        monkeypatch.setenv(ledger.FREE_ONLY, "1")
    ledgered = ledger.LEDGER.read_text() if ledger.LEDGER.exists() else None
    jobs = Store.in_folder(tmp_path / "store").objects
    fleet = types.SimpleNamespace(folder=tmp_path, deadline=time.time() + 60, attempts=[])
    monkeypatch.setenv(compute.TICKET, "override restore-test")
    points = {"month": said(month_check),
              "cleared": said(lambda: compute.require_cleared("a test rent", NAMED)),
              "submit": said(lambda: compute.submit(None, "render@hangar", jobs, "run-1", "job-1",
                                                    {"kind": "blender", "image": "x", "command": []}))}
    rent = said(lambda: batch.rent(fleet, None, OFFER, 0))
    monkeypatch.delenv(compute.TICKET)

    if why is OPEN:
        assert points == {"month": None, "cleared": None, "submit": None}, points
        assert len(jobs.keys("")) == 1, jobs.keys("")  # the cleared job was written
    else:
        assert all(text and why in text for text in points.values()), points
        assert jobs.keys("") == []
    assert rent and all(word in rent for word in (rent_says or (why,))), rent
    assert asked == [scaleway.SERVERS_URL.format(zone=OFFER.zone)] * key_reads  # an empty or unreadable key never asked
    assert (ledger.LEDGER.read_text() if ledger.LEDGER.exists() else None) == ledgered  # a refusal writes no line
    with pytest.raises(SystemExit, match="owner"):
        batch.ssh_key()
    assert batch.KEY.exists() == shape["ssh"] and not batch.KEY.with_suffix(".pub").exists()
    assert ran == [], ran  # no key made, no machine ordered

    books = ledger.read_books()
    assert {name: books.get(name) for name in books_after} == books_after, books
    assert ("bill_all" in books) == ("scw" in (books.get("bill_all_unread") or "")), books  # no scw: the whole bill unread
    year, month = map(int, this_month().split("-"))
    assert bool(queries) == (shape["export"] is not None)
    assert all(name == EXPORT and f"invoice.month = '{year:04d}{month:02d}'" in sql for name, sql in queries)
    read = compute.read_google_bill()
    if isinstance(google_read, str):
        assert google_read in (read["google_unread"] or ""), read
    else:
        assert (read["google_bill"], read["google_unread"]) == (google_read, None), read
    before, month_euros = books_figure(ledger.google_before), books_figure(lambda: compute.books_now()["google"])
    if isinstance(google, str):
        assert google in before and google in month_euros, (before, month_euros)
    else:
        assert (before, month_euros) == google
