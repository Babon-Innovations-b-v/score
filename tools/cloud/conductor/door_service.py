"""The agents' door as a small service in the conductor's pod (#76, the plan of 2026-11-07, step 4): the same door,
reached by `kubectl port-forward` to that one pod in place of ssh. What it allows and how is agent_door.py's alone:
each request runs `agent_door.sh` exactly as sshd's forced command does, the asked command in SSH_ORIGINAL_COMMAND,
the request's body on its stdin (store-push's stream, store-pull's manifest), so the verbs, their refusals and the
agents' marker on every command are one code. The ssh door stays until the cutover.

    python3 -I door_service.py --port 8780              # the conductor pod's `door` container (k8s/conductor)
    python3 door_service.py ask "<command>" [--context C] [< stdin]   # an agent's side (`ask`, below)

The service listens on the pod's loopback only (port-forward reaches it there; nothing on the pod network can) and
answers one POST: header `X-Score-Door-Token` (the secret `score-agent-door-token`, read by name through the secret
reader at the start, compared in constant time; anything else is 403 and runs nothing), header `X-Score-Command` (the
words an agent would give ssh), the body the command's stdin. The answer: the command's stdout as the body,
`X-Score-Exit` its exit code and `X-Score-Stderr` its stderr (base64, its last STDERR_BYTES). `ask` opens the
port-forward (`kubectl port-forward pod/score-conductor-0 :8780`, the agents' role allows that and nothing else),
sends one command, writes stdout and stderr where ssh would and exits with the door's code.
"""
import argparse
import base64
import hmac
import http.server
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
DOOR = ["/bin/sh", str(HERE / "agent_door.sh")]
TOKEN_SECRET = "score-agent-door-token"
TOKEN_HEADER, COMMAND_HEADER = "X-Score-Door-Token", "X-Score-Command"
EXIT_HEADER, STDERR_HEADER = "X-Score-Exit", "X-Score-Stderr"
STDERR_BYTES = 32_000
NAMESPACE, POD, PORT = "score", "score-conductor-0", 8780
FORWARDING = re.compile(r"Forwarding from 127\.0\.0\.1:(\d+)")


class Handler(http.server.BaseHTTPRequestHandler):
    """One door request: refused without the token, else agent_door.sh run once with the asked command."""

    token, door, environment = "", DOOR, None

    def do_POST(self):
        given = self.headers.get(TOKEN_HEADER, "")
        if not self.token or not hmac.compare_digest(given.encode(), self.token.encode()):
            self.send_error(403, "the door's token is wrong")
            return
        length = int(self.headers.get("Content-Length") or 0)
        with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as stdout:
            left = length
            while left > 0:
                chunk = self.rfile.read(min(left, 1 << 20))
                if not chunk:
                    break
                stdin.write(chunk)
                left -= len(chunk)
            stdin.seek(0)
            environment = {**(os.environ if self.environment is None else self.environment),
                           "SSH_ORIGINAL_COMMAND": self.headers.get(COMMAND_HEADER, "")}
            done = subprocess.run(self.door, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, env=environment)
            stdout.seek(0, os.SEEK_END)
            size = stdout.tell()
            stdout.seek(0)
            self.send_response(200)
            self.send_header(EXIT_HEADER, str(done.returncode))
            self.send_header(STDERR_HEADER, base64.b64encode(done.stderr[-STDERR_BYTES:]).decode())
            self.send_header("Content-Length", str(size))
            self.end_headers()
            shutil.copyfileobj(stdout, self.wfile)

    def log_message(self, format, *args):  # noqa: A002  the base class's name
        print(f"door: {self.address_string()} {format % args}", file=sys.stderr, flush=True)


def serve(token, port, door=None, environment=None, host="127.0.0.1"):
    """The door's server on host:port (port 0: any free one), not yet serving; refused without a token."""
    if not token:
        raise SystemExit(f"door: no token: the secret {TOKEN_SECRET} reads empty, so the door stays shut")
    handler = type("DoorHandler", (Handler,), {"token": token, "door": door or DOOR, "environment": environment})
    return http.server.ThreadingHTTPServer((host, port), handler)


def read_token(reader=None):
    """The door's token by name through the secret reader (SCORE_SECRET_READER, else score-secret-reader)."""
    reader = reader or os.environ.get("SCORE_SECRET_READER") or "/usr/local/bin/score-secret-reader"
    return subprocess.run([reader, TOKEN_SECRET], capture_output=True, text=True, check=True).stdout.strip()


def send(url, token, command, stdin=b"", out=None):
    """(exit code, stdout bytes, stderr bytes) of one command through the door at url; with `out`, a binary file, the
    body is copied into it as it comes and the bytes are b"" (a store-pull's tar of many GB never held in memory)."""
    request = urllib.request.Request(url, data=stdin, method="POST",
                                     headers={TOKEN_HEADER: token, COMMAND_HEADER: command})
    with urllib.request.urlopen(request, timeout=3600) as answer:
        if out is None:
            body = answer.read()
        else:
            shutil.copyfileobj(answer, out, 1 << 20)
            out.flush()
            body = b""
        return (int(answer.headers[EXIT_HEADER]), body, base64.b64decode(answer.headers.get(STDERR_HEADER, "")))


def forwarded(context=None):
    """A `kubectl port-forward` to the conductor's pod and its local port, once kubectl says it forwards."""
    chosen = ["--context", context] if context else []
    forward = subprocess.Popen(["kubectl", *chosen, "-n", NAMESPACE, "port-forward", f"pod/{POD}", f":{PORT}"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in forward.stdout:
        found = FORWARDING.search(line)
        if found:
            threading.Thread(target=forward.stdout.read, daemon=True).start()  # keep its pipe drained
            return forward, int(found.group(1))
    forward.wait()
    raise SystemExit(f"door: kubectl port-forward ended: {forward.stderr.read().strip()}")


def ask(command, context=None, token=None):
    """An agent's one command through the door: stdout and stderr where ssh writes them, the door's exit code."""
    stdin = b"" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.buffer.read()
    forward, port = forwarded(context)
    try:
        code, _, err = send(f"http://127.0.0.1:{port}/", token or read_token(), command, stdin, sys.stdout.buffer)
    finally:
        forward.terminate()
        forward.wait()
    sys.stderr.buffer.write(err)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(prog="door_service.py")
    parser.add_argument("action", nargs="?", default="serve", choices=("serve", "ask"))
    parser.add_argument("command", nargs="?", default="")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--context")
    options = parser.parse_args(argv)
    if options.action == "ask":
        return ask(options.command, options.context)
    server = serve(read_token(), options.port)
    print(f"door: serving on 127.0.0.1:{options.port}", file=sys.stderr, flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
