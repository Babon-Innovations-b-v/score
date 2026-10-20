"""The Library pages: the explorer (a tree of kinds and categories, the entries of the chosen one, the chosen entry
with its 3D view first) drawn in the browser from /api/library (api/library_api.py), and an entry's full-screen 3D view.
What the API answers is made here."""
from urllib.parse import quote

from django.http import Http404
from django.shortcuts import render

from score.dashboard import state
from score.dashboard.pages import actions, library_actions
from score.dashboard.state import library as lib

WEB_COPY_KINDS = ("model", "kit", "character")  # the kinds whose web GLB copies are being made for the viewer
SORTS = ("name", "score_low", "score_high")
BANDS = {"low": (0, 50), "mid": (50, 80), "high": (80, 101)}  # a score's band, its percent from and below


def thumb_url(entry):
    return f"/library-files/thumbs/{entry.picture}.jpg" if entry.picture else None


def missing_words():
    if actions.hosted():
        return "No library has arrived with the state export yet."
    return "No library is set for this cockpit: set SCORE_LIB_ROOT to the library's folder."


def first_view(request):
    """Where the explorer opens: the folder, entry, place and words in the page's query."""
    return {name: request.GET.get(name, "").strip() for name in ("node", "entry", "place", "q")}


def library_page(request):
    shown = lib.library()
    if shown is None or not shown.entries():
        return render(request, "pages/library.html", {"missing": missing_words()})
    every = shown.entries()
    return render(request, "pages/library.html", {
        "total": len(every), "locked": sum(1 for entry in every if entry.state == "locked"),
        "first_view": first_view(request)})


# --- the tree and a folder's entries ---------------------------------------------------------------------------

def tree_of(shown):
    """The explorer's tree, the places entries came from, and the totals."""
    every = shown.entries()
    return {"tree": shown.folders()["tree"], "places": lib.places_of(every), "states": list(lib.STATES),
            "total": len(every), "locked": sum(1 for entry in every if entry.state == "locked")}


def in_band(entry, band):
    """True when an entry's score is in the band (low, mid, high), or it has none and the band is "none"."""
    percent = lib.percent(entry.score)
    if band == "none":
        return percent is None
    low, below = BANDS[band]
    return percent is not None and low <= percent < below


def sorted_by(entries, sort):
    """By name, or by score worst or best first (the unscored last either way)."""
    if sort == "name":
        return sorted(entries, key=lambda entry: (entry.title.lower(), entry.version))
    worst_first = sort == "score_low"
    return sorted(entries, key=lambda entry: (entry.score is None,
                                              (lib.percent(entry.score) or 0) * (1 if worst_first else -1),
                                              entry.title.lower()))


def band_counts(entries):
    return {band: sum(1 for entry in entries if in_band(entry, band)) for band in (*BANDS, "none")}


def row(entry, asked):
    """One entry as the folder's list shows it."""
    return {"address": entry.address, "title": entry.title, "kind": entry.kind, "state": entry.state,
            "thumb": thumb_url(entry), "score": lib.percent(entry.score), "place": entry.place,
            "has3d": bool(model_file(entry)), "waits3d": entry.kind in WEB_COPY_KINDS and not model_file(entry),
            "refine": entry.refine_options, "asked": asked.get(entry.address)}


def folder_entries(shown, node, place="", entry_state="", words=""):
    """The entries of one folder (the whole library for none) that pass the filters; None for an unknown folder."""
    members = shown.folders()["members"].get(node) if node else shown.entries()
    return None if members is None else lib.filtered(members, place=place, state=entry_state, words=words)


def folder_list(shown, node, filters):
    """A folder's rows, sorted and narrowed to a score band, with how many each band holds; None for no folder."""
    found = folder_entries(shown, node, filters["place"], filters["state"], filters["q"])
    if found is None:
        return None
    counts = band_counts(found)
    if filters["band"] in (*BANDS, "none"):
        found = [entry for entry in found if in_band(entry, filters["band"])]
    asked = library_actions.waiting()
    sort = filters["sort"] if filters["sort"] in SORTS else "name"
    return {"node": node, "count": len(found), "bands": counts, "sort": sort,
            "entries": [row(entry, asked) for entry in sorted_by(found, sort)]}


# --- one entry -------------------------------------------------------------------------------------------------

def step_link(node):
    """{label, url} of the step that made an entry, the url only when the cockpit holds that step."""
    if not node:
        return None
    place, stage = lib.step_of(node)
    held = state.source().step_detail(place, stage) is not None
    return {"label": stage.replace("-", " ").replace("_", " "), "url": lib.step_url(node) if held else None}


def place_link(place):
    if not place:
        return None
    return {"label": place.replace("_", " "), "url": f"/place/{place}/" if place in state.source().places() else None}


def model_file(entry):
    """The GLB the viewer opens for an entry: its web copy, else its own GLB, when this cockpit holds it."""
    shown = lib.library()
    return next((each for each in (entry.web3d, entry.glb) if each and shown.file_path(each.sha)), None)


def place_copy(entry):
    """A place entry's own 3D web copy in the cockpit's viewer, or None."""
    source = state.source()
    if entry.kind == "place" and entry.entry_id in source.places() and source.web3d(entry.entry_id):
        return f"/view/{entry.entry_id}"
    return None


def three_d(entry):
    """What the entry's 3D view opens: its GLB, a surface's finish, a place's copy; or that a copy is on its way."""
    found = model_file(entry)
    if found:
        return {"model": f"/library-files/files/{found.sha}", "bytes": found.bytes,
                "web_copy": found is entry.web3d, "full": lib.viewer_url(entry)}
    if entry.kind == "surface" and entry.finish and "colour" in entry.finish:
        printed = entry.finish.get("print")
        shown_print = printed and lib.library().file_path(printed["sha"])
        return {"finish": {name: value for name, value in entry.finish.items() if name != "print"},
                "print": f"/library-files/files/{printed['sha']}" if shown_print else None}
    if place_copy(entry):
        return {"place": place_copy(entry)}
    return {"waiting": True} if entry.kind in WEB_COPY_KINDS else None


def requirement_links(entry, shown):
    return [{"address": address, "title": shown.entry(address).title if shown.entry(address) else address,
             "known": shown.entry(address) is not None} for address in entry.requires]


def versions_of(entry, shown):
    return [{"address": other.address, "version": other.version, "state": other.state}
            for other in shown.entries() if other.kind == entry.kind and other.entry_id == entry.entry_id]


def takes_of(entry, shown):
    return [{"name": take.name.rsplit("/", 1)[-1], "url": f"/library-files/files/{take.sha}"}
            for take in entry.takes if shown.file_path(take.sha)]


def quality_of(entry):
    """The entry's score, its parts (each as a percent) and its refine options."""
    return {"score": lib.percent(entry.score), "refine": entry.refine_options,
            "parts": [{"name": part["name"].replace("_", " "), "score": lib.percent(part["value"]), "how": part["how"]}
                      for part in entry.score_parts]}


def entry_detail(shown, entry):
    """Everything the explorer's entry panel shows."""
    return {"address": entry.address, "title": entry.title, "kind": entry.kind,
            "kind_label": lib.kind_label(entry.kind), "state": entry.state, "locked": entry.locked,
            "sentence": lib.sentence(entry),
            "picture": f"/library-files/pictures/{entry.picture}.jpg" if entry.picture else None,
            "three_d": three_d(entry), "takes": takes_of(entry, shown), "world": entry.world,
            "place": place_link(entry.place), "step": step_link(entry.node), "source": entry.source,
            "seen_in": [place_link(place) for place in entry.seen_in], "requires": requirement_links(entry, shown),
            "versions": versions_of(entry, shown), "quality": quality_of(entry),
            "asked": library_actions.waiting().get(entry.address),
            "ids": {"node": entry.node, "commit": entry.commit, "tags": entry.tags}}


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
    return render(request, "pages/library_view3d.html", {"entry": entry, "bytes": found.bytes, "back": quote(
        entry.address), "viewer": {"place": found.sha, "base": "/library-files/view/", "layers": {}, "order": []}})


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

