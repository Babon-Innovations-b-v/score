"""Sign-in: the trusted proxy alone names the user; the allow-list admits and creates once; local mode has no
default user, its owner command needs a terminal and a long password, and serve binds only loopback without a proxy."""
import asyncio
import ipaddress

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, override_settings

from score.dashboard.auth import owner, proxy
from score.dashboard.auth.backends import AllowListRemoteUserBackend, AllowListRemoteUserMiddleware

PROXY = [ipaddress.ip_network("10.0.0.2/32")]


def answer(path, peer, headers, networks=PROXY):
    """The status the guard gives a request (200: passed on to the app)."""
    sent = []

    async def app(scope, receive, send):
        sent.append(200)

    async def send(message):
        if message["type"] == "http.response.start":
            sent.append(message["status"])
    scope = {"type": "http", "path": path, "client": (peer, 5000),
             "headers": [(name.encode(), value.encode()) for name, value in headers.items()]}
    asyncio.run(proxy.TrustedProxyGuard(app, networks)(scope, None, send))
    return sent[0]


def test_a_sign_in_header_from_an_untrusted_peer_is_refused():
    assert answer("/", "10.0.0.9", {"Remote-User": "joey"}) == 403
    assert answer("/", "10.0.0.9", {"remote-email": "a@b"}) == 403
    assert answer("/", "127.0.0.1", {"Remote-User": "joey"}, networks=[]) == 403  # local mode: never


def test_an_underscore_header_is_refused_from_every_peer():
    assert answer("/", "10.0.0.2", {"Remote_User": "joey"}) == 403
    assert answer("/", "10.0.0.2", {"remote_email": "a@b", "Remote-User": "joey"}) == 403


def test_a_trusted_peer_without_a_user_is_refused_but_health_and_sync_pass():
    assert answer("/", "10.0.0.2", {}) == 403
    assert answer("/healthz", "10.0.0.2", {}) == 200
    assert answer("/api/sync/requests", "10.0.0.2", {}) == 200
    assert answer("/", "10.0.0.2", {"Remote-User": "joey"}) == 200
    assert answer("/", "10.0.0.9", {}) == 403  # in proxy mode nothing comes round the proxy


@pytest.mark.django_db
@override_settings(SCORE_ALLOWED_USERS=["joey"])
def test_an_allow_listed_user_is_admitted_and_made_once_with_the_email():
    request = RequestFactory().get("/", HTTP_REMOTE_EMAIL="joey@example.org")
    backend = AllowListRemoteUserBackend()
    first = backend.authenticate(request, "joey")
    again = backend.authenticate(request, "joey")
    assert first.pk == again.pk and get_user_model().objects.filter(username="joey").count() == 1
    assert get_user_model().objects.get(username="joey").email == "joey@example.org"


@pytest.mark.django_db
@override_settings(SCORE_ALLOWED_USERS=["joey"],
                   AUTHENTICATION_BACKENDS=["score.dashboard.auth.backends.AllowListRemoteUserBackend"])
def test_a_user_off_the_list_is_refused_and_not_made():
    with pytest.raises(PermissionDenied):
        AllowListRemoteUserBackend().authenticate(RequestFactory().get("/"), "mallory")
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.sessions.backends.db import SessionStore
    request = RequestFactory().get("/", HTTP_REMOTE_USER="mallory")
    request.user, request.session = AnonymousUser(), SessionStore()
    response = AllowListRemoteUserMiddleware(lambda _: "page")(request)
    assert response.status_code == 403
    assert not get_user_model().objects.filter(username="mallory").exists()


@pytest.mark.django_db
def test_local_mode_has_no_default_user():
    assert not get_user_model().objects.exists()


@pytest.mark.django_db
def test_the_owner_command_needs_a_terminal_and_a_long_password():
    with pytest.raises(owner.Refused, match="terminal"):
        owner.owner_command("joey", terminal=False)
    answers = iter(["short", "short"])
    with pytest.raises(owner.Refused, match="12 characters"):
        owner.owner_command("joey", terminal=True, ask=lambda _: next(answers))
    answers = iter(["a long enough password", "another long password"])
    with pytest.raises(owner.Refused, match="differ"):
        owner.owner_command("joey", terminal=True, ask=lambda _: next(answers))
    answers = iter(["a long enough password"] * 2)
    user = owner.owner_command("joey", terminal=True, ask=lambda _: next(answers))
    assert user.check_password("a long enough password") and user.is_superuser


def test_serve_binds_only_loopback_without_a_proxy():
    assert owner.bind_refusal("127.0.0.1:8780", False) is None
    assert owner.bind_refusal("localhost:8780", False) is None
    assert owner.bind_refusal("[::1]:8780", False) is None
    assert "not a loopback" in owner.bind_refusal("0.0.0.0:8780", False)
    assert owner.bind_refusal("0.0.0.0:8780", True) is None
