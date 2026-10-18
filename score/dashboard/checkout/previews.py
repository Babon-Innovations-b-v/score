"""The hash of the preview the owner reviews for a fix branch: its commit and every proposal the cockpit keeps for it
(`<home>/proposals/<branch>/<place>/proposal.json`, score/dashboard/proposals). A new commit on the branch or a
proposal made again gives a new hash, so a checkout can refuse what he never saw."""
import hashlib
import pathlib

from django.conf import settings

RECORD = "proposal.json"


def proposals_root():
    return pathlib.Path(settings.SCORE_HOME) / "proposals"


def preview_hash(branch, head):
    """sha256 of the branch's commit and its proposals' records, place by place."""
    digest = hashlib.sha256(f"{branch}\n{head}\n".encode())
    for path in sorted((proposals_root() / branch).glob(f"*/{RECORD}")):
        digest.update(f"{path.parent.name}\n".encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
