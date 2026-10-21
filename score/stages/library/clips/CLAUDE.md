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
- **The price is measured** (2026-10-21): library-clips-sample's 6 clips, EUR 0.96 on one L4 in 72 min (EUR 0.16
  and about 12 min a clip, 7.3 s a frame), a `RECORDED` run in `tools/costs/per_unit.py`, so prepare prices the layer
  from `data/costs/per-unit.json`. `per_item` (the films' seconds a frame, `ESTIMATED_FROM`) is now only the row's
  clearance estimate. The clip gate's check runs before attach: one clip not whole and none goes into the library.
- **What the plan opens** (score_lib 259d7488, 2026-10-21): `clip-plan` fetches an entry's picture-role files too (a
  sky's dome picture; before, a sky rendered magenta), and plays an effect as one loop (`score:effect:loop`) from the
  time code where its points show most (`clip.busiest_loop`), so a sparse effect (the breath: a puff every 20 s
  over a 600 s stage) opens on the puff, not an empty first frame. Not yet rendered since.
- **The benchmark is `library-clips-sample`** (one environment node, paid): the same make over the drafts
  `data/definitions/clip_samples.json` names (one a framing), clipped and put into their entries, so a clip's
  seconds and euros are measured. Only on the owner's yes: `SCORE_BENCHMARK_GRANT=<grant> python -m score run world1
  --stage library-clips-sample --detach`.
- **Never edit `tools/blender/inside/` for this row** (other rows declare that folder: their keys would move). The
  framing lives in `blender/framing.py`.
- Test: `PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/library/clips/clips_test.py` (no Blender, no spend:
  a fake library and a fake render; the frames encoded with the real ffmpeg).
