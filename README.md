# starter

The scaffolding every new project of mine begins with: the working loop, the skills that drive it,
the docs that hold the truth, and the GitHub setup the loop reads from. No application code, no
language toolchain, no opinion about what the project actually is.

Use it with **Use this template** on GitHub, or `gh repo create <name> --template JoeyKardolus/starter --private --clone`.

## First run, in order

```bash
bash .claude/scripts/bootstrap.sh          # links Claude's memory folder into the repo, checks gh
python3 .claude/scripts/setup-github.py --board   # labels, and a project board with the loop's columns
$EDITOR CLAUDE.md                          # fill the four placeholders, delete the banner
```

`setup-github.py` writes the ids it discovers into `.claude/project.json`, which is the one file
the scripts and hooks read for repo, board and people. Nothing else is hard-coded.

Then open Claude Code in the repo and describe the first piece of work. The `SessionStart` hook
routes it into `grill`, and the loop takes over.

## What is in here

**The loop.** `grill` (interview the plan against the domain model) → `to-prd` (publish it as a
PRD epic on GitHub) → code → `close` (ship, record, close only when actually done). Two branches
off `grill`: `brain-dump` for a message that is a page of thinking rather than a task, and
`wayfinder` for an effort too big and too fogged for one session.

**The rest of the skills.** `triage` and `ralph` (the ready-for-agent queue), `diagnose`, `tdd`,
`prototype`, `tour`, `improve-codebase-architecture`, `audit-dead-code`,
`audit-function-purposes`, `my-issues`, `handoff`, `zoom-out`, `caveman`, `write-a-skill`.

**The docs.** `docs/bible.md` is the single source of truth, one file with chapter slugs the
chapter map in `CLAUDE.md` points at. `docs/adr/` holds decision records, with
`tools/check_index.py` failing when the index stops telling the truth about the files. `CONTEXT.md`
is the glossary, and it is deliberately almost empty: the first `grill` session fills it.

**The hooks.** `md_guard.py` blocks a new markdown file (they multiply, and every one here is
meant to be living). `issue_guard.py` blocks a bare issue creation without an assignee and a
category, and blocks destructive git. The `Stop` hook commits and pushes Claude's memory folder so
memory survives a wiped machine.

**The rules.** `CLAUDE.md` carries them: `main` only, minimal changes, no fake data, one function
one purpose, no loose files outside the carve-out. Four seed ADRs record the ones that are hard to
reverse.

## What is deliberately not in here

- **The diagram set** (`case-study`, the drawing pipeline, the `◈` bible markers). It needs a
  vendored renderer, a served host and a 60 MB page set. Worth porting per-project if the project
  earns it, not worth carrying by default.
- **Anything measured, deployed or paid for**: no CI, no infrastructure, no secrets, no cost map.
- **A language toolchain.** The audit skills assume Python, TypeScript or bash tooling and will
  say so plainly when the project is neither; that is the honest failure, not a stub.
