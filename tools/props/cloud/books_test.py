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
import google_spend  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
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
    """What two paid points say now: month_refusal's reason and require_cleared's Refused, None when open."""
    said = {"month": compute.month_refusal(1.0)}
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
    assert round(compute.month_spent(), 6) == 415.0
    assert round(compute.books_now()["google"], 6) == 405.0


def test_books_of_an_earlier_month_count_nothing_now():
    fresh_books([cloud_line(last_month())], [google_line(last_month())],
                {"month": last_month(), "state": "known", "google_before": 400.0})
    assert ledger.google_before() == 0.0 and ledger.books_refusal() is None


def test_a_free_only_process_refuses_before_the_books_are_read():
    fresh_books([cloud_line(last_month())], [google_line(last_month())])
    os.environ[ledger.FREE_ONLY] = "1"
    try:
        compute.month_refusal(1.0)
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

