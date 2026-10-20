"""Every dashboard test runs in temp folders: PROPS_HOME and the dashboard's home are made here before Django's
settings are read, so no test can reach the real store or write beside it."""
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(tempfile.mkdtemp(prefix="score-dashboard-test-"))
os.environ["PROPS_HOME"] = str(ROOT / "props")
os.environ["SCORE_DASHBOARD_HOME"] = str(ROOT / "dashboard")
os.environ["DJANGO_SETTINGS_MODULE"] = "score.dashboard.site.settings"
os.environ.setdefault("SCORE_OWNER", "joey")
os.environ.setdefault("SCORE_COMPUTE_BACKEND", "score.dashboard.tests.fixture:FakeBackend")
for name in ("SCORE_TRUSTED_PROXIES", "SCORE_ALLOWED_USERS", "SCORE_SYNC_TOKEN", "SCORE_DASHBOARD_MODE"):
    os.environ.pop(name, None)
(ROOT / "props").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import django  # noqa: E402
import pytest  # noqa: E402

django.setup()  # pytest-django reads the settings module before this file runs, so it is set up here

from django.conf import settings  # noqa: E402

settings.SCORE_LIB_ROOT = None  # its default is the real score_lib beside score: a test brings its own (library_test)


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The fixture environment (tests/fixture.py) served as this process's source, decisions on."""
    from score.dashboard import state
    from score.dashboard.pages import actions
    from score.dashboard.tests import fixture
    built = fixture.build(tmp_path)
    monkeypatch.setattr(state, "source", lambda: built.source)
    monkeypatch.setattr(actions, "agent_started", lambda: False)
    fixture.FakeBackend.calls.clear()
    return built


@pytest.fixture
def read(world):
    """alpha's and beta's concepts picked and their scene inventories read from them, so their numbers count
    (CONTEXT.md "scene inventory"; alpha's its concepts.json picture, beta's a sha of its own: its picture is lost)."""
    from score.dashboard.tests import fixture
    alpha = json.loads((world.data / "places/concepts.json").read_text())["concepts"]["alpha"]["sha256"]
    for place, sha in (("alpha", alpha), ("beta", "b" * 64)):
        fixture.an_inventory_read(world.store, world.data, place, sha)
    world.source.refresh()
    return world
