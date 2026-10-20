"""Concept review (CONTEXT.md "concept review"): the creator's draws of one place's concept outside any batch, each
one direct Nano Banana Pro call that his click paid for, and his pick that locks the concept for the design.

The store keeps them; in the framework's store an agent's process cannot write them (`recorded`: the store's own
barrier for its owner areas, applied here, so score/store, which most stages' keys read, stays as it is):

    concepts/<place>/draws/<time>.json   {place, sha, name, at, by, euros, yes, base, marks, note, wording, picks}
    concepts/<place>/picks/<time>.json   {place, sha (None: unlocked again), by, at}
    concepts/<place>/wordings/<time>.json {place, wording (None: back to the generated), by, at}
    blobs/<sha>                          the drawn picture (PNG)

Every draw is also copied off this PC as soon as it is made (`kept_offsite`: the cloud backend's object store, the
private bucket, content-addressed), so a disk loss never loses a paid draw (2026-10-19 lost all of them):

    concept-draws/<sha>.png              the picture, put once
    concept-draws/<sha>.json             its draw record

A draw whose copy failed is kept here all the same; its record names why (`offsite_refused`) and its answer says so.
A pick hands the place's concept to the creator's library through score_lib's own command (`handed_over`: `score-lib
concept`, which locks the picked draw as `concept/<place>` and withdraws it on an unlock), so no work folder holds
the only copy of a locked concept (CONTEXT.md "concept").

A draw runs as a process of its own, inside the owner's yes for exactly that call (score.review.web.concept_draw, node
`override`, key `concept-<place>-<time>`, at the price his button showed), started by the cockpit's owner process:

    SCORE_SPEND_TICKET="override <key>" python -m score.review.concepts <place> <request.json> <by>

`request.json` is {marks: [{x, y, w, h, note}] (shares of the picture, 0 to 1), note, base (the sha of the draw it
redraws, None for a first draw), wording (a first draw's: the creator's edit of the wording his page showed; absent:
the place's wording now)}. A first draw sent with his edited wording sends exactly it (his note after it) and keeps it
as the place's own wording (`wordings/`, in his process only) from then on, for every first draw and Draw all and for
which draw counts as current, until he takes it back to the generated one (`worded` with None; owner, 2026-10-20).
A redraw sends the base twice: once with the marked areas boxed and numbered, once
clean. A first draw is worded by one rule for every place at every layer (`generated`; the owner, 2026-10-20): its
look (data/definitions/place.json, no measures), the creator's says (data/places/concept_inputs.json), its own doors
and openings from its plan's leads and that it has no others, its size against the places beside it in relative
words, the places listed inside it (data/places/within.json) and how they join, the place it sits within as context,
the pictures sent with it named in order, the fixed viewpoint and the environment's style
(data/definitions/concept_views.json `style`). A place within another is sent that one's picked concept first, and
cannot be drawn while it is not picked (`waits`); then the picked concept of each place beside it that it opens into,
so their shared door matches; then its references (the owner's, kept in the private bucket's references/, never the
public repository; read from the local copy under {home}/references; a draw whose reference is not here waits). A
draw's record keeps the picks it was sent (`picks`), so a new pick of one puts it out of date (`current_draw`). A draw's
price is the measured Nano Banana Pro picture (data/costs/per-unit.json, stage closeup) at the standard tier: a draw
is one direct call, not a batch call.
"""
import base64
import datetime
import hashlib
import io
import json
import re
import math
import pathlib
import shlex
import subprocess
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
LONGEST_WORDING = 8000  # characters of a creator's own wording
MARK_WIDTH = 6
OFFSITE = "concept-draws"  # the bucket's prefix a draw is copied under
LIBRARY_SECONDS = 300  # the library's concept command, its lock wait included
LIBRARY_LOCK_WAIT = 120  # how long a pick waits for another handover to let go of the library


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


def inventory_read(place, folder=DATA / "inventory"):
    """{concept, rows} of the place's scene inventory file (CONTEXT.md "scene inventory"), None with none: the sha of
    the concept draw it was read from (its `concept_pick.sha256`; None when it names none) and its rows as [{name,
    count}]. It counts only while `concept` is the place's picked draw: none counts while its concept is not
    locked, and one from an older concept, or naming none, never does (the owner, 2026-10-20)."""
    path = pathlib.Path(folder) / f"{place}.json"
    if not path.is_file():
        return None
    found = json.loads(path.read_text())
    return {"concept": (found.get("concept_pick") or {}).get("sha256"),
            "rows": [{"name": row.get("name") or row["id"], "count": row.get("count", 1)}
                     for row in found.get("rows", [])]}


def undrawn(store, nodes):
    """The Environment's Draw all (owner, 2026-10-20): ([node] of `nodes`, none picked, with no first draw from its
    current wording yet, whose first draw can be made now, {node: why not} for the others with none): layer by layer,
    a place within another waits for that one's pick, so it is drawn on it (CONTEXT.md "concept")."""
    ready, waiting = [], {}
    for node in nodes:
        if picked(store, node):
            continue
        if why := waits(store, node):
            waiting[node] = why
        elif not current_draw(store, node, wording_now(store, node)):
            ready.append(node)
    return ready, waiting


def current_draw(store, place, wording):
    """Whether `place` has a first draw made from `wording`, its current first-draw wording (wording_now: the
    creator's own when set), on the picks it is sent now (the layer above's and its joined places'); a draw from an
    older wording or pick (its data, the draw rules, his wording or one of those picks changed since) does not count,
    so Draw all draws it again."""
    sent = sent_picks(store, place)
    return any(draw.get("base") in (None, "None") and str(draw.get("wording", "")).startswith(wording)
               and (draw.get("picks") or {}) == sent for draw in draws(store, place))


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


def handed_over(store, place, run=subprocess.run):
    """Hand the place's standing pick to the creator's library with its own command (`score-lib concept`: the picked
    draw locked as concept/<place>, or withdrawn on an unlock); what it did, in words. Never raises: the pick stands
    in the store whatever the library answers, and the words say what did not happen."""
    from score.stages.library import backend
    values = backend.settings()
    if backend.kind(values) == backend.NONE:
        return "not in the library: no library is set (SCORE_LIB_ROOT)"
    world = json.loads((DATA / "definitions/world.json").read_text())["name"]
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    words = [*shlex.split(values.get("SCORE_LIB_COMMAND") or backend.DEFAULT_COMMAND), "--root",
             values["SCORE_LIB_ROOT"], "concept", "--world", world, "--place", place, "--commit", commit, "--store",
             str(store.objects.root)]
    try:
        env = {**backend.command_environment(values, store.objects.root, REPO),
               "SCORE_LIB_LOCK_WAIT": str(LIBRARY_LOCK_WAIT)}
        done = run(words, env=env, cwd=values["SCORE_LIB_ROOT"], capture_output=True, text=True,
                   timeout=LIBRARY_SECONDS)
    except (OSError, subprocess.TimeoutExpired, RuntimeError, SystemExit) as failed:
        return f"not in the library: {str(failed)[:300]}"
    lines = (done.stdout or "").strip().splitlines()
    if done.returncode != 0 or not lines:
        said = ((done.stderr or done.stdout or "").strip().splitlines() or [f"exit {done.returncode}"])[-1]
        return f"not in the library: {said[:300]}"
    report = json.loads(lines[-1])
    saved = report.get("saved") or {"pushed": True}
    pushed = "" if saved.get("pushed") else f" (not pushed: {saved.get('why') or 'unknown'})"
    return f"library: {report['did']} {report.get('address') or ''}".rstrip() + pushed


def recorded(store, key, record):
    """Write a draw's or a pick's record once; PermissionError in an agent's process on the framework's store."""
    if store.is_framework_store() and running_under_agent():
        raise PermissionError(f"{key}: only the owner draws or picks a concept, from his own cockpit; an agent's "
                              "process cannot write it")
    store.write_once(key, record)


# --- the wording ----------------------------------------------------------------------------------------------
# One rule for every place at every layer (the owner, 2026-10-20: "just feed down the concept of the layer above"):
# its own look and the creator's says, the places listed inside it and how they join, the place it sits within as
# context, the pictures sent with it named in order (the layer above's picked concept first, then its references),
# the fixed viewpoint and the environment's style. No measures but the creator's own says: the drawing finds the shape.

OUTSIDE_VIEW = ("Viewpoint: a high three-quarter view from one corner, looking down about 35 to 45 degrees, so its "
                "footprint, its roofs and two of its sides show; the whole place in frame with a small margin, its "
                "surroundings only at the edges; a long lens with little perspective distortion, so sizes compare "
                "honestly; clear, readable light within the place's own mood.")
INSIDE_VIEW = ("Viewpoint: a cutaway, the roof and the near walls removed, seen from a high three-quarter view from one "
               "corner looking down about 35 to 45 degrees, so the whole floor and every remaining wall can be read; "
               "a long lens with little perspective distortion; clear, readable light within the place's own mood.")
EVERY_DRAW = "One picture, 16:9, no text and no labels; people in view for scale."
ROOF_KEPT = (" Its roof features as the picture of the place it sits within shows them (openings, domes, glazing) stay "
             "visible along the cutaway's edges.")


def resolved(path):
    """A data path with its {home} (the prop tools' home: the private references' local copy is its references/),
    {seeds} and {data} filled in."""
    filled = path.replace("{home}", str(PROPS_HOME)).replace("{seeds}", str(PROPS_HOME / "work"))
    return pathlib.Path(filled.replace("{data}", str(DATA)))


def look_of(place):
    """The look in place.json a place takes: one whose `scenes` lists it, else `prologue_<place>`, else `<place>`."""
    looks = json.loads((DATA / "definitions/place.json").read_text())
    for look in looks.values():
        if isinstance(look, dict) and place in (look.get("scenes") or []):
            return look
    return next((looks[name] for name in (f"prologue_{place}", place) if isinstance(looks.get(name), dict)), None)


def plan_of(place):
    """A place's plan (data/plans/<place>.json), {} when it has none."""
    plan_path = DATA / "plans" / f"{place}.json"
    return json.loads(plan_path.read_text()) if plan_path.is_file() else {}


def inputs_of(place):
    """{says, references} the creator gave `place`'s draw (data/places/concept_inputs.json), {} when none."""
    return json.loads((DATA / "places/concept_inputs.json").read_text())["places"].get(place, {})


def style():
    """The environment's one style wording (data/definitions/concept_views.json `style`, the owner's), every
    place's draw shares, as a sentence; empty when none is set."""
    found = json.loads((DATA / "definitions/concept_views.json").read_text()).get("style", "").strip()
    return f"The whole environment's style: {found}" if found else ""


def tree():
    """data/places/within.json: {within: {place: what holds it}, shells: {shell: its short name}}."""
    found = json.loads((DATA / "places/within.json").read_text())
    return {"within": {name: entry["within"] for name, entry in found["within"].items()},
            "shells": {name: entry["name"] for name, entry in found["shells"].items()}}


def above(place):
    """The place or shell `place` sits within, None for an outside place of its own."""
    return tree()["within"].get(place)


def inside_of(place):
    """The inside places the creator listed directly under `place`, in within.json's order."""
    return [name for name, holder in tree()["within"].items() if holder == place]


def name_of(place):
    """A place's name as its look gives it, else "the <place>"."""
    return (look_of(place) or {}).get("name") or f"the {place}"


def no_sizes(words):
    """`words` with every measure in metres taken out ("27 x 55 m", "at 9 m", "15 m"), and a bracket left empty by
    it: the drawing finds the shape (the owner, 2026-10-20)."""
    words = re.sub(r",? ?(at |about )?\d+(\.\d+)?( ?x ?\d+(\.\d+)?)? ?m\b", "", words)
    return re.sub(r" ?\(\s*[,;:]?\s*\)", "", words).strip()


def look_text(place):
    """The words of `place`'s look (place.json `style.text`), no measures; "" when it has none."""
    return no_sizes(((look_of(place) or {}).get("style") or {}).get("text") or "")


def own_words(place):
    """[sentence] of `place` itself: its look and the creator's says (as he set them)."""
    look = look_text(place)
    return [part for part in (f"Its look: {look}" if look else "", inputs_of(place).get("says", "")) if part]


def door_label(plan, side):
    """The plan's own label of the door a lead names (`N`, `90`, `W@9`: the side, at a height), lower case."""
    face, _, level = side.partition("@")
    for door in plan.get("doors", []):
        if str(door[0]) == face and (not level or door[-1] == float(level)):
            label = [part for part in door if isinstance(part, str)][-1].lower()
            return no_sizes(label)
    return f"{face} door"


def joins_of(place, inside):
    """How `place`'s open leads join it (its plan's `leads`): [(the other inside place or None, the words)]. A lead
    onto a walkway tube joins the place it names in `joins`, else the other inside place its `why` names first."""
    plan, found = plan_of(place), []
    for side, lead in plan.get("leads", {}).items():
        target, why = lead.get("to"), lead.get("why", "")
        if target == "sealed":
            continue
        if target == "tube":
            named = [name for name in inside if name not in (place, target) and name in why]
            other = lead.get("joins") or min(named, key=why.find, default=None)
            found.append((other, f"a walkway tube to the {other}" if other else "a walkway tube"))
        elif target in inside:
            found.append((target, f"opens straight into the {target}"))
        else:
            found.append((None, f"its {door_label(plan, side)} opens onto the {target}"))
    return found


def holding_words(place):
    """The places the creator listed inside `place` (within.json), each by its name and says, and how they join;
    "" when it lists none."""
    inside = inside_of(place)
    if not inside:
        return ""
    parts = [name_of(name) + (f" ({says.rstrip('.')})" if (says := inputs_of(name).get("says")) else "")
             for name in inside]
    joins, said = [], set()
    for name in inside:
        for other, words in joins_of(name, inside):
            pair = frozenset((name, other)) if other else (name, words)
            if pair not in said:
                said.add(pair)
                joins.append(f"the {name}: {words}")
    joined = f" They join as laid out: {'; '.join(joins)}." if joins else ""
    return f"Inside it, each its own part, recognisable as what it is: {'; '.join(parts)}.{joined}"


def context_words(place):
    """Where `place` sits: the layer above's name and the first sentence of its says, else of its look, short; ""
    for an outside place."""
    holder = above(place)
    if not holder:
        return ""
    first = (inputs_of(holder).get("says") or look_text(holder)).split(". ")[0].rstrip(".")
    return f"This place sits within {name_of(holder)}" + (f": {first}." if first else ".")


def unbracketed(words):
    """`words` without its brackets (the plans' file and node notes) and measures, from its first comma."""
    return no_sizes(re.sub(r" ?\([^)]*\)", "", words)).strip()


def opening_words(place, side, lead):
    """One lead of `place`'s plan in relational words: its door by its plan's label, and what it opens onto (a
    place by its name, the outside or a tube with its `why`, so a facing the data names is said), or kept shut."""
    plan, target = plan_of(place), lead.get("to")
    label = re.split(r",(?![^(]*\))", door_label(plan, side))[0]
    why = unbracketed(lead.get("why", ""))
    if target == "sealed":
        return f"its {label}, kept shut"
    if target in ("outside", "tube"):
        return f"its {label} opens onto the {target}" + (f": {why}" if why else "")
    return f"its {label} opens into {name_of(target)}"


def openings_words(place):
    """Every door and opening `place`'s plan leads through, and that it has no others; "" when its plan has none."""
    leads = plan_of(place).get("leads") or {}
    if not leads:
        return ""
    said = "; ".join(opening_words(place, side, lead) for side, lead in leads.items())
    return f"Its doors and openings, as laid out: {said}. No other doors, balconies or openings than these."


PERSON = 1.8  # a person's height in metres, the yardstick of the relative height words
TIMES = {2: "twice", 3: "three times", 4: "four times", 5: "five times", 6: "six times", 7: "seven times",
         8: "eight times", 9: "nine times", 10: "ten times"}


def floor_and_walls(place):
    """(floor area, wall height) of `place` from its plan's `w`, `d` and the tallest measure its `height` words name
    (a "27 x 55 m" opening's second side left out), or None when its plan gives no floor."""
    plan = plan_of(place)
    if not (plan.get("w") and plan.get("d")):
        return None
    heights = [float(found) for found in
               re.findall(r"(?<![\d.])(?<!x )(\d+(?:\.\d+)?) ?m\b", str(plan.get("height", "")))]
    return plan["w"] * plan["d"], max(heights, default=None)


def size_words(place):
    """How big `place` is against the places beside it under the same layer above, in relative words only (ranked by
    its plan's floor area, its walls against a person's height); "" when its plan gives no floor."""
    holder, own = above(place), floor_and_walls(place)
    if not holder or own is None:
        return ""
    others = sorted(found[0] for name in inside_of(holder) if name != place and (found := floor_and_walls(name)))
    words = []
    if others and own[0] > others[-1]:
        ratio = round(own[0] / others[-1])
        words.append(f"the largest place in {name_of(holder)}, its floor "
                     + (f"about {TIMES.get(ratio, 'many times')} any other's" if ratio >= 2 else "larger than any other's"))
    elif others and own[0] < others[0]:
        words.append(f"the smallest place in {name_of(holder)}")
    elif others:
        larger = own[0] >= others[len(others) // 2]
        words.append(f"one of the {'larger' if larger else 'smaller'} places in {name_of(holder)}")
    if own[1]:
        tall = own[1] / PERSON
        words.append("its walls several times a person's height; people are tiny inside it" if tall >= 4 else
                     "its walls about twice a person's height" if tall >= 2 else "its ceiling a little above a person's head")
    return f"Its size: {', '.join(words)}." if words else ""


def joined(place):
    """The places beside `place` under the same layer above that its plan's leads open into (a tube's `joins` too)."""
    holder, found = above(place), []
    for lead in (plan_of(place).get("leads") or {}).values():
        for other in (lead.get("to"), lead.get("joins")):
            if other and other != place and other not in found and holder and above(other) == holder:
                found.append(other)
    return found


def sent_picks(store, place):
    """{place: sha} of the picked concepts a first draw of `place` sends: the layer above's, then each joined
    place's that is picked."""
    return {other: sha for other in [above(place), *joined(place)] if other and (sha := picked(store, other))}


def sent_pictures(store, place):
    """[(what it is, its source)] a first draw of `place` sends, in order: the layer above's picked concept (source:
    that place's name) when it sits within one, each joined place's picked concept, then the creator's references
    (their paths)."""
    holder = above(place)
    found = [(f"the picked concept of {name_of(holder)} this place sits within: this place is {name_of(place)} as "
              "it stands there, and its outer shape, size against the others, roof, windows and doors must match it",
              holder)] if holder else []
    found += [(f"the picked concept of {name_of(other)}, which this place opens into: the door they share must match "
               "it", other) for other in joined(place) if picked(store, other)]
    return found + [(f"a reference for {ref['shows']}; never its size, layout or viewpoint", resolved(ref["picture"]))
                    for ref in inputs_of(place).get("references", [])]


def indoors(place):
    """Whether `place` is drawn as a cutaway: as its plan says (`inside`), else when it sits within another place
    and is no shell of its own."""
    said = plan_of(place).get("inside")
    return said if said is not None else (above(place) is not None and place not in tree()["shells"])


def generated(store, place):
    """The first-draw wording of `place` by the one rule, every part from data and the picks it is sent."""
    pictures = sent_pictures(store, place)
    listed = "Attached pictures, in order: " + "; ".join(
        f"{number}. {words}" for number, (words, _) in enumerate(pictures, 1)) + "." if pictures else ""
    roof = (ROOF_KEPT if indoors(place) and above(place) else "")
    return " ".join(part for part in (
        f"One concept painting of {name_of(place)}.", *own_words(place), openings_words(place), size_words(place),
        holding_words(place), context_words(place), listed,
        f"{INSIDE_VIEW if indoors(place) else OUTSIDE_VIEW}{roof} {EVERY_DRAW}", style()) if part)


def waits(store, place):
    """Why a first draw of `place` cannot be made now (its layer above not picked, a reference not on this
    machine), or None."""
    holder = above(place)
    if holder and not picked(store, holder):
        return f"waits for {holder}'s concept to be picked"
    missing = [ref["picture"] for ref in inputs_of(place).get("references", [])
               if not resolved(ref["picture"]).is_file()]
    if missing:
        return (f"its reference {missing[0]} is not on this machine (the private bucket's references/, copied to "
                f"{PROPS_HOME / 'references'})")
    return None


def own_wording(store, place):
    """The creator's own first-draw wording of `place`, or None while it is the generated one."""
    found = records(store, place, "wordings")
    return found[-1]["wording"] if found else None


def wording_now(store, place):
    """The wording the next first draw of `place` sends: the creator's own when he set one, else the generated."""
    return own_wording(store, place) or generated(store, place)


def worded(store, place, wording, by):
    """Keep `wording` as `place`'s own first-draw wording from now on (None: back to the generated); the record.
    PermissionError in an agent's process on the framework's store."""
    record = {"place": place, "wording": wording, "by": by, "at": now()}
    recorded(store, f"{AREA}/{place}/wordings/{stamp_key(record['at'])}.json", record)
    return record


def checked_wording(wording):
    """A request's wording stripped, None when it gives none; Refused past LONGEST_WORDING."""
    found = str(wording or "").strip()
    if len(found) > LONGEST_WORDING:
        raise Refused(f"the wording is {len(found)} characters; at most {LONGEST_WORDING}")
    return found or None


def kept_as_own(store, place, request, by):
    """A first draw sent with an edited wording keeps it as the place's own (none again once it is the generated)."""
    asked = checked_wording(request.get("wording"))
    if request.get("base") or asked is None:
        return
    own = None if asked == generated(store, place) else asked
    if own != own_wording(store, place):
        worded(store, place, own, by)


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
    if why := waits(store, place):
        raise Refused(f"{place} {why}")
    sent = checked_wording(request.get("wording")) or wording_now(store, place)
    pictures = [Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{picked(store, source)}")))
                if isinstance(source, str) else Image.open(source) for _, source in sent_pictures(store, place)]
    return with_note(sent, note), pictures


def redraw_preview():
    """What Redraw with notes sends, its notes as placeholders (the concept review page shows it)."""
    return redraw_wording([{"note": "<mark 1's note>"}, {"note": "<mark 2's note>"}], "<your note>")


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


def offsite_store():
    """The private bucket: the cloud backend's object store, its key from the secret store."""
    import submit  # tools/cloud/runtime, on the path through score.store
    return submit.cloud_store()


def copied_offsite(png, record, offsite):
    """Copy one draw's picture (once) and its record into `offsite` under OFFSITE/<sha>; the picture's key."""
    key = f"{OFFSITE}/{record['sha']}.png"
    if not offsite.exists(key):
        offsite.write_bytes(key, png)
    offsite.write_bytes(f"{OFFSITE}/{record['sha']}.json", json.dumps(record, indent=1).encode())
    return key


def kept_offsite(png, record, offsite=None):
    """The record with where its draw was copied off this PC (`offsite`), or why it was not (`offsite_refused`)."""
    try:
        return {**record, "offsite": copied_offsite(png, record, offsite or offsite_store())}
    except Exception as failed:  # any failure of the copy: the paid draw stays kept here and its record says why
        return {**record, "offsite": None, "offsite_refused": f"{type(failed).__name__}: {str(failed)[:300]}"}


def draw(store, place, request, by, caller=call, offsite=None):
    """One draw of `place`'s concept inside the owner's yes (SCORE_SPEND_TICKET names it; compute.require_cleared
    refuses otherwise, and while the month's books are unknown); its record, copied off this PC first (`offsite`: a
    store with the bucket's calls, None the bucket). `caller(wording, pictures)` makes the picture's PNG bytes."""
    from score.adapters import compute
    yes = compute.require_cleared("a concept draw", store)
    wording, pictures = request_parts(store, place, request)
    kept_as_own(store, place, request, by)  # before the call: a refused call still keeps his edit
    png = caller(wording, pictures)
    sha = kept(store, png)
    record = {"place": place, "sha": sha, "name": f"{place}-concept.png", "at": now(), "by": by,
              "euros": yes["euros"], "yes": yes["key"], "base": request.get("base") or None,
              "marks": checked_marks(request.get("marks")), "note": str(request.get("note", "")), "wording": wording,
              "picks": None if request.get("base") else sent_picks(store, place)}
    record = kept_offsite(png, record, offsite)
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
