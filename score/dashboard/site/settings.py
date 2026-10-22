"""The dashboard's Django settings, read from the environment only: nothing host- or company-specific is in the repo.

Mode `local` sits beside the store and reads it; `hosted` reads a state export the store's machine pushes and queues
the owner's requests for that machine to pull (score/dashboard/sync). Sign-in is the trusted proxy's single sign-on
when SCORE_TRUSTED_PROXIES is set, else (local only) the one owner account.
"""
import ipaddress
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


def trusted_networks(entries):
    """The trusted proxies' addresses or CIDRs as networks."""
    return [ipaddress.ip_network(entry, strict=False) for entry in entries]


SCORE_MODE = os.environ.get("SCORE_DASHBOARD_MODE", LOCAL)
if SCORE_MODE not in (LOCAL, HOSTED):
    raise ValueError(f"SCORE_DASHBOARD_MODE is {SCORE_MODE!r}: it is {LOCAL} or {HOSTED}")
SCORE_HOME = pathlib.Path(os.environ.get("SCORE_DASHBOARD_HOME", PROPS_HOME / "dashboard"))
SCORE_HOME.mkdir(parents=True, exist_ok=True)
SCORE_BIND = os.environ.get("SCORE_BIND", "127.0.0.1:8780")
SCORE_TRUSTED_PROXIES = trusted_networks(listed("SCORE_TRUSTED_PROXIES"))
SCORE_PROXY_MODE = bool(SCORE_TRUSTED_PROXIES)
SCORE_ALLOWED_USERS = listed("SCORE_ALLOWED_USERS")
SCORE_OWNER = os.environ.get("SCORE_OWNER", "").strip()
SCORE_STORE_WRITABLE = os.environ.get("SCORE_STORE_WRITABLE", "1") == "1"
SCORE_COMPUTE_BACKEND = os.environ.get("SCORE_COMPUTE_BACKEND", "score.dashboard.launch.localrun:LocalBackend")
SCORE_LEDGER_FILES = [pathlib.Path(item) for item in os.environ.get("SCORE_LEDGER_FILES", "").split(":") if item]
# The fresh 3D web copies (python -m score.dashboard web3d <place>), made from each accepted assembly.
SCORE_WEB_COPIES = pathlib.Path(os.environ.get("SCORE_WEB_COPIES", SCORE_HOME / "web3d"))
# The creator's library (state/library.py): its folder, the folder of its file bytes, and its own command, run there
# for the owner's lock and withdraw. Unset: no Library page.
SCORE_LIB_ROOT = os.environ.get("SCORE_LIB_ROOT", "").strip() or sibling_library()
SCORE_LIB_BLOBS_DIR = os.environ.get("SCORE_LIB_BLOBS_DIR", "").strip() or None
SCORE_LIB_COMMAND = os.environ.get("SCORE_LIB_COMMAND", "score-lib")
SCORE_SYNC_TOKEN = os.environ.get("SCORE_SYNC_TOKEN", "")
SCORE_SYNC_URL = os.environ.get("SCORE_SYNC_URL", "").rstrip("/")
# Raised from the spec's 300 for the 3D copies in the export (owner, 2026-10-18: the hosted cockpit has 3D too).
SCORE_EXPORT_MAX_MB = float(os.environ.get("SCORE_EXPORT_MAX_MB", "1000"))
SCORE_SYNC_MAX_EUROS = float(os.environ.get("SCORE_SYNC_MAX_EUROS", "0"))
SCORE_PROPS_HOME = PROPS_HOME
SCORE_REPO = REPO
# The score commit this process was built at: the hosted image's SCORE_COMMIT (its Dockerfile's ARG, set as ENV), told
# by /healthz so the conductor's score-update timer follows the one pin a release moves. Unset (None) outside an image.
SCORE_COMMIT = os.environ.get("SCORE_COMMIT", "").strip() or None

SECRET_KEY = secret_key(SCORE_HOME)
DEBUG = False
ALLOWED_HOSTS = listed("SCORE_ALLOWED_HOSTS") or ["127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS] if SCORE_PROXY_MODE else [
    f"http://{host}:{SCORE_BIND.rsplit(':', 1)[-1]}" for host in ALLOWED_HOSTS]
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SCORE_PROXY_MODE
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "score.dashboard.pages.apps.PagesConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    *(["score.dashboard.auth.backends.AllowListRemoteUserMiddleware"] if SCORE_PROXY_MODE else []),
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
]
AUTHENTICATION_BACKENDS = (["score.dashboard.auth.backends.AllowListRemoteUserBackend"] if SCORE_PROXY_MODE
                           else ["django.contrib.auth.backends.ModelBackend"])
ROOT_URLCONF = "score.dashboard.site.urls"
DATA_UPLOAD_MAX_MEMORY_SIZE = 18 * 1024 * 1024  # a reference picture, base64 in its JSON (pages/environment.py)
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "score.dashboard.pages.views.everywhere",
    ]},
}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": SCORE_HOME / "dashboard.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                             "OPTIONS": {"min_length": 12}}]
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
STATIC_ROOT = PACKAGE / "pages" / "static"
DESIGN_ROOT = REPO / "design"  # the design tokens and font, served at /static/design/
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "WARNING"}}
