"""A preview clip's views, from the box of what it shows: plain Python (no Blender, no pxr), so the Blender script and
the tests share it. Points are the stage's own (metres, y up); a view is tools/blender/inside/usd_views.py's
(`name`, `eye`, `aim`, `up`, `fov`, `frame`, `look_only`).

    turn   a model, character, kit or surface: the eye goes once round the item at TURN_RISE degrees up
    sweep  a sky or a place's lamps lighting the sample room: the eye goes SWEEP degrees round the room, higher
    play   an effect or a motion: the eye stands at a three-quarter view while its time plays (time_codes)
"""
import math

RATE = 24  # frames a second, the films' (tools/review/demo.py RATE)
SECONDS = 4.0  # a clip's length: one film shot's (score/stages/demo_film SECONDS)
FRAMES = round(RATE * SECONDS)
FOV = 40.0  # degrees across the picture
TURN_RISE = 20.0
SWEEP = 120.0
SWEEP_RISE = 30.0
PLAY_RISE = 25.0
PLAY_HEADING = 35.0
MARGIN = 1.15  # the item's bounding sphere a little inside the picture's height
SMALLEST = 0.05  # metres: a box smaller than this is framed as this (a speck, a point light)
FRAMING = {"model": "turn", "character": "turn", "kit": "turn", "surface": "turn", "sky": "sweep", "lamp": "sweep",
           "effect": "play", "motion": "play"}
ASPECT = 16 / 9


def centre_and_reach(low, high):
    """The box's centre and the radius of its bounding sphere (at least SMALLEST)."""
    centre = [(a + b) / 2 for a, b in zip(low, high)]
    return centre, max(SMALLEST, math.dist(low, high) / 2)


def distance_for(reach, fov=FOV, aspect=ASPECT):
    """How far the eye stands for a sphere of `reach` to fit the picture's height, with MARGIN."""
    tall = 2 * math.atan(math.tan(math.radians(fov) / 2) / aspect)
    return reach * MARGIN / math.sin(tall / 2)


def eye_at(centre, distance, heading, rise):
    """The eye `distance` from `centre` at a heading (degrees round y, 0 looking down -z) and a rise (degrees up)."""
    across, up = math.radians(heading), math.radians(rise)
    flat = distance * math.cos(up)
    return [centre[0] + flat * math.sin(across), centre[1] + distance * math.sin(up),
            centre[2] + flat * math.cos(across)]


def view(number, eye, aim, frame):
    return {"name": f"f{number:03d}", "eye": eye, "aim": aim, "up": [0.0, 1.0, 0.0], "fov": FOV, "frame": frame,
            "look_only": True}


def time_codes(start, end, per_second, frames=FRAMES, rate=RATE):
    """The time code of each frame: real time from `start`, looping over [start, end] where it is shorter than the
    clip, sped up to fit the clip where it is longer (a long move plays whole)."""
    span = max(0.0, end - start)
    step = per_second / rate
    if span > step * (frames - 1):
        step = span / (frames - 1)
    return [start + ((number * step) % (span + per_second / rate) if span else 0.0) for number in range(frames)]


def views(framing, low, high, start=0.0, end=0.0, per_second=RATE, frames=FRAMES):
    """The clip's views of a box (`low`, `high`) by its framing (module docstring)."""
    centre, reach = centre_and_reach(low, high)
    distance = distance_for(reach)
    if framing == "play":
        eye = eye_at(centre, distance, PLAY_HEADING, PLAY_RISE)
        return [view(number, eye, centre, code) for number, code in
                enumerate(time_codes(start, end, per_second, frames))]
    turn, rise = (360.0, TURN_RISE) if framing == "turn" else (SWEEP, SWEEP_RISE)
    return [view(number, eye_at(centre, distance, PLAY_HEADING + turn * number / frames, rise), centre, start)
            for number in range(frames)]
