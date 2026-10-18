"""The API's sign-in: the same Django session as the pages (one auth for both), the proxy's user checked again in
proxy mode, the owner's name for owner routes, and Django's CSRF check on every write."""
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.crypto import constant_time_compare
from fastapi import HTTPException, Request

WRITES = ("POST", "PUT", "PATCH", "DELETE")


def session_user(session_key):
    """The user a Django session holds, its auth hash checked, or None."""
    if not session_key:
        return None
    session = SessionStore(session_key=session_key)
    user_id = session.get(SESSION_KEY)
    if user_id is None or session.get(BACKEND_SESSION_KEY) not in settings.AUTHENTICATION_BACKENDS:
        return None
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None or not constant_time_compare(session.get(HASH_SESSION_KEY, ""), user.get_session_auth_hash()):
        return None
    return user


def django_request(request: Request):
    """A Django HttpRequest with the FastAPI request's method, headers and cookies (for the CSRF check)."""
    built = HttpRequest()
    built.method = request.method
    built.path = request.url.path
    built.COOKIES = dict(request.cookies)
    for name, value in request.headers.items():
        built.META["HTTP_" + name.upper().replace("-", "_")] = value
    built.META["SERVER_NAME"], built.META["SERVER_PORT"] = request.url.hostname or "", str(request.url.port or "")
    built.META["wsgi.url_scheme"] = "https" if settings.SCORE_PROXY_MODE else request.url.scheme
    if settings.SCORE_PROXY_MODE:
        built.is_secure = lambda: True
    return built


def csrf_refusal(request: Request):
    """Why a write fails Django's CSRF check (X-CSRFToken header, the csrftoken cookie, an allowed Origin), or None."""
    if not request.headers.get("origin"):
        return "a write needs its Origin header"
    built = django_request(request)
    refused = CsrfViewMiddleware(lambda _: None).process_view(built, lambda _: None, (), {})
    return None if refused is None else "the CSRF check failed: send X-CSRFToken from the csrftoken cookie"


def signed_in(request: Request):
    """The signed-in Django user (FastAPI dependency); 401 without a session, 403 when the proxy names another user
    or a write fails the CSRF check."""
    user = session_user(request.cookies.get(settings.SESSION_COOKIE_NAME))
    if user is None:
        raise HTTPException(401, "sign in first")
    if settings.SCORE_PROXY_MODE and request.headers.get("remote-user") != user.username:
        raise HTTPException(403, "the proxy names another user than this session's")
    if request.method in WRITES:
        refused = csrf_refusal(request)
        if refused:
            raise HTTPException(403, refused)
    return user


def owner_only(request: Request):
    """signed_in, and the user is SCORE_OWNER."""
    user = signed_in(request)
    if not settings.SCORE_OWNER or user.username != settings.SCORE_OWNER:
        raise HTTPException(403, "only the owner")
    return user
