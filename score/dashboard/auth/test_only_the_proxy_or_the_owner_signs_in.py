"""Invariant: a user is named only by the trusted proxy, and admitted only from the allow-list; local mode has no
default user, its one owner account is set from a terminal with a long password, and without a proxy the server binds
only loopback.

One test: every knock on the dashboard is a row (a request to the proxy guard, a name the proxy sends to Django, an
owner command, a bind address), each driven through its real entry point in one database world.

Breaks that turn this red (each applied once and seen red, then reverted):
- proxy.refusal: drop the underscore check (`if any("_" in name ...)`) -> the guard rows with an underscore header
- proxy.refusal: `if named and not trusted` -> `if False` -> the guard rows with a header from an untrusted peer
- proxy.OPEN_PATHS = () -> the guard row for /healthz from the trusted peer with no user
- backends.authenticate: drop the allow-list check -> the sign-in row for mallory (refused, never made)
- backends.with_email: `if email and ...` -> `if False` -> the sign-in rows for joey (made once, with the email)
- owner.SHORTEST = 4 -> the owner row with an eleven-character password
- owner.loopback: `return True` first -> the bind rows for 0.0.0.0 and 192.168.1.5 without a proxy
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
LOCAL = []

# (path, peer, headers, trusted networks, status the guard gives: 200 passed on to the app)
GUARD_ROWS = [
    ("/", "10.0.0.9", {"Remote-User": "joey"}, PROXY, 403),  # a sign-in header from an untrusted peer
    ("/", "10.0.0.9", {"remote-email": "a@b"}, PROXY, 403),
    ("/", "127.0.0.1", {"Remote-User": "joey"}, LOCAL, 403),  # local mode: never
    ("/", "127.0.0.1", {}, LOCAL, 200),  # local mode, no header: the password sign-in's page
    # Django reads `remote_user` and `Remote-User` as one name, so the underscore spelling is refused from every peer
    ("/", "10.0.0.2", {"Remote_User": "joey"}, PROXY, 403),
    ("/", "10.0.0.2", {"remote_email": "a@b", "Remote-User": "joey"}, PROXY, 403),
    ("/", "10.0.0.2", {}, PROXY, 403),  # the trusted peer sent no user
    ("/healthz", "10.0.0.2", {}, PROXY, 200),
    ("/api/sync/requests", "10.0.0.2", {}, PROXY, 200),
    ("/", "10.0.0.2", {"Remote-User": "joey"}, PROXY, 200),
    ("/", "10.0.0.9", {}, PROXY, 403),  # in proxy mode nothing comes round the proxy
]

# (name the proxy sends, Remote-Email, admitted)
SIGN_IN_ROWS = [("joey", "joey@example.org", True), ("joey", "joey@example.org", True), ("mallory", "", False)]

# (at a terminal, the two password entries, the refusal's words or None for an owner made)
OWNER_ROWS = [
    (False, None, "terminal"),
    (True, ["elevenchars", "elevenchars"], "12 characters"),  # one short of the 12 the owner rule asks
    (True, ["a long enough password", "another long password"], "differ"),
    (True, ["twelve chars"] * 2, None),
]

# (bind address, proxy mode, refused)
BIND_ROWS = [("127.0.0.1:8780", False, False), ("localhost:8780", False, False), ("[::1]:8780", False, False),
             ("0.0.0.0:8780", False, True), ("192.168.1.5:8780", False, True), ("0.0.0.0:8780", True, False)]


def guard_status(path, peer, headers, networks):
    """The status the proxy guard gives a request (200: passed on to the app)."""
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


def signed_in(name, email):
    """The middleware's answer to a request the proxy names `name` on: the page, or its 403."""
    request = RequestFactory().get("/", HTTP_REMOTE_USER=name, HTTP_REMOTE_EMAIL=email)
    request.user, request.session = AnonymousUser(), SessionStore()
    return AllowListRemoteUserMiddleware(lambda _: "page")(request)


def owner_answer(terminal, entries):
    """The owner command's account, or the words of its refusal."""
    answers = iter(entries or [])
    try:
        return owner.owner_command("owner", terminal=terminal, ask=lambda _: next(answers))
    except owner.Refused as refused:
        return str(refused)


@pytest.mark.django_db
@override_settings(SCORE_ALLOWED_USERS=["joey"],
                   AUTHENTICATION_BACKENDS=["score.dashboard.auth.backends.AllowListRemoteUserBackend"])
def test_only_the_proxy_or_the_owner_signs_in():
    users = get_user_model().objects
    for path, peer, headers, networks, status in GUARD_ROWS:
        assert guard_status(path, peer, headers, networks) == status, (path, peer, headers, networks)

    assert not users.exists()  # local mode starts with no default user (no migration makes one)
    for terminal, entries, refusal in OWNER_ROWS:
        answer = owner_answer(terminal, entries)
        if refusal:
            assert isinstance(answer, str) and refusal in answer, (terminal, entries, answer)
            assert not users.exists(), (terminal, entries)  # nothing refused made an account
        else:
            assert answer.check_password(entries[0]) and answer.is_superuser, (terminal, entries)

    for name, email, admitted in SIGN_IN_ROWS:
        response = signed_in(name, email)
        assert (response == "page") == admitted, (name, response)
        if not admitted:
            assert response.status_code == 403, name
            with pytest.raises(PermissionDenied):
                AllowListRemoteUserBackend().authenticate(RequestFactory().get("/"), name)
        made = users.filter(username=name)
        assert made.count() == (1 if admitted else 0), name  # made once, and never off the list
        if admitted:
            assert made.get().email == email, name

    for bind, proxy_mode, refused in BIND_ROWS:
        assert (owner.bind_refusal(bind, proxy_mode) is not None) == refused, (bind, proxy_mode)
