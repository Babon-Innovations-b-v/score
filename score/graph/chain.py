"""A hole's chain: every node that must run so the node that fills a hole is made and its place is complete, walked
over the stage table's reads, for pricing only. It sits beside rebuy.to_make and never replaces it: the plan and the
run keep their refusals, and this walk buys nothing.

    with runner.still():
        reading = chain.readers(runner, places)                # {node: the nodes that read it}, once for every hole
        found = chain.hole_chain(runner, stage, place, reading)  # {node: whether its stage is paid}

A node is left out only when it stands: its current output passed and stands accepted at its current key
(Runner.standing). A key that cannot be worked out (a missing input, an earlier node that does not stand) does not
stand: unknown is a hole, never a pass. A node that stands ends the walk on its branch. A node that reads the hole's
node is in the chain when the place's completion node reads it in turn, standing or not: it runs again once the
hole's node is made. What those later nodes read and does not stand is in the chain too, so every node the place
needs is priced.
"""
from score.graph import node_name

COMPLETE = "complete"  # the completion gate's stage: a hole's place is complete when its node stands


def readers(runner, places):
    """{node: the nodes that read it}, over every node of the places' lines."""
    found = {}
    for stage, place in runner.nodes(places):
        for before in runner.read_nodes(stage, place):
            found.setdefault(node_name(*before), set()).add(node_name(stage, place))
    return found


def upstream(runner, starts):
    """The nodes that do not stand which the `starts` ((stage, place) pairs) read, directly or through other nodes
    that do not stand; the starts themselves left out."""
    seen, found, todo = {node_name(*start) for start in starts}, set(), list(starts)
    while todo:
        for before in runner.read_nodes(*todo.pop()):
            name = node_name(*before)
            if name in seen:
                continue
            seen.add(name)
            if runner.standing(*before) is not None:
                found.add(name)
                todo.append(before)
    return found


def completion_reads(runner, place):
    """The nodes the place's completion node reads, directly or transitively, with the completion node itself; none
    when the place has no completion node."""
    stage = runner.stages.get(COMPLETE)
    if stage is None or (stage.applies is not None and not stage.applies(place)):
        return set()
    found, todo = {node_name(stage, place)}, [(stage, place)]
    while todo:
        for before in runner.read_nodes(*todo.pop()):
            if node_name(*before) not in found:
                found.add(node_name(*before))
                todo.append(before)
    return found


def downstream(runner, stage, place, reading):
    """The nodes that read the node of `stage` at `place`, directly or transitively, that the place's completion node
    reads in turn (or is); `reading` is readers()."""
    wanted = completion_reads(runner, place)
    found, todo = set(), [node_name(stage, place)]
    while todo:
        for later in reading.get(todo.pop(), ()):
            if later not in found:
                found.add(later)
                todo.append(later)
    return found & wanted


def hole_chain(runner, stage, place, reading):
    """{node: whether its stage is paid} of every node in the chain of the hole at `place` whose node is `stage`'s
    there (a world stage's own): that node, the later nodes the place's completion reads (downstream) and every node
    that does not stand those read (upstream)."""
    later = downstream(runner, stage, place, reading)
    starts = [(stage, None if stage.grain == "world" else place), *runner.nodes_named(later)]
    names = {node_name(stage, place), *later, *upstream(runner, starts)}
    return {name: bool(runner.stages[name.partition("@")[0]].paid) for name in sorted(names)}
