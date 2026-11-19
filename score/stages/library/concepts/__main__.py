"""Run the concept part of the library check alone; exit 1 when a locked concept is not in the library as locked:

    SCORE_LIB_ROOT=<the library folder> .venv/bin/python -m score.stages.library.concepts

Prints one line, and each finding's words below it. Reads the store and the library only.
"""
from score.stages.complete.library import entries, stored
from score.stages.library import concepts


def main():
    shelf = entries.from_environment()
    if shelf is None:
        raise SystemExit("SCORE_LIB_ROOT is not set: the check needs the library folder")
    store = stored.reading()
    found = concepts.findings(store, shelf)
    print(concepts.line(store, found))
    for item in found:
        print(f"  {item['place']}: {item['instead']}")
    raise SystemExit(1 if found else 0)


if __name__ == "__main__":
    main()
