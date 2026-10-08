---
name: audit-dead-code
description: Hybrid mechanical+LLM dead-code audit. Runs vulture (Python), ts-prune (TS), shellcheck SC2034 (bash unused vars), then resolves false positives with an LLM pass over import sites. Use when user says "audit dead code" / "find unused code" / runs the skill mid-refactor; or after a deletion sweep to verify nothing leaked back. Read-only — emits a report, never deletes.
---

# Audit dead code

Three mechanical detectors + one LLM resolver. Outputs a markdown report at `tmp/audit-dead-code-<sha>.md` with three sections: `## Dead`, `## Live`, `## Uncertain`.

The skill is read-only. Deletions are a separate slice (the user reviews the `Dead` section + grep-confirms callers + commits).

## Quick start

```bash
bash .claude/skills/audit-dead-code/scripts/run.sh
```

Output path is printed at the end. Re-runs on the same tree produce the same output (modulo `tmp/` filename SHA).

## Process

### 1. Mechanical pass

Three tools run in parallel; outputs land in `tmp/_audit-mechanical/`:

| Tool | Scope | Catches |
|---|---|---|
| `vulture` | every tracked `*.py` | unused functions, classes, vars, imports, attributes |
| `ts-prune` | every directory with its own `package.json` | unused TypeScript exports |
| `shellcheck -i SC2034` | every tracked `*.sh` | unused bash variables |

**Excluded by default**: vendored third-party code, `tests/`, generated code (migrations), `.venv/`, `node_modules/`, and build output.

**If the project is none of these languages** (a Java or Go repo, say), the mechanical pass has nothing to run. Say so plainly and stop; do not substitute a hand-rolled scan and present it as the same thing.

Vulture confidence threshold: `--min-confidence 80` (default). Below that → too noisy.

### 2. LLM resolve pass

For every flagged symbol, gather:

- The symbol's source file + line range.
- `grep -rn` results across the repo (callers, string references, dynamic dispatch hints).
- Decorator context (`@register_*`, `@app.route`, `@pytest.fixture`).
- Per-framework allow-list signals (a framework's registry strings, a plugin manifest, a settings list that names classes by string).

Prompt (per symbol): "is this dead, live, or uncertain?" with the gathered context. Verdict + one-line reasoning per item.

LLM keeps three buckets:
- **Dead** — confirmed no callers, no string refs, no framework dispatch. Safe to delete.
- **Live** — caller found (the mechanical tool was wrong). Don't delete.
- **Uncertain** — ambiguous (dynamic dispatch, runtime registration, MCP). Human eyeball needed.

### 3. Report

Output at `tmp/audit-dead-code-<HEAD-sha>.md`:

```markdown
# Dead-code audit — <SHA> — <date>

## Dead (N items, safe to delete)
- `src/api/foo.py:42` — `def _unused_helper()` — no callers, no string refs.

## Live (N false positives — leave alone)
- `src/panels/main.py:88` — `register_renderer` — flagged by vulture; called through a registry by name.

## Uncertain (N items — human review)
- `src/registry.py:201` — `LegacyExtractor` — referenced in a `getattr` lookup; cannot prove dead or alive.
```

Re-runs are stable: same tree → same output.

## Common false-positive patterns (LLM allow-list)

The resolver should NOT mark these as dead:
- Framework lifecycle hooks invoked by the framework, not by an import.
- Anything registered by string name in a registry or plugin manifest.
- Pytest `conftest.py` fixtures — referenced by name in test signatures.
- Symbols re-exported in `__init__.py` and referenced as strings elsewhere.
- Route handlers declared by decorator.
- Migrations — applied by name, never imported.

## Failure modes

- **Tool missing**: `vulture` / `ts-prune` not installed → script prints install hint, exits non-zero.
- **No flagged items**: emits report with empty sections + a `Nothing flagged — clean tree.` note.
- **Nothing in scope**: the repo has no Python, TypeScript or bash. Report that, and do not improvise a replacement pass.

## Out of scope

- Deletion. The skill never modifies code — only reports.
- Test coverage gaps. A different question, and a different tool.
