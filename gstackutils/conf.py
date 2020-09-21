import importlib
import pathlib
import inspect
import re

from . import exceptions
from . import fields


class File:
    def __init__(self, path):
        self.path = pathlib.Path(path)


class Section:
    def __init__(self):
        self.fields = dict([
            (field_name, field_instance)
            for field_name, field_instance in self.__class__.__dict__.items()
            if isinstance(field_instance, fields.Field)
        ])


class Service:
    def __init__(self, name, path="", user=None, group=None, mode=None, environ=False):
        self.name = name
        self.path = path
        self.user = user
        self.group = group
        self.mode = mode
        self.environ = environ


class Config:
    ENV_REGEX = re.compile(r"^\s*([^#].*?)=(.*)$")

    def __init__(self, config_module):
        self.config_module = importlib.import_module(config_module)

        self.sections = [
            s() for s in self.config_module.__dict__.values()
            if inspect.isclass(s) and issubclass(s, Section) and s != Section
        ]

        self.fields = {}
        for s in self.sections:
            for fn in s.fields:
                self.fields[fn] = s

    def ensure_file(self, file):
        if not file.path.is_file():
            open(file.path, "a").close()

    def set(self, name, value):
        section = self.fields[name]
        field = section.fields[name]
        self.ensure_file(field.file)

        if value is not None:
            # fi.validate(value)  # do we want to validate here
            storagestr = field.to_storage(value)
            actualline = f"{name}={storagestr}\n"

        newlines = []
        done = False
        with open(field.file.path, "r") as f:
            lines = [l for l in f.readlines() if l]
        for l in lines:
            if done:  # if we are done, just append remaining lines
                newlines.append(l)
                continue
            m = self.ENV_REGEX.match(l)
            if m and m.group(1) == name:
                done = True
                if value is not None:  # if we delete, skip
                    newlines.append(actualline)
            else:
                newlines.append(l)
        if not done and value is not None:
            newlines.append(actualline)
        with open(field.file.path, "w") as f:
            f.writelines(newlines)
