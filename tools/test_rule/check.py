"""The guard on the test rule (docs/bible.md workflow/module-standard; owner, 2026-10-26: "only 1 but one actual good
meaning full test file per module ... i feel like that rule kinda drifted by now"): it lists every way the repository's
test files break the rule, so the rule cannot drift again. `make tests` runs it and fails on any fault.

    python3 tools/test_rule/check.py                 # every module in the repository
    python3 tools/test_rule/check.py <test file> ... # only the modules those files belong to

A test file is a file named `test_*.py` or `*_test.py`, tracked or new (not ignored), outside `vendor/`. Its faults:

- **named for its module, not its invariant**: every test file is `test_<invariant>.py`.
- **no break**: its module docstring has no line naming the break that turns it red ("break" and "red" in one statement,
  at most 200 characters apart, as "Breaks (each applied once, seen red, reverted), in ...:").
- **more than one test function in a file** (owner, 2026-11-01): a test file holds ONE `test_*` function (a method of
  a `Test*` class counts); parametrized cases of one check are one function. A script-style file's checks count the
  same (2026-11-07): each entry of its top-level `CHECKS` and each top-level `def check_*`, a name counted once. A
  docstring line starting `second test:` with a reason excuses it, but only up to the count the file has on
  origin/main (one for a file not there): a note never grows a file. `FUNCTION_DEBT` holds the files over it that day
  with their count: one may not grow, one that shrank must lower its entry, one down to one test (or gone) must lose it.
- **tests that run only under `__main__`**: a test file with an `if __name__ == ...` block and no `test_*` function
  holds checks pytest never finds. `MAIN_ONLY` lists the files that did so on 2026-11-07; it only shrinks.
- **a SyntaxWarning** (an invalid escape sequence, say) is a fault of the file that raises it.
- **more than one test file in a module**: a module is the directory its test file sits in, a `tests/` folder counting
  as its parent's (`.claude/hooks/tests` is `.claude/hooks`). In a flat folder of independent tools (`FLAT_TOOL_FOLDERS`)
  a top-level test file belongs to the tool script its docstring names first (as `tools/<folder>/<tool>.py`, else as
  `<tool>.py`, else as the bare name), and one that names none is a fault of its own.

- **stacked old tests** (owner, 2026-11-13): two or more of the file's own asserting functions in one literal that a
  loop walks calling them, or that a parametrize hands the test, are old tests renamed and called from a list.

Over the whole tree (no files named), its modules are found from the tree, not from its test files (#121): each folder
holding a .py file of code (no test file, conftest.py or empty __init__.py), a `tests/` folder its parent's and a flat
tool folder's script its own, is a module, and each folder under which two or more modules sit a module group. A
module with no test is a fault, and so is a group with no test in its own folder, unless `UNTESTED` (or `UNGROUPED`)
names it: those list what had none on 2026-11-25, and only shrink.

`ALLOWLIST` holds the modules other agents' sweeps are still reworking, dated, each pattern with the test files and
test functions it covered on 2026-11-07; like `FUNCTION_DEBT` it only shrinks (a pattern covering more is a fault, one
covering less must lower its entry, one covering none must go), and nothing else goes in it.

    python3 tools/test_rule/check.py --ran <test file> <its output file>

is the run's own fault (`make tests` asks it for each file whose output says skipped): a file that printed a line
starting `skipped`, or whose pytest summary is skips only, did not run, unless `MAY_SKIP` names it with the reason.
The output is one summary line, then one line a fault.
"""
import ast
import fnmatch
import functools
import pathlib
import re
import subprocess
import sys
import warnings

REPO = pathlib.Path(__file__).resolve().parents[2]

# Folders of independent command-line tools: each top-level tool script is a module of its own.
FLAT_TOOL_FOLDERS = ("tools/cloud", "tools/props", "tools/review", "tools/usd")

# Modules still being swept by other agents on 2026-10-26: skipped until their sweep empties the entry. Each pattern
# holds (test files, test functions) it covered when recounted on 2026-11-07; only ever shrinks.
ALLOWLIST_DATE = "2026-10-26"
ALLOWLIST_COUNT_DATE = "2026-11-07"
ALLOWLIST = {
    "tools/usd/*": (21, 144),
    "score/stages/complete/*": (8, 94),
    "score/stages/props/*": (4, 55),
    "score/stages/settling/*": (1, 17),
    "score/stages/physics/*": (1, 9),
    "*prepare*": (1, 32),
}

# Test files whose checks ran only under `__main__` on 2026-11-07 (pytest finds none of them); only ever shrinks.
MAIN_ONLY_DATE = "2026-11-07"
MAIN_ONLY = (
    "score/stages/sim_body/inside/batched/test_every_frame_on_the_card_is_mujocos_own_to_its_rounding.py",
    "score/stages/sim_body/inside/bone_groups/test_each_segment_rides_and_groups_bodies_of_its_side_joint_to_joint.py",
    "score/stages/sim_body/inside/calibration/test_the_calibration_lays_each_bone_along_its_segment.py",
    "score/stages/sim_body/inside/contact/test_only_a_point_within_gap_is_pushed.py",
    "score/stages/sim_body/inside/fit/_card/tests/test_the_card_step_and_projection_equal_the_cpu_prototype.py",
    "score/stages/sim_body/inside/fit/test_the_solver_gives_back_the_pose_and_constants_that_made_its_targets.py",
    "score/stages/sim_body/inside/ground/test_a_point_stands_on_the_highest_ground_in_reach.py",
    "score/stages/sim_body/inside/landmarks/test_every_landmark_resolves_on_both_models_where_worked_by_hand.py",
    "score/stages/sim_body/inside/model/test_couplings_keep_a_follower_on_its_leader.py",
    "score/stages/sim_body/inside/muscles/test_a_standing_body_is_carried_by_the_ground.py",
    "score/stages/sim_body/inside/myo/test_the_persons_file_builds_in_newton_as_mujoco_compiles_it.py",
    "score/stages/sim_body/inside/records/test_a_record_keeps_poses_meshes_and_moves_as_worked_by_hand.py",
    "score/stages/sim_body/inside/resting/test_no_muscle_stands_past_its_resting_length.py",
    "score/stages/sim_body/inside/rra/test_rra_moves_mass_and_torso_by_the_mean_residual.py",
    "score/stages/sim_body/inside/sizing/test_a_sized_group_is_somas_length_and_weight.py",
)

# Test files that may print `skipped` (a check not run on this box), each with the reason.
MAY_SKIP = {
    "score/stages/sim_body/inside/*": "needs a GPU: run by hand (make tests) on a GPU box",
    "tools/usd/test_a_hollow_body_keeps_its_hollow.py": "two of its drops need the Newton env, which needs a GPU",
    "score/stages/settling/test_the_settle_layer_lays_and_its_gate_fails_a_broken_drop.py":
        "its two room drops need the Newton env, which needs a GPU",
    "score/stages/place_build/ready/test_every_planted_physics_fault_is_told_by_name.py":
        "its MuJoCo settle needs the physics trial's Python (newton_env.sh); a sandbox home has none: link it in by hand",
    "score/stages/physics/test_the_trial_comes_from_the_design_and_each_gate_fails_its_break.py":
        "its adopted-model reading needs the physics trial's Python (newton_env.sh); a sandbox home has none: link it in "
        "by hand",
}

# Test files holding more than one test function on 2026-11-01 (118 files, 2139 functions over one), each
# with its count that day, and the script-style files counted from 2026-11-07 (their `CHECKS` and `check_*`
# functions) at their count that day; only ever shrinks.
FUNCTION_DEBT_DATE = "2026-11-01"
FUNCTION_DEBT = {
    "score/graph/test_a_key_is_made_once_from_accepted_inputs.py": 4,
    "score/stages/sim_body/inside/bone_groups/test_each_segment_rides_and_groups_bodies_of_its_side_joint_to_joint.py": 2,
    "score/stages/sim_body/inside/calibration/test_the_calibration_lays_each_bone_along_its_segment.py": 8,
    "score/stages/sim_body/inside/contact/test_only_a_point_within_gap_is_pushed.py": 5,
    "score/stages/sim_body/inside/evaluation/test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py": 9,
    "score/stages/sim_body/inside/fit/test_the_solver_gives_back_the_pose_and_constants_that_made_its_targets.py": 24,
    "score/stages/sim_body/inside/ground/test_a_point_stands_on_the_highest_ground_in_reach.py": 6,
    "score/stages/sim_body/inside/landmarks/test_every_landmark_resolves_on_both_models_where_worked_by_hand.py": 7,
    "score/stages/sim_body/inside/model/test_couplings_keep_a_follower_on_its_leader.py": 4,
    "score/stages/sim_body/inside/muscles/test_a_standing_body_is_carried_by_the_ground.py": 3,
    "score/stages/sim_body/inside/myo/test_the_persons_file_builds_in_newton_as_mujoco_compiles_it.py": 10,
    "score/stages/sim_body/inside/records/test_a_record_keeps_poses_meshes_and_moves_as_worked_by_hand.py": 6,
    "score/stages/sim_body/inside/rra/test_rra_moves_mass_and_torso_by_the_mean_residual.py": 14,
    "score/stages/sim_body/inside/sizing/test_a_sized_group_is_somas_length_and_weight.py": 6,
    "score/stages/sim_body/inside/tuning/_adjoint/test_implicit_columns_equal_re_solved_differences.py": 27,
    "score/stages/sim_body/inside/tuning/_paired/test_a_step_counts_only_past_its_noise_floor_on_a_fixed_case_set.py": 6,
    "score/stages/sim_body/inside/tuning/test_one_optimisation_moves_every_unknown_together_within_its_bounds.py": 17,
    "tools/blender/inside/test_ink_at_edges_and_each_prim_its_own.py": 5,
    "tools/characters/maker/test_made_as_asked_and_bound_to_its_limbs.py": 59,
    "tools/characters/people/test_body_pieces_hold_together.py": 16,
    "tools/props/closeup/test_only_a_clean_closeup_goes_on.py": 25,
    "tools/props/library/test_pieces_keep_true_shape_and_library_paint.py": 40,
}

# The modules (tree_modules) and module groups (module_groups) with no test on 2026-11-25 (#121); each only shrinks. A
# flat tool folder is a group no test can be in yet: a top-level test there belongs to one of its tools.
UNTESTED_DATE = "2026-11-25"
UNTESTED = (
    ".claude/hooks/local",
    ".claude/skills/improve-env/scripts/stills",
    ".claude/skills/my-issues/scripts",
    "docs/adr/tools",
    "score",
    "score/dashboard",
    "score/dashboard/films/preview",
    "score/dashboard/launch",
    "score/dashboard/pages",
    "score/dashboard/pages/migrations",
    "score/dashboard/site",
    "score/stages/demo_film/blender",
    "score/stages/effects/inside",
    "score/stages/library/demo",
    "score/stages/light/inside",
    "score/stages/motion/inside",
    "score/stages/people/inside",
    "score/stages/people_bodies",
    "score/stages/people_cloth/inside",
    "score/stages/place_build/maker/shim/flash_attn",
    "score/stages/place_build/maker/shim/nvdiffrast",
    "score/stages/sim_body/inside",
    "score/stages/surfaces/inside",
    "tools/characters/clips",
    "tools/characters/garments/inside",
    "tools/characters/maker/inside",
    "tools/cloud/closeups_cloud",
    "tools/cloud/delight_worker",
    "tools/cloud/finish_masks",
    "tools/cloud/finish_masks_worker",
    "tools/cloud/geosam2_worker",
    "tools/cloud/google_bill",
    "tools/cloud/images/newton",
    "tools/cloud/images/runner",
    "tools/cloud/input_fetch",
    "tools/cloud/judge_worker",
    "tools/cloud/machine_run",
    "tools/cloud/moss_generate",
    "tools/cloud/picture_worker",
    "tools/cloud/provider",
    "tools/cloud/secret_store",
    "tools/cloud/segment_worker",
    "tools/cloud/segvigen_worker",
    "tools/cloud/self_delete",
    "tools/cloud/similar",
    "tools/cloud/similar_worker",
    "tools/cloud/unirig",
    "tools/cloud/unirig_worker",
    "tools/props/baked_gltf",
    "tools/props/blender_clean_bake",
    "tools/props/finish_elsewhere",
    "tools/props/heavy",
    "tools/props/paths",
    "tools/props/picture",
    "tools/props/review",
    "tools/review/characters",
    "tools/review/layers_lift",
    "tools/review/opening",
    "tools/review/records",
    "tools/review/renders",
    "tools/sound",
)
UNGROUPED = (
    ".claude",
    ".claude/skills",
    "score",
    "score/adapters",
    "score/dashboard",
    "score/stages/place_build/maker/shim",
    "score/stages/sim_body/inside",
    "tools",
    "tools/cloud",
    "tools/props",
    "tools/props/bench",
    "tools/review",
    "tools/sound",
)

# The docstring line that excuses a second test function, with its reason after the colon.
SECOND_TEST = re.compile(r"^\s*second test:\s*\S", re.IGNORECASE | re.MULTILINE)

# The pytest summary of a file that ran nothing but skips ("3 skipped in 0.1s").
ONLY_SKIPS = re.compile(r"^\s*\d+ skipped\b", re.MULTILINE)

# "break" and "red" in one statement, which may wrap over the docstring's lines.
BREAK_LINE = re.compile(r"\bbreaks?\b.{0,200}?\bred\b|\bred\b.{0,200}?\bbreaks?\b", re.IGNORECASE)


def is_test_file(path):
    """Whether a repository path names a test file under the rule (vendor/ is third-party, kept as released)."""
    name = path.name
    return (not path.parts or path.parts[0] != "vendor") and name.endswith(".py") and (
        name.startswith("test_") or name.endswith("_test.py"))


def tree_paths(root):
    """The repository's files, tracked or new and not ignored, that exist on disk, as paths from the root."""
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            check=True, capture_output=True, text=True).stdout
    paths = {pathlib.PurePosixPath(entry) for entry in listed.split("\0") if entry}
    return sorted(path for path in paths if (root / path).is_file())


def test_files(root):
    """The repository's test files (tree_paths), as paths from the root."""
    return [path for path in tree_paths(root) if is_test_file(path)]


def allowlisted(path, allowlist):
    """Whether a test file sits in a module the allowlist still exempts."""
    return any(fnmatch.fnmatch(str(path), pattern) for pattern in allowlist)


@functools.lru_cache(maxsize=None)
def parse(source):
    """A source's tree (None when it does not parse) and the lines of the SyntaxWarnings parsing it raised."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = None
    raised = tuple(warning.lineno for warning in caught if issubclass(warning.category, SyntaxWarning))
    return tree, raised


def parsed(root, path):
    """A test file's tree and SyntaxWarnings (see `parse`)."""
    return parse((root / path).read_text(encoding="utf-8"))


def docstring(root, path):
    """A test file's module docstring ("" when it has none), or None when the file does not parse."""
    tree, _ = parsed(root, path)
    return None if tree is None else ast.get_docstring(tree) or ""


def named_tool(root, path, text):
    """The tool script of a flat folder that a top-level test file's docstring names first, or None."""
    folder = path.parent
    tools = {sibling.stem for sibling in (root / folder).glob("*.py")
             if not is_test_file(pathlib.PurePosixPath(sibling.name)) and sibling.name != "__init__.py"}
    for pattern in (re.escape(str(folder)) + r"/(\w+)\.py\b", r"\b(\w+)\.py\b", r"\b(\w+)\b"):
        for found in re.finditer(pattern, text):
            if found.group(1) in tools:
                return found.group(1)
    return None


def module_of(root, path, text):
    """The module a test file belongs to, as a path from the root, or None for a flat-folder test naming no tool."""
    folder = path.parent
    if folder.name == "tests":
        folder = folder.parent
    if str(path.parent) in FLAT_TOOL_FOLDERS:
        tool = named_tool(root, path, text or "")
        return folder / tool if tool else None
    return folder


def pytest_tests(tree):
    """The names of the test functions pytest finds in a tree (a `Test*` class's methods as `Class.method`)."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            names.update(f"{node.name}.{item.name}" for item in node.body
                         if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"))
    return names


def script_checks(tree):
    """The names of a script-style file's checks: its top-level `CHECKS` entries and `def check_*` functions."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("check_"):
            names.add(node.name)
        elif (isinstance(node, ast.Assign) and isinstance(node.value, (ast.Tuple, ast.List))
              and any(isinstance(target, ast.Name) and target.id == "CHECKS" for target in node.targets)):
            names.update(entry.id if isinstance(entry, ast.Name) else f"CHECKS[{index}]"
                         for index, entry in enumerate(node.value.elts))
    return names


def tree_count(tree):
    """How many test functions a tree defines, pytest's and the script's checks, each name once; 0 for None."""
    return 0 if tree is None else len(pytest_tests(tree) | script_checks(tree))


def test_count(root, path):
    """How many test functions a test file defines (see `tree_count`), 0 when it does not parse."""
    return tree_count(parsed(root, path)[0])


def runs_only_under_main(root, path):
    """Whether a test file has an `if __name__ == ...` block and no test function pytest finds."""
    tree, _ = parsed(root, path)
    if tree is None or pytest_tests(tree):
        return False
    return any(isinstance(node, ast.If) and "__name__" in {name.id for name in ast.walk(node.test)
                                                           if isinstance(name, ast.Name)} for node in tree.body)


def base_count(root, path, base):
    """A test file's test-function count at the git ref `base`, or None when the file (or the ref) is not there."""
    shown = subprocess.run(["git", "-C", str(root), "show", f"{base}:{path}"], capture_output=True, text=True)
    return tree_count(parse(shown.stdout)[0]) if shown.returncode == 0 else None


def count_faults(path, count, text, debt, based):
    """One test file's fault under the one-function rule, against its debt entry if it has one.

    `based` gives the file's count on origin/main, asked only when a `second test:` note must be weighed.
    """
    owed = debt.get(str(path))
    if owed is None:
        if count <= 1:
            return []
        if not SECOND_TEST.search(text or ""):
            return [f"{path}: {count} test functions, one a file (merge them into one test of the answer that matters)"]
        before = based() or 1
        if count > before:
            return [f"{path}: {count} test functions, its `second test:` note covers the {before} it has on origin/main"
                    " (a note never grows a file)"]
        return []
    if count > owed:
        return [f"{path}: {count} test functions, its FUNCTION_DEBT entry allows {owed} (a debt file may not grow)"]
    if count <= 1:
        return [f"{path}: {count} test function now, delete its FUNCTION_DEBT entry"]
    if count < owed:
        return [f"{path}: {count} test functions now, lower its FUNCTION_DEBT entry from {owed} to {count}"]
    return []


def file_faults(path, text, raised=()):
    """One test file's own faults: its name, its docstring's break line and the SyntaxWarnings it raises."""
    faults = [f"{path}: raises a SyntaxWarning on line {line} (python3 -m py_compile shows it)" for line in raised]
    if not path.name.startswith("test_"):
        faults.append(f"{path}: named for its module, not its invariant (rename to test_<invariant>.py)")
    if text is None:
        faults.append(f"{path}: does not parse")
    elif not BREAK_LINE.search(" ".join(text.split())):
        faults.append(f"{path}: its docstring has no line naming the break that turns it red")
    return faults


def asserting_functions(tree):
    """The names of a tree's top-level functions that hold an `assert`: old tests, when a list of them is called."""
    return {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(isinstance(inner, ast.Assert) for inner in ast.walk(node))}


def listed_names(node):
    """Every bare name a literal list, tuple, set or dict (its values) holds, `pytest.param(...)`'s arguments too."""
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return {name for entry in node.elts for name in listed_names(entry)}
    if isinstance(node, ast.Dict):
        return {name for entry in node.values for name in listed_names(entry)}
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "param":
        return {name for entry in node.args for name in listed_names(entry)}
    return set()


def literal_of(node, bound):
    """The literal a loop or a parametrize walks: `node` itself, the top-level literal a name is bound to (`bound`),
    or the literal under an `enumerate(...)`, a `.items()` or a `.values()`; None for anything else."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "enumerate" and node.args:
        node = node.args[0]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("items", "values"):
        node = node.func.value
    if isinstance(node, ast.Name):
        node = bound.get(node.id)
    return node if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)) else None


def loops_of(node):
    """(target, what it walks, its body) of a `for` statement or of each of a comprehension's generators."""
    if isinstance(node, ast.For):
        return [(node.target, node.iter, node.body)]
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        return [(generator.target, generator.iter, [node.elt]) for generator in node.generators]
    if isinstance(node, ast.DictComp):
        return [(generator.target, generator.iter, [node.key, node.value]) for generator in node.generators]
    return []


def walked_tests(node, bound, asserting):
    """The asserting functions a node hands on as tests: in a literal its loop walks, calling what it takes, or in a
    literal a parametrize gives the test; an empty set when none."""
    for target, walked, body in loops_of(node):
        literal = literal_of(walked, bound)
        found = listed_names(literal) & asserting if literal is not None else set()
        taken = {name.id for name in ast.walk(target) if isinstance(name, ast.Name)}
        if len(found) > 1 and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                                  and call.func.id in taken for part in body for call in ast.walk(part)):
            return found
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "parametrize" \
            and len(node.args) > 1:
        literal = literal_of(node.args[1], bound)
        return listed_names(literal) & asserting if literal is not None else set()
    return set()


def stacked(tree):
    """The old tests a file stacks (owner, 2026-11-13: "per test one actual test function, so stacking checks cant
    happen"): two or more of its asserting functions handed on as tests (walked_tests), sorted; empty when none."""
    asserting = asserting_functions(tree)
    bound = {target.id: node.value for node in tree.body if isinstance(node, ast.Assign)
             for target in node.targets if isinstance(target, ast.Name)}
    for node in ast.walk(tree):
        found = walked_tests(node, bound, asserting)
        if len(found) > 1:
            return sorted(found)
    return []


def stacked_faults(root, path):
    """A test file's fault when it stacks old tests (stacked)."""
    tree, _ = parsed(root, path)
    found = stacked(tree) if tree is not None else []
    if not found:
        return []
    shown = ", ".join(found[:3]) + (", ..." if len(found) > 3 else "")
    return [f"{path}: stacks {len(found)} old tests called from a list ({shown}): fold their checks into rows of one"
            " table"]


def code_module(path):
    """The module a file of code (a .py file that is no test file, no conftest.py and outside vendor/) is, as a path
    from the root, a `tests/` folder counting as its parent's and a flat tool folder's script its own module; None for
    any other file (a flat tool folder's __init__.py too)."""
    if path.suffix != ".py" or is_test_file(path) or path.name == "conftest.py" or path.parts[:1] == ("vendor",):
        return None
    if str(path.parent) in FLAT_TOOL_FOLDERS:
        return None if path.name == "__init__.py" else path.parent / path.stem
    return path.parent.parent if path.parent.name == "tests" else path.parent


def tree_modules(root):
    """Every module the tree holds (code_module of each of its files, an empty __init__.py making none), sorted."""
    return sorted({module for path in tree_paths(root) if (module := code_module(path)) is not None
                   and not (path.name == "__init__.py" and not (root / path).read_text(encoding="utf-8").strip())})


def module_groups(modules):
    """The module groups (CONTEXT.md): each folder under which two or more of the modules sit, sorted."""
    under = {}
    for module in modules:
        for parent in module.parents:
            if str(parent) != ".":
                under[parent] = under.get(parent, 0) + 1
    return sorted(group for group, count in under.items() if count > 1)


def exempt(module, allowlist):
    """Whether a module or group sits where the allowlist still exempts the test files."""
    return any(fnmatch.fnmatch(f"{module}/", pattern) or fnmatch.fnmatch(str(module), pattern) for pattern in allowlist)


def owed_faults(kind, present, tested, owed, name, allowlist):
    """The faults of one kind (module or module group) against its debt list `owed` (`name`): one with no test not on
    it, and an entry that has its test now or is no longer one of `present`."""
    found = [f"{entry}: a {kind} with no test (write its test_<invariant>.py there)"
             for entry in sorted(present - tested - owed) if not exempt(entry, allowlist)]
    found += [f"{entry}: on {name} but has its test now, delete its entry" for entry in sorted(owed & tested)]
    found += [f"{entry}: on {name} but no {kind} of the tree, delete its entry" for entry in sorted(owed - present - tested)]
    return found


def tree_faults(root, untested=None, ungrouped=None, allowlist=None):
    """The tree's faults (owner, 2026-11-13, #121): a module with no test, a module group with no test in its own
    folder, and an UNTESTED or UNGROUPED entry with its test now or gone from the tree. `untested`, `ungrouped` and
    `allowlist` are UNTESTED, UNGROUPED and ALLOWLIST when None."""
    root = pathlib.Path(root)
    allowlist = ALLOWLIST if allowlist is None else allowlist
    modules = tree_modules(root)
    tested = {str(module_of(root, path, docstring(root, path))) for path in test_files(root)}
    found = owed_faults("module", {str(module) for module in modules}, tested,
                        set(UNTESTED if untested is None else untested), "UNTESTED", allowlist)
    found += owed_faults("module group", {str(group) for group in module_groups(modules)}, tested,
                         set(UNGROUPED if ungrouped is None else ungrouped), "UNGROUPED", allowlist)
    parse.cache_clear()
    return sorted(found)


def allowlist_faults(root, listed, allowlist):
    """The allowlist's own faults: a pattern covering more test files or functions than its entry, less, or none."""
    found = []
    for pattern, owed in sorted(allowlist.items()):
        covered = [path for path in listed if fnmatch.fnmatch(str(path), pattern)]
        count = (len(covered), sum(test_count(root, path) for path in covered))
        if not covered:
            found.append(f"ALLOWLIST {pattern}: covers no test file, delete its entry")
        elif count[0] > owed[0] or count[1] > owed[1]:
            found.append(f"ALLOWLIST {pattern}: covers {count[0]} test files, {count[1]} test functions, its entry"
                         f" allows {owed[0]}, {owed[1]} (an allowlisted module may not grow)")
        elif count != tuple(owed):
            found.append(f"ALLOWLIST {pattern}: covers {count[0]} test files, {count[1]} test functions now, lower its"
                         f" entry from {tuple(owed)} to {count}")
    return found


def stale_faults(listed, debt, main_only):
    """The FUNCTION_DEBT and MAIN_ONLY entries whose file is not in the tree."""
    present = {str(path) for path in listed}
    return [f"{test}: on {name} but not in the tree, delete its entry"
            for name, entries in (("FUNCTION_DEBT", debt), ("MAIN_ONLY", main_only))
            for test in entries if test not in present]


def main_faults(root, path, main_only):
    """A test file's fault under the pytest-finds-it rule, against its MAIN_ONLY entry if it has one."""
    only = runs_only_under_main(root, path)
    if only and str(path) not in main_only:
        return [f"{path}: its tests run only under __main__, pytest finds none (make them one test_ function)"]
    if not only and str(path) in main_only:
        return [f"{path}: pytest finds its test now, delete its MAIN_ONLY entry"]
    return []


def faults(root, named=(), debt=None, allowlist=None, main_only=None, base="origin/main"):
    """Every fault of the rule in the repository at `root`, or only in the modules of the `named` test files.

    `debt`, `allowlist` and `main_only` are `FUNCTION_DEBT`, `ALLOWLIST` and `MAIN_ONLY` when None, and `base` the
    ref a `second test:` note is weighed against; a test passes its own.
    """
    root = pathlib.Path(root)
    debt = FUNCTION_DEBT if debt is None else debt
    allowlist = ALLOWLIST if allowlist is None else allowlist
    main_only = MAIN_ONLY if main_only is None else main_only
    modules = {}
    found = []
    listed = test_files(root)
    if not named:
        found.extend(stale_faults(listed, debt, main_only))
        found.extend(allowlist_faults(root, listed, allowlist))
    for path in listed:
        if allowlisted(path, allowlist):
            continue
        text = docstring(root, path)
        module = module_of(root, path, text)
        if module is None:
            found.append(f"{path}: its docstring names none of {path.parent}'s tool scripts")
            module = path
        modules.setdefault(module, []).append((path, text))
    wanted = {pathlib.PurePosixPath(name) for name in named}
    for module, files in sorted(modules.items()):
        if wanted and not wanted & {path for path, _ in files}:
            continue
        if len(files) > 1:
            found.append(f"{module}: {len(files)} test files, one a module: {', '.join(str(path) for path, _ in files)}")
        for path, text in files:
            found.extend(file_faults(path, text, parsed(root, path)[1]))
            found.extend(count_faults(path, test_count(root, path), text, debt,
                                      functools.partial(base_count, root, path, base)))
            found.extend(main_faults(root, path, main_only))
            found.extend(stacked_faults(root, path))
    parse.cache_clear()  # the trees held to the interpreter's exit cost it two seconds to free
    return sorted(set(found))


def ran_faults(path, output, may_skip=None):
    """A test file's run's fault: it printed `skipped` (or pytest skipped all of it) and `may_skip` names it not."""
    may_skip = MAY_SKIP if may_skip is None else may_skip
    skipped = any(line.lstrip().lower().startswith("skipped") for line in output.splitlines())
    if not (skipped or ONLY_SKIPS.search(output)) or any(fnmatch.fnmatch(str(path), key) for key in may_skip):
        return []
    return [f"{path}: printed skipped, so it did not run (run it where it can, or name it in MAY_SKIP with the reason)"]


def main(argv):
    """Print the summary line and each fault; exit 1 when there is any."""
    if argv[:1] == ["--ran"]:
        found = ran_faults(argv[1], pathlib.Path(argv[2]).read_text(encoding="utf-8", errors="replace"))
        for fault in found:
            print(f"  {fault}")
        return 1 if found else 0
    found = faults(REPO, argv) + ([] if argv else tree_faults(REPO))
    print(f"test rule: {len(found)} fault(s) (allowlist of {ALLOWLIST_DATE}: {len(ALLOWLIST)} entries)")
    for fault in found:
        print(f"  {fault}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
