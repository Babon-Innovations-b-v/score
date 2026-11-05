"""kubectl against one kubeconfig, for the job path's modules: every call fails loudly, and objects go in through
stdin so a Secret's value is never on disk or in a command line."""
import json
import subprocess

import manifests


class Kubectl:
    """kubectl against one kubeconfig (and one of its contexts, when it holds several clusters); every call fails
    loudly."""

    def __init__(self, config, context=None):
        self.config, self.context = config, context

    def run(self, *arguments, stdin=None):
        chosen = ["--context", self.context] if self.context else []
        done = subprocess.run(["kubectl", "--kubeconfig", self.config, *chosen, *arguments], input=stdin, check=True,
                              capture_output=True, text=True)
        return done.stdout

    def json(self, *arguments):
        return json.loads(self.run(*arguments, "-o", "json"))

    def apply(self, objects):
        """Apply objects through stdin, so a Secret's value is never on disk or in a command line."""
        return self.run("apply", "-f", "-", stdin=json.dumps(manifests.as_list(objects)))

    def delete_job(self, name):
        self.run("delete", "job", name, "-n", manifests.NAMESPACE, "--ignore-not-found", "--wait=false",
                 "--cascade=background")
