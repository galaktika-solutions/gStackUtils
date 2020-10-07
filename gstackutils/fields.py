import base64
from email import utils as email_utils

from . import exceptions
from . import validators


class Field:
    """Base class for specific config fields."""

    binary = False
    default_validators = []

    def __init__(
        self, file, hide=False, b64=False, default=None, help_text=None,
        validators=(), services=[]
    ):
        self.file = file
        self.hide = hide
        self.b64 = b64
        self.default = default
        self.help_text = help_text
        self.validators = [*self.default_validators, *validators]
        self.services = services

    def from_stream(self, bytes_or_str):
        if self.binary:
            if not isinstance(bytes_or_str, bytes):
                raise ValueError(f"Wrong stream type: expected bytes, got {type(bytes_or_str).__name__}")
            return self.from_bytes(bytes_or_str)
        if not isinstance(bytes_or_str, str):
            raise ValueError(f"Wrong stream type: expected str, got {type(bytes_or_str).__name__}")
        return self.from_str(bytes_or_str)

    def from_bytes(b):
        raise NotImplementedError()

    def from_str(s):
        raise NotImplementedError()

    def to_stream(self, value):
        if self.binary:
            return self.to_bytes(value)
        return self.to_str(value)

    def to_str(self, value):
        raise NotImplementedError()

    def to_bytes(self, value):
        raise NotImplementedError()

    def from_storage(self, storage_str):
        if self.hide or self.binary or self.b64:
            stream = base64.b64decode(storage_str)
            if not self.binary:
                stream = stream.decode()
        else:
            stream = storage_str
        return self.from_stream(stream)

    def to_storage(self, value):
        stream = self.to_stream(value)
        if self.hide or self.binary or self.b64:
            return base64.b64encode(
                stream if self.binary else stream.encode()
            ).decode()
        if ("\n" in stream) or ("\r" in stream):
            raise ValueError(r"Value should not contain \n or \r. Use b64=True")
        return stream

    def validate(self, value):
        errors = []
        for validator in self.validators:
            try:
                validator(value)
            except exceptions.ValidationError as e:
                errors.append(e)
        if errors:
            raise exceptions.ValidationError(errors)

    def human_readable(self, value):
        return str(value)

    def reportable(self, value):
        if self.hide and value != self.default:
            return "*****"
        return self.human_readable(value)


class MaxMinLengthMixin:
    def __init__(self, *args, max_length=None, min_length=None, **kwargs):
        self.max_length = max_length
        self.min_length = min_length
        super().__init__(*args, **kwargs)
        if min_length is not None:
            self.validators.append(validators.MinLengthValidator(int(min_length)))
        if max_length is not None:
            self.validators.append(validators.MaxLengthValidator(int(max_length)))


class ListMixin:
    def __init__(self, *args, separator=",", min_items=None, max_items=None, **kwargs):
        assert not self.binary, "ListMixin can not be used on a binary field."
        self.separator = separator
        self.min_items = min_items
        self.max_items = max_items
        super(ListMixin, self).__init__(*args, **kwargs)

    def from_str(self, s):
        return [super(ListMixin, self).from_str(e) for e in s.split(self.separator)]

    def to_str(self, value):
        return self.separator.join([super(ListMixin, self).to_str(e) for e in value])

    def human_readable(self, value):
        return "[" + self.separator.join([super(ListMixin, self).human_readable(v) for v in value]) + "]"

    def validate(self, value):
        errors = []
        if self.min_items is not None and len(value) < self.min_items:
            errors.append(exceptions.ValidationError(f"list should contain at least {self.min_items} elements"))
        if self.max_items is not None and len(value) > self.max_items:
            errors.append(exceptions.ValidationError(f"list should contain at most {self.max_items} elements"))
        for v in value:
            try:
                super().validate(v)
            except exceptions.ValidationError as e:
                errors += e.error_list
        if errors:
            raise exceptions.ValidationError(errors)


class StringField(MaxMinLengthMixin, Field):
    def from_str(self, s):
        return s

    def to_str(self, value):
        return value


class StringListField(ListMixin, StringField):
    pass


class IntegerField(Field):
    def __init__(self, *args, max_value=None, min_value=None, **kwargs):
        self.max_value = max_value
        self.min_value = min_value
        super().__init__(*args, **kwargs)
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(int(min_value)))
        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(int(max_value)))

    def from_str(self, s):
        return int(s)

    def to_str(self, value):
        return str(value)


class IntegerListField(ListMixin, IntegerField):
    pass


class BooleanField(Field):
    def from_str(self, s):
        return s.upper() in ("TRUE", "ON", "1")

    def to_str(self, value):
        return str(value)


class FileField(MaxMinLengthMixin, Field):
    binary = True

    def from_bytes(self, b):
        return b

    def to_bytes(self, value):
        return value

    def human_readable(self, value):
        return f"File of size {len(value)} bytes"


class EmailField(Field):
    default_validators = [validators.EmailValidator()]

    def from_str(self, s):
        return email_utils.parseaddr(s)

    def to_str(self, value):
        if value[0]:
            return f"{value[0]} <{value[1]}>"
        return value[1]

    def human_readable(self, value):
        return self.to_str(value)


class EmailListField(ListMixin, EmailField):
    pass


class HostNameField(StringField):
    default_validators = [validators.HostNameValidator()]


class HostNameListField(ListMixin, HostNameField):
    pass


class IPField(StringField):
    default_validators = [validators.IPValidator()]


class IPListField(ListMixin, IPField):
    pass


class SSLPrivateKeyField(Field):
    binary = True

    def __init__(self, *args, **kwargs):
        if "secret" in kwargs and not kwargs["secret"]:
            raise exceptions.InvalidUsage("SSLPrivateKey must always be a secret.")
        kwargs["secret"] = True
        super().__init__(*args, **kwargs)

    def from_bytes(self, b):
        return crypto.load_privatekey(SSL.FILETYPE_PEM, b)

    def to_bytes(self, value):
        return crypto.dump_privatekey(SSL.FILETYPE_PEM, value)

    def human_readable(self, value):
        return f"SSL private key, bitsize: {value.bits()}"


class SSLCertificateField(Field):
    binary = True
    default_validators = [validators.CertificateExpiryValidator()]

    def from_bytes(self, b):
        cert = crypto.load_certificate(SSL.FILETYPE_PEM, b)
        return cert

    def to_bytes(self, value):
        return crypto.dump_certificate(SSL.FILETYPE_PEM, value)

    def human_readable(self, value):
        sanlist = cert.get_alt_names(value)
        simplelist = ", ".join([x[1] for x in sanlist])
        return f"certificate for {simplelist}; valid until {cert.expiry(value)} UTC"
