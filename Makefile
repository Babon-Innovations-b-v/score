# The project's commands. No CI runs these: they run locally, before a push.

.PHONY: paper check

# The scaffold's tests are pytest tests; pytest runs the paper's unittest check too.
PYTEST ?= uv run -q --with pytest pytest

# Rebuild the paper's PDF and LaTeX from paper/source/score.md (pandoc + xelatex or tectonic).
paper:
	python3 paper/build/build.py

# The gate: what gate-scope says the change needs, then the ADR index check.
check:
	@python3 .claude/scripts/gate-scope.py | tee /tmp/score-gate-scope.txt
	@if grep -q '^MODE full' /tmp/score-gate-scope.txt; then \
		$(PYTEST) paper/build .claude/scripts/tests .claude/hooks/tests; \
	fi
	python3 docs/adr/tools/check_index.py
