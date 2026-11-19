"""The push gate's refusal of private names (score #142; CLAUDE.md, Deployment: "Nothing from babon or Movalytics
(business files, data, people, clients), no secrets, keys or cloud account and project ids, ever"): a line a push adds
that names another company's cloud project, cluster label or pool, a path in its private repository, or a patent
application number is refused.

    python3 tools/private_names/check.py <base> <tip>   # the lines tip adds over base; base '' = tip's own commit

The names are held as sha256 digests (`NAMES`), so this file never publishes what it refuses; a new one is added as
`hashlib.sha256(name.lower().encode()).hexdigest()`. A line's candidates are its path-like words and every run of
their '/'-parts. `vendor/` is left out. One summary line, then one line a fault (file, line, why).
"""
import hashlib
import re
import subprocess
import sys

NAMES = frozenset((
    "d659463a5305a8deba16cc8ba2a7398fcd94a33544d0f129f48cb66e3b7ca3b2",  # the shared cloud project
    "ca04dcf2ab78b8beed32d579e26180c8fcfebe3d105735d53a9d5a37e01698ae",  # a further cloud project
    "f38e4c507e29e69a8e610ffa8e95ef5f60827849f161cd7e2f8b0620d4722223",  # the operations secrets project
    "a79fb5b2ea55dde04b59534fc0ec51c54ab462cf1d15d09d0e5d24549fcf1d07",  # the cluster's label domain
    "028dff8941d10ea88c5e1961d4ed8ca91378bd181a7018b910ed1178449e967f",  # the cluster's node-role label
    "63299fa0de6fa84319cd9b7de8501b2b6abba94056ec6b2b10bdbd45f7cd4439",  # the conductor's node pool
    "c7ab1bdcc64c3c87a0a6f213d72627eca1c7142b112386f10d1b837c2e2d7616",  # the private infrastructure repository
))
WORD = re.compile(r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*")
PATENT = re.compile(r"\b(?:NL|EP|WO|US)\s?\d{6,}\b")
LEFT_OUT = ("vendor/",)


def candidates(line):
    """Every word of a line, lowercased, and every run of its '/'-parts, each also without trailing dots."""
    found = set()
    for word in WORD.findall(line.lower()):
        parts = word.split("/")
        for start in range(len(parts)):
            for end in range(start + 1, len(parts) + 1):
                joined = "/".join(parts[start:end])
                found.update((joined, joined.rstrip(".")))
    return found


def line_fault(line, names=NAMES):
    """Why a line may not be published, or None."""
    if PATENT.search(line):
        return "a patent application number"
    if any(hashlib.sha256(each.encode()).hexdigest() in names for each in candidates(line)):
        return "a private name (a cloud project, cluster label or pool, or private repository path)"
    return None


def added_lines(base, tip, cwd=None):
    """[(file, line number, text)] of every line tip adds over base (tip's own commit when base is empty)."""
    asked = ["diff", f"{base}..{tip}"] if base else ["show", "--format=", tip]
    diff = subprocess.run(["git", *asked, "-U0", "--no-color", "--no-ext-diff"], cwd=cwd, check=True,
                          capture_output=True, text=True, errors="replace").stdout
    found, path, number = [], None, 0
    for text in diff.splitlines():
        if text.startswith("+++ "):
            path = text[6:] if text.startswith("+++ b/") else None
        elif text.startswith("@@"):
            number = int(re.search(r"\+(\d+)", text).group(1))
        elif text.startswith("+") and path is not None:
            found.append((path, number, text[1:]))
            number += 1
    return [each for each in found if not each[0].startswith(LEFT_OUT)]


def faults(base, tip, cwd=None, names=NAMES):
    """[(file, line number, why)] of the added lines that may not be published."""
    return [(path, number, why) for path, number, text in added_lines(base, tip, cwd)
            if (why := line_fault(text, names))]


def main(argv):
    """0 when no added line names a private name, else 1 with each fault."""
    found = faults(argv[0], argv[1])
    print(f"private names: {len(found)} fault(s)")
    for path, number, why in found:
        print(f"{path}:{number}: {why}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
