"""This month's Google bill, read (read-only) from Cloud Billing's standard usage cost export in BigQuery, through
the bq CLI logged in on this PC.

    google_bill.month_euros("2026-10")   # cost plus credits for invoice month 202610, in EUR; Unread when it cannot

The export table is named by SCORE_GOOGLE_BILLING_TABLE, else by the one line of $PROPS_HOME/cloud/google-billing-table
(`<project>.<dataset>.<table>`; a trailing `*` matches Google's gcp_billing_export_v1_<account> table before its
account is known). Neither the project nor the billing account is ever written in this repository (it is public).
The export fills within hours of being switched on and lags the bill by hours, like the Scaleway bill.
"""
import json
import os
import subprocess

from paths import HOME

TABLE = "SCORE_GOOGLE_BILLING_TABLE"
SETTINGS = HOME / "cloud" / "google-billing-table"
# The most a read may scan (about EUR 0.006 at on-demand prices); a larger scan fails rather than pays.
MAX_BYTES = 1_000_000_000
READ_SECONDS = 120


class Unread(Exception):
    """The Google bill could not be read: no export table is set, it does not exist yet, or it holds no EUR rows."""


def table():
    """The export table's full name (TABLE, else the SETTINGS file), or None when neither sets one."""
    named = os.environ.get(TABLE, "").strip()
    if not named and SETTINGS.exists():
        named = SETTINGS.read_text().strip()
    return named or None


def month_query(name, month):
    """The SQL summing cost plus credits per currency for invoice month `month` (YYYY-MM) in table `name`."""
    return (f"SELECT currency, SUM(cost) + SUM(IFNULL((SELECT SUM(credit.amount) FROM UNNEST(credits) AS credit), 0)) "
            f"AS euros, COUNT(*) AS lines FROM `{name}` WHERE invoice.month = '{month.replace('-', '')}' "
            f"GROUP BY currency")


def run_query(name, sql):
    """The rows bq returns for `sql`, run in `name`'s project; Unread with bq's own words when it fails."""
    done = subprocess.run(["bq", "--headless", "query", "--use_legacy_sql=false", "--format=json",
                           f"--project_id={name.split('.')[0]}", f"--maximum_bytes_billed={MAX_BYTES}", sql],
                          capture_output=True, text=True, timeout=READ_SECONDS)
    if done.returncode != 0:
        said = " ".join((done.stderr or done.stdout).split())
        raise Unread(f"the Google billing export could not be read ({TABLE}): {said}")
    return json.loads(done.stdout) if done.stdout.strip() else []


def euros_of(rows, month):
    """The month's euros in the export's rows (month_query's); Unread when it has no rows yet or bills another
    currency."""
    if not rows:
        raise Unread(f"the Google billing export holds no rows for {month} yet (it fills within hours of being "
                     "switched on)")
    currencies = sorted(row["currency"] for row in rows)
    if currencies != ["EUR"]:
        raise Unread(f"the Google billing export bills {currencies} for {month}, not EUR alone")
    return float(rows[0]["euros"])


def month_euros(month):
    """What Google billed for invoice month `month` (YYYY-MM) so far, in EUR, cost plus credits; Unread when not
    readable."""
    name = table()
    if name is None:
        raise Unread(f"no Google billing export table is set ({TABLE}, or one line in {SETTINGS})")
    return euros_of(run_query(name, month_query(name, month)), month)
