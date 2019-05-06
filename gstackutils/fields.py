import re
import os
import base64
import subprocess

from .exceptions import (
    ConfigMissingError, DefaultUsedException, ValidationError, ImproperlyConfigured
)
from .validators import (
    MinLengthValidator, MaxLengthValidator, TypeValidator, PrivateKeyValidator,
    CertificateValidator
)
from .helpers import uid as _uid, gid as _gid


class NotSet:
    pass


class ConfigField:
    ENV_REGEX = re.compile(r"^\s*([^#].*?)=(.*)$")
    hide_input = False
    services = {}

    def __init__(self, default=NotSet(), help_text=None, validators=[]):
        self.default = default
        self.help_text = help_text
        self.validators = validators
        self.name = None

    def _setup_field(self, config, name):
        """Must be called befor the field can be used."""
        self.name = name
        self.config = config

    def get(self, root=False, default_exception=False, validate=False):
        """Returns value depending on the field typeself.

        No validation occurs except when `validate` is set to `True`.
        """
        if root:
            value = self.get_root()
        else:
            value = self.get_app()
        if value is None:
            if isinstance(self.default, NotSet):
                raise ConfigMissingError(f"Config missing: {self.name}")
            if default_exception:
                raise DefaultUsedException(f"Default used for config: {self.name}")
            return self.default
        if validate:
            self.validate(value)
        return value

    def set(self, value, no_validate=False):
        """Validation is done based on the value of `no_validate`."""
        if not no_validate and value is not None:
            self.validate(value)
        self.set_root(value)

    def validate(self, value):
        errors = []
        for validator in self.validators:
            try:
                validator.validate(self.config, value)
            except ValidationError as e:
                errors.append(e.args[0])
        if errors:
            raise ValidationError(errors)

    def _get_filepath(self):
        raise NotImplementedError()

    def get_root(self):
        """Returns value from the storage file (or None)"""
        with open(self._get_filepath(), "r") as f:
            for l in f.readlines():
                m = self.ENV_REGEX.match(l)
                if m and m.group(1) == self.name:
                    return m.group(2)
        return None

    def set_root(self, value):
        newlines = []
        done = False
        with open(self._get_filepath(), "r") as f:
            lines = f.readlines()
        for l in lines:
            if done:  # if we are done, just append remaining lines
                newlines.append(l)
                continue
            m = self.ENV_REGEX.match(l)
            if m and m.group(1) == self.name:
                done = True
                if value is not None:  # if we delete, leave this line alone
                    newlines.append(f"{self.name}={value}\n")
            else:
                newlines.append(l)
        if not done and value is not None:
            newlines.append(f"{self.name}={value}\n")
        with open(self._get_filepath(), "w") as f:
            f.writelines(newlines)

    def get_app(self):
        """Returns value as presented for the app (or None)"""
        raise NotImplementedError()

    def set_app(self, value, service=None):
        raise NotImplementedError()

    def to_human_readable(self, value):
        return str(value)

    def to_stdout(self, value):
        """Converts to meaningful bytes"""
        return str(value).encode()

    def from_stdin(self, b):
        """Converts from bytes"""
        return b.decode()

    def prepare(self, service):
        if service in self.services:
            value = self.get(root=True, validate=True)
            self.set_app(value, service)


class EnvConfigField(ConfigField):
    def _get_filepath(self):
        return self.config.env_file_path

    def get_app(self):
        return os.environ.get(self.name)

    def set_app(self, value, service=None):
        # os.environ[self.name] = value
        pass


class SecretConfigField(ConfigField):
    hide_input = True

    def __init__(self, services={}, **kwargs):
        self.services = {}
        for s, ugm in services.items():
            if isinstance(ugm, (tuple, list)):
                if len(ugm) == 0:
                    self.services[s] = {}
                elif len(ugm) == 1:
                    self.services[s] = {"uid": ugm[0]}
                elif len(ugm) == 2:
                    self.services[s] = {"uid": ugm[0], "gid": ugm[1]}
                else:
                    self.services[s] = {"uid": ugm[0], "gid": ugm[1], "mode": ugm[2]}
            elif isinstance(ugm, dict):
                p = {}
                for k in ["uid", "gid", "mode"]:
                    if k in ugm:
                        p[k] = ugm[k]
                self.services[s] = p
            else:
                raise ImproperlyConfigured(
                    "The `services` parameter must be a tuple, a list or a dict"
                )
        super().__init__(**kwargs)

    def _get_filepath(self):
        return self.config.secret_file_path

    def get_root(self):
        value = super().get_root()
        if value is not None:
            return base64.b64decode(value).decode()

    def set_root(self, value):
        if value is not None:
            value = base64.b64encode(value.encode()).decode()
        super().set_root(value)

    def get_app(self):
        fn = os.path.join(self.config.secret_dir, self.name)
        with open(fn, "r") as f:
            return f.read()

    def set_app(self, value, service=None):
        s = self.services.get(service, {})
        uid = _uid(s.get("uid", 0))
        gid = _gid(s.get("gid", uid))
        mode = s.get("mode", 0o400)
        fn = os.path.join(self.config.secret_dir, self.name)
        with open(fn, "w") as f:
            f.write(value)
        os.chown(fn, uid, gid)
        os.chmod(fn, mode)

    def to_human_readable(self, value):
        return "*****"


class StringMixin:
    def __init__(self, min_length=0, max_length=None, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(TypeValidator(str))
        if min_length:
            validators.append(MinLengthValidator(min_length))
        if max_length:
            validators.append(MaxLengthValidator(max_length))
        super().__init__(validators=validators, **kwargs)


class EnvString(StringMixin, EnvConfigField):
    pass


class SecretString(StringMixin, SecretConfigField):
    pass


class EnvBool(EnvConfigField):
    def __init__(self, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(TypeValidator(bool))
        super().__init__(validators=validators, **kwargs)

    def _from_str(self, s):
        # print(f"_from_str {self.name}: {s}")
        if s == "True":
            return True
        elif s == "False":
            return False
        elif s is None:
            return None
        raise ValidationError("Invalid value.")

    def get_root(self):
        return self._from_str(super().get_root())

    def get_app(self):
        return self._from_str(super().get_app())

    def from_stdin(self, b):
        return self._from_str(b.decode())


class FileMixin:
    def __init__(self, min_size=None, max_size=None, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(TypeValidator(bytes))
        if min_size:
            validators.append(MinLengthValidator(min_size))
        if max_size:
            validators.append(MaxLengthValidator(max_size))
        super().__init__(validators=validators, **kwargs)

    def get_root(self):
        value = super().get_root()
        if value is not None:
            return base64.b64decode(value)

    def set_root(self, value):
        if value is not None:
            value = base64.b64encode(value).decode()
        super().set_root(value)

    def get_app(self):
        fn = os.path.join(self.config.secret_dir, self.name)
        with open(fn, "rb") as f:
            return f.read()

    def set_app(self, value, service=None):
        s = self.services.get(service, {})
        uid = _uid(s.get("uid", 0))
        gid = _gid(s.get("gid", uid))
        mode = s.get("mode", 0o400)
        fn = os.path.join(self.config.secret_dir, self.name)
        with open(fn, "wb") as f:
            f.write(value)
        os.chown(fn, uid, gid)
        os.chmod(fn, mode)

    def to_human_readable(self, value):
        return f"File of size {len(value)} bytes"

    def to_stdout(self, value):
        return value

    def from_stdin(self, b):
        return b


class EnvFile(FileMixin, EnvConfigField):
    pass


class SecretFile(FileMixin, SecretConfigField):
    pass


class SSLPrivateKey(SecretFile):
    def __init__(self, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(PrivateKeyValidator())
        super().__init__(validators=validators, **kwargs)

    def to_human_readable(self, value):
        return f"SSL private key file of size {len(value)} bytes"


class SSLCertificate(SecretFile):
    def __init__(self, **kwargs):
        getnamefor = kwargs.pop("getnamefor", None)
        getCA = kwargs.pop("getCA", None)
        validate = kwargs.pop("validate", True)
        validators = kwargs.pop("validators", [])
        if validate:
            validators.append(CertificateValidator(getnamefor=getnamefor, getCA=getCA))
        super().__init__(validators=validators, **kwargs)

    def to_human_readable(self, value):
        try:
            ret = subprocess.run(
                ("openssl", "x509", "-text", "-noout"),
                input=value, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            return "SSL certificate (could not load info)"

        stdout = ret.stdout.decode()
        try:
            cn = re.match(r".*Subject: CN = (.+?)\n", stdout, re.DOTALL).group(1)
        except AttributeError:
            cn = "?"
        try:
            ex = re.match(r".*Not After\s*: (.+?)\n", stdout, re.DOTALL).group(1)
        except AttributeError:
            ex = "?"

        return f"SSL certificate for '{cn}' (exp.: {ex})"
