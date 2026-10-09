"""Pin install-agent-tools.sh and bootstrap.sh against a scratch HOME and scratch repo.

The pinned binaries are already "installed" as stand-ins reporting the pinned versions, so
nothing is downloaded; `claude` and `gh` are stand-ins that log their calls.
"""
import json
import os
import subprocess

import pytest

from conftest import write_tool

LOGGING_TOOL = '#!/bin/sh\necho "$(basename "$0") $*" >> "$TOOL_LOG"\n'


@pytest.fixture
def machine(tmp_path, scratch_repo):
    """A scratch HOME with the pinned tools in place, and the env to run the scripts in."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    write_tool(home / ".local" / "bin", "codebase-memory-mcp",
               '#!/bin/sh\n[ "$1" = --version ] && { echo "codebase-memory-mcp 0.11.0"; exit; }\n'
               + LOGGING_TOOL.split("\n", 1)[1])
    write_tool(home / ".bun" / "bin", "bun", "#!/bin/sh\necho 1.4.2\n")
    # The real `claude` writes the marketplace path into the committed settings; so does this one.
    write_tool(tmp_path / "bin", "claude",
               LOGGING_TOOL + 'echo scribbled > "$PWD/.claude/settings.json"\n')
    write_tool(tmp_path / "bin", "gh", '#!/bin/sh\nexit 1\n')
    env = {key: value for key, value in os.environ.items()
           if key not in ("CLAUDE_MEM_DATA_DIR", "CLAUDE_CONFIG_DIR", "CBM_BIN_DIR")}
    env.update(HOME=str(home), PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}",
               TOOL_LOG=str(tmp_path / "tools.log"))
    return home, env


def run_script(repo, env, name):
    return subprocess.run(["bash", repo / ".claude" / "scripts" / name], env=env,
                          capture_output=True, text=True)


def test_install_writes_claude_mem_settings_and_keeps_the_rest(scratch_repo, machine, tmp_path):
    home, env = machine
    mem = home / ".claude-mem"
    mem.mkdir()
    (mem / "settings.json").write_text(json.dumps({
        "MINE": "kept",
        "CLAUDE_MEM_PROJECT_ENVIRONMENTS": json.dumps([{"name": "other", "patterns": ["/x/**"]},
                                                       {"name": "score", "patterns": ["/old/**"]}])}))
    (mem / "telemetry.json").write_text(json.dumps({"installId": "abc", "enabled": True}))

    for _ in range(2):  # safe to re-run
        run = run_script(scratch_repo, env, "install-agent-tools.sh")
        assert run.returncode == 0, run.stderr

    settings = json.loads((mem / "settings.json").read_text())
    assert settings == {
        "MINE": "kept",
        "CLAUDE_MEM_PROJECT_ENVIRONMENTS": [{"name": "other", "patterns": ["/x/**"]},
                                            {"name": "score", "patterns": [f"{scratch_repo}/**"]}],
        "CLAUDE_MEM_TELEMETRY": "0",
        "CLAUDE_MEM_TELEMETRY_ERRORS": "0",
        "CLAUDE_MEM_CHROMA_ENABLED": "false",
        "CLAUDE_MEM_FILE_READ_GATE_ENABLED": "false",
        "CLAUDE_MEM_CONTEXT_OBSERVATION_TYPES": "decision,bugfix",
        "CLAUDE_MEM_SKIP_SUBAGENT_OBSERVATIONS": "false",
    }
    telemetry = json.loads((mem / "telemetry.json").read_text())
    assert (telemetry["installId"], telemetry["enabled"]) == ("abc", False)
    assert "decidedAt" in telemetry
    assert (home / ".claude" / ".ponytail-statusline-nudged").exists()
    assert "codebase-memory-mcp: 0.11.0 already installed" in run.stdout
    assert "bun: 1.4.2 already installed" in run.stdout


def test_install_adds_the_plugin_and_puts_the_committed_settings_back(scratch_repo, machine, tmp_path):
    _, env = machine
    run = run_script(scratch_repo, env, "install-agent-tools.sh")
    assert run.returncode == 0, run.stderr
    assert (scratch_repo / ".claude" / "settings.json").read_text() == '{"committed": true}\n'
    assert (tmp_path / "tools.log").read_text().splitlines() == [
        f"claude plugin marketplace add {scratch_repo}/vendor/claude-mem --scope project",
        "claude plugin install claude-mem@thedotmack --scope project",
        f"codebase-memory-mcp cli --quiet index_repository --repo-path {scratch_repo}",
    ]


def test_bootstrap_links_memory_without_losing_any(scratch_repo, machine):
    home, env = machine
    encoded = str(scratch_repo).replace("/", "-")
    target = home / ".claude" / "projects" / encoded / "memory"
    target.mkdir(parents=True)
    (target / "note.txt").write_text("an old memory")

    run = run_script(scratch_repo, env, "bootstrap.sh")
    assert run.returncode == 0, run.stderr
    assert target.is_symlink() and target.resolve() == scratch_repo / ".claude" / "memory"
    assert (scratch_repo / ".claude" / "memory" / "note.txt").read_text() == "an old memory"
    assert len(list(target.parent.glob("memory.bak.*"))) == 1
    assert "memory: existing folder copied into the repo and saved to" in run.stdout

    again = run_script(scratch_repo, env, "bootstrap.sh")
    assert "memory: already linked" in again.stdout


def test_bootstrap_sets_the_hooks_and_reports_what_is_missing(scratch_repo, machine):
    _, env = machine
    run = run_script(scratch_repo, env, "bootstrap.sh")
    assert run.returncode == 0, run.stderr
    hooks = subprocess.run(["git", "-C", scratch_repo, "config", "core.hooksPath"],
                           capture_output=True, text=True).stdout.strip()
    assert hooks == ".githooks"
    assert "gh: installed but not logged in. Run: gh auth login" in run.stdout
    assert "project.json: acme/widget" in run.stdout
