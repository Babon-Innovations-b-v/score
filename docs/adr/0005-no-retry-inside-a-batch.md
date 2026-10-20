# No retry inside a batch, except a free step or a read that buys nothing

**Status:** accepted

A batch is one shot of paid work the creator said yes to, with one spend estimate given before it
starts (`CONTEXT.md`: batch). The runner nevertheless reran any node after a transient error, up to
five times, and every rerun of a paid node took a new clearance, so one paid stage could be paid
for five times inside one yes; the World API client asked a paid call again up to thirty times.
Retry, wait and fallback code was built for ten days and reversed on 2026-10-20 (#30).

We decided: inside a batch a paid step runs once. Its failure is a gap, recorded and priced into
the next batch, which is a new ask. The runner (`run_retrying`) reruns only a node whose stage is
not paid; a client may ask again only on a read that buys nothing (a status poll, a listing), never
on a call that starts paid work. A free local step (a thinning pass tried again at a gentler
setting) may loop as it likes.

The trade-off: a passing network fault now costs a gap and a second ask instead of a silent
retry. We take that, because a silent retry is spend nobody said yes to and an estimate that is no
longer the bill. The rule's wording lives in bible `workflow/module-standard`.
