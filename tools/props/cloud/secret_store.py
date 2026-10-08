"""Secrets by name, from wherever this box keeps them: an environment variable first, else the cloud backend's
secret store (Scaleway Secret Manager on the current backend). No secret is ever written into the repo.

    SCORE_SECRET_GEMINI_API_KEY=... python3 ...   # the secret `gemini-api-key`, for local use
"""
import os


def environment_name(name):
    """The environment variable that holds the secret `name`: SCORE_SECRET_ and its name in capitals."""
    return "SCORE_SECRET_" + "".join(letter if letter.isalnum() else "_" for letter in name).upper()


def secret(name):
    """The secret `name`'s value: from its environment variable when set, else from the cloud backend."""
    if os.environ.get(environment_name(name)):
        return os.environ[environment_name(name)]
    from provider import cloud

    return cloud.secret(name)
