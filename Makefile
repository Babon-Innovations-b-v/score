# The project's commands. No CI runs these here: the whole suite runs on every push to main in the cluster's gate, one
# pod per module group (`make test-groups`, `make test-group GROUP=<group>`); read its answer with `make gate-result`.

.PHONY: paper check env tests test-groups test-group gate-result

# The scaffold's tests are pytest tests; pytest runs the paper's unittest check too.
PYTEST ?= uv run -q --with pytest pytest

# The framework's Python environment (pyproject.toml, uv.lock) in .venv: the plain-Python side, no models.
PYTHON := $(CURDIR)/.venv/bin/python
# Every framework check (tools/ and score/), or only the ones named: make tests TESTS="<module>/test_<invariant>.py ...".
# Each is a plain script, or, when it has test_ functions and no __main__ block (it wants pytest's fixtures), a pytest
# file; a heavy one runs under a memory cap so it can never take the machine down. Each runs in a fresh sandbox home
# (.claude/scripts/sandbox-home.py: an empty PROPS_HOME in the temp folder, nothing of the real home linked, the real
# home read-only), so no test touches or leans on the real one; conftest.py refuses a pytest run without one (a test
# unlinked the real cloud ledger, 2026-10-17).
# First the test rule's guard (tools/test_rule/check.py: one test file a module, named test_<invariant>.py, its
# docstring naming its break), always over every module, TESTS given or not (it takes about a second). A file whose
# output says skipped did not run, and fails, unless the guard's MAY_SKIP names it with the reason.
SANDBOX := python3 $(CURDIR)/.claude/scripts/sandbox-home.py --
TESTS ?= $(shell git ls-files 'tools/*_test.py' 'score/*_test.py' 'tools/*/test_*.py' 'score/*/test_*.py')
MEMORY_CAP ?= systemd-run --user --scope -q -p MemoryMax=16G
# The files run side by side, at most JOBS at once (JOBS=1: one after another), each its own sandbox and memory cap;
# a file's line prints as it ends, a failure's tail with it in one write.
JOBS ?= 6
# One test file's time budget (owner, 2026-10-21: a slow test file is a failure, docs/bible.md workflow/module-standard).
TEST_SECONDS ?= 120

# One file (its path the first argument), in the shell xargs starts: its line, and its path added to $$FAILED.
define ONE_TEST
test=$$1; log=$$(mktemp); runner="$(PYTHON)";
if grep -q '^def test_' $$test && ! grep -q '^if __name__' $$test; then runner="$(PYTHON) -m pytest -q -p no:cacheprovider"; fi;
start=$$(date +%s);
if PROPS_PYTHON=$(PYTHON) $(MEMORY_CAP) $(SANDBOX) timeout $(TEST_SECONDS) $$runner $$test > $$log 2>&1 && { ! grep -qi skipped $$log || $(PYTHON) $(CURDIR)/tools/test_rule/check.py --ran $$test $$log > $$log.ran || { cat $$log.ran >> $$log; false; }; }; then echo "ok    $$test ($$(( $$(date +%s) - start )) s)";
else code=$$?; { if [ $$code = 124 ]; then echo "FAIL  $$test (over $(TEST_SECONDS) s: the module standard's time budget)"; else echo "FAIL  $$test ($$(( $$(date +%s) - start )) s)"; fi; tail -n 15 $$log; } > $$log.fail; cat $$log.fail; rm -f $$log.fail; echo $$test >> $$FAILED; fi;
rm -f $$log $$log.ran
endef
export ONE_TEST

env:
	uv sync -q --group dashboard

tests: env
	@FAILED=$$(mktemp); export FAILED; \
	$(PYTHON) $(CURDIR)/tools/test_rule/check.py || echo tools/test_rule/check.py >> $$FAILED; \
	printf '%s\n' $(TESTS) | xargs -P $(JOBS) -n 1 sh -c "$$ONE_TEST" one; \
	failed=$$(paste -sd ' ' $$FAILED); rm -f $$FAILED; \
	if [ -n "$$failed" ]; then echo "failed: $$failed"; exit 1; fi

# The whole suite as module groups, for the cluster's gate (one pod a group, each pod its group's files side by side):
# every test file `tests` runs plus the harness's and the paper's, grouped by their module's first two path parts (a
# `tests/` folder counting as its parent), and `rule`, the test rule's guard over every module. `make test-groups` prints
# `<group> <file>` per file and `rule` alone; `make test-group GROUP=<group>` runs that group exactly as `make tests
# TESTS=<its files>` runs them (the guard over its modules first, each file in its sandbox at TEST_SECONDS).
ALL_TESTS = $(TESTS) $(shell git ls-files '.claude/*/tests/test_*.py' 'paper/*/test_*.py')
GROUP_OF = awk -F/ '{n = NF - 1; if ($$n == "tests") n--; if (n > 2) n = 2; group = $$1; for (i = 2; i <= n; i++) group = group "/" $$i; print group, $$0}'
test-groups:
	@echo rule; printf '%s\n' $(ALL_TESTS) | $(GROUP_OF)

test-group:
	@if [ "$(GROUP)" = rule ]; then $(MAKE) --no-print-directory env && $(PYTHON) $(CURDIR)/tools/test_rule/check.py; exit $$?; fi; \
	files=$$(printf '%s\n' $(ALL_TESTS) | $(GROUP_OF) | awk -v group="$(GROUP)" '$$1 == group {print $$2}' | paste -sd ' '); \
	if [ -z "$$files" ]; then echo "no test group '$(GROUP)' (make test-groups lists them)"; exit 2; fi; \
	$(MAKE) --no-print-directory tests TESTS="$$files"

# The cluster gate's answer for one commit (SHA, default the newest on main): its commit status `cluster/gate` and, when
# it failed, the failing files' tails it posted on the commit. Needs gh logged in.
SHA ?= main
REPO_SLUG = $(shell python3 -c "import json; print(json.load(open('.claude/project.json'))['repo'])")
gate-result:
	@sha=$$(gh api repos/$(REPO_SLUG)/commits/$(SHA) --jq .sha) && \
	gh api repos/$(REPO_SLUG)/commits/$$sha/statuses --jq '[.[] | select(.context == "cluster/gate")][0] // {state: "none", description: "no gate answer yet"} | "\(.state)  \(.description)"' | sed "s/^/$${sha%????????????????????????????}  /" && \
	gh api repos/$(REPO_SLUG)/commits/$$sha/comments --jq '[.[] | select(.body | startswith("cluster/gate"))][-1].body // empty'

# Rebuild the paper's PDF and LaTeX from paper/source/score.md (pandoc + xelatex or tectonic).
paper:
	python3 paper/build/build.py

# The gate: what gate-scope says the change needs, then the ADR index check.
check:
	@python3 .claude/scripts/gate-scope.py | tee /tmp/score-gate-scope.txt
	@if grep -q '^MODE full' /tmp/score-gate-scope.txt; then \
		$(SANDBOX) $(PYTEST) paper/build .claude/scripts/tests .claude/hooks/tests .claude/index/tests && $(MAKE) --no-print-directory tests; \
	fi
	python3 docs/adr/tools/check_index.py
