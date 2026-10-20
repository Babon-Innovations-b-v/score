"""The money data: the month's cost one line per source as the runner read it, a total that says it is not whole while
a line is partial or missing, the environment against the stop the last batch's yes wrote (no stop is set from the
cockpit), and a hosted page never getting a broken picture."""
import pytest
from django.test import override_settings

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
    assert [line.source for line in shown.lines] == ["cloud", "models"]
    assert not shown.total.whole and shown.total.gaps == ["Model calls"]
    assert shown.total.euros == 2517.93
    assert shown.stop is None and "no stop set" in shown.note


def test_a_month_the_runner_could_not_read_has_no_figure_and_is_not_whole():
    unread = Spend(world="world1", month=MONTH, lines=[
        CostLine(source="cloud", label="Cloud compute", euros=2117.93, origin="the cloud bill"),
        CostLine(source="models", label="Model calls", euros=None, partial=True, origin="the export holds no rows")])
    shown = money.view(unread)
    assert shown.lines[1].euros is None and not shown.total.whole and shown.total.euros == 2117.93
    assert [line.source for line in money.view(Spend(note="spend not read")).lines] == ["cloud", "models"]


def test_the_runners_whole_lines_make_the_month_whole_against_the_last_batchs_stop():
    whole = measured(stop=900.0)
    whole.lines[1] = CostLine(source="models", label="Model calls", euros=1012.5, origin="the billing export")
    shown = money.view(whole)
    assert shown.total.whole and shown.total.euros == 3130.43
    assert (shown.stop, shown.world_spent, shown.in_flight) == (900.0, 120.0, 30.0)


def test_anyone_signed_in_reads_the_money_and_no_stop_or_cost_is_set_from_the_cockpit(world):
    owner = api("joey")
    MoneyView.model_validate(owner.get("/api/money").json())
    for route in ("/api/money/owner-costs", "/api/money/stop", "/api/money/month"):
        assert owner.post(route, json={"euros": 5}).status_code in (404, 405)


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
