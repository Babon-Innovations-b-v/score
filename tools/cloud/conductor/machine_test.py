"""The conductor's dry check, free: no cloud call, no machine. The rendered cloud-init against `cloud-init schema`,
every unit against `systemd-analyze --user verify`, `up --dry` naming the project and zone on each scw call and
making none, boot.sh against a temp root with its commands shimmed, and the agents' door refusing a shell, a paid run
and the owner's commands while it runs the allowed ones marked as an agent's.

    .venv/bin/python tools/cloud/conductor/machine_test.py
    make tests TESTS=tools/cloud/conductor/machine_test.py
"""
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import machine  # noqa: E402
from score.store import AGENT_MARKERS  # noqa: E402

# A call that lists or creates may skip the project only when it acts inside a resource the project owns (a rule in
# its own group, a function in its own namespace) or is the global project lookup itself.
INSIDE_OWNED = ("instance security-group create-rule", "function function create", "function deploy",
                "account project list")


def executable(path, text):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def owner_keys(folder):
    """A throwaway key pair standing in for the owner's (dry runs never read the private half)."""
    private = pathlib.Path(folder) / "owner"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "owner", "-f", str(private)], check=True)
    return private


def test_cloud_init_passes_schema():
    problem = machine.check_cloud_init()
    assert problem is None, problem


def test_cloud_init_holds_the_agents_key_to_the_door():
    text = machine.render_cloud_init("ssh-ed25519 AAAA owner", "ssh-ed25519 BBBB agent", "vol-1", "c" * 40)
    door_line = next(line for line in text.splitlines() if "BBBB" in line)
    for option in ('command=\\"/usr/local/bin/score-agent-door\\"', "no-pty", "no-port-forwarding",
                   "no-agent-forwarding"):
        assert option in door_line, (option, door_line)
    owner_line = next(line for line in text.splitlines() if "AAAA" in line)
    assert "command=" not in owner_line
    assert "scsi-0SCW_sbs_volume-vol-1" in text and "c" * 40 in text
    assert re.search(r"@[A-Z_]+@", text) is None, "a slot left unfilled"


def test_units_pass_systemd_verify():
    with tempfile.TemporaryDirectory() as folder:
        problem = machine.check_units(machine.fake_home(folder))
    assert problem is None, problem


def test_the_sync_unit_install_sync_renders_for_user_score_passes_verify_and_updates_first():
    """`install-sync --no-pull` on the conductor: the sync pass runs the update first, on the system python."""
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "score.dashboard.site.settings")  # the sync's modules read them
    django.setup()
    from score.dashboard.sync import timer
    with tempfile.TemporaryDirectory() as folder:
        home = machine.fake_home(folder)
        repo, env = home / "projects" / "score", home / "dashboard.env"
        env.write_text("SCORE_SYNC_URL=https://cockpit.test\n")
        copies = []
        for name in ("score-sync.service", "score-sync.timer"):
            copy = pathlib.Path(folder) / name
            copy.write_text(timer.unit_text(name, repo, env, timer.SECRET, pull=False))
            copies.append(str(copy))
        service = pathlib.Path(copies[0]).read_text()
        done = subprocess.run(["systemd-analyze", "--user", "verify", *copies], capture_output=True, text=True)
    assert done.returncode == 0 and not (done.stderr + done.stdout).strip(), done.stderr + done.stdout
    assert f"\nExecStartPre=/usr/bin/python3 -I {repo}/tools/cloud/conductor/update.py --repo {repo}\n" in service
    assert "git -C" not in service


def test_units_never_name_a_pc_path():
    for unit in machine.unit_files():
        text = unit.read_text()
        assert "/home/dupe" not in text and "wsl" not in text.lower(), unit.name


def dry_up(folder, say):
    """up --dry with throwaway keys and no env file; every scw call recorded, none made."""
    private = owner_keys(folder)
    options = types.SimpleNamespace(owner_key=str(private), agent_key=f"{private}.pub",
                                    env_file=str(pathlib.Path(folder) / "none.env"))
    scw = machine.Scw(dry=True, say=say)
    real_run = subprocess.run

    def no_scw(arguments, *args, **kwargs):
        assert arguments[0] != "scw", f"a dry run called scw: {arguments}"
        return real_run(arguments, *args, **kwargs)

    machine.subprocess.run = no_scw
    try:
        machine.up(options, scw, say)
    finally:
        machine.subprocess.run = real_run
    return scw.calls


def test_up_dry_names_project_and_zone_and_calls_nothing():
    printed = []
    with tempfile.TemporaryDirectory() as folder:
        calls = dry_up(folder, printed.append)
    assert calls and all(f"scw {call}" in printed for call in calls)
    for call in calls:
        assert "farm-factory-batch" not in call, call
        if not call.startswith("account project list"):
            assert any(f" {key}=" in f" {call}" for key in ("zone", "region")), f"no zone or region: {call}"
        if (" list " in f" {call} " or " create " in f" {call} ") and not call.startswith(INSIDE_OWNED):
            assert "project-id=" in call, f"no project: {call}"
    created = [call for call in calls if " create " in f" {call} "]
    server = next(call for call in created if call.startswith("instance server create"))
    for part in ("type=POP2-HM-2C-16G", "zone=fr-par-2", "tags.0=score-conductor", "root-volume=sbs:20GB:5000",
                 "project-id=<id of project score-conductor>"):
        assert part in server, part
    assert any("perf-iops=5000 from-empty.size=100GB" in call for call in created)
    assert any("inbound-default-policy=drop" in call for call in created)
    assert any("dest-port-from=22 dest-port-to=22" in call for call in calls)
    assert any(call.startswith("function deploy") for call in calls)
    assert all("<secret>" in call for call in calls if ".value=" in call)


def test_up_refuses_in_an_agents_process():
    for marker in AGENT_MARKERS:
        assert machine.agent_refusal({marker: "1"}), marker
    assert machine.agent_refusal({}) is None


def test_an_agents_up_and_move_run_only_under_the_owners_open_yes():
    yes = {"id": "y-1", "answer": "yes", "question": "Switch the conductor on?"}
    marked = {AGENT_MARKERS[0]: "1"}
    refused, found = machine.step_refusal("up", marked, open_yes=lambda step: None)
    assert "none open for up" in refused and found is None
    assert machine.step_refusal("up", marked, open_yes=lambda step: yes) == (None, yes)
    assert machine.step_refusal("move", {}, open_yes=lambda step: yes) == (None, None), "the owner needs no yes"
    (_, environment), _ = machine.move_steps("scw", yes)
    assert environment["SCORE_CONDUCTOR_YES"] == "y-1", "the migrate steps check the same yes"


def test_the_conductors_key_comes_from_its_own_project_or_is_typed():
    stored = machine.credential_text("org-1", {"access_key": "SCWAAA", "secret_key": "s-1"})
    assert "access_key: SCWAAA\nsecret_key: s-1\ndefault_organization_id: org-1\n" in stored
    typed = iter(["SCWBBB", "s-2"])
    assert "access_key: SCWBBB" in machine.credential_text("org-1", None, ask=lambda prompt: next(typed))
    printed = []
    scw = machine.Scw(dry=True, say=printed.append)
    machine.stored_key(scw)
    assert any("secret secret list name=score-conductor-key 'project-id=<id of project score-conductor>'" in line
               for line in printed), printed


def test_status_reads_the_health_record_with_the_conductors_own_key():
    """The PC's own key belongs to another project, so the bucket refuses it (HTTP 403, 2026-10-24)."""
    kept = machine.stored_key
    machine.stored_key = lambda scw: {"access_key": "SCWCON", "secret_key": "s-con"}
    try:
        read = []
        record = machine.health_record(types.SimpleNamespace(dry=False),
                                       read=lambda *args: read.append(args) or b'{"active_runs": 0}')
    finally:
        machine.stored_key = kept
    assert record == {"active_runs": 0} and read[0][-2:] == ("SCWCON", "s-con"), read


def test_the_move_sets_the_pcs_home_aside_read_only_after_its_test_home_is_filled():
    with tempfile.TemporaryDirectory() as folder:
        home = pathlib.Path(folder) / "props"
        (home / "store").mkdir(parents=True)
        kept = machine.PROPS_HOME, machine.PC_FINAL_HOME
        machine.PROPS_HOME, machine.PC_FINAL_HOME = home, pathlib.Path(folder) / "props.pc-final"
        ran, marked = [], []
        kept_mark = machine.conductor_yes.mark_done
        machine.conductor_yes.mark_done = lambda yes, step, store=None: marked.append((step, store.objects.root))
        try:
            machine.retire_pc_home({"id": "y-1"}, "scw", run=lambda command, **kwargs: ran.append(
                (command, kwargs.get("env", {}))) or types.SimpleNamespace(returncode=0))
        finally:
            machine.PROPS_HOME, machine.PC_FINAL_HOME = kept
            machine.conductor_yes.mark_done = kept_mark
        final = pathlib.Path(folder) / "props.pc-final"
        assert final.is_dir() and home.is_dir() and not any(home.iterdir())
        assert ran[0][0][-1] == "--pc-test-home" and ran[0][1]["SCORE_CONDUCTOR_YES_HOME"] == str(final)
        assert ran[1][1]["UV_PROJECT_ENVIRONMENT"] == str(home / "env")
        assert marked == [("move", final / "store" / "objects")]
        assert ran[-1][0] == ["chmod", "-R", "a-w", str(final)], "read-only last, after the yes is marked"


PREPARE_SECRETS = ("score-conductor-key", "score-conductor-size-key", "score-conductor-size-token",
                   "score-backup-restic-password", "score-cockpit-sync-token", "score-lib-deploy-key")
# An scw that holds everything prepare.sh makes: every list answers the one item asked for, a secret with a version.
HOLDING_SCW = """#!/bin/sh
echo "$*" >> "{log}"
name=$(for argument in "$@"; do case "$argument" in name=*|policy-name=*) echo "${{argument#*=}}";; esac; done)
case "$1 $2" in
  "config get") echo org-1 ;;
  "account project"|"iam application"|"iam policy") echo "[{{\\"name\\": \\"$name\\", \\"id\\": \\"id-$name\\"}}]" ;;
  "secret secret") echo "[{{\\"name\\": \\"$name\\", \\"id\\": \\"s-$name\\", \\"version_count\\": 1}}]" ;;
esac
"""


def prepare(folder, *arguments, scw_text=None):
    """prepare.sh run with an scw shim (logging every call to folder/scw.log) and an owner's yes in the folder's
    store (an agent's process needs one); the finished process."""
    folder = pathlib.Path(folder)
    machine.conductor_yes.record("yes", "Switch the conductor on?", machine.Store.in_folder(folder / "store"))
    env = {**os.environ, "SCORE_CONDUCTOR_YES_HOME": str(folder), "SCORE_GH": "/bin/false",
           "SCORE_PC_SECRET_READER": "/bin/false"}
    if scw_text:
        env["SCORE_SCW"] = str(executable(folder / "scw", scw_text.format(log=folder / "scw.log")))
    return subprocess.run(["bash", str(HERE / "prepare.sh"), *arguments], env=env, capture_output=True, text=True,
                          timeout=60)


def test_prepare_dry_prints_every_call_and_makes_none():
    with tempfile.TemporaryDirectory() as folder:
        done = prepare(folder, "--dry")
        assert done.returncode == 0, done.stderr
        assert not (pathlib.Path(folder) / "scw.log").exists()
    calls = done.stderr
    assert "scw account project create name=score-conductor" in calls
    for secret in PREPARE_SECRETS:
        assert f"scw secret secret create name={secret} " in calls, secret
    assert "name=score-conductor-key project-id=<new>" in calls, "the conductor's key lives in its own project"
    assert "name=score-conductor-size-key project-id=<id of farm-factory>" in calls
    assert "rules.0.project-ids.0=<new> rules.0.permission-set-names.0=InstancesFullAccess" in calls
    assert "repo deploy-key add <its .pub> -R Babon-Innovations-b-v/score_lib -w" in calls and "openssl rand -base64 32" in calls
    assert "data=@<a file in /dev/shm>" in calls and "<value>" not in calls


def test_prepare_again_keeps_what_exists_and_makes_nothing():
    with tempfile.TemporaryDirectory() as folder:
        done = prepare(folder, scw_text=HOLDING_SCW)
        assert done.returncode == 0, done.stderr
        calls = (pathlib.Path(folder) / "scw.log").read_text().splitlines()
    assert calls and not [call for call in calls if " create" in call], calls
    for secret in PREPARE_SECRETS:
        assert f"have the secret {secret}" in done.stderr, secret
    assert "have the policy score-conductor (kept as it is)" in done.stderr


def test_env_file_carries_no_secret_and_names_the_backup_repository():
    with tempfile.TemporaryDirectory() as folder:
        owner_env = pathlib.Path(folder) / "dashboard.env"
        owner_env.write_text("SCORE_OWNER=owner\nSCORE_SYNC_URL=https://cockpit.example\nSCORE_SYNC_TOKEN=secret\n"
                             "SCORE_SECRET_READER=/home/someone/.local/bin/reader\n")
        text = machine.env_text(owner_env)
    values = dict(line.split("=", 1) for line in text.splitlines())
    assert "SCORE_SYNC_TOKEN" not in values and "secret" not in text.replace("secret-reader", "")
    assert values["SCORE_SECRET_READER"] == "/usr/local/bin/score-secret-reader"
    assert values["SCORE_BACKUP_REPO"] == "s3:https://s3.nl-ams.scw.cloud/score-conductor-backup/restic"
    assert values["SCORE_OWNER"] == "owner" and values["CLOUDSDK_CONFIG"] == "/run/user/1100/score/gcloud"


def test_move_dry_backs_this_pc_up_then_restores_before_the_sync_is_installed():
    printed = []
    options = types.SimpleNamespace(owner_key="~/.ssh/id_ed25519")
    scw = machine.Scw(dry=True, say=printed.append)
    machine.move(options, scw, printed.append)
    (local, environment), remote = machine.move_steps("/home/someone/.local/bin/scw")
    assert local[-3:] == ["score.store.backup", "migrate", "--from-pc"]
    assert environment["SCORE_BACKUP_REPO"] == machine.BACKUP_REPO
    # the PC reads the backup's password where the conductor does: the conductor's reader, its secrets project
    assert environment["SCORE_SECRET_READER"] == str(machine.HERE / "secret_reader.sh")
    assert environment["SCORE_SECRETS_PROJECT"] == machine.SECRETS_PROJECT_NAME
    assert environment["SCORE_SCW"] == "/home/someone/.local/bin/scw"
    assert remote.index("--onto-conductor") < remote.index("install-sync") and "--no-pull" in remote
    assert remote.index("--onto-conductor") < remote.index("boot.sh env") < remote.index("install-sync")
    assert printed.index(next(line for line in printed if "disable --now" in line)) < \
        printed.index(next(line for line in printed if "--from-pc" in line))
    assert any("--from-pc" in line for line in printed) and any("--onto-conductor" in line for line in printed)
    assert all(call.startswith("account project list") or call.startswith("instance server list")
               for call in scw.calls), scw.calls


def test_down_refused_unless_confirmed():
    options = types.SimpleNamespace(with_data=False)
    scw = machine.Scw(dry=True, say=lambda line: None)
    saved = {marker: os.environ.pop(marker) for marker in AGENT_MARKERS if marker in os.environ}
    try:
        try:
            machine.down(options, scw, say=lambda line: None, answer=lambda question: "no")
            raise AssertionError("down went on without its confirmation")
        except SystemExit as refused:
            assert "not confirmed" in str(refused)
        assert scw.calls == []
    finally:
        os.environ.update(saved)


# boot.sh against a temp root. Every command it runs that touches the machine is a shim writing its words to LOG.
SHIM = """#!/bin/sh
echo "$(basename "$0") $*" >> "$SHIM_LOG"
case "$(basename "$0")" in
  blkid)
    if [ "$1" = "-p" ]; then [ -f "$SHIM_STATE/formatted" ] && exit 0; exit 2; fi
    echo 1111-uuid ;;
  mkfs.ext4) touch "$SHIM_STATE/formatted" ;;
  mountpoint) exit 1 ;;
  id) echo 1100 ;;
  runuser)
    while [ "$1" != "--" ]; do shift; done
    shift
    exec "$@" ;;
  curl)
    while [ "$1" != "-o" ]; do shift; done
    echo "not the pinned file" > "$2" ;;
esac
exit 0
"""
SHIMMED = ("apt-get", "id", "useradd", "loginctl", "blkid", "mkfs.ext4", "mountpoint", "mount", "chown", "systemctl",
           "runuser", "git", "curl", "chattr", "npx")


def boot_root(folder, installed=True):
    """A temp root for boot.sh: shims on PATH, the pinned tools already there when `installed`, user score's home
    with a checkout whose tools are this repository's, and his credential."""
    root = pathlib.Path(folder) / "root"
    shims = pathlib.Path(folder) / "shims"
    for name in SHIMMED:
        executable(shims / name, SHIM)
    (root / "etc").mkdir(parents=True)
    (pathlib.Path(folder) / "state").mkdir()
    if installed:
        bin_folder = root / "usr" / "local" / "bin"
        executable(bin_folder / "restic", "#!/bin/sh\necho 'restic 0.19.1 compiled with go'\n")
        executable(bin_folder / "uv", "#!/bin/sh\n[ \"$1\" = --version ] && echo 'uv 0.12.23' && exit 0\n"
                                      "echo \"uv $*\" >> \"$SHIM_LOG\"\n")
        executable(bin_folder / "scw", "#!/bin/sh\necho 'Version          2.65.1'\n")
        (root / "opt" / "google-cloud-sdk").mkdir(parents=True)
        (root / "opt" / "google-cloud-sdk" / "VERSION").write_text("588.0.0")
    home = root / "home" / "score"
    checkout = home / "projects" / "score"
    (checkout / ".git").mkdir(parents=True)
    (checkout / "tools").symlink_to(REPO / "tools")
    (home / ".config" / "scw").mkdir(parents=True)
    (home / ".config" / "scw" / "config.yaml").write_text("access_key: test\n")
    (home / "projects" / "score_lib" / ".git").mkdir(parents=True)
    return root, shims


def run_boot(folder, root, shims):
    env = {**os.environ, "PATH": f"{shims}:{os.environ['PATH']}", "SHIM_LOG": str(pathlib.Path(folder) / "log"),
           "SHIM_STATE": str(pathlib.Path(folder) / "state"), "SCORE_BOOT_ROOT": str(root),
           "SCORE_DATA_DEVICE": "/dev/disk/by-id/scsi-0SCW_sbs_volume-test"}
    done = subprocess.run(["bash", str(HERE / "boot.sh"), "system"], env=env, capture_output=True, text=True,
                          timeout=60)
    log = pathlib.Path(env["SHIM_LOG"])
    return done, log.read_text().splitlines() if log.exists() else []


def test_boot_runs_against_a_temp_root_and_again():
    with tempfile.TemporaryDirectory() as folder:
        root, shims = boot_root(folder)
        done, calls = run_boot(folder, root, shims)
        assert done.returncode == 0, done.stderr + done.stdout
        assert "mkfs.ext4 -q -L score-data /dev/disk/by-id/scsi-0SCW_sbs_volume-test" in calls
        assert "loginctl enable-linger score" in calls
        assert not any(call.startswith("curl") for call in calls), "a pinned tool already there was downloaded again"
        fstab = (root / "etc" / "fstab").read_text()
        assert "UUID=1111-uuid /home/score/.farm-factory-props ext4" in fstab
        mountpoint = root / "home" / "score" / ".farm-factory-props"
        assert calls.index(f"chattr +i {mountpoint}") < calls.index(f"mount {mountpoint}"), \
            "the bare mountpoint is not made immutable before the data volume is mounted on it"
        for name in ("score-secret-reader", "score-agent-door"):
            assert os.access(root / "usr" / "local" / "bin" / name, os.X_OK), name
        sshd = (root / "etc" / "ssh" / "sshd_config.d" / "50-score-conductor.conf").read_text()
        assert "PasswordAuthentication no" in sshd and "PermitRootLogin no" in sshd
        assert any(call.startswith("uv sync -q --frozen") for call in calls)
        assert not any("--no-dev" in call for call in calls), "the prop environment was built before the move"
        enabled = next(call for call in calls if call.startswith("systemctl --user enable"))
        for unit in ("score-resume.service", "score-secrets.timer", "score-update.timer", "score-health.timer"):
            assert unit in enabled, unit
        units = root / "home" / "score" / ".config" / "systemd" / "user"
        for unit in machine.unit_files():
            installed = (units / unit.name).read_text()
            assert installed == machine.rendered_unit(unit), unit.name
            assert not any(slot in installed for slot in machine.UNIT_SLOTS), unit.name
        # resume and health write into the home, so on the conductor they wait for the move's machine.json
        waits = "ConditionPathExists=%h/.farm-factory-props/machine.json"
        assert waits in (units / "score-resume.service.d" / "conductor.conf").read_text().splitlines()
        assert waits in (units / "score-health.service").read_text().splitlines()
        assert "npx -y -p playwright@1.62.1 playwright install-deps chromium" in calls  # the film preview's recorder
        assert "npx -y -p playwright@1.62.1 playwright install chromium" in calls
        assert "systemctl --user start score-secrets.service" in calls
        assert any(call.startswith("git -C") and "core.sshCommand" in call for call in calls)

        # after the move (machine.json), every boot syncs the prop environment the rows' PROPS_PYTHON runs in
        (root / "home" / "score" / ".farm-factory-props" / "machine.json").write_text("{}")
        again, calls_again = run_boot(folder, root, shims)
        assert again.returncode == 0, again.stderr
        assert f"uv sync -q --frozen --no-dev --project {root}/home/score/projects/score" in calls_again
        assert calls_again.count("mkfs.ext4 -q -L score-data /dev/disk/by-id/scsi-0SCW_sbs_volume-test") == 1
        assert (root / "etc" / "fstab").read_text().count("UUID=1111-uuid") == 1


def test_boot_stops_on_a_download_that_misses_its_pin():
    with tempfile.TemporaryDirectory() as folder:
        root, shims = boot_root(folder, installed=False)
        done, calls = run_boot(folder, root, shims)
        assert done.returncode != 0
        assert "does not match its pinned SHA-256" in done.stderr
        assert not (root / "usr" / "local" / "bin" / "restic").exists()
        assert not any(call.startswith("runuser") for call in calls)


# The agents' door, end to end through agent_door.sh: a copy of the door in a fake checkout whose interpreter runs
# the door itself and records whatever the door hands on, instead of running score.
RECORDER = """#!/bin/sh
if [ "$1" = "-I" ]; then exec "{python}" "$@"; fi
printf '%s\\n' "$@" > "$DOOR_RECORD/argv"
env > "$DOOR_RECORD/env"
"""


def door_checkout(folder):
    checkout = pathlib.Path(folder) / "checkout"
    (checkout / "tools" / "cloud" / "conductor").mkdir(parents=True)
    shutil.copy(HERE / "agent_door.py", checkout / "tools" / "cloud" / "conductor" / "agent_door.py")
    (checkout / "score").symlink_to(REPO / "score")
    executable(checkout / ".venv" / "bin" / "python", RECORDER.format(python=sys.executable))
    return checkout


def through_door(folder, asked, env_file_text=""):
    """(exit code, stderr, recorded argv or None, recorded environment) of one asked command."""
    record = pathlib.Path(folder) / "record"
    shutil.rmtree(record, ignore_errors=True)
    record.mkdir()
    env_file = pathlib.Path(folder) / "dashboard.env"
    env_file.write_text(env_file_text)
    env = {name: value for name, value in os.environ.items() if name not in AGENT_MARKERS}
    env.update({"SCORE_DOOR_REPO": str(pathlib.Path(folder) / "checkout"), "SCORE_DOOR_ENV": str(env_file),
                "DOOR_RECORD": str(record), "SSH_ORIGINAL_COMMAND": asked, "SCORE_BENCHMARK_GRANT": "smuggled"})
    done = subprocess.run(["sh", str(HERE / "agent_door.sh")], env=env, capture_output=True, text=True, timeout=60)
    argv = (record / "argv").read_text().splitlines() if (record / "argv").exists() else None
    recorded = dict(line.split("=", 1) for line in (record / "env").read_text().splitlines() if "=" in line) \
        if (record / "env").exists() else {}
    return done.returncode, done.stderr, argv, recorded


def test_door_refuses_a_shell_a_paid_run_and_the_owners_commands():
    with tempfile.TemporaryDirectory() as folder:
        door_checkout(folder)
        for asked in ("", "bash", "sh -c id", "bash -i", "status; bash", "python -m score.review accept x",
                      "spend --google-month 12", "spend --read-back", "run world1", "resume",
                      "benchmark world1 --detach", "benchmark 'g 1' world1 --detach", "scw instance server list",
                      "cat /home/score/.config/scw/config.yaml", "health --write", "gaps", "gaps a b",
                      "gaps ../x", "gaps 'closeup@hub;id'"):
            code, why, argv, _ = through_door(folder, asked)
            assert code == 126 and argv is None, (asked, code, why)
            assert "refused" in why, asked
        code, why, argv, _ = through_door(folder, "benchmark g1 world1 --detach", "SCORE_FREE_ONLY=1\n")
        assert code == 126 and argv is None and "latch" in why


def test_door_runs_the_allowed_commands_marked_as_an_agents():
    with tempfile.TemporaryDirectory() as folder:
        door_checkout(folder)
        code, why, argv, env = through_door(folder, "run world1 --place hangar --detach")
        assert code == 0, why
        assert argv == ["-m", "score", "run", "world1", "--place", "hangar", "--detach"]
        assert env["SCORE_FREE_ONLY"] == "1" and "SCORE_BENCHMARK_GRANT" not in env
        assert all(env.get(marker) == "1" for marker in AGENT_MARKERS)
        code, why, argv, env = through_door(folder, "status world1 $(id)")
        assert code == 0 and argv == ["-m", "score", "status", "world1", "$(id)"], (why, argv)
        code, why, argv, env = through_door(folder, "benchmark g-1 world1 --stage x --detach")
        assert code == 0 and argv == ["-m", "score", "run", "world1", "--stage", "x", "--detach"], (why, argv)
        assert env["SCORE_BENCHMARK_GRANT"] == "g-1" and "SCORE_FREE_ONLY" not in env
        assert all(env.get(marker) == "1" for marker in AGENT_MARKERS)
        code, why, argv, _ = through_door(folder, "grant-benchmark 12 'yes, go' 'may I spend EUR 12 on x?'")
        assert code == 0 and argv[0] == "-c" and argv[2:] == ["12", "yes, go", "may I spend EUR 12 on x?"], argv
        code, why, argv, _ = through_door(folder, "resume --dry")
        assert code == 0 and argv == ["-m", "score", "resume", "--dry"]
        code, why, argv, _ = through_door(folder, "logs --lines 5")
        assert code == 0 and argv == ["-m", "score.conductor", "logs", "--lines", "5"], (why, argv)
        code, why, argv, _ = through_door(folder, "health")
        assert code == 0 and argv == ["-m", "score.conductor", "health"], (why, argv)
        code, why, argv, _ = through_door(folder, "gaps closeup@hub")
        assert code == 0 and argv[0] == "-c" and argv[2:] == ["closeup@hub"], (why, argv)


def test_the_move_switches_off_the_pcs_store_units_it_has():
    calls = []

    def systemctl(*args):
        calls.append(args)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    switched = machine.pc_units_off(present=["score-sync.timer", "score-listen.service"], systemctl=systemctl)
    assert switched == ["score-sync.timer", "score-listen.service"]
    assert calls == [("disable", "--now", "score-sync.timer", "score-listen.service")]
    assert machine.pc_units_off(present=[], systemctl=systemctl) == [] and len(calls) == 1

    def refusing(*args):
        return types.SimpleNamespace(returncode=1, stdout="", stderr="Access denied")
    try:
        machine.pc_units_off(present=["score-resume.service"], systemctl=refusing)
        raise AssertionError("a failed disable was not said")
    except SystemExit as failed:
        assert "Access denied" in str(failed)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")
