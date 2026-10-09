"""The Earth's surface as the framework draws it on a ball in a place's sky: the game 2099's ink_earth shader
(game/art/shaders/ink_earth.gdshader, #115) repeated in numpy and baked once into a longitude-latitude picture that a
sphere's uvs (builders.sphere) take, so any USD reader shows the same planet. Blue ocean, continents in green and in
desert tan, white ice at the poles and white cloud, each one flat colour from the palette, with an ink line along every
coast. Nothing here is a photograph: land and cloud come from seeded noise over the ball's own directions.

The shader's day and night step is the light's work in the stage: the ball is a plain diffuse surface lit by the
place's own sun, so its night side is dark where the sun does not reach it. The game's thin glow of air round the lit
side (air_edge.gdshader) is not drawn.

    picture(width) -> uint8 (height, width, 3) array, sRGB
    write(path, width=2048) -> path
"""
import json
import pathlib

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

# ink_earth.gdshader's constants.
LAND_SCALE = 1.6
LAND_WARP = 0.55
SEA_LEVEL = 0.56
DESERT_LATITUDE = 0.38
DESERT_BELT = 0.16
ICE_FROM = 0.86
CLOUD_SCALE = 2.4
CLOUD_STRETCH = 2.2
CLOUD_LEVEL = 0.6
COAST_PX = 1.4
# The palette tokens the shader's colours are set from (tools/design/build.gd in the game).
TOKENS = {"ocean": "earth-ocean", "land": "earth-land", "desert": "earth-desert", "cloud": "earth-cloud",
          "ink": "ink-line"}


def hash3(at):
    """The shader's gradient hash: a pseudo-random vector from -1 to 1 for each whole point."""
    dotted = np.stack([at @ np.array([127.1, 311.7, 74.7]), at @ np.array([269.5, 183.3, 246.1]),
                       at @ np.array([113.5, 271.9, 124.6])], axis=-1)
    value = np.sin(dotted) * 43758.5453123
    return (value - np.floor(value)) * 2.0 - 1.0


def noise(at):
    """Smooth gradient noise in space, about -1 to 1, for points (..., 3)."""
    cell = np.floor(at)
    inside = at - cell
    blend = inside * inside * (3.0 - 2.0 * inside)
    corners = []
    for index in range(8):
        corner = np.array([index & 1, (index >> 1) & 1, (index >> 2) & 1], dtype=np.float64)
        corners.append(np.sum(hash3(cell + corner) * (inside - corner), axis=-1))
    bx, by, bz = blend[..., 0], blend[..., 1], blend[..., 2]

    def mix(low, high, share):
        return low + (high - low) * share
    near_x = mix(mix(corners[0], corners[1], bx), mix(corners[2], corners[3], bx), by)
    far_x = mix(mix(corners[4], corners[5], bx), mix(corners[6], corners[7], bx), by)
    return mix(near_x, far_x, bz)


def layered(at):
    """Five sizes of noise laid over each other, about 0 to 1."""
    total, weight = np.zeros(at.shape[:-1]), 0.5
    for _ in range(5):
        total += noise(at) * weight
        at = at * 2.03 + np.array([17.1, 5.3, 11.7])
        weight *= 0.5
    return total + 0.5


def land_height(way):
    """How high the land stands at a way out from the middle: sea under SEA_LEVEL."""
    at = way * LAND_SCALE
    push = np.stack([layered(at + np.array([3.1, 0.0, 0.0])), layered(at + np.array([0.0, 7.7, 0.0])),
                     layered(at + np.array([0.0, 0.0, 1.9]))], axis=-1) - 0.5
    return layered(at + push * LAND_WARP * 2.0)


def cloud_over(way):
    """How much cloud hangs over a way out, streaked along the lines of latitude."""
    at = np.stack([way[..., 0], way[..., 1] * CLOUD_STRETCH, way[..., 2]], axis=-1) * CLOUD_SCALE \
        + np.array([41.0, 13.0, 29.0])
    return layered(at)


def edge(value, level, pixel):
    """A hard edge between two flat colours, softened over one texel."""
    return np.clip((value - (level - pixel * 0.5)) / np.maximum(pixel, 1e-5), 0.0, 1.0)


def texel_width(value):
    """How much a value changes from one texel to the next (the shader's fwidth, on the picture)."""
    rows, columns = np.gradient(value)
    return np.abs(rows) + np.abs(columns)


def ways(width):
    """The unit way out from the ball's middle at each texel's centre, as builders.sphere lays its uvs: u its
    longitude from 0 to 1, v from the south pole (0) to the north (1)."""
    height = width // 2
    u = (np.arange(width) + 0.5) / width
    v = 1.0 - (np.arange(height) + 0.5) / height
    azimuth = 2.0 * np.pi * u[None, :]
    polar = np.pi * (1.0 - v[:, None])
    return np.stack(np.broadcast_arrays(np.sin(polar) * np.sin(azimuth), np.cos(polar) + 0.0 * azimuth,
                                        -np.sin(polar) * np.cos(azimuth)), axis=-1)


def colours():
    """The shader's colours as linear floats, from the palette tokens."""
    found = {}
    for key, token in TOKENS.items():
        value = token_value(token)
        found[key] = srgb_to_linear(np.array([int(value[index:index + 2], 16) / 255.0 for index in (1, 3, 5)]))
    return found


def token_value(name):
    """A colour token's '#rrggbb' from design/tokens/tokens.json."""
    tokens = json.loads((REPO / "design/tokens/tokens.json").read_text())["color"]["tokens"]
    value = next(token["value"] for token in tokens if token["name"] == name)
    return (value if isinstance(value, str) else value["ops"])[:7]


def srgb_to_linear(value):
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(value):
    return np.where(value <= 0.0031308, value * 12.92, 1.055 * np.power(np.clip(value, 0.0, None), 1 / 2.4) - 0.055)


def picture(width=2048):
    """The Earth's surface as an sRGB picture, longitude across and latitude up."""
    way = ways(width)
    paint = colours()
    height = land_height(way)
    land = edge(height, SEA_LEVEL, texel_width(height))
    latitude = np.abs(way[..., 1])
    belt = np.abs(latitude - DESERT_LATITUDE) + (height - SEA_LEVEL) * 0.6
    desert = 1.0 - edge(belt, DESERT_BELT, texel_width(belt))
    ground = paint["land"] + (paint["desert"] - paint["land"]) * desert[..., None]
    surface = paint["ocean"] + (ground - paint["ocean"]) * land[..., None]
    coast = 1.0 - np.clip(np.abs(height - SEA_LEVEL) / np.maximum(texel_width(height) * COAST_PX, 1e-5), 0.0, 1.0)
    surface = surface + (paint["ink"] - surface) * coast[..., None]
    icy = latitude + (height - 0.5) * 0.25
    ice = edge(icy, ICE_FROM, texel_width(icy))
    clouds = cloud_over(way)
    cloud = edge(clouds, CLOUD_LEVEL, texel_width(clouds))
    surface = surface + (paint["cloud"] - surface) * np.maximum(ice, cloud)[..., None]
    return (np.clip(linear_to_srgb(surface), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def write(path, width=2048):
    """The picture saved as PNG at `path` (made once: a picture already there is kept, the bake being seeded)."""
    path = pathlib.Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(picture(width)).save(path)
    return path
