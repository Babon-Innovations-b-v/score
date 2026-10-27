"""A place's concept light as an input (reading.concept_light, kept by plans.keep under {home}/design/light): its own
module, so the light rows read it without the writer's code or the plan review's (2026-10-27)."""
from score.store import PROPS_HOME

KEPT_LIGHT = PROPS_HOME / "design" / "light"  # plans.KEPT_LIGHT, held equal by the scene record's test


def concept_light_input(place):
    """{"concept light": its kept path pattern} once the place's concept's light is read (reading.concept_light,
    kept by plans.keep), else {}: a place read before it was asked keeps its row-kind lamps alone."""
    return {"concept light": "{home}/design/light/{place}.json"} if (KEPT_LIGHT / f"{place}.json").is_file() else {}
