# tools/private_names/

The push gate's refusal of private names (score #142; root `CLAUDE.md`, Deployment: nothing from babon or Movalytics,
no cloud account or project ids). `.claude/hooks/local/pre-push` runs `check.py <base> <tip>` over the lines a push
adds; one fault refuses the push.

- **Digests, never the names.** `NAMES` holds sha256 digests, so the guard never publishes what it refuses; add one as
  `hashlib.sha256(name.lower().encode()).hexdigest()` with a comment saying what kind of name it is, never the name.
- **What it refuses**: another company's cloud project, cluster label or pool, a path in its private repository, and
  any patent application number (`PATENT`). A cluster's own setting the code needs comes from the box's environment
  (`SCORE_K8S_*`), never a literal.
- **Only added lines**: lines already in history are the owner's call (#142 lists them by file and commit); a line that
  stays where it is never trips the gate.
