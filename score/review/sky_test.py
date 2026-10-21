"""The sky over a site (score/review/sky.py), run from a setting, against known skies: environment 1's bodies (the
reference table's Sun, Earth, Moon and Mars) and a house on a flat plot with a sun path and no bodies."""
import datetime

import pytest

from score.review import setting, sky

BODIES = setting.now()["bodies"]
PLOT = {"plot": "plot", "name": "the plot", "gravity": 9.81, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24.0,
        "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}


def moon_of(when):
    return next(world for world in sky.sky_at(BODIES, "earth", 0.0, 0.0, when)["worlds"] if world["world"] == "moon")


def test_the_moon_is_full_and_new_when_it_was():
    assert moon_of("2024-01-25T18:00:00Z")["lit"] > 0.97  # full Moon, 25 January 2024, 17:54 UT
    assert moon_of("2024-01-11T12:00:00Z")["lit"] < 0.03  # new Moon, 11 January 2024, 11:57 UT
    assert moon_of("2024-01-25T18:00:00Z")["across"] == pytest.approx(0.52, abs=0.04)


def test_the_sun_stands_where_it_does_over_greenwich_at_the_equinox():
    sun = sky.sky_at(BODIES, "earth", 51.48, 0.0, "2024-03-20T12:07:00Z")["sun"]
    assert sun["altitude"] == pytest.approx(90 - 51.48, abs=0.5) and sun["azimuth"] == pytest.approx(180, abs=1)


def test_earth_hangs_still_about_two_degrees_across_over_a_near_side_moon_site_and_its_phase_turns():
    seen = [next(world for world in sky.sky_at(BODIES, "moon", 55.0, 0.0, f"2099-06-{day:02d}T12:00:00Z")["worlds"]
                 if world["world"] == "earth") for day in (1, 8, 15)]
    assert all(1.75 < earth["across"] < 2.05 for earth in seen)  # Earth from the Moon: about 1.9 degrees
    assert max(earth["altitude"] for earth in seen) - min(earth["altitude"] for earth in seen) < 1  # locked: it stays
    assert seen[0]["lit"] < 0.1 and seen[2]["lit"] > 0.8  # a fortnight from new Earth to nearly full


def test_mars_from_earth_and_earth_from_mars_are_points():
    assert next(world for world in sky.sky_at(BODIES, "earth", 22.3, 114.2, "2099-06-01T12:00:00Z")["worlds"]
                if world["world"] == "mars")["across"] < 0.01
    assert next(world for world in sky.sky_at(BODIES, "mars", 30.0, 130.0, "2099-06-01T12:00:00Z")["worlds"]
                if world["world"] == "earth")["across"] < 0.01


def test_a_plots_sun_follows_its_path_and_its_sky_holds_no_bodies():
    noon = sky.plot_sky(PLOT, "2024-03-20T12:00:00Z")
    assert noon["worlds"] == [] and noon["sun"]["altitude"] == pytest.approx(90 - 52.0, abs=0.01)
    assert noon["sun"]["azimuth"] == pytest.approx(180, abs=0.01)
    summer = sky.plot_sky(PLOT, "2024-06-20T12:00:00Z")["sun"]  # a quarter year on: the sun at its highest
    assert summer["altitude"] == pytest.approx(90 - 52.0 + 23.44, abs=0.3)
    assert sky.plot_sky(PLOT, "2024-03-21T00:00:00Z")["sun"]["altitude"] == pytest.approx(-38.0, abs=0.5)  # midnight
    morning = sky.plot_sky(PLOT, "2024-03-20T06:00:00Z")["sun"]
    assert morning["altitude"] == pytest.approx(0.0, abs=0.15) and morning["azimuth"] == pytest.approx(90, abs=0.2)


def test_an_invented_body_turns_by_its_own_day():
    world = {"body": "home", "name": "Home", "radius_km": 5000.0, "mass_kg": 5e24, "around": "star",
             "distance_km": 1.2e8, "period_days": 300.0, "eccentricity": 0.0, "inclination_deg": 0.0,
             "day_hours": 30.0, "tilt_deg": 0.0}
    bodies = [{"body": "star", "name": "Star", "radius_km": 600000.0, "mass_kg": 2e30}, world]
    start = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
    heights = [sky.sky_at(bodies, "home", 0.0, 0.0, (start + datetime.timedelta(hours=hour)).isoformat())["sun"]
               ["altitude"] for hour in range(31)]
    assert max(heights) > 80 and min(heights) < -80  # on its equator the star passes over and under once a day
    again = sky.sky_at(bodies, "home", 0.0, 0.0, "2100-01-02T06:00:00Z")["sun"]["altitude"]  # one 30 h day on
    assert again == pytest.approx(heights[0], abs=1.5)  # back where it was, less its orbit's turn of 1.5 degrees
