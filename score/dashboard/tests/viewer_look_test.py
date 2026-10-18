"""The viewer look check's measures on pictures made here (no browser, no store): the same picture passes, a black
one and one of stand-in pink fail, and the #view= link carries the camera and its moment."""
from PIL import Image

from score.dashboard.tests import viewer_look


def picture(path, colour):
    Image.new("RGB", (320, 180), colour).save(path)
    return path


def test_a_picture_against_itself_passes_and_black_or_pink_fails(tmp_path):
    film = picture(tmp_path / "film.png", (120, 110, 100))
    same = viewer_look.measures(film, film)
    assert same == {"difference": 0.0, "structure": 1.0, "brightness": 1.0, "pink": 0.0, "black": 0.0}
    assert viewer_look.passes(same)
    black = viewer_look.measures(film, picture(tmp_path / "black.png", (0, 0, 0)))
    assert black["black"] == 1.0 and not viewer_look.passes(black)
    pink = viewer_look.measures(film, picture(tmp_path / "pink.png", (240, 130, 150)))
    assert pink["pink"] == 1.0 and not viewer_look.passes(pink)


def test_the_view_link_carries_the_camera_and_its_moment():
    camera = {"eye": [1, 2, 3], "aim": [4, 5.5, -6], "fov": 80.0, "frame": 132}
    assert viewer_look.view_link(camera) == ("view=1.000000,2.000000,3.000000,4.000000,5.500000,-6.000000,80.000000"
                                             "&t=132.000")
    assert viewer_look.view_link({**camera, "frame": None}).endswith(",80.000000")
