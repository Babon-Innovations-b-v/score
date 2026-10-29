# tools/cloud/backends/

The cloud providers the runners rent from, one module each, behind `../provider.py`'s interface.
`scaleway.py` is the current backend; `SCORE_CLOUD` chooses one. `local.py` is this PC's own card as one machine
(a Docker container, never rented, EUR 0; `../CLAUDE.md` "This PC's card"): its offers are always `parked`, and its
`take`, which only `park.here` calls, holds the PC's one claim, or for a `SHARED` kind (Blender) a share of it with
the free ones of its `RUNS_AT_ONCE` turns, so several places' Blender claims run side by side. `card_turn.py` is no backend: a Blender startup
script `local.take` copies into the container so the Blender jobs a claim runs side by side take the card at most
`card_turn.CARD_SLOTS` (two) calls at a time.

**Adding a backend:**
1. Write `<name>.py` with everything `../provider.py`'s docstring lists (`NAME`, `CLASSES`, `QUOTAS`, `account()`,
   `offers()`, `price()`, `month_spend()`, `allow_key()`, `create()`, `start_if_stopped()`, `address()`, `retag()`,
   `delete()`, `ours()`, the leftover sweeps, `secret()`, `registry()`, `object_store()`). Copy the shape of
   `scaleway.py`. Check every resource's own account field before deleting it, never only a list filter.
2. Give `../self_delete.py` the backend's way for a machine to learn its id and delete itself (its `BACKENDS`
   table), using only the standard library and a key that can do nothing but that.
3. Run with `SCORE_CLOUD=<name>`, first with `--dry-run`, then one small batch, and compare its rows in
   `../capacity.py report` with the current backend's.

- **A backend holds every provider detail:** its machine types per capability class (`CLASSES`, in the
  order to try them), zones, images, prices, stock words and its CLI or API. Nothing provider-specific
  leaks into the runners or `capacity.py`.
- **Name the account and the zone on every call.** With Scaleway, every `scw` call names the project
  and the zone: the CLI's default profile may point at another project; never change it, and never
  rent from it.
- **Check each resource's own account field before deleting it** (`ours`, `leftover_*`); a list
  filter that silently does not apply returns other projects' resources.
- **Map a class only to a type that was seen working.** The P100 (Scaleway RENDER-S) gives no class:
  its machines booted but the GPU image's driver did not see the card (2026-10-08).
- A machine's self-delete for the backend lives in `../self_delete.py`'s `BACKENDS`, standard library
  only, since that file goes onto the machine alone.
