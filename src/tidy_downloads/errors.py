"""Errors a user can fix, shown without a traceback."""


class TidyError(Exception):
    """Expected failure (bad config, unreadable folder, failed move)."""


class ConfigError(TidyError):
    """The user config is missing or invalid."""


class UndoError(TidyError):
    """The undo log is missing or cannot be applied safely."""
