---
name: close
description: Cleanly end a work session. Ship what's done, record where the PRD stands and what's next, and park every loose end durably under a parent PRD so nothing is lost to the chat. Closes the PRD only when its work is actually finished, never just because the session is ending. Use at session end, or when the user says "close this out", "anything left?", "wrap up", or invokes /close.
---

# Close

A clean end to a session. A PRD can span many sessions, so the job is to leave it resumable, not to force it shut. Ship what is done, write down where it stands, and lose nothing to the chat.

## Steps

1. **Find the work.** The PRD/issue this session served: a `#N` from the chat, or infer it from the branch and commits. No issue and the work was real → run `to-prd` first. A throwaway question → nothing to close.

2. **Sweep.** `git status` + `git log` for what landed or is still uncommitted. Open threads in the chat: half-done edits, "I'll do X next", decisions not written down. Leave any `TODO(<reviewer>)` in place.

3. **Park each loose end.** A small in-scope one you can finish now, finish it. The rest is written down, never filed: a loose end becomes a **Tasks** checklist line or a comment on the parent PRD, not a new issue.
   - fits this PRD → its **Tasks** checklist;
   - a small task that fits no workstream → a checklist comment on the standing backlog PRD (its number is `backlog_prd` in `.claude/project.json`); if the project has areas, a small task in another area goes under that area's workstream PRD instead;
   - filing a **new issue** (sub-issue via `to-prd`, its own module PRD, a `ready-for-agent`/`ready-for-human` hand-off) needs the user's explicit go-ahead in this session; without it, park the checklist line and note "candidate issue" so the next session can ask. Several sessions each filing a few unasked issues reads as spam on the board.
   A decision you made goes where it survives compaction: an issue comment or `CONTEXT.md`. An ADR is offered, never written unasked (root CLAUDE.md).

4. **Ship.** Before committing, run the project's own test command and `python3 docs/adr/tools/check_index.py`. Both must exit clean; a red gate is unfinished work, not a nit. Then commit scoped and push to `main` (ADR-0001). Push is the ship: there is no PR step to catch what you skipped.

5. **Record where it stands.** Comment on the PRD: what shipped this session, what is left, the next step. Tick the **Tasks** lines that are done. This comment is the resume point for the next session.

6. **Set the board Status.** Every issue this session touched must match reality on the board, never skip this step. An issue that stays open with real work landed goes to `In Progress`: `python3 .claude/scripts/board-status.py <N> "In Progress"`. The standing backlog PRD is the exception: it stays on `LowPriority` whatever landed under it (root `CLAUDE.md`). Closing an issue moves it to `Done` automatically, so skip that; but an issue that was already closed when it joined the board never gets the automatic move, set it by hand.

7. **Close only if done.** Re-check each **Acceptance** line from scratch. All genuinely met → close the issue, and the parent PRD too if it is fully done. Anything left → leave it open; step 5's comment is enough. When you close an issue, strip its triage-state labels (`needs-triage`, `ready-for-agent`, `ready-for-human`): those describe an open queue, and a closed issue that keeps them pollutes the board (`gh issue edit N --remove-label ...`).

8. **Hand off the assignee.** The board filters on the whole issue's assignee, so an open issue must be assigned to whoever owns the next action. For each issue that stays open (and each open parent of anything you closed): if the user's part is done and the rest belongs to someone else, remove the user and assign that person (`gh issue edit N --remove-assignee <user> --add-assignee <owner>`). Read the next owner from the open sub-issues or the issue body; if it is genuinely unclear, leave the assignee and say so in the step-5 comment.

9. **Report.** One line: what shipped, what is parked where, whether the PRD closed or stays open with what is left.

Team-facing text (comments, PRD edits) in English per [`.claude/soul.md`](../../soul.md). This skill closes a session; it does not open new scope.
