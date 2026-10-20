"""Minutes in words for the pages. The cockpit prices nothing itself: every euro and minute is the runner's
(`score price` through the compute backend, summed by checkout/pricing; ADR-0006)."""


def hours(minutes):
    """Minutes in words: "2 h 05 min" or "14 min"."""
    minutes = int(round(minutes or 0))
    return f"{minutes // 60} h {minutes % 60:02d} min" if minutes >= 60 else f"{minutes} min"
