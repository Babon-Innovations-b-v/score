# score/stages/library/clips/

The library-clips row (owner, 2026-10-20): each item a place's handover made new gets its preview clip (CONTEXT.md
"preview clip"), rendered in cloud Blender with the films' renderer and light rig. `__init__.py`'s docstring has the
make, the output, the gate and the price; `sample.py` the sample shapes; `blender/` what runs on the card.

- **Part of the handover, never a re-render of the library.** Only entries the place's handover report made new
  (`NEW`) without a standing clip are rendered; an unchanged entry is never clipped here (the remake replaces most of
  the library; rendering what stands is waste). The row reads library@<place> and nothing reads it.
- **A place's clips spread over warm cards** (owner's one-shot rules: waste is time on one card; quality
  unchanged). The node's items go in shares of `CLIPS_A_CARD` (7: a card works about as long as the remake's longest
  timed layer, `CARD_MINUTES` 90 at the measured `CLIP_MINUTES` 12), one Blender job (`blender/render_clips.py`) a
  share, all in one `blender_cloud.py` call that puts one card on each share side by side; no machine per item.
  The flat's 54 clips: 8 cards, about 1.5 h, not 10.5 h on one card. A failed item is named in its share's
  `rendered.json` and the others still render; a share whose job brought nothing back leaves its items not
  rendered; a paid node never runs again inside its batch.
- **What ships, not a cheaper look.** The films' drawer (`tools/blender/inside/usd_views.py`), size and samples;
  never lower them for the clips (quality is never a cost lever). The length (`framing.SECONDS`) is the films' shot.
- **score never imports the library.** What a clip opens comes from the library's `clip-plan`, the clip goes in
  through its `clip-attach`; score reads only their JSON.
- **The price is measured** (2026-10-21): library-clips-sample's 6 clips, EUR 0.96 on one L4 in 72 min (EUR 0.16
  and about 12 min a clip, 7.3 s a frame), a `RECORDED` run in `tools/costs/per_unit.py` with its line's own time
  (703.95 s a clip, 1.45 min a fresh card's set-up), so prepare prices and times the layer from
  `data/costs/per-unit.json`. `per_item` (the films' seconds a frame, `ESTIMATED_FROM`) is now only the row's
  clearance estimate. The clip gate's check runs before attach: one clip not whole and none goes into the library.
- **What the plan opens** (score_lib 259d7488, 2026-10-21): `clip-plan` fetches an entry's picture-role files too (a
  sky's dome picture; before, a sky rendered magenta), and plays an effect as one loop (`score:effect:loop`) from the
  time code where its points show most (`clip.busiest_loop`), so a sparse effect (the breath: a puff every 20 s
  over a 600 s stage) opens on the puff, not an empty first frame. Not yet rendered since.
- **No benchmark row.** `library-clips-sample` clipped the old library drafts `data/definitions/clip_samples.json`
  named; it measured the make (its runs are the price above) on old models only, so it was dropped with them (owner,
  2026-10-21: all old stuff is retired). The clips of the batch's own new items are their own measure: each run of
  library-clips is a ledger line `tools/costs/per_unit.py` reads.
- **Never edit `tools/blender/inside/` for this row** (other rows declare that folder: their keys would move). The
  framing lives in `blender/framing.py`.
- Test: `PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/library/clips/clips_test.py` (no Blender, no spend:
  a fake library and a fake render; the frames encoded with the real ffmpeg).
