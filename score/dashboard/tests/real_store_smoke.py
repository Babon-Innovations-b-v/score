"""The dashboard against the real store, read-only, by hand (not in `make tests`):

    SCORE_DASHBOARD_HOME=$(mktemp -d) .venv/bin/python -m score.dashboard.tests.real_store_smoke [--shots DIR]

It renders the world board, every place page, every accepted step page of the hangar and of the world line, the
basket, the hangar's viewer and every /api read, each as a signed-in owner of a throwaway account in the dashboard's
temp home; checks each answers 200, the index builds under 2 s and each place page under 2 s; and snapshots the
store's areas and data/ before and after: they must be the same. Then it exports into a temp folder and renders the
hosted pages from that export. The month's spend is not read (no cloud call): its backend here is Offline.
"""
import argparse
import os
import pathlib
import sys
import tempfile
import time

os.environ["SCORE_STORE_WRITABLE"] = "0"
os.environ["SCORE_COMPUTE_BACKEND"] = "score.dashboard.tests.real_store_smoke:Offline"
os.environ.setdefault("SCORE_OWNER", "smoke-owner")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")
if "SCORE_DASHBOARD_HOME" not in os.environ:
    sys.exit("set SCORE_DASHBOARD_HOME to a temp folder: the smoke's account and thumbnails go there")

AREAS = ("accepts", "rejects", "records", "judgements", "waivers", "clearances", "spend-yes", "outputs")
MOST_SECONDS = 2.0
FAILED = []  # every page or read that did not answer 200


class Offline:
    """A backend that reads no spend and starts nothing (the smoke never launches)."""

    name = "offline"

    def spend(self):
        from score.dashboard.state.models import Spend
        return Spend(note="not read in the smoke run: no cloud calls")

    def plan(self, group):
        raise RuntimeError("the smoke run plans nothing")

    def measured(self):
        return []

    def launch(self, group, jobs, rebuy_reason):
        raise RuntimeError("the smoke run launches nothing")

    def poll(self, handle):
        raise RuntimeError("the smoke run launches nothing")


def tree_state(folder):
    """(file count, newest mtime) of a folder, or of one file."""
    folder = pathlib.Path(folder)
    if folder.is_file():
        return 1, folder.stat().st_mtime
    count, newest = 0, 0.0
    for root, _, names in os.walk(folder):
        for name in names:
            count += 1
            newest = max(newest, os.stat(os.path.join(root, name)).st_mtime)
    return count, newest


def snapshot(props, repo):
    objects = props / "store" / "objects"
    found = {area: tree_state(objects / area) for area in AREAS}
    found["reservations.json"] = tree_state(props / "store" / "reservations.json")
    found["data"] = tree_state(repo / "data")
    return found


def owner_client():
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.test import Client
    user, _ = get_user_model().objects.get_or_create(username=settings.SCORE_OWNER)
    client = Client(HTTP_HOST="127.0.0.1", raise_request_exception=False)
    client.force_login(user)
    return client


def api_client(pages):
    """The whole ASGI app (the /api routes are FastAPI's) carrying the pages client's session."""
    from fastapi.testclient import TestClient

    from score.dashboard.site.asgi import app
    client = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    for cookie in pages.cookies.values():
        client.cookies.set(cookie.key, cookie.value)
    return client


def fetched(client, path, shots, timings):
    started = time.monotonic()
    answer = (api_client(client) if path.startswith("/api") else client).get(path)
    timings[path] = time.monotonic() - started
    if answer.status_code != 200:
        FAILED.append(f"{path}: {answer.status_code}")
    if shots and not path.startswith("/api"):
        name = path.strip("/").replace("/", "_") or "board"
        (shots / f"{name}.html").write_bytes(answer.content)
    return answer


def api_reads(source):
    yield "/api/state"
    yield "/api/spend"
    yield "/api/requests"
    yield "/api/launches"
    yield "/api/basket/items"
    for place in source.places():
        yield f"/api/places/{place}"
    yield "/api/places/hangar/steps/assembly"
    yield "/api/world/steps/terrain"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=pathlib.Path, help="save each page's HTML here")
    options = parser.parse_args()
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=0)
    from score.dashboard import state
    props, repo = settings.SCORE_PROPS_HOME, settings.SCORE_REPO
    before = snapshot(props, repo)
    source = state.source()
    started = time.monotonic()
    source.refresh()
    index_seconds = time.monotonic() - started
    client, timings = owner_client(), {}
    if options.shots:
        options.shots.mkdir(parents=True, exist_ok=True)
    fetched(client, "/", options.shots, timings)
    for place in source.places():
        fetched(client, f"/place/{place}/", options.shots, timings)
    hangar = [row.name for row in source.place_rows("hangar") if source.accepted_output(f"{row.name}@hangar")]
    for stage in hangar:
        fetched(client, f"/place/hangar/step/{stage}/", options.shots if stage in ("closeup", "assembly") else None,
                timings)
    for row in source.world_rows():
        if source.accepted_output(row.name):
            fetched(client, f"/world/step/{row.name}/", None, timings)
    for path in ("/basket/", "/view/hangar", "/runs/", "/requests/", *api_reads(source)):
        fetched(client, path, options.shots if path == "/basket/" else None, timings)
    after = snapshot(props, repo)
    slow = {path: round(seconds, 2) for path, seconds in timings.items()
            if path.startswith("/place/") and path.count("/") == 3 and seconds > MOST_SECONDS}
    print(f"index built in {index_seconds:.2f} s; {len(timings)} pages and reads, not 200: {FAILED or 'none'}; "
          f"slowest {max(timings, key=timings.get)} {max(timings.values()):.2f} s")
    print(f"place pages over {MOST_SECONDS} s: {slow or 'none'}")
    print("store and data unchanged" if before == after else f"CHANGED: {before} -> {after}")
    hosted_pages(source, options.shots)
    if before != after or slow or index_seconds > MOST_SECONDS or FAILED:
        sys.exit(1)


def hosted_pages(source, shots):
    """Export into a temp folder and render the hosted pages from it."""
    from django.conf import settings

    from score.dashboard import state
    from score.dashboard.state.exported import ExportedSource
    from score.dashboard.sync import building
    folder = pathlib.Path(tempfile.mkdtemp(prefix="score-export-", dir=settings.SCORE_HOME))
    started = time.monotonic()
    manifest = building.build(source, folder, "2026-10-18T00:00:00+00:00", settings.SCORE_EXPORT_MAX_MB,
                              Offline().spend(), settings.SCORE_REPO)
    print(f"export: {manifest['bytes'] / 1e6:.1f} MB in {time.monotonic() - started:.1f} s, "
          f"{len(manifest['left_out'])} files left out over the {manifest['cap_mb']} MB cap")
    state.source = lambda: ExportedSource(folder)
    settings.SCORE_MODE = settings.HOSTED
    client, timings = owner_client(), {}
    for path in ("/", "/place/hangar/", "/place/hangar/step/closeup/", "/requests/"):
        fetched(client, path, None, timings)
    if shots:
        (shots / "hosted_board.html").write_bytes(client.get("/").content)
    print(f"hosted pages from the export: {len(timings)} pages; not 200 so far: {FAILED or 'none'}")


if __name__ == "__main__":
    main()
