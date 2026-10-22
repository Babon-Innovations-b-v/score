"""Which natural ground recipe (tools/props/library/recipes.py: regolith, rock, sand, ocean, ice) a body's face or an
outdoor ground is made with, by rule (2026-10-22: before it, both took the nearest man-made recipe). Never a body's or
a place's name, never a picture's colour: a ground row's own words where they name one, else its body's physics.

    of_body(body, bodies, table) -> (recipe, why)       from the body's physics; (None, what is missing) when the
                                                         setting does not give it
    of_row(row, body, bodies, table) -> (recipe, why)   a ground row of a scene inventory (its name and noun), else
                                                         its body's; None for a made ground (a plaza, a road: MADE),
                                                         whose recipe the scene's ask picks

The physics (each rule set 2026-10-22, before any ground was made by it): its surface pressure (the setting's own,
else the cited reference table's, data/physics/bodies.json, as the sound stage's beds read it) and its equilibrium
temperature at zero albedo (none is known: the star's kelvin times the root of its radius over twice the body's
distance from it, a moon at its planet's distance), against water's phases:
    ocean     liquid water stands: the pressure at least water's triple point, the temperature from its triple point
              to its boiling at that pressure (Clausius-Clapeyron from 373.15 K at 101.325 kPa)
    rock      the pressure holds water, the temperature over its boiling there: a hot, dry world bare to the rock
    ice       colder than ICE_K: water ice lasts on its surface
    sand      an air of at least WIND_KPA, whose wind lays the dust in drifts
    regolith  none of these: an airless body's dust, ground by impacts
"""
import math
import re

RECIPES = ("regolith", "rock", "sand", "ocean", "ice")
WATER_TRIPLE_KPA = 0.611657  # water's triple point: 611.657 Pa at 273.16 K (IAPWS)
WATER_TRIPLE_K = 273.16
BOILING_K, BOILING_KPA = 373.15, 101.325  # water's normal boiling point
VAPORISATION_J_MOL = 40650.0  # water's enthalpy of vaporisation at its boiling point
GAS_J_MOL_K = 8.314462618
# Set between the outer giants' icy moons (about 120 K at zero albedo) and the dusty inner asteroid belt (about 170 K).
ICE_K = 150.0
# Set under Mars's 0.636 kPa, whose wind lays its dust in dunes, and far over an airless body's.
WIND_KPA = 0.1
# A ground row's words that name its recipe, before its body's physics; the first recipe whose word it holds.
WORDS = {"ocean": ("sea", "ocean", "water", "lake", "bay", "harbour", "harbor", "waves"),
         "ice": ("ice", "icy", "snow", "frost", "frozen", "glacier"),
         "sand": ("sand", "sandy", "dune", "dunes", "desert", "beach"),
         "rock": ("rock", "rocks", "rocky", "boulder", "boulders", "cliff", "cliffs", "outcrop", "bedrock", "stone",
                  "stones"),
         "regolith": ("regolith", "dust", "dusty")}
# A ground row's words that say people made it (paved, laid, built): no natural ground; its recipe is the ask's.
MADE = ("plaza", "square", "pavement", "paving", "paved", "concrete", "asphalt", "road", "street", "deck", "floor",
        "tiles", "tiled", "courtyard", "pad", "runway", "platform")


def boiling_k(kpa):
    """Water's boiling point at `kpa` (Clausius-Clapeyron from its normal boiling point)."""
    return 1.0 / (1.0 / BOILING_K - GAS_J_MOL_K * math.log(kpa / BOILING_KPA) / VAPORISATION_J_MOL)


def pressure_kpa(body, table):
    """The body's surface pressure: the setting's own, else the reference table's; None when neither gives one."""
    real = (table or {}).get("bodies", {}).get(body.get("reference") or body["body"], {})
    return body.get("surface_pressure_kpa", real.get("surface_pressure_kpa"))


def warmth_k(body, bodies):
    """The body's equilibrium temperature at zero albedo from the star it or its planet orbits; None with no star."""
    by_key = {entry["body"]: entry for entry in bodies}
    child, parent = body, by_key.get(body.get("around"))
    while parent is not None and parent.get("kelvin") is None:
        child, parent = parent, by_key.get(parent.get("around"))
    if parent is None or not child.get("distance_km"):
        return None
    return parent["kelvin"] * math.sqrt(parent["radius_km"] / (2.0 * child["distance_km"]))


def of_body(body, bodies, table):
    """(the recipe the body's physics calls for, why), or (None, what the setting does not give)."""
    kpa, kelvin = pressure_kpa(body, table), warmth_k(body, bodies)
    name = body.get("name") or body["body"].title()
    if kpa is None or kelvin is None:
        return None, f"{name}: no {'surface pressure' if kpa is None else 'star to warm it'} in the setting"
    said = f"{name}: {kpa:.3g} kPa, {kelvin:.0f} K at zero albedo"
    if kpa >= WATER_TRIPLE_KPA and kelvin >= WATER_TRIPLE_K:
        boils = boiling_k(kpa)
        if kelvin <= boils:
            return "ocean", f"{said}: liquid water stands (boiling at {boils:.0f} K there)"
        return "rock", f"{said}: over water's boiling at {boils:.0f} K there, dry to the rock"
    if kelvin < ICE_K:
        return "ice", f"{said}: under {ICE_K:.0f} K, water ice lasts"
    if kpa >= WIND_KPA:
        return "sand", f"{said}: an air of at least {WIND_KPA} kPa drifts its dust"
    return "regolith", f"{said}: airless, its dust ground by impacts"


def of_row(row, body, bodies, table):
    """(the recipe a ground row is made with, why): one its own words name, else its body's (of_body); None for a
    ground its words say people made (MADE) and on a plot, which has no physics of a body."""
    words = set(re.findall(r"[a-z]+", f"{row.get('name') or ''} {row.get('noun') or ''}".lower()))
    named = next((recipe for recipe, said in WORDS.items() if words & set(said)), None)
    if named:
        return named, f"the row {row.get('id')} says {sorted(words & set(WORDS[named]))[0]}"
    if words & set(MADE):
        return None, f"the row {row.get('id')} says {sorted(words & set(MADE))[0]}: a made ground, no natural one"
    if body is None:
        return None, f"the row {row.get('id')} names no ground and stands on no body of the setting"
    return of_body(body, bodies, table)
