"""Checks for the cloud batch runner's limits, list, inventory refusal and sweep, without renting anything."""
import json
import os
import pathlib
import socket
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import ledger  # noqa: E402

L4 = 0.013125


def test_limits():
    assert ledger.refusal(90, L4, 0) is None
    assert "4 h" in ledger.refusal(241, L4, 0)
    assert "€60" in ledger.refusal(210, 0.3, 0)
    assert "month" in ledger.refusal(60, L4, ledger.MONTH_EUROS - 0.5)
    assert ledger.minutes_allowed(L4, 0) == 240
    assert round(ledger.minutes_allowed(0.3, 0)) == 200
    assert ledger.minutes_allowed(L4, ledger.MONTH_EUROS) == 0
    assert ledger.cost(1.2, L4) == 2 * L4


def test_month_total():
    batches = [{"started": "2026-09-29T10:00:00Z", "euros": 1.5},
               {"started": "2026-08-31T23:00:00Z", "euros": 9.0}]
    assert ledger.month_total("2026-09", batches) == 1.5


def test_list():
    with tempfile.TemporaryDirectory() as folder:
        picture = pathlib.Path(folder) / "crate.png"
        picture.write_bytes(b"")
        listing = pathlib.Path(folder) / "list.txt"
        listing.write_text(f"# approved 2026-09-29\ncrate {picture} --faces 12000 --feet\n\n"
                           f"barrel {picture}  # the tall one\n")
        models = batch.read_list(listing)
        assert [model.name for model in models] == ["crate", "barrel"]
        assert models[0].faces == 12000 and models[0].feet and not models[1].feet
        listing.write_text(f"crate {picture}\ncrate {picture}\n")
        try:
            batch.read_list(listing)
        except SystemExit as refused:
            assert "twice" in str(refused)
        else:
            raise AssertionError("a repeated name was accepted")


def test_fleet_size():
    # 229 models at 3.95 card minutes each, 3 at once, in an hour: 5 min setup and a 12 min last run.
    assert batch.cards_needed(229, 3, 60, 3.95) == 21
    assert round(batch.expected_minutes(229, 21, 3, 3.95)) == 60
    assert batch.cards_needed(5, 3, 60, 3.95) == 1
    try:
        batch.cards_needed(10, 6, 20, 3.95)
    except SystemExit as refused:
        assert "too short" in str(refused)
    else:
        raise AssertionError("a target shorter than one run was accepted")


def test_model_minutes_come_from_the_batch_started_last():
    # A batch stopped part way is written after a later one; its slow rate must not set the estimate.
    entries = [{"started": "2026-09-30T17:56:47Z", "models_done": 5, "card_minutes": 25},
               {"started": "2026-09-30T17:35:47Z", "models_done": 3, "card_minutes": 380}]
    kept, ledger.entries = ledger.entries, lambda: entries
    try:
        assert batch.card_minutes_per_model() == 5
    finally:
        ledger.entries = kept


def test_a_batch_builds_only_an_approved_inventorys_rows():
    with tempfile.TemporaryDirectory() as folder:
        picture = pathlib.Path(folder) / "locker.png"
        picture.write_bytes(b"")
        listing = pathlib.Path(folder) / "list.txt"
        listing.write_text(f"habitat-locker {picture}\nlocker-b {picture}\nr2 {picture}\n")
        models = batch.read_list(listing)
        path = pathlib.Path(folder) / "habitat.json"
        rows = [{"id": "r1", "view": "v1", "box": [0, 0, 9, 9], "name": "locker", "kind": "generate",
                 "anchor": "wall", "size": [0.6, 0.5, 1.9], "count": 1, "thing": "prop:locker"},
                {"id": "r2", "view": "v1", "box": [0, 0, 9, 9], "name": "desk", "kind": "mechanic",
                 "anchor": "floor", "size": [1.6, 0.8, 0.75], "count": 1, "thing": "node:Workstation",
                 "prop": "desk"},
                {"id": "r3", "view": "v1", "box": [0, 0, 9, 9], "name": "sign", "kind": "code",
                 "anchor": "wall", "size": [1.3, 0.03, 0.24], "count": 1, "thing": "gear:sign"}]
        inventory = {"scene": "habitat", "place": "habitat", "plan": {"views": [{"id": "v1"}]},
                     "approved": "", "migrated": "",
                     "room": {"shell": "", "light": "place", "backdrop": "", "wall_fill": []}, "rows": rows}
        for wanted, change in (("no inventory", None), ("not approved", {}), (None, {"approved": "2026-10-05"}),
                               ("no place", {"approved": "2026-10-05", "place": "no_such_place"})):
            if change is not None:
                path.write_text(json.dumps(dict(inventory, **change)))
            try:
                batch.from_the_inventory(models, [path])
            except SystemExit as refused:
                assert wanted and wanted in str(refused), refused
            else:
                assert wanted is None, f"accepted without {wanted}"
        path.write_text(json.dumps(dict(inventory, approved="2026-10-05")))
        listing.write_text(f"sign {picture}\n")
        try:
            batch.from_the_inventory(batch.read_list(listing), [path])
        except SystemExit as refused:
            assert "on no row" in str(refused)
        else:
            raise AssertionError("a code row's fitting was sent to be generated")


def test_a_batch_builds_a_character_only_when_its_spec_is_approved():
    with tempfile.TemporaryDirectory() as folder:
        picture = pathlib.Path(folder) / "tang.png"
        picture.write_bytes(b"")
        spec = {"name": "fish_tang", "kind": "animal", "picture": str(picture), "body": "fish"}
        path = pathlib.Path(folder) / "fish_tang.json"
        for wanted, change in (("not approved", {}), ("no picture", {"approved": "owner", "picture": None}),
                               (None, {"approved": "owner, 2026-10-09"})):
            path.write_text(json.dumps(dict(spec, **change)))
            try:
                models = batch.from_the_characters([path])
            except SystemExit as refused:
                assert wanted and wanted in str(refused), refused
            else:
                assert wanted is None, f"accepted with {wanted}"
        assert [(options.name, options.picture) for options in models] == [("fish_tang", str(picture))]
        try:
            batch.from_the_characters([path, path])
        except SystemExit as refused:
            assert "share a name" in str(refused)
        else:
            raise AssertionError("two specs of one name were both built")


def test_leftovers():
    here = socket.gethostname()
    later = 2e9
    assert batch.is_leftover([], 1e9)
    assert batch.is_leftover([f"deadline={1e9 - 1:.0f}"], 1e9)
    assert not batch.is_leftover([f"deadline={later:.0f}", f"host={here}", f"pid={os.getpid()}"], 1e9)
    assert batch.is_leftover([f"deadline={later:.0f}", f"host={here}", "pid=999999999"], 1e9)
    assert not batch.is_leftover([f"deadline={later:.0f}", "host=elsewhere", "pid=999999999"], 1e9)


def test_a_fleet_short_of_cards_rents_more_as_stock_comes_up():
    import threading
    import time
    import provider

    class Fleet:
        def __init__(self):
            self.stop, self.renting, self.deadline = threading.Event(), threading.Lock(), time.time() + 60
            self.machines, self.offers, self.work = [], [], True

        def no_more_work(self):
            return not self.work
    fleet, rounds = Fleet(), []
    found = [provider.Offer(0.01, 0, "L4", "zone-a", 0.01, "gpu-24gb", 0, "available")]

    def rent_fleet(fleet, cards):
        rounds.append(cards)
        if len(rounds) < 3:
            return 0  # out of stock on the first rounds
        fleet.machines.append({"cards": cards, "deleted": None})
        fleet.work = False
        fleet.machines[-1]["deleted"] = time.time()
        return cards
    kept = batch.rent_fleet, batch.cloud.offers, batch.STOCK_RETRY_MINUTES, batch.time.sleep
    batch.rent_fleet, batch.cloud.offers = rent_fleet, lambda classes: list(found)
    batch.STOCK_RETRY_MINUTES, batch.time.sleep = 0, lambda seconds: None
    try:
        batch.keep_the_fleet(fleet, found, 2)
    finally:
        batch.rent_fleet, batch.cloud.offers, batch.STOCK_RETRY_MINUTES, batch.time.sleep = kept
    assert rounds == [2, 2, 2] and fleet.offers == found


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("batch_test: ok")
