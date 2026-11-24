"""The picture judge on pictures named by hand (#184): its calibration on NVIDIA's own renders, and a round's looks
judged against a previous round's pictures that no run keeps as a look (the rounds before #182).

    .venv/bin/python -m tools.props.bench.judge <cases.json> <out.json>

cases.json: [{"name", "words", "made", "given", "previous" (optional)}], picture paths. Each case is judged side by
side (claude_code.PARALLEL at once); out.json holds each case's group "picture" and its judgement at measures.BARS.
One summary line: the cases, how many pass, out.json.
"""
import concurrent.futures
import json
import pathlib
import sys

from tools.props.bench import judge, measures


def judged_case(case):
    """One case's picture group and its rows at the bars."""
    found = judge.looked(case["words"], case["made"], case["given"], case.get("previous"))
    return {**case, "picture": found, "judged": measures.judged({"picture": found})}


def main():
    cases_path, out_path = sys.argv[1:3]
    cases = json.loads(pathlib.Path(cases_path).read_text())
    from score.adapters.models import claude_code
    with concurrent.futures.ThreadPoolExecutor(claude_code.PARALLEL) as pool:
        done = list(pool.map(judged_case, cases))
    pathlib.Path(out_path).write_text(json.dumps(done, indent=1))
    print(json.dumps({"cases": len(done), "pass": sum(case["judged"]["pass"] for case in done), "out": out_path}))


if __name__ == "__main__":
    main()
