"""Pin the output_cap PostToolUse hook by driving the real script via stdin, as the harness does.

Covers: short outputs untouched, a long output spilled whole to a file and replaced by head, error lines and tail in
the Bash output shape, JSON outlined, whole-file cat pointed at ranged reads, narrowed reads and the full-output
marker left alone, images and background commands left alone, and fail-open on garbage or an unwritable spill folder.

Run: python3 -m pytest .claude/hooks/tests/
"""

import json
import os
import pathlib
import subprocess
import sys

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "output_cap.py"
sys.path.insert(0, str(_HOOK.parent))
import output_cap  # noqa: E402


def _run(payload, spill_dir):
    result = subprocess.run([sys.executable, str(_HOOK)], input=payload if isinstance(payload, str) else
                            json.dumps(payload), capture_output=True, text=True,
                            env=dict(os.environ, SCORE_OUTPUT_DIR=str(spill_dir)))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"] if result.stdout.strip() else None


def _bash(command, stdout, stderr="", **response):
    return {"tool_name": "Bash", "session_id": "s1", "tool_use_id": "toolu_1", "tool_input": {"command": command},
            "tool_response": {"stdout": stdout, "stderr": stderr, "interrupted": False, "isImage": False, **response}}


def _long_log():
    lines = [f"step {index}: fine, the part settled at rest on the floor" for index in range(400)]
    lines[200] = "ERROR: the bake of part 7 failed"
    lines[250] = "Traceback (most recent call last):"
    return "\n".join(lines)


def test_short_output_untouched(tmp_path):
    assert _run(_bash("ls", "a\nb\n"), tmp_path) is None


def test_long_output_spilled_whole_and_summarised(tmp_path):
    log = _long_log()
    output = _run(_bash("python3 tools/usd/settle.py hub", log, "a warning on stderr"), tmp_path)
    spill = tmp_path / "s1" / "toolu_1.txt"
    assert spill.read_text() == "$ python3 tools/usd/settle.py hub\n" + log + "\n--- stderr ---\na warning on stderr"
    assert set(output) == {"stdout", "stderr", "interrupted", "isImage"}
    assert output["stderr"] == "" and output["interrupted"] is False and output["isImage"] is False
    text = output["stdout"]
    assert str(spill) in text and "401 lines" in text
    assert "step 0: fine," in text and "a warning on stderr" in text
    assert "201: ERROR: the bake of part 7 failed" in text and "251: Traceback" in text
    assert "step 100: fine," not in text
    assert len(text) < output_cap.CAP_CHARS


def test_extra_response_fields_kept(tmp_path):
    output = _run(_bash("make tests", _long_log(), returnCodeInterpretation="exit 1"), tmp_path)
    assert output["returnCodeInterpretation"] == "exit 1"


def test_json_outlined(tmp_path):
    document = {"rows": [{"row": f"r{index}", "copies": 2} for index in range(300)], "place": "wreck"}
    text = _run(_bash("python3 -c 'print(json)'", json.dumps(document, indent=1)), tmp_path)["stdout"]
    assert "JSON object, 2 keys" in text and "rows: array, 300 items" in text and 'place: "wreck"' in text
    assert json.loads((tmp_path / "s1" / "toolu_1.txt").read_text().split("\n", 1)[1]) == document


def test_whole_file_cat_points_to_ranged_reads(tmp_path):
    text = _run(_bash("cd /x && cat tools/props/library/route.py", _long_log()), tmp_path)["stdout"]
    assert "whole-file cat of tools/props/library/route.py" in text and "offset, limit" in text


def test_narrowed_reads_left_alone(tmp_path):
    log = _long_log()
    for command in ("sed -n '1,400p' route.py", "git log -p | head -500", "grep -c x big.log",
                    "awk 'NR>=10 && NR<=400' f", "cd /x; sed -n 1,300p a.py; echo ===; tail -n 200 b.py"):
        assert _run(_bash(command, log), tmp_path) is None, command


def test_mixed_list_still_capped(tmp_path):
    assert _run(_bash("sed -n 1,20p a.py; cat big.log", _long_log()), tmp_path) is not None


def test_full_output_marker_left_alone(tmp_path):
    assert _run(_bash("SCORE_FULL_OUTPUT=1 make tests", _long_log()), tmp_path) is None


def test_images_background_and_other_tools_left_alone(tmp_path):
    log = _long_log()
    assert _run(_bash("cat a.png", log, isImage=True), tmp_path) is None
    assert _run(_bash("make tests", log, backgroundTaskId="b1"), tmp_path) is None
    assert _run({"tool_name": "Read", "tool_input": {}, "tool_response": {"stdout": log}}, tmp_path) is None


def test_fail_open(tmp_path):
    assert _run("not json", tmp_path) is None
    assert _run({"tool_name": "Bash", "tool_input": {"command": "x"}, "tool_response": "text"}, tmp_path) is None
    blocker = tmp_path / "file"
    blocker.write_text("")
    assert _run(_bash("make tests", _long_log()), blocker) is None  # spill folder is a file: output stays whole
