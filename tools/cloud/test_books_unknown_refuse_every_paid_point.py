"""The month's books (ledger.books_refusal, compute's books check, google_bill's read-back): paid work is refused
while this month's books are unknown, at every paid point (the month check, require_cleared, compute.submit, rent),
before anything is ordered or written; the books open only when they say this month is `known`, or the cloud ledger
and the Google ledger each hold a line from before the month began; a read-back opens them only once Google's bill
was read, and keeps a known month when it fails; the owner's Google figure is a finite figure of at least zero, counted
once; and the runner's keys are never made here. No cloud: the ledgers, the books and the keys are temp files, the
provider a recorder.

Fault (2026-10-19, #13): the old WSL disk went with the cloud ledger, the Google ledger and the runner's keys. A
missing ledger read as EUR 0; the first refused rent would have written a ledger line; and batch.ssh_key would have
made a new key for the account beside the stale one. Review of #13: `--google-month nan` was taken.

Break that turns it red: in ledger.books_refusal accept one ledger from before the month (`or` for `and`); in
compute.read_back_books make the books `known` from the Scaleway bill alone; or in batch.rent order before checking
the self-delete key.
"""
import json
import os
import pathlib
import sys
import time
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import batch  # noqa: E402
import google_bill  # noqa: E402
import google_spend  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

OFFER = provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")
# A store whose ticket names a yes, so require_cleared reaches its books check (no owner area is written).
NAMED = types.SimpleNamespace(clearances=lambda node, key: [], spend_yes=lambda node, key: {"euros": 1.0})


@pytest.fixture(autouse=True)
def no_cloud(tmp_path, monkeypatch):
    """No provider bill read, no billing export table set, the ledgers and the books in the test's folder."""
    monkeypatch.setattr(compute, "cloud_bill", lambda: 0.0)
    monkeypatch.delenv(google_bill.TABLE, raising=False)
    monkeypatch.delenv(compute.TICKET, raising=False)
    monkeypatch.delenv(ledger.FREE_ONLY, raising=False)
    monkeypatch.setattr(google_bill, "SETTINGS", tmp_path / "google-billing-table")
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(ledger, "BOOKS", tmp_path / "books.json")


def last_month():
    """The month before this one, YYYY-MM."""
    year, month = map(int, ledger.this_month().split("-"))
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def books_of(cloud_lines=(), google_lines=(), books=None):
    """The ledgers holding these lines and the books this record."""
    for path, lines in ((ledger.LEDGER, cloud_lines), (google_spend.LEDGER, google_lines)):
        if lines:
            path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    if books is not None:
        ledger.BOOKS.write_text(json.dumps(books))


def cloud_line(month, euros=0.0):
    return {"started": f"{month}-02T10:00:00Z", "batch": "pixal-1", "euros": euros}


def google_line(month, euros=0.0):
    return {"time": f"{month}-02T10:00:00+02:00", "call": "one", "state": "finished", "model": "gemini-3.1-pro-preview",
            "euros": euros}


def refusals(monkeypatch):
    """What two paid points say now: books_refusal's reason and require_cleared's Refused, None when open."""
    said = {"month": compute.books_refusal()}
    monkeypatch.setenv(compute.TICKET, "override restore-test")
    try:
        compute.require_cleared("a test rent", NAMED)
        said["cleared"] = None
    except compute.Refused as refused:
        said["cleared"] = str(refused)
    monkeypatch.delenv(compute.TICKET)
    return said


OPEN = {"month": None, "cleared": None}


@pytest.mark.parametrize("cloud, google, books", [
    ((), (), None),  # no ledgers at all
    ([{**cloud_line(ledger.this_month()), "kind": ledger.RENT_REFUSED}], [google_line(ledger.this_month())], None),
    ([cloud_line(last_month())], [google_line(ledger.this_month())], None),  # one ledger from before is not enough
    ([cloud_line(last_month())], [google_line(last_month())],
     {"month": ledger.this_month(), "state": "lost", "bill": 1200.0}),
    ([cloud_line(last_month())], [google_line(last_month())],
     {"month": ledger.this_month(), "state": "known", "google_before": float("nan")}),
], ids=["no-ledgers", "ledger-begun-again", "one-ledger-before", "read-back-lost", "nan-google-month"])
def test_unknown_books_refuse_every_paid_point(monkeypatch, cloud, google, books):
    books_of(cloud, google, books)
    said = refusals(monkeypatch)
    assert said["month"] and said["cleared"]


def test_ledgers_running_from_before_the_month_open_the_books(monkeypatch):
    books_of([cloud_line(last_month())], [google_line(last_month())])
    assert refusals(monkeypatch) == OPEN


def test_known_books_count_the_owners_google_month_once(monkeypatch):
    books_of([cloud_line(ledger.this_month(), 10.0)], [google_line(ledger.this_month(), 5.0)],
             {"month": ledger.this_month(), "state": "known", "bill": 0.0, "google_before": 400.0})
    assert refusals(monkeypatch) == OPEN
    assert round(compute.books_now()["google"], 6) == 405.0


def test_books_of_an_earlier_month_count_nothing_now():
    books_of([cloud_line(last_month())], [google_line(last_month())],
             {"month": last_month(), "state": "known", "google_before": 400.0})
    assert ledger.google_before() == 0.0 and ledger.books_refusal() is None


def test_a_nan_google_month_is_never_counted():
    books_of(books={"month": ledger.this_month(), "state": "known", "google_before": float("nan")})
    with pytest.raises(ledger.BooksUnknown, match="not a figure of euros"):
        ledger.google_before()


def test_a_free_only_process_refuses_before_the_books_are_read(monkeypatch):
    books_of([cloud_line(last_month())], [google_line(last_month())])
    monkeypatch.setenv(ledger.FREE_ONLY, "1")
    with pytest.raises(ledger.FreeOnly):
        compute.books_refusal()


def test_a_cleared_submit_writes_no_job_while_the_books_are_unknown(tmp_path, monkeypatch):
    jobs = Store.in_folder(tmp_path / "store").objects
    monkeypatch.setattr(compute, "clearance", lambda runner, node, euros: {"key": "k" * 64})
    with pytest.raises(compute.Refused, match="unknown"):
        compute.submit(None, "render@hangar", jobs, "run-1", "job-1", {"kind": "blender", "image": "x", "command": []})
    assert jobs.keys("") == []


def test_rent_refuses_without_the_runners_keys_before_any_provider_call(tmp_path, monkeypatch):
    books_of([cloud_line(last_month())], [google_line(last_month())])
    ordered = []
    monkeypatch.setattr(batch.cloud, "create", lambda *arguments: ordered.append(arguments) or (None, "refused"))
    monkeypatch.setattr(batch, "month_spent", lambda account: ordered.append("bill") or 0.0)
    monkeypatch.setattr(batch.compute, "require_cleared", lambda what: None)
    monkeypatch.setattr(batch, "KEY", tmp_path / "ssh_key")
    monkeypatch.setattr(batch, "SELF_DELETE_KEY", tmp_path / "self_delete_key.json")
    batch.KEY.write_text("private")  # the ssh key alone: the self-delete key is missing
    fleet = types.SimpleNamespace(folder=tmp_path, deadline=time.time() + 60, attempts=[])
    with pytest.raises(compute.Refused) as refused:
        batch.rent(fleet, None, OFFER, 0)
    assert "self_delete_key.json" in str(refused.value) and "owner" in str(refused.value)
    assert ordered == []


def test_the_runners_ssh_key_is_never_made_here(tmp_path, monkeypatch):
    ran = []
    monkeypatch.setattr(batch, "KEY", tmp_path / "ssh_key")
    monkeypatch.setattr(batch.subprocess, "run", lambda *arguments, **options: ran.append(arguments))
    with pytest.raises(SystemExit, match="owner"):
        batch.ssh_key()
    assert ran == [] and not (tmp_path / "ssh_key").exists()


def unread_google_bill():
    raise google_bill.Unread("gcp_billing_export_v1_* does not match any table")


def read_back_with(monkeypatch, google):
    """compute.read_back_books with the Scaleway bill at EUR 1234.5 and `google` as the Google bill's reader."""
    monkeypatch.setattr(compute, "cloud_bill", lambda: 1234.5)
    monkeypatch.setattr(compute, "google_bill", google)
    return compute.read_back_books()


def test_a_read_back_without_googles_bill_leaves_the_books_lost_and_says_why(monkeypatch):
    books_of([cloud_line(last_month())], [google_line(last_month())])
    books = read_back_with(monkeypatch, unread_google_bill)
    assert (books["state"], books["bill"], books["vat_in_bill"]) == ("lost", 1234.5, "unknown")
    said = refusals(monkeypatch)
    assert said["cleared"] and "does not match any table" in said["month"]


def test_a_read_back_of_both_bills_makes_the_books_known(monkeypatch):
    books_of(google_lines=[google_line(ledger.this_month(), 20.0)])
    books = read_back_with(monkeypatch, lambda: 321.456)
    assert (books["state"], books["google_bill"], books["google_unread"]) == ("known", 321.46, None)
    assert compute.google_month() == 321.46  # the higher of the bill and the Google ledger's EUR 20
    assert refusals(monkeypatch) == OPEN


def test_the_month_check_reads_both_bills_back_when_an_export_is_set(monkeypatch):
    books_of(books={"month": ledger.this_month(), "state": "lost"})
    monkeypatch.setattr(compute, "google_bill_set", lambda: True)
    monkeypatch.setattr(compute, "google_bill", lambda: 99.0)
    assert compute.books_refusal() is None
    assert (ledger.read_books()["state"], ledger.read_books()["google_bill"]) == ("known", 99.0)


def test_the_owners_google_figure_overrides_the_bill_read(monkeypatch):
    books_of(google_lines=[google_line(ledger.this_month(), 20.0)],
             books={"month": ledger.this_month(), "state": "known", "google_before": 400.0})
    books = read_back_with(monkeypatch, lambda: 50.0)
    assert (books["state"], books["google_before"], books["google_bill"]) == ("known", 400.0, 50.0)
    assert compute.google_month() == 420.0


def test_a_failed_read_back_keeps_a_known_month(monkeypatch):
    books_of(books={"month": ledger.this_month(), "state": "known", "google_bill": 80.0, "google_before": 400.0})
    books = read_back_with(monkeypatch, unread_google_bill)
    assert (books["state"], books["google_bill"], books["google_before"]) == ("known", 80.0, 400.0)


def test_the_billing_export_rows_give_the_months_euros_or_say_why_not():
    assert "invoice.month = '202610'" in google_bill.month_query("p.d.gcp_billing_export_v1_*", "2026-10")
    assert google_bill.euros_of([{"currency": "EUR", "euros": "12.5", "lines": "3"}], "2026-10") == 12.5
    for rows, said in (([], "no rows"), ([{"currency": "USD", "euros": "1"}], "not EUR")):
        with pytest.raises(google_bill.Unread, match=said):
            google_bill.euros_of(rows, "2026-10")
    with pytest.raises(google_bill.Unread, match=google_bill.TABLE):
        google_bill.month_euros("2026-10")  # no table set


def test_the_owners_google_month_must_be_a_finite_figure_of_at_least_zero(monkeypatch):
    monkeypatch.setattr(compute, "running_under_agent", lambda: False)
    for figure in (float("nan"), float("inf"), -5.0):
        with pytest.raises(compute.Refused, match="finite figure"):
            compute.owners_google_month(figure)
        assert not ledger.BOOKS.exists()
    assert compute.owners_google_month(12.5)["google_before"] == 12.5
    assert refusals(monkeypatch) == OPEN
