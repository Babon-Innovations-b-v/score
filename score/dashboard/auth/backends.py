"""The proxy sign-in's Django side: the user the trusted proxy names, admitted only from the allow-list."""
from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden


class AllowListRemoteUserBackend(RemoteUserBackend):
    """Finds or creates the named user only when SCORE_ALLOWED_USERS lists the name; keeps Remote-Email on the
    user; anyone else is refused and no user is made."""

    create_unknown_user = True

    def authenticate(self, request, remote_user):
        if not remote_user or remote_user not in settings.SCORE_ALLOWED_USERS:
            raise PermissionDenied(f"{remote_user!r} is not on this dashboard's allow-list")
        return super().authenticate(request, remote_user)

    def configure_user(self, request, user, created=True):
        return self.with_email(request, user)

    def user_can_authenticate(self, user):
        return user.username in settings.SCORE_ALLOWED_USERS and super().user_can_authenticate(user)

    @staticmethod
    def with_email(request, user):
        """The proxy's Remote-Email stored on the user when it changed."""
        email = request.META.get("HTTP_REMOTE_EMAIL", "") if request else ""
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])
        return user


class AllowListRemoteUserMiddleware(RemoteUserMiddleware):
    """Django's RemoteUserMiddleware on the `Remote-User` header (every request; a missing header signs out), run
    synchronously so this class's own steps run under ASGI too: a named user the allow-list refuses gets 403, and
    the email is refreshed each request."""

    header = "HTTP_REMOTE_USER"
    async_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        self.is_async = False

    def __call__(self, request):
        self.process_request(request)
        named = request.META.get(self.header)
        if named and not request.user.is_authenticated:
            return HttpResponseForbidden(f"{named} is not on this dashboard's allow-list")
        if request.user.is_authenticated:
            AllowListRemoteUserBackend.with_email(request, request.user)
        return self.get_response(request)
