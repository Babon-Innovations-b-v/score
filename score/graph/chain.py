"""A gap's chain: every node that must run so the node that fills a gap is made and its place's line runs to its end,
walked over the stage table's reads, for pricing only. It sits beside rebuy.to_make and never replaces it: the plan
and the run keep their refusals, and this walk buys nothing.

    with runner.still():
        reading = chain.readers(runner, places)                  # {node: the nodes that read it}, once for every gap
        found = chain.gap_chain(runner, stage, place, reading)  # {node: whether its stage is paid}
        whole = chain.line_chain(runner, place, reading)         # the place's whole line to its end (None: the world's)

A node is left out only when it stands: its current output passed and stands accepted at its current key
(Runner.standing). A key that cannot be worked out (a missing input, an earlier node that does not stand) does not
stand: unknown is a gap, never a pass. A node that stands ends the walk on its branch. A node that reads the gap's
node is in the chain when the place's line's ends read it in turn (or it is one), standing or not: it runs again
once the gap's node is made. What those later nodes read and does not stand is in the chain too, so every node the
place needs is priced.

A line's ends are its nodes no node of any line reads: past the place's completion gate, so the films that read it
and the rows that hand the place over are in (in environment 1's table the library row, which reads every row of
the place, the showcase renders too). A read the stage marks optional (read only while usable, Runner.reads) is
walked like any other: a remake makes it (the characters layer's people).
"""
from score.graph import node_name


def reads(runner, stage, place):
    """(stage, place) of every node a node reads once all it may read is made: Runner.read_nodes with its optional
    reads in too (Runner.reads leaves out one not usable now; a remake makes it)."""
    own = [(runner.stages[before], place if runner.stages[before].grain == "place" else None)
           for before in stage.after
           if place is None or runner.stages[before].applies is None or runner.stages[before].applies(place)]
    return own + [(runner.stages[before], other) for before, other, _ in runner.besides(stage, place).values()]


def readers(runner, places):
    """{node: the nodes that read it}, over every node of the places' lines."""
    found = {}
    for stage, place in runner.nodes(places):
        for before in reads(runner, stage, place):
            found.setdefault(node_name(*before), set()).add(node_name(stage, place))
    return found


def upstream(runner, starts):
    """The nodes that do not stand which the `starts` ((stage, place) pairs) read, directly or through other nodes
    that do not stand; the starts themselves left out."""
    seen, found, todo = {node_name(*start) for start in starts}, set(), list(starts)
    while todo:
        for before in reads(runner, *todo.pop()):
            name = node_name(*before)
            if name in seen:
                continue
            seen.add(name)
            if runner.standing(*before) is not None:
                found.add(name)
                todo.append(before)
    return found


def ends(runner, place, reading):
    """(stage, place) of the line's ends: the nodes of the place's line (None: the environment's own nodes) that no
    node reads (`reading`, readers())."""
    return [(stage, at) for stage, at in runner.nodes([] if place is None else [place])
            if at == place and node_name(stage, at) not in reading]


def end_reads(runner, place, reading):
    """The nodes the place's line's ends read, directly or transitively, with the ends themselves."""
    todo = ends(runner, place, reading)
    found = {node_name(*end) for end in todo}
    while todo:
        for before in reads(runner, *todo.pop()):
            if node_name(*before) not in found:
                found.add(node_name(*before))
                todo.append(before)
    return found


def downstream(runner, stage, place, reading):
    """The nodes that read the node of `stage` at `place`, directly or transitively, that the place's line's ends read
    in turn (or are); `reading` is readers()."""
    wanted = end_reads(runner, place, reading)
    found, todo = set(), [node_name(stage, place)]
    while todo:
        for later in reading.get(todo.pop(), ()):
            if later not in found:
                found.add(later)
                todo.append(later)
    return found & wanted


def paid_of(runner, names):
    """{node: whether its stage is paid} of node names."""
    return {name: bool(runner.stages[name.partition("@")[0]].paid) for name in sorted(names)}


def gap_chain(runner, stage, place, reading):
    """{node: whether its stage is paid} of every node in the chain of the gap at `place` whose node is `stage`'s
    there (a world stage's own): that node, the later nodes the place's line's ends read (downstream) and every node
    that does not stand those read (upstream)."""
    later = downstream(runner, stage, place, reading)
    starts = [(stage, None if stage.grain == "world" else place), *runner.nodes_named(later)]
    return paid_of(runner, {node_name(stage, place), *later, *upstream(runner, starts)})


def line_chain(runner, place, reading):
    """{node: whether its stage is paid} of every node the place's line (None: the environment's own nodes) still
    needs to run to its end: each end that does not stand and every node that does not stand those read; empty when
    every end stands."""
    starts = [end for end in ends(runner, place, reading) if runner.standing(*end) is not None]
    return paid_of(runner, {*(node_name(*start) for start in starts), *upstream(runner, starts)})
