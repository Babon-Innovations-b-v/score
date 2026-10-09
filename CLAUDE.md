# CLAUDE.md

SCORE: a world generation framework that turns a creator's picks into a complete, owned, editable world (coding agents and open models in cloud batches, checks before every paid step), and its paper. Public repository, MIT. Owner: `@JoeyKardolus`.

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
| ~~Trust boundaries / auth / secrets~~ (offline batches, secrets only by name: not used yet) | `architecture/trust-boundaries` |
| Failure scope + recovery | `architecture/failure` |
| Build, test and release | `build/release` |
| Workflow — grill → plan → code → close, the mechanism stack, the board, what to run before pushing, commit style | `workflow/loop` |
| Workflow — the house module standard (tiers, layout, interface, tests, failure tiers) | `workflow/module-standard` |
| Fresh box / wipe recovery / memory durability | `workflow/bootstrap` |
| Names, hosts, IDs, secret names | `Identifiers` |
| Glossary (canonical terms + `_Avoid_` aliases) | `CONTEXT.md` (repo root) |

Per-area overlays: `<area>/CLAUDE.md` auto-loads when files in its directory are touched; read the overlay closest to the file you edit. If a prompt touches 2+ areas, spawn general-purpose subagents in parallel.

**Glossary is the working surface.** Opinionated CONTEXT format — every term has `_Avoid_:` aliases. When you reach for a domain word in any output (issue title, refactor proposal, hypothesis, test name), use the canonical term, not the alias. Skills that explore the codebase obey [`.claude/skills/DOMAIN-AWARENESS.md`](.claude/skills/DOMAIN-AWARENESS.md). The `grill` skill writes glossary updates to `CONTEXT.md` inline as terms get sharpened; a decided trade-off is proposed as an ADR in one line and written only if the owner says yes.

## Agent tools

Three tools are wired in for every session and agent here, each pinned (`.claude/settings.json`, `.mcp.json`):

- **codebase-memory-mcp** (code graph, v0.11.0, MCP server plus hooks). Look code up with `search_graph` and `trace_path` (callers, callees) before Grep or whole-file reads, and run `check_index_coverage` on any file you rely on: the graph can lag behind uncommitted edits, so read what it reports as missed. `.cbmignore` keeps `vendor/`, `data/` and the paper's outputs out of it. Its agent types (`.claude/agents/`: `codebase-memory-scout` for a quick lookup, `codebase-memory` to verify, `codebase-memory-auditor` for a bounded audit; read-only) and its skill (`/codebase-memory`) come from its 0.11.0 installer as released; send code-finding work to them rather than to a general agent.
- **claude-mem** (cross-session memory, v13.35.0, `vendor/claude-mem`). Search it (`mem-search`) for past decisions and fixes, sub-agents' included. It is a log, not a rulebook: a lesson worth keeping still goes into its `CLAUDE.md` overlay or the bible, which load every time and are reviewed. Its observer runs on Haiku under the owner's subscription, one call stream per agent. It is installed but switched off (`enabledPlugins` in `.claude/settings.json`): in the 2026-10-09 with-and-without run the lesson reached every probe and all three still repeated the mistake, and the observer saved one probe's rejected method as a "decision". Switch it on only with a new with-and-without run. Test and benchmark sessions never write to the shared memory: start them with their own memory and worker, `CLAUDE_MEM_DATA_DIR=~/.claude-mem-test CLAUDE_MEM_WORKER_PORT=37810 claude --settings '{"enabledPlugins":{"claude-mem@thedotmack":true}}' ...` (set it up once with `CLAUDE_MEM_DATA_DIR=~/.claude-mem-test bash .claude/scripts/install-agent-tools.sh`; checked 2026-10-09: the shared database stayed untouched).
- **ponytail** (lean-code rules, v5.1.0, `vendor/ponytail`), injected at session start and into coding sub-agents. Where it differs from the house rules, the house rules win: one function, one purpose still means split; no `shortcut:` comments.

**Output: summaries, not dumps.** Every output an agent reads stays in its context and is paid for again on every later turn, so long output goes to a file and the agent reads only the part it needs. A tool here prints one summary line (counts, pass or fail, the paths it wrote) and writes the detail to a file; `--verbose` gives the full output where a tool has it. The `output_cap.py` hook (PostToolUse on Bash) does the same for any command: an output over 6,000 characters is saved whole to `/tmp/score-output/<session>/<call>.txt`, and the agent sees its first and last lines, its error and warning lines (or, for JSON, its keys and array lengths) and that file's path. Nothing is lost: read the file with Read (offset, limit), `grep` or `sed -n`. Reads you narrow yourself (`sed -n`, `head`, `tail`, `grep -c`, `wc`) and a `cat` of a rules file you must read whole (a `CLAUDE.md` overlay, `SKILL.md`, `soul.md`, `CONTEXT.md`) are left alone, and a command prefixed with `SCORE_FULL_OUTPUT=1` keeps its whole output. Read a large file in ranges rather than with `cat`. A failing command's output cannot be replaced by a hook; Claude Code shows about 10,000 characters of it, so send a long failing run to a file yourself (`cmd > /tmp/x.log 2>&1; tail -n 40 /tmp/x.log`).

**Never wait in the foreground** (owner, 2026-10-09). An agent's turn that comes more than 5 minutes after its previous one re-writes its whole context to the prompt cache; on 2026-10-09 that was about half of all agent spend, mostly after sleep and poll loops, cloud runs, Blender and game runs and test gates that blocked in the foreground. So start anything that takes minutes with the Bash tool's `run_in_background` and go on with other work, or end your turn and let the completion notice wake you. The cloud Blender tools take `--detach` (`blender_cloud.py`, `tools/usd/settle.py`, `tools/review/page.py`), and `tools/props/cloud/detached.py -- <command>` does the same for any command, a test gate included: progress goes to a log and one result line (status, log, outputs) comes at the end, so there is nothing to poll and no log to read whole. To wait for a condition, use the Monitor tool. `.claude/hooks/wait_guard.py` blocks foreground sleeps over a minute, poll loops and foreground cloud Blender runs. Every session here keeps its prompt cache for an hour (`promptCacheTtl` and `subagentPromptCacheTtl` in `.claude/settings.json`), sub-agents included, so a wait that cannot be avoided does not cost a re-write. Effort and quality are never cut to save tokens; only waste is.

Fresh box: `bash .claude/scripts/bootstrap.sh` runs `.claude/scripts/install-agent-tools.sh`, which downloads and checks the pinned binaries, writes claude-mem's settings, installs the plugin for this project and indexes the repo. State outside the repo: `~/.claude-mem` (memory database and settings), `~/.cache/codebase-memory-mcp` (graph index), `~/.local/bin/codebase-memory-mcp`, `~/.bun`, and Claude Code's plugin cache.

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
- **A new `.md` file needs the owner's go-ahead (hard rule).** Ask before creating a markdown file anywhere in this repo, and take no for an answer. Every `.md` here is living: someone reads it, it has one clear purpose, and it is kept current, so the count stays minimal. What would have been a new file goes into an existing one, into a `docs/bible.md` chapter, or as a comment on the issue it belongs to; a generated page renders to a path outside the repo. **This includes ADRs**: a decision goes on the issue where it was made, and into its `docs/bible.md` chapter when it is load-bearing; an ADR is a one-line proposal ("want this as an ADR?") and gets written only after a yes. Editing an existing `.md`, ADRs included, is free. **Per-area `CLAUDE.md` overlays are the one standing exception**: a new code directory gets its overlay without asking, because the overlay is the mechanism that loads the directory's rules and a directory without one is a gap, not a document. `.claude/hooks/md_guard.py` blocks the creation routes (Write, shell redirect, `tee`, `touch`, `cp`). `vendor/` is exempt: third-party code comes with its own docs, kept as released. (ADR-0003.)
- **One function, one purpose**: Functions doing >1 thing must be split. If the docstring needs "and" between concerns, split it.
- **No single-letter variable names** in production code. Comprehensions and lambda arguments are exempt because the binding's lifetime is one line.
- **Delete dead code**: stubs, unused exports, archived "we might need it" leftovers all go. Apply the deletion test before adding new code.
- **No loose files outside the carve-out**: every directory contains only subdirectories plus an explicit carve-out list (framework-required files only: `__init__.py`, `conftest.py`, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `build.gradle`, `build.gradle.kts`, `settings.gradle`, `settings.gradle.kts`, `gradle.properties`, `gradlew`, `gradlew.bat`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `README.md`, `CLAUDE.md`, `CONTEXT.md`, `LICENSE`, `docs/bible.md`). Anything else loose must move into a named subdir. `vendor/` (vendored third-party tools, kept as released) is exempt wholesale. ADR-0002. Carve-out is append-only by ADR amendment, and `docs/adr/tools/check_index.py` checks this list against ADR-0002's copy so the two cannot drift.

## Deployment

Nothing is deployed. A push to `main` publishes the source, the paper's PDF and its arXiv tree; nothing runs from it. No GitHub Actions.

**Public from the first commit.** Nothing from babon or Movalytics (business files, data, people, clients), no secrets, keys or cloud account and project ids, ever: not in code, docs, the paper or its comments.

**Claude's memory stays private.** `.claude/memory/` is git-ignored: this repository is public and memory is private working notes, so it is never committed or pushed. Anything a later session must know goes into the bible, `CONTEXT.md` or an issue.

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
