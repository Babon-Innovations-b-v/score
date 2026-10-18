"""The full cost of SCORE this month, one line per source, for the pages and GET /api/money: the measured lines the store's
machine read (pages read them from the Spend), the owner's own figures where nothing measured is whole (the model
provider's bill, the subscriptions), and the month's total, which says "at least" while any line is partial or missing. Every
line says where its number comes from and when it was read."""
import datetime

from score.dashboard.pages.models import OwnerCost
from score.dashboard.state.models import CostLine, MonthTotal, MoneyView

SOURCES = {"models": "Model calls", "subscriptions": "Subscriptions"}


def this_month(spend):
    return spend.month or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def owner_figure(source, month):
    """The owner's newest figure for `source` that stands in `month`: the model bill's for that month only, the
    subscriptions' from their month on; None when he entered none."""
    entries = OwnerCost.objects.filter(source=source)
    entries = entries.filter(month=month) if source == "models" else entries.filter(month__lte=month)
    return entries.order_by("-month", "-at").first()


def entered_line(source, entry, label):
    """The owner's figure as a cost line."""
    words = f" ({entry.words})" if entry.words else ""
    return CostLine(source=source, label=label, euros=entry.euros,
                    origin=f"the owner's figure{words}, entered by {entry.by}",
                    read_at=entry.at.isoformat(timespec="seconds"))


def models_line(measured, month):
    """The model provider bill's figure when the owner entered this month's, else the call ledger's partial count."""
    entry = owner_figure("models", month)
    if entry is None:
        return measured or CostLine(source="models", label=SOURCES["models"], partial=True,
                                    origin="not read and not entered")
    line = entered_line("models", entry, measured.label if measured else SOURCES["models"])
    if measured and measured.euros is not None:
        line.origin += f"; SCORE's own ledger counts EUR {measured.euros:.2f} of it"
    return line


def subscriptions_line(month):
    entry = owner_figure("subscriptions", month)
    if entry is None:
        return CostLine(source="subscriptions", label=SOURCES["subscriptions"], partial=True,
                        origin="not entered yet: the owner enters the fixed monthly figure")
    return entered_line("subscriptions", entry, SOURCES["subscriptions"])


def lines(spend):
    """[CostLine]: the cloud bill, the model calls, the subscriptions."""
    month = this_month(spend)
    measured = {line.source: line for line in spend.lines}
    cloud = measured.get("cloud") or CostLine(source="cloud", label="Cloud compute", partial=True,
                                              origin=spend.note or "the bill was not read")
    return [cloud, models_line(measured.get("models"), month), subscriptions_line(month)]


def total(found):
    """The sum of the lines' euros; whole only when no line is partial or missing, else the gaps named."""
    gaps = [line.label for line in found if line.partial or line.euros is None]
    return MonthTotal(euros=round(sum(line.euros or 0.0 for line in found), 2), whole=not gaps, gaps=gaps)


def view(spend):
    """The month, its lines, the total, the environment against its stop, and the shared credit as a note only."""
    found = lines(spend)
    return MoneyView(month=this_month(spend), lines=found, total=total(found), world=spend.world,
                     stop=spend.ceiling, stop_at=spend.stop_at, world_spent=spend.spent, in_flight=spend.reserved,
                     note=spend.note, credit_note=spend.credit_note)
