r"""Invariant of characters.py's set-up (tools/cloud/characters_setup.sh): it installs, as root, every package the
vendored SAM3DBody-cpp setup (vendor/sam3dbody-cpp/scripts/setup.sh) checks for, so that script never reaches its
`sudo apt-get install` branch; this PC's container runs as root with no sudo (env1 round 33: the sam3dbody step
failed on "sudo: command not found" for python3-pip).

The break that turns it red: drop `python3-pip` from characters_setup.sh's apt-get install line.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]


def test_every_package_sam3dbody_checks_for_is_installed_before_it_runs():
    vendored = (REPO / "vendor/sam3dbody-cpp/scripts/setup.sh").read_text()
    checked = set(re.search(r'SYSTEM_DEPENDENCIES="([^"]*)"', vendored).group(1).replace("\\\n", " ").split())
    setup = (REPO / "tools/cloud/characters_setup.sh").read_text()
    install = re.search(r"^apt-get install -y -qq (.*?)>/dev/null", setup, re.MULTILINE | re.DOTALL).group(1)
    assert checked <= set(install.replace("\\\n", " ").split()), checked - set(install.replace("\\\n", " ").split())
