"""The written exceptions to the library rule: one data file the check reads, so an exception is wired, never only
written.

    data/checks/library-exceptions.json   {"exceptions": [{"place", "prim", "aspect", "what", "why", "allowed_by",
                                                         "allowed_on", "expires"}]}

`place` is a place or `*`; `prim` a prim path or a pattern (`fnmatch`: `/hangar/Structure/*`); `aspect` is `source`
(where the thing comes from), `finish` (its finishes) or `both`; `allowed_by` the owner's handle; `allowed_on` and the
optional `expires` are dates (YYYY-MM-DD). An exception without a reason (`why`) or an owner (`allowed_by`), or with
any other field missing, refuses the whole file: the check does not run on a half-written exception. One past its
`expires` covers nothing.
"""
import datetime
import fnmatch
import json
import pathlib

FILE = pathlib.Path(__file__).resolve().parents[4] / "data/checks/library-exceptions.json"
REQUIRED = ("place", "prim", "what", "why", "allowed_by", "allowed_on")
ASPECTS = ("source", "finish", "both")


class Refused(ValueError):
    """An exception the file cannot hold."""


def date_of(text, field, number):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        raise Refused(f"exception {number}: {field} {text!r} is not a date (YYYY-MM-DD)") from None


def checked(exception, number):
    """One exception as written, refused when a field is missing or empty, its aspect unknown or a date not one."""
    missing = [field for field in REQUIRED if not str(exception.get(field) or "").strip()]
    if missing:
        raise Refused(f"exception {number} ({exception.get('prim', '?')}): no {', '.join(missing)}")
    aspect = exception.get("aspect", "both")
    if aspect not in ASPECTS:
        raise Refused(f"exception {number}: aspect {aspect!r} is not one of {', '.join(ASPECTS)}")
    date_of(exception["allowed_on"], "allowed_on", number)
    if exception.get("expires"):
        date_of(exception["expires"], "expires", number)
    return dict(exception, aspect=aspect)


def read(path=FILE):
    """Every exception of the file, each checked; none when the file is not there."""
    path = pathlib.Path(path)
    if not path.is_file():
        return []
    written = json.loads(path.read_text()).get("exceptions", [])
    return [checked(exception, number) for number, exception in enumerate(written, 1)]


def in_force(exception, today):
    return not exception.get("expires") or datetime.date.fromisoformat(exception["expires"]) >= today


def covers(exception, place, prim, aspect):
    """True when the exception names this place, this prim (or a pattern it matches) and this aspect."""
    return (exception["place"] in ("*", place) and exception["aspect"] in ("both", aspect)
            and (exception["prim"] == prim or fnmatch.fnmatchcase(prim, exception["prim"])))


def matching(exceptions, place, prim, aspect, today):
    """The first exception in force covering the prim's aspect, or None."""
    return next((exception for exception in exceptions
                 if in_force(exception, today) and covers(exception, place, prim, aspect)), None)
