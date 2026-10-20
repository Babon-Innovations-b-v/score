"""Surface recipes: no demo here. The recipes (`tools/props/library/recipes.py` `channels`) are ProcFunc node graphs
that only Blender evaluates (ProcFunc needs bpy; the wear and dirt masks read the true geometry and its ambient
occlusion), and no baked tile of one is kept on this machine, so its page shows what it reads and makes."""
from score.stages.library.demos import NoExample

ALGORITHM = "surface_recipes"


def made(inputs):
    raise NoExample("its recipes are ProcFunc node graphs only Blender evaluates (wear and dirt read the true "
                    "geometry and its ambient occlusion), and no baked tile of one is kept on this machine")
