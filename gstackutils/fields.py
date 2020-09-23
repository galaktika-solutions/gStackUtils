import base64

from . import exceptions


class Field:
    """Base class for specific config fields."""

    binary = False
    default_validators = []

    def __init__(
        self, file, hide=False, default=None, help_text=None,
        validators=(), services=[]
    ):
        self.file = file
        self.hide = hide
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
        if self.hide or self.binary:
            stream = base64.b64decode(storage_str)
            if not self.binary:
                stream = stream.decode()
        else:
            stream = storage_str
        return self.from_stream(stream)

    def to_storage(self, value):
        stream = self.to_stream(value)
        if self.hide or self.binary:
            return base64.b64encode(
                stream if self.binary else stream.encode()
            ).decode()
        if ("\n" in stream) or ("\r" in stream):
            raise ValueError(r"Value should not contain \n or \r. Use hide=True")
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

    def reportable(self, value):
        raise NotImplementedError()


class MaxMinLengthMixin:
    def __init__(self, *args, max_length=None, min_length=None, **kwargs):
        self.max_length = max_length
        self.min_length = min_length
        super().__init__(*args, **kwargs)
        if min_length is not None:
            self.validators.append(validators.MinLengthValidator(int(min_length)))
        if max_length is not None:
            self.validators.append(validators.MaxLengthValidator(int(max_length)))


class MaskMixin:
    def reportable(self, value):
        if self.hide:
            return "*****"
        return super(MaskMixin, self).reportable(value)


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

    def reportable(self, value):
        return f"[{super(ListMixin, self).reportable(value)}]"

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


class StringField(MaxMinLengthMixin, MaskMixin, Field):
    def from_str(self, s):
        return s

    def to_str(self, value):
        return value


class StringListField(ListMixin, StringField):
    pass


class IntegerField(MaskMixin, Field):
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
