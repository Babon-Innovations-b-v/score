"""Every dashboard test runs in temp folders: PROPS_HOME and the dashboard's home are made here before Django's
settings are read, so no test can reach the real store or write beside it."""
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


@pytest.fixture(scope="session")
def blockouts():
    """One folder of blockout renders every test run shares (each written whole, local.blockout_ref): each is named by
    the hash of what it is built from and the blockout code (blockout.scene_key), so a test reads the render an
    earlier test or run made of the same scene, never another's (2.7 s a render, five a page)."""
    folder = pathlib.Path(tempfile.gettempdir()) / "score-test-blockouts"
    folder.mkdir(exist_ok=True)
    return folder


@pytest.fixture
def world(tmp_path, monkeypatch, blockouts):
    """The fixture environment (tests/fixture.py) served as this process's source, decisions on, both places
    designed."""
    return served(fixture_built(tmp_path, True), monkeypatch, blockouts)


@pytest.fixture
def drafting(tmp_path, monkeypatch, blockouts):
    """The fixture environment still in design (alpha drawn, beta not, nothing locked) served the same way."""
    return served(fixture_built(tmp_path, False), monkeypatch, blockouts)


def fixture_built(tmp_path, design):
    from score.dashboard.tests import fixture
    return fixture.build(tmp_path, design)


def served(built, monkeypatch, blockouts):
    """`built` served as this process's source, decisions on."""
    from score.dashboard import state
    from score.dashboard.pages import actions
    from score.dashboard.tests import fixture
    built.source.home.mkdir(parents=True, exist_ok=True)
    (built.source.home / "blockouts").symlink_to(blockouts)
    monkeypatch.setattr(state, "source", lambda: built.source)
    monkeypatch.setattr(actions, "agent_started", lambda: False)
    fixture.FakeBackend.calls.clear()
    return built


@pytest.fixture
def read(world):
    """alpha's and beta's scene inventories read from their picked concepts, so their numbers count (CONTEXT.md
    "scene inventory"): the fixture designs both (fixture.designed); alpha's its drawn picture, beta's lost."""
    world.source.refresh()
    return world
