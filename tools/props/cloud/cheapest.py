"""The cheapest card that fits a job (owner, 2026-10-12: L4 before H100 unless the job needs 80 GB or an H100 is
measured faster per euro; no H100 for bakes or Blender).

Measured per job, October 2026 (`capacity.py report`): Blender EUR 0.23 on an L4 against 0.86 on an H100 (an H100 has
no ray-tracing cores); the mesh splitting (meshparts) EUR 0.14 and 387 s on an L4 against 0.73 and 609 s on an H100;
the close-up judge EUR 0.33 and 627 s on an L40S against 0.78 and 662 s on an H100. Those three runs cost EUR 360 on
H100s in October. capacity.py's order takes the best stocked offer first, so an H100 in stock beat a scarce L4.
"""
# The 80 GB cards: the H100s.
BIG = ("gpu-80gb", "gpu-80gb-x2")


def never_big(classes):
    """The classes without the 80 GB cards, for work that never takes one (Blender, bakes)."""
    kept = [machine_class for machine_class in classes if machine_class not in BIG]
    if not kept:
        raise SystemExit(f"only 80 GB cards asked for ({', '.join(classes)}); Blender and bakes never take one "
                         "(owner, 2026-10-12): ask for gpu-24gb, gpu-48gb or a processor class")
    return kept


def big_last(offers):
    """The offers without the 80 GB cards while a smaller card is to be had (not out of stock), else all of them:
    for work that fits a smaller card and is cheaper per job on it."""
    smaller = [offer for offer in offers if offer.machine_class not in BIG]
    return smaller if any(offer.stock_word != "shortage" for offer in smaller) else list(offers)
