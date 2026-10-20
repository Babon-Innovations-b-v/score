"""The finish route's list row (paid: one Gemini 3.1 Pro answer a take, all the place's takes in one batch at half
price, route_ask.py: asked once, an ask asked before read back free).

Gemini sees the take's close-up (its own, or the stand-in, said so in the question), every view of the model's own
texture and the same views split into the views row's colour regions, and gives in one answer the take's complete
finish list and a label for each region in each view. Each finish is matched FIRST to a surface of the library with
its settings: the palette token of its colour (one the library's variants or the places use), its shine (roughness,
metal) and its seed (the node's, one a finish); its wear is the place's one level (the room's wear rule, owner): a
finish that looks more or less worn says so in `wear_wish`, an owner question, never a setting. A new surface is
proposed only when no surface fits with any settings (`fits` false). Each region showing in a view is labelled with
the finish its part has there; the split votes the labels across views.

Output: <take>.json per take (its finishes, each with surface, settings, fits, new_surface, wear_wish; its labels,
{view: {region: finish}}, 0-based), questions.json (the wear wishes for the owner, the takes with no usable answer).
Gate "library first": every cast take is listed, every finish names a library surface with settings inside the
library's ranges, and one that does not fit proposes a surface; a take with no usable answer is a hole, named.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_ask  # noqa: E402
import finish_parts  # noqa: E402
import route_ask  # noqa: E402
import route_data  # noqa: E402
import surface_gates as gates  # noqa: E402

LIST_EUROS = 0.5  # a guess for the row's run (a place's takes at half of google_spend.ESTIMATES); never a price
CALLER = "finish-route-list"
QUESTION = """You help paint a 3D model with surfaces from a shared library. The object: {object}.
The first picture is {close_up}. The next {count} pictures show the model from every side ({views}) in its own
texture, shaded only by angle. The {count} after them show the same views with the model split into colour regions,
each region one flat colour, the same colour for the same region in every view:
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
any settings, set "fits" to false and propose a new library surface. Wear is the place's one level ({wear}); only if
a finish clearly looks more or less worn than that, say how in "wear_wish", else leave it empty.
Then label every region showing in every view with the finish (its number in your list, from 1) that the region's
part has in that view: one label for each view and region listed above."""


def library_tokens():
    """{token: linear RGB} of the palette tokens the library's variants and the places use."""
    import library
    every = library.token_colours()
    used = {variant["token"] for variant in library.variants(library.theme_library()).values()}
    places = json.loads(library.PLACES.read_text())
    used |= {entry["token"] for place in places.values() for entry in place.get("materials", {}).values()
             if isinstance(entry, dict) and "token" in entry}
    return {token: every[token] for token in sorted(used) if token in every}


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


def list_schema(surfaces, tokens, views):
    """The answer's schema: the finishes, each surface one of the surfaces' codes and token one of the tokens, and the
    labels, each a view, a region and a finish."""
    proposal = {"type": "OBJECT", "properties": {"name": {"type": "STRING"}, "description": {"type": "STRING"},
                                                 "why": {"type": "STRING"}}, "required": ["name", "description", "why"]}
    finish = {"type": "OBJECT",
              "properties": {"parts": {"type": "STRING"}, "finish": {"type": "STRING"},
                             "surface": {"type": "STRING", "enum": finish_ask.surface_codes(surfaces)},
                             "token": {"type": "STRING", "enum": list(tokens)},
                             "roughness": {"type": "NUMBER"}, "metal": {"type": "NUMBER"},
                             "fits": {"type": "BOOLEAN"}, "new_surface": proposal, "wear_wish": {"type": "STRING"}},
              "required": ["parts", "finish", "surface", "token", "roughness", "metal", "fits"],
              "propertyOrdering": ["parts", "finish", "surface", "token", "roughness", "metal", "fits", "new_surface",
                                   "wear_wish"]}
    label = {"type": "OBJECT", "properties": {"view": {"type": "STRING", "enum": list(views)},
                                              "region": {"type": "INTEGER"}, "finish": {"type": "INTEGER"}},
             "required": ["view", "region", "finish"]}
    return {"type": "OBJECT", "properties": {"finishes": {"type": "ARRAY", "items": finish},
                                             "labels": {"type": "ARRAY", "items": label}},
            "required": ["finishes", "labels"], "propertyOrdering": ["finishes", "labels"]}


def list_body(pictures, entry, record, library, wear):
    """The request: the close-up, the views, the region views, the question and its schema. `record` is the take's
    views record; `library` its surfaces and the tokens."""
    surfaces, tokens = library
    stand_in = record.get("close_up") == route_data.STAND_IN
    views = list(record["views"])
    text = QUESTION.format(object=entry["object"], close_up=(f"a {route_data.STAND_IN}" if stand_in
                                                             else "the object's close-up"),
                           count=len(views), views=", ".join(views), regions=region_lines(record["regions"]),
                           shown=shown_lines(pictures["shown"]), surfaces=surface_lines(surfaces),
                           tokens=token_lines(tokens), wear=wear)
    parts = [finish_ask.picture_part(pictures["close_up"], 1024)]
    parts += [finish_ask.picture_part(picture, 512) for picture in pictures["shaded"]]
    parts += [finish_ask.picture_part(picture, 512) for picture in pictures["regions"]]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": list_schema(surfaces, tokens, views)}}


def finishes_of(answer, surfaces, seed):
    """The answer's finishes: each surface by its library name, its settings clipped to 0-1 with the node's seed
    (one a finish)."""
    names, codes = list(surfaces), finish_ask.surface_codes(surfaces)
    found = []
    for number, entry in enumerate(answer["finishes"]):
        settings = {"token": entry["token"], "roughness": round(float(np.clip(entry["roughness"], 0, 1)), 3),
                    "metal": round(float(np.clip(entry["metal"], 0, 1)), 3), "seed": int(seed) + number}
        found.append({"finish": entry["finish"], "parts": entry["parts"], "surface": names[codes.index(entry["surface"])],
                      "settings": settings, "fits": bool(entry["fits"]), "new_surface": entry.get("new_surface"),
                      "wear_wish": (entry.get("wear_wish") or "").strip() or None, "by": "the list"})
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


def pictures_of(folder, views):
    from PIL import Image
    return {"close_up": Image.open(folder / "close-up.png"),
            "shaded": [Image.open(folder / f"{view}.png") for view in views],
            "regions": [Image.open(folder / f"regions-{view}.png") for view in views],
            "shown": regions_shown(folder, views)}


def ask(bodies):
    """The one batch of the row's asks: {take: answer text, or why there is none}."""
    return route_ask.asked(bodies, CALLER)


def listed(answer, surfaces, seed, shown):
    """A take's list from its answer's text: (finishes, labels); a reply that does not parse raises."""
    parsed = json.loads(answer)
    finishes = finishes_of(parsed, surfaces, seed)
    return finishes, labels_of(parsed, shown, len(finishes))


def make_list(inputs, out, seed, params):
    """Every cast take's finish list and labels from one batch, and the owner's questions. Each take is asked once; one
    with no usable answer gets no list, so judge_list names it a hole."""
    import library
    views = pathlib.Path(inputs["finish-route-views"])
    place, takes = route_data.takes_written(out, inputs, params)
    cast_takes = {take: record for take, record in json.loads((views / "views.json").read_text()).items()
                  if record.get("model")}
    tokens = library_tokens()
    wear = json.loads(library.PLACES.read_text())[place]["wear"]["level"]
    pictures = {take: pictures_of(views / take, record["views"]) for take, record in cast_takes.items()}
    bodies = {take: list_body(pictures[take], takes[take], record, (finish_parts.take_surfaces(takes[take]), tokens),
                              wear) for take, record in cast_takes.items()}
    answers = ask(bodies) if bodies else {}
    questions, unanswered = [], {}
    for take in cast_takes:
        answer = answers.get(take, finish_ask.NoAnswer("the batch gave no answer"))
        try:
            if isinstance(answer, Exception):
                raise answer
            finishes, labels = listed(answer, finish_parts.take_surfaces(takes[take]), seed, pictures[take]["shown"])
        except route_ask.UNANSWERED as error:
            unanswered[take] = f"no usable answer: {error!r}"[:300]
            continue
        (out / f"{take}.json").write_text(json.dumps({"take": take, "wear": wear, "finishes": finishes,
                                                      "labels": labels}, indent=1))
        questions += [f"{take}: {entry['finish']}: {entry['wear_wish']} (the place's wear is {wear})"
                      for entry in finishes if entry["wear_wish"]]
    (out / "questions.json").write_text(json.dumps({"wear_wishes": questions, "unanswered": unanswered}, indent=1))


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
    not fit proposes a surface. The owner's wear questions and the labels left out as measures."""
    cast_takes = [take for take, record in json.loads((pathlib.Path(inputs["finish-route-views"]) /
                                                       "views.json").read_text()).items() if record.get("model")]
    tokens = library_tokens()
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
                         {"wear_questions": len(asked["wear_wishes"]), "regions_unlabelled": unlabelled})
