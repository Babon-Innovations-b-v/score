"""The film rows' free forecast, read before the creator's yes (#21): nothing rented, nothing written to the store.

    .venv/bin/python -m score.stages.demo_film forecast <place>

Prints one line: the film's frames, the cards they are dealt over, its card minutes and euros likely and high, and
what the scan of the place's accepted final stage found (fog, volumes, glass). The film's free frames are
tools/review/film_preview.py's; with both seen, the creator writes `"final": true` in the film's record.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.stages import demo_film  # noqa: E402
from score.store import Store  # noqa: E402


def accepted_final_stage(store, place):
    """The root layer of the place's accepted final stage: its neighbours output where it has one, else its
    assembly."""
    for row in ("neighbours", "assembly"):
        output = store.accepted(f"{row}@{place}")
        if output:
            return pathlib.Path(store.checkout(output)) / f"{place}.usda"
    raise SystemExit(f"{place} has no accepted assembly in the store")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.stages.demo_film", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("forecast",))
    parser.add_argument("place")
    options = parser.parse_args(argv)
    planned = demo_film.forecast(accepted_final_stage(Store.default(), options.place), demo_film.SHOTS)
    print(f"{options.place}: {demo_film.forecast_line(planned)}")


if __name__ == "__main__":
    main()
