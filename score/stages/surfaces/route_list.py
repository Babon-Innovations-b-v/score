"""The finish route's list row (paid: one Gemini 3.1 Pro answer a take, all the place's takes in one batch at half
price, route_ask.py: asked once, an ask asked before read back free).

Gemini sees the take's close-up (its own, or the stand-in, said so in the question), every view of the model's own
texture and the same views split into the views row's colour regions (and its close-up laid on the model in those
regions, the view route_views.CLOSE_UP, where the views row laid it), and gives in one answer the take's complete
finish list and a label for each region in each view. Each finish is matched FIRST to a surface of the library with
its settings: the palette token of its colour (one of the scene palette's, read from its design by the palette row,
scene_palette.py), its shine (roughness, metal), its seed (one a finish of each take, `take_seed`, so each object's wear
and dirt pattern is its own) and its wear: the scene's level (its scene palette's), or its own level of the library's
where the pictures show a cause for it (a walked path, worn edges, the ground round a door; owner, 2026-10-20), the
level and its cause both given or neither. The surfaces offered are the whole library filtered by the scene palette,
with the kind's own (palette_library.take_surfaces). A new surface is proposed only when no surface fits with any
settings (`fits` false). Each region showing in a view is labelled with the finish its part has there; the split votes
the labels across views. Each finish also keeps its token's colour and its surface's family, which the split's colour
check reads before anything is baked. A take whose answer lists a finish it labels no region with is asked once more,
its answer and that finish told (followed_up), in one more batch of those takes alone: every other take's ask and
answer stay as they were.

Output: <take>.json per take (its finishes, each with surface, settings, fits, new_surface, wear_level, wear_cause,
colour, family; its labels, {view: {region: finish}}, 0-based), questions.json (the finishes with their own wear and
why, the takes with no usable answer).
Gate "library first": every cast take is listed, every finish names a library surface with settings inside the
library's ranges, and one that does not fit proposes a surface; a take with no usable answer is a gap, named. Each
such take is a batch gap (batch-gaps.json, score/stages/batch_gaps.py, with the ones carried from the views): the gate
still fails it, the table moves the fault to complete, and the split leaves the take out.
"""
import copy
import json
import pathlib
import sys
import zlib

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_ask  # noqa: E402
import palette_library  # noqa: E402
import route_ask  # noqa: E402
import route_data  # noqa: E402
import route_views  # noqa: E402
import surface_gates as gates  # noqa: E402
import score.stages.batch_gaps as batch_gaps  # noqa: E402

LIST_EUROS = 0.5  # a guess for the row's run (a place's takes at half of google_spend.ESTIMATES); never a price
CALLER = "finish-route-list"
SEED_SPAN = 100000  # take seeds lie within this of the node's, each take's finishes counted on from its own
LAID = (". The last picture is the close-up's own colours laid on the model, split into the same regions (the view "
        "named {view}): a small part the texture shows faintly or not at all, such as a label, a lamp or a screen, has "
        "its region there")
QUESTION = """You help paint a 3D model with surfaces from a shared library. The object: {object}.
The first picture is {close_up}. The next {count} pictures show the model from every side ({views}) in its own
texture, shaded only by angle. The {count} after them show the same views with the model split into colour regions,
each region one flat colour, the same colour for the same region in every view{laid}:
{regions}
The regions showing in each view:
{shown}
First, list the object's finishes: the distinct surface treatments a painter would give its parts. List a finish only
when it truly differs in material or paint from the others; dirt, wear, scratches, light and shadow are not finishes.
For each finish give its parts in words and FIRST the library surface it is, with its settings: the palette token
nearest its colour, and its roughness and metal from 0 to 1 (the surface's own unless the pictures clearly show
otherwise). The library's surfaces, each with its own token, roughness and metal:
{surfaces}
The palette tokens:
{tokens}
Choose by what the part is and how such a part is made, then by its colour. Only when no library surface fits with
any settings, set "fits" to false and propose a new library surface. Wear is the scene's level ({wear}). A finish
takes another of the library's wear levels ({levels}) only where the pictures show a cause for it, such as a walked
path, worn edges or the ground round a door: then set "wear" to that level and say the cause in "wear_cause"; else
leave both out.
Then label every region showing in every view with the finish (its number in your list, from 1) that the region's
part has in that view: one label for each view and region listed above."""
# The follow-up of an answer that lists a finish it labels no region with (followed_up).
FOLLOW_UP = ("Your answer was:\n{answer}\nIt lists finish {finishes} but labels no region with it in any view. Look "
             "again, view by view, for the regions its parts show in, and answer the whole question again, in full: "
             "keep every finish of your list, and label each region with the finish its part has in that view.")


def palette_tokens(palette):
    """{token: linear RGB} of the scene palette's tokens (read from its design), in the scene library's order."""
    chosen = set(palette["tokens"])
    return {token: colour for token, colour in palette_library.library_tokens(palette).items() if token in chosen}


def surface_lines(surfaces):
    """Each surface as a line: its code, part_judge's words for it, its token, roughness and metal."""
    import part_judge
    words = part_judge.material_lines(surfaces).splitlines()
    return "\n".join(f"{line}; token {spec.get('token')}, roughness {spec.get('roughness', 0.5):.2f}, metal "
                     f"{spec.get('metal', 0.0):.2f}" for line, spec in zip(words, surfaces.values()))


def token_lines(tokens):
    import part_judge
    return "\n".join(f"- {token}: {part_judge.colour_words(colour)}" for token, colour in tokens.items())


def region_lines(regions):
    return "\n".join(f"- region {entry['region'] + 1}: {finish_ask.LABEL_WORDS[entry['region']]}, "
                     f"{entry['share']:.0%} of the model seen, its texture there about RGB {entry['srgb']}"
                     for entry in regions)


def shown_lines(shown):
    """Each view and the regions (1-based) showing in it."""
    return "\n".join(f"- {view}: regions {', '.join(str(region + 1) for region in regions)}"
                     for view, regions in shown.items())


def list_schema(surfaces, tokens, views, levels):
    """The answer's schema: the finishes, each surface one of the surfaces' codes, token one of the tokens and wear one
    of the library's wear levels, and the labels, each a view, a region and a finish."""
    proposal = {"type": "OBJECT", "properties": {"name": {"type": "STRING"}, "description": {"type": "STRING"},
                                                 "why": {"type": "STRING"}}, "required": ["name", "description", "why"]}
    finish = {"type": "OBJECT",
              "properties": {"parts": {"type": "STRING"}, "finish": {"type": "STRING"},
                             "surface": {"type": "STRING", "enum": finish_ask.surface_codes(surfaces)},
                             "token": {"type": "STRING", "enum": list(tokens)},
                             "roughness": {"type": "NUMBER"}, "metal": {"type": "NUMBER"},
                             "fits": {"type": "BOOLEAN"}, "new_surface": proposal,
                             "wear": {"type": "STRING", "enum": list(levels)}, "wear_cause": {"type": "STRING"}},
              "required": ["parts", "finish", "surface", "token", "roughness", "metal", "fits"],
              "propertyOrdering": ["parts", "finish", "surface", "token", "roughness", "metal", "fits", "new_surface",
                                   "wear", "wear_cause"]}
    label = {"type": "OBJECT", "properties": {"view": {"type": "STRING", "enum": list(views)},
                                              "region": {"type": "INTEGER"}, "finish": {"type": "INTEGER"}},
             "required": ["view", "region", "finish"]}
    return {"type": "OBJECT", "properties": {"finishes": {"type": "ARRAY", "items": finish},
                                             "labels": {"type": "ARRAY", "items": label}},
            "required": ["finishes", "labels"], "propertyOrdering": ["finishes", "labels"]}


def list_body(pictures, entry, record, library, wear):
    """The request: the close-up, the views, the region views (the laid close-up's last, where the views row laid it),
    the question and its schema. `record` is the take's views record; `library` its surfaces, the tokens and the wear
    levels; `wear` the scene's level (its scene palette's)."""
    surfaces, tokens, levels = library
    stand_in = record.get("close_up") == route_data.STAND_IN
    views = list(record["views"])
    laid = pictures.get("laid")
    text = QUESTION.format(object=entry["object"], close_up=(f"a {route_data.STAND_IN}" if stand_in
                                                             else "the object's close-up"),
                           count=len(views), views=", ".join(views), regions=region_lines(record["regions"]),
                           laid=LAID.format(view=route_views.CLOSE_UP) if laid is not None else "",
                           shown=shown_lines(pictures["shown"]), surfaces=surface_lines(surfaces),
                           tokens=token_lines(tokens), wear=wear, levels=", ".join(levels))
    parts = [finish_ask.picture_part(pictures["close_up"], 1024)]
    parts += [finish_ask.picture_part(picture, 512) for picture in pictures["shaded"]]
    parts += [finish_ask.picture_part(picture, 512) for picture in pictures["regions"]]
    parts += [finish_ask.picture_part(laid, 1024)] if laid is not None else []
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": list_schema(surfaces, tokens, list(pictures["shown"]), levels)}}


def take_seed(seed, take):
    """The seed of a take's first finish: the node's moved by the take's name (the same every run), so the same finish
    on two objects wears and dirties apart."""
    return int(seed) + zlib.crc32(take.encode()) % SEED_SPAN


def own_wear(entry, levels):
    """(level, cause) of a finish's own wear, or (None, None): a library level and a cause, both given or neither."""
    level, cause = entry.get("wear"), (entry.get("wear_cause") or "").strip()
    return (level, cause) if level in levels and cause else (None, None)


def finishes_of(answer, library, seed):
    """The answer's finishes: each surface by its library name, its settings clipped to 0-1 with its own seed (`seed`
    the take's, one a finish) and its own wear where it gives a level with a cause, its token's colour and its
    surface's family. `library` is the take's surfaces, the tokens and the wear levels."""
    surfaces, tokens, levels = library
    names, codes = list(surfaces), finish_ask.surface_codes(surfaces)
    found = []
    for number, entry in enumerate(answer["finishes"]):
        settings = {"token": entry["token"], "roughness": round(float(np.clip(entry["roughness"], 0, 1)), 3),
                    "metal": round(float(np.clip(entry["metal"], 0, 1)), 3), "seed": int(seed) + number}
        level, cause = own_wear(entry, levels)
        if level is not None:
            settings["wear"] = float(levels[level])
        name, colour = names[codes.index(entry["surface"])], tokens.get(entry["token"])
        found.append({"finish": entry["finish"], "parts": entry["parts"], "surface": name, "settings": settings,
                      "fits": bool(entry["fits"]), "new_surface": entry.get("new_surface"), "wear_level": level,
                      "wear_cause": cause, "family": surfaces[name].get("family"), "by": "the list",
                      "colour": None if colour is None else [round(float(value), 5) for value in colour]})
    if not found:
        raise ValueError("the finish list is empty")
    return found


def labels_of(answer, shown, count):
    """{view: {region: finish}} (0-based) of the answer's labels: only a region showing in its view and a finish of
    the list; the first label of a view's region stands."""
    found = {view: {} for view in shown}
    for label in answer["labels"]:
        view, region, finish = label["view"], int(label["region"]) - 1, int(label["finish"]) - 1
        if view in shown and region in shown[view] and 0 <= finish < count:
            found[view].setdefault(str(region), finish)
    return found


def regions_shown(folder, views):
    """{view: the regions (0-based) showing in it}, from the views row's regions.npz."""
    regions = np.load(folder / "regions.npz")
    return {view: sorted(int(region) for region in np.unique(regions[view]) if region >= 0) for view in views}


def labelled_views(folder, views):
    """The views a take's regions are labelled in: its views, and the laid close-up where the views row laid it."""
    laid = (folder / f"regions-{route_views.CLOSE_UP}.png").exists()
    return [*views, route_views.CLOSE_UP] if laid else list(views)


def pictures_of(folder, views):
    from PIL import Image
    laid = folder / f"regions-{route_views.CLOSE_UP}.png"
    return {"close_up": Image.open(folder / "close-up.png"),
            "shaded": [Image.open(folder / f"{view}.png") for view in views],
            "regions": [Image.open(folder / f"regions-{view}.png") for view in views],
            "laid": Image.open(laid) if laid.exists() else None,
            "shown": regions_shown(folder, labelled_views(folder, views))}


def ask(bodies):
    """The one batch of the row's asks: {take: answer text, or why there is none}."""
    return route_ask.asked(bodies, CALLER)


def listed(answer, library, seed, shown):
    """A take's list from its answer's text: (finishes, labels); a reply that does not parse raises."""
    parsed = json.loads(answer)
    finishes = finishes_of(parsed, library, seed)
    return finishes, labels_of(parsed, shown, len(finishes))


def unlabelled(finishes, labels):
    """The finishes (0-based) no region of any view is labelled with."""
    used = {finish for regions in labels.values() for finish in regions.values()}
    return [number for number in range(len(finishes)) if number not in used]


def follow_up(body, answer, finishes, missing):
    """`body` with its answer and the finishes it labels no region with after its question, in its one user turn."""
    told = copy.deepcopy(body)
    names = "; ".join(f"{number + 1} ({finishes[number]['finish']})" for number in missing)
    told["contents"][0]["parts"].append({"text": FOLLOW_UP.format(answer=answer, finishes=names)})
    return told


def followed_up(answers, bodies, reading):
    """{take: its follow-up's answer} of each take whose answer lists a finish it labels no region with in any view
    (unlabelled), asked once more in one batch (follow_up), its answer kept where it lists at least as many finishes
    and leaves fewer unlabelled: habitat's dining table listed its cloth runner and hangar's rack its hose, the
    split gave neither a face (#36, 2026-10-30). `reading(take, answer)` is the take's (finishes, labels)."""
    asking, first = {}, {}
    for take, answer in answers.items():
        finishes, labels = usable(reading, take, answer)
        missing = unlabelled(finishes, labels)
        if missing:
            asking[take], first[take] = follow_up(bodies[take], answer, finishes, missing), (len(finishes), len(missing))
    kept = {}
    for take, answer in (ask(asking) if asking else {}).items():
        finishes, labels = usable(reading, take, answer)
        if finishes and len(finishes) >= first[take][0] and len(unlabelled(finishes, labels)) < first[take][1]:
            kept[take] = answer
    return kept


def usable(reading, take, answer):
    """`reading`'s (finishes, labels) of a take's answer, or ([], {}) for no usable answer."""
    if isinstance(answer, Exception):
        return [], {}
    try:
        return reading(take, answer)
    except route_ask.UNANSWERED:
        return [], {}


def make_list(inputs, out, seed, params):
    """Every cast take's finish list and labels from one batch, and the finishes with their own wear. Each take is
    asked once, and once more where its answer lists a finish it labels no region with (followed_up); one with no
    usable answer gets no list, so judge_list names it a gap."""
    views = pathlib.Path(inputs["finish-route-views"])
    _, takes = route_data.takes_written(out, inputs, params)
    cast_takes = {take: record for take, record in json.loads((views / "views.json").read_text()).items()
                  if record.get("model")}
    palette = palette_library.read(inputs)
    tokens, levels = palette_tokens(palette), palette_library.scene_library(palette)["wear_levels"]
    wear = palette["wear"]["level"]
    surfaces = {take: palette_library.take_surfaces(takes[take], palette) for take in cast_takes}
    pictures = {take: pictures_of(views / take, record["views"]) for take, record in cast_takes.items()}
    bodies = {take: list_body(pictures[take], takes[take], record, (surfaces[take], tokens, levels), wear)
              for take, record in cast_takes.items()}
    answers = ask(bodies) if bodies else {}
    answers.update(followed_up(answers, bodies, lambda take, answer: listed(
        answer, (surfaces[take], tokens, levels), take_seed(seed, take), pictures[take]["shown"])))
    own, unanswered = [], {}
    for take in cast_takes:
        answer = answers.get(take, finish_ask.NoAnswer("the batch gave no answer"))
        try:
            if isinstance(answer, Exception):
                raise answer
            finishes, labels = listed(answer, (surfaces[take], tokens, levels),
                                      take_seed(seed, take), pictures[take]["shown"])
        except route_ask.UNANSWERED as error:
            unanswered[take] = f"no usable answer: {error!r}"[:300]
            continue
        (out / f"{take}.json").write_text(json.dumps({"take": take, "wear": wear, "finishes": finishes,
                                                      "labels": labels}, indent=1))
        own += [f"{take}: {entry['finish']}: {entry['wear_level']} ({entry['wear_cause']}; the scene's wear is {wear})"
                for entry in finishes if entry["wear_level"]]
    (out / "questions.json").write_text(json.dumps({"own_wear": own, "unanswered": unanswered}, indent=1))
    batch_gaps.write(out, [*batch_gaps.of(inputs), *list_gaps(out, cast_takes, unanswered, tokens)])


def list_gaps(out, cast_takes, unanswered, tokens):
    """The batch gap of each take the one list ask failed: no usable answer, or a list off the library (take_faults,
    the gate's own sorting); the split leaves it out."""
    found = []
    for take in cast_takes:
        if take in unanswered:
            found.append(batch_gaps.gap(f"{take}: no finish list", "finish-route-list", "library first", (take,),
                                        [f"{take}: {unanswered[take]}"], "the one list ask gave no usable answer"))
            continue
        faults = take_faults(take, json.loads((out / f"{take}.json").read_text())["finishes"], tokens)
        if faults:
            found.append(batch_gaps.gap(f"{take}: finish list off the library", "finish-route-list", "library first",
                                        (take,), faults, "the one list answer named finishes off the library"))
    return found


def list_faults(folder):
    return [] if (folder / "questions.json").exists() else ["no questions.json"]


def take_faults(take, finishes, tokens):
    """A listed take's finishes off the library: a token not the library's, a misfit proposing no surface."""
    failing = [f"{take}: {entry['finish']}: token {entry['settings']['token']} is not the library's"
               for entry in finishes if entry["settings"]["token"] not in tokens]
    return failing + [f"{take}: {entry['finish']}: does not fit and proposes no surface"
                      for entry in finishes if not entry["fits"] and not entry.get("new_surface")]


def judge_list(output, inputs, evidence):
    """Every cast take listed; every finish a library surface with a library token and settings 0-1; a finish that does
    not fit proposes a surface. The finishes with their own wear and the labels left out as measures."""
    cast_takes = [take for take, record in json.loads((pathlib.Path(inputs["finish-route-views"]) /
                                                       "views.json").read_text()).items() if record.get("model")]
    tokens = palette_tokens(palette_library.read(inputs))
    asked = json.loads((output / "questions.json").read_text())
    failing, unlabelled = [], 0
    for take in cast_takes:
        if not (output / f"{take}.json").exists():
            failing.append(f"{take}: no finish list" + (f" ({asked['unanswered'][take]})"
                                                         if take in asked["unanswered"] else ""))
            continue
        found = json.loads((output / f"{take}.json").read_text())
        failing += take_faults(take, found["finishes"], tokens)
        shown = regions_shown(pathlib.Path(inputs["finish-route-views"]) / take, found["labels"])
        unlabelled += sum(str(region) not in found["labels"][view] for view, regions in shown.items()
                          for region in regions)
    return gates.verdict("library first", failing, len(cast_takes), "takes off the library",
                         {"own_wear": len(asked["own_wear"]), "regions_unlabelled": unlabelled})
