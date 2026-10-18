"""The money data: the month's cost one line per source with the owner's own figures where nothing measured is whole,
a total that says it is not whole while a line is partial or missing, the world against its stop line, the owner-only
figure entry, and a hosted page never getting a broken picture."""
import pytest
from django.test import override_settings

from score.dashboard.pages import actions
from score.dashboard.state import money
from score.dashboard.state.models import CostLine, MoneyView, Spend
from score.dashboard.tests.api_test import api

pytestmark = pytest.mark.django_db(transaction=True)
MONTH = "2026-10"


def measured(stop=None):
    """A Spend as the store's machine reads it: the cloud bill whole, the model call ledger partial."""
    return Spend(spent=None if stop is None else 120.0, reserved=None if stop is None else 30.0, ceiling=stop,
                 world="world1", month=MONTH, note="" if stop else "world1: no stop set, paid launches refused",
                 lines=[CostLine(source="cloud", label="Cloud compute", euros=2117.93, origin="the cloud bill"),
                        CostLine(source="models", label="Model calls", euros=400.0, partial=True,
                                 origin="the call ledger")])


def test_a_partial_line_is_never_the_total():
    shown = money.view(measured())
    assert [line.source for line in shown.lines] == ["cloud", "models", "subscriptions"]
    assert not shown.total.whole and set(shown.total.gaps) == {"Model calls", "Subscriptions"}
    assert shown.total.euros == 2517.93
    assert shown.stop is None and "no stop set" in shown.note


def test_the_owners_figures_make_the_month_whole():
    assert actions.enter_cost("joey", "models", "1012.50", "the bill", MONTH).startswith("entered")
    assert actions.enter_cost("joey", "subscriptions", "800", "four seats", "2026-09").startswith("entered")
    shown = money.view(measured(stop=900.0))
    by_source = {line.source: line for line in shown.lines}
    assert by_source["models"].euros == 1012.5 and not by_source["models"].partial
    assert "ledger counts EUR 400.00" in by_source["models"].origin
    assert by_source["subscriptions"].euros == 800.0 and "four seats" in by_source["subscriptions"].origin
    assert shown.total.whole and shown.total.euros == 3930.43
    assert (shown.stop, shown.world_spent, shown.in_flight) == (900.0, 120.0, 30.0)


def test_a_model_bill_stands_for_its_own_month_only():
    actions.enter_cost("joey", "models", "1000", "", "2026-09")
    assert money.view(measured()).lines[1].euros == 400.0


def test_an_entry_that_is_not_a_figure_is_refused():
    assert actions.enter_cost("joey", "cloud", "5", "", MONTH).startswith("refused")
    assert actions.enter_cost("joey", "models", "lots", "", MONTH).startswith("refused")
    assert actions.enter_cost("joey", "models", "-3", "", MONTH).startswith("refused")


def test_only_the_owner_enters_a_figure_and_anyone_signed_in_reads_the_money(world):
    assert api("mallory").post("/api/money/owner-costs", json={"source": "models", "euros": 5}).status_code == 403
    owner = api("joey")
    assert owner.post("/api/money/owner-costs", json={"source": "models", "euros": 5}).status_code == 200
    assert owner.post("/api/money/owner-costs", json={"source": "cloud", "euros": 5}).status_code == 422
    MoneyView.model_validate(owner.get("/api/money").json())


@override_settings(SCORE_MODE="hosted")
def test_a_hosted_picture_not_yet_up_is_a_stand_in_never_a_broken_image(world):
    sha, owner = "a" * 64, api("joey")
    for path in (f"/files/{sha}", f"/thumbs/{sha}.jpg"):
        answer = owner.get(path)
        assert answer.status_code == 200 and answer.headers["content-type"].startswith("image/svg+xml")
        assert "picture on its way" in answer.text and answer.headers["cache-control"] == "no-store"
    assert owner.get("/files/not-a-sha").status_code == 404


def test_a_local_picture_that_is_not_there_stays_a_404(world):
    assert api("joey").get(f"/thumbs/{'b' * 64}.jpg").status_code == 404
