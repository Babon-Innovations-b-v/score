"""The one ASGI app: FastAPI's /api and file routes, the static files, and Django for every page, inside the trusted
proxy guard.

    uvicorn score.dashboard.site.asgi:app --no-proxy-headers --workers 1
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")

from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

django_app = get_asgi_application()

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.openapi.docs import get_swagger_ui_html  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from score.dashboard.api.deps import signed_in  # noqa: E402
from score.dashboard.api.library import library_files  # noqa: E402
from score.dashboard.api.library_api import library_api  # noqa: E402
from score.dashboard.api.routes import api, files  # noqa: E402
from score.dashboard.auth.proxy import TrustedProxyGuard  # noqa: E402
from score.dashboard.checkout.routes import checkout  # noqa: E402
from score.dashboard.sync.endpoints import sync  # noqa: E402

inner = FastAPI(title="SCORE dashboard", docs_url=None, redoc_url=None, openapi_url=None)
inner.include_router(sync, prefix="/api/sync")
inner.include_router(checkout, prefix="/api/checkout")
inner.include_router(library_api, prefix="/api/library")
inner.include_router(api, prefix="/api")
inner.include_router(files)
inner.include_router(library_files)


@inner.get("/api/openapi.json", include_in_schema=False)
def openapi(user=Depends(signed_in)):
    return inner.openapi()


@inner.get("/api/docs", include_in_schema=False)
def docs(user=Depends(signed_in)):
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="SCORE dashboard API")


inner.mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")
inner.mount("/", django_app)
app = TrustedProxyGuard(inner, settings.SCORE_TRUSTED_PROXIES)
