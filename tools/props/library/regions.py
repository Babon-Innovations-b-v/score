"""A clean close-up's finish regions, the painting unit of labels.py `--regions`: SAM 2.1's masks
(../cloud/segment.py) made into one region per pixel (job repaint, 2026-10-08: PartCrafter's parts do not follow
where one finish ends and the next begins, a foil patch on a lander's hull, a seat on its frame; the picture's own
regions do).

A pixel belongs to the smallest kept mask over it (a patch on a panel is the patch). A mask under REGION_LEAST of the
object's pixels is not kept (the judge is asked about every region), nor one over REGION_MOST (the whole object, or
most of it: what it leaves between the smaller masks mixed a chair's seat with its frame), and a pixel of the object
no kept mask covers takes the nearest region. Each region is judged on its own: regions grouped by colour joined a grey
seat with its grey base.
"""
import numpy as np
from scipy import ndimage

REGION_LEAST = 0.01
REGION_MOST = 0.6


def masks_of(path):
    """The masks a segment.py file holds, as booleans (n x height x width)."""
    with np.load(path) as stored:
        height, width = stored["shape"]
        return np.unpackbits(stored["masks"], axis=-1)[..., :width].astype(bool).reshape(-1, height, width)


def region_map(masks, inside):
    """Each pixel's region (-1 outside the object, `inside`): the smallest kept mask over it, else the nearest
    region."""
    area = (masks & inside).sum(axis=(1, 2))
    kept = [index for index in np.argsort(-area)
            if REGION_LEAST * inside.sum() <= area[index] <= REGION_MOST * inside.sum()]
    found = np.full(inside.shape, -1)
    for number, index in enumerate(kept):  # largest first, so the smallest over a pixel is laid last
        found[masks[index] & inside] = number
    if (found >= 0).any():
        _, nearest = ndimage.distance_transform_edt(found < 0, return_indices=True)
        found = found[nearest[0], nearest[1]]
    found[~inside] = -1
    used = np.unique(found[found >= 0])  # a mask the smaller ones laid over it covered whole is no region
    found[found >= 0] = np.searchsorted(used, found[found >= 0])
    return found


def vivid(regions, colours, share=0.9):
    """Each region's chroma at its `share` quantile (Lab, `colours` per pixel): how colourful its most colourful
    tenth is (the power unit's gold tape regions are mostly grey at the median and gold at the top)."""
    chroma = np.hypot(colours[..., 1], colours[..., 2])
    return np.array([np.quantile(chroma[regions == region], share) for region in range(int(regions.max()) + 1)])


def medians(regions, colours):
    """Each region's median colour (Lab, `colours` per pixel)."""
    return np.array([np.median(colours[regions == region], axis=0) for region in range(int(regions.max()) + 1)])
