import base64
from email import utils as email_utils

from OpenSSL import crypto, SSL

from . import exceptions
from . import validators
from . import cert


class Field:
    """Base class for specific config fields."""

    binary = False
    default_validators = []

    def __init__(
        self, secret=False, b64=False, default=None, help_text=None,
        validators=()
    ):
        self.secret = secret
        self.b64 = b64 or self.binary or secret
        self.default = default
        self.help_text = help_text
        self.validators = [*self.default_validators, *validators]

    def from_stream(self, bytes_or_str):
        raise NotImplementedError()

    def to_stream(self, value):
        raise NotImplementedError()

    def _from_stream(self, bytes_or_str):
        if self.binary and not isinstance(bytes_or_str, bytes):
            raise ValueError("`from_stream` got wrong argument, should be bytes.")
        if not self.binary and not isinstance(bytes_or_str, str):
            raise ValueError("`from_stream` got wrong argument, should be str.")
        try:
            return self.from_stream(bytes_or_str)
        except Exception:
            raise ValueError("invalid stream representation")

    def _to_stream(self, value):
        val = self.to_stream(value)
        if self.binary and not isinstance(val, bytes):
            raise ValueError("`to_stream` returned wrong value: should be bytes.")
        if not self.binary and not isinstance(val, str):
            raise ValueError("`to_stream` returned wrong value: should be str.")
        return val

    def to_storage(self, value):
        stream = self._to_stream(value)
        if not self.b64:
            assert isinstance(stream, str), "Bytes stream can only be stored in base64."
            ret = stream
        else:
            ret = base64.b64encode(
                stream if isinstance(stream, bytes) else stream.encode()
            ).decode()
        if "\n" in ret:
            raise exceptions.ValidationError(
                "The value must not contain the newline character"
            )
        return ret

    def from_storage(self, storage_str):
        if not self.b64:
            return self._from_stream(storage_str)

        try:
            stream = base64.b64decode(storage_str)
        except Exception:
            raise ValueError("invalid storeage representation")
        if self.binary:
            return self._from_stream(stream)
        try:
            decoded = stream.decode()
        except Exception:
            raise ValueError("invalid storeage representation")
        return self._from_stream(decoded)

    def validate(self, value):
        errors = []
        for validator in self.validators:
            try:
                validator(value)
            except exceptions.ValidationError as e:
                errors.append(e)
        if errors:
            raise exceptions.ValidationError(errors)

    def reportable(self, value):
        raise NotImplementedError()


class MaxMinLengthMixin:
    def __init__(self, *, max_length=None, min_length=None, **kwargs):
        self.max_length = max_length
        self.min_length = min_length
        super().__init__(**kwargs)
        if min_length is not None:
            self.validators.append(validators.MinLengthValidator(int(min_length)))
        if max_length is not None:
            self.validators.append(validators.MaxLengthValidator(int(max_length)))


class ShowStreamOrMaskMixin:
    def reportable(self, value):
        if self.secret:
            return "*****"
        return self.to_stream(value)


class ListMixin:
    def __init__(self, *args, separator=",", **kwargs):
        assert not self.binary, "ListMixin can not be used on a binary field."
        self.separator = separator
        super(ListMixin, self).__init__(*args, **kwargs)

    def validate(self, value):
        errors = []
        for v in value:
            try:
                super().validate(v)
            except exceptions.ValidationError as e:
                errors += e.error_list

    def from_stream(self, s):
        return [super(ListMixin, self).from_stream(e) for e in s.split(self.separator)]

    def to_stream(self, value):
        return self.separator.join([super(ListMixin, self).to_stream(e) for e in value])

    def reportable(self, value):
        return f"[{super(ListMixin, self).reportable(value)}]"


class StringField(MaxMinLengthMixin, ShowStreamOrMaskMixin, Field):
    def from_stream(self, s):
        return s

    def to_stream(self, value):
        return value


class IntegerField(ShowStreamOrMaskMixin, Field):
    def __init__(self, *args, max_value=None, min_value=None, **kwargs):
        self.max_value = max_value
        self.min_value = min_value
        super().__init__(*args, **kwargs)
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(int(min_value)))
        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(int(max_value)))

    def from_stream(self, s):
        return int(s)

    def to_stream(self, value):
        return str(value)


class IntegerListField(ListMixin, IntegerField):
    pass


class StringListField(ListMixin, StringField):
    pass


class BooleanField(ShowStreamOrMaskMixin, Field):
    def from_stream(self, s):
        return s.upper() in ("TRUE", "ON", "1")

    def to_stream(self, value):
        return str(value)


class FileField(MaxMinLengthMixin, Field):
    binary = True

    def from_stream(self, b):
        return b

    def to_stream(self, value):
        return value

    def reportable(self, value):
        return f"File of size {len(value)} bytes"


class EmailField(ShowStreamOrMaskMixin, Field):
    default_validators = [validators.EmailValidator()]

    def from_stream(self, s):
        return email_utils.parseaddr(s)

    def to_stream(self, value):
        if value[0]:
            return f"{value[0]} <{value[1]}>"
        return value[1]


class EmailListField(ListMixin, EmailField):
    pass


class SSLPrivateKeyField(Field):
    binary = True

    def __init__(self, *args, **kwargs):
        if "secret" in kwargs and not kwargs["secret"]:
            raise exceptions.InvalidUsage("SSLPrivateKey must always be a secret.")
        kwargs["secret"] = True
        super().__init__(*args, **kwargs)

    def from_stream(self, b):
        return crypto.load_privatekey(SSL.FILETYPE_PEM, b)

    def to_stream(self, value):
        return crypto.dump_privatekey(SSL.FILETYPE_PEM, value)

    def reportable(self, value):
        return f"SSL private key, bitsize: {value.bits()}"


class SSLCertificateField(Field):
    binary = True
    default_validators = [validators.CertificateExpiryValidator()]

    def from_stream(self, b):
        cert = crypto.load_certificate(SSL.FILETYPE_PEM, b)
        return cert

    def to_stream(self, value):
        return crypto.dump_certificate(SSL.FILETYPE_PEM, value)

    def reportable(self, value):
        sanlist = cert.get_alt_names(value)
        simplelist = ", ".join([x[1] for x in sanlist])
        return f"certificate for {simplelist}; valid until {cert.expiry(value)} UTC"
