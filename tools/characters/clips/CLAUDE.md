# tools/characters/clips/

The tools for video clips (CONTEXT.md "video clip", #52): a body's motion read off the creator's video and put onto
the people's rig. They are run by the row `video-clip-<clip>` (`score/stages/video_clips`).

- `video_motion.py` runs on the rented characters machine (`../../cloud/characters.py` program
  `video_motion.py`, through `../maker/chain.py`'s step runner). It runs sam3dbody-cpp's offline extractor on the
  video and keeps the BVH of the person seen in the most frames. Nothing here runs a model on the owner's PC.
- `retarget.py` is plain numpy and scipy and runs on the store's machine. It reads the BVH, gives each of SOMA-X's 27
  kept joints the world turn of its mapped BVH joint (`MAP`; an unmapped joint takes the turn of its nearest mapped
  joint above it) applied to its own rest, and keeps the rig's bone lengths. It then resamples to 30 frames a second,
  smooths, and takes the travel off. Its module docstring has the maths.
- **Look at the result.** As `../people/` says, the numbers only show that something changed. Before a clip is called
  right, a person playing it has to be watched. Nothing has been watched yet: the BVH's joint names, its turns as
  sam3dbody-cpp writes them and the body's facing are taken from its README and `bvh_writer.cpp`, not from a real
  run.
- `people/body.py`'s rules (travel off, stood over the node) are repeated in `retarget.on_the_spot`, because body.py
  imports torch and the gate runs without it. If one of them changes, change both.
- Never edit `../maker/` or `../people/` for this route. Both folders are declared inputs of the paid people rows, so
  an edit there re-keys every body.
- Tests: `retarget_test.py` runs a synthetic BVH through the seam (read, retarget, smoothing, resampling, on the spot).
