"""Paid calls only through the clients that write a ledger line before the call: a Gemini call through
google_spend.generate, a Scaleway machine, disk, address or cluster pool through the backends that batch.rent and the
cluster set-up drive. Any other module that calls Gemini directly or orders one of those fails here (2026-10-17: a
Google day billed about EUR 520 the ledger never held, and 21% of the bill was in no ledger row).

Read from each tracked Python file's syntax tree (its imports, its string constants, and the scw words a call is
given), and from the lines of each shell script; vendor/ is third-party and left out.

Run: python3 tools/costs/paid_calls_test.py
"""
import ast
import pathlib
import re
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
# The files that may make a paid call, and why. A new one is added only when it writes its ledger line first.
ALLOWED = {
    "tools/props/cloud/google_spend.py": "the Gemini client: a started line before every call",
    "tools/props/cloud/google_spend_test.py": "the Gemini client's own lint names Google's hosts and clients",
    "tools/props/cloud/backends/scaleway.py": "the machine backend: create writes the started line before its "
                                              "order, under batch.rent; disks and addresses go to the ledger at "
                                              "delete",
    "tools/cloud/k8s/clusters/scaleway.py": "the cluster's own set-up: its pools are the cluster runner's machines",
    "tools/costs/paid_calls_test.py": "this lint and its fixtures",
}
GEMINI_MODULES = ("google.genai", "google.generativeai", "google.cloud.aiplatform", "vertexai")
GEMINI_NAMES = {"genai", "generativeai"}
PAID_TEXT = re.compile(r"generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com|x-goog-api-key|"
                       r"api\.scaleway\.com/(instance|block)/v1/zones/[^/\s]+/(servers|volumes|ips)/?$|"
                       r"api\.scaleway\.com/k8s/v1/regions/[^/\s]+/clusters(/[^/\s]+/pools)?/?$|"
                       r"scw\s+(instance\s+(server|volume|ip)|block\s+volume|k8s\s+(pool|cluster))\s+create")
SCALEWAY_SDK = ("scaleway.instance", "scaleway.block", "scaleway.k8s", "scaleway_core")
# scw's words that order something billed: (product, resource) followed by "create".
SCW_PAID = {("instance", "server"), ("instance", "volume"), ("instance", "ip"), ("block", "volume"),
            ("k8s", "pool"), ("k8s", "cluster")}


def imported_paid_modules(tree):
    """(line, what) for each import of Google's Gemini clients or Scaleway's SDK."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
        else:
            continue
        found += [(node.lineno, f"imports {name}") for name in names
                  if name.startswith(GEMINI_MODULES + SCALEWAY_SDK)
                  or (name.startswith("google.") and name.split(".")[-1] in GEMINI_NAMES)]
    return found


def paid_strings(tree):
    """(line, what) for each string constant that names a paid host, key header or order."""
    return [(node.lineno, f"names {PAID_TEXT.search(node.value).group(0)!r}") for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and PAID_TEXT.search(node.value)]


def call_words(call):
    """The plain string words a call is given, in order, list and tuple arguments opened."""
    words = []
    for argument in call.args:
        items = argument.elts if isinstance(argument, (ast.List, ast.Tuple)) else [argument]
        words += [item.value for item in items if isinstance(item, ast.Constant) and isinstance(item.value, str)]
    return words


def scw_orders(tree):
    """(line, what) for each call given scw words that order a billed resource ("instance", "server", "create")."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        words = call_words(node)
        found += [(node.lineno, f"orders scw {' '.join(words[index:index + 3])}") for index in range(len(words) - 2)
                  if tuple(words[index:index + 2]) in SCW_PAID and words[index + 2] == "create"]
    return found


def python_paid_calls(text):
    """(line, what) for each paid call a Python source makes outside the ledgered clients."""
    tree = ast.parse(text)
    return sorted(imported_paid_modules(tree) + paid_strings(tree) + scw_orders(tree))


def shell_paid_calls(text):
    """(line, what) for each line of a shell script that names a paid host or order."""
    return [(number, f"names {PAID_TEXT.search(line).group(0)!r}")
            for number, line in enumerate(text.splitlines(), 1) if PAID_TEXT.search(line)]


def paid_calls(path):
    """(line, what) for each paid call in one file."""
    text = path.read_text(errors="replace")
    return python_paid_calls(text) if path.suffix == ".py" else shell_paid_calls(text)


def tracked_sources():
    """The repository's tracked Python and shell files outside vendor/, repository-relative."""
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "*.py", "*.sh"], capture_output=True, text=True,
                            check=True).stdout.split()
    return [path for path in listed if not path.startswith("vendor/") and (REPO / path).is_file()]


def fixture(source):
    """A module written to a fresh folder from `source`; its path."""
    path = pathlib.Path(tempfile.mkdtemp()) / "fixture.py"
    path.write_text(source)
    return path


def test_a_module_calling_gemini_directly_fails():
    path = fixture('import urllib.request\n'
                   'URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"\n'
                   'def ask(body):\n'
                   '    return urllib.request.urlopen(urllib.request.Request(URL, data=body))\n')
    assert [line for line, _ in paid_calls(path)] == [2], paid_calls(path)


def test_a_module_loading_googles_client_fails():
    path = fixture("from google import genai\nimport vertexai\n")
    assert [line for line, _ in paid_calls(path)] == [1, 2], paid_calls(path)


def test_a_module_ordering_a_scaleway_machine_or_disk_fails():
    path = fixture('import subprocess\n'
                   'subprocess.run(["scw", "instance", "server", "create", "type=L4-1-24G"])\n'
                   'scw("block", "volume", "create", "size=20GB")\n'
                   'subprocess.run("scw instance ip create zone=fr-par-2", shell=True)\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3, 4], paid_calls(path)


def test_reading_and_deleting_are_not_paid_calls():
    path = fixture('scw("instance", "server", "get", "id")\nscw("instance", "server", "delete", "id")\n'
                   'API = "https://api.scaleway.com/instance/v1/zones/{zone}/servers/{server}/action"\n'
                   'from score.adapters import compute\n')
    assert paid_calls(path) == []


def test_the_repository_makes_paid_calls_only_through_the_ledgered_clients():
    found = {path: calls for path in tracked_sources() if path not in ALLOWED
             for calls in [paid_calls(REPO / path)] if calls}
    assert not found, ("call Gemini through google_spend.generate and rent through batch.rent, not directly: "
                       f"{found}")


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("paid_calls: all checks pass")
