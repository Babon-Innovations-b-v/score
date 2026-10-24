"""The release and the timer's install, on repositories made in the test (never a real host): a release pins the
host's Dockerfile to a pushed score commit in one commit of the host's style (subject, the score commits since the
old pin, the trailers) pushed to the host's main from a worktree of its own, and refuses a commit not pushed or a
checkout with changes; the install refuses an env file without its URL or reader and a cockpit that runs another
dashboard, and otherwise writes both units with every slot filled and enables the timer."""
import io
import json
import subprocess

import pytest

from score.dashboard.sync import release, timer

DOCKERFILE = "apps/cockpit/Dockerfile"
SUBJECT = "dashboards: the cockpit at score {short} (#1)"
TRAILER = "Co-Authored-By: a tester <t@example.org>"


def run(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def committed(clone, path, text, words):
    """Write a file in a clone, commit it; the commit's sha."""
    (clone / path).parent.mkdir(parents=True, exist_ok=True)
    (clone / path).write_text(text)
    run(clone, "git", "add", path)
    run(clone, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", words)
    return run(clone, "git", "rev-parse", "HEAD")


def a_repository(root, name):
    """A clone of a bare origin of its own (main): the clone."""
    origin, clone = root / f"{name}.git", root / name
    run(root, "git", "init", "-q", "--bare", "-b", "main", str(origin))
    run(root, "git", "clone", "-q", str(origin), str(clone))
    run(clone, "git", "config", "user.name", "t")
    run(clone, "git", "config", "user.email", "t@t")
    return clone


@pytest.fixture
def repositories(tmp_path):
    """(score, host, first): a score checkout with two pushed commits, the host pinning the first of them."""
    score = a_repository(tmp_path, "score")
    first = committed(score, "score/dashboard/a.py", "a = 1\n", "dashboard: the first")
    committed(score, "score/dashboard/a.py", "a = 2\n", "dashboard: the second, a subject " + "long " * 30)
    run(score, "git", "push", "-q", "origin", "HEAD:main")
    host = a_repository(tmp_path, "host")
    committed(host, DOCKERFILE, f"FROM x\nARG SCORE_COMMIT={first}\nRUN y\n", "cockpit: pinned")
    run(host, "git", "push", "-q", "origin", "HEAD:main")
    return score, host, first


def test_a_release_pins_the_pushed_head_in_one_commit_of_the_hosts_style(repositories, tmp_path):
    score, host, first = repositories
    head = run(score, "git", "rev-parse", "HEAD")
    said = release.release(score, host, DOCKERFILE, SUBJECT, trailers=[TRAILER])
    assert f"moved from score {first[:8]} to {head[:8]}" in said, said
    run(host, "git", "fetch", "-q", "origin", "main")
    pinned = run(host, "git", "show", f"FETCH_HEAD:{DOCKERFILE}")
    assert pinned == f"FROM x\nARG SCORE_COMMIT={head}\nRUN y"
    words = run(host, "git", "log", "-1", "--format=%B", "FETCH_HEAD")
    subject, body, trailer = words.split("\n\n")
    assert subject == f"dashboards: the cockpit at score {head[:8]} (#1)" and trailer == TRAILER
    assert body == f"{head[:8]} " + ("dashboard: the second, a subject " + "long " * 30)[:release.SUBJECT_WIDTH]
    assert run(host, "git", "worktree", "list").count("\n") == 0  # its own worktree is gone
    assert "already pins" in release.release(score, host, DOCKERFILE, SUBJECT)


def test_a_release_refuses_a_commit_not_pushed_or_a_checkout_with_changes(repositories):
    score, host, _ = repositories
    (score / "score/dashboard/a.py").write_text("a = 3\n")
    with pytest.raises(release.Refused, match="has changes not committed"):
        release.release(score, host, DOCKERFILE, SUBJECT)
    local = committed(score, "score/dashboard/a.py", "a = 3\n", "dashboard: not pushed")
    for commit in (None, local):
        with pytest.raises(release.Refused, match="is not on origin's main: push it first"):
            release.release(score, host, DOCKERFILE, SUBJECT, commit)
    assert "ARG SCORE_COMMIT=" in (host / DOCKERFILE).read_text()


def test_a_release_refuses_a_dockerfile_path_outside_the_host_and_keeps_other_braces(repositories):
    score, host, _ = repositories
    for path in (str(host / DOCKERFILE), "../host/" + DOCKERFILE):
        with pytest.raises(release.Refused, match="inside the host's repository"):
            release.release(score, host, path, SUBJECT)
    release.release(score, host, DOCKERFILE, "cockpit {short} {not a slot}")
    run(host, "git", "fetch", "-q", "origin", "main")
    assert run(host, "git", "log", "-1", "--format=%s", "FETCH_HEAD").endswith(" {not a slot}")


def test_a_dockerfile_must_pin_exactly_one_commit():
    for text in ("FROM x\n", "ARG SCORE_COMMIT=" + "a" * 40 + "\nARG SCORE_COMMIT=" + "b" * 40 + "\n"):
        with pytest.raises(release.Refused, match="expected one"):
            release.pinned(text)
    assert release.repinned("ARG SCORE_COMMIT=" + "a" * 40 + "\n", "c" * 40) == "ARG SCORE_COMMIT=" + "c" * 40 + "\n"


def an_env_file(tmp_path, reader=True):
    path = tmp_path / "sync.env"
    script = tmp_path / "read-secret"
    script.write_text("#!/bin/sh\necho token\n")
    script.chmod(0o755)
    path.write_text("SCORE_SYNC_URL=https://cockpit.test\n" + (f"SCORE_SECRET_READER={script}\n" if reader else ""))
    return path


def test_the_install_refuses_an_env_file_without_its_url_or_reader_and_a_cockpit_on_another_dashboard(
        repositories, tmp_path, monkeypatch):
    score, host, _ = repositories
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    assert timer.env_refusal(tmp_path / "none.env") == f"no env file at {tmp_path / 'none.env'}"
    assert "SCORE_SECRET_READER" in timer.env_refusal(an_env_file(tmp_path, reader=False))
    with pytest.raises(release.Refused, match="whose dashboard is not this checkout's: release this commit first"):
        timer.install(score, an_env_file(tmp_path), host, DOCKERFILE, systemctl=lambda *args: None)
    assert not (tmp_path / "config").exists()  # nothing written


def test_the_install_writes_both_units_filled_and_enables_the_timer(repositories, tmp_path, monkeypatch):
    score, host, _ = repositories
    release.release(score, host, DOCKERFILE, SUBJECT)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    called = []
    timer.install(score, an_env_file(tmp_path), host, DOCKERFILE, systemctl=lambda *args: called.append(args))
    assert called == [("daemon-reload",), ("enable", "--now", "score-sync.timer", "score-listen.service"),
                      ("restart", "score-listen.service")]
    listener = (tmp_path / "config/systemd/user/score-listen.service").read_text()
    assert "<" not in "".join(line for line in listener.splitlines() if not line.startswith("#"))
    service = (tmp_path / "config/systemd/user/score-sync.service").read_text()
    lines = [line for line in service.splitlines() if not line.startswith("#")]
    assert not any("<" in line for line in lines), lines  # every slot filled
    assert f"EnvironmentFile={tmp_path / 'sync.env'}" in lines and f"WorkingDirectory={score}" in lines
    start = next(line for line in lines if line.startswith("ExecStart="))
    assert '"$$SCORE_SECRET_READER" "score-cockpit-sync-token"' in start


def test_a_quoted_reader_is_read_as_systemd_reads_it_and_a_failed_user_manager_is_said(repositories, tmp_path,
                                                                                         monkeypatch):
    score, host, _ = repositories
    release.release(score, host, DOCKERFILE, SUBJECT)
    env = an_env_file(tmp_path)
    env.write_text(env.read_text().replace("SCORE_SECRET_READER=", 'SCORE_SECRET_READER="').replace(
        "read-secret\n", 'read-secret"\n'))
    assert timer.env_refusal(env) is None
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    with pytest.raises(release.Refused, match="systemctl --user daemon-reload failed: no user manager"):
        timer.install(score, env, host, DOCKERFILE, systemctl=lambda *args: "no user manager")


def test_the_units_render_for_the_conductors_user_and_no_pull_runs_the_update_in_the_pulls_place():
    """On the conductor the same templates fill in for user score; --no-pull puts the conductor's update in place of
    the sync unit's pull before each pass (so every pass starts on the cockpit's pin) and changes nothing else."""
    repo, env = "/home/score/projects/score", "/home/score/.config/score/dashboard.env"
    pulled = timer.unit_text("score-sync.service", repo, env, timer.SECRET).splitlines()
    unpulled = timer.unit_text("score-sync.service", repo, env, timer.SECRET, pull=False).splitlines()
    pull = f"ExecStartPre=/usr/bin/git -C {repo} pull -q --ff-only"
    update = f"ExecStartPre=/usr/bin/python3 -I {repo}/tools/cloud/conductor/update.py --repo {repo}"
    assert pull in pulled and update not in pulled
    assert [update if line == pull else line for line in pulled] == unpulled
    lines = [line for line in unpulled if not line.startswith("#")]
    assert not any("<" in line for line in lines) and not any("/home/dupe" in line for line in unpulled)
    assert f"WorkingDirectory={repo}" in lines and f"EnvironmentFile={env}" in lines
    assert any(line.startswith("ExecStart=") and f'"{repo}/.venv/bin/python" -m score.dashboard sync' in line
               for line in lines)
    listener = timer.unit_text("score-listen.service", repo, env, timer.SECRET, pull=False)
    assert f"WorkingDirectory={repo}" in listener and "WSL" not in listener


class Pin:
    """A urlopen stand-in for the cockpit's /api/sync/pin; what it was asked, with the token it was given."""

    def __init__(self, commit):
        self.body = json.dumps({"commit": commit}).encode()
        self.asked = []

    def __call__(self, request, timeout):
        self.asked.append((request.full_url, request.get_header("Authorization")))
        return io.BytesIO(self.body)


def test_without_a_host_the_install_checks_the_commit_the_cockpits_pin_reports(repositories, tmp_path, monkeypatch):
    """Not /healthz: the hosting proxy answers that with a body of its own, so it never names the commit."""
    score, _, first = repositories
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    for commit, why in ((None, "reports no commit"), (first, "whose dashboard is not this checkout's")):
        with pytest.raises(release.Refused, match=why):
            timer.install(score, an_env_file(tmp_path), systemctl=lambda *args: None, opener=Pin(commit))
    assert not (tmp_path / "config").exists()  # nothing written
    cockpit = Pin(run(score, "git", "rev-parse", "HEAD"))
    said = timer.install(score, an_env_file(tmp_path), systemctl=lambda *args: None, pull=False, opener=cockpit)
    assert cockpit.asked == [("https://cockpit.test/api/sync/pin", "Bearer token")]
    assert "no pull before a pass" in said
    service = (tmp_path / "config/systemd/user/score-sync.service").read_text()
    assert "\nExecStartPre=/usr/bin/git" not in service and f"WorkingDirectory={score}" in service
    assert f"\nExecStartPre=/usr/bin/python3 -I {score}/tools/cloud/conductor/update.py --repo {score}\n" in service
