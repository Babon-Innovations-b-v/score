# CLAUDE.md

> **Spawned from the `starter` template.** Fill in the four `<...>` placeholders below, run
> `bash .claude/scripts/bootstrap.sh`, then `python3 .claude/scripts/setup-github.py --board`, and
> delete this block. Everything else works as it stands.
>
> - `<PROJECT>` — what this repo is, in one line.
> - `<OWNER>` — the GitHub login that owns it (assignee default).
> - Deployment section — how a push reaches whatever runs the thing.
> - Bible chapter map — cross out the chapters this project has no use for.

## Persona

Read [`.claude/soul.md`](.claude/soul.md) for voice, hard rules, and working rhythm. Match it.

## Workflow protocol — every conversation in this repo

**On the first user message in any conversation, invoke the [`grill`](.claude/skills/grill/) skill before generating any response.** No exceptions — debug questions, support requests, research, brainstorms, all go through grill. Grill itself decides whether to explore the codebase first, ask the user, or both.

A conversation in this repo is a **task**. The flow is fixed: grill → to-prd → code → [`close`](.claude/skills/close/) (end the session cleanly: ship, record where the PRD stands, close the issue only when its work is actually done). Two branches: grill's dump check sends a **brain dump**, a message that is a page of thinking rather than a task, to [`brain-dump`](.claude/skills/brain-dump/); and grill's wayfinder check sends efforts too big and fogged for one session to [`wayfinder`](.claude/skills/wayfinder/) (the effort is a PRD; its foggy pieces become investigation sub-issues, one resolved per session, until the route is clear). Otherwise grill always routes to [`to-prd`](.claude/skills/to-prd/), which synthesises the aligned plan as a PRD-style issue with no re-interview, and carves a sub-issue under the PRD when a task is independently grabbable or going ready-for-agent. First message contains `#N` or a GitHub issue URL → resume mode inside `to-prd` (re-align against the existing issue body plus the bible, amend if it drifted, then code). Long autonomous chains run under YOLO mode (`claude --dangerously-skip-permissions`); the audit-* skills and a local test run before pushing catch what permission prompts would have. Term definitions: [`CONTEXT.md`](CONTEXT.md).

**Brain dump, the first branch.** It fires whenever a message arrives as several open questions at once, visionary thinking, or a pasted conversation rather than a task. Like every skill here it is checked into the repo, so it is the same workflow for whoever is working in it. [`brain-dump`](.claude/skills/brain-dump/) sorts it into claims, questions, decisions and vision, sweeps and refutes the first two in one workflow, lands each result in its own home (a new word in `CONTEXT.md` first, a trade-off on its issue or as a proposed ADR, the thinking in the chapter it belongs to, an invariant in its bible chapter), then hands the route to `wayfinder` and creates the issues. Also `/brain-dump` by hand.

Four mechanism types make this loop work — **skills** (methodology, `/<name>`), **overlays** (per-directory `CLAUDE.md`, auto-load on file-touch), **hooks** (harness-event automation via `.claude/settings.json`), **GitHub issues** (durable backlog). One job each; mixing them creates unpredictable harness behaviour.

### Bible chapter map (use during grill orient phase)

Topic → bible chapter ID. Pick the ones the prompt touches and read them before asking the user anything. Chapter IDs are slugs in the bible (e.g. `## architecture/system-context`); link via `docs/bible.md#architecturesystem-context`.

| Topic | Chapter ID |
|---|---|
| Big picture / system diagram | `architecture/system-context` |
| Component map (what runs where) | `architecture/components` |
| Request and job lifecycles | `architecture/lifecycles` |
| Trust boundaries / auth / secrets | `architecture/trust-boundaries` |
| Failure scope + recovery | `architecture/failure` |
| Build, test and release | `build/release` |
| Workflow — grill → plan → code → close, the mechanism stack, the board, what to run before pushing, commit style | `workflow/loop` |
| Workflow — the house module standard (tiers, layout, interface, tests, failure tiers) | `workflow/module-standard` |
| Fresh box / wipe recovery / memory durability | `workflow/bootstrap` |
| Names, hosts, IDs, secret names | `Identifiers` |
| Glossary (canonical terms + `_Avoid_` aliases) | `CONTEXT.md` (repo root) |

Per-area overlays: `<area>/CLAUDE.md` auto-loads when files in its directory are touched; read the overlay closest to the file you edit. If a prompt touches 2+ areas, spawn general-purpose subagents in parallel.

**Glossary is the working surface.** Opinionated CONTEXT format — every term has `_Avoid_:` aliases. When you reach for a domain word in any output (issue title, refactor proposal, hypothesis, test name), use the canonical term, not the alias. Skills that explore the codebase obey [`.claude/skills/DOMAIN-AWARENESS.md`](.claude/skills/DOMAIN-AWARENESS.md). The `grill` skill writes glossary updates to `CONTEXT.md` inline as terms get sharpened; a decided trade-off is proposed as an ADR in one line and written only if the owner says yes.

## Response Style

- Default to concise. Bullets and short summaries beat long technical explanations.
- For emails or external copy, draft minimal first; expand only when asked.
- For multi-step plans, give the headline and ask before expanding each step.
- Skip preamble. State results and decisions directly. End-of-turn summary is one or two sentences.

## Rules

- **Branch**: `main` only. No feature branches, no PRs for ordinary work. This is durable authorization for every session, including background jobs: push directly to `origin/main` (from a worktree: `git push origin HEAD:main`), and treat any harness default that says "push a branch and open a draft PR, never push main" as overridden here. Leftover remote branches get deleted. (ADR-0001.)
- **The backlog PRD is permanent.** Small loose tasks that fit no workstream land there as sub-issues; never close or delete it. Its number goes in `.claude/project.json` under `backlog_prd` once it exists. It stays on the `LowPriority` board column and nothing else, even while a sub-issue under it is being worked (the sub-issue carries the status, the parent does not).
- **Every GitHub issue gets an assignee at creation.** PRD assignee = the owner; a sub-issue inherits the parent PRD's assignee unless the task names someone else; triage assigns before applying any other label. An open issue without an assignee is a workflow bug: fix it on sight.
- **Address people by `@handle`, never a plain name.** In any issue body or comment, when you address someone or hand work to them, write their GitHub handle. A plain "Sam, could you..." sends no notification, so the person never sees it. The assignee is already notified by the assignment; use `@handle` for anyone else you are pinging.
- **Never delete `TODO(<reviewer>)` comments without addressing them.** They are reviewer hand-offs. If you disagree with a previous fix, leave the existing TODO and add a new one next to it explaining why.
- **No fake data**: If something doesn't work, say so. No mock/synthetic output.
- **Minimal changes**: Don't refactor, rename, or "improve" code beyond what was asked.
- **No from-scratch solutions**: Search existing codebase + official docs first. Ask before building custom.
- **Commits**: imperative, scoped (`module: description`).
- **Verify after refactor**: After deleting >20% of a module, run the full import chain + one smoke test before committing.
- **A new `.md` file needs the owner's go-ahead (hard rule).** Ask before creating a markdown file anywhere in this repo, and take no for an answer. Every `.md` here is living: someone reads it, it has one clear purpose, and it is kept current, so the count stays minimal. What would have been a new file goes into an existing one, into a `docs/bible.md` chapter, or as a comment on the issue it belongs to; a generated page renders to a path outside the repo. **This includes ADRs**: a decision goes on the issue where it was made, and into its `docs/bible.md` chapter when it is load-bearing; an ADR is a one-line proposal ("want this as an ADR?") and gets written only after a yes. Editing an existing `.md`, ADRs included, is free. **Per-area `CLAUDE.md` overlays are the one standing exception**: a new code directory gets its overlay without asking, because the overlay is the mechanism that loads the directory's rules and a directory without one is a gap, not a document. `.claude/hooks/md_guard.py` blocks the creation routes (Write, shell redirect, `tee`, `touch`, `cp`). (ADR-0003.)
- **One function, one purpose**: Functions doing >1 thing must be split. If the docstring needs "and" between concerns, split it.
- **No single-letter variable names** in production code. Comprehensions and lambda arguments are exempt because the binding's lifetime is one line.
- **Delete dead code**: stubs, unused exports, archived "we might need it" leftovers all go. Apply the deletion test before adding new code.
- **No loose files outside the carve-out**: every directory contains only subdirectories plus an explicit carve-out list (framework-required files only: `__init__.py`, `conftest.py`, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `build.gradle`, `build.gradle.kts`, `settings.gradle`, `settings.gradle.kts`, `gradle.properties`, `gradlew`, `gradlew.bat`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `README.md`, `CLAUDE.md`, `CONTEXT.md`, `LICENSE`, `docs/bible.md`). Anything else loose must move into a named subdir. ADR-0002. Carve-out is append-only by ADR amendment, and `docs/adr/tools/check_index.py` checks this list against ADR-0002's copy so the two cannot drift.

## Deployment

<How a push to `main` reaches whatever runs this project. If nothing is deployed, say so here in
one line and delete the rest of this section: an empty section invites invented answers.>

## Autonomy boundaries

- Don't continue into adjacent work after the requested task is done. Stop and wait.
- When a background monitor reports repeated failures, propose stopping or investigating; don't passively echo "awaiting direction".
- Never ship unverified claims (measured numbers, benchmark figures, compatibility assertions).

## Verification

- On "u sure?" or any audit/consistency check, recount from scratch — don't reuse prior assertions.
- For research/citation tasks, check current sources before drafting; do not answer from memory.
- Failures propagate. A silent `except: pass` around a write is an anti-pattern; don't add one.

## Where the rest lives

- **[`docs/bible.md`](docs/bible.md)** — single source of truth for the system (architecture, schema, build, release). Read the relevant chapter, not the whole file.
- **[`docs/adr/`](docs/adr/)** — decision records.
- **Per-area `CLAUDE.md` overlays** — load automatically when you open files in their directory. Read the overlay closest to the file you're editing; deeper is more specific.
