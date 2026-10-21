"""The sky over a site (score/review/sky.py), run from the environment's physics state, against known skies."""
import pytest

from score.review import sky

STATE = sky.bodies()


def moon_of(when):
    return next(world for world in sky.sky_at(STATE, "earth", 0.0, 0.0, when)["worlds"] if world["world"] == "moon")


def test_the_moon_is_full_and_new_when_it_was():
    assert moon_of("2024-01-25T18:00:00Z")["lit"] > 0.97  # full Moon, 25 January 2024, 17:54 UT
    assert moon_of("2024-01-11T12:00:00Z")["lit"] < 0.03  # new Moon, 11 January 2024, 11:57 UT
    assert moon_of("2024-01-25T18:00:00Z")["across"] == pytest.approx(0.52, abs=0.04)


def test_the_sun_stands_where_it_does_over_greenwich_at_the_equinox():
    sun = sky.sky_at(STATE, "earth", 51.48, 0.0, "2024-03-20T12:07:00Z")["sun"]
    assert sun["altitude"] == pytest.approx(90 - 51.48, abs=0.5) and sun["azimuth"] == pytest.approx(180, abs=1)


def test_earth_hangs_still_two_degrees_across_over_a_near_side_moon_site_and_its_phase_turns():
    seen = [next(world for world in sky.sky_at(STATE, "moon", 55.0, 0.0, f"2099-06-{day:02d}T12:00:00Z")["worlds"]
                 if world["world"] == "earth") for day in (1, 8, 15)]
    assert all(1.75 < earth["across"] < 2.05 for earth in seen)  # Earth from the Moon: about 2 degrees
    assert max(earth["altitude"] for earth in seen) - min(earth["altitude"] for earth in seen) < 1  # locked: it stays
    assert seen[0]["lit"] < 0.1 and seen[2]["lit"] > 0.8  # a fortnight from new Earth to nearly full


def test_mars_from_earth_and_earth_from_mars_are_points():
    assert next(world for world in sky.sky_at(STATE, "earth", 22.3, 114.2, "2099-06-01T12:00:00Z")["worlds"]
                if world["world"] == "mars")["across"] < 0.01
    assert next(world for world in sky.sky_at(STATE, "mars", 30.0, 130.0, "2099-06-01T12:00:00Z")["worlds"]
                if world["world"] == "earth")["across"] < 0.01
