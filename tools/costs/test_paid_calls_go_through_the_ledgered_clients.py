"""Paid calls only through the clients that write a ledger line before the call: a Gemini call through
google_spend.generate, a Scaleway machine, disk, address or cluster pool through the backends that batch.rent and the
cluster set-up drive. Any other module that calls Gemini directly or orders one of those fails here (2026-10-17: a
Google day billed about EUR 520 the ledger never held, and 21% of the bill was in no ledger row).

Read from each tracked Python file's syntax tree (its imports, by statement or by importlib.import_module or
__import__ given a string; its strings joined with + and f-strings; and the scw words a call is given, read through
variables, joined and starred lists, .append, .extend and .insert), and from the lines of every other runnable file
(shell and other scripts, Makefiles, Dockerfiles, manifests, a #! file with no suffix), a line ending in a backslash
joined with the next; vendor/ is third-party, and docs and data run nothing, so both are left out. A variable is
read as the function it is in set it, in source order, and every setting or growing of one is checked too, so an
order built in one branch counts. A word it cannot read (a function's parameter) between a product and "create"
still counts as an order. It does not follow words across modules, through other functions' return values, through
attributes (self.cmd), lists indexed or sliced, an .insert at an index it cannot read (read as the end), or built
with % or .format.

A wording check by design, guarding the owner's rule (tools/cloud/CLAUDE.md, "Paid calls only through the ledgered
clients"); the lint's own reading is pinned on fixtures whose paid lines are counted by hand.

Break that turns it red: drop "insert" from GROW_ARGUMENTS (an order put together with .insert passes).
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
    "tools/cloud/google_spend.py": ("the Gemini client: a started line before every call", {"URL", "post"}),
    "tools/cloud/google_batch.py": ("the Gemini Batch API client: a started line on google_spend's ledger for "
                                          "each request before its job is sent", {"API", "send", "status"}),
    "tools/cloud/test_google_spend_ledgers_every_call_before_it_is_sent.py": (
        "the Gemini client's own lint names Google's hosts and clients", {"test_no_module_calls_google_another_way"}),
    "tools/cloud/backends/scaleway.py": (
        "the machine backend: create writes the started line before its order, under batch.rent, and the machine's "
        "disks and addresses go to the ledger at its delete. Known gap: quarantine_bad_address's fresh address is "
        "the machine's and ledgered at its delete, but the bad address it detaches stays in the project for good, "
        "billed by the hour with no ledger line (reconcile-day shows it in disks and addresses)",
        {"create", "quarantine_bad_address"}),
    "tools/cloud/k8s/clusters/scaleway.py": ("the cluster set-up: ledger.order_started before each cluster and pool "
                                             "order; the nodes come to the ledger as the submitter's run rows",
                                             {"create_cluster", "ensure_pools"}),
    "tools/cloud/conductor/machine.py": ("the conductor's own set-up, run only by the owner: ledger.order_started "
                                         "before each billed order (address, data volume, server)",
                                         {"address", "data_volume", "make_server"}),
    "score/conductor/logs.py": ("the log scrubber names the Google key header to blank it, calls nothing",
                                {"SECRET_WORDS"}),
    "tools/costs/test_paid_calls_go_through_the_ledgered_clients.py": (
        "this lint's pattern and its fixtures", {"PAID_TEXT", "test_a_module_calling_gemini_directly_fails",
                                        "test_a_module_ordering_a_scaleway_machine_or_disk_fails",
                                        "test_an_address_built_in_an_f_string_fails",
                                        "test_a_shell_order_broken_over_lines_fails",
                                        "test_runnable_files_beyond_python_and_shell_are_read"}),
}
GEMINI_MODULES = ("google.genai", "google.generativeai", "google.cloud.aiplatform", "vertexai")
GEMINI_NAMES = {"genai", "generativeai"}
PAID_TEXT = re.compile(r"generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com|x-goog-api-key|"
                       r"api\.scaleway\.com/(instance|block)/v1[a-z0-9]*/zones/[^/\s]+/(servers|volumes|ips)/?$|"
                       r"api\.scaleway\.com/k8s/v1[a-z0-9]*/regions/[^/\s]+/clusters(/[^/\s]+/pools)?/?$|"
                       r"scw\s+(instance\s+(server|volume|ip)|block\s+volume|k8s\s+(pool|cluster))\s+create")
SCALEWAY_SDK = ("scaleway.instance", "scaleway.block", "scaleway.k8s", "scaleway_core")
DYNAMIC_IMPORTS = {"import_module", "__import__"}
# scw's words that order something billed: (product, resource) followed by "create".
SCW_PAID = {("instance", "server"), ("instance", "volume"), ("instance", "ip"), ("block", "volume"),
            ("k8s", "pool"), ("k8s", "cluster")}
SCW_PRODUCTS = {product for product, _ in SCW_PAID}
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
# The list methods that grow a list of words, by how many arguments each takes.
GROW_ARGUMENTS = {"append": 1, "extend": 1, "insert": 2}
RUNNABLE_SUFFIXES = {".py", ".sh", ".bash", ".lua", ".yaml", ".yml", ".js", ".mjs", ".ts", ".toml"}
RUNNABLE_NAMES = {"Makefile", "Dockerfile"}


def paid_module(name):
    """Whether a module's dotted name is one of Google's Gemini clients or Scaleway's SDK."""
    return (name.startswith(GEMINI_MODULES + SCALEWAY_SDK)
            or (name.startswith("google.") and name.split(".")[-1] in GEMINI_NAMES))


def imported_paid_modules(tree):
    """(line, what) for each import of Google's Gemini clients or Scaleway's SDK, by an import statement or by
    importlib.import_module or __import__ given the module's name as a string."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Call) and called_name(node) in DYNAMIC_IMPORTS and node.args:
            names = [name for name in [string_text(node.args[0])] if name]
        else:
            continue
        found += [(node.lineno, f"imports {name}") for name in names if paid_module(name)]
    return found


def called_name(node):
    """The name a call calls: `f` for f(...) and for x.f(...); None for anything else."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def string_text(node):
    """A string constant's text, or an f-string's with each value it fills in as "{}"; None for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
    return None


def variable_string(assigned, name):
    """The one string a variable holds in `assigned`; None when it holds anything else."""
    words = assigned.get(name)
    return words[0] if words and len(words) == 1 and isinstance(words[0], str) else None


def joined_text(node, assigned):
    """The text a string expression stands for: strings joined with +, an f-string, a variable set to one string
    (in `assigned`), each part it cannot read as "{}"; None when no part of it is a string."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = joined_text(node.left, assigned), joined_text(node.right, assigned)
        return None if left is None and right is None else (left or "{}") + (right or "{}")
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant)
                       else variable_string(assigned, part.value.id) or "{}" if isinstance(part.value, ast.Name)
                       else "{}" for part in node.values)
    if isinstance(node, ast.Name):
        return variable_string(assigned, node.id)
    return string_text(node)


def paid_strings(tree):
    """(line, what) for each string, f-string or joined string that names a paid host, key header or order."""
    states = variable_states(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)):
            continue
        text = joined_text(node, states.get(id(node), {}))
        if text is not None and PAID_TEXT.search(text):
            found.append((node.lineno, f"names {PAID_TEXT.search(text).group(0)!r}"))
    return found


def grown_list(node):
    """(variable, method, its arguments) when `node` is `variable.append(x)`, `variable.extend(x)` or
    `variable.insert(i, x)`; else None."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
            and len(node.args) == GROW_ARGUMENTS.get(node.func.attr)):
        return node.func.value.id, node.func.attr, node.args
    return None


def inserted(words, index_node, word):
    """`words` with `word` put in at the index `index_node` reads as (an int constant); at the end when it cannot be
    read."""
    index = index_node.value if isinstance(index_node, ast.Constant) and type(index_node.value) is int else len(words)
    return words[:index] + [word] + words[index:]


def setting(node, assigned):
    """(variable, its words after) when `node` sets, adds to or grows (.append, .extend, .insert) a variable, read
    from `assigned`, the words its variables hold just before; None for any other node."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, sequence_words(node.value, assigned)
    if isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
        return node.target.id, sequence_words(node.value, assigned)
    if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
        return node.target.id, assigned.get(node.target.id, [None]) + sequence_words(node.value, assigned)
    grown = grown_list(node)
    if grown is None:
        return None
    name, method, arguments = grown
    before = assigned.get(name, [None])
    if method == "extend":
        return name, before + sequence_words(arguments[0], assigned)
    if method == "insert":
        return name, inserted(before, arguments[0], string_text(arguments[1]))
    return name, before + [string_text(arguments[0])]


def scope_members(scope):
    """The nodes a module or function holds itself; a function inside it is a scope of its own, so its body is left
    out (the function's own node stays in)."""
    members, stack = [], list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        members.append(node)
        if not isinstance(node, FUNCTIONS):
            stack.extend(ast.iter_child_nodes(node))
    return members


def scopes(tree):
    """(scope, the scope around it) for the module (None around it) and each function in it, outer before inner."""
    found, waiting = [], [(tree, None)]
    while waiting:
        scope, outer = waiting.pop(0)
        found.append((scope, outer))
        waiting += [(node, scope) for node in scope_members(scope) if isinstance(node, FUNCTIONS)]
    return found


def variable_states(tree):
    """{id(node): {variable: its words}} for each node, as the node's own function (or the module) had set its
    variables just before it in source order, starting from the words the scope around it left; a setting takes
    effect where it ends. So a name two functions both use is read from the function the node is in (review of C1,
    2026-10-17: one module-wide table read one function's call with another's words)."""
    states, left = {}, {None: {}}
    for scope, outer in scopes(tree):
        assigned = left[outer]
        events = []
        for node in scope_members(scope):
            if not hasattr(node, "lineno"):
                continue
            events.append(((node.lineno, node.col_offset, 1), node))
            events.append(((node.end_lineno, node.end_col_offset, 0), node))
        for (_, _, reading), node in sorted(events, key=lambda event: event[0]):
            if reading:
                states[id(node)] = assigned
                continue
            changed = setting(node, states[id(node)])
            if changed is not None:
                assigned = {**assigned, changed[0]: changed[1]}
        left[scope] = assigned
    return states


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
    """(line, what) for each call given, list built with, or variable set or grown to scw words that order a billed
    resource: the words read through variables (as the node's own function set them), joined and starred lists,
    .append, .extend and .insert (sequence_words, setting)."""
    states = variable_states(tree)
    compared = {id(side) for node in ast.walk(tree) if isinstance(node, ast.Compare)
                for side in [node.left, *node.comparators]}
    found = set()
    for node in ast.walk(tree):
        if id(node) in compared or id(node) not in states:  # a test's check (`command[:4] == [...]`) orders nothing
            continue
        assigned = states[id(node)]
        changed = setting(node, assigned)
        if isinstance(node, ast.Call):
            words = [word for argument in node.args for word in sequence_words(argument, assigned)]
        elif isinstance(node, (ast.List, ast.Tuple)) or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            words = sequence_words(node, assigned)
        else:
            words = []
        for run in (words, changed[1] if changed else []):
            found |= {(node.lineno, f"orders scw {order}") for order in orders_in(run)}
    return sorted(found)


def python_paid_calls(text):
    """(line, what) for each paid call a Python source makes outside the ledgered clients."""
    tree = ast.parse(text)
    return sorted(set(imported_paid_modules(tree) + paid_strings(tree) + scw_orders(tree)))


def logical_lines(text):
    """(first line number, text) for each line of a script, a line ending in a backslash joined with the next."""
    lines, start, held = [], None, []
    for number, line in enumerate(text.splitlines(), 1):
        start = number if start is None else start
        if line.rstrip().endswith("\\"):
            held.append(line.rstrip()[:-1])
            continue
        lines.append((start, " ".join(held + [line])))
        start, held = None, []
    return lines + ([(start, " ".join(held))] if held else [])


def shell_paid_calls(text):
    """(line, what) for each line of a script (a shell script, Makefile, Dockerfile, manifest) that names a paid host
    or order, a command broken over lines with a backslash read as one."""
    return [(number, f"names {PAID_TEXT.search(line).group(0)!r}")
            for number, line in logical_lines(text) if PAID_TEXT.search(line)]


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


def runnable(path):
    """Whether a tracked file is code that can run: Python, a shell or other script, a Makefile, a Dockerfile, a
    manifest, or a file with no suffix that starts with #!. Text that runs nothing (docs, data, json) is left out."""
    if path.suffix in RUNNABLE_SUFFIXES or path.name in RUNNABLE_NAMES:
        return True
    return path.suffix == "" and path.read_bytes()[:2] == b"#!"


def tracked_sources():
    """The repository's tracked runnable files outside vendor/, repository-relative."""
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True,
                            check=True).stdout.splitlines()
    return [path for path in listed
            if not path.startswith("vendor/") and (REPO / path).is_file() and runnable(REPO / path)]


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
    assert [line for line, _ in paid_calls(path)] == [3, 4, 6, 7], paid_calls(path)


def test_a_name_two_functions_use_is_read_in_each_functions_own_words():
    """Fault (review of C1, 2026-10-17): variables were one module-wide table with only the last setting by line
    kept, so a call in an earlier function read a later function's words and its order came back clean."""
    path = fixture('import subprocess\n'
                   'def a():\n'
                   '    cmd = ["scw", "instance", "server"]\n'
                   '    subprocess.run(cmd + ["create"])\n'
                   'def b():\n'
                   '    cmd = ["ls"]\n'
                   '    subprocess.run(cmd)\n'
                   'def c():\n'
                   '    api = "https://api.scaleway.com/instance/v1/zones/fr-par-2"\n'
                   '    requests.post(api + "/servers")\n'
                   'def d():\n'
                   '    api = "https://example.org"\n')
    assert [line for line, _ in paid_calls(path)] == [4, 10], paid_calls(path)


def test_an_order_grown_in_one_branch_fails():
    """A list grown to an order in one branch and to something else after it still orders: the growing line itself
    is checked, not only the words left at the call."""
    path = fixture('import subprocess\n'
                   'def a(new):\n'
                   '    cmd = ["scw", "instance", "server"]\n'
                   '    if new:\n'
                   '        cmd.append("create")\n'
                   '    else:\n'
                   '        cmd = ["scw", "instance", "server", "list"]\n'
                   '    subprocess.run(cmd)\n')
    assert [line for line, _ in paid_calls(path)] == [5], paid_calls(path)


def test_an_order_put_together_with_insert_fails():
    """Fault (review of C1, 2026-10-17): .insert was not read, so `cmd.insert(1, "instance")` building an order passed."""
    path = fixture('import subprocess\n'
                   'cmd = ["scw", "server", "create"]\n'
                   'cmd.insert(1, "instance")\n'
                   'subprocess.run(cmd)\n')
    assert [line for line, _ in paid_calls(path)] == [3, 4], paid_calls(path)


def test_googles_client_loaded_by_name_fails():
    """Fault (review of C1, 2026-10-17): only import statements were read, so importlib.import_module("google.genai")
    passed."""
    path = fixture('import importlib\n'
                   'genai = importlib.import_module("google.genai")\n'
                   'scaleway = __import__("scaleway.instance")\n'
                   'json = importlib.import_module("json")\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3], paid_calls(path)


def test_a_shell_order_broken_over_lines_fails():
    """Fault (review of C1, 2026-10-17): shell was matched one line at a time, so `scw instance server \\` with
    `create` on the next line passed."""
    path = pathlib.Path(tempfile.mkdtemp()) / "rent.sh"
    path.write_text('#!/bin/bash\nscw instance server \\\n  create type=L4-1-24G\nscw instance server list\n')
    assert [line for line, _ in paid_calls(path)] == [2], paid_calls(path)


def test_runnable_files_beyond_python_and_shell_are_read():
    """Fault (review of C1, 2026-10-17): only *.py and *.sh were scanned, so an order in a Makefile, Dockerfile,
    manifest or a #! script with no suffix passed. Docs and data are left out: they run nothing."""
    folder = pathlib.Path(tempfile.mkdtemp())
    names = {"Makefile": "rent:\n\tscw instance server create\n", "job.yaml": "args: [scw k8s pool create]\n",
             "hook": "#!/bin/sh\nscw block volume create\n", "notes.md": "scw instance server create\n"}
    for name, text in names.items():
        (folder / name).write_text(text)
    assert sorted(name for name in names if runnable(folder / name)) == ["Makefile", "hook", "job.yaml"]
    assert [line for line, _ in paid_calls(folder / "Makefile")] == [2]


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

