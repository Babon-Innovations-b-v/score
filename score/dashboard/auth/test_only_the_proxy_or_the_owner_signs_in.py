"""Invariant: a user is named only by the trusted proxy, and admitted only from the allow-list; local mode has no
default user, its one owner account is set from a terminal with a long password, and without a proxy the server binds
only loopback.

Breaks that turn this red (each applied once and seen red, then reverted):
- proxy.refusal: drop the underscore check (`if any("_" in name ...)`) -> test_an_underscore_header_is_refused_...
- proxy.refusal: `if named and not trusted` -> `if False` -> test_a_sign_in_header_from_an_untrusted_peer_...
- proxy.OPEN_PATHS = () -> test_a_trusted_peer_without_a_user_is_refused_but_health_and_sync_pass
- backends.authenticate: drop the allow-list check -> test_a_user_off_the_list_is_refused_and_not_made
- backends.with_email: `if email and ...` -> `if False` -> test_an_allow_listed_user_is_made_once_with_the_email
- owner.SHORTEST = 4 -> test_the_owner_command_needs_a_terminal_and_a_long_password
- owner.loopback: `return True` first -> test_serve_binds_only_loopback_without_a_proxy
"""
import asyncio
import ipaddress

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
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
    assert answer("/", "127.0.0.1", {}, networks=[]) == 200  # local mode, no header: the password sign-in's page


def test_an_underscore_header_is_refused_from_every_peer():
    """Django reads `remote_user` and `Remote-User` as one name, so the underscore spelling is never let through."""
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
def test_an_allow_listed_user_is_made_once_with_the_email():
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
    request = RequestFactory().get("/", HTTP_REMOTE_USER="mallory")
    request.user, request.session = AnonymousUser(), SessionStore()
    response = AllowListRemoteUserMiddleware(lambda _: "page")(request)
    assert response.status_code == 403
    assert not get_user_model().objects.filter(username="mallory").exists()


@pytest.mark.django_db
def test_the_owner_command_needs_a_terminal_and_a_long_password():
    assert not get_user_model().objects.exists()  # local mode starts with no default user (no migration makes one)
    with pytest.raises(owner.Refused, match="terminal"):
        owner.owner_command("joey", terminal=False)
    answers = iter(["elevenchars", "elevenchars"])  # one short of the 12 the owner rule asks
    with pytest.raises(owner.Refused, match="12 characters"):
        owner.owner_command("joey", terminal=True, ask=lambda _: next(answers))
    answers = iter(["a long enough password", "another long password"])
    with pytest.raises(owner.Refused, match="differ"):
        owner.owner_command("joey", terminal=True, ask=lambda _: next(answers))
    assert not get_user_model().objects.exists()  # nothing refused made an account
    answers = iter(["twelve chars"] * 2)
    user = owner.owner_command("joey", terminal=True, ask=lambda _: next(answers))
    assert user.check_password("twelve chars") and user.is_superuser


def test_serve_binds_only_loopback_without_a_proxy():
    assert owner.bind_refusal("127.0.0.1:8780", False) is None
    assert owner.bind_refusal("localhost:8780", False) is None
    assert owner.bind_refusal("[::1]:8780", False) is None
    assert owner.bind_refusal("0.0.0.0:8780", False) is not None
    assert owner.bind_refusal("192.168.1.5:8780", False) is not None
    assert owner.bind_refusal("0.0.0.0:8780", True) is None
