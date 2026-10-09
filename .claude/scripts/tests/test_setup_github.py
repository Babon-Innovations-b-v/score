"""Pin setup-github: labels synced, a template's config reset, a dry run changes nothing."""
import json
import subprocess

REPO_VIEW = {"stdout": json.dumps({"nameWithOwner": "acme/widget", "owner": {"login": "acme"}})}
LABELS = ["PRD", "vision", "bug", "enhancement", "needs-triage", "needs-info",
          "ready-for-agent", "ready-for-human", "wontfix"]


def setup_github(repo, env, *args):
    return subprocess.run(["python3", repo / ".claude" / "scripts" / "setup-github.py", *args],
                          env=env, capture_output=True, text=True)


def test_without_gh_login_nothing_happens(scratch_repo, fake_gh):
    env, answer, _ = fake_gh
    answer({"auth status": {"exit": 1}})
    run = setup_github(scratch_repo, env)
    assert run.returncode != 0
    assert "gh auth login" in run.stderr


def test_a_dry_run_changes_nothing(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    config = scratch_repo / ".claude" / "project.json"
    before = config.read_text()
    answer({"repo view": REPO_VIEW, "label list": {"stdout": json.dumps([{"name": "bug"}])}})
    run = setup_github(scratch_repo, env, "--dry-run", "--board")
    assert run.returncode == 0, run.stderr
    assert "would update label bug" in run.stdout
    assert "would create label PRD" in run.stdout
    assert "would create a project on acme and link it to acme/widget" in run.stdout
    assert config.read_text() == before
    assert not any(call["args"][:2] == ["label", "create"] for call in calls())


def test_a_template_config_is_reset_and_labels_synced(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    config = scratch_repo / ".claude" / "project.json"
    config.write_text(json.dumps({"repo": "template/origin", "project": {"number": 4, "owner": "template"},
                                  "backlog_prd": 12, "people": {"someone": "someone"}, "areas": ["paper"]}))
    answer({"repo view": REPO_VIEW, "label list": {"stdout": "[]"}})
    run = setup_github(scratch_repo, env)
    assert run.returncode == 0, run.stderr
    assert "config came from template/origin; resetting board, backlog and people" in run.stdout
    assert json.loads(config.read_text()) == {
        "repo": "acme/widget", "owner": "acme", "project": {"number": 0, "owner": ""},
        "backlog_prd": None, "people": {"acme": "acme"}, "areas": ["paper"]}
    created = [call["args"][2] for call in calls() if call["args"][:2] == ["label", "create"]]
    assert created == LABELS


def test_the_board_is_found_and_given_its_columns_and_fields(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    config = scratch_repo / ".claude" / "project.json"
    config.write_text(json.dumps({"repo": "acme/widget", "areas": ["paper"]}))
    fields = {"fields": [{"id": "F1", "name": "Status", "options": [{"name": "Todo"}]},
                         {"id": "F2", "name": "Roadmap start"}]}
    answer({"repo view": REPO_VIEW, "label list": {"stdout": "[]"},
            "project list": {"stdout": json.dumps({"projects": [
                {"title": "widget", "closed": False, "number": 5, "url": "https://example.test/5"}]})},
            "project view": {"stdout": json.dumps({"id": "PROJ"})},
            "project field-list": {"stdout": json.dumps(fields)},
            "graphql mutation": {"stdout": json.dumps({"data": {}})}})
    run = setup_github(scratch_repo, env, "--board")
    assert run.returncode == 0, run.stderr
    assert json.loads(config.read_text())["project"] == {"number": 5, "owner": "acme"}
    mutations = [json.loads(call["stdin"])["variables"] for call in calls() if call["stdin"]]
    assert [option["name"] for option in mutations[0]["o"]] == [
        "LowPriority", "Not started", "In Progress", "Review", "Done"]
    assert mutations[1] == {"p": "PROJ", "n": "Roadmap end"}
    assert mutations[2]["o"] == [{"name": "paper", "color": "BLUE", "description": "paper"}]
    assert len(mutations) == 3
    assert ["project", "link", "5", "--owner", "acme", "--repo", "acme/widget"] in [
        call["args"] for call in calls()]
