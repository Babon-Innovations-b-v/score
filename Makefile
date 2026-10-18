# The project's commands. No CI runs these: they run locally, before a push.

.PHONY: paper check env tests

# The scaffold's tests are pytest tests; pytest runs the paper's unittest check too.
PYTEST ?= uv run -q --with pytest pytest

# The framework's Python environment (pyproject.toml, uv.lock) in .venv: the plain-Python side, no models.
PYTHON := $(CURDIR)/.venv/bin/python
# Every framework check (tools/ and score/), or only the ones named: make tests TESTS="tools/props/library/paint_test.py ...".
# Each is a plain script, or, when it has test_ functions and no __main__ block (it wants pytest's fixtures), a pytest
# file; a heavy one runs under a memory cap so it can never take the machine down. Each runs in a fresh sandbox home
# (.claude/scripts/sandbox-home.py: PROPS_HOME in the temp folder, the real home read-only), so no test touches the
# real one; conftest.py refuses a pytest run without one (a test unlinked the real cloud ledger, 2026-10-17).
SANDBOX := python3 $(CURDIR)/.claude/scripts/sandbox-home.py --
TESTS ?= $(shell git ls-files 'tools/*_test.py' 'score/*_test.py')
MEMORY_CAP ?= systemd-run --user --scope -q -p MemoryMax=16G

env:
	uv sync -q --group dashboard

tests: env
	@failed=""; log=$$(mktemp); for test in $(TESTS); do \
		runner="$(PYTHON)"; \
		if grep -q '^def test_' $$test && ! grep -q '^if __name__' $$test; then \
			runner="$(PYTHON) -m pytest -q -p no:cacheprovider"; fi; \
		if PROPS_PYTHON=$(PYTHON) $(MEMORY_CAP) $(SANDBOX) $$runner $$test > $$log 2>&1; then \
			echo "ok    $$test"; \
		else \
			echo "FAIL  $$test"; tail -n 15 $$log; failed="$$failed $$test"; \
		fi; \
	done; rm -f $$log; \
	if [ -n "$$failed" ]; then echo "failed:$$failed"; exit 1; fi

# Rebuild the paper's PDF and LaTeX from paper/source/score.md (pandoc + xelatex or tectonic).
paper:
	python3 paper/build/build.py

# The gate: what gate-scope says the change needs, then the ADR index check.
check:
	@python3 .claude/scripts/gate-scope.py | tee /tmp/score-gate-scope.txt
	@if grep -q '^MODE full' /tmp/score-gate-scope.txt; then \
		$(SANDBOX) $(PYTEST) paper/build .claude/scripts/tests .claude/hooks/tests && $(MAKE) --no-print-directory tests; \
	fi
	python3 docs/adr/tools/check_index.py
