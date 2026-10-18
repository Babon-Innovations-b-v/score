"""What a plan costs in money and time, from measured runs only; a stage with none falls back to the runner's
estimate and says so. Never per-piece prices alone: the pages show the total against the stop."""
import statistics


def median(values):
    return statistics.median(values) if values else None


def percentile(values, share):
    """The value at `share` (0..1) of the sorted values, nearest rank."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(share * len(ordered)) - 1))]


def by_stage(measured, field):
    """{stage: [values of `field`]} of measured runs that have it."""
    found = {}
    for run in measured:
        value = getattr(run, field)
        if value is not None:
            found.setdefault(run.stage, []).append(float(value))
    return found


def stage_of(node):
    return node.split("@")[0]


def line_of(node):
    return node.split("@")[1] if "@" in node else "world"


def money(buys, measured, bill_factor):
    """{high, likely, not_measured}: high the sum of the runner's estimates (what its clearance reserves); likely
    each paid node at its stage's median measured euros times the bill factor, or its estimate when unmeasured."""
    euros = by_stage(measured, "euros")
    high = sum(float(buy["euros"]) for buy in buys)
    likely, unmeasured = 0.0, []
    for buy in buys:
        found = median(euros.get(stage_of(buy["node"]), []))
        if found is None or float(buy["euros"]) == 0.0:
            likely += float(buy["euros"])
            if found is None and float(buy["euros"]) > 0:
                unmeasured.append(stage_of(buy["node"]))
        else:
            likely += found * bill_factor
    return {"high": round(high, 2), "likely": round(likely, 2), "not_measured": sorted(set(unmeasured))}


def stage_minutes(records):
    """{stage: [minutes]} of finish records that were made, not carried."""
    found = {}
    for record in records:
        if record.get("carried") or record.get("minutes") is None:
            continue
        found.setdefault(record.get("stage") or stage_of(record["node"]), []).append(float(record["minutes"]))
    return found


def line_minutes(nodes, per_stage, pick):
    """{line: minutes} summing each node's `pick` of its stage's minutes (0 when unmeasured)."""
    found = {}
    for node in nodes:
        value = pick(per_stage.get(stage_of(node), [])) or 0.0
        found[line_of(node)] = found.get(line_of(node), 0.0) + value
    return found


def time_of(nodes, per_stage, jobs):
    """{likely_minutes, high_minutes, unmeasured}: likely the larger of the longest line's sum and the total over
    `jobs`, each node at its stage's median; high the same at each stage's 90th percentile."""
    jobs = max(1, int(jobs))

    def span(pick):
        lines = line_minutes(nodes, per_stage, pick)
        return max(max(lines.values(), default=0.0), sum(lines.values()) / jobs)
    return {"likely_minutes": round(span(median), 1),
            "high_minutes": round(span(lambda values: percentile(values, 0.9)), 1),
            "unmeasured": sorted({stage_of(node) for node in nodes if not per_stage.get(stage_of(node))})}


def hours(minutes):
    """Minutes in words: "2 h 05 min" or "14 min"."""
    minutes = int(round(minutes or 0))
    return f"{minutes // 60} h {minutes % 60:02d} min" if minutes >= 60 else f"{minutes} min"
