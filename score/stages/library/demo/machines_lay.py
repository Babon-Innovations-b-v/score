"""Machines laid on their supports, seen from the side in the hangar: the ship let down onto its bay plate, then its
engines and thrusters mounted on it, each where placed.json (the library's machines layer entry) lays it, and how
well each laid model's outline matches its close-up from the best of eight ways round."""
ALGORITHM = "machines_lay"
PLACE = "hangar"
ENTRY = f"layer/machines.{PLACE}@1"


def side_point(at, lift=0.0):
    """Seen from the side: front to back (the place's z) across, height up."""
    return [round(float(at[2]), 2), round(float(at[1] + lift), 2)]


def words(name):
    return name.replace("_", " ")


def made(inputs):
    machines = inputs.json(ENTRY, "placed.json")["machines"]
    standing = {name: each for name, each in machines.items() if not each.get("mounted")}
    mounted = {name: each for name, each in machines.items() if each.get("mounted")}
    across = [each["at"][2] for each in machines.values()]
    high = max(each["at"][1] + each["dropped"] for each in machines.values())
    return {
        "example": f"the {PLACE}'s ship and its {len(mounted)} engines and thrusters",
        "view": "side", "bounds": [min(across) - 3, -1.0, max(across) + 3, high + 2.0],
        "axes": {"x": "front to back, metres", "y": "height, metres"},
        "steps": [
            {"label": "The ship over what holds it up",
             "shapes": [{"kind": "dots", "points": [side_point(each["at"], each["dropped"])], "r": 0.8, "tone": "base",
                         "id": name, "label": f"{words(name)} over {words(each['on'])}"}
                        for name, each in standing.items()]},
            {"label": "Let down onto it, " + ", ".join(f"{each['dropped']:.2f} m" for each in standing.values()),
             "shapes": [{"kind": "dots", "points": [side_point(each["at"])], "r": 0.8, "tone": "made", "id": name,
                         "label": f"{words(name)} resting on {words(each['on'])}"} for name, each in standing.items()]},
            {"label": "Its engines and thrusters mounted on it",
             "shapes": [{"kind": "dots", "points": [side_point(each["at"])], "r": 0.5, "tone": "c1", "id": name,
                         "label": f"{words(name)} on {words(each['on'])}"} for name, each in mounted.items()]},
            {"label": "Each laid model's outline against its close-up, the best of eight ways round",
             "shapes": [{"kind": "text", "points": [side_point(each["at"], 0.9 + 0.5 * (rank % 2))], "tone": "accent",
                         "label": f"{round(each['outline'] * 100)}%"}
                        for rank, (name, each) in enumerate(machines.items())]}],
        "numbers": [{"label": "machines", "value": len(machines), "unit": "", "tip": "models laid on what holds them"},
                    {"label": "let down", "value": round(max(each["dropped"] for each in standing.values()), 2),
                     "unit": "m", "tip": "how far the ship was let down onto its bay plate"}]}
