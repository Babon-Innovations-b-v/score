"""Each scene's sky as its stages read it (CONTEXT.md "physics"; the owner, 2026-10-21: no fixed sky): the physics of
the environment concept in force, as the environment's plan settles it, and the site and scene time the scene's sky
is seen from: its own when it is a top scene, else the top scene's that holds it (a room sees the sky of the site it
stands in). Kept beside the plans the plan stage reads, so the light layer declares it as an input and works out what
is overhead itself (score/review/overhead.py through score/stages/light/sky.py):

    {home}/design/sky/<scene>.json  {place, top, site: {on, latitude, longitude | x, y, height_m}, time, setting}

A scene whose top scene has no site on the environment's plan, or no scene time there yet, keeps none: its sky is a
gap (score/stages/light/needs.py) until the plan has both.

    keep(store, places) -> ([kept], [changed])
"""
import json

from score.review import concepts, environment_plan
from score.store import PROPS_HOME

KEPT = PROPS_HOME / "design" / "sky"
WHERE = ("latitude", "longitude", "x", "y", "height_m")


def top_of(store, place):
    """The top scene `place` stands in: itself when it is one, else the outermost scene holding it."""
    seen = {place}
    while (holder := concepts.above(place, store)) is not None:
        if holder in seen:
            raise ValueError(f"{place} stands within itself")
        seen.add(holder)
        place = holder
    return place


def sky_of(plan, place, top):
    """The scene's sky inputs from the environment's settled plan, None when its top scene has no site or no time."""
    for found in plan["maps"]:
        for site in found["sites"]:
            if site["place"] == top and site.get("time"):
                return {"place": place, "top": top, "time": site["time"], "setting": plan["setting"],
                        "site": {"on": found["on"], **{name: site[name] for name in WHERE if name in site}}}
    return None


def keep(store, places):
    """Every scene's sky inputs where its stages read them, a scene with none taken out there; ([kept], [changed])."""
    plan = environment_plan.current(store)["plan"]
    kept, changed = [], []
    for place in places:
        path = KEPT / f"{place}.json"
        before = path.read_text() if path.is_file() else None
        found = sky_of(plan, place, top_of(store, place))
        if found is not None:
            text = json.dumps(found, indent=1) + "\n"
            if text != before:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            kept.append(place)
        elif before is not None:
            path.unlink()
        if (path.read_text() if path.is_file() else None) != before:
            changed.append(place)
    return kept, changed
