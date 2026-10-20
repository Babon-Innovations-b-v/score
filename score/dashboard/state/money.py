"""The full cost of SCORE this month, one line per source, for the pages and GET /api/money: the lines the store's
machine read (`score spend`: the cloud bill, the model calls' month from their billing export or the owner's books
figure), and the month's total, which says "at least" while any line is partial or missing. Every line says where its
number comes from and when it was read."""
import datetime
import json

from score.dashboard.state.models import CostLine, MonthTotal, MoneyView


def this_month(spend):
    return spend.month or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def lines(spend):
    """[CostLine]: the cloud bill and the model calls' month as the runner read them (`score spend`), each a line
    with no figure when it was not read."""
    measured = {line.source: line for line in spend.lines}
    cloud = measured.get("cloud") or CostLine(source="cloud", label="Cloud compute", partial=True,
                                              origin=spend.note or "the bill was not read")
    models = measured.get("models") or CostLine(source="models", label="Model calls", partial=True,
                                                origin=spend.note or "not read")
    return [cloud, models]


def with_bill_days(spend, home):
    """`spend` with this month's bill days: its lines' figures kept as today's in `home`/bill-days.json (the newest
    read of each day; a line not read keeps the day's earlier figure), every day of its month so far listed. The
    store's machine reads the bills every few minutes; this is the only record of how the month grew."""
    path = home / "bill-days.json"
    days = json.loads(path.read_text()) if path.is_file() else {}
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    read = {line.source: line.euros for line in spend.lines if line.euros is not None}
    days[today] = {**days.get(today, {}), **read}
    home.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.partial")
    partial.write_text(json.dumps(days, sort_keys=True))
    partial.replace(path)
    month = this_month(spend)
    return spend.model_copy(update={"bill_days": [
        {"day": day, "cloud": found.get("cloud"), "models": found.get("models")}
        for day, found in sorted(days.items()) if day.startswith(month)]})


def total(found):
    """The sum of the lines' euros; whole only when no line is partial or missing, else the gaps named."""
    gaps = [line.label for line in found if line.partial or line.euros is None]
    return MonthTotal(euros=round(sum(line.euros or 0.0 for line in found), 2), whole=not gaps, gaps=gaps)


def view(spend):
    """The month, its lines, the total, the environment against its stop, and the shared credit as a note only."""
    found = lines(spend)
    return MoneyView(month=this_month(spend), lines=found, total=total(found), world=spend.world,
                     stop=spend.ceiling, stop_at=spend.stop_at, world_spent=spend.spent, in_flight=spend.reserved,
                     note=spend.note, credit_note=spend.credit_note,
                     paid_refused=spend.paid_refused)
