"""Which looks are made in full, from the creator's design alone (data/people/rows.json, score/stages/people_rows.py):
a look a person row of a picked design maps is full when that person fills at least FAR_SHARE of the locked
concept's frame height (the row's `share`, its tallest SAM 3 box over the picture's height, measured by the reading);
under it the person is seen only far off, so the far body serves. A crowd row's look is far always (a crowd maps no
`looks`). A person row with no share measured is full: nothing shows it is far.

The same FAR_SHARE as the cast stage's (score/stages/cast/spread.py) and the completion gate's (tools/usd/contents.py):
a far-only look may fill at most this share of any view's frame height. No imports: a body row's code version takes
this module in, and the completion gate imports it too.
"""
FAR_SHARE = 0.10


def full_looks(record):
    """{look} of every look a person row of the design (`record`, rows.json's content) maps that fills at least
    FAR_SHARE of its concept's frame height, or has no share measured."""
    return {look for entry in record["places"].values() for fields in entry["rows"].values()
            if fields.get("share") is None or fields["share"] >= FAR_SHARE
            for look in fields.get("looks", [])}
