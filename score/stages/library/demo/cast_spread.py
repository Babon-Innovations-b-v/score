"""Cast placement: the square's launch crowd as `score.stages.cast.spread.stand_every` stood it (the library's
place/square cast/cast.json): the crowd's area and where it is kept off, the named people, the front row's group
stood in its band, then the crowd's copies. The slider asks for fewer copies: the spread keeps the first that fit
in its seeded order, so a smaller ask is the start of the same list."""
import json

ALGORITHM = "cast_spread"
PLACE = "square"
ASKS = (1000, 4000)  # the slider's smaller asks; the last stop is the whole crowd as stood


def plan_point(at):
    return [round(float(at[0]), 2), round(float(-at[2]), 2)]


def rectangle(left, near, wide, long):
    """A record's [x, z, wide, long] rectangle as a plan outline."""
    return [plan_point(corner) for corner in ((left, 0, near), (left + wide, 0, near), (left + wide, 0, near + long),
                                              (left, 0, near + long))]


def crowd_dots(copies):
    """The crowd as one dots shape, a decimetre each point (its lattice is 0.56 m apart)."""
    return [{"kind": "dots", "points": [[round(copy["at"][0], 1), round(-copy["at"][2], 1)] for copy in copies],
             "r": 0.4, "tone": "c3",
             "label": f"the crowd: {len(copies)} people"}]


def made(inputs):
    cast = inputs.json(f"place/{PLACE}@1", "cast/cast.json")
    record = json.loads((inputs.repo / "data/characters" / f"{PLACE}.json").read_text())
    crowd, group = record["crowd"], record["groups"][0]
    copies = cast["crowd"]["copies"]
    members = [person for person in cast["characters"] if person["name"].startswith(group["name"])]
    named = [person for person in cast["characters"] if not person["name"].startswith(group["name"])]
    left, near, wide, long = crowd["spread"]
    asks = [ask for ask in ASKS if ask < len(copies)] + [len(copies)]
    return {
        "example": f"the {PLACE}'s launch crowd",
        "view": "plan", "bounds": [round(value, 2) for value in (left - 8, -(near + long) - 2, left + wide + 2, -near + 2)],
        "steps": [
            {"label": "Where the crowd may stand, and where it is kept off",
             "shapes": [{"kind": "area", "points": rectangle(*crowd["spread"]), "tone": "ground",
                         "label": "the crowd's area"},
                        *({"kind": "area", "points": rectangle(*kept), "tone": "warn", "label": "kept clear"}
                          for kept in crowd["kept_off"]),
                        {"kind": "area", "points": rectangle(*group["band"]), "tone": "ghost",
                         "label": "the front row's band"}]},
            {"label": "The named people stand where the record puts them",
             "shapes": [{"kind": "dots", "points": [plan_point(person["at"])], "r": 0.8, "tone": "c1",
                         "label": person["name"].replace("_", " ")} for person in named]},
            {"label": "The front row's people, each nudged until they fit",
             "shapes": [{"kind": "dots", "points": [plan_point(person["at"]) for person in members], "r": 0.5,
                         "tone": "c2", "label": f"the front row: {len(members)} people"}]},
            {"label": f"Crowd spots on a lattice, kept when a body fits: {len(copies)} of {crowd['count']} asked",
             "shapes": crowd_dots(copies)}],
        "slider": {"label": "people asked", "unit": "", "values": asks, "at": len(asks) - 1,
                   "shapes": [crowd_dots(copies[:ask]) for ask in asks]},
        "numbers": [{"label": "stood", "value": len(copies), "unit": "", "tip": "crowd copies that fit"},
                    {"label": "asked", "value": crowd["count"], "unit": "", "tip": "crowd copies the record asks for"}]}
