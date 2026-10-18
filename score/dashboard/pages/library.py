"""The Library pages: the library's entries as a picture grid by kind with search and filters, an entry's own page,
its 3D view, the owner's lock and withdraw (pages/library_actions.py), and the strip of a place's entries."""
from urllib.parse import urlencode

from django.contrib import messages
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from score.dashboard import state
from score.dashboard.pages import actions, library_actions
from score.dashboard.pages.models import is_owner
from score.dashboard.state import library as lib

GROUP_SHOWN = 12  # tiles a kind shows on the overview
PAGE_SHOWN = 120  # tiles one kind's page shows
STRIP_SHOWN = 12


def tile(entry, asked):
    """What one grid tile shows."""
    return {"entry": entry, "url": lib.entry_url(entry), "asked": asked.get(entry.address),
            "thumb": f"/library-files/thumbs/{entry.picture}.jpg" if entry.picture else None}


def chosen_filters(request):
    """The page's filters from its query: kind, place, state, words."""
    found = {name: request.GET.get(name, "").strip() for name in ("kind", "place", "state", "q")}
    found["kind"] = found["kind"] if found["kind"] in dict(lib.KINDS) else ""
    found["state"] = found["state"] if found["state"] in lib.STATES else ""
    return found


def query_with(filters, **changed):
    """The query string of these filters with some changed (empty ones left out)."""
    merged = {**filters, **changed}
    return urlencode({name: value for name, value in merged.items() if value})


def kind_groups(found, filters, asked):
    """The overview: each kind with its first tiles and how many there are."""
    groups = []
    for kind, label in lib.KINDS:
        of_kind = [entry for entry in found if entry.kind == kind]
        if of_kind:
            groups.append({"kind": kind, "label": label, "total": len(of_kind),
                           "tiles": [tile(entry, asked) for entry in of_kind[:GROUP_SHOWN]],
                           "all_url": "?" + query_with(filters, kind=kind)})
    return groups


def one_kind(found, filters, asked, page):
    """One kind's page of tiles, with the links to the pages before and after."""
    start = (page - 1) * PAGE_SHOWN
    shown = found[start:start + PAGE_SHOWN]
    return [{"kind": filters["kind"], "label": lib.kind_label(filters["kind"]), "total": len(found),
             "tiles": [tile(entry, asked) for entry in shown],
             "before": "?" + query_with(filters, page=str(page - 1)) if page > 1 else None,
             "after": "?" + query_with(filters, page=str(page + 1)) if start + PAGE_SHOWN < len(found) else None,
             "first": start + 1, "last": start + len(shown)}]


def page_number(request):
    try:
        return max(1, int(request.GET.get("page", "1")))
    except ValueError:
        return 1


def missing_words():
    if actions.hosted():
        return "No library has arrived with the state export yet."
    return "No library is set for this cockpit: set SCORE_LIB_ROOT to the library's folder."


def library_page(request):
    shown = lib.library()
    if shown is None or not shown.entries():
        return render(request, "pages/library.html", {"missing": missing_words()})
    every = shown.entries()
    filters = chosen_filters(request)
    found = lib.filtered(every, filters["kind"], filters["place"], filters["state"], filters["q"])
    asked = library_actions.waiting()
    groups = (one_kind(found, filters, asked, page_number(request)) if filters["kind"]
              else kind_groups(found, filters, asked))
    counts = {kind: sum(1 for entry in every if entry.kind == kind) for kind, _ in lib.KINDS}
    return render(request, "pages/library.html", {
        "groups": groups, "filters": filters, "found": len(found), "total": len(every),
        "kinds": [(kind, label, counts[kind]) for kind, label in lib.KINDS if counts[kind]],
        "places": lib.places_of(every), "states": lib.STATES,
        "locked": sum(1 for entry in every if entry.state == "locked"), "back": request.get_full_path()})


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


def three_d(entry):
    """Where the entry opens in 3D: a place's own web copy, or the entry's GLB here; None when it cannot."""
    source = state.source()
    if entry.kind == "place" and entry.entry_id in source.places() and source.web3d(entry.entry_id):
        return f"/view/{entry.entry_id}"
    if entry.glb and lib.library().file_path(entry.glb.sha):
        return lib.entry_url(entry) + "3d/"
    return None


def requirement_links(entry, shown):
    return [{"address": address, "url": lib.entry_url(shown.entry(address)) if shown.entry(address) else None,
             "title": shown.entry(address).title if shown.entry(address) else address} for address in entry.requires]


def found_entry(kind, entry_id, version):
    shown = lib.library()
    entry = shown.entry(f"{kind}/{entry_id}@{version}") if shown else None
    if entry is None:
        raise Http404(f"no library entry {kind}/{entry_id}@{version}")
    return shown, entry


def entry_page(request, kind, entry_id, version):
    shown, entry = found_entry(kind, entry_id, version)
    others = [other for other in shown.entries() if other.kind == kind and other.entry_id == entry_id]
    return render(request, "pages/library_entry.html", {
        "entry": entry, "sentence": lib.sentence(entry), "kind_label": lib.kind_label(kind),
        "picture": f"/library-files/pictures/{entry.picture}.jpg" if entry.picture else None,
        "takes": [{"name": take.name.rsplit("/", 1)[-1], "url": f"/library-files/files/{take.sha}"}
                  for take in entry.takes if shown.file_path(take.sha)],
        "open3d": three_d(entry), "step": step_link(entry.node), "place": place_link(entry.place),
        "seen_in": [place_link(place) for place in entry.seen_in], "requires": requirement_links(entry, shown),
        "versions": [{"version": other.version, "state": other.state, "url": lib.entry_url(other)} for other in others],
        "asked": library_actions.waiting().get(entry.address), "back": request.get_full_path()})


def entry_viewer(request, kind, entry_id, version):
    """An entry's GLB in the cockpit's 3D viewer."""
    shown, entry = found_entry(kind, entry_id, version)
    if not entry.glb or not shown.file_path(entry.glb.sha):
        raise Http404("this entry has no 3D file here")
    return render(request, "pages/library_view3d.html", {"entry": entry, "viewer": {
        "place": entry.glb.sha, "base": "/library-files/view/", "layers": {}, "order": []}})


@require_POST
def ask(request):
    """The owner's lock or withdraw of the chosen entries."""
    if not is_owner(request.user):
        return HttpResponseForbidden("only the owner locks or withdraws library entries")
    said = library_actions.ask(request.user.username, request.POST.get("action", ""),
                               request.POST.getlist("address"), actions.hosted())
    (messages.error if said.startswith(("refused", "nothing")) else messages.success)(request, said)
    back = request.POST.get("back", "")
    return redirect(back if back.startswith("/library/") and not back.startswith("//") else "/library/")


def strip_of(place):
    """The place page's "In the library" strip: its entries' first tiles and how many there are, or None."""
    shown = lib.library()
    if shown is None:
        return None
    found = lib.from_place(shown.entries(), place)
    if not found:
        return None
    counts = [(kind, sum(1 for entry in found if entry.kind == kind)) for kind, _ in lib.KINDS]
    return {"total": len(found), "kinds": [lib.counted_kind(kind, count) for kind, count in counts if count],
            "tiles": [tile(entry, {}) for entry in lib.kinds_mixed(found)[:STRIP_SHOWN]],
            "url": f"/library/?place={place}"}
