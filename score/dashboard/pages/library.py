"""The Library screen (#42): the library's tree by kind with each branch's count, a branch's children only when it
opens (/api/library/children, a page at a time), and an item's own page: the item itself in its kind's viewer
(turned, played or lit; `viewer_of`) with a few numbers of its kind (`numbers_of`); and an entry's full-screen 3D
view."""
from urllib.parse import quote

from django.http import Http404
from django.shortcuts import render

from score.dashboard import state
from score.dashboard.pages import actions, library_actions
from score.dashboard.pages.models import is_owner
from score.dashboard.state import library as lib
from score.dashboard.state.files import HERO_SIDE

PAGE = 60  # a branch's children sent at a time
TONES = {"locked": "done", "draft": "review", "withdrawn": "idle"}


def thumb_url(entry):
    return f"/library-files/thumbs/{entry.picture}.jpg" if entry.picture else None


def missing_words():
    if actions.hosted():
        return "No library has arrived with the state export yet."
    return "No library is set for this cockpit: set SCORE_LIB_ROOT to the library's folder."


def library_page(request):
    """Screen 5: the tree of kinds (each opened lazily) beside each state's count."""
    shown = lib.library()
    if shown is None or not shown.entries():
        return render(request, "pages/library.html", {"missing": missing_words()})
    every = shown.entries()
    return render(request, "pages/library.html", {
        "nodes": kind_nodes(shown), "total": len(every),
        "states": [{"label": name, "tone": TONES[name], "count": sum(entry.state == name for entry in every)}
                   for name in lib.STATES]})


# --- the tree, a branch at a time ------------------------------------------------------------------------------

def children_url(node_id, page=0):
    return f"/api/library/children?node={quote(node_id)}" + (f"&page={page}" if page else "")


def kind_nodes(shown):
    """Every kind with its count; a kind with entries opens to its children."""
    members = shown.folders()["members"]
    nodes = []
    for kind, label in lib.KINDS:
        count = len(members.get(kind, []))
        nodes.append({"label": label, "count": count, "tone": "done" if count else "idle", "tip": lib.WHAT[kind],
                      "children_url": children_url(kind) if count else None})
    return nodes


def folder_node(node):
    return {"label": node["label"], "count": node["count"], "tone": "idle", "children_url": children_url(node["id"])}


def item_node(entry):
    """An entry as a tree leaf: its state's dot, its thumbnail, its name, its score; a link to its page."""
    means = lib.score_meaning(entry)
    score = lib.percent(entry.score) if means else None
    return {"label": entry.title, "count": score, "tone": TONES.get(entry.state, "idle"), "href": lib.entry_url(entry),
            "picture": f"/library-files/thumbs/{entry.picture}.jpg" if entry.picture else None,
            "tip": (f"{entry.about}; " if entry.about else "") + f"{entry.state}, version {entry.version}"
            + (f"; score {score}: {means}" if score is not None else "")}


def node_by_id(tree, node_id):
    """A folder of the tree by its id, or None."""
    waiting = list(tree)
    while waiting:
        node = waiting.pop()
        if node["id"] == node_id:
            return node
        waiting.extend(node["children"])
    return None


def children(shown, node_id, page=0):
    """One page of a folder's children as tree nodes: its sub-folders, then its entries no sub-folder holds; a "more"
    branch holds the next page. None for an unknown folder."""
    folders = shown.folders()
    node = node_by_id(folders["tree"], node_id)
    if node is None:
        return None
    held = {entry.address for child in node["children"] for entry in folders["members"][child["id"]]}
    loose = [entry for entry in folders["members"][node_id] if entry.address not in held]
    rows = [folder_node(child) for child in node["children"]] + [
        item_node(entry) for entry in sorted(loose, key=lambda entry: entry.title.lower())]
    shown_rows = rows[page * PAGE:(page + 1) * PAGE]
    left = len(rows) - (page + 1) * PAGE
    if left > 0:
        shown_rows.append({"label": "more", "count": left, "tone": "idle",
                           "children_url": children_url(node_id, page + 1)})
    return shown_rows


# --- one item --------------------------------------------------------------------------------------------------

def model_file(entry):
    """The GLB the viewer opens for an entry: its web copy, else its own GLB, else its light copy, when this cockpit
    holds it."""
    shown = lib.library()
    return next((each for each in (entry.web3d, entry.glb, entry.web3d_light) if each and shown.file_path(each.sha)),
                None)


def place_of(entry):
    """The place a place or layer entry shows: a place's own id, a layer's place."""
    return entry.entry_id if entry.kind == "place" else entry.place


def place_copy(entry):
    """A place or layer entry's place 3D web copy in the cockpit's viewer, or None."""
    source = state.source()
    place = place_of(entry) if entry.kind in ("place", "layer") else None
    if place and place in source.places() and source.web3d(place):
        return f"/view/{place}"
    return None


def found_entry(kind, entry_id, version):
    shown = lib.library()
    entry = shown.entry(f"{kind}/{entry_id}@{version}") if shown else None
    if entry is None:
        raise Http404(f"no library entry {kind}/{entry_id}@{version}")
    return shown, entry


def entry_viewer(request, kind, entry_id, version):
    """An entry's GLB full screen in the cockpit's 3D viewer, with its measuring tools."""
    _, entry = found_entry(kind, entry_id, version)
    found = model_file(entry)
    if found is None:
        raise Http404("this entry has no 3D file here")
    return render(request, "pages/library_view3d.html", {"entry": entry, "bytes": found.bytes, "back": lib.entry_url(
        entry), "viewer": {"place": found.sha, "base": "/library-files/view/", "layers": {}, "order": []}})


def score_tip(entry):
    """What the score measures, then its parts, as hover text: "how sound its mesh is: ...; holes 100, seams 92"."""
    parts = ", ".join(f"{part['name'].replace('_', ' ')} "
                      + (str(lib.percent(part["value"])) if part["value"] is not None else "not measured")
                      for part in entry.score_parts)
    return "; ".join(each for each in (lib.score_meaning(entry), parts) if each)


def versions_of(shown, entry):
    return [{"version": other.version, "url": lib.entry_url(other), "tone": TONES.get(other.state, "idle")}
            for other in shown.entries() if other.kind == entry.kind and other.entry_id == entry.entry_id]


def takes_of(shown, entry):
    return [{"name": take.name.rsplit("/", 1)[-1], "url": f"/library-files/files/{take.sha}"}
            for take in entry.takes if shown.file_path(take.sha)]


# --- each kind's viewer and numbers ------------------------------------------------------------------------------

PLAYED = {"surface": "surface", "effect": "effect", "light": "sky", "lamp": "light"}  # item3d.js draws these from facts


def file_url(shown, each):
    return f"/library-files/files/{each.sha}" if each and shown.file_path(each.sha) else None


def played(entry):
    """Whether this cockpit has what item3d.js draws a surface, effect, sky or lamps from: its finish, settings, its
    sky picture, or its lamps."""
    return {"surface": bool((entry.finish or {}).get("colour")), "effect": bool(entry.facts.get("settings")),
            "light": bool(entry.facts.get("sky") and entry.picture), "lamp": bool(entry.facts.get("lamps"))}[shelf(entry)]


def shelf(entry):
    return entry.shelf or entry.kind


def played_as(entry):
    """The kind an entry's viewer and numbers follow: its shelf's, but code is shown as code on any shelf."""
    return entry.kind if entry.kind == "algorithm" else shelf(entry)


def view_of(shown, entry):
    """Which viewer the page holds: 3d (item3d.js), sound (takes.js), demo (an algorithm's work on a real example,
    demo.js), diagram (what an algorithm reads and makes, while it has no example), place (the place viewer in a
    frame) or picture (what it plays is not in this cockpit)."""
    if entry.kind == "sound":
        return "sound"
    if entry.kind == "algorithm":
        return "demo" if "missing" not in (shown.demo(entry.entry_id) or {"missing": ""}) else "diagram"
    if shelf(entry) in PLAYED:
        return "3d" if played(entry) else "picture"
    if entry.kind in ("place", "layer"):
        return "place" if place_copy(entry) else "picture"
    if file_url(shown, entry.web3d_light) or file_url(shown, entry.web3d):
        return "3d"
    return "picture"


VIEWER_FILES = {"surface": (".usda",), "effect": ("settings.json",), "light": (".usda",)}


def viewer_names(entry):
    """The names of the files an entry's viewer plays: its copies, its takes, its material, settings or OpenUSD."""
    ends = VIEWER_FILES.get(entry.kind, ())
    return [each.name for each in (entry.web3d_light, entry.web3d, *entry.takes) if each] + [
        listed.name for listed in entry.files if ends and listed.name.endswith(ends)]


def absent(missing, names):
    """How a file the page cannot show is said: missing when the library's blob store lost it, else not here."""
    return "missing" if any(name in missing for name in names) else "not here"


def picture_url(shown, entry):
    """The entry's large picture when this cockpit holds it, else None."""
    held = entry.picture and shown.picture_path(entry.picture, HERO_SIDE)
    return f"/library-files/pictures/{entry.picture}.jpg" if held else None


def closeup_url(shown, entry):
    """A model's close-up, the picture it was made from, when this cockpit holds it, else None."""
    held = entry.closeup and shown.picture_path(entry.closeup.sha, HERO_SIDE)
    return f"/library-files/pictures/{entry.closeup.sha}.jpg" if held else None


def viewer_of(shown, entry):
    """What item3d.js plays: {mode (copy, kit, surface, effect, light), light (the light copy's url), full (the whole
    copy's, when this cockpit holds it), finish, print, token, palette, settings, lamps, inside (a kit cut open)}."""
    mode = "kit" if entry.kind == "kit" else PLAYED.get(played_as(entry), "copy")
    found = {"mode": mode, "light": file_url(shown, entry.web3d_light), "full": file_url(shown, entry.web3d)}
    if mode == "surface":
        printed = (entry.finish or {}).get("print")
        found.update(finish=entry.finish or {}, token=entry.facts.get("token"), palette=lib.palette(),
                     print=file_url(shown, lib.FileOf.model_validate(printed)) if printed else None)
    elif mode == "effect":
        found["settings"] = entry.facts.get("settings")
    elif mode == "light":
        found["lamps"] = entry.facts.get("lamps") or []
    elif mode == "kit":
        found["inside"] = "inside" in entry.tags.get("place_kind", [])
    elif mode == "sky":
        found.update(sky=entry.facts.get("sky"), picture=picture_url(shown, entry))
    return found


def number(label, value, unit="", tip=None, fact=None, unknown="not in the library's record"):
    """One number card's arguments (pages/c/number.html); `fact` names a value item3d.js fills once it is loaded."""
    return {"label": label, "value": value, "unit": unit, "tip": tip, "fact": fact, "unknown": unknown}


def lamp_numbers(lamps):
    brightest = max(lamps, key=lambda lamp: lamp["power"], default=None)
    if brightest is None:
        return [number("temperature", None, "K"), number("power", None)]
    return [number("temperature", brightest["kelvin"], "K", f"{brightest['name']}: from its colour unless it sets one"),
            number("power", brightest["power"], "", f"{brightest['name']}: intensity times 2 to its exposure")]


def tenths(value):
    return round(value, 1) if isinstance(value, (int, float)) else value


def effect_numbers(settings):
    settings = settings or {}
    loop = settings.get("loop")
    return [number("length", tenths(settings.get("lifetime")), "s", "a card's life"),
            number("loop", tenths(loop) if loop else ("no" if "loop" in settings else None), "s" if loop else "",
                   "it plays again after this long")]


def numbers_of(entry, copy_here):
    """The few numbers of an item's kind, its hover text with each; a value item3d.js reads off the loaded copy
    (size, clips) starts unknown, and is left out while its copy is not here (`copy_here`)."""
    facts = entry.facts
    size = [number("size", None, "m", "width, height and depth of its copy", "size", "measured once its copy loads")]
    clips = [number("clips", None, "", "clips its copy plays", "clips", "counted once its copy loads")]
    size, clips = (size, clips) if copy_here else ([], [])
    parts = number("parts", facts.get("parts"), "", "objects in its web copy")
    by_kind = {
        "model": [*size, parts], "kit": [number("pieces", facts.get("parts"), "", "pieces in its kit"), *size],
        "character": [parts, *clips],
        "place": [parts],
        "surface": [number("token", facts.get("token"), "", "its palette token")],
        "sound": [number("loudness", facts.get("lufs"), "LUFS", "integrated loudness"),
                  number("length", facts.get("seconds"), "s", "its first take")],
        "effect": effect_numbers(facts.get("settings")), "lamp": lamp_numbers(facts.get("lamps") or [])}
    return by_kind.get(played_as(entry), [])


def demo_of(shown, entry):
    """An algorithm's demo, or None while it has none."""
    found = shown.demo(entry.entry_id) if entry.kind == "algorithm" else None
    return found if found and "missing" not in found else None


def diagram_of(shown, entry):
    """What an algorithm reads and makes, for the plain diagram shown while it has no example: {reads, makes, steps,
    why (hover text: why there is no example)}."""
    found = shown.demo(entry.entry_id) or {"missing": "its example has not been made on the store's machine yet"}
    stage = entry.facts.get("stage") or "its output"
    return {"reads": entry.facts.get("reads") or [], "makes": stage.replace("-", " "),
            "steps": entry.facts.get("steps") or 0, "why": found.get("missing", "")}


def step_labels(demo):
    """The names of a demo's steps, in order: a relief's, else its shapes'."""
    steps = (demo.get("relief") or {}).get("steps") if demo.get("view") == "relief" else demo.get("steps")
    return [step["label"] for step in steps or []]


def demo_numbers(demo):
    return [number(each["label"], each.get("value"), each.get("unit", ""), each.get("tip")) for each in
            (demo or {}).get("numbers", [])[:4]]


def item_page(request, kind, entry_id, version):
    """An item's page: the item in its kind's viewer, a few numbers of its kind and its score, its versions, a link
    to its full-screen 3D view; the owner's lock, withdraw and refine."""
    shown, entry = found_entry(kind, entry_id, version)
    missing, view = shown.missing(entry), view_of(shown, entry)
    return render(request, "pages/library_item.html", {
        "entry": entry, "kind_label": lib.kind_label(shelf(entry)), "made_by_code": lib.made_by_code(entry),
        "tone": TONES.get(entry.state, "idle"),
        "picture": picture_url(shown, entry), "picture_absent": absent(missing, [entry.picture_file]),
        "closeup": closeup_url(shown, entry),
        "absent": absent(missing, viewer_names(entry)),
        "score": lib.percent(entry.score) if lib.score_meaning(entry) else None,
        "score_tip": score_tip(entry), "versions": versions_of(shown, entry),
        "view": view, "viewer": viewer_of(shown, entry),
        "numbers": numbers_of(entry, view == "3d") + demo_numbers(demo_of(shown, entry)),
        "demo": demo_of(shown, entry), "steps": step_labels(demo_of(shown, entry) or {}), "diagram": diagram_of(shown, entry) if view == "diagram" else None,
        "takes": takes_of(shown, entry), "place": place_copy(entry),
        "three_d": lib.viewer_url(entry) if model_file(entry) else None,
        "owner": is_owner(request.user), "asked": library_actions.waiting().get(entry.address)})


# --- the basket's refine items --------------------------------------------------------------------------------

def refine_cards(items):
    """The basket's refine items with each entry's picture and name, and the option in words."""
    shown = lib.library()
    cards = []
    for item in items:
        found = shown.entry(item.address) if shown else None
        options = {choice["id"]: choice["label"] for choice in (found.refine_options if found else [])}
        cards.append({"pk": item.pk, "address": item.address, "title": found.title if found else item.address,
                      "thumb": thumb_url(found) if found else None, "url": lib.entry_url(found) if found else None,
                      "option": options.get(item.option, item.option) or "as its scoring suggests",
                      "score": lib.percent(found.score) if found else None})
    return cards

