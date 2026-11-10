"""python -m tools.cloud.k8s.conductor render|check|apply [--image REF] [--context NAME] [--only NAME ...]: the
conductor's objects as one List (render), or through kubectl's server-side dry run, nothing applied (check: one line,
kubectl's own on a fault), or applied for real after that dry run passes (apply: only with --only, the objects named,
so the conductor's running StatefulSet is never rolled by accident; one line, kubectl's own on a fault).

    python -m tools.cloud.k8s.conductor apply --only score-cap-watch    # the env1 cap's watcher (plan B3), once

apply needs a login that may write CronJobs in namespace score (the owner's, from his PC): the conductor's own Role
(`score-conductor`) holds jobs, pods and secrets only, so the conductor cannot apply its own CronJobs.
"""
import argparse
import json
import subprocess
import sys

from tools.cloud.k8s import conductor


def kubectl_apply(text, chosen, dry):
    """kubectl apply of `text` (a List), server-side dry run when `dry`; the finished process."""
    return subprocess.run(["kubectl", *chosen, "apply", *(["--dry-run=server"] if dry else []), "-f", "-"],
                          input=text, text=True, capture_output=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m tools.cloud.k8s.conductor")
    parser.add_argument("action", choices=("render", "check", "apply"))
    parser.add_argument("--image", help="the conductor image; default: images.json's conductor")
    parser.add_argument("--context", help="the kubeconfig context of babon's cluster")
    parser.add_argument("--only", action="append", default=[], help="an object's name (apply needs at least one)")
    options = parser.parse_args(argv)
    found = conductor.objects(options.image or conductor.image_of())
    if options.only:
        found = conductor.picked(found, options.only)
    elif options.action == "apply":
        parser.error("apply names its objects with --only (the whole set is the cutover's)")
    text = json.dumps(conductor.as_list(found), indent=1)
    if options.action == "render":
        print(text)
        return 0
    chosen = ["--context", options.context] if options.context else []
    for dry in (True, False) if options.action == "apply" else (True,):
        done = kubectl_apply(text, chosen, dry)
        if done.returncode:
            sys.stderr.write(done.stderr)
            return done.returncode
    words = "applied" if options.action == "apply" else "pass the server-side dry run"
    print(f"conductor manifests: {len(done.stdout.splitlines())} objects {words}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
