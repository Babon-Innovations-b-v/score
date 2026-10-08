# The bible

The single source of truth for how this system works. One file, chaptered. A chapter ID is the
slug after the `##` (for example `architecture/system-context`), and the chapter map in root
[`CLAUDE.md`](../CLAUDE.md) points at it; link to a chapter as `docs/bible.md#architecturesystem-context`.

**How to use it.** Read the chapter the work touches, never the whole file. When you learn
something load-bearing that a future reader would otherwise have to re-derive from code, write it
into its chapter in the same session. When a chapter contradicts the code, the code wins and the
chapter gets fixed on the spot.

**What does not go here.** Vocabulary goes in [`CONTEXT.md`](../CONTEXT.md). Decisions that were
hard to reverse go in [`docs/adr/`](adr/). Status of ongoing work goes on its GitHub issue. The
bible holds how the thing works, not what we are doing about it.

A chapter that is still a placeholder says so in one line. An empty chapter is honest; an invented
one is not.

---

## architecture/system-context

<The big picture in one screen: what this system is, who or what talks to it, what it talks to.
Placeholder until the first real component exists.>

## architecture/components

<What runs where: each running piece, what it is responsible for, and where its code lives.
Placeholder.>

## architecture/lifecycles

<What happens end to end for the two or three paths that matter: a request, a job, a build.
Placeholder.>

## architecture/trust-boundaries

<Where untrusted input crosses into trusted code, how it is authenticated, where secrets live and
who can read them. Placeholder.>

## architecture/failure

<What breaks when each piece breaks, what the blast radius is, and how to recover. Placeholder.>

## build/release

<How the project is built, tested and released. The exact commands, and what a green run means.
Placeholder.>

**Scope the gate.** Running every test on every push stops scaling once several sessions work
side by side on one machine. The project's test command asks
`python3 .claude/scripts/gate-scope.py` first and reads its `MODE` line: `none` when the change
touches only documents and working notes (`.md`, `docs/`, `.claude/`), so nothing runs; `full`
otherwise. When the full run grows slow, grow the script into a graph that picks only the suites
a change can reach, and keep its rules:

- **Unknown means full.** A path the scope does not recognise, a file that went away and could
  have been named by something, no origin/main to compare with, `--full`, `GATE_FULL=1`, or a run
  on CI: everything runs. A new kind of path goes to full, never to "none".
- **A change to the gate itself runs everything**: the test runner, its config, vendored test
  frameworks, the CI workflow.
- **CI always runs everything.** It is the net under a test the scope misses, so it stays
  unscoped.
- **The scope has its own check against the real tree**: every suite is chosen when the file it
  is named after changes, and an exception is written down with the reason.
- **Print the reasons**, one line each, so whoever reads the gate's output sees what was skipped.

Two grown versions to copy from: the babon repo's `engine/infra/ops/gate_scope/` (Python import
graph) and farm-factory's `tools/test/scope/` (Godot scripts, scenes and `res://` paths).

## workflow/loop

The working loop, and the mechanisms that keep it from drifting.

**The loop.** Every conversation in this repo is a task, and it runs the same four steps.

1. **grill** — the first message in any conversation goes here, enforced by the `SessionStart`
   hook. Grill orients silently (the prompt, `.claude/soul.md`, root `CLAUDE.md`, the `CONTEXT.md`
   glossary, the bible chapters the prompt touches, the related GitHub issues), then interviews the
   plan one question at a time until the plan and the domain model agree. Facts get looked up, not
   asked. Decisions get asked, not assumed.
2. **to-prd** — the aligned plan becomes one PRD epic: a GitHub issue with a goal, a scope, a task
   list and a verifiable definition of done. No re-interviewing. A task that is independently
   grabbable, or that is going to an agent, is carved out as a natively linked sub-issue; everything
   else stays a checklist line.
3. **code** — the work itself, against the PRD.
4. **close** — ship what is done, write where the PRD stands, park every loose end under a parent
   PRD, and close the issue only when its acceptance list is genuinely met.

Two branches off step 1. A **brain dump** (several open questions at once, visionary thinking, a
pasted conversation) goes to `brain-dump`, which sorts it into claims, questions, decisions and
vision, sweeps and refutes, and lands each result in its own home. An effort that is **too big and
too fogged** for one session goes to `wayfinder`, which charts it as a PRD whose route is unknown
and breaks the fog into investigation sub-issues, one resolved per session.

**The mechanism stack.** Four types, one job each. Mixing them makes harness behaviour
unpredictable.

- **Skills** (`.claude/skills/<name>/SKILL.md`) hold methodology. Invoked by name (`/grill`) or by
  the model when the description matches.
- **Overlays** (`<area>/CLAUDE.md`) hold the rules for one directory and auto-load when a file in
  it is touched. A new code directory gets one without asking; it is the mechanism, not a document.
- **Hooks** (`.claude/settings.json`) hold automation that must fire on a harness event, not on the
  model remembering. Today: the grill protocol on `SessionStart`, the soul rules on every prompt,
  `md_guard` and `issue_guard` on `PreToolUse`, and the memory commit-and-push on `Stop`.
- **GitHub issues** hold the durable backlog. Anything that must survive the chat lives there.

**The board.** One GitHub project, created by `.claude/scripts/setup-github.py --board`. Status is
a board column, never a label: `LowPriority`, `Not started`, `In Progress`, `Review`, `Done`. Set it
with `python3 .claude/scripts/board-status.py <issue> "In Progress"`. Triage state is a label
(`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) and is a different
axis from the column; do not confuse them.

**Before you push.** Run the project's own test command (scoped by
`.claude/scripts/gate-scope.py`, see build/release), and
`python3 docs/adr/tools/check_index.py`. Both must exit clean. The push is the ship: this repo
works on `main` only (ADR-0001), so a push is visible to everyone immediately and there is no PR
step to catch anything you skipped.

**Commits.** Imperative and scoped: `module: description`. The scope is the module or area, not the
file. A commit that needs "and" in its subject line is two commits.

**Memory.** Claude's memory folder is linked into `.claude/memory` by
`.claude/scripts/bootstrap.sh`, and the `Stop` hook commits and pushes it. Memory therefore
survives a wiped machine, and is readable by anyone with the repo. Nothing secret goes in it.

## workflow/module-standard

The house standard for a module in this repo. It exists so that a reader can predict the shape of
code they have not seen yet.

- **One interface, one directory.** A module is a directory with an obvious way in. Callers import
  the way in, never a file inside it. Files that are not part of the interface are private
  (`_prefix` in Python, not exported in TypeScript, package-private in Java).
- **Deep over shallow.** A module earns its existence by hiding more than it exposes. If its
  interface is nearly as complicated as its implementation, it is a shallow module and belongs
  inlined into its caller. Vocabulary and the full argument:
  [`.claude/skills/improve-codebase-architecture/LANGUAGE.md`](../.claude/skills/improve-codebase-architecture/LANGUAGE.md).
- **One function, one purpose.** If the docstring needs "and" between two concerns, it is two
  functions.
- **Tests sit with the module** they test, named for the invariant rather than the function
  (`test_<invariant>`), and drive the module through its public interface. A test that reaches into
  the implementation freezes the implementation.
- **Failures propagate.** A write that can fail raises; it does not log and continue. The two tiers
  are: a failure the caller can do something about (raise a typed error) and a failure nothing can
  be done about (crash loudly). Swallowing is neither.
- **Every directory carries its overlay** (`CLAUDE.md`) once it has rules of its own.

<Extend this chapter with the specifics this project needs: the layer names, the test command, the
directory layout. The rules above hold whatever the language is.>

## workflow/bootstrap

Getting a fresh machine, or a wiped one, back to working.

1. Clone the repo, and install the GitHub CLI so `gh auth status` is green. The skills that touch
   issues and the board go through `gh`; without it, `to-prd`, `triage`, `close` and `my-issues`
   cannot run.
2. `bash .claude/scripts/bootstrap.sh`. It links `~/.claude/projects/<encoded-repo-path>/memory` to
   the repo's tracked `.claude/memory`, so memory rides along with git, and reports anything else
   that is missing. It is safe to re-run; every step skips what is already done.
3. `python3 .claude/scripts/setup-github.py --board` on a fresh repo only. Labels and the board are
   GitHub-side state and are not copied by "Use this template", so a repo spawned from the template
   starts without them.

**What survives a wipe:** everything in git, memory included. **What does not:** `gh` auth, any
local toolchain, and anything a session left uncommitted. That asymmetry is the reason the memory
folder is tracked.

## Identifiers

<The names and numbers a session needs and cannot derive: repository, board number, hosts, service
IDs, secret names. Keep it a table. Anything secret goes in a secret store, and only its name goes
here.>

| What | Value |
|---|---|
| Repository | `<owner>/<repo>` |
| Project board | `<number>` |
