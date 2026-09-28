class JolpicaError(Exception):
    """Base error raised by the Jolpica adapter."""


class JolpicaUnavailable(JolpicaError):
    """The API could not be reached or returned a transient server error."""


class JolpicaRateLimited(JolpicaError):
    """The API rejected the request because its public quota was exhausted."""


class JolpicaInvalidPayload(JolpicaError):
    """The API response did not match the required public contract."""
