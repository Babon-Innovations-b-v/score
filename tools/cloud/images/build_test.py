"""Checks for the image builder's offline logic, renting nothing: the tag follows the files (models.json aside) and
the parent's digest, a built image is not built again, a child is rebuilt with its parent, and the buildx command
pushes with the registry as its layer cache.

Run: .venv/bin/python tools/cloud/images/build_test.py   (make tests runs it)
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import build  # noqa: E402


def in_a_copy(check):
    """Run `check` with the builder pointed at a scratch images folder: a base and a child of it."""
    kept = build.HERE, build.RUNTIME
    root = pathlib.Path(tempfile.mkdtemp())
    for kind, text in (("base", "# platforms: linux/amd64,linux/arm64\nFROM x\n"),
                       ("child", "ARG BASE\nFROM ${BASE}\n")):
        (root / kind).mkdir()
        (root / kind / "Dockerfile").write_text(text)
        (root / kind / "models.json").write_text("[]")
    (root / "runtime").mkdir()
    (root / "runtime/job.py").write_text("print()")
    (root / "runtime/job_test.py").write_text("print()")
    build.HERE, build.RUNTIME = root, root / "runtime"
    try:
        check(root)
    finally:
        build.HERE, build.RUNTIME = kept


def test_the_parent_comes_first_and_platforms_are_read():
    def check(_root):
        assert build.image_kinds() == ["base", "child"]
        assert build.platforms("base") == "linux/amd64,linux/arm64" and build.platforms("child") == "linux/amd64"
        assert build.has_parent("child") and not build.has_parent("base")
        assert "runtime/job.py" in build.context_files("base") and "runtime/job_test.py" not in build.context_files("base")
    in_a_copy(check)


def test_the_tag_follows_the_files_but_not_the_weights_list():
    def check(root):
        first = build.tag("base", {})
        (root / "base/models.json").write_text('[{"name": "x"}]')
        assert build.tag("base", {}) == first
        (root / "runtime/job.py").write_text("print(1)")
        assert build.tag("base", {}) != first
        assert build.tag("base", {}).startswith(build.IMAGE_VERSION + "-")
    in_a_copy(check)


def test_a_child_follows_its_parents_digest():
    def check(_root):
        one = build.tag("child", {"base": {"digest": "sha256:a"}})
        assert build.tag("child", {"base": {"digest": "sha256:b"}}) != one
    in_a_copy(check)


def test_only_what_changed_is_built():
    def check(_root):
        built = {"base": {"tag": build.tag("base", {}), "digest": "sha256:a"}}
        built["child"] = {"tag": build.tag("child", built)}
        assert build.stale(["base", "child"], built, force=False) == []
        assert build.stale(["base", "child"], built, force=True) == ["base", "child"]
        assert build.stale(["child"], {}, force=False) == ["child"]
        stale_base = {**built, "base": {**built["base"], "tag": "old"}}
        assert build.stale(["base", "child"], stale_base, force=False) == ["base", "child"]
    in_a_copy(check)


def test_the_build_pushes_with_a_registry_cache():
    def check(_root):
        command = build.build_command("child", "reg/score-child:1-x", "reg/score-child:buildcache", "reg/base@sha256:a")
        assert "--push" in command and "BASE=reg/base@sha256:a" in command
        assert "type=registry,ref=reg/score-child:buildcache" in command
        assert any(part.startswith("type=registry,ref=reg/score-child:buildcache,mode=max") for part in command)
    in_a_copy(check)


def test_the_context_keeps_each_files_mode():
    def check(root):
        script = root / "child/run.sh"
        script.write_text("#!/bin/sh\n")
        script.chmod(0o755)
        first = build.tag("child", {"base": {"digest": "sha256:a"}})
        staged = build.staged_context("child", root)
        assert (staged / "run.sh").stat().st_mode & 0o777 == 0o755
        assert (staged / "runtime/job.py").read_text() == "print()"
        script.chmod(0o644)
        assert build.tag("child", {"base": {"digest": "sha256:a"}}) != first
    in_a_copy(check)


def renting(machine_class, work):
    """Stand in for the cloud: batch, the provider and spread.on_machines, one machine of `machine_class` that runs
    `work(machine, share)` on each share; what was deleted and recorded."""
    seen = {"deleted": [], "ledger": [], "said": []}
    folder = pathlib.Path(tempfile.mkdtemp())

    def on_machines(run, _account, _found, _count, _kind, shares, prepare, do, disk_gb=None):
        machine = {"folder": run.folder / "m1", "host": "h", "class": machine_class, "type": "T", "zone": "z",
                   "created": 0.0}
        machine["folder"].mkdir(parents=True)
        run.machines.append(machine)
        prepare(machine)
        while shares.waiting:
            share = shares.waiting.popleft()
            try:
                do(machine, share, None)
            except RuntimeError:
                shares.failed.append(share)

    class Offer:
        price = 0.01

    stubs = {(build.batch, "BATCHES"): folder, (build.batch, "offers"): lambda classes: [Offer()],
             (build.batch, "month_spent"): lambda account: 0.0, (build.batch, "sweep"): lambda account: None,
             (build.batch, "ssh_key"): lambda: "key", (build.batch, "stop_on_signals"): lambda: None,
             (build.batch, "remote"): lambda *arguments, **keywords: None,
             (build.batch, "delete_machine"): seen["deleted"].append, (build.batch, "say"): seen["said"].append,
             (build.ledger, "record"): seen["ledger"].append,
             (build.ledger, "machines_record"): lambda machines, attempts, started: {"euros": 0.5},
             (build.spread, "on_machines"): on_machines, (build.cloud, "account"): lambda: "account",
             (build.cloud, "registry"): lambda: {"endpoint": "reg/ns", "username": "u", "password": "p"},
             (build.cloud, "allow_key"): lambda account, name, key: None,
             (build, "build_one"): lambda machine, kind, registry, built: work(machine, kind)}
    kept = {key: getattr(*key) for key in stubs}
    for (owner, name), value in stubs.items():
        setattr(owner, name, value)
    return seen, lambda: [setattr(owner, name, value) for (owner, name), value in kept.items()]


def test_a_failed_build_still_deletes_its_machine_and_records_the_run():
    def work(_machine, kind):
        if kind == "child":
            raise RuntimeError("buildx exited with 1")

    seen, restore = renting("cpu-16c-64gb", work)
    try:
        build.build(["base", "child"], "tester", smoke_test=False)
        raise AssertionError("a failed build must stop the run")
    except SystemExit as stop:
        assert "did not finish" in str(stop)
    finally:
        restore()
    assert [machine["class"] for machine in seen["deleted"]] == ["cpu-16c-64gb"]
    entry = seen["ledger"][0]
    assert entry["kind"] == "images" and entry["who"] == "tester" and entry["images"] == ["base", "child"]
    assert entry["batch"].startswith("images-") and entry["euros"] == 0.5
    assert seen["said"][-1].startswith("images: ")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("build_test: ok")
