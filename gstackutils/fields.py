import re
import os
import base64
import subprocess
from email.utils import parseaddr

from .exceptions import (
    ConfigMissingError, DefaultUsedException, ValidationError,
    ImproperlyConfigured, ServiceNotFound, InvalidValue,
)
from .validators import (
    MinMaxLengthValidator,
    TypeValidator,
    PrivateKeyValidator,
    CertificateValidator,
    EmailValidator,
    MinMaxValueValidator,
)
from .helpers import uid as _uid, gid as _gid


class NotSet:
    pass


class ConfigField:
    ENV_REGEX = re.compile(r"^\s*([^#].*?)=(.*)$")
    b64 = False
    default_validators = []

    def __init__(
        self, default=NotSet(), help_text=None,
        validators=[], services=[], secret=False,
    ):
        self.default = default
        self.help_text = help_text
        self.validators = validators
        self.secret = secret
        if secret:
            self.b64 = True
        self.name = None
        self.config = None

        if not isinstance(services, (list, tuple, dict)):
            raise ImproperlyConfigured(
                "The `services` parameter must be a tuple, a list or a dict"
            )
        if isinstance(services, (list, tuple)):
            services = dict([(k, []) for k in services])
        self.services = {}
        for s, ugm in services.items():
            if isinstance(ugm, (tuple, list)):
                if len(ugm) == 0:
                    self.services[s] = {"uid": 0, "gid": 0, "mode": 0o400}
                elif len(ugm) == 1:
                    self.services[s] = {"uid": ugm[0], "gid": ugm[0], "mode": 0o400}
                elif len(ugm) == 2:
                    self.services[s] = {"uid": ugm[0], "gid": ugm[1], "mode": 0o400}
                else:
                    self.services[s] = {"uid": ugm[0], "gid": ugm[1], "mode": ugm[2]}
            elif isinstance(ugm, dict):
                p = {}
                for k in ["uid", "gid", "mode"]:
                    if k in ugm:
                        p[k] = ugm[k]
                u = p.setdefault("uid", 0)
                p.setdefault("gid", u)
                p.setdefault("mode", 0o400)
                self.services[s] = p
            else:
                raise ImproperlyConfigured(
                    "A service item must be a tuple, a list or a dict"
                )

    def _setup_field(self, config, name):
        self.name = name
        self.config = config

    def get(self, root=False, default_exception=False, validate=False):
        try:
            if root:
                value = self.get_root()
            else:
                value = self.get_app()
        except ConfigMissingError:
            if isinstance(self.default, NotSet):
                raise ConfigMissingError(f"Config missing: {self.name}")
            if default_exception:
                raise DefaultUsedException(f"Default used for config: {self.name}")
            return self.default
        if validate:
            self.validate(value)
        return value

    def set(self, value, no_validate=False):
        if not no_validate and value is not None:
            self.validate(value)
        self.set_root(value)

    def validate(self, value):
        errors = []
        for validator in self.default_validators + self.validators:
            try:
                validator(self, value)
            except ValidationError as e:
                errors.append(e.args[0])
        if errors:
            raise ValidationError(errors)

    def get_root(self):
        try:
            with open(self.get_filepath(), "r") as f:
                for l in f.readlines():
                    m = self.ENV_REGEX.match(l)
                    if m and m.group(1) == self.name:
                        if self.b64:
                            ret = base64.b64decode(m.group(2))
                        else:
                            ret = m.group(2).encode()
                        return self.to_python(ret)
        except (FileNotFoundError, PermissionError):
            raise ConfigMissingError()
        else:
            raise ConfigMissingError()

    def set_root(self, value):
        # if to_bytes could not be decoded cleanly, b64 should be set
        if value is not None:
            value = self.to_bytes(value)
            if self.b64:
                value = base64.b64encode(value)
            value = value.decode()

        newlines = []
        actualline = f"{self.name}={value}\n"
        done = False
        with open(self.get_filepath(), "r") as f:
            lines = f.readlines()
        for l in lines:
            if done:  # if we are done, just append remaining lines
                newlines.append(l)
                continue
            m = self.ENV_REGEX.match(l)
            if m and m.group(1) == self.name:
                done = True
                if value is not None:  # if we delete, leave this line alone
                    newlines.append(actualline)
            else:
                newlines.append(l)
        if not done and value is not None:
            newlines.append(actualline)
        with open(self.get_filepath(), "w") as f:
            f.writelines(newlines)

    def prepare(self, service):
        if service in self.services:
            value = self.get(root=True, validate=True)
            self.set_app(value, service)

    def get_filepath(self):
        return self.config.secret_file_path if self.secret else self.config.env_file_path

    def to_python(self, b):
        raise NotImplementedError()

    def to_bytes(self, value):
        raise NotImplementedError()

    def get_app(self):
        if self.secret:
            fn = os.path.join(self.config.secret_dir, self.name)
            try:
                with open(fn, "rb") as f:
                    return self.to_python(f.read())
            except (FileNotFoundError, PermissionError):
                raise ConfigMissingError()

        s = os.environ.get(self.name)
        if s is None:
            raise ConfigMissingError()
        return self.to_python(s.encode())

    def set_app(self, value, service=None):
        if not self.secret:
            return
        try:
            s = self.services[service]
        except KeyError:
            raise ServiceNotFound(f"No such service: {service}")
        uid = _uid(s["uid"])
        gid = _gid(s["gid"])
        mode = s["mode"]
        fn = os.path.join(self.config.secret_dir, self.name)
        with open(fn, "wb") as f:
            f.write(self.to_bytes(value))
        os.chown(fn, uid, gid)
        os.chmod(fn, mode)

    def to_human_readable(self, value):
        if self.secret:
            return "*****"
        return str(value)


class StringConfig(ConfigField):
    validate_type = str
    default_validators = [MinMaxLengthValidator(), TypeValidator()]

    def __init__(self, min_length=None, max_length=None, **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(**kwargs)

    def to_python(self, b):
        return b.decode()

    def to_bytes(self, value):
        return value.encode()


class IntConfig(ConfigField):
    validate_type = int
    default_validators = [MinMaxValueValidator(), TypeValidator()]

    def __init__(self, min_value=None, max_value=None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(**kwargs)

    def to_python(self, b):
        try:
            return int(b)
        except ValueError:
            raise InvalidValue()

    def to_bytes(self, value):
        return str(value).encode()


class FileConfig(ConfigField):
    validate_type = bytes
    default_validators = [MinMaxLengthValidator(), TypeValidator()]

    def __init__(self, min_length=None, max_length=None, **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        self.b64 = True
        super().__init__(**kwargs)

    def to_python(self, b):
        return b

    def to_bytes(self, value):
        return value

    def to_human_readable(self, value):
        return f"File of size {len(value)} bytes"


class BoolConfig(ConfigField):
    validate_type = bool
    default_validators = [TypeValidator()]

    def to_python(self, b):
        if b == b"True":
            return True
        elif b == b"False":
            return False
        raise InvalidValue()

    def to_bytes(self, value):
        return b"True" if value else b"False"


class EmailConfig(StringConfig):
    default_validators = [EmailValidator()]

    def to_python(self, b):
        return parseaddr(b.decode())

    def to_bytes(self, value):
        if value[0]:
            return f"{value[0]} <{value[1]}>".encode()
        return value[1].encode()


class SSLPrivateKey(FileConfig):
    default_validators = [MinMaxLengthValidator(), TypeValidator(), PrivateKeyValidator()]

    def __init__(self, secret=True, **kwargs):
        if secret is False:
            raise ImproperlyConfigured("SSLPrivateKey must be secret.")
        super().__init__(**kwargs)
        self.secret = True

    def to_human_readable(self, value):
        return f"SSL private key file of size {len(value)} bytes"


class SSLCertificate(FileConfig):
    default_validators = [MinMaxLengthValidator(), TypeValidator(), CertificateValidator()]

    def __init__(self, getname=None, getca=None, **kwargs):
        self.getname = getname
        self.getca = getca
        super().__init__(**kwargs)

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


class ListMixin:
    def __init__(self, separator=b",", **kwargs):
        self.separator = separator
        if not isinstance(separator, bytes):
            self.separator = separator.encode()
        super().__init__(**kwargs)

    def to_python(self, b):
        return [super(ListMixin, self).to_python(x) for x in b.split(self.separator)]

    def to_bytes(self, value):
        return self.separator.join([super(ListMixin, self).to_bytes(x) for x in value])

    def validate(self, value):
        errors = []
        for val in value:
            try:
                super().validate(val)
            except ValidationError as ve:
                errors += ve.args[0]
        if errors:
            raise ValidationError(errors)

    def to_human_readable(self, value):
        return str([super(ListMixin, self).to_human_readable(x) for x in value])


class StringListConfig(ListMixin, StringConfig):
    pass


class EmailListConfig(ListMixin, EmailConfig):
    def to_human_readable(self, value):
        return str(value)


class IntListConfig(ListMixin, IntConfig):
    pass
