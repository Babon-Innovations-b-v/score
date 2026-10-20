# score/stages/library/clips/

The library-clips row (owner, 2026-10-20): each item a place's handover made new gets its preview clip (CONTEXT.md
"preview clip"), rendered in cloud Blender with the films' renderer and light rig. `__init__.py`'s docstring has the
make, the output, the gate and the price; `sample.py` the sample shapes; `blender/` what runs on the card.

- **Part of the handover, never a re-render of the library.** Only entries the place's handover report made new
  (`NEW`) without a standing clip are rendered; an unchanged entry is never clipped here (the remake replaces most of
  the library; rendering what stands is waste). The row reads library@<place> and nothing reads it.
- **One machine a batch.** Every item of the node is one Blender job (`blender/render_clips.py`) on one card: no
  machine started per item. A failed item is named in `rendered.json` and the others still render; a paid node never
  runs again inside its batch.
- **What ships, not a cheaper look.** The films' drawer (`tools/blender/inside/usd_views.py`), size and samples;
  never lower them for the clips (quality is never a cost lever). The length (`framing.SECONDS`) is the films' shot.
- **score never imports the library.** What a clip opens comes from the library's `clip-plan`, the clip goes in
  through its `clip-attach`; score reads only their JSON.
- **The price is estimated until measured.** `per_item` is the films' measured seconds a frame at the L4's billed
  price (`ESTIMATED_FROM`), said so wherever it shows (prepare's `estimated_from`); once library-clips has a measured
  per unit in `data/costs/per-unit.json`, prepare uses that.
- **The benchmark is `library-clips-sample`** (one environment node, paid): the same make over the drafts
  `data/definitions/clip_samples.json` names (one a framing), clipped and put into their entries, so a clip's
  seconds and euros are measured. Only on the owner's yes: `SCORE_BENCHMARK_GRANT=<grant> python -m score run world1
  --stage library-clips-sample --detach`.
- **Never edit `tools/blender/inside/` for this row** (other rows declare that folder: their keys would move). The
  framing lives in `blender/framing.py`.
- Test: `PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/library/clips/clips_test.py` (no Blender, no spend:
  a fake library and a fake render; the frames encoded with the real ffmpeg).
