"""What is seen overhead at a site (score/review/overhead.py), worked out from a setting, against known skies:
environment 1's (the reference table's Sun, Earth, Moon and Mars as bodies, the stars as a backdrop) and a house on a
flat plot with a sun light on its day path and a sky backdrop, no bodies. One code path for both."""
import datetime

import pytest

from score.review import overhead, setting

ENVIRONMENT_1 = setting.now()
BODIES = ENVIRONMENT_1["bodies"]
HOUSE = setting.checked({
    "plots": [{"name": "Meadow", "gravity": 9.81}],
    "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
                "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}],
    "backdrops": [{"name": "Sky", "shape": "dome", "lux": 10000, "kelvin": 9000}],
    "sites": [{"place": "house", "on": "meadow", "x": 0, "y": 0}]})


def at(found, key):
    return next(body for body in found["bodies"] if body["body"] == key)


def moon_of(when):
    return at(overhead.from_body(BODIES, "earth", 0.0, 0.0, when), "moon")


def test_the_moon_is_full_and_new_when_it_was():
    assert moon_of("2024-01-25T18:00:00Z")["lit"] > 0.97  # full Moon, 25 January 2024, 17:54 UT
    assert moon_of("2024-01-11T12:00:00Z")["lit"] < 0.03  # new Moon, 11 January 2024, 11:57 UT
    assert moon_of("2024-01-25T18:00:00Z")["across"] == pytest.approx(0.52, abs=0.04)


def test_the_suns_light_stands_where_it_does_over_greenwich_at_the_equinox_at_its_strength():
    sun = overhead.from_body(BODIES, "earth", 51.48, 0.0, "2024-03-20T12:07:00Z")["lights"][0]
    assert sun["of"] == "sun" and sun["kelvin"] == 5772.0
    assert sun["altitude"] == pytest.approx(90 - 51.48, abs=0.5) and sun["azimuth"] == pytest.approx(180, abs=1)
    assert sun["lux"] == pytest.approx(128000, rel=0.02)  # March: Earth near its mean distance


def test_the_suns_disc_is_widest_in_january_and_narrowest_in_july():
    sun = [overhead.from_body(BODIES, "earth", 0.0, 0.0, when)["lights"][0]["across"]
           for when in ("2024-01-03T00:00:00Z", "2024-07-05T00:00:00Z")]
    # the Sun's apparent diameter at perihelion and aphelion: 32.53 and 31.46 arc minutes
    assert sun[0] == pytest.approx(32.53 / 60, abs=0.005) and sun[1] == pytest.approx(31.46 / 60, abs=0.005)


def test_earth_hangs_still_about_two_degrees_across_over_a_near_side_moon_site_and_its_phase_turns():
    seen = [at(overhead.from_body(BODIES, "moon", 55.0, 0.0, f"2099-06-{day:02d}T12:00:00Z"), "earth")
            for day in (1, 8, 15)]
    assert all(1.75 < earth["across"] < 2.05 for earth in seen)  # Earth from the Moon: about 1.9 degrees
    assert max(earth["altitude"] for earth in seen) - min(earth["altitude"] for earth in seen) < 1  # locked: it stays
    assert seen[0]["lit"] < 0.1 and seen[2]["lit"] > 0.8  # a fortnight from new Earth to nearly full


def test_mars_from_earth_and_earth_from_mars_are_points_and_the_sun_is_dimmer_at_mars():
    assert at(overhead.from_body(BODIES, "earth", 22.3, 114.2, "2099-06-01T12:00:00Z"), "mars")["across"] < 0.01
    from_mars = overhead.from_body(BODIES, "mars", 30.0, 130.0, "2099-06-01T12:00:00Z")
    assert at(from_mars, "earth")["across"] < 0.01
    assert 45000 < from_mars["lights"][0]["lux"] < 65000  # 1.38 to 1.67 AU: 128000 over its square


def test_environment_1_overhead_holds_its_bodies_the_suns_light_and_the_stars():
    site = next(site for site in ENVIRONMENT_1["sites"] if site["place"] == "base")
    found = overhead.seen(ENVIRONMENT_1, site, "2099-06-01T12:00:00Z")
    assert [light["of"] for light in found["lights"]] == ["sun"]
    assert {body["body"] for body in found["bodies"]} == {"earth", "mars"}  # never the Moon it stands on, nor the Sun
    assert found["backdrops"] == [{"name": "Stars", "shape": "dome", "lux": 0.0001}]


def test_a_houses_sun_is_a_light_on_its_day_path_with_no_bodies():
    site = HOUSE["sites"][0]
    noon = overhead.seen(HOUSE, site, "2024-03-20T12:00:00Z")
    assert noon["bodies"] == [] and noon["backdrops"][0]["name"] == "Sky"
    sun = noon["lights"][0]
    assert sun["of"] is None and sun["lux"] == 100000 and sun["kelvin"] == 5800
    assert sun["altitude"] == pytest.approx(90 - 52.0, abs=0.01) and sun["azimuth"] == pytest.approx(180, abs=0.01)
    summer = overhead.seen(HOUSE, site, "2024-06-20T12:00:00Z")["lights"][0]  # a quarter year on: at its highest
    assert summer["altitude"] == pytest.approx(90 - 52.0 + 23.44, abs=0.3)
    assert overhead.seen(HOUSE, site, "2024-03-21T00:00:00Z")["lights"][0]["altitude"] == pytest.approx(-38.0, abs=0.5)
    morning = overhead.seen(HOUSE, site, "2024-03-20T06:00:00Z")["lights"][0]
    assert morning["altitude"] == pytest.approx(0.0, abs=0.15) and morning["azimuth"] == pytest.approx(90, abs=0.2)


def test_an_invented_body_turns_by_its_own_day_under_an_invented_star():
    world = {"body": "home", "name": "Home", "radius_km": 5000.0, "mass_kg": 5e24, "around": "star",
             "distance_km": 1.2e8, "period_days": 300.0, "eccentricity": 0.0, "inclination_deg": 0.0,
             "day_hours": 30.0, "tilt_deg": 0.0}
    bodies = [{"body": "star", "name": "Star", "radius_km": 600000.0, "mass_kg": 2e30, "kelvin": 4000.0,
               "lux": 1e5, "lux_at_km": 1.2e8}, world]
    start = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
    heights = [overhead.from_body(bodies, "home", 0.0, 0.0, (start + datetime.timedelta(hours=hour)).isoformat())
               ["lights"][0]["altitude"] for hour in range(31)]
    assert max(heights) > 80 and min(heights) < -80  # on its equator the star passes over and under once a day
    again = overhead.from_body(bodies, "home", 0.0, 0.0, "2100-01-02T06:00:00Z")["lights"][0]["altitude"]
    assert again == pytest.approx(heights[0], abs=1.5)  # back where it was, less its orbit's turn of 1.5 degrees
