"""Level 3 on the card (#70, plan step 1): mink's damped step in reduced dofs and the exact projection, batched
over rows (frames, later bodies' level-1 sets). The CPU mink path in `_frames.py` stays the reference."""
from ._project import Projection, project
from ._step import Reduction, damped_step

__all__ = ["Projection", "Reduction", "damped_step", "project"]
