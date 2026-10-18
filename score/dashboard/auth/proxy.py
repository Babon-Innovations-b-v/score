"""The outermost ASGI guard of the trusted-proxy sign-in: only the reverse proxy may name the user.

From a peer that is not a trusted proxy, any `Remote-User` or `Remote-Email` header is refused (403). A header
spelled with an underscore (`remote_user`) is refused from every peer, since Django reads `-` and `_` as one name.
From a trusted peer, a request with no `Remote-User` is refused, except /healthz and /api/sync/* (token sign-in).
With no trusted proxies configured (local mode) only the header rules apply: no peer may send them at all.
uvicorn runs with --no-proxy-headers, so the peer is the direct connection, never X-Forwarded-For.
"""
import ipaddress
import json

SIGN_IN_HEADERS = ("remote-user", "remote-email")
OPEN_PATHS = ("/healthz",)
TOKEN_PREFIX = "/api/sync/"


def peer_trusted(scope, networks):
    """True when the request's direct peer is inside one of the trusted networks."""
    client = scope.get("client")
    if not client or not networks:
        return False
    try:
        address = ipaddress.ip_address(client[0])
    except ValueError:
        return False
    return any(address in network for network in networks)


def header_names(scope):
    return [name.decode("latin-1").lower() for name, _ in scope.get("headers", [])]


def refusal(scope, networks):
    """Why a request is refused, or None."""
    names = header_names(scope)
    if any("_" in name and name.replace("_", "-") in SIGN_IN_HEADERS for name in names):
        return "a sign-in header spelled with an underscore is never accepted"
    named = any(name in SIGN_IN_HEADERS for name in names)
    trusted = peer_trusted(scope, networks)
    if named and not trusted:
        return "sign-in headers come only from the trusted proxy"
    path = scope.get("path", "")
    if networks and trusted and "remote-user" not in names and path not in OPEN_PATHS and not path.startswith(
            TOKEN_PREFIX):
        return "the proxy sent no signed-in user"
    if networks and not trusted and path not in OPEN_PATHS and not path.startswith(TOKEN_PREFIX):
        return "this dashboard is reached only through its proxy"
    return None


class TrustedProxyGuard:
    """ASGI middleware applying `refusal` to every HTTP request."""

    def __init__(self, app, networks):
        self.app = app
        self.networks = networks

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            refused = refusal(scope, self.networks)
            if refused:
                body = json.dumps({"error": refused}).encode()
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)
