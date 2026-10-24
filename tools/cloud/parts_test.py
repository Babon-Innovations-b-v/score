"""Checks for a PartCrafter run as a cluster job (SCORE_CLOUD=k8s), without renting anything."""
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import parts  # noqa: E402


def test_a_run_comes_back_where_the_machine_runner_puts_it():
    picture = pathlib.Path("/pics/microwave.png")
    job = parts.cluster_job(picture, 6)
    words = shlex.split(job["command"][2])
    assert "parts-run" in words and words[words.index("--num_parts") + 1] == "6"
    assert words[words.index("--tag") + 1] == "microwave-6"
    assert job["inputs"] == [{"local": "/pics/microwave.png", "path": "/work/in/microwave.png"}]
    assert job["outputs"] == [{"path": "/work/out/microwave-6", "local": "/pics/parts/microwave-6"}]
    assert job["models"] == ["partcrafter"]
