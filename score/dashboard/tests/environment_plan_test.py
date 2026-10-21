"""The environment's plan page (pages/environment_plan.py) on the fixture environment: a map a ground with its sites,
each site's sky once it has a scene time (on hover over its time, no column), the top places' blockouts, his Keep kept as his own and anyone but the
owner refused. No model is called, nothing is spent."""
import json

import pytest

from score.dashboard.tests.pages_test import signed_in
from score.review import environment_plan

pytestmark = pytest.mark.django_db(transaction=True)


def test_the_plan_page_shows_each_world_and_keeps_his_scene_times(world):
    name = world.source.world_state().world
    owner = signed_in()
    html = owner.get(f"/environments/{name}/plan/").content.decode()
    assert 'aria-label="Moon map"' in html and 'aria-label="Mars map"' in html and 'aria-label="Earth map"' in html
    assert 'data-place="base"' in html and "base blockout" in html.lower()  # its site's blockout, rendered free
    assert "55.0000° N, 0.0000° E" in html  # where the setting puts it
    assert f'href="/environments/{name}/plan/"' in owner.get(f"/environments/{name}/").content.decode()
    plan = {"maps": [{"on": "moon", "sites": [{"place": "base", "time": "2099-06-01T12:00:00Z"}]}]}
    answer = owner.post(f"/environments/{name}/plan/keep/", json.dumps({"plan": plan}),
                        content_type="application/json")
    assert answer.status_code == 200, answer.content
    shown = environment_plan.current(world.store, name)
    assert shown["how"] == "edited"
    base = environment_plan.site_of(world.store, "base", name)
    assert base["time"] == "2099-06-01T12:00:00Z" and base["overhead"]["bodies"]
    world.source.refresh()
    page = owner.get(f"/environments/{name}/plan/").content.decode()
    assert ">Sky<" not in page and ">Sun<" not in page  # the sky is no column: it follows from the setting
    assert "Overhead, from the setting: Sun" in page and "Earth " in page  # on hover over its time
    refused = signed_in("joey2").post(f"/environments/{name}/plan/keep/", json.dumps({"plan": plan}),
                                      content_type="application/json")
    assert refused.status_code == 403
