"""The walkers' pieces made by Kimodo, one after another from the pose each last one ended in, and joined
(score/stages/walker_route, the owner's design of 2026-11-17), free on this PC's card in Kimodo's own environment:

    <motion env>/bin/python walker_route.py <tree> <folder>

<folder>/walkers.json is the plan (walker_route.write_plan). Kimodo's model is loaded once (people/clips.py's model;
its fixed seed for the first walker, the next seed for each walker after), the text encoder answered from saved embeddings when SCORE_KIMODO_EMBEDDINGS names their folder.
Writes per walker <folder>/motions/<clip>.npz (Kimodo's NPZ keys, in the walker's placement frame: its route's start
at the origin, its first heading +Z, its start's ground y = 0), <folder>/joined/<clip>.npz (the scene's frame) and
<folder>/made.json (each piece's frames, sentence and seconds taken).
"""
import importlib
import importlib.util
import json
import os
import pathlib
import sys
import time

import numpy as np

tree, folder = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("walker_route", tree / "score/stages/walker_route/__init__.py")
walker_route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(walker_route)
sys.path.insert(0, str(tree / "tools/characters/people"))
import clips as sentences  # noqa: E402

import torch  # noqa: E402

load_model = importlib.import_module("kimodo.model.load_model")
if os.environ.get("SCORE_KIMODO_EMBEDDINGS"):
    sys.path.insert(0, os.environ["SCORE_KIMODO_EMBEDDINGS_CODE"])
    load_model._select_text_encoder_conf = lambda url, fp32=False: {"_target_": "cached_encoder.CachedEncoder"}
from kimodo import load_model as loaded  # noqa: E402
from kimodo.constraints import load_constraints_lst  # noqa: E402
from kimodo.tools import seed_everything  # noqa: E402

device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = loaded(sentences.MODEL, device=device, default_family="Kimodo")
plan = json.loads(walker_route.plan_file(folder).read_text())
for name in ("motions", "joined"):
    (folder / name).mkdir(exist_ok=True)
record = {"place": plan["place"], "model": sentences.MODEL, "seed": sentences.CLIP_SEED, "walkers": {}}
for number, walker in enumerate(plan["walkers"]):  # each walker its own seed: walkers on like routes never step as one
    roots, headings = np.asarray(walker["roots"]), np.asarray(walker["headings"])
    feet = np.asarray(walker["feet"])
    motion, made = None, []
    for piece in walker["pieces"]:
        began = time.time()
        ask = walker_route.asked(piece, roots, headings, feet, motion)
        seed_everything(sentences.CLIP_SEED + number)
        output = model([ask["sentence"]], [ask["frames"]], num_denoising_steps=100, multi_prompt=True,
                       constraint_lst=load_constraints_lst(ask["constraints"], model.skeleton),
                       num_samples=1, post_processing=ask["postprocess"], return_numpy=True, progress_bar=lambda x: x)
        single = {key: np.asarray(output[key])[0] for key in walker_route.KEYS}
        if len(single["posed_joints"]) != ask["frames"]:
            raise RuntimeError(f"{walker['name']}: Kimodo gave {len(single['posed_joints'])} frames for {ask['frames']}")
        placed = walker_route.moved(single, np.asarray(ask["origin"]), ask["heading"])
        motion = walker_route.joined(motion, placed, piece["start"])
        made.append({**piece, "frames": ask["frames"], "sentence": ask["sentence"], "postprocess": ask["postprocess"],
                     "seconds": round(time.time() - began, 1)})
        print(walker["name"], piece, round(time.time() - began, 1), "s", flush=True)
    motion = walker_route.held_feet({key: value[:len(roots)] for key, value in motion.items()})
    np.savez(folder / "joined" / f"{walker['clip']}.npz", **motion)
    origin = np.array([roots[0, 0], roots[0, 1], roots[0, 2]])
    own = walker_route.moved(motion, origin, float(headings[0]), inverse=True)
    np.savez(folder / "motions" / f"{walker['clip']}.npz", **{key: own[key].astype(np.float32) if own[key].dtype.kind == "f"
                                                                else own[key] for key in own})
    record["walkers"][walker["name"]] = made
(folder / "made.json").write_text(json.dumps(record, indent=1))
print("made", len(plan["walkers"]), "walkers", flush=True)
