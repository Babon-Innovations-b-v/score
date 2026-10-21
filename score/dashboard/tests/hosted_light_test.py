"""A hosted dashboard stays light: in a process of its own in hosted mode, every page renders from an export, no score
module outside score/dashboard is imported (the hosted image holds no other), and
numpy, pxr, score.stages and score.store are never imported; its memory stays under 200 MB."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

from score.dashboard.state.models import Spend
from score.dashboard.sync import building

pytestmark = pytest.mark.django_db
REPO = pathlib.Path(__file__).resolve().parents[3]
MOST_MB = 200
CHILD = """
import json, os, sys
import django
django.setup()
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
from django.contrib.auth import get_user_model
from django.test import Client
user = get_user_model().objects.create_user("joey", password="a long enough password")
client = Client()
client.force_login(user)
pages = ["/", "/places/", "/environments/world1/", "/place/alpha/", "/place/beta/", "/place/alpha/step/closeup/",
         "/world/step/terrain/", "/basket/", "/runs/", "/requests/", "/healthz"]
codes = {page: client.get(page, HTTP_HOST="127.0.0.1").status_code for page in pages[:-1]}
import score.dashboard.site.asgi  # what the hosted image serves
heavy = [name for name in ("numpy", "pxr", "score.stages", "score.store", "score.dashboard.previews", "matplotlib")
         if name in sys.modules]
# the hosted image holds score/__init__.py and score/dashboard alone
heavy += [name for name in sys.modules if name.startswith("score.") and not name.startswith("score.dashboard")]
# VmHWM, this process's own peak (ru_maxrss keeps the forking parent's peak across exec)
rss = int(next(line for line in open("/proc/self/status") if line.startswith("VmHWM")).split()[1]) / 1024
print(json.dumps({"codes": codes, "heavy": heavy, "rss_mb": rss}))
"""


# owner rule: hosted mode never imports score.stages, score.store, numpy or usd-core (dashboard overlay)
def test_hosted_renders_every_page_light(world, tmp_path):
    home = tmp_path / "hosted"
    building.build(world.source, home / "export" / "one", "2026-10-18T12:00:00+00:00", 50,
                   Spend(spent=1.0, reserved=0.0, ceiling=250.0), REPO)
    (home / "export" / "current").symlink_to("one")
    env = {**os.environ, "SCORE_DASHBOARD_MODE": "hosted", "SCORE_DASHBOARD_HOME": str(home),
           "DJANGO_SETTINGS_MODULE": "score.dashboard.site.settings", "PYTHONPATH": str(REPO)}
    done = subprocess.run([sys.executable, "-c", CHILD], env=env, cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-3000:]
    found = json.loads(done.stdout.strip().splitlines()[-1])
    assert set(found["codes"].values()) == {200}, found["codes"]
    assert found["heavy"] == [], found["heavy"]
    assert found["rss_mb"] < MOST_MB, found["rss_mb"]
