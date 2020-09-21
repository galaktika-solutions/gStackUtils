import base64


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
        raise NotImplementedError()

    def to_stream(self, value):
        raise NotImplementedError()

    def from_storage(self, storage_str):
        stream = base64.b64decode(storage_str)
        return self.from_stream(stream)

    def to_storage(self, value):
        stream = self.to_stream(value)
        return base64.b64encode(
            stream if isinstance(stream, bytes) else stream.encode()
        ).decode()

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


class MaskMixin:
    def reportable(self, value):
        if self.hide:
            return "*****"
        return super(MaskMixin, self).reportable(value)


class ListMixin:
    def __init__(self, *args, separator=",", **kwargs):
        assert not self.binary, "ListMixin can not be used on a binary field."
        self.separator = separator
        super(ListMixin, self).__init__(*args, **kwargs)

    def from_stream(self, s):
        return [super(ListMixin, self).from_stream(e) for e in s.split(self.separator)]

    def to_stream(self, value):
        return self.separator.join([super(ListMixin, self).to_stream(e) for e in value])

    def reportable(self, value):
        return f"[{super(ListMixin, self).reportable(value)}]"


class StringField(MaxMinLengthMixin, MaskMixin, Field):
    def from_stream(self, s):
        return s

    def to_stream(self, value):
        return value


class StringListField(ListMixin, StringField):
    pass
