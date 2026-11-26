"""The photograph's incident meter (render.py, #223): what a light meter held at the person reads under a library sky,
and the exposure and white balance a photographer sets from it. numpy only, so it is the same inside Blender and in
the test.

    found = metered(radiance, turn)        # {front, ground}: irradiance (linear RGB) on a card facing the camera
                                           # and on the level ground, from an equirectangular panorama
    exposure_of(found), balance_of(found)  # stops that make an 18% grey card read 18%; the gains that make it neutral

The panorama is in Cycles' equirectangular layout (u = 1/2 - atan2(y, x) / 2 pi, v up from the nadir, the bottom
row first), looked up through a Mapping node turned `turn` degrees about z: a world direction d is looked up at R d, so
a pixel's direction t lights the world from R^-1 t. Measured 2026-11-26 under the park's sky turned -45, 90 and 180
degrees: a white card facing the camera read the meter's front irradiance over pi within 1% each time.
"""
import math

import numpy as np

GREY_CARD = 0.18
LUMA = np.array([0.2126, 0.7152, 0.0722])  # Rec. 709 luminance of Blender's linear scene colour
CARDS = {"front": (0.0, -1.0, 0.0), "ground": (0.0, 0.0, 1.0)}  # the camera looks along +y; z is up


def directions(width, height):
    """Each panorama pixel's direction (before the turn) and its solid angle."""
    longitude = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * math.pi
    latitude = ((np.arange(height) + 0.5) / height - 0.5) * math.pi
    lon, lat = np.meshgrid(longitude, latitude)
    way = np.stack([np.cos(lon) * np.cos(lat), -np.sin(lon) * np.cos(lat), np.sin(lat)], axis=-1)
    solid = np.cos(lat) * (2.0 * math.pi / width) * (math.pi / height)
    return way, solid


def turned(degrees):
    """The Mapping node's turn of `degrees` about z as a matrix (a world direction d is looked up at this times d)."""
    angle = math.radians(degrees)
    return np.array([[math.cos(angle), -math.sin(angle), 0.0], [math.sin(angle), math.cos(angle), 0.0],
                     [0.0, 0.0, 1.0]])


def metered(radiance, turn):
    """{card: irradiance (linear RGB)} on each of CARDS from the panorama `radiance` (rows bottom first, RGB) turned
    `turn` degrees."""
    height, width = radiance.shape[:2]
    way, solid = directions(width, height)
    world = way @ turned(turn)  # as rows: t R is R^-1 t, the world direction a pixel is seen in
    found = {}
    for name, normal in CARDS.items():
        weight = np.clip(world @ np.array(normal), 0.0, None) * solid
        found[name] = (radiance[..., :3].astype(np.float64) * weight[..., None]).sum(axis=(0, 1))
    return found


def exposure_of(found):
    """Stops that make an 18% grey card at the person read 18% (the incident meter's exposure)."""
    card = GREY_CARD * float(found["front"] @ LUMA) / math.pi
    return math.log2(GREY_CARD / card)


def balance_of(found):
    """Each channel's gain that makes the card at the person neutral (the grey card's white balance)."""
    front = found["front"]
    return float(front @ LUMA) / front
