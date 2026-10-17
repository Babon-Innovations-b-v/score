"""Paid calls only through the clients that write a ledger line before the call: a Gemini call through
google_spend.generate, a Scaleway machine, disk, address or cluster pool through the backends that batch.rent and the
cluster set-up drive. Any other module that calls Gemini directly or orders one of those fails here (2026-10-17: a
Google day billed about EUR 520 the ledger never held, and 21% of the bill was in no ledger row).

Read from each tracked Python file's syntax tree (its imports, its strings joined with + and f-strings, and the scw
words a call is given, read through variables, joined and starred lists, .append and .extend), and from the lines of
each shell script; vendor/ is third-party and left out. A word it cannot read (a function's parameter) between a
product and "create" still counts as an order. It does not follow words across modules, through other functions'
return values, or built with % or .format.

Run: python3 tools/costs/paid_calls_test.py
"""
import ast
import pathlib
import re
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
# The files that may make a paid call: (why, the top-level functions and constants it may be in). A paid call
# anywhere else in the file fails as in any other. A new one is added only when it writes its ledger line first.
ALLOWED = {
    "tools/props/cloud/google_spend.py": ("the Gemini client: a started line before every call", {"URL", "post"}),
    "tools/props/cloud/google_spend_test.py": ("the Gemini client's own lint names Google's hosts and clients",
                                               {"test_no_module_calls_google_another_way"}),
    "tools/props/cloud/backends/scaleway.py": (
        "the machine backend: create writes the started line before its order, under batch.rent, and the machine's "
        "disks and addresses go to the ledger at its delete. Known gap: quarantine_bad_address's fresh address is "
        "the machine's and ledgered at its delete, but the bad address it detaches stays in the project for good, "
        "billed by the hour with no ledger line (reconcile-day shows it in disks and addresses)",
        {"create", "quarantine_bad_address"}),
    "tools/cloud/k8s/clusters/scaleway.py": ("the cluster set-up: ledger.order_started before each cluster and pool "
                                             "order; the nodes come to the ledger as the submitter's run rows",
                                             {"create_cluster", "ensure_pools"}),
    "tools/costs/paid_calls_test.py": ("this lint's pattern and its fixtures",
                                       {"PAID_TEXT", "test_a_module_calling_gemini_directly_fails",
                                        "test_a_module_ordering_a_scaleway_machine_or_disk_fails",
                                        "test_an_address_built_in_an_f_string_fails"}),
}
GEMINI_MODULES = ("google.genai", "google.generativeai", "google.cloud.aiplatform", "vertexai")
GEMINI_NAMES = {"genai", "generativeai"}
PAID_TEXT = re.compile(r"generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com|x-goog-api-key|"
                       r"api\.scaleway\.com/(instance|block)/v1[a-z0-9]*/zones/[^/\s]+/(servers|volumes|ips)/?$|"
                       r"api\.scaleway\.com/k8s/v1[a-z0-9]*/regions/[^/\s]+/clusters(/[^/\s]+/pools)?/?$|"
                       r"scw\s+(instance\s+(server|volume|ip)|block\s+volume|k8s\s+(pool|cluster))\s+create")
SCALEWAY_SDK = ("scaleway.instance", "scaleway.block", "scaleway.k8s", "scaleway_core")
# scw's words that order something billed: (product, resource) followed by "create".
SCW_PAID = {("instance", "server"), ("instance", "volume"), ("instance", "ip"), ("block", "volume"),
            ("k8s", "pool"), ("k8s", "cluster")}
SCW_PRODUCTS = {product for product, _ in SCW_PAID}


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


def string_text(node):
    """A string constant's text, or an f-string's with each value it fills in as "{}"; None for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
    return None


def joined_text(node, strings):
    """The text a string expression stands for: strings joined with +, an f-string, a variable set to one string
    (`strings`), each part it cannot read as "{}"; None when no part of it is a string."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = joined_text(node.left, strings), joined_text(node.right, strings)
        return None if left is None and right is None else (left or "{}") + (right or "{}")
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant)
                       else strings.get(part.value.id, "{}") if isinstance(part.value, ast.Name) else "{}"
                       for part in node.values)
    if isinstance(node, ast.Name):
        return strings.get(node.id)
    return string_text(node)


def paid_strings(tree):
    """(line, what) for each string, f-string or joined string that names a paid host, key header or order."""
    strings = {name: words[0] for name, words in assigned_words(tree).items()
               if len(words) == 1 and isinstance(words[0], str)}
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)):
            continue
        text = joined_text(node, strings)
        if text is not None and PAID_TEXT.search(text):
            found.append((node.lineno, f"names {PAID_TEXT.search(text).group(0)!r}"))
    return found


def grown_list(node):
    """(variable, method, its argument) when `node` is `variable.append(x)` or `variable.extend(x)`; else None."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
            and node.func.attr in ("append", "extend") and len(node.args) == 1):
        return node.func.value.id, node.func.attr, node.args[0]
    return None


def assigned_words(tree):
    """{variable: its words} for each variable a module sets, adds to, or grows (.append, .extend) with words, in
    source order, the last setting kept."""
    assigned = {}
    settings = sorted((node for node in ast.walk(tree)
                       if isinstance(node, (ast.Assign, ast.AugAssign)) or grown_list(node)),
                      key=lambda node: (node.lineno, node.col_offset))
    for node in settings:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assigned[node.targets[0].id] = sequence_words(node.value, assigned)
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
            assigned[node.target.id] = assigned.get(node.target.id, [None]) + sequence_words(node.value, assigned)
        elif isinstance(node, ast.Call):
            name, method, argument = grown_list(node)
            added = sequence_words(argument, assigned) if method == "extend" else [string_text(argument)]
            assigned[name] = assigned.get(name, [None]) + added
    return assigned


def sequence_words(node, assigned):
    """The words an expression stands for, in order: a string, a list or tuple opened (starred lists too), lists
    joined with +, a variable set to words; None for each part it cannot read, so words never join across it."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return [word for item in node.elts for word in sequence_words(item, assigned)]
    if isinstance(node, ast.Starred):
        return sequence_words(node.value, assigned)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return sequence_words(node.left, assigned) + sequence_words(node.right, assigned)
    if isinstance(node, ast.Name):
        return assigned.get(node.id, [None])
    return [string_text(node)]


def orders_in(words):
    """The scw orders of billed resources ("instance server create") in a run of words; a word that cannot be read
    (None, as a function's parameter) between a product and "create" counts as an order."""
    return [" ".join(str(word) for word in words[index:index + 3]) for index in range(len(words) - 2)
            if words[index + 2] == "create" and (tuple(words[index:index + 2]) in SCW_PAID
                                                 or (words[index] in SCW_PRODUCTS and words[index + 1] is None))]


def scw_orders(tree):
    """(line, what) for each call given, or list built with, scw words that order a billed resource: the words read
    through variables, joined and starred lists (sequence_words)."""
    assigned = assigned_words(tree)
    compared = {id(side) for node in ast.walk(tree) if isinstance(node, ast.Compare)
                for side in [node.left, *node.comparators]}
    found = set()
    for node in ast.walk(tree):
        if id(node) in compared:  # a test's check of what was ordered (`command[:4] == [...]`) orders nothing
            continue
        if isinstance(node, ast.Call):
            words = [word for argument in node.args for word in sequence_words(argument, assigned)]
        elif isinstance(node, (ast.List, ast.Tuple)) or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            words = sequence_words(node, assigned)
        else:
            continue
        found |= {(node.lineno, f"orders scw {order}") for order in orders_in(words)}
    return sorted(found)


def python_paid_calls(text):
    """(line, what) for each paid call a Python source makes outside the ledgered clients."""
    tree = ast.parse(text)
    return sorted(set(imported_paid_modules(tree) + paid_strings(tree) + scw_orders(tree)))


def shell_paid_calls(text):
    """(line, what) for each line of a shell script that names a paid host or order."""
    return [(number, f"names {PAID_TEXT.search(line).group(0)!r}")
            for number, line in enumerate(text.splitlines(), 1) if PAID_TEXT.search(line)]


def paid_calls(path):
    """(line, what) for each paid call in one file."""
    text = path.read_text(errors="replace")
    return python_paid_calls(text) if path.suffix == ".py" else shell_paid_calls(text)


def top_level_spans(tree):
    """(name, first line, last line) of each top-level function, class and constant of a module."""
    spans = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            spans.append((node.name, node.lineno, node.end_lineno))
        elif isinstance(node, ast.Assign):
            spans += [(target.id, node.lineno, node.end_lineno) for target in node.targets
                      if isinstance(target, ast.Name)]
    return spans


def outside_allowed(path, names):
    """(line, what) for each paid call in one file outside its top-level functions and constants named in `names`."""
    found = paid_calls(path)
    if path.suffix != ".py" or not names:
        return found
    spans = [(first, last) for name, first, last in top_level_spans(ast.parse(path.read_text(errors="replace")))
             if name in names]
    return [(line, what) for line, what in found if not any(first <= line <= last for first, last in spans)]


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


def test_an_order_built_before_its_call_fails():
    """Fault (review, 2026-10-17): only words passed straight into one call were read, so an order put in a variable
    first, a list with more joined on, or a starred list came back clean."""
    path = fixture('import subprocess\n'
                   'cmd = ["scw", "instance", "server", "create"]\n'
                   'subprocess.run(cmd)\n'
                   'subprocess.run(["scw", "block", "volume", "create"] + extra)\n'
                   'subprocess.run([*["scw", "instance", "ip", "create"], "zone=fr-par-2"])\n'
                   'base = ["scw", "k8s", "pool"]\n'
                   'subprocess.run(base + ["create", "size=0"])\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3, 4, 5, 7], paid_calls(path)


def test_an_address_built_in_an_f_string_fails():
    """Fault (review, 2026-10-17): an f-string splits into pieces, so the address was never seen whole; and the
    block API is v1alpha1, which a v1-only pattern missed."""
    path = fixture('zone = "fr-par-2"\n'
                   'SERVERS = f"https://api.scaleway.com/instance/v1/zones/{zone}/servers"\n'
                   'VOLUMES = "https://api.scaleway.com/block/v1alpha1/zones/fr-par-2/volumes"\n'
                   'ORDER = f"scw instance server create zone={zone}"\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3, 4], paid_calls(path)


def test_an_order_grown_by_append_or_extend_fails():
    """Fault (review of C1, 2026-10-17): a list grown with .append or .extend was read only as first set, so an order
    finished by one came back clean."""
    path = fixture('import subprocess\n'
                   'cmd = ["scw", "instance", "server"]\n'
                   'cmd.append("create")\n'
                   'subprocess.run(cmd)\n'
                   'disk = ["scw", "block"]\n'
                   'disk.extend(["volume", "create"])\n'
                   'subprocess.run(disk)\n')
    assert [line for line, _ in paid_calls(path)] == [4, 7], paid_calls(path)


def test_an_order_whose_resource_is_a_parameter_fails():
    """Fault (review of C1, 2026-10-17): a word given as a function's parameter cannot be read, so
    `scw("instance", what, "create")` came back clean. A product's create with an unread word between still orders."""
    path = fixture('def order(what):\n'
                   '    scw("instance", what, "create")\n'
                   'def look(what):\n'
                   '    scw("instance", what, "list")\n')
    assert [line for line, _ in paid_calls(path)] == [2], paid_calls(path)


def test_an_address_joined_from_strings_fails():
    """Fault (review of C1, 2026-10-17): only one string at a time was matched, so an order's address joined from a
    base and a path (with + or inside an f-string) came back clean."""
    path = fixture('import requests\n'
                   'API = "https://api.scaleway.com/instance/v1"\n'
                   'requests.post(API + f"/zones/{zone}/servers")\n'
                   'requests.post(f"{API}/zones/{zone}/ips")\n'
                   'requests.get(API + f"/zones/{zone}/servers/{server}/action")\n')
    assert [line for line, _ in paid_calls(path)] == [3, 4], paid_calls(path)


def test_an_allowed_file_may_order_only_in_its_named_parts():
    """Fault (review of C1, 2026-10-17): ALLOWED covered whole files, so a paid call added anywhere in the backend or
    in this file passed. A call in an allowed file passes only inside the top-level functions or constants named."""
    path = fixture('def create():\n'
                   '    scw("instance", "server", "create")\n'
                   'def later():\n'
                   '    scw("instance", "ip", "create")\n')
    assert [line for line, _ in outside_allowed(path, {"create"})] == [4], outside_allowed(path, {"create"})


def test_reading_and_deleting_are_not_paid_calls():
    path = fixture('scw("instance", "server", "get", "id")\nscw("instance", "server", "delete", "id")\n'
                   'assert command[:4] == ["scw", "instance", "server", "create"]\n'
                   'API = "https://api.scaleway.com/instance/v1/zones/{zone}/servers/{server}/action"\n'
                   'from score.adapters import compute\n')
    assert paid_calls(path) == []


def test_the_repository_makes_paid_calls_only_through_the_ledgered_clients():
    found = {path: calls for path in tracked_sources()
             for calls in [outside_allowed(REPO / path, ALLOWED.get(path, ("", set()))[1])] if calls}
    assert not found, ("call Gemini through google_spend.generate and rent through batch.rent, not directly: "
                       f"{found}")


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("paid_calls: all checks pass")
