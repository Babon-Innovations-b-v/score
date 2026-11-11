"""A flat thing the plan stacks on what stands on its holder's top (flat's second blanket, drawn at 0.7 m on the first
blanket on its 0.5 m bed, its middle 1 cm past the bed's side): it is on its holder's top, like one the plan stands at
that top (holders.stands_on_top), never against the holder's side, where it was laid 0.24 m up its bed's side and
floated (settle@flat, 2026-11-11)."""


def on_stack(item, holder_item, plan, reach):
    """Whether the plan stands `item` on a stack on its holder item's top: its shape's base within `reach` of the top
    of a plan item whose footprint meets both its own and the holder's, and whose base is within `reach` of the
    holder's top or of the top of another such item."""
    from score.review.holders import items_of, shape_of
    others = [other for name, other in items_of(plan)[0].items()
              if name not in (item[0], holder_item[0]) and meets(other, holder_item) and meets(other, item)]
    tops, stack_tops, found = {top_of(holder_item[0], plan, shape_of)}, set(), set()
    while True:
        more = {other[0] for other in others if other[0] not in found
                and any(abs(float(shape_of(other[0], plan).get("base") or 0.0) - top) <= reach for top in tops)}
        if not more:
            break
        found |= more
        stack_tops |= {top_of(name, plan, shape_of) for name in more}
        tops |= stack_tops
    base = float(shape_of(item[0], plan).get("base") or 0.0)
    return any(abs(base - top) <= reach for top in stack_tops)


def top_of(name, plan, shape_of):
    """A plan item's top: its shape's base plus tall, metres over the floor."""
    shape = shape_of(name, plan)
    return float(shape.get("base") or 0.0) + float(shape.get("tall") or 0.0)


def meets(item, other):
    """Whether two plan items' footprints (x, y, w, d) overlap."""
    return all(float(item[1 + axis]) < float(other[1 + axis]) + float(other[3 + axis]) and
               float(other[1 + axis]) < float(item[1 + axis]) + float(item[3 + axis]) for axis in (0, 1))
