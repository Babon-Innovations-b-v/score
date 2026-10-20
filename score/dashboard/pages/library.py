"""The Library screen (#42): the library's tree by kind with each branch's count, a branch's children only when it
opens (/api/library/children, a page at a time), and an item's own page: its picture, version, quality and files; and
an entry's full-screen 3D view."""
from urllib.parse import quote

from django.http import Http404
from django.shortcuts import render

from score.dashboard import state
from score.dashboard.pages import actions, library_actions
from score.dashboard.pages.models import is_owner
from score.dashboard.state import library as lib

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
    score = lib.percent(entry.score)
    return {"label": entry.title, "count": score, "tone": TONES.get(entry.state, "idle"), "href": lib.entry_url(entry),
            "picture": f"/library-files/thumbs/{entry.picture}.jpg" if entry.picture else None,
            "tip": f"{entry.state}, version {entry.version}" + (f", score {score}" if score is not None else "")}


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
    """One page of a folder's children as tree nodes: its sub-folders, else its entries; a "more" branch holds the
    next page. None for an unknown folder."""
    folders = shown.folders()
    node = node_by_id(folders["tree"], node_id)
    if node is None:
        return None
    rows = [folder_node(child) for child in node["children"]] or [
        item_node(entry) for entry in sorted(folders["members"][node_id], key=lambda entry: entry.title.lower())]
    shown_rows = rows[page * PAGE:(page + 1) * PAGE]
    left = len(rows) - (page + 1) * PAGE
    if left > 0:
        shown_rows.append({"label": "more", "count": left, "tone": "idle",
                           "children_url": children_url(node_id, page + 1)})
    return shown_rows


# --- one item --------------------------------------------------------------------------------------------------

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


def parts_of(entry):
    return [{"name": part["name"].replace("_", " "), "score": lib.percent(part["value"]), "how": part["how"]}
            for part in entry.score_parts]


def versions_of(shown, entry):
    return [{"version": other.version, "url": lib.entry_url(other), "tone": TONES.get(other.state, "idle")}
            for other in shown.entries() if other.kind == entry.kind and other.entry_id == entry.entry_id]


def takes_of(shown, entry):
    return [{"name": take.name.rsplit("/", 1)[-1], "url": f"/library-files/files/{take.sha}"}
            for take in entry.takes if shown.file_path(take.sha)]


def item_page(request, kind, entry_id, version):
    """An item's page: its picture, state, version and the other versions, its score and parts, its files, its takes,
    a link to its 3D view; the owner's lock, withdraw and refine."""
    shown, entry = found_entry(kind, entry_id, version)
    return render(request, "pages/library_item.html", {
        "entry": entry, "kind_label": lib.kind_label(entry.kind), "tone": TONES.get(entry.state, "idle"),
        "picture": f"/library-files/pictures/{entry.picture}.jpg" if entry.picture else None,
        "score": lib.percent(entry.score), "parts": parts_of(entry), "versions": versions_of(shown, entry),
        "more_files": entry.file_count - len(entry.files), "takes": takes_of(shown, entry),
        "three_d": lib.viewer_url(entry) if model_file(entry) else place_copy(entry),
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

