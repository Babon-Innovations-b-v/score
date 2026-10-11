"""The concept-people stage's commands, on world 1 and the framework's store ($PROPS_HOME/store).

    .venv/bin/python -m score.stages.concept_people status
    .venv/bin/python -m score.stages.concept_people run
    .venv/bin/python -m score.stages.concept_people why
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.stages import concept_people  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.stages.concept_people", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("status", "run", "why"))
    options = parser.parse_args(argv)
    runner = concept_people.runner()
    if options.command == "why":
        print("\n".join(runner.why(concept_people.STAGE.name)))
        return
    found = runner.run([]) if options.command == "run" else runner.status([])
    for node, state in found.items():
        print(f"{node}: {state}")


if __name__ == "__main__":
    main()
