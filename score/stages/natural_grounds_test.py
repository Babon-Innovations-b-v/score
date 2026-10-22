"""The natural ground rule (natural_grounds.py): a ground row's own words first, else its body's physics against
water's phases; nothing read off a body's name."""
from score.stages import natural_grounds

STAR = {"body": "star", "name": "Star", "kelvin": 5772.0, "radius_km": 695700.0}
AU = 149597870.7


def world(name, kpa, distance_km, around="star"):
    return {"body": name, "name": name.title(), "around": around, "distance_km": distance_km,
            "surface_pressure_kpa": kpa}


def test_the_physics_pick_ocean_rock_ice_sand_and_regolith():
    wet, hot = world("wet", 101.3, AU), world("hot", 101.3, 0.2 * AU)  # 278 K and 622 K at zero albedo
    frozen, windy = world("frozen", 0.0, 5.2 * AU), world("windy", 0.6, 1.52 * AU)
    airless = world("airless", 0.0, 384400.0, around="wet")  # a moon: its planet's distance from the star
    bodies = [STAR, wet, hot, frozen, windy, airless]
    picked = {body["body"]: natural_grounds.of_body(body, bodies, {})[0] for body in bodies[1:]}
    assert picked == {"wet": "ocean", "hot": "rock", "frozen": "ice", "windy": "sand", "airless": "regolith"}


def test_a_row_s_words_come_first_and_what_is_missing_is_named():
    windy = world("windy", 0.6, 1.52 * AU)
    assert natural_grounds.of_row({"id": "dunes", "name": "red dunes", "noun": "ground"}, None, [], {})[0] == "sand"
    assert natural_grounds.of_row({"id": "g", "name": "martian ground", "noun": "ground"}, windy, [STAR, windy],
                                  {})[0] == "sand"  # the physics, never the word "martian"
    assert natural_grounds.of_row({"id": "g", "noun": "ground"}, None, [], {})[0] is None  # a plot: no physics
    plaza = natural_grounds.of_row({"id": "plaza", "name": "main plaza", "noun": "plaza"}, windy, [STAR, windy], {})
    assert plaza == (None, "the row plaza says plaza: a made ground, no natural one")  # people paved it
    assert natural_grounds.of_row({"id": "sea", "noun": "sea"}, windy, [STAR, windy], {})[0] == "ocean"
    recipe, why = natural_grounds.of_body({"body": "x", "name": "X", "around": "star", "distance_km": AU},
                                          [STAR], {})
    assert recipe is None and "no surface pressure" in why
    table = {"bodies": {"x": {"surface_pressure_kpa": 0.0}}}  # the reference table's value when the setting has none
    assert natural_grounds.of_body({"body": "x", "name": "X", "around": "star", "distance_km": AU}, [STAR],
                                   table)[0] == "regolith"
