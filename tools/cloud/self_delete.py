"""Runs on a rented machine from the moment it is set up: deletes the machine through its cloud provider's API
if the runner at home goes quiet, so a crash of the owner's PC never leaves a paid card running.

    python3 self_delete.py <deadline epoch> <key file> [quiet minutes] [backend]

The runner touches /root/batch/heartbeat every time it looks at the machine. When the heartbeat is
older than `quiet minutes` (15), or the batch's hard time limit has passed, the machine asks the API
to terminate itself: the card's cost stops there. Its address and disk outlive it, and the next
run's sweep deletes them after checking each belongs to the account. The key can only read, stop and
delete the account's machines, addresses and disks (#55, 2026-09-29). Each backend's way to ask the
machine who it is and to delete it is in BACKENDS (Scaleway: its metadata service and instance API).
Standard library only: this file goes onto the machine alone.
"""
import json
import pathlib
import sys
import time
import urllib.request

HEARTBEAT = pathlib.Path("/root/batch/heartbeat")
SCALEWAY_METADATA = "http://169.254.42.42/conf?format=json"
SCALEWAY_API = "https://api.scaleway.com/instance/v1/zones/{zone}/servers/{server}/action"
LOOK_SECONDS = 60


def scaleway_who_am_i():
    """This machine's id and zone, from Scaleway's metadata service."""
    with urllib.request.urlopen(SCALEWAY_METADATA, timeout=10) as answer:
        metadata = json.load(answer)
    return metadata["id"], metadata["location"]["zone_id"]


def quiet_seconds():
    """How long since the runner last touched the heartbeat."""
    return time.time() - HEARTBEAT.stat().st_mtime


def scaleway_terminate(server, zone, secret):
    """Ask Scaleway's API to terminate this machine; the answer's status code."""
    request = urllib.request.Request(SCALEWAY_API.format(zone=zone, server=server),
                                     data=json.dumps({"action": "terminate"}).encode(),
                                     headers={"X-Auth-Token": secret, "Content-Type": "application/json"},
                                     method="POST")
    with urllib.request.urlopen(request, timeout=30) as answer:
        return answer.status


# Each backend's (who am I, terminate me), by the backend's name (provider.py).
BACKENDS = {"scaleway": (scaleway_who_am_i, scaleway_terminate)}


def main():
    deadline, key_file = float(sys.argv[1]), pathlib.Path(sys.argv[2])
    quiet_limit = float(sys.argv[3] if len(sys.argv) > 3 else 15) * 60
    who_am_i, terminate = BACKENDS[sys.argv[4] if len(sys.argv) > 4 else "scaleway"]
    secret = json.loads(key_file.read_text())["secret_key"]
    server, zone = who_am_i()
    HEARTBEAT.touch()
    while True:
        why = ("past the batch's time limit" if time.time() > deadline
               else "the runner has been quiet too long" if quiet_seconds() > quiet_limit else None)
        if why:
            print(f"{time.strftime('%H:%M:%S')} deleting {server} in {zone}: {why}", flush=True)
            try:
                print("terminate answered", terminate(server, zone, secret), flush=True)
            except Exception as error:  # noqa: BLE001 - keep asking until the machine is gone
                print("terminate failed:", error, flush=True)
        time.sleep(LOOK_SECONDS)


if __name__ == "__main__":
    main()
