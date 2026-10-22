#!/bin/sh
# The agents' door, installed by boot.sh as /usr/local/bin/score-agent-door: the forced command of the agents' line in
# user score's authorized_keys (command="/usr/local/bin/score-agent-door",no-pty,no-port-forwarding,
# no-agent-forwarding,no-X11-forwarding). What it allows and how is agent_door.py's docstring; this only hands the
# asked command (SSH_ORIGINAL_COMMAND, set by sshd) to it under the checkout's interpreter, isolated from PYTHON*
# variables and the user's site folder.
REPO="${SCORE_DOOR_REPO:-/home/score/projects/score}"
exec "$REPO/.venv/bin/python" -I "$REPO/tools/cloud/conductor/agent_door.py"
