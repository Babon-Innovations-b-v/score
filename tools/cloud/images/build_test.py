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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("build_test: ok")
