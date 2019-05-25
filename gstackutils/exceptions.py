class GstackException(Exception):
    """Base exception for all others."""
    pass


class PermissionDenied(GstackException):
    """Indicates insufficient privileges."""
    pass


class ImproperlyConfigured(GstackException):
    """Raised when the current setup (values, file locations etc.) does not meet
    one or more requirements.
    """
    pass
