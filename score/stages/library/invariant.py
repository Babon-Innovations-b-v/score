"""The library invariant: what an environment holds, what its library holds and what its handovers say, compared, pure.

    found = invariant.problems(environment, places, handed, rows, accepted, configured)
    # {place or "world": [{"rule", "sentence", "address", "node"}]}

The three sets (the wiring contract's C1, the export side left to the cockpit's sync):

    handed      {place or "world": {"node", "output" or None, "why", "report" or None}}: each library node's accepted
                output and its handover.json, else why none stands
    rows        the library's entries, every version: {"address", "kind", "id", "version", "state", "world", "place",
                "node", "output"} (provenance flattened; node and output None for a repo-made entry)
    accepted    {node: its accepted output or None} of every node an entry names

Each mismatch is one problem, said in a plain sentence:

    not handed     a place (or the environment) with no accepted library node
    not in library an address a handover names that the library lacks, or holds withdrawn
    moved on       a newest entry of this environment whose node's accepted output is no longer the one it was made from
    shown nowhere  a newest entry of this environment that no handover names, once its own place's handover stands
    not pushed     a handover whose library commit did not reach its remote

Nothing here reads a file: `sweep.py` gathers the sets and writes the problems where the cockpit reads them.
"""
WORLD = "world"
WITHDRAWN = "withdrawn"


def newest(rows):
    """The newest version of every (kind, id) of the rows, history left out."""
    found = {}
    for row in rows:
        key = (row["kind"], row["id"])
        if key not in found or row["version"] > found[key]["version"]:
            found[key] = row
    return list(found.values())


def problem(rule, sentence, address=None, node=None):
    return {"rule": rule, "sentence": sentence, "address": address, "node": node}


def where_said(where):
    """A place's name as a sentence says it; the environment's own nodes as "the whole environment"."""
    return "the whole environment" if where == WORLD else f"the {where}"


def not_handed(where, held):
    """The problem of a place or environment whose library node stands nowhere, or None when it stands."""
    if held.get("output"):
        return None
    return problem("not handed", f"{where_said(where).capitalize()} is not handed to the library yet "
                                 f"({held['node']}: {held['why']}).", node=held["node"])


def not_in_library(where, report, by_address):
    """Every address the handover names that the library lacks or holds withdrawn."""
    found = []
    for entry in report.get("entries", []):
        address = entry["address"]
        row = by_address.get(address)
        if row is None:
            found.append(problem("not in library", f"{address} is in {where_said(where)} but not in the library.",
                                 address, entry.get("node")))
        elif row["state"] == WITHDRAWN:
            found.append(problem("not in library", f"{address} is in {where_said(where)} but the library has "
                                                   "withdrawn it.", address, entry.get("node")))
    return found


def not_pushed(where, report):
    """The problem of a handover whose library commit did not reach its remote, or None."""
    saved = report.get("saved") or {}
    if not saved.get("committed") or saved.get("pushed"):
        return None
    why = f": {saved['why']}" if saved.get("why") else ""
    return problem("not pushed", f"The library's last handover of {where_said(where)} did not push{why}.")


def home_of(row, handed):
    """Where an entry's problem is shown: its place when that place has a library node, else the environment."""
    return row["place"] if row.get("place") in handed else WORLD


def moved_on(row, accepted, handed):
    """The problem of an entry whose node no longer holds the output it was made from, or None."""
    if not row.get("node") or not row.get("output"):
        return None
    now = accepted.get(row["node"])
    if now == row["output"]:
        return None
    holds = "no longer holds" if now else "no longer has accepted"
    return problem("moved on", f"{row['address']} was made from an output {where_said(home_of(row, handed))} "
                               f"{holds} ({row['node']}).", row["address"], row["node"])


def named_addresses(handed):
    """Every address any accepted handover names."""
    return {entry["address"] for held in handed.values() if held.get("report")
            for entry in held["report"].get("entries", [])}


def handover_problems(handed, by_address):
    """{where: problems} from each library node: not handed, not in library, not pushed."""
    found = {}
    for where, held in handed.items():
        listed = [not_handed(where, held)]
        if held.get("report"):
            listed += not_in_library(where, held["report"], by_address)
            listed.append(not_pushed(where, held["report"]))
        found[where] = [item for item in listed if item]
    return found


def entry_problems(world, rows, accepted, handed):
    """[(where, problem)] from the library's newest entries of this environment: moved on, shown nowhere."""
    named = named_addresses(handed)
    found = []
    for row in newest(rows):
        if row.get("world") != world or row["state"] == WITHDRAWN:
            continue
        where = home_of(row, handed)
        moved = moved_on(row, accepted, handed)
        if moved:
            found.append((where, moved))
        if (handed.get(where) or {}).get("report") and row["address"] not in named:
            found.append((where, problem("shown nowhere", f"The library holds {row['address']}, which no place "
                                                          "of the world shows.", row["address"], row.get("node"))))
    return found


def problems(world, handed, rows, accepted, configured):
    """{place or "world": [problem]} of the environment: every library node's handover against the library's entries.
    With no library configured, one problem a library node, saying so."""
    if not configured:
        return {where: [problem("not handed", f"{where_said(where).capitalize()} is not handed: no library is "
                                              "configured on this machine.", node=held["node"])]
                for where, held in handed.items()}
    by_address = {row["address"]: row for row in rows}
    found = handover_problems(handed, by_address)
    for where, item in entry_problems(world, rows, accepted, handed):
        found.setdefault(where, []).append(item)
    return found
