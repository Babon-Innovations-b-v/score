"""The Django settings of the owner's chat decisions and Buys (their records: pages/models.py), read from the
environment only: nothing host- or company-specific is in the repo. No page is served: the cockpit's pages, sign-in
and hosted side went (owner, 2026-11-16, "cockpit can also go"). It sits beside the store and reads it.
"""
import os
import pathlib
import secrets

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
LOCAL, HOSTED = "local", "hosted"


def listed(name):
    """A comma list from the environment, empty items dropped."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def sibling_library():
    """score_lib's checkout beside score's main checkout (found from a worktree's .git file too), as the library
    command's own default does (tools/library/library_files.py default_root); None when there is none (a hosted
    image)."""
    git = REPO / ".git"
    main = pathlib.Path(git.read_text().split(":", 1)[1].strip()).parents[2] if git.is_file() else REPO
    found = main.parent / "score_lib"
    return str(found) if (found / "entries").is_dir() else None


def secret_key(home):
    """SCORE_DASHBOARD_SECRET_KEY, else one generated once into the dashboard's home (mode 0600)."""
    given = os.environ.get("SCORE_DASHBOARD_SECRET_KEY")
    if given:
        return given
    path = home / "secret_key"
    if not path.exists():
        home.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as written:
            written.write(secrets.token_urlsafe(50))
    return path.read_text().strip()


SCORE_MODE = os.environ.get("SCORE_DASHBOARD_MODE", LOCAL)
if SCORE_MODE not in (LOCAL, HOSTED):
    raise ValueError(f"SCORE_DASHBOARD_MODE is {SCORE_MODE!r}: it is {LOCAL} or {HOSTED}")
SCORE_HOME = pathlib.Path(os.environ.get("SCORE_DASHBOARD_HOME", PROPS_HOME / "dashboard"))
SCORE_HOME.mkdir(parents=True, exist_ok=True)
SCORE_OWNER = os.environ.get("SCORE_OWNER", "").strip()
SCORE_STORE_WRITABLE = os.environ.get("SCORE_STORE_WRITABLE", "1") == "1"
SCORE_COMPUTE_BACKEND = os.environ.get("SCORE_COMPUTE_BACKEND", "score.dashboard.launch.localrun:LocalBackend")
SCORE_LEDGER_FILES = [pathlib.Path(item) for item in os.environ.get("SCORE_LEDGER_FILES", "").split(":") if item]
# The creator's library (state/library.py): its folder, the folder of its file bytes, and its own command, run there
# for the owner's lock and withdraw. Unset: no Library page.
SCORE_LIB_ROOT = os.environ.get("SCORE_LIB_ROOT", "").strip() or sibling_library()
SCORE_LIB_BLOBS_DIR = os.environ.get("SCORE_LIB_BLOBS_DIR", "").strip() or None
SCORE_LIB_COMMAND = os.environ.get("SCORE_LIB_COMMAND", "score-lib")
SCORE_SYNC_MAX_EUROS = float(os.environ.get("SCORE_SYNC_MAX_EUROS", "0"))
SCORE_PROPS_HOME = PROPS_HOME
SCORE_REPO = REPO

SECRET_KEY = secret_key(SCORE_HOME)
DEBUG = False
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "score.dashboard.pages.apps.PagesConfig",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": SCORE_HOME / "dashboard.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                             "OPTIONS": {"min_length": 12}}]
USE_TZ = True
TIME_ZONE = "UTC"
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "WARNING"}}
