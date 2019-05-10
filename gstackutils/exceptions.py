class ImproperlyConfigured(Exception):
    pass


class DatabaseNotPresent(Exception):
    pass


class ServiceNotFound(Exception):
    pass


class ConfigMissingError(Exception):
    pass


class ValidationError(Exception):
    pass


class DefaultUsedException(Exception):
    pass


class PermissionDenied(Exception):
    pass


class InvalidValue(Exception):
    pass
