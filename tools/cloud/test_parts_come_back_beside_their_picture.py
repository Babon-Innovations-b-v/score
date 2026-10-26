"""parts.py's invariant: a PartCrafter run of picture <folder>/<name>.png at n parts comes back as
<folder>/parts/<name>-<n>/ on the cluster as on a machine (the layout the parts folder's readers and timings.json rely
on), at the part count asked for, and two part counts of one picture never land in one folder.

Break that turns it red: in `cluster_job`, drop the `"parts"` folder from the output's local path, or tag the run
with the picture's stem alone.
"""
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import parts  # noqa: E402


def test_each_part_count_comes_back_into_its_own_folder_under_parts():
    picture = pathlib.Path("/pics/microwave.png")
    four, six = parts.cluster_job(picture, 4), parts.cluster_job(picture, 6)
    assert six["inputs"] == [{"local": "/pics/microwave.png", "path": "/work/in/microwave.png"}]
    assert [output["local"] for output in four["outputs"] + six["outputs"]] == [
        "/pics/parts/microwave-4", "/pics/parts/microwave-6"]
    words = shlex.split(six["command"][2])
    assert words[words.index("--num_parts") + 1] == "6"
    # the folder the run writes is the one brought back
    assert f"{words[words.index('--output_dir') + 1]}/{words[words.index('--tag') + 1]}" == six["outputs"][0]["path"]
