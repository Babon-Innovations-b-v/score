"""The names the owner sees for library entries: everyday words, no asides, brackets or technical terms (owner,
2026-10-20: "Camera moves: RRT* walk paths and film shots (the render needs a GPU)" was a jargon title). The library's
own title stays as hover text (`about`); ids and addresses never change.

    plain(kind, entry_id, title)   # (the name shown, the library's title when it differs, else "")
"""
import re

ALGORITHMS = {  # an algorithm's name, by its id: the physics setups, then the code that makes other things
    "body_weight": "A body's weight and material", "drop": "A drop onto its target",
    "hinge_motor": "A hinge with its limits and motor", "planet_gravity": "A planet's gravity and orbits",
    "push": "A push by an unseen hand", "physics_layer": "Weight, hinges and motors",
    "settle": "Things settling into rest", "snap": "Things snapped into place",
    "camera_paths": "Camera paths", "cast_spread": "People in groups and crowds", "crops_spots": "Crops on beds",
    "far_city": "Distant city skyline", "ground_detail": "Ground detail and rocks", "light_rig": "Lamps and light",
    "machines_lay": "Machines on their stands", "mars_sky": "Mars daytime sky", "motion": "Moving things",
    "motion_movers": "Moving things", "particle_effects": "Dust, smoke and steam",
    "room_layout": "Furniture laid out in a room", "sky_dust_stars_haze": "Stars, dust and haze",
    "sky_orbits": "Sun, Earth and stars moving across the sky", "sound_layer": "A place's sound mix",
    "surface_recipes": "Surface finishes", "terrain_landforms": "Landscape shapes"}
WORDS = [  # (a pattern of the library's title, the everyday words), applied in order
    (re.compile(r"\bAc unit\b", re.I), "Air conditioner"), (re.compile(r"\bTv\b"), "TV"),
    (re.compile(r"\blkr\b"), "locker"), (re.compile(r"\bMed\b"), "Medical"), (re.compile(r"\bmed\b"), "medical"),
    (re.compile(r"\bNav\b"), "Navigation"), (re.compile(r"\bDesklamp\b", re.I), "Desk lamp"),
    (re.compile(r"\blabbench\b"), "lab bench"), (re.compile(r"\btalllocker\b"), "tall locker"),
    (re.compile(r"\bengineroom\b", re.I), "Engine room"), (re.compile(r"^Kit_m_avg\b"), "Man of average build,"),
    (re.compile(r"^Far\b"), "Distant"), (re.compile(r"\b(\d+)p(\d+)\b"), r"\1.\2 m"),
    (re.compile(r"_"), " ")]
GRID = re.compile(r"^(?P<name>.*\D) (?P<row>\d+) (?P<spot>\d+)$")  # an effect laid on a grid: "Drift 0 3"
ASIDE = re.compile(r"^(?P<name>.*?) \((?P<aside>[^()]*)\)$")  # "Flat ground (earth)"


def without_aside(title):
    """A trailing bracketed aside said in words, after a comma."""
    found = ASIDE.match(title)
    if not found:
        return title
    return f"{found['name']}, {found['aside']}"


def everyday(title):
    """The library's title with its abbreviations, sizes and underscores in everyday words."""
    for pattern, words in WORDS:
        title = pattern.sub(words, title)
    grid = GRID.match(title)
    if grid:
        title = f"{grid['name']}, row {int(grid['row']) + 1} spot {int(grid['spot']) + 1}"
    return re.sub(r"\s+", " ", title).strip()


def plain(kind, entry_id, title):
    """(the name the owner sees, the library's own title when it differs from it, else "")."""
    shown = ALGORITHMS.get(entry_id) if kind == "algorithm" else None
    shown = shown or everyday(without_aside(title.replace(" light layer", " lamps")))
    shown = shown[:1].upper() + shown[1:]
    return shown, (title if shown != title else "")
