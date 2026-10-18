"""The owner's named gaps of a place (data/checks/gaps/<place>.json), each with its step and a picture of what it
names, for the local source only (it reads the store and draws through previews/, which a hosted process never
imports): the named things ringed in the frame of the place's accepted film that shows them best, else ringed on the
place's plan, else the picture of the step the gap was named at. Free and light: no render, one ffmpeg frame. Each
picture is made once per (film, stage, plan, names) and kept under <home>/previews/<VERSION>/gaps/; a gap whose
things stand nowhere keeps a `.none` mark there, so it is not looked for again."""
import hashlib
import json
import re
import threading

from score.dashboard.state import groups, plain
from score.dashboard.state.files import file_ref
from score.dashboard.state.models import NamedGap

IN_FILM, ON_PLAN, STEP_PICTURE = "ringed in the film", "ringed on the plan", "its step's picture"
THE_PLACE, THE_LAYOUT = "the place in its film", "the place's layout"
LAYOUT_CHECKS = ("game",)  # a gap about where things stand is pictured by the plan
SHOWN = {".jpg": IN_FILM, ".png": ON_PLAN}
MOST_RINGS = 8
NAME = "gap{suffix}"
_one_at_a_time = threading.Lock()


def entries(data, place):
    """The place's named gaps as written, [] when it has none."""
    path = data / "checks/gaps" / f"{place}.json"
    return json.loads(path.read_text())["gaps"] if path.exists() else []


def named_gaps(source, place):
    """Every named gap of the place with its step and its picture."""
    rows = {row.name for row in source.place_rows(place)}
    return [named_gap(source, place, entry, rows) for entry in entries(source.data, place)]


def named_gap(source, place, entry, rows):
    row = entry.get("row")
    objects = [item for item in entry.get("objects") or [] if isinstance(item, str)]
    picture, words = gap_picture(source, place, objects) if objects else (None, "")
    if picture is None:
        picture, words = unnamed_picture(source, place, row, entry.get("check"))
    return NamedGap(name=entry["name"], sentence=plain.gap_sentence(entry, place), reason=entry.get("reason", ""),
                    step=row, step_label=groups.label(row) if row else None,
                    step_url=f"/place/{place}/step/{row}/" if row in rows else None, objects=objects,
                    picture=picture, picture_is=words if picture else "")


def unnamed_picture(source, place, row, check):
    """(FileRef, words) for a gap whose things stand nowhere: its step's own picture when it made one, the plan
    for a gap about the layout, else the place in its film, else whatever its step's picture is."""
    found = own_picture(source, place, row)
    if found:
        return found, STEP_PICTURE
    if check in LAYOUT_CHECKS:
        found = step_picture(source, place, "plan")
        if found:
            return found, THE_LAYOUT
    found = source.still(place) or source.hero(place)
    if found:
        return found, THE_PLACE
    return step_picture(source, place, row), STEP_PICTURE


def own_picture(source, place, row):
    """The image a step's shown output made of its own, or None (a drawn preview is not one)."""
    if not row:
        return None
    record = source.shown_record(source.node_of(row, place))
    return source.own_image(record["output"]) if record else None


def step_picture(source, place, row):
    """The picture of a step at the place (its shown output's own image, else one drawn from its files), or None."""
    if not row:
        return None
    node = source.node_of(row, place)
    record = source.shown_record(node)
    return source.picture_of(node, record["output"]) if record else None


def gap_id(source, place, objects):
    """The 64-hex id of a gap's picture: what it is drawn from (the film, the stage, the plan) and the names."""
    from score.dashboard import previews
    film = source.film(place)
    made_from = [previews.VERSION, film.sha if film else "", source.accepted_output(f"assembly@{place}") or "",
                 source.accepted_output(f"plan@{place}") or "", *objects]
    return hashlib.sha256(("score-dashboard-gap:" + "\n".join(made_from)).encode()).hexdigest()


def gap_picture(source, place, objects):
    """(FileRef, words) of the gap's named things ringed, kept or drawn now; (None, "") when they stand nowhere."""
    from score.dashboard import previews
    ident = gap_id(source, place, objects)
    folder = source.home / "previews" / previews.VERSION / "gaps"
    with _one_at_a_time:
        path = kept(folder, ident) or drawn(source, place, objects, folder, ident)
    if path is None:
        return None, ""
    name = NAME.format(suffix=path.suffix)
    source.known.add(ident, name, path)
    return file_ref(ident, name, path.stat().st_size), SHOWN[path.suffix]


def kept(folder, ident):
    """The gap's kept picture; None when there is none (or it is marked as standing nowhere)."""
    return next((folder / f"{ident}{suffix}" for suffix in SHOWN if (folder / f"{ident}{suffix}").is_file()), None)


def drawn(source, place, objects, folder, ident):
    """The gap's picture drawn now: ringed in the film, else on the plan; None (and marked) when its things stand
    nowhere."""
    if (folder / f"{ident}.none").is_file():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    located = [found for name in objects for found in matched(stage_points(source, place), name)][:MOST_RINGS]
    path = None
    if located:
        path = film_ring(source, place, located, folder / f"{ident}.jpg") or plan_ring(
            source, place, located, folder / f"{ident}.png")
    if path is None:
        (folder / f"{ident}.none").write_text("its named things stand nowhere the film or the plan shows\n")
    return path


def matched(points, wanted):
    """[(name, (x, y, z))] of the stage's prims a gap names: a prim path exactly, else a prim name with or without
    its number (hose_reel names hose_reel_1)."""
    if wanted.startswith("/"):
        return [(wanted.rsplit("/", 1)[-1], points[wanted])] if wanted in points else []
    pattern = re.compile(rf"^{re.escape(wanted)}(_\d+)?$")
    return [(path.rsplit("/", 1)[-1], point) for path, point in points.items()
            if pattern.match(path.rsplit("/", 1)[-1])]


def stage_points(source, place):
    """{prim path: (x, y, z)} of what the place's accepted OpenUSD stage places, its stronger layers last."""
    def read():
        from score.dashboard.previews import maps
        index = source.usd_index(place)
        listing = source.listing(index.own_output) if index.own_output else {}
        found = {}
        for layer in reversed([layer for layer in index.layers if layer.present and layer.path.endswith(".usda")]):
            found.update(maps.layer_points(layer.path, source.blob_path(listing[layer.path])))
        return found
    return source.remembered(("stage points", place), read)


def film_ring(source, place, located, destination):
    """The located things ringed in the frame of the accepted film that shows the most of them; None when no frame
    shows any."""
    from score.dashboard.previews import films
    output = source.accepted_output(f"demo-film@{place}")
    listing = source.listing(output) if output else {}
    if "film.mp4" not in listing or "views.json" not in listing:
        return None
    size, views = films.film_views(source.blob_path(listing["views.json"]).read_text())
    chosen = films.best_view(views, located, size)
    film = source.blob_path(listing["film.mp4"])
    probed = films.probe(film) if chosen else None
    if not probed:
        return None
    number, shown = chosen
    frame = films.shot_frame(number, probed[0], views)
    still = films.frame_picture(film, frame, probed[1], source.home / "stills" / f"{listing['film.mp4']}-{frame}.jpg")
    if still is None:
        return None
    spots = [(name, column, row, films.ring_radius(depth, size, views[number]))
             for name, column, row, depth in shown]
    return films.ringed(still, spots, size, destination)


def plan_ring(source, place, located, destination):
    """The located things ringed on the place's plan; None when it has no plan."""
    from score.dashboard.previews import maps
    plan = source.place_plan(place)
    if not plan:
        return None
    spots = [(name, point[0], point[2]) for name, point in located]
    return maps.ringed_plan(plan, spots, plan.get("title") or place, destination)
