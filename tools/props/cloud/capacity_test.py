"""Checks for the capacity lists, the order a fleet takes offers in, the ledger's machine rows and the report,
without renting anything."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402

L4, L40S, H100 = 0.013125, 0.024498, 0.047775


def offer(per_card, stock, machine_type, zone):
    return (per_card, stock, machine_type, zone, per_card * capacity.cards(machine_type))


def test_every_kind_names_known_types():
    for kind, types in capacity.KINDS.items():
        assert types and set(types) <= set(capacity.CARDS), kind
    assert capacity.cards("POP2-32C-128G") == 0
    try:
        capacity.types_for("nothing")
    except SystemExit as refused:
        assert "no machine types" in str(refused)
    else:
        raise AssertionError("an unknown kind was given types")


def test_a_run_takes_the_best_stocked_then_fastest_card_and_spreads_over_zones():
    offers = [offer(L4, 2, "L4-1-24G", "pl-waw-2"), offer(L4, 2, "L4-1-24G", "fr-par-2"),
              offer(L4, 2, "L4-1-24G", "fr-par-1"), offer(H100, 2, "H100-1-80G", "fr-par-2")]
    assert capacity.next_offer(offers, [])[2] == "L4-1-24G"
    rented = [{"zone": "fr-par-1"}]
    assert capacity.next_offer(offers, rented)[3] != "fr-par-1"
    rented += [{"zone": "fr-par-2"}, {"zone": "pl-waw-2"}]
    assert capacity.next_offer(offers, rented)[2] == "L4-1-24G"
    # A bigger card in stock goes before an L4 that is short.
    assert capacity.next_offer(offers + [offer(H100, 0, "H100-1-80G", "pl-waw-2")], [])[2] == "H100-1-80G"
    assert capacity.next_offer([offer(H100, 2, "H100-1-80G", "fr-par-2"), offer(L40S, 2, "L40S-1-48G", "fr-par-2")],
                               [])[2] == "L40S-1-48G"
    assert capacity.next_offer([], []) is None


def test_a_big_card_runs_several_jobs_at_once():
    assert capacity.runs_at_once("pixal", "L4-1-24G") == 3
    assert capacity.runs_at_once("pixal", "L40S-1-48G") == 6
    assert capacity.runs_at_once("pixal", "H100-1-80G") == 10
    assert capacity.runs_at_once("parts", "H100-1-80G") == 1
    assert "RENDER-S" not in capacity.CARDS


def test_hourly_machines_are_billed_by_the_started_hour():
    assert ledger.cost(1.2, L4) == 2 * L4
    assert abs(ledger.cost(61, 1.221 / 60, 60) - 2 * 1.221) < 1e-9


def test_a_machine_row_says_how_long_it_waited_and_worked():
    machine = {"type": "L40S-1-48G", "zone": "fr-par-2", "cards": 1, "price": L40S, "created": 1000.0,
               "ready": 1150.0, "deleted": 1750.0, "unit_seconds": [200.0, 210.0]}
    row = ledger.machine_row(machine)
    assert row["started"] and row["start_wait_minutes"] == 2.5 and row["work_minutes"] == 10.0
    assert row["minutes"] == 12.5 and row["euros"] == 13 * L40S and row["unit_seconds"] == [200.0, 210.0]
    silent = ledger.machine_row(dict(machine, ready=None, deleted=1300.0))
    assert not silent["started"] and silent["start_wait_minutes"] == 5.0 and silent["work_minutes"] == 0.0
    record = ledger.machines_record([machine], [silent, batch.refused_row("L4-1-24G", "pl-waw-2", "out of stock")],
                                    started=900.0)
    assert len(record["attempts"]) == 2 and record["start_wait_minutes"] == 250 / 60
    assert record["euros"] == row["euros"] + silent["euros"]


def test_the_report_groups_by_kind_and_card():
    entries = [{"started": "2026-09-30T10:00:00Z", "machines": [{"type": "L4-1-24G", "zone": "pl-waw-2",
                                                                 "minutes": 30.0, "euros": 0.4}]},
               {"started": "2026-10-08T10:00:00Z", "kind": "pixal",
                "machines": [{"type": "L40S-1-48G", "zone": "fr-par-2", "started": True, "start_wait_minutes": 2.0,
                              "work_minutes": 20.0, "minutes": 22.0, "euros": 0.54,
                              "unit_seconds": [300.0, 320.0, 340.0]}],
                "attempts": [{"type": "L4-1-24G", "zone": "pl-waw-2", "started": False, "minutes": 0.0,
                              "euros": 0.0}]}]
    table = capacity.summarise(capacity.machine_rows(entries))
    by = {(row["kind"], row["type"]): row for row in table}
    assert by[("pixal", "L4-1-24G")]["machines"] == 1 and by[("pixal", "L4-1-24G")]["failed_starts"] == 1
    l40s = by[("pixal", "L40S-1-48G")]
    assert l40s["units"] == 3 and l40s["seconds_a_unit"] == 320.0 and abs(l40s["euros_a_unit"] - 0.18) < 1e-9
    assert len(capacity.summarise(capacity.machine_rows(entries, since="2026-10-01"))) == 2
    assert {row["type"] for row in capacity.summarise(capacity.machine_rows(entries[:1]))} == {"L4-1-24G"}


def test_a_batch_leaves_out_cards_the_limits_cannot_hold():
    found = [offer(L4, 1, "L4-1-24G", "pl-waw-2"), offer(H100, 2, "H100-1-80G", "fr-par-2")]
    kept = batch.affordable(found, minutes=180, cards=20, spent=0)
    assert [item[2] for item in kept] == ["L4-1-24G"]
    assert batch.affordable(found, minutes=30, cards=2, spent=0) == found


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("capacity_test: ok")
