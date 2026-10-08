# tools/props/closeup/

The close-up stage: one clean, three-quarter picture of each generated row of a place, the input to the prop
pipeline. Entry: `stage.py`; its docstring says how to call it. The owner's decision (2026-10-08): Qwen-Image-Edit-2511
draws every close-up first, the shape check (`check.py`) decides without a person whether each may go on, and Nano
Banana Pro (`pro.py`) draws only the ones it fails. Pro's pictures are checked the same way: given the whole room,
Pro sometimes draws it behind the object, as a miniature, or with dimension lines, so a failed first Pro take is
drawn again from the crop alone, and a row whose every take fails is left for the creator.

- **No model runs here.** Qwen draws on rented cards (`../cloud/pictures.py --model qwen-edit`), the judge answers on
  one (`../cloud/judge.py`); the measurements and the decision are plain Python.
- **The check leans to failing.** A close-up passed wrongly costs a bad 3D model; one failed wrongly costs one Pro
  picture. Its limits were tuned on the 40 hand-scored close-ups of job openpics (2026-10-08); a change to a limit
  or to the judge's question is measured on those again before it lands.
- **Pro's quota is shared** (250 a day): only `stage.py` calls `pro.py`, and only for rows the check failed.
- **Print does not matter** on a close-up: labels and print go on the model as decals later.
- Checks are plain scripts (`*_test.py`) run by `make tests`.
