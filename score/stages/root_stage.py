"""An output's root OpenUSD file, on its own: the assembly and the library check both read it, and the library check
reaching it through the assembly package put the whole assembly into surface-library's code version (every
fitting.py edit re-keyed every place's surface-library row, 2026-10-30)."""


def stage_file(output):
    """The output's root OpenUSD file."""
    found = list(output.glob("*.usda"))
    if len(found) != 1:
        raise FileNotFoundError(f"{output} holds {len(found)} root stages, not one")
    return found[0]
