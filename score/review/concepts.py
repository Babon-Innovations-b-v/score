"""Concept review (CONTEXT.md "concept review"): the creator's draws of one place's concept outside any batch, each
one direct Nano Banana Pro call that his click paid for, and his pick that locks the concept for the design.

The store keeps them; in the framework's store an agent's process cannot write them (`recorded`: the store's own
barrier for its owner areas, applied here, so score/store, which most stages' keys read, stays as it is):

    concepts/<place>/draws/<time>.json   {place, sha, name, at, by, euros, yes, base, marks, note, wording}
    concepts/<place>/picks/<time>.json   {place, sha (None: unlocked again), by, at}
    blobs/<sha>                          the drawn picture (PNG)

A draw runs as a process of its own, inside the owner's yes for exactly that call (score.review.web.concept_draw, node
`override`, key `concept-<place>-<time>`, at the price his button showed), started by the cockpit's owner process:

    SCORE_SPEND_TICKET="override <key>" python -m score.review.concepts <place> <request.json> <by>

`request.json` is {marks: [{x, y, w, h, note}] (shares of the picture, 0 to 1), note, base (the sha of the draw it
redraws, None for a first draw)}. A redraw sends the base twice: once with the marked areas boxed and numbered, once
clean. A first draw (no concept yet: all of environment 1's were lost) is worded from the place's data the way the
concept-views row words its views: its view in data/definitions/concept_views.json when it has one (the newest), else
its look (data/definitions/place.json) and its plan's size and elements, with the environment's one style wording
(concept_views.json `style`, the owner's) after it; a view's reference picture (the owner's, kept in the private
bucket's references/, never the public repository; read from its local copy under {home}/references) goes with it,
and a draw whose reference is not on this machine is refused. A draw's price is the measured Nano Banana Pro picture (data/costs/per-unit.json, stage closeup)
at the standard tier: a draw is one direct call, not a batch call.
"""
import base64
import datetime
import hashlib
import io
import json
import math
import pathlib
import sys
import urllib.error

from score.store import PROPS_HOME, running_under_agent, stamp_key

REPO = pathlib.Path(__file__).resolve().parents[2]
DATA = REPO / "data"
AREA = "concepts"
MEASURED_STAGE = "closeup"  # the stage whose measured unit is one Nano Banana Pro picture
CALLER = "concept-review"
TIMEOUT = 400
LONGEST_SENT = 1600
MARK_WIDTH = 6


class Refused(ValueError):
    """A draw or pick that cannot be made as asked."""


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


def tools():
    """pro.py (the model, its picture parts and answers), google_spend (the call, on the Google ledger) and the
    secret reader, imported with the prop tools' folders on the path."""
    folders, kept = REPO / "tools/props", list(sys.path)
    sys.path[:0] = [str(folders / "closeup"), str(folders / "cloud")]
    try:
        import google_spend
        import pro
        import secret_store
    finally:
        sys.path[:] = kept
    return pro, google_spend, secret_store


def draw_euros(per_unit=DATA / "costs/per-unit.json"):
    """The euros of one draw: the measured Nano Banana Pro picture's high at the standard tier (measured calls billed
    at the batch tier are divided by its share), rounded up to the cent; None while it is not measured."""
    stage = json.loads(pathlib.Path(per_unit).read_text())["stages"].get(MEASURED_STAGE) or {}
    high = stage.get("high_euros")
    if high is None:
        return None
    _, google_spend, _ = tools()
    share = google_spend.TIER_PRICE["batch"] if "batch" in stage.get("basis", "") else 1.0
    return math.ceil(round(high / share * 100, 6)) / 100


def yes_key(place, at):
    """The owner's spend yes key for one draw of `place` asked at `at`."""
    return f"concept-{place}-{stamp_key(at)}"


def records(store, place, kind):
    """The records of one place's `kind` (draws or picks), oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{place}/{kind}/"))]


def draws(store, place):
    return records(store, place, "draws")


def picked(store, place):
    """The sha of the draw picked for `place`, or None while none is (never picked, or unlocked again)."""
    found = records(store, place, "picks")
    return found[-1]["sha"] if found else None


def placed(store):
    """The places with a draw or a pick in the store."""
    return sorted({key.split("/")[1] for key in store.objects.keys(f"{AREA}/")})


def pick(store, place, sha, by):
    """Lock `place`'s concept on its draw `sha` (None: unlock it); the record. Refused for a sha that is no draw of
    the place."""
    if sha is not None and sha not in {draw["sha"] for draw in draws(store, place)}:
        raise Refused(f"{sha[:12]} is no draw of {place}")
    record = {"place": place, "sha": sha, "by": by, "at": now()}
    recorded(store, f"{AREA}/{place}/picks/{stamp_key(record['at'])}.json", record)
    return record


def recorded(store, key, record):
    """Write a draw's or a pick's record once; PermissionError in an agent's process on the framework's store."""
    if store.is_framework_store() and running_under_agent():
        raise PermissionError(f"{key}: only the owner draws or picks a concept, from his own cockpit; an agent's "
                              "process cannot write it")
    store.write_once(key, record)


# --- the wording ----------------------------------------------------------------------------------------------

def resolved(path):
    """A data path with its {home} (the prop tools' home: the private references' local copy is its references/),
    {seeds} and {data} filled in."""
    filled = path.replace("{home}", str(PROPS_HOME)).replace("{seeds}", str(PROPS_HOME / "work"))
    return pathlib.Path(filled.replace("{data}", str(DATA)))


def view_of(place):
    """The newest concept view requested for `place` (data/definitions/concept_views.json), or None."""
    views = json.loads((DATA / "definitions/concept_views.json").read_text())["views"]
    found = [view for view in views if view["id"].split("_", 1)[-1] == place]
    return found[-1] if found else None


def look_of(place):
    """The look in place.json a place takes: one whose `scenes` lists it, else `prologue_<place>`, else `<place>`."""
    looks = json.loads((DATA / "definitions/place.json").read_text())
    for look in looks.values():
        if isinstance(look, dict) and place in (look.get("scenes") or []):
            return look
    return next((looks[name] for name in (f"prologue_{place}", place) if isinstance(looks.get(name), dict)), None)


def from_data(place):
    """A first draw's wording from the place's look and plan."""
    plan_path = DATA / "plans" / f"{place}.json"
    plan = json.loads(plan_path.read_text()) if plan_path.is_file() else {}
    look = look_of(place) or {}
    name = look.get("name") or plan.get("title", place).lower()
    words = [f"One concept painting of {name}, a wide landscape view at standing eye height, the whole place in view."]
    if plan.get("w") and plan.get("d"):
        words.append(f"It is about {plan['w']} m by {plan['d']} m" + (f", {plan['height']}." if plan.get("height")
                                                                     else "."))
    if look.get("style", {}).get("text"):
        words.append(f"Its look: {look['style']['text']}")
    elements = [element["element"] for element in plan.get("elements", []) if element.get("element")]
    if elements:
        words.append(f"It holds: {'; '.join(elements)}.")
    words.append("No people, no text, no labels.")
    return " ".join(words)


def style():
    """The environment's one style wording (data/definitions/concept_views.json `style`, the owner's), every
    place's draw shares, as a sentence; empty when none is set."""
    found = json.loads((DATA / "definitions/concept_views.json").read_text()).get("style", "").strip()
    return f"The whole environment's style: {found}" if found else ""


def floor_wording(place, floor):
    """A shell's first draw from its floor plan (data/definitions/<shell>_floor.json; the owner, 2026-10-20): its
    whole outside at its true length, large enough for every room it holds, people and a vehicle beside it for scale;
    its own views' reference (concept_views.json ids `<shell>_...`) for its look only, never its size: (wording,
    that view or None)."""
    plan = json.loads(floor.read_text())
    rooms = [room["name"] for room in plan.get("rooms", [])]
    words = [f"One concept painting of the whole {place} seen from outside, standing on the ground, a wide landscape "
             f"view. It is {plan['length']:g} m long: large enough to hold, on one deck inside, {', '.join(rooms)}, "
             "and a walkway joining them. Show its true size: people and a vehicle on the ground beside it, small "
             "against it."]
    views = json.loads((DATA / "definitions/concept_views.json").read_text())["views"]
    own = [view for view in views if view["id"].startswith(f"{place}_")]
    if own:
        words.append("The attached picture gives its look only (its shape language, materials and landing legs), "
                     "never its size or proportions: it shows a much smaller ship.")
    return " ".join(words), (own[-1] if own else None)


def first_wording(place):
    """(wording, reference path or None) of a first draw: the place's own description (its view's, a shell's floor
    plan's, else its data's) with the environment's style; Refused when its reference is not on this machine."""
    view, floor = view_of(place), DATA / "definitions" / f"{place}_floor.json"
    if view is None and floor.is_file():
        wording, view = floor_wording(place, floor)
    else:
        wording = view["wording"] if view else from_data(place)
    if view is None:
        return " ".join(part for part in (wording, style()) if part), None
    reference = resolved(view["reference"])
    if not reference.is_file():
        raise Refused(f"its reference {view['reference']} is not on this machine (the private bucket's references/, "
                      f"copied to {PROPS_HOME / 'references'})")
    return " ".join(part for part in (wording, style()) if part), reference


def redraw_wording(marks, note):
    """A redraw's wording: what to change in each numbered box, and overall."""
    words = ["Image 1 is a concept painting with numbered red boxes marking areas to change; image 2 is the same "
             "painting without them. Paint image 2 again as one whole concept painting, the same view, style, light "
             "and everything not named here unchanged."]
    words += [f"Box {number}: {mark['note'].strip()}." for number, mark in enumerate(marks, 1)
              if mark["note"].strip()]
    if note.strip():
        words.append(f"Overall: {note.strip()}")
    words.append("Draw no boxes, numbers, text or labels.")
    return " ".join(words)


def with_note(wording, note):
    return f"{wording} The creator's note: {note.strip()}" if note.strip() else wording


def boxed(picture, marks):
    """A copy of `picture` with each mark drawn as a numbered red box."""
    from PIL import ImageDraw
    copy = picture.convert("RGB")
    pen = ImageDraw.Draw(copy)
    wide, tall = copy.size
    for number, mark in enumerate(marks, 1):
        left, top = mark["x"] * wide, mark["y"] * tall
        box = (left, top, left + mark["w"] * wide, top + mark["h"] * tall)
        pen.rectangle(box, outline=(255, 0, 0), width=MARK_WIDTH)
        pen.text((box[0] + 2 * MARK_WIDTH, box[1] + 2 * MARK_WIDTH), str(number), fill=(255, 0, 0),
                 font_size=max(24, tall // 20))
    return copy


def checked_marks(marks):
    """The marks as given, each a box inside the picture with its note; Refused otherwise."""
    found = []
    for mark in marks or []:
        try:
            box = [float(mark[name]) for name in ("x", "y", "w", "h")]
        except (KeyError, TypeError, ValueError) as broken:
            raise Refused(f"a marked area is not a box: {mark!r}") from broken
        if not (0 <= box[0] < 1 and 0 <= box[1] < 1 and 0 < box[2] <= 1.000001 - box[0]
                and 0 < box[3] <= 1.000001 - box[1]):
            raise Refused(f"a marked area lies outside the picture: {box}")
        found.append({"x": box[0], "y": box[1], "w": box[2], "h": box[3], "note": str(mark.get("note", ""))[:500]})
    return found


# --- the draw ---------------------------------------------------------------------------------------------------

def request_parts(store, place, request):
    """(wording, [PIL pictures]) a draw sends: a redraw's boxed and clean base, else the first draw's wording with
    its reference where one is on disk."""
    from PIL import Image
    marks, note = checked_marks(request.get("marks")), str(request.get("note", ""))
    base = request.get("base")
    if base:
        if base not in {draw["sha"] for draw in draws(store, place)}:
            raise Refused(f"{base[:12]} is no draw of {place}")
        picture = Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{base}")))
        return redraw_wording(marks, note), [boxed(picture, marks), picture]
    if marks:
        raise Refused("a first draw has no picture to mark")
    wording, reference = first_wording(place)
    return with_note(wording, note), [Image.open(reference)] if reference else []


def call(wording, pictures):
    """One Nano Banana Pro call (google_spend, on its ledger, never cached: each click is its own draw); the PNG bytes
    of the picture it answered, or Refused."""
    from PIL import Image
    pro, google_spend, secret_store = tools()
    body = {"contents": [{"role": "user", "parts": [{"text": wording}]
                          + [pro.part(picture, LONGEST_SENT) for picture in pictures]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"imageSize": "2K"}}}
    try:
        found = pro.pictures_in(google_spend.generate(pro.MODEL, body, secret_store.secret(pro.KEY_SECRET),
                                                      TIMEOUT, caller=CALLER))
    except urllib.error.HTTPError as error:
        raise Refused(f"the model refused ({error.code})") from error
    if not found:
        raise Refused("the model answered with no picture")
    buffer = io.BytesIO()
    Image.open(io.BytesIO(base64.b64decode(found[-1]))).convert("RGB").save(buffer, "PNG")
    return buffer.getvalue()


def kept(store, png):
    """The picture into the store's blobs; its sha."""
    sha = hashlib.sha256(png).hexdigest()
    folder = store.cache / AREA
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha}.png"
    path.write_bytes(png)
    store.put_blob(path, sha)
    path.unlink()
    return sha


def draw(store, place, request, by, caller=call):
    """One draw of `place`'s concept inside the owner's yes (SCORE_SPEND_TICKET names it; compute.require_cleared
    refuses otherwise, and while the month's books are unknown); its record. `caller(wording, pictures)` makes the
    picture's PNG bytes."""
    from score.adapters import compute
    yes = compute.require_cleared("a concept draw", store)
    wording, pictures = request_parts(store, place, request)
    sha = kept(store, caller(wording, pictures))
    record = {"place": place, "sha": sha, "name": f"{place}-concept.png", "at": now(), "by": by,
              "euros": yes["euros"], "yes": yes["key"], "base": request.get("base") or None,
              "marks": checked_marks(request.get("marks")), "note": str(request.get("note", "")), "wording": wording}
    recorded(store, f"{AREA}/{place}/draws/{stamp_key(record['at'])}.json", record)
    return record


def main(argv):
    """`<place> <request.json> <by>`: one draw in the store its yes is in (SCORE_SPEND_STORE, else the framework's);
    its record as one JSON line, or the refusal on stderr with exit 1."""
    import os
    from score.adapters.compute import STORE, Refused as NotCleared
    from score.store import Store
    place, request, by = argv
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    try:
        record = draw(store, place, json.loads(pathlib.Path(request).read_text()), by)
    except (Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
