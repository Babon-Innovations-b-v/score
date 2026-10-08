"""Checks for the capacity lists, the order a fleet takes offers in, the ledger's machine rows and the report,
without renting anything."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
import secret_store  # noqa: E402

L4, L40S, H100 = 0.013125, 0.024498, 0.047775


def offer(per_card, stock, machine_class, zone, order=0):
    return provider.Offer(per_card, stock, f"{machine_class}-type{order}", zone,
                          per_card * max(1, provider.cards(machine_class)), machine_class, order, "")


def test_every_kind_names_capability_classes():
    for kind, classes in capacity.KINDS.items():
        assert classes and all(provider.cards(machine_class) for machine_class in classes), kind
    assert provider.cards("cpu-32c-128gb") == 0 and provider.cards("gpu-80gb-x2") == 2
    assert provider.card_gb("gpu-48gb") == 48
    for wrong in ("L4-1-24G", "gpu"):
        try:
            provider.cards(wrong)
        except SystemExit as refused:
            assert "capability class" in str(refused)
        else:
            raise AssertionError(f"{wrong} was taken for a capability class")
    try:
        capacity.classes_for("nothing")
    except SystemExit as refused:
        assert "no capability classes" in str(refused)
    else:
        raise AssertionError("an unknown kind was given classes")


def test_a_run_takes_the_best_stocked_then_fastest_card_and_spreads_over_zones():
    offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(L4, 2, "gpu-24gb", "zone-b"),
              offer(L4, 2, "gpu-24gb", "zone-c"), offer(H100, 2, "gpu-80gb", "zone-b")]
    assert capacity.next_offer(offers, []).machine_class == "gpu-24gb"
    rented = [{"zone": "zone-c"}]
    assert capacity.next_offer(offers, rented).zone != "zone-c"
    rented += [{"zone": "zone-a"}, {"zone": "zone-b"}]
    assert capacity.next_offer(offers, rented).machine_class == "gpu-24gb"
    # A bigger card in stock goes before a 24 GB card that is short.
    assert capacity.next_offer(offers + [offer(H100, 0, "gpu-80gb", "zone-a")], []).machine_class == "gpu-80gb"
    assert capacity.next_offer([offer(H100, 2, "gpu-80gb", "zone-b"), offer(L40S, 2, "gpu-48gb", "zone-b")],
                               []).machine_class == "gpu-48gb"
    # Within a class, the backend's own order.
    assert capacity.next_offer([offer(H100, 2, "gpu-80gb-x2", "zone-a", 1), offer(H100, 2, "gpu-80gb-x2", "zone-b", 0)],
                               []).order == 0
    assert capacity.next_offer([], []) is None


def test_each_kind_takes_cards_in_its_own_order():
    offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a"),
              offer(L40S, 2, "gpu-48gb", "zone-a")]
    assert capacity.next_offer(offers, [], "pixal").machine_class == "gpu-80gb"
    assert capacity.next_offer(offers, [], "library").machine_class == "gpu-24gb"
    assert capacity.next_offer(offers[1:], [], "library").machine_class == "gpu-48gb"
    assert capacity.next_offer(offers, [], "parts").machine_class == "gpu-24gb"
    assert "gpu-80gb" in capacity.late_for("library") and not capacity.late_for("pixal")


def test_a_bake_takes_a_card_without_ray_tracing_cores_only_after_the_wait():
    taken = []

    def claim_from(run, account, offers, number, kind, disk_gb=batch.DISK_GB):
        taken.append(sorted({item.machine_class for item in offers}))
        return None if "gpu-80gb" not in taken[-1] else "machine"
    kept_claim, kept_sleep, kept_minutes = batch.claim_from, batch.time.sleep, capacity.LATE_MINUTES
    batch.claim_from, batch.time.sleep, capacity.LATE_MINUTES = claim_from, lambda seconds: None, 0
    try:
        offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a")]
        assert batch.claim(None, None, offers, 1, "library") == "machine"
        assert taken == [["gpu-24gb"], ["gpu-80gb"]]
        taken.clear()
        assert batch.claim(None, None, offers, 1, "pixal") == "machine" and taken == [["gpu-24gb", "gpu-80gb"]]
    finally:
        batch.claim_from, batch.time.sleep, capacity.LATE_MINUTES = kept_claim, kept_sleep, kept_minutes


def test_a_big_card_runs_several_jobs_at_once():
    assert capacity.runs_at_once("pixal", "gpu-24gb") == 3
    assert capacity.runs_at_once("pixal", "gpu-48gb") == 6
    assert capacity.runs_at_once("pixal", "gpu-80gb") == 10
    assert capacity.runs_at_once("parts", "gpu-80gb") == 1


def test_every_backend_class_is_a_capability_class():
    for machine_class in provider.cloud.CLASSES:
        provider.cards(machine_class)


def test_a_secret_comes_from_the_environment_first():
    import os
    os.environ["SCORE_SECRET_SOME_API_KEY"] = "from-the-environment"
    try:
        assert secret_store.environment_name("some-api-key") == "SCORE_SECRET_SOME_API_KEY"
        assert secret_store.secret("some-api-key") == "from-the-environment"
    finally:
        del os.environ["SCORE_SECRET_SOME_API_KEY"]


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
    record = ledger.machines_record([machine], [silent, batch.refused_row(offer(L4, 2, "gpu-24gb", "zone-a"), "out of stock")],
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
    found = [offer(L4, 1, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-b")]
    kept = batch.affordable(found, minutes=180, cards=20, spent=0)
    assert [item.machine_class for item in kept] == ["gpu-24gb"]
    assert batch.affordable(found, minutes=30, cards=2, spent=0) == found


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("capacity_test: ok")
