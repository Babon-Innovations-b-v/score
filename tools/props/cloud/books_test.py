"""Paid work is refused while the month's books are unknown, at every paid point, before anything is ordered; and the
runner's keys are never made silently. No cloud: the ledgers, the books and the keys are temp files, the provider is
a recorder.

Fault (2026-10-19): the old WSL disk went with the cloud ledger, the Google ledger and the runner's keys. A missing
ledger read as EUR 0, so the month's ceiling counted only the Scaleway bill; the first refused rent would have written
a ledger line; and batch.ssh_key would have made a new key for the account beside the stale one.
"""
import json
import os
import pathlib
import sys
import tempfile
import time
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import batch  # noqa: E402
import google_bill  # noqa: E402
import google_spend  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
os.environ.pop(google_bill.TABLE, None)  # nor Google's: no billing export table is set (google_bill_set is false)
OFFER = provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")
# A store whose ticket names a yes, so require_cleared reaches its books check (no owner area is written).
NAMED = types.SimpleNamespace(clearances=lambda node, key: [], spend_yes=lambda node, key: {"euros": 1.0})


def last_month():
    """The month before this one, YYYY-MM."""
    year, month = map(int, ledger.this_month().split("-"))
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def fresh_books(cloud_lines=(), google_lines=(), books=None):
    """Point the ledgers and the books at temp files holding these lines and this books record."""
    folder = pathlib.Path(tempfile.mkdtemp())
    ledger.LEDGER, google_spend.LEDGER, ledger.BOOKS = (folder / "ledger.jsonl", folder / "google-ledger.jsonl",
                                                        folder / "books.json")
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


def refusals():
    """What two paid points say now: books_refusal's reason and require_cleared's Refused, None when open."""
    said = {"month": compute.books_refusal()}
    os.environ[compute.TICKET] = "override restore-test"
    try:
        compute.require_cleared("a test rent", NAMED)
        said["cleared"] = None
    except compute.Refused as refused:
        said["cleared"] = str(refused)
    finally:
        os.environ.pop(compute.TICKET)
    return said


def test_with_no_ledgers_every_paid_point_refuses():
    fresh_books()
    said = refusals()
    assert "unknown" in said["month"] and "unknown" in said["cleared"]


def test_a_ledger_begun_again_after_the_loss_stays_refused():
    """A refused rent writes a ledger line; a ledger holding only lines from this month proves nothing."""
    fresh_books([{**cloud_line(ledger.this_month()), "kind": ledger.RENT_REFUSED}], [google_line(ledger.this_month())])
    assert all(refusals().values())


def test_ledgers_running_from_before_the_month_open_the_books():
    fresh_books([cloud_line(last_month())], [google_line(last_month())])
    assert refusals() == {"month": None, "cleared": None}


def test_one_ledger_from_before_the_month_is_not_enough():
    fresh_books([cloud_line(last_month())], [google_line(ledger.this_month())])
    assert all(refusals().values())


def test_books_read_back_as_lost_stay_refused():
    fresh_books([cloud_line(last_month())], [google_line(last_month())],
                {"month": ledger.this_month(), "state": "lost", "bill": 1200.0})
    assert all(refusals().values())


def test_known_books_count_the_owners_google_month_once():
    fresh_books([cloud_line(ledger.this_month(), 10.0)], [google_line(ledger.this_month(), 5.0)],
                {"month": ledger.this_month(), "state": "known", "bill": 0.0, "google_before": 400.0})
    assert refusals() == {"month": None, "cleared": None}
    assert round(compute.books_now()["google"], 6) == 405.0


def test_books_of_an_earlier_month_count_nothing_now():
    fresh_books([cloud_line(last_month())], [google_line(last_month())],
                {"month": last_month(), "state": "known", "google_before": 400.0})
    assert ledger.google_before() == 0.0 and ledger.books_refusal() is None


def test_a_free_only_process_refuses_before_the_books_are_read():
    fresh_books([cloud_line(last_month())], [google_line(last_month())])
    os.environ[ledger.FREE_ONLY] = "1"
    try:
        compute.books_refusal()
    except ledger.FreeOnly:
        pass
    else:
        raise AssertionError("a paid run was weighed in a free-only process")
    finally:
        os.environ.pop(ledger.FREE_ONLY)


def test_a_cleared_submit_writes_no_job_while_the_books_are_unknown():
    fresh_books()
    jobs = Store.in_folder(tempfile.mkdtemp()).objects
    kept = compute.clearance
    compute.clearance = lambda runner, node, euros: {"key": "k" * 64}
    try:
        compute.submit(None, "render@hangar", jobs, "run-1", "job-1", {"kind": "blender", "image": "x", "command": []})
    except compute.Refused as refused:
        assert "unknown" in str(refused)
    else:
        raise AssertionError("a job was written while the month's books are unknown")
    finally:
        compute.clearance = kept
    assert jobs.keys("") == []


def test_rent_refuses_without_the_runners_keys_before_any_provider_call():
    fresh_books([cloud_line(last_month())], [google_line(last_month())])
    folder = pathlib.Path(tempfile.mkdtemp())
    ordered = []
    kept = (batch.cloud.create, batch.month_spent, batch.compute.require_cleared, batch.KEY, batch.SELF_DELETE_KEY)
    batch.cloud.create = lambda *arguments: ordered.append(arguments) or (None, "refused")
    batch.month_spent = lambda account: ordered.append("bill") or 0.0
    batch.compute.require_cleared = lambda what: None
    batch.KEY, batch.SELF_DELETE_KEY = folder / "ssh_key", folder / "self_delete_key.json"
    batch.KEY.write_text("private")  # the ssh key alone: the self-delete key is missing
    fleet = types.SimpleNamespace(folder=folder, deadline=time.time() + 60, attempts=[])
    try:
        batch.rent(fleet, None, OFFER, 0)
    except compute.Refused as refused:
        assert "self_delete_key.json" in str(refused) and "owner" in str(refused)
    else:
        raise AssertionError("a machine was ordered without the self-delete key")
    finally:
        batch.cloud.create, batch.month_spent, batch.compute.require_cleared, batch.KEY, batch.SELF_DELETE_KEY = kept
    assert ordered == []


def test_the_runners_ssh_key_is_never_made_here():
    folder = pathlib.Path(tempfile.mkdtemp())
    ran = []
    kept = batch.KEY, batch.subprocess.run
    batch.KEY, batch.subprocess.run = folder / "ssh_key", lambda *arguments, **options: ran.append(arguments)
    try:
        batch.ssh_key()
    except SystemExit as refused:
        assert "owner" in str(refused)
    else:
        raise AssertionError("a key was handed out with none made by the owner")
    finally:
        batch.KEY, batch.subprocess.run = kept
    assert ran == [] and not (folder / "ssh_key").exists()


def unread_google_bill():
    raise google_bill.Unread("gcp_billing_export_v1_* does not match any table")


def read_back_with(google):
    """compute.read_back_books with the Scaleway bill at EUR 1234.5 and `google` as the Google bill's reader."""
    kept = compute.cloud_bill, compute.google_bill
    compute.cloud_bill, compute.google_bill = lambda: 1234.5, google
    try:
        return compute.read_back_books()
    finally:
        compute.cloud_bill, compute.google_bill = kept


def test_a_read_back_without_googles_bill_leaves_the_books_lost_and_says_why():
    """No billing export table yet: the read-back alone never opens paid work, and the refusal says why."""
    fresh_books([cloud_line(last_month())], [google_line(last_month())])
    books = read_back_with(unread_google_bill)
    assert (books["state"], books["bill"], books["vat_in_bill"]) == ("lost", 1234.5, "unknown"), books
    said = refusals()
    assert all(said.values()) and "does not match any table" in said["month"], said


def test_a_read_back_of_both_bills_makes_the_books_known():
    fresh_books(google_lines=[google_line(ledger.this_month(), 20.0)])
    books = read_back_with(lambda: 321.456)
    assert (books["state"], books["google_bill"], books["google_unread"]) == ("known", 321.46, None), books
    assert "google billing export" in books["source"], books
    assert compute.google_month() == 321.46  # the higher of the bill and the Google ledger's EUR 20
    assert refusals() == {"month": None, "cleared": None}


def test_the_month_check_reads_both_bills_back_when_an_export_is_set():
    """The runner's books check (books_refusal) reads the books back itself, so lost books open once Google's bill
    reads, with no figure typed by anyone."""
    fresh_books(books={"month": ledger.this_month(), "state": "lost"})
    kept = compute.google_bill_set, compute.google_bill
    compute.google_bill_set, compute.google_bill = (lambda: True), (lambda: 99.0)
    try:
        assert compute.books_refusal() is None
    finally:
        compute.google_bill_set, compute.google_bill = kept
    assert (ledger.read_books()["state"], ledger.read_books()["google_bill"]) == ("known", 99.0)


def test_the_owners_google_figure_overrides_the_bill_read():
    fresh_books(google_lines=[google_line(ledger.this_month(), 20.0)],
                books={"month": ledger.this_month(), "state": "known", "google_before": 400.0})
    books = read_back_with(lambda: 50.0)
    assert (books["state"], books["google_before"], books["google_bill"]) == ("known", 400.0, 50.0), books
    assert compute.google_month() == 420.0


def test_a_failed_read_back_keeps_a_known_month():
    fresh_books(books={"month": ledger.this_month(), "state": "known", "google_bill": 80.0})
    books = read_back_with(unread_google_bill)
    assert (books["state"], books["google_bill"]) == ("known", 80.0), books


def test_the_billing_export_rows_give_the_months_euros_or_say_why_not():
    assert "invoice.month = '202610'" in google_bill.month_query("p.d.gcp_billing_export_v1_*", "2026-10")
    assert google_bill.euros_of([{"currency": "EUR", "euros": "12.5", "lines": "3"}], "2026-10") == 12.5
    for rows, said in (([], "no rows"), ([{"currency": "USD", "euros": "1"}], "not EUR")):
        try:
            google_bill.euros_of(rows, "2026-10")
            raise AssertionError(f"read {rows}")
        except google_bill.Unread as unread:
            assert said in str(unread), unread


def test_no_billing_export_table_set_is_unread():
    kept = os.environ.pop(google_bill.TABLE, None)
    google_bill.SETTINGS = pathlib.Path(tempfile.mkdtemp()) / "google-billing-table"
    try:
        google_bill.month_euros("2026-10")
        raise AssertionError("read a bill with no table set")
    except google_bill.Unread as unread:
        assert google_bill.TABLE in str(unread), unread
    finally:
        if kept is not None:
            os.environ[google_bill.TABLE] = kept


def test_a_read_back_keeps_the_owners_known_month():
    fresh_books(books={"month": ledger.this_month(), "state": "known", "google_before": 400.0})
    books = compute.read_back_books()
    assert (books["state"], books["google_before"]) == ("known", 400.0), books


def test_the_owners_google_month_must_be_a_finite_figure_of_at_least_zero():
    """Review of #13: `score spend --google-month nan` was taken (argparse's float reads it), and a NaN month made the
    old month ceiling's sum false for every run; a negative figure lowered the month."""
    fresh_books()
    kept, compute.running_under_agent = compute.running_under_agent, lambda: False
    try:
        for figure in (float("nan"), float("inf"), -5.0):
            try:
                compute.owners_google_month(figure)
                raise AssertionError(f"took {figure}")
            except compute.Refused as refused:
                assert "finite figure" in str(refused), refused
            assert not ledger.BOOKS.exists()
        assert compute.owners_google_month(12.5)["google_before"] == 12.5
    finally:
        compute.running_under_agent = kept
    assert refusals() == {"month": None, "cleared": None}


def test_books_edited_to_a_nan_google_month_stay_refused():
    fresh_books([cloud_line(last_month())], [google_line(last_month())],
                {"month": ledger.this_month(), "state": "known", "google_before": float("nan")})
    assert all(refusals().values())
    try:
        ledger.google_before()
        raise AssertionError("a NaN Google month was counted")
    except ledger.BooksUnknown as unknown:
        assert "not a figure of euros" in str(unknown), unknown
