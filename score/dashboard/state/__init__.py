"""The world's state as the dashboard shows it: one source per mode, the same models (state/models.py) from both.

    source = state.source()   # local: the store beside it (state/local.py); hosted: the pushed export (exported.py)
"""
import functools


@functools.cache
def source():
    """The source this process serves from, made once: local mode reads the store, hosted mode the export."""
    from django.conf import settings
    if settings.SCORE_MODE == settings.HOSTED:
        from score.dashboard.state.exported import ExportedSource
        return ExportedSource(settings.SCORE_HOME / "export" / "current")
    from score.dashboard.state.local import LocalSource
    return LocalSource(settings.SCORE_PROPS_HOME, settings.SCORE_HOME, settings.SCORE_WEB_COPIES)
