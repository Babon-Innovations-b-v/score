r"""Invariant of characters.py's set-up (tools/cloud/characters_setup.sh): it installs, as root, every package the
vendored SAM3DBody-cpp setup (vendor/sam3dbody-cpp/scripts/setup.sh) checks for, so that script never reaches its
`sudo apt-get install` branch; this PC's container runs as root with no sudo (env1 round 33: the sam3dbody step
failed on "sudo: command not found" for python3-pip).

The break that turns it red: drop `python3-pip` from characters_setup.sh's apt-get install line.

second test: characters.py's cluster path (SCORE_CLOUD=k8s) is another invariant of the same runner: a clip make
goes to the cluster as one job in the characters-motion image, its in/ up and its out/ back at the make folder, its
program in the motion environment with its models named; a make with a step the image cannot run (a look's shell) or a
held machine (--hold) rents machines as without the cluster, nothing sent to it, and `cluster_job` refuses such a make
(env1's try of 2026-11-08: refused, the looks' bodies had no route). Breaks that turn it red: drop the
`provider.on_cluster()` branch in `main`; drop `not options.hold` or `on_the_image` from it; drop the
`steps <= CLUSTER_STEPS` refusal in `cluster_job`; drop `"models"` from `cluster_job`'s job.
"""
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


def test_every_package_sam3dbody_checks_for_is_installed_before_it_runs():
    vendored = (REPO / "vendor/sam3dbody-cpp/scripts/setup.sh").read_text()
    checked = set(re.search(r'SYSTEM_DEPENDENCIES="([^"]*)"', vendored).group(1).replace("\\\n", " ").split())
    setup = (REPO / "tools/cloud/characters_setup.sh").read_text()
    install = re.search(r"^apt-get install -y -qq (.*?)>/dev/null", setup, re.MULTILINE | re.DOTALL).group(1)
    assert checked <= set(install.replace("\\\n", " ").split()), checked - set(install.replace("\\\n", " ").split())


def test_a_clip_make_goes_to_the_cluster_and_a_look_make_to_machines(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / "tools/cloud"))
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import characters
    import cluster_jobs

    sent = []
    monkeypatch.setattr(cluster_jobs, "run", lambda kind, jobs, who, classes=None, image=None, **_: sent.append(
        (kind, jobs, image)) or [])
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    clips, look = tmp_path / "people-clips-make", tmp_path / "look-make"
    for make, steps in ((clips, ["clips", "rig"]), (look, ["shell", "build"])):
        (make / "in").mkdir(parents=True)
        (make / "in" / "spec.json").write_text(json.dumps({"program": "prop_chain.py", "steps": steps}))
    monkeypatch.setattr(sys, "argv", ["characters.py", str(clips), "--who", "test"])
    characters.main()
    (kind, jobs, image), = sent
    job, = jobs
    assert (kind, image) == ("characters", "characters-motion")
    assert job["inputs"] == [{"local": str(clips / "in"), "path": "/root/make/people-clips-make/in"}]
    assert job["outputs"] == [{"path": "/root/make/people-clips-make/out", "local": str(clips / "out")}]
    assert "tools/characters/maker/prop_chain.py /root/make/people-clips-make" in job["command"][-1]
    assert job["code"] == ["tools/characters"] and "kimodo-soma-rp-v1.1" in job["models"]
    def machines():
        raise SystemExit("to machines")
    monkeypatch.setattr(characters.cloud, "account", machines)
    for argv in ([str(look)], [str(clips), "--hold"]):
        monkeypatch.setattr(sys, "argv", ["characters.py", *argv, "--who", "test"])
        with pytest.raises(SystemExit, match="to machines"):
            characters.main()
    with pytest.raises(SystemExit, match="shell"):
        characters.cluster_job(look)
    assert len(sent) == 1
