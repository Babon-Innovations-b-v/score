"""Far city: the harbour city `tools/usd/far_city.py` lays itself, seed 7 (the seed the far_city place stands on,
data/scene/flat.json), of the five tower kinds made so far: the far shore, the business districts, then the towers
laid row by row behind the shore. The slider lays the city again with the same code at other seeds."""
import math
import sys

ALGORITHM = "far_city"
SEED = 7  # the far_city place's seed (data/scene/flat.json, street.json, square.json)
NOT_MADE = {"far_city_pencil_tower", "far_city_low_block", "far_city_housing_slab"}  # no made model yet (same notes)
SEEDS = (SEED, 11, 23, 42)
FRONT_ROWS = 4  # the rows shown first


def city(repo):
    sys.path.insert(0, str(repo / "tools/usd"))
    import far_city as laid
    return laid


def made_kinds(laid):
    return {kind["row"] for kind in laid.kinds()} - NOT_MADE


def plain(row):
    return row.removeprefix("far_city_").replace("_", " ")


def plan_point(spot):
    return [round(spot[0]), round(-spot[1])]


def row_of(laid, tower, seed):
    """Which row behind the shore a tower stands in, from how far past the shore it stands."""
    bearing = math.degrees(math.atan2(tower["at"][0], -tower["at"][1])) % 360.0
    reach = math.hypot(*tower["at"]) - laid.shore_distance(bearing, seed) - laid.FIRST_ROW
    return max(0, round(reach / laid.ROW_DEEP))


def towers(laid, laid_towers, tones):
    """One dots shape a tower kind: each tower a dot as wide as its foot."""
    return [{"kind": "dots", "points": [plan_point(tower["at"]) for tower in laid_towers if tower["kind"] == kind],
             "r": round(2 * sum(tower["radius"] for tower in laid_towers) / max(len(laid_towers), 1), 1),
             "tone": tone, "label": f"{plain(kind)} towers"} for kind, tone in tones.items()]


def shore(laid, seed):
    bearings = range(int(laid.CITY_FROM) - 10, int(laid.CITY_TO) + 11, 2)
    return [plan_point((laid.shore_distance(bearing, seed) * math.sin(math.radians(bearing)),
                        -laid.shore_distance(bearing, seed) * math.cos(math.radians(bearing)))) for bearing in bearings]


def districts(laid, seed):
    return [{"kind": "text", "tone": "accent", "label": "business district",
             "points": [plan_point(((laid.shore_distance(middle, seed) + 300) * math.sin(math.radians(middle)),
                                    -(laid.shore_distance(middle, seed) + 300) * math.cos(math.radians(middle))))]}
            for middle, _, _ in laid.DISTRICTS]


def made(inputs):
    laid = city(inputs.repo)
    kinds = made_kinds(laid)
    tones = {kind: f"c{rank + 1}" for rank, kind in enumerate(sorted(kinds))}
    by_seed = {seed: laid.lay_towers(seed, kinds) for seed in SEEDS}
    chosen = by_seed[SEED]
    front = [tower for tower in chosen if row_of(laid, tower, SEED) < FRONT_ROWS]
    points = [plan_point(tower["at"]) for tower in chosen]
    xs, ys = [point[0] for point in points] + [0], [point[1] for point in points] + [0]
    return {
        "example": f"the far city across the harbour, seed {SEED}",
        "view": "plan", "bounds": [min(xs) - 100, min(ys) - 100, max(xs) + 100, max(ys) + 100],
        "steps": [
            {"label": "The far shore, round the harbour's far side",
             "shapes": [{"kind": "line", "points": shore(laid, SEED), "tone": "ground", "label": "far shore"},
                        {"kind": "text", "points": [[0, 0]], "tone": "ghost", "label": "the harbour"}]},
            {"label": "Business districts, where office towers stand tallest",
             "shapes": districts(laid, SEED)},
            {"label": f"Towers on the first {FRONT_ROWS} rows behind the shore", "shapes": towers(laid, front, tones)},
            {"label": f"All {laid.ROWS} rows, a lot left empty here and there",
             "shapes": towers(laid, chosen, tones)}],
        "slider": {"label": "seed", "unit": "", "values": list(SEEDS), "at": 0,
                   "shapes": [towers(laid, by_seed[seed], tones) for seed in SEEDS]},
        "numbers": [{"label": "towers", "value": len(chosen), "unit": "", "tip": f"towers laid by seed {SEED}"},
                    {"label": "kinds", "value": len(kinds), "unit": "", "tip": "tower kinds with a made model"},
                    {"label": "rows", "value": laid.ROWS, "unit": "", "tip": "rows deep behind the shore"}]}
