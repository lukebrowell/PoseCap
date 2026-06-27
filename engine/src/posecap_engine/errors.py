"""Engine-side exceptions."""


class EngineError(Exception):
    """Base class for engine bridge failures."""


class CaptureUnavailableError(EngineError):
    """Camera capture cannot run in the current environment."""


class StreamServerError(EngineError):
    """The TCP pose stream could not start or continue."""
