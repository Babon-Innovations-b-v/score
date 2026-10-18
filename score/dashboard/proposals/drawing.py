"""What a proposal's pictures draw, worked out once from the branch and kept on its record (`drawing`), so its after
and its before are drawn from the same cameras, at the same moments, with the same settings and the same lamps rule,
and the pair compares (finish.py draws the before from this record field, never from the accepted scene record).

    cameras   the branch's own scene record (the record its stage was assembled from), the first MOST_CAMERAS;
              where the branch moved a camera, its new eye is the one both sides are drawn from
    film      where the branch moves the demo film and plans it with its own tools/review/film_preview.py, MOMENTS
              of that plan's views (each with its frame), so a film's new cameras are pictured too
    moments   where the branch made a layer that moves (MOVING: its motion, effects, people, machines), the first
              camera at MOMENTS frames over the stage's time span, so what moves is seen moving; they make the clip
    lamps     every view is lit by the drawn stage's own lamps (pictures.stage_lamps), so a light layer the branch
              made is in the picture; the same rule draws the before with the accepted stage's lamps
    previews  the paid rows standing in that a free local draw previews (PAID_PREVIEWS); the picture then says
              PAID_LABEL. The other paid rows standing in are `unshown`: the card says their change is not drawn.

Plain data only (no store, no Blender), so it is tested on its own."""

MOST_CAMERAS = 4
MOMENTS = 6
SIZE = (640, 360)
UP = [0.0, 1.0, 0.0]
FILM_ROW = "demo-film"
# Layer rows whose output moves over the stage's time span: a still at one moment cannot show them.
MOVING = ("motion", "effects-layer", "characters-layer", "machines-layer", "physics-layer")
# Paid rows a free local draw previews, and how: the light passes sweep the light layer's lamps, which every view
# draws at their layer's strengths in Eevee.
PAID_PREVIEWS = {"light-passes": "the light layer's lamps at their written strengths, drawn in Eevee",
                 "light-haze": "the light layer's lamps at their written strengths, drawn in Eevee (no haze)"}
LOCAL_LABEL = "local preview: Eevee on the processor, 640x360, rough light"
PAID_LABEL = "preview: the paid batch makes the full version"


def camera(view, name=None, frame=None):
    """One camera as usd_views.py takes it, its look alone (and its frame, when it is drawn at a moment)."""
    found = {"name": name or view["name"], "eye": list(view["eye"]), "aim": list(view["aim"]),
             "up": list(view.get("up", UP)), "fov": float(view.get("fov", 75.0)), "look_only": True}
    if frame is not None:
        found["frame"] = int(frame)
    elif "frame" in view:
        found["frame"] = int(view["frame"])
    return found


def spread(items, count):
    """`count` items spread evenly over `items`, the first and last included (all of them when fewer)."""
    if len(items) <= count:
        return list(items)
    if count == 1:
        return [items[0]]
    return [items[round(number * (len(items) - 1) / (count - 1))] for number in range(count)]


def moments(span, count=MOMENTS):
    """`count` whole frames spread over the stage's (start, end) time span; [] when it has none."""
    if not span or span[1] <= span[0]:
        return []
    start, end = span
    return sorted({round(start + number * (end - start) / (count - 1)) for number in range(count)})


def made_stages(layers):
    """The rows the proposal made for free, from its record's layers."""
    return {item["stage"] for item in layers if item["how"] == "made"}


def paid_stages(layers):
    """The rows standing in for the paid batch, from its record's layers."""
    return {item["stage"] for item in layers if item["how"] == "needs the paid batch"}


def film_cameras(film_views):
    """MOMENTS of the branch's planned film views, named film-<n> (each keeps its frame)."""
    return [camera(view, name=f"film-{number}") for number, view in enumerate(spread(film_views, MOMENTS), 1)]


def moving_cameras(first, span):
    """The first camera at each moment of the stage's span, named <camera>-at-<frame>."""
    return [camera(first, name=f"{first['name']}-at-{frame:04d}", frame=frame) for frame in moments(span)]


def plan(layers, branch_views, film_views=(), span=None):
    """The record's `drawing`: {views, clip, moving, previews, unshown, labels, size}. `layers` the record's layers,
    `branch_views` the branch's scene record views, `film_views` the branch's planned film views ([] when it plans
    none), `span` the drawn stage's (start, end) time codes."""
    cameras = [camera(view) for view in branch_views[:MOST_CAMERAS]]
    film = film_cameras(list(film_views))
    moving = sorted(made_stages(layers) & set(MOVING))
    first = (cameras or film or [None])[0]
    timed = moving_cameras(first, span) if moving and first is not None else []
    paid = sorted(paid_stages(layers))
    previews = [{"stage": stage, "how": PAID_PREVIEWS[stage]} for stage in paid if stage in PAID_PREVIEWS]
    return {"views": cameras + film + timed, "clip": [view["name"] for view in timed or film],
            "moving": moving, "previews": previews, "unshown": [stage for stage in paid if stage not in PAID_PREVIEWS],
            "labels": [LOCAL_LABEL] + ([PAID_LABEL] if previews else []), "size": list(SIZE)}
