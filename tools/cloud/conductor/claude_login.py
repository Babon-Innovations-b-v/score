#!/usr/bin/python3 -I
"""Claude Code on the conductor (owner's yes, 2026-11-05: "Yes, log Claude in on the conductor"): the finish route's
palette, library, list and recheck ask `claude -p` (score/adapters/models/claude_code.py, whose bytes are in those
rows' code version and stay as they are); this decides only where that call runs and with which login.

    python3 claude_login.py link    # secrets.sh, every boot and hour: `claude` on the PATH while the secret exists
    claude -p ...                   # LINK -> this file: the login read by name, then the pinned CLI exec'd

boot.sh installs the pinned CLI at CLI (`~/.local/lib/claude-code`, off the PATH). `link` puts LINK
(`~/.local/bin/claude`, on the env file's PATH) to this file while CLI is there and the secret TOKEN_SECRET reads,
and removes it otherwise, so the adapter's `shutil.which("claude")` finds nothing and its NotHere ("runs on this PC")
stops the rows exactly as before. Run as `claude`, it reads the secret by name through SCORE_SECRET_READER (the
conductor's one reader, score-secret-reader) at the call and execs CLI with it in CLAUDE_CODE_OAUTH_TOKEN, in that
process's environment alone: never a file, a log line, a ledger, a fault report or an argument. Standard library
only: it runs under /usr/bin/python3, outside any checkout's environment.
"""
import os
import pathlib
import subprocess
import sys

TOKEN_SECRET = "claude-code-oauth-token"
TOKEN_ENV = "CLAUDE_CODE_OAUTH_TOKEN"
READER = "SCORE_SECRET_READER"
HOME = pathlib.Path(os.environ.get("HOME", pathlib.Path.home()))
CLI = pathlib.Path(os.environ.get("SCORE_CLAUDE_CLI", HOME / ".local" / "lib" / "claude-code" / "bin" / "claude"))
LINK = pathlib.Path(os.environ.get("SCORE_CLAUDE_LINK", HOME / ".local" / "bin" / "claude"))


def token():
    """The login's value, read by name through the secret reader into this process only; None when the secrets
    project holds no such secret or no reader is named. A failed read raises, never reads as absent."""
    reader = os.environ.get(READER)
    if not reader:
        return None
    done = subprocess.run([reader, "--if-present", TOKEN_SECRET], capture_output=True, text=True, timeout=60)
    if done.returncode:
        raise RuntimeError(f"{TOKEN_SECRET} not read (exit {done.returncode})")
    return done.stdout.strip() or None


def environment(base, value):
    """The CLI's environment: `base` with the login in TOKEN_ENV and no API key, so it bills the subscription."""
    return {**{name: each for name, each in base.items() if name != "ANTHROPIC_API_KEY"}, TOKEN_ENV: value}


def link():
    """LINK to this file while the CLI is installed and the login reads, else none of ours (a `claude` that is not
    this file's link is left as it is); one line saying which."""
    here = CLI.is_file() and os.access(CLI, os.X_OK) and token() is not None
    LINK.parent.mkdir(parents=True, exist_ok=True)
    if here:
        partial = LINK.with_name(f".{LINK.name}.{os.getpid()}")
        partial.unlink(missing_ok=True)
        partial.symlink_to(pathlib.Path(__file__).resolve())
        partial.replace(LINK)
        return f"claude-login: {LINK} -> the pinned CLI with {TOKEN_SECRET}"
    if LINK.is_symlink() and LINK.resolve() == pathlib.Path(__file__).resolve():  # never a claude of someone else's
        LINK.unlink()
    return f"claude-login: no {LINK} (CLI installed: {CLI.is_file()}; the secret {TOKEN_SECRET} not held)"


def run(arguments):
    """Exec the pinned CLI with `arguments` and the login in its environment; exit 1, saying why, without either."""
    value = token()
    if value is None or not CLI.is_file():
        sys.exit(f"claude-login: no {TOKEN_SECRET} secret or no CLI at {CLI}: Claude Code is not logged in here")
    os.execve(CLI, [str(CLI), *arguments], environment(os.environ, value))


if __name__ == "__main__":
    if sys.argv[1:] == ["link"]:
        print(link())
    else:
        run(sys.argv[1:])
