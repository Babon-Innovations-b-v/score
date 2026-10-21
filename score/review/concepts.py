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
A Redraw with notes is two calls inside one yes (the owner, 2026-10-20; `redraw_euros`, the measured Gemini 3.1 Pro
answer and draw): Gemini (`revise`, direct) gets the base boxed and numbered and clean, each picked concept it was
drawn on that he marked (the layer above's, a joined place's; boxes P1, P2, ...), the prompt the base was drawn from
and every note, and answers the corrected prompt naming each area by where it lies; that prompt becomes the place's
own wording (`corrected` in the record, both calls in `calls`), then one draw sends it with every note and the same
pictures. A first draw is worded by one rule for every place at every layer (`generated`; the owner, 2026-10-20): its
look (data/definitions/place.json, no measures), the creator's says (data/places/concept_inputs.json), its own doors
and openings from its plan's leads and that it has no others, its size against the places beside it in relative
words, the places listed inside it (data/places/within.json) and how they join, the place it sits within as context,
the pictures sent with it named in order, the fixed viewpoint, people only where its data has them (`has_people`) and
the environment's style
(its locked environment concept's, else data/definitions/concept_views.json `style`; its references the same way; a
draw and a pick record the environment concept's version they were made under, one under another is out of date, and
none is made while it is unlocked: score/review/environment_concept.py). A place within another is sent first a crop of that one's picked concept
to the scene inventory row its plan says holds it ("the inside of what this crop shows": the ship for its rooms, the
block for the flat), never the whole scene; the design steps are strict, in one place (`step_refusal`, owner
2026-10-21): it is drawn or picked only once the layer above is picked (the pick is the approval), its inventory read,
its plan made and that row outlined; then the picked concept of each place beside it that it opens into,
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
MEASURED_ASK = "finish-route-list"  # the stage whose measured unit is one Gemini 3.1 Pro answer on pictures
PROMPT_MODEL = "gemini-3.1-pro-preview"  # the model that corrects a prompt from the creator's notes
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


def draw_euros(per_unit=DATA / "costs/per-unit.json", measured=(MEASURED_STAGE,)):
    """The euros of one draw: the measured high of each call it makes (`measured`, stages of per-unit.json) at the
    standard tier (measured calls billed at the batch tier are divided by its share), summed and rounded up to the
    cent; None while one is not measured."""
    _, google_spend, _ = tools()
    total = 0.0
    for name in measured:
        stage = json.loads(pathlib.Path(per_unit).read_text())["stages"].get(name) or {}
        if stage.get("high_euros") is None:
            return None
        share = google_spend.TIER_PRICE["batch"] if "batch" in stage.get("basis", "") else 1.0
        total += stage["high_euros"] / share
    return math.ceil(round(total * 100, 6)) / 100


def redraw_euros(per_unit=DATA / "costs/per-unit.json"):
    """The euros of one Redraw with notes: the Gemini 3.1 Pro call that corrects the prompt (its measured call,
    MEASURED_ASK) and the draw, both direct; None while either is not measured."""
    return draw_euros(per_unit, (MEASURED_STAGE, MEASURED_ASK))


def yes_key(place, at):
    """The owner's spend yes key for one draw of `place` asked at `at`."""
    return f"concept-{place}-{stamp_key(at)}"


def records(store, place, kind):
    """The records of one place's `kind` (draws or picks), oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{place}/{kind}/"))]


def draws(store, place):
    return records(store, place, "draws")


def picked(store, place):
    """The sha of the draw picked for `place`, or None while none is (never picked, unlocked again, or picked under
    another version of the environment concept: out of date)."""
    found = records(store, place, "picks")
    return found[-1]["sha"] if found and found[-1].get("environment") == environment().version(store) else None


def environment():
    """score/review/environment_concept.py (CONTEXT.md "environment concept"), which every draw reads; imported here
    because it reads this module."""
    from score.review import environment_concept
    return environment_concept


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
        if picked(store, node) or node in tree()["parts"]:
            continue
        if why := waits(store, node):
            waiting[node] = why
        elif not current_draw(store, node, wording_now(store, node)):
            ready.append(node)
    return ready, waiting


def current_draw(store, place, wording):
    """Whether `place` has a draw made from `wording`, its current wording (wording_now: the creator's own when set,
    a Redraw with notes' corrected prompt among them), on the picks it is sent now (the layer above's and its joined
    places'); a draw from an older wording or pick (its data, the draw rules, his wording or one of those picks
    changed since), or made without a blockout while one can be built now (the owner, 2026-10-21), does not count,
    so Draw all draws it again."""
    sent, version = sent_picks(store, place), environment().version(store)
    structured = bool(structure_pictures(store, place))
    return any(str(draw.get("wording", "")).startswith(wording) and (draw.get("picks") or {}) == sent
               and draw.get("environment") == version and (draw.get("blockout") or not structured)
               for draw in draws(store, place))


def placed(store):
    """The places with a draw or a pick in the store."""
    return sorted({key.split("/")[1] for key in store.objects.keys(f"{AREA}/")})


def pick(store, place, sha, by):
    """Lock `place`'s concept on its draw `sha` (None: unlock it); the record. Refused for a sha that is no draw of
    the place, and while its design step may not be taken (step_refusal's pick)."""
    if sha is not None and sha not in {draw["sha"] for draw in draws(store, place)}:
        raise Refused(f"{sha[:12]} is no draw of {place}")
    if sha is not None and (why := step_refusal(store, place, "pick")):
        raise Refused(f"{place} {why}")
    version = environment().version(store)
    if sha is not None and next(draw for draw in draws(store, place) if draw["sha"] == sha).get("environment") != version:
        raise Refused(f"{sha[:12]} was drawn under another environment concept: draw it again")
    record = {"place": place, "sha": sha, "by": by, "at": now(), "environment": version}
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
# One rule for every place at every layer, kept short (the owner, 2026-10-20: "just feed down the concept of the layer
# above"; "your prompt is already too strong and too much"): what the place is and where it sits, its look in a
# sentence or two, what it holds and its own doors, its size against the places beside it, the pictures sent with it,
# the viewpoint and the style. No measures but the creator's own says: the drawing finds the shape.

OUTSIDE_VIEW = "View: high three-quarter from a corner, 35 to 45 degrees down, the whole place in frame, long lens"
INSIDE_VIEW = "View: cutaway (roof and near walls removed), high three-quarter from a corner, 35 to 45 degrees down"
ROOF_KEPT = ", roof openings and domes kept at the cut edges"
EVERY_DRAW = "16:9, no text"
WITH_PEOPLE = "people for scale"
NO_PEOPLE = "no people"
PEOPLE_WORDS = re.compile(r"\b(people|person|crowd|crew)\b", re.IGNORECASE)
COPIED_STYLE = re.compile(r"\bin the ([\w' ]+?)'s style\b")  # a look that says it copies another place's style
FACING = re.compile(r"^(over|facing|towards|toward|across|to the|onto the) ")  # a lead's last clause that faces
LOOK_MOST = 160  # characters of a place's look a draw sends
LONGEST_GENERATED = 1100  # characters of a generated wording, the test's cap (about a third of 2026-10-20's longest, 2992)


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
    """{says, references, people} the creator gave `place`'s draw (data/places/concept_inputs.json), {} when none."""
    return json.loads((DATA / "places/concept_inputs.json").read_text())["places"].get(place, {})


def references_of(store, place):
    """[{picture, shows}] of the creator's references sent with `place`'s draw: the locked environment concept's
    that go with it, else data/places/concept_inputs.json's."""
    held = environment().in_force(store)
    if held is None:
        return inputs_of(place).get("references", [])
    return [{"picture": ref["picture"], "shows": ref["shows"]} for ref in held["references"] if ref["place"] == place]


def style(store):
    """The environment's one style wording, every place's draw shares: the locked environment concept's style line,
    else data/definitions/concept_views.json `style` (the owner's); empty when none is set."""
    held = environment().in_force(store)
    found = held["style"] if held else environment().style_now()
    return f"Style: {found}" if found else ""


def tree(store=None):
    """data/places/within.json: {within: {place: what holds it}, shells: {shell: its short name}, parts: {part: (the
    place whose outside it is part of, its words in that place's draw)}}: a part has no concept of its own (the
    owner, 2026-10-21: the launch, now the Square's). Given the store, each holder's inside places are those his
    newest kept plan of it lays out (plans.overlaid, the one rule of what sits inside what)."""
    found = json.loads((DATA / "places/within.json").read_text())
    within = {name: entry["within"] for name, entry in found["within"].items()}
    if store is not None:
        from score.review import plans
        within = plans.overlaid(store, within)
    return {"within": within,
            "shells": {name: entry["name"] for name, entry in found["shells"].items()},
            "parts": {name: (entry["of"], entry["as"]) for name, entry in found.get("parts", {}).items()}}


def above(place, store=None):
    """The place or shell `place` sits within, None for an outside place of its own (`tree`: given the store, as his
    kept plans lay it out)."""
    return tree(store)["within"].get(place)


def inside_of(place, store=None):
    """The inside places listed directly under `place`, in within.json's order (`tree`: given the store, his kept
    plans' after them)."""
    return [name for name, holder in tree(store)["within"].items() if holder == place]


def name_of(place):
    """A place's name as its look gives it, else "the <place>"."""
    return (look_of(place) or {}).get("name") or f"the {place}"


def short_name(place):
    """A place's short name as its look gives it (place.json `short`), "the <short>", else its name."""
    short = (look_of(place) or {}).get("short")
    return f"the {short.lower()}" if short else name_of(place)


def no_sizes(words):
    """`words` with every measure in metres taken out ("27 x 55 m", "at 9 m", "15 m"), and a bracket left empty by
    it: the drawing finds the shape (the owner, 2026-10-20)."""
    words = re.sub(r",? ?(at |about )?\d+(\.\d+)?( ?x ?\d+(\.\d+)?)? ?m\b", "", words)
    return re.sub(r" ?\(\s*[,;:]?\s*\)", "", words).strip()


def copied_from(text):
    """The place whose style a look's words say they copy ("..., in the cockpit's style: ..."), None when none: such
    a look is that place's, not its own (the owner, 2026-10-21: every ship room drew as the cockpit)."""
    found = COPIED_STYLE.search(text)
    return found.group(1) if found else None


def look_text(place):
    """The words of `place`'s own look (place.json `style.text`), no measures; "" when it has none, or when its words
    copy another place's style."""
    text = ((look_of(place) or {}).get("style") or {}).get("text") or ""
    return "" if copied_from(text) else no_sizes(text)


def floor_words(place):
    """What a floor plan the creator approved says `place` is for (data/definitions/<shell>_floor.json: a room's or
    its walkway's `for`, with its side of the shell), as a sentence; "" when no floor plan names it."""
    for path in sorted((DATA / "definitions").glob("*_floor.json")):
        plan = json.loads(path.read_text())
        for entry in [*plan.get("rooms", []), plan.get("walkway") or {}]:
            if entry.get("place") == place and entry.get("for"):
                side = f" on the {entry['side']} side" if entry.get("side") in ("port", "starboard") else ""
                return f"In the {path.stem.removesuffix('_floor')}{side}; for {no_sizes(entry['for'])}."
    return ""


def short_look(place):
    """`place`'s look in a sentence or two: its first sentences up to LOOK_MOST characters, a longer first one cut at
    its last clause that fits; "" when it has none."""
    kept = ""
    for sentence in re.split(r"(?<=\.) ", look_text(place)):
        if len(kept) + len(sentence) > LOOK_MOST:
            if not kept:
                cut = max(sentence.rfind(mark, 0, LOOK_MOST) for mark in (", ", "; ", ": "))
                kept = sentence[:cut] + "." if cut > 0 else sentence[:LOOK_MOST]
            break
        kept = f"{kept} {sentence}".strip()
    return kept


def door_label(plan, side):
    """The plan's own label of the door a lead names (`N`, `90`, `W@9`: the side, at a height), lower case, its
    words after a comma left out."""
    face, _, level = side.partition("@")
    for door in plan.get("doors", []):
        if str(door[0]) == face and (not level or door[-1] == float(level)):
            label = [part for part in door if isinstance(part, str)][-1].lower()
            return re.split(r",(?![^(]*\))", no_sizes(label))[0]
    return f"{face} door"


def facing(why):
    """The facing a lead's `why` names in its last clause ("over the square and the harbour"), "" when none."""
    last = re.sub(r" ?\([^)]*\)", "", why).rsplit(", ", 1)[-1].strip()
    return last if FACING.match(last) else ""


def door_words(place, side, lead):
    """One lead of `place`'s plan in a few relational words: its door by its plan's label and what it opens into."""
    label, target = door_label(plan_of(place), side), lead.get("to")
    if target == "sealed":
        return f"{label} (shut)"
    if target == "tube":
        return f"{label} onto a walkway tube"
    if target == "outside":
        faces = facing(lead.get("why", ""))
        return f"{label} onto the outside" + (f", {faces}" if faces else "")
    return f"{label} into {short_name(target)}"


def holds_and_doors(store, place):
    """One sentence: the places listed inside `place` and its own doors from its plan's leads, no others; ""
    with neither."""
    inside, leads = inside_of(place, store), plan_of(place).get("leads") or {}
    shown = [words for of, words in tree()["parts"].values() if of == place]
    parts = [f"inside: {', '.join(short_name(name) for name in inside)}" if inside else "",
             f"part of it: {'; '.join(shown)}" if shown else "",
             (f"its doors: {'; '.join(door_words(place, side, lead) for side, lead in leads.items())}; no other doors "
              "or openings") if leads else ""]
    said = "; ".join(part for part in parts if part)
    return f"{said[0].upper()}{said[1:]}." if said else ""


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


def size_words(store, place):
    """How big `place` is against the places beside it under the same layer above, in relative words only (ranked by
    its plan's floor area, its walls against a person's height); "" when its plan gives no floor."""
    holder, own = above(place, store), floor_and_walls(place)
    if not holder or own is None:
        return ""
    others = sorted(found[0] for name in inside_of(holder, store) if name != place and (found := floor_and_walls(name)))
    words = []
    if others and own[0] > others[-1]:
        ratio = round(own[0] / others[-1])
        words.append(f"the largest in {short_name(holder)}"
                     + (f", floor about {TIMES.get(ratio, 'many times')} any other's" if ratio >= 2 else ""))
    elif others and own[0] < others[0]:
        words.append(f"the smallest in {short_name(holder)}")
    elif others:
        words.append(f"one of the {'larger' if own[0] >= others[len(others) // 2] else 'smaller'} in "
                     f"{short_name(holder)}")
    if own[1]:
        tall = own[1] / PERSON
        words.append("walls towering over people" if tall >= 4 else
                     "walls twice a person's height" if tall >= 2 else "ceiling just above head height")
    return f"Size: {', '.join(words)}." if words else ""


def joined(store, place):
    """The places beside `place` under the same layer above that its plan's leads open into (a tube's `joins` too)."""
    holder, found = above(place, store), []
    for lead in (plan_of(place).get("leads") or {}).values():
        for other in (lead.get("to"), lead.get("joins")):
            if other and other != place and other not in found and holder and above(other, store) == holder:
                found.append(other)
    return found


def sent_picks(store, place):
    """{place: sha} of the picked concepts a first draw of `place` sends: the layer above's, then each joined
    place's that is picked."""
    return {other: sha for other in [above(place, store), *joined(store, place)]
            if other and (sha := picked(store, other))}


# --- the design steps, in one place (the owner, 2026-10-21) ----------------------------------------------------
# A place's concept is drawn only once the layer above is picked (the pick is the approval), its scene inventory read
# and its plan made; its scene inventory is read only after its own pick; its plan made only after that reading. Every
# button and the server ask `step_refusal`.

def plan_made(store, place):
    """Whether `place`'s plan is made: plan@<place> stands accepted, after its concept's pick standing now (a place
    with no plan row, a shell: its plan shown; score/review/plans.made)."""
    from score.review import plans
    return plans.made(store, place)


def holding_row(store, place):
    """The scene inventory row of the layer above whose outline holds `place` on its plan (the ship for the ship's
    rooms, a module for a base room, the block for the flat): the row its plan's inside places give it
    (score/review/plans.holder_of), else the layer above's data/plans `holds` {place: row id}, else None."""
    from score.review import plans
    held = plans.holder_of(store, place)
    return held["row"] if held and held["row"] else (plan_of(above(place, store)).get("holds") or {}).get(place)


def holding_box(store, place):
    """The pixel box [left, top, right, bottom] on the layer above's picked concept of the row that holds `place`
    (its surest SAM box, score/review/reading.row_boxes), or None while there is none."""
    from score.review import reading
    row = holding_row(store, place)
    boxes = reading.row_boxes(store, above(place, store), row) if row else None
    return boxes[0] if boxes else None


def outlined(store, place):
    """Whether the layer above's plan lays out `place`'s own outline, held by an inventory row or by its own walls
    (the owner, 2026-10-21: the blockout is drawn from it; the flat and the camp stand on their holder's walls)."""
    from score.review import plans
    return plans.holder_of(store, place) is not None


def step_refusal(store, place, step):
    """Why `place` may not take its design `step` now ("draw", "pick", "read" its scene inventory, "plan"), in words,
    or None. Draw and pick: the layer above picked, its inventory read, its plan made and this place's outline on it
    (`outlined`; a draw also needs its references here); read: its own pick; plan: its own reading."""
    from score.review import reading
    holder = above(place, store)
    if place in tree()["parts"]:
        return f"is part of the {tree()['parts'][place][0]}'s concept, with none of its own"
    if step == "read":
        return None if picked(store, place) else "its concept is not picked"
    if step == "plan":
        return None if reading.reading_of(store, place) else "its scene inventory is not read"
    if environment().unlocked(store):
        return "waits for the environment concept to be locked"
    if holder and not picked(store, holder):
        return f"waits for {holder}'s concept to be picked"
    if holder and not reading.reading_of(store, holder):
        return f"waits for {holder}'s scene inventory to be read"
    if holder and not plan_made(store, holder):
        return f"waits for {holder}'s plan to be made"
    if holder and not outlined(store, place):
        return f"waits for {holder}'s plan to lay it out"
    missing = [ref["picture"] for ref in references_of(store, place)
               if not resolved(ref["picture"]).is_file()] if step == "draw" else []
    if missing:
        return (f"its reference {missing[0]} is not on this machine (the private bucket's references/, copied to "
                f"{PROPS_HOME / 'references'})")
    return None


def waits(store, place):
    """Why a first draw of `place` cannot be made now (step_refusal's draw), or None."""
    return step_refusal(store, place, "draw")


WINDOW_ROW = re.compile(r"\b(window|windows|porthole|portholes|pane|panes|glazing)$", re.IGNORECASE)
WINDOW_LOOK = re.compile(r"\b(windows?|portholes?|glazing)\b", re.IGNORECASE)
VIEW_SCALE = 2.5  # how much wider than what holds a place the view through its windows reaches, each way


def looks_out(place):
    """Whether `place` has windows or openings to the outside (the owner, 2026-10-21): a plan lead onto the outside,
    a scene inventory row that is a window (its name, before any colon, ends in window, porthole, pane or glazing),
    or its own look naming windows."""
    leads = (plan_of(place).get("leads") or {}).values()
    rows = (inventory_read(place) or {}).get("rows", [])
    return (any(lead.get("to") == "outside" for lead in leads)
            or any(WINDOW_ROW.search(row["name"].split(":")[0].strip()) for row in rows)
            or bool(WINDOW_LOOK.search(look_text(place))))


def view_box(box, size):
    """The box around `box` (pixels) VIEW_SCALE times as wide and tall about its middle, inside a picture of `size`."""
    wide, tall = (box[2] - box[0]) * VIEW_SCALE / 2, (box[3] - box[1]) * VIEW_SCALE / 2
    middle = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    return (max(0, middle[0] - wide), max(0, middle[1] - tall), min(size[0], middle[0] + wide),
            min(size[1], middle[1] + tall))


STRUCTURE = ("the structure: a rough grey model of it at real sizes from {parent}'s plan, seen from the fixed view{rest}; "
             "keep this layout, shapes and proportions exactly, add the look")
SKY_PICTURE = "its sky over its site: keep each world's place, size and phase, add the look"


def structure_pictures(store, place):
    """[(what it is, its source)] of `place`'s blockout (score/review/blockout.py: ("blockout", place)) and, for a top
    place whose sky holds a world the fixed view does not show, its sky picture (("sky", place)); [] while the plan
    it is built from is not there."""
    from score.review import blockout, environment_plan, plans
    holder = above(place, store)
    if holder:  # its blockout stands once the holder's plan lays out its outline (blockout.scene_of)
        return [(STRUCTURE.format(parent=short_name(holder), rest=", its own shell lighter, the places beside it "
                                  "darker"), ("blockout", place))] if plans.holder_of(store, place) else []
    site = environment_plan.site_of(store, place)
    if site is None:
        return []
    found = [(STRUCTURE.format(parent="the environment", rest=", the ground round it at its heights"),
              ("blockout", place))]
    worlds = (site.get("overhead") or {}).get("bodies", [])
    parts = blockout.scene_of(store, place)[0]
    return found + ([(SKY_PICTURE, ("sky", place))] if blockout.unseen(parts, worlds) else [])


def sent_pictures(store, place):
    """[(what it is, its source)] a first draw of `place` sends, in order: its blockout and sky picture
    (`structure_pictures`), a crop of the layer above's picked concept
    showing only what holds it (source: ("crop", the place above, its box)), for a place that looks out (looks_out) the
    surroundings of that around it (("view", the place above, the same box)), each joined place's picked concept
    (source: that place's name), then the creator's references (their paths)."""
    holder = above(place, store)
    box = holding_box(store, place) if holder else None
    found = structure_pictures(store, place)
    found += [(f"a crop of {short_name(holder)}'s picked concept: draw the inside of what this crop shows",
               ("crop", holder, box))] if box else []
    found += [(f"{short_name(holder)}'s picked concept around it: through its windows, this view",
               ("view", holder, box))] if box and looks_out(place) else []
    found += [(f"{short_name(other)}, picked: match the door they share", other)
              for other in joined(store, place) if picked(store, other)]
    return found + [(f"reference for {ref['shows']}, not its size", resolved(ref["picture"]))
                    for ref in references_of(store, place)]


COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


def phase_words(world):
    """A world's face as seen from here in a few words: a bright point when too small for a disc, else its phase and
    the side the Sun lights it from."""
    if world["across"] < 0.05:
        return "a bright point"
    lit = world["lit"]
    phase = ("dark, new" if lit < 0.03 else "a thin crescent" if lit < 0.25 else "a crescent" if lit < 0.45 else
             "half lit" if lit < 0.55 else "gibbous" if lit < 0.97 else "full")
    east, north, _ = world["lit_from"]
    side = COMPASS[round(math.degrees(math.atan2(east, north)) % 360 / 45) % 8]
    return f"{phase}, lit from the {side}" if 0.03 <= lit < 0.97 else phase


def overhead_words(store, place):
    """What is seen overhead at a top place at its scene time (its site on the environment's plan), one sentence: each
    body above the horizon where it stands, how big and its phase; each light's height; each backdrop. "" for a place
    within another or before it is known."""
    from score.review import environment_plan
    if above(place, store):
        return ""
    site = environment_plan.site_of(store, place)
    found = (site or {}).get("overhead")
    if not found:
        return ""
    shown = [f"{world['name']} {world['altitude']:.0f} degrees up to the "
             f"{COMPASS[round(world['azimuth'] / 45) % 8]}, {world['across']:.1f} degrees across, {phase_words(world)}"
             if world["across"] >= 0.05 else
             f"{world['name']} {world['altitude']:.0f} degrees up to the {COMPASS[round(world['azimuth'] / 45) % 8]}, "
             "a bright point" for world in found["bodies"] if world["altitude"] > 0]
    lights = [f"the {light['name']} below the horizon" if light["altitude"] < -6 else
              f"the {light['name']} low" if light["altitude"] < 15 else
              f"the {light['name']} {light['altitude']:.0f} degrees up" for light in found["lights"]]
    backdrops = [f"the {backdrop['name']} {'all round' if backdrop['shape'] == 'dome' else 'on the horizon'}"
                 for backdrop in found["backdrops"]]
    return f"Overhead: {'; '.join(shown + lights + backdrops)}."


def has_people(place):
    """Whether `place`'s draw shows people (the owner, 2026-10-20: not in every concept): as the creator's `people`
    says when set, else when its cast record (data/characters/<place>.json) holds people, groups or a crowd, or its
    look names people."""
    said = inputs_of(place).get("people")
    if said is not None:
        return said
    cast_path = DATA / "characters" / f"{place}.json"
    cast = json.loads(cast_path.read_text()) if cast_path.is_file() else {}
    return bool(cast.get("people") or cast.get("groups") or cast.get("crowd")
                or PEOPLE_WORDS.search(look_text(place)))


def indoors(store, place):
    """Whether `place` is drawn as a cutaway: as its plan says (`inside`), else when it sits within another place
    and is no shell of its own."""
    said = plan_of(place).get("inside")
    return said if said is not None else (above(place, store) is not None and place not in tree()["shells"])


def view_words(store, place):
    """The fixed viewpoint (an outside place from above, an inside one as a cutaway keeping the roof the picture above
    shows), the frame and whether people show, in one line."""
    view = INSIDE_VIEW + (ROOF_KEPT if above(place, store) else "") if indoors(store, place) else OUTSIDE_VIEW
    return f"{view}; {EVERY_DRAW}, {WITH_PEOPLE if has_people(place) else NO_PEOPLE}."


def generated(store, place):
    """The first-draw wording of `place` by the one rule, short, every part from data and the picks it is sent."""
    look = short_look(place)
    pictures = sent_pictures(store, place)
    listed = "Pictures: " + "; ".join(f"{number}. {words}" for number, (words, _) in enumerate(pictures, 1)) + "."
    crop = next((number for number, (_, source) in enumerate(pictures, 1)
                 if isinstance(source, tuple) and source[0] == "crop"), None)
    return " ".join(part for part in (
        f"Concept painting of {short_name(place)}" + (f": the inside of what picture {crop} shows." if crop else "."),
        floor_words(place), inputs_of(place).get("says", ""), f"Look: {look}" if look else "",
        holds_and_doors(store, place), size_words(store, place), overhead_words(store, place),
        listed if pictures else "",
        view_words(store, place),
        style(store)) if part)


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


def where_in(mark):
    """Where a mark lies in its picture, in words ("top left", "middle", "bottom right"), from its centre."""
    across = ("left", "middle", "right")[min(2, int((mark["x"] + mark["w"] / 2) * 3))]
    down = ("top", "middle", "bottom")[min(2, int((mark["y"] + mark["h"] / 2) * 3))]
    return "middle" if across == down == "middle" else f"{down} {across}".replace("middle middle", "middle")


def numbered(marks, context):
    """[(label, mark)] of every note-carrying mark: the draw's numbered 1, 2, ..., the context pictures' (the picked
    concepts it was drawn on) P1, P2, ... across them, in their order."""
    return ([(str(number), mark) for number, mark in enumerate(marks, 1)]
            + [(f"P{number}", mark) for number, mark in enumerate(context, 1)])


def notes_words(marks, context, note):
    """The creator's notes, each box's tied to its label, its picture and where it lies, then his note on the whole."""
    words = [f"Box {label} ({where_in(mark)}" + (f" of the picked concept of the {mark['on']}" if "on" in mark else "")
             + f"): {mark['note'].strip()}." for label, mark in numbered(marks, context) if mark["note"].strip()]
    return " ".join(words + ([f"Overall: {note.strip()}"] if note.strip() else []))


def pictures_words(context):
    """What the pictures a Redraw with notes sends are, in order: the draw boxed, clean, then each context picture."""
    places = list(dict.fromkeys(mark["on"] for mark in context))
    return ("Image 1 is the current painting with numbered red boxes marking areas to change; image 2 is the same "
            "painting clean" + "".join(f"; image {number} is the picked concept of the {name}, its boxes labelled P"
                                       for number, name in enumerate(places, 3)) + ".")


def prompt_question(prompt, marks, context, note):
    """What Gemini is asked for a Redraw with notes (the owner, 2026-10-20): the prompt the picture was drawn from
    corrected by the creator's notes, each changed area named by where it lies, in the draw or in a context picture."""
    return (f"{pictures_words(context)} The painting was drawn from the prompt below. Rewrite the prompt so a new "
            "drawing makes exactly the changes the creator's notes ask and keeps everything else: work each note into "
            "the prompt, naming each area by where it lies in its picture (for example 'the doorway at the bottom "
            "left', 'the launch pad far across the water, as the square's picture shows it top right'), never by box "
            "label. Keep it as short as the prompt. Answer with the corrected prompt only.\n\n"
            f"The creator's notes: {notes_words(marks, context, note)}\n\nThe prompt:\n{prompt}")


def redraw_wording(corrected, marks, context, note):
    """A redraw's wording: the corrected prompt, then the pictures and what each box changes."""
    return (f"{corrected}\n\n{pictures_words(context)} Paint image 2 again from the wording above, changing only "
            f"these: {notes_words(marks, context, note)} Everything else stays as it is. Draw no boxes, numbers, "
            "text or labels.")


def with_note(wording, note):
    return f"{wording} The creator's note: {note.strip()}" if note.strip() else wording


def boxed(picture, labelled):
    """A copy of `picture` with each (label, mark) drawn as a red box with its label."""
    from PIL import ImageDraw
    copy = picture.convert("RGB")
    pen = ImageDraw.Draw(copy)
    wide, tall = copy.size
    for label, mark in labelled:
        left, top = mark["x"] * wide, mark["y"] * tall
        box = (left, top, left + mark["w"] * wide, top + mark["h"] * tall)
        pen.rectangle(box, outline=(255, 0, 0), width=MARK_WIDTH)
        pen.text((box[0] + 2 * MARK_WIDTH, box[1] + 2 * MARK_WIDTH), label, fill=(255, 0, 0),
                 font_size=max(24, tall // 20))
    return copy


def checked_marks(marks, on=None):
    """The marks as given, each a box inside its picture with its note (and, for a context picture's, the place
    `on` it lies, one of `on`); Refused otherwise."""
    found = []
    for mark in marks or []:
        try:
            box = [float(mark[name]) for name in ("x", "y", "w", "h")]
        except (KeyError, TypeError, ValueError) as broken:
            raise Refused(f"a marked area is not a box: {mark!r}") from broken
        if not (0 <= box[0] < 1 and 0 <= box[1] < 1 and 0 < box[2] <= 1.000001 - box[0]
                and 0 < box[3] <= 1.000001 - box[1]):
            raise Refused(f"a marked area lies outside the picture: {box}")
        checked = {"x": box[0], "y": box[1], "w": box[2], "h": box[3], "note": str(mark.get("note", ""))[:500]}
        if on is not None:
            if mark.get("on") not in on:
                raise Refused(f"{mark.get('on')!r} is no picked concept this place was drawn on")
            checked["on"] = mark["on"]
        found.append(checked)
    return found


# --- the draw ---------------------------------------------------------------------------------------------------

def first_parts(store, place, request):
    """(wording, [PIL pictures]) a first draw sends: its wording (his edit, else the place's now) with his note, and
    the pictures sent_pictures names; Refused while it waits."""
    from PIL import Image
    if request.get("marks") or request.get("context_marks"):
        raise Refused("a first draw has no picture to mark")
    if why := waits(store, place):
        raise Refused(f"{place} {why}")
    sent = checked_wording(request.get("wording")) or wording_now(store, place)
    pictures = [sent_picture(store, source) for _, source in sent_pictures(store, place)]
    return with_note(sent, str(request.get("note", ""))), pictures


def sent_picture(store, source):
    """The PIL picture of one of sent_pictures' sources: a crop of a place's picked concept to its box, a place's
    picked concept, or a file."""
    from PIL import Image
    if isinstance(source, tuple) and source[0] in ("blockout", "sky"):
        from score.review import blockout
        return (blockout.picture if source[0] == "blockout" else blockout.sky_picture)(store, source[1])
    if isinstance(source, tuple):
        kind, holder, box = source
        picture = blob_picture(store, picked(store, holder))
        return picture.crop(tuple(box) if kind == "crop" else view_box(box, picture.size))
    if isinstance(source, str):
        return blob_picture(store, picked(store, source))
    return Image.open(source)


def blob_picture(store, sha):
    from PIL import Image
    return Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{sha}")))


def redrawn(store, place, request, by, reviser):
    """(wording, [PIL pictures], record fields) of a Redraw with notes: Gemini (`reviser(question, pictures)`) corrects
    the prompt the base was drawn from by his notes, seeing the base boxed and clean and each picked concept he marked
    (the layer above's, a joined place's) with its boxes; the corrected prompt is kept as the place's own wording; the
    draw then sends it with every note and the same pictures."""
    base = request["base"]
    found = [record for record in draws(store, place) if record["sha"] == base]
    if not found:
        raise Refused(f"{base[:12]} is no draw of {place}")
    if why := waits(store, place):
        raise Refused(f"{place} {why}")
    picks = sent_picks(store, place)
    marks, note = checked_marks(request.get("marks")), str(request.get("note", ""))
    context = checked_marks(request.get("context_marks"), on=picks)
    clean, labelled = blob_picture(store, base), numbered(marks, context)
    pictures = [boxed(clean, [(label, mark) for label, mark in labelled if "on" not in mark]), clean]
    pictures += [boxed(blob_picture(store, picks[name]), [(label, mark) for label, mark in labelled
                                                          if mark.get("on") == name])
                 for name in dict.fromkeys(mark["on"] for mark in context)]
    prompt = found[-1].get("corrected") or found[-1].get("wording") or wording_now(store, place)
    question = prompt_question(prompt, marks, context, note)
    corrected = checked_wording(reviser(question, pictures))
    if not corrected:
        raise Refused("the prompt model answered with no prompt")
    if corrected != own_wording(store, place):
        worded(store, place, corrected, by)  # before the draw: a refused draw still keeps the paid correction
    calls = [{"model": PROMPT_MODEL, "asked": question, "answered": corrected}]
    return redraw_wording(corrected, marks, context, note), pictures, {
        "corrected": corrected, "calls": calls, "context_marks": context, "picks": found[-1].get("picks"),
        "blockout": found[-1].get("blockout")}


def redraw_preview():
    """What Redraw with notes sends to the draw, its notes as placeholders (the concept review page shows it)."""
    marks = [{"x": 0.0, "y": 0.0, "w": 0.3, "h": 0.3, "note": "<mark 1's note>"}]
    context = [{"x": 0.7, "y": 0.0, "w": 0.3, "h": 0.3, "note": "<mark P1's note>", "on": "<place above>"}]
    return redraw_wording("<this draw's prompt, corrected by your notes>", marks, context, "<your note>")


def revise(question, pictures):
    """One Gemini 3.1 Pro call (google_spend, on its ledger, never cached: each click is its own) on the question and
    pictures; the text it answered, or Refused."""
    pro, google_spend, secret_store = tools()
    body = {"contents": [{"role": "user", "parts": [{"text": question}]
                          + [pro.part(picture, LONGEST_SENT) for picture in pictures]}],
            "generationConfig": {"temperature": 0.2}}
    try:
        answer = google_spend.generate(PROMPT_MODEL, body, secret_store.secret(pro.KEY_SECRET), TIMEOUT,
                                       caller=CALLER)
    except urllib.error.HTTPError as error:
        raise Refused(f"the prompt model refused ({error.code})") from error
    candidate = (answer.get("candidates") or [{}])[0]
    return "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                   if not part.get("thought")).strip().strip('"')


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


def blockout_kept(store, place, pictures):
    """The sha of the blockout a first draw of `place` sends (its first picture when structure_pictures gives one),
    kept in the store's blobs; None when it sends none."""
    if not structure_pictures(store, place):
        return None
    buffer = io.BytesIO()
    pictures[0].convert("RGB").save(buffer, "PNG")
    return kept(store, buffer.getvalue())


def without_blockout(store, nodes):
    """[node] of `nodes` whose picked draw was drawn without a blockout (the owner, 2026-10-21: picked top places keep
    their picks; this names them)."""
    return [node for node in nodes if (sha := picked(store, node))
            and not next((draw for draw in draws(store, node) if draw["sha"] == sha), {}).get("blockout")]


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


def draw(store, place, request, by, caller=call, offsite=None, reviser=revise):
    """One draw of `place`'s concept inside the owner's yes (SCORE_SPEND_TICKET names it; compute.require_cleared
    refuses otherwise, and while the month's books are unknown): a first draw one call, a Redraw with notes two (the
    prompt corrected by `reviser(question, pictures)`, then the draw); its record, copied off this PC first
    (`offsite`: a store with the bucket's calls, None the bucket). `caller(wording, pictures)` makes the PNG bytes."""
    from score.adapters import compute
    yes = compute.require_cleared("a concept draw", store)
    if environment().unlocked(store):
        raise Refused("the environment concept is unlocked; lock it first")
    if request.get("base"):
        wording, pictures, fields = redrawn(store, place, request, by, reviser)
    else:
        wording, pictures = first_parts(store, place, request)
        kept_as_own(store, place, request, by)  # before the call: a refused call still keeps his edit
        fields = {"picks": sent_picks(store, place), "calls": [], "blockout": blockout_kept(store, place, pictures)}
    png = caller(wording, pictures)
    sha = kept(store, png)
    record = {"place": place, "sha": sha, "name": f"{place}-concept.png", "at": now(), "by": by,
              "euros": yes["euros"], "yes": yes["key"], "base": request.get("base") or None,
              "marks": checked_marks(request.get("marks")), "note": str(request.get("note", "")), "wording": wording,
              "environment": environment().version(store),
              **fields, "calls": [*fields["calls"], {"model": tools()[0].MODEL, "asked": wording, "answered": sha}]}
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
