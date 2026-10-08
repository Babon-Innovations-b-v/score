# tools/props/cloud/backends/

The cloud providers the runners rent from, one module each, behind `../provider.py`'s interface.
`scaleway.py` is the current backend; `SCORE_CLOUD` chooses one. The README's "Add a cloud backend"
says how to add another.

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
