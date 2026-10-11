# score/stages/finishmap/

EXPERIMENTAL (bible `architecture/experimental`): the finish-map route of the surface stage, tested on round 4's six
models on 2026-10-11 with the owner's approval (EUR 15 in all). A model's parts come from its close-up, not from its own
texture (shaded, and invented on unseen sides): Gemini 3.1 Pro lists the close-up's finishes, each a library surface
(`ask.finish_list`); Nano Banana Pro redraws the close-up as a finish map (`ask.draw_map`), checked by measurement
(`maps.check`); the map is laid onto the raw Pixal3D model, its geometry kept (`lay.py`).

- **Rows, not scripts** (`trial.py`, `python -m score.stages.finishmap.trial status|run|why`): fm-lists, fm-maps and
  fm-segvigen are paid and cleared by the runner; fm-arms is free. Nothing spends outside the runner.
- **A picture's colours never reach a model.** The map's label colours only name finishes; every part is painted from
  its finish's library surface. A new surface Gemini proposes is reported, never added to the library.
- **Every Google call goes through `google_spend.generate`** with `cache=True`: priced on the Google ledger, asked once
  per input.
- **Licences**: SegviGen and TRELLIS.2 (MIT) through `tools/props/cloud/meshparts.py` (nvdiffrast and RMBG-2.0 never
  installed); Tencent Hunyuan3D-Paint is out (its licence excludes the EU).
- **Measured, never judged by eye**: the arms are measured by round 4's own `measure.py` (surface-first branch), from
  the coordinator's `refocus/surface/fm/measure_fm.py`, outside these rows.
- Checks: `finishmap_test.py`.
