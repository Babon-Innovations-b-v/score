"""The environment's state as the store beside it holds it (state/local.py), in the models of state/models.py.

    source = state.source()
"""
import functools


@functools.cache
def source():
    """The store this process reads, made once."""
    from django.conf import settings
    from score.dashboard.state.local import LocalSource
    return LocalSource(settings.SCORE_PROPS_HOME, settings.SCORE_HOME, settings.SCORE_HOME / "web3d")
