"""An environment's setting (score/review/setting.py) on two settings: environment 1's (the Sun, Earth, the Moon and
Mars of the reference table as bodies, the stars a backdrop, its sites on them) and a single house on a flat plot (its
sun a light, a sky backdrop, no bodies at all)."""
import pytest

from score.review import setting

SUN = {"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
       "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}
HOUSE = {"bodies": [], "plots": [{"name": "Meadow", "gravity": 9.81}], "lights": [SUN],
         "backdrops": [{"name": "Sky", "lux": 10000}],
         "sites": [{"place": "house", "on": "meadow", "x": 0, "y": "0", "height_m": 0}]}


def test_every_real_bodys_value_names_its_source():
    table = setting.reference()
    for key, body in table["bodies"].items():
        values = [field for field in body if field != "cited"]
        assert set(body["cited"]) == set(values), key
        assert all(source in table["sources"] for source in body["cited"].values()), key


def test_environment_one_takes_its_bodies_from_the_table_and_its_gravity_from_their_mass():
    found = setting.now()
    bodies = {body["body"]: body for body in found["bodies"]}
    assert set(bodies) == {"sun", "earth", "moon", "mars"} and found["plots"] == []
    assert {key: bodies[key]["gravity"] for key in ("earth", "moon", "mars")} == pytest.approx(
        {"earth": 9.82, "moon": 1.62, "mars": 3.73}, abs=0.005)  # NASA's fact sheets: surface gravity (mean)
    assert bodies["moon"]["radius_km"] == 1737.4 and bodies["moon"]["locked_to"] == "earth"
    assert bodies["moon"]["distance_km"] == pytest.approx(384400, rel=1e-3)
    assert {site["place"]: site["on"] for site in found["sites"]} == {
        "square": "earth", "wreck": "moon", "old_station": "moon", "base": "moon", "campgrounds": "mars"}
    assert bodies["sun"]["kelvin"] == 5772.0 and bodies["sun"]["lux"] == 128000.0  # the body and the light it gives
    assert "lux" not in bodies["earth"] and found["lights"] == []
    assert found["backdrops"] == [{"backdrop": "stars", "name": "Stars", "shape": "dome", "lux": 0.0001}]


def test_a_house_on_a_plot_needs_no_bodies_its_sun_is_a_light():
    found = setting.checked(HOUSE)
    assert found["bodies"] == [] and found["plots"] == [{"plot": "meadow", "name": "Meadow", "gravity": 9.81}]
    assert found["lights"][0]["light"] == "sun" and found["lights"][0]["day_hours"] == 24.0
    assert found["backdrops"] == [{"backdrop": "sky", "name": "Sky", "shape": "dome", "lux": 10000.0}]
    assert found["sites"] == [{"place": "house", "on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}]
    with pytest.raises(setting.Refused, match="no equinox|equinox is no moment"):
        setting.checked({**HOUSE, "lights": [{**SUN, "equinox": "noon"}]})
    with pytest.raises(setting.Refused, match="shape is one of"):
        setting.checked({**HOUSE, "backdrops": [{"name": "Sky", "lux": 1, "shape": "box"}]})
    with pytest.raises(setting.Refused, match="share a key"):
        setting.checked({**HOUSE, "backdrops": [{"name": "Sun", "lux": 1}]})
    with pytest.raises(setting.Refused, match="shines with"):
        setting.checked({"bodies": [{"name": "Star", "radius_km": 1, "mass_kg": 1, "lux": 5}]})


def test_a_real_body_set_off_the_table_keeps_his_values_and_an_invented_one_needs_all_of_its_own():
    rows = [{"reference": "sun"}, {"reference": "earth", "day_hours": "30", "radius_km": "7000,5"}]
    earth = setting.checked({"bodies": rows})["bodies"][1]
    assert earth["radius_km"] == 7000.5 and earth["day_hours"] == 30.0 and "pole_ra_deg" not in earth  # his own day
    assert earth["mass_kg"] == 5.9722e24 and earth["name"] == "Earth"  # the rest the table's
    with pytest.raises(setting.Refused, match="no distance_km"):
        setting.checked({"bodies": [{"reference": "sun"}, {"name": "Home", "radius_km": 5000, "mass_kg": 5e24,
                                                           "around": "sun"}]})
    with pytest.raises(setting.Refused, match="no real body"):
        setting.checked({"bodies": [{"reference": "vulcan"}]})


def test_a_setting_out_of_shape_is_refused():
    with pytest.raises(setting.Refused, match="no body or plot"):
        setting.checked({**HOUSE, "sites": [{"place": "house", "on": "the moon", "x": 0, "y": 0}]})
    with pytest.raises(setting.Refused, match="orbits nothing"):
        setting.checked({"bodies": [{"reference": "sun"}, {"reference": "mars", "around": ""},
                                    {"name": "Star two", "radius_km": 1, "mass_kg": 1}]})
    with pytest.raises(setting.Refused, match="is no body"):
        setting.checked({"bodies": [{"reference": "sun"}, {"reference": "moon"}]})  # it orbits an Earth not there
    with pytest.raises(setting.Refused, match="latitude of 95"):
        setting.checked({"bodies": [{"reference": "sun"}, {"reference": "mars"}],
                         "sites": [{"place": "camp", "on": "mars", "latitude": 95, "longitude": 0}]})


def test_a_models_values_for_a_real_body_are_dropped_for_the_tables():
    proposed = setting.proposed({"bodies": [{"body": "moon", "name": "Moon", "reference": "moon", "radius_km": 220}]})
    assert proposed["bodies"] == [{"body": "moon", "name": "Moon", "reference": "moon"}]


def test_a_models_answer_never_stacks_two_sites_the_concept_had_apart():
    before = setting.now()
    rounded = [{**site, "latitude": 55.0, "longitude": 0.0} if site["on"] == "moon" else site
               for site in before["sites"]]
    kept = setting.kept_apart({**before, "sites": rounded}, before)
    assert kept["sites"] == before["sites"]  # every Moon site back where it stood
    spots = [setting.spot(site) for site in before["sites"]]
    assert len(set(spots)) == len(spots)  # environment 1's proposal: each site its own spot
    moved = [{**site, "longitude": 0.5} if site["place"] == "base" else site for site in before["sites"]]
    assert setting.kept_apart({**before, "sites": moved}, before)["sites"] == moved  # a site he moves alone moves
