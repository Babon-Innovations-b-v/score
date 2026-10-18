"""The local mode's one owner account: made or updated from the owner's own terminal, never with a default password.

    .venv/bin/python -m score.dashboard owner <name>
"""
import getpass
import ipaddress
import sys

SHORTEST = 12
LOOPBACK_NAMES = ("localhost",)


class Refused(Exception):
    """The owner command or the server start is refused, with why."""


def at_terminal(stdin=None, stdout=None):
    """True when both stdin and stdout are terminals (the owner typing)."""
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    return stdin.isatty() and stdout.isatty()


def checked_password(first, second):
    """The password when both entries match and it is long enough; else Refused."""
    if first != second:
        raise Refused("the two passwords differ")
    if len(first) < SHORTEST:
        raise Refused(f"the password needs at least {SHORTEST} characters")
    return first


def asked_password(ask=getpass.getpass):
    return checked_password(ask("owner password: "), ask("again: "))


def set_owner(name, password):
    """Create or update the owner account `name` (a superuser, for the admin) with `password`; the user."""
    from django.contrib.auth import get_user_model
    user, _ = get_user_model().objects.get_or_create(username=name)
    user.is_staff = user.is_superuser = True
    user.set_password(password)
    user.save()
    return user


def owner_command(name, terminal=None, ask=getpass.getpass):
    """The `owner` command: refused without a terminal, the password asked twice."""
    if not (terminal if terminal is not None else at_terminal()):
        raise Refused("the owner account is set from the owner's own terminal (stdin and stdout a TTY)")
    if not name.strip():
        raise Refused("the owner needs a user name")
    return set_owner(name.strip(), asked_password(ask))


def loopback(host):
    """True for a loopback bind host: 127.0.0.0/8, ::1 or localhost."""
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def bind_refusal(bind, proxy_mode):
    """Why `serve` must not start on `bind`, or None: without a trusted proxy only a loopback address."""
    host = bind.rsplit(":", 1)[0]
    if not proxy_mode and not loopback(host):
        return (f"refused: {host} is not a loopback address, and with no trusted proxy (SCORE_TRUSTED_PROXIES) the "
                "password sign-in serves this machine only")
    return None
