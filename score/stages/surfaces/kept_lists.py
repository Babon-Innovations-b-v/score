"""A take's finish list kept by what it was asked of (#229): its pictures, the question's own wording and the kinds of
thing it may name, never the library's own lists. Claude Code takes no temperature, so a list asked again draws again:
the hand drill listed 2 finishes and 4 parts in r15s and 1 and 1 in r15f, with only the library's lists changed
between them, and every round's library change asked every take again (about 45 s an asset).

A kept answer is stored by name: each finish's surface by its library name, each mark's decal and hardware piece by
its address, never by its code (M1, D1, H1: its place in today's lists). It is read back in today's codes and only
when everything it names is still offered and it fits today's schema; otherwise there is none and the take is asked
again. The folder is a cache on this machine, at most LIMIT answers, the oldest dropped first."""
import hashlib
import json
import os
import pathlib

import finish_ask

FOLDER = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "cloud" / "kept-lists"
LIMIT = 5000  # kept answers, a few kB each


def key(take, body, wording, vocabulary):
    """The hash a take's answer is kept by: the take, `wording` (the question's templates), `vocabulary` (the kinds
    of thing the answer may name: hardware kinds, pattern openings) and the body's pictures, in order."""
    digest = hashlib.sha256(json.dumps({"take": take, "wording": wording, "vocabulary": vocabulary},
                                       sort_keys=True).encode())
    for part in body["contents"][0]["parts"]:
        if "inline_data" in part:
            digest.update(part["inline_data"]["data"].encode())
    return digest.hexdigest()


def renamed(answer, codes, names):
    """`answer` (parsed) with each finish's surface and each mark's decal and hardware moved from `codes` to `names`
    ({"surface"|"decal"|"hardware": [...]} each in the same order); KeyError where one is not offered."""
    moved = json.loads(json.dumps(answer))
    for field, entries in (("surface", moved.get("finishes", [])), ("decal", moved.get("marks") or []),
                           ("hardware", moved.get("marks") or [])):
        lookup = dict(zip(codes[field], names[field]))
        for entry in entries:
            if entry.get(field) is not None:
                entry[field] = lookup[entry[field]]
    return moved


def fits(value, schema, required=True):
    """Whether `value` fits a Gemini responseSchema's types, enums and required fields (a field left null or out where
    it is not required fits)."""
    if value is None:
        return not required
    if "enum" in schema and value not in schema["enum"]:
        return False
    if schema.get("type") == "OBJECT":
        properties, needed = schema.get("properties", {}), set(schema.get("required", []))
        return (isinstance(value, dict) and needed <= set(value)
                and all(name in properties and fits(item, properties[name], name in needed)
                        for name, item in value.items()))
    if schema.get("type") == "ARRAY":
        return isinstance(value, list) and all(fits(item, schema["items"]) for item in value)
    return True


def offered(surfaces, decals, pieces):
    """({field: today's codes}, {field: their names}) for the surfaces, decals and hardware pieces a take is offered."""
    codes = {"surface": finish_ask.surface_codes(surfaces), "decal": finish_ask.decal_codes(decals),
             "hardware": finish_ask.piece_codes(pieces)}
    names = {"surface": list(surfaces), "decal": [decal["address"] for decal in decals],
             "hardware": [piece["address"] for piece in pieces]}
    return codes, names


def read(digest, body, surfaces, decals, pieces):
    """The kept answer's JSON text in today's codes, or None when none is kept or it no longer fits."""
    path = FOLDER / f"{digest}.json"
    if not path.exists():
        return None
    codes, names = offered(surfaces, decals, pieces)
    try:
        answer = renamed(json.loads(path.read_text()), names, codes)
    except (KeyError, json.JSONDecodeError):
        return None
    if not fits(answer, body["generationConfig"]["responseSchema"]):
        return None
    return json.dumps(answer)


def keep(digest, answer, surfaces, decals, pieces):
    """Keep a usable answer's JSON text under `digest`, by name; the oldest dropped past LIMIT."""
    codes, names = offered(surfaces, decals, pieces)
    FOLDER.mkdir(parents=True, exist_ok=True)
    path = FOLDER / f"{digest}.json"
    part = path.with_name(f"{path.name}.{os.getpid()}")
    part.write_text(json.dumps(renamed(json.loads(answer), codes, names)))
    part.replace(path)
    kept = sorted(FOLDER.glob("*.json"), key=lambda found: found.stat().st_mtime)
    for old in kept[:max(len(kept) - LIMIT, 0)]:
        old.unlink(missing_ok=True)
