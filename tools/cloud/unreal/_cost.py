"""What one Unreal frame cost, from a render job's record (on_card.py) and its run's ledger rows: the whole run's
euros over the full pass's frames (set-up and a cold shader compile included: the price a film pays today), and the
check pass's seconds over its frames, a warm pass (it ran after the full pass had compiled everything; its editor
start and level load included). A run that went
through the box's queue has no rows of its own (its nodes are booked shared): its euros are the job's own minutes at
the card class's list price, and `basis` says so.
"""


def frame_cost(record, rows, card_class, euros_per_minute=None):
    """The cost record of one render job."""
    passes = record["passes"]
    frames = passes["full"]["frames"]
    if rows:
        euros, basis = sum(row["euros"] for row in rows), "the run's ledger rows"
    else:
        euros = euros_per_minute * record["job_seconds"] / 60
        basis = "the job's own minutes at the class's list price (a queue run: its nodes are booked shared)"
    return {"card_class": card_class, "card": record.get("card"), "frames": frames, "euros": round(euros, 4),
            "basis": basis, "euros_per_frame": round(euros / frames, 6),
            "warm_pass_seconds_per_frame": round(passes["check"]["seconds"] / passes["check"]["frames"], 2),
            "seconds": {name: one["seconds"] for name, one in passes.items()}, "job_seconds": record["job_seconds"],
            "shader_cache": {"bytes_before": record["ddc"]["bytes_before"],
                             "bytes_after": record["ddc"]["bytes_after"],
                             "compiled": record["ddc"]["bytes_after"] > record["ddc"]["bytes_before"]}}
