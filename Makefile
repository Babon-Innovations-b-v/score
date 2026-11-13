# The project's commands. No CI runs these: the push gate (.claude/hooks/local/pre-push) runs the touched modules' tests
# before every push to main, and the whole suite (`make tests`) is run by hand.

.PHONY: paper check env tests

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
# The time budget (docs/bible.md workflow/module-standard), the one place every gate reads it from: one test file at
# most TEST_SECONDS (owner, 2026-11-07: "we have a one test max of 60 sec").
TEST_SECONDS ?= 60

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

# Rebuild the paper's PDF and LaTeX from paper/score/source/score.md (pandoc + xelatex or tectonic).
paper:
	python3 paper/score/build/build.py

# The gate: what gate-scope says the change needs, then the ADR index check.
check:
	@python3 .claude/scripts/gate-scope.py | tee /tmp/score-gate-scope.txt
	@if grep -q '^MODE full' /tmp/score-gate-scope.txt; then \
		$(SANDBOX) $(PYTEST) paper/score/build .claude/scripts/tests .claude/hooks/tests .claude/index/tests && $(MAKE) --no-print-directory tests; \
	fi
	python3 docs/adr/tools/check_index.py
