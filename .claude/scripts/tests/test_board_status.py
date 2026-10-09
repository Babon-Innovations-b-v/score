"""Pin board-status: it moves only this repo's card, only into a column the board has."""
import json
import subprocess

FIELDS = {"fields": [{"id": "F1", "name": "Status", "options": [
    {"id": "O1", "name": "Not started"}, {"id": "O2", "name": "Done"}]}]}


def on_board(project_number):
    return {"repository": {"issue": {"id": "I1", "projectItems": {"nodes": [
        {"id": "ITEM", "project": {"id": "P1", "number": project_number}}]}}}}


def board_status(repo, env, *args):
    return subprocess.run(["python3", repo / ".claude" / "scripts" / "board-status.py", *args],
                          env=env, capture_output=True, text=True)


def configure(repo, config):
    (repo / ".claude" / "project.json").write_text(json.dumps(config))


def test_wrong_arguments_print_the_usage(scratch_repo, fake_gh):
    env, _, _ = fake_gh
    run = board_status(scratch_repo, env, "7")
    assert run.returncode != 0
    assert "board-status.py <issue-number> <status>" in run.stderr


def test_a_config_naming_another_repo_is_refused(scratch_repo, fake_gh):
    env, _, calls = fake_gh
    configure(scratch_repo, {"repo": "template/origin", "project": {"number": 3}})
    run = board_status(scratch_repo, env, "7", "Done")
    assert run.returncode != 0
    assert "project.json names template/origin but this checkout is acme/widget" in run.stderr
    assert calls() == []


def test_a_config_without_a_board_is_refused(scratch_repo, fake_gh):
    env, _, _ = fake_gh
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 0}})
    run = board_status(scratch_repo, env, "7", "Done")
    assert run.returncode != 0
    assert "setup-github.py --board" in run.stderr


def test_an_unknown_column_lists_the_real_ones(scratch_repo, fake_gh):
    env, answer, _ = fake_gh
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}})
    answer({"project field-list": {"stdout": json.dumps(FIELDS)}})
    run = board_status(scratch_repo, env, "7", "Doing")
    assert run.returncode != 0
    assert "unknown status 'Doing'; board columns: Not started, Done" in run.stderr


def test_a_card_on_the_board_moves_to_the_column(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}})
    answer({"project field-list": {"stdout": json.dumps(FIELDS)},
            "graphql query": {"stdout": json.dumps({"data": on_board(3)})},
            "graphql mutation": {"stdout": json.dumps({"data": {}})}})
    run = board_status(scratch_repo, env, "7", "Done")
    assert run.returncode == 0, run.stderr
    assert run.stdout == "#7 -> Done\n"
    mutation = calls()[-1]["args"]
    assert {"p=P1", "i=ITEM", "f=F1", "o=O2"} <= set(mutation)
    assert not any(call["args"][:2] == ["project", "item-add"] for call in calls())


def test_a_card_on_another_board_is_added_first(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}})
    # The fake answers every query the same way, so after item-add the issue is still elsewhere.
    answer({"project field-list": {"stdout": json.dumps(FIELDS)},
            "graphql query": {"stdout": json.dumps({"data": on_board(9)})}})
    run = board_status(scratch_repo, env, "7", "Done")
    assert run.returncode != 0
    assert "#7 could not be added to board #3" in run.stderr
    added = [call["args"] for call in calls() if call["args"][:2] == ["project", "item-add"]]
    assert added == [["project", "item-add", "3", "--owner", "acme",
                      "--url", "https://github.com/acme/widget/issues/7"]]
