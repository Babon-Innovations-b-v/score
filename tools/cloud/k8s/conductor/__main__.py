"""python -m tools.cloud.k8s.conductor render|check [--image REF] [--context NAME]: the conductor's objects as one
List (render), or through kubectl's server-side dry run, nothing applied (check: one line, kubectl's own on a fault)."""
import argparse
import json
import subprocess
import sys

from tools.cloud.k8s import conductor


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m tools.cloud.k8s.conductor")
    parser.add_argument("action", choices=("render", "check"))
    parser.add_argument("--image", help="the conductor image; default: images.json's conductor")
    parser.add_argument("--context", help="the kubeconfig context of babon's cluster")
    options = parser.parse_args(argv)
    text = json.dumps(conductor.as_list(conductor.objects(options.image or conductor.image_of())), indent=1)
    if options.action == "render":
        print(text)
        return 0
    chosen = ["--context", options.context] if options.context else []
    done = subprocess.run(["kubectl", *chosen, "apply", "--dry-run=server", "-f", "-"], input=text, text=True,
                          capture_output=True)
    if done.returncode:
        sys.stderr.write(done.stderr)
        return done.returncode
    print(f"conductor manifests: {len(done.stdout.splitlines())} objects pass the server-side dry run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
