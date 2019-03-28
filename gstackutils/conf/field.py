from .storage import EnvVarStorage, EnvFileStorage, SecretStorage, SecretFileStorage
from .exceptions import ConfigMissingError, ValidationError, DefaultUsedException


class NotSet:
    pass


class ConfigField:
    def __init__(self, default=NotSet(), help_text=None):
        self.default = default
        self.help_text = help_text
        self.name = None
        self.app_storage = None
        self.root_storage = None

    def setup_storage(self, config):
        raise NotImplementedError()

    def setup_field(self, config, name):
        self.name = name
        self.setup_storage(config)

    def get(self, root=False, default_exception=False):
        read = self.root_storage.read if root else self.app_storage.read
        val = read(self.name)
        if val is None:
            if isinstance(self.default, NotSet):
                raise ConfigMissingError()
            if default_exception:
                raise DefaultUsedException()
            return self.default
        val = self.from_storage(val)
        return self.validate(val)

    def set(self, value):
        val = self.validate(value)
        val = self.to_storage(value)
        self.root_storage.write(self.name, val)

    def delete(self):
        self.root_storage.delete(self.name)

    def prepare(self, **kwargs):
        val = self.get(root=True)
        val = self.to_storage(val)
        self.app_storage.write(self.name, val, **kwargs)

    def from_storage(self, value):
        raise NotImplementedError()

    def to_storage(self, value):
        raise NotImplementedError()

    def human_readable(self, value):
        return repr(value)

    def validate(self, value):
        return value


class SecretString(ConfigField):
    def __init__(self, min_length=0, max_length=None, **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(**kwargs)

    def setup_storage(self, config):
        self.app_storage = SecretStorage(config.secret_dir)
        self.root_storage = SecretFileStorage(config.secret_file_path)

    def validate(self, value):
        if not isinstance(value, str):
            raise ValidationError(f"Not a string: {value}.")
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(
                f"Too short ({len(value)} < {self.min_length})"
            )
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(
                f"Too long ({len(value)} > {self.max_length})."
            )
        return super().validate(value)

    def from_storage(self, value):
        return value.decode()

    def to_storage(self, value):
        return value.encode()

    def human_readable(self, value):
        return value


class EnvString(SecretString):
    def setup_storage(self, config):
        self.app_storage = EnvVarStorage()
        self.root_storage = EnvFileStorage(config.env_file_path)

    def prepare(self):
        pass
