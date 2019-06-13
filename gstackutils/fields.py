import base64

from . import exceptions
from . import validators


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
        return self.from_stream(bytes_or_str)

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

        stream = base64.b64decode(storage_str)
        if self.binary:
            return self._from_stream(stream)
        return self._from_stream(stream.decode())

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


class StringField(MaxMinLengthMixin, ShowStreamOrMaskMixin, Field):
    def from_stream(self, s):
        return s

    def to_stream(self, value):
        return value


class IntegerField(ShowStreamOrMaskMixin, Field):
    def __init__(self, *, max_value=None, min_value=None, **kwargs):
        self.max_value = max_value
        self.min_value = min_value
        super().__init__(**kwargs)
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(int(min_value)))
        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(int(max_value)))

    def from_stream(self, s):
        return int(s)

    def to_stream(self, value):
        return str(value)


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
