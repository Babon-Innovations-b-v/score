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
           "runuser", "git", "curl", "chattr")


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
        enabled = next(call for call in calls if call.startswith("systemctl --user enable"))
        for unit in ("score-resume.service", "score-secrets.timer", "score-update.timer", "score-health.timer"):
            assert unit in enabled, unit
        units = root / "home" / "score" / ".config" / "systemd" / "user"
        for unit in machine.unit_files():
            installed = (units / unit.name).read_text()
            assert installed == machine.rendered_unit(unit), unit.name
            assert not any(slot in installed for slot in machine.UNIT_SLOTS), unit.name
        assert "systemctl --user start score-secrets.service" in calls
        assert any(call.startswith("git -C") and "core.sshCommand" in call for call in calls)

        again, calls_again = run_boot(folder, root, shims)
        assert again.returncode == 0, again.stderr
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
                      "cat /home/score/.config/scw/config.yaml"):
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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok {name}")
