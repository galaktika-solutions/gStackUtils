import importlib
import pathlib
import inspect
import re

from . import exceptions
from . import fields


def format_docstring(s):
    s = s or ""
    info = [l.strip() for l in s.splitlines()]
    return "\n".join(info).strip()


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

    def __init__(self, config_module=None):
        # cli will pass config_module as None by default
        config_module = config_module or "gstack_conf"
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

    def get_field(self, name):
        try:
            section = self.fields[name]
            field = section.fields[name]
        except KeyError as e:
            raise exceptions.ConfigMissingError(name)
        else:
            return section, field

    def retrieve(self, name, to_stream=False, validate=True):
        _, field = self.get_field(name)

        try:
            with open(field.file.path, "r") as f:
                lines = [l for l in f.readlines() if l]
        except FileNotFoundError:
            lines = []

        for l in lines:
            m = self.ENV_REGEX.match(l)
            if m and m.group(1) == name:
                value = field.from_storage(m.group(2))
                if validate:
                    field.validate(value)
                if to_stream:
                    return field.to_stream(value)
                return value
        if field.default is None:
            raise exceptions.ConfigNotSetError(f"Config not set: {name}")
        raise exceptions.DefaultException(field.default)

    def set(self, name, value, from_stream=False, validate=True):
        _, field = self.get_field(name)
        self.ensure_file(field.file)

        if value is not None:
            if from_stream:
                value = field.from_stream(value)
            if validate:
                field.validate(value)
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

    def provide(self, service, name=None, validate=True):
        pass

    def use(self, service, name):
        pass

    def info(self, verbosity=0):
        ret = []
        for s in self.sections:
            section_info = {}
            ret.append(section_info)
            section_info["section"] = s.__class__.__name__
            section_info["help_text"] = format_docstring(s.__class__.__doc__)
            section_info["config_items"] = config_items = []
            # cons.print(s.info(verbosity))
            for fn, fi in s.fields.items():
                config_info = {}
                config_items.append(config_info)
                config_info["field"] = fn
                config_info["help_text"] = fi.help_text
                config_info["errors"] = []
                try:
                    value = self.retrieve(fn, validate=False)
                except exceptions.DefaultException as e:
                    config_info["reportable"] = fi.reportable(e.default)
                    config_info["status"] = "DEFAULT"
                except exceptions.ConfigNotSetError as e:
                    config_info["reportable"] = ""
                    config_info["status"] = "NOT SET"
                except ValueError as e:
                    config_info["reportable"] = ""
                    config_info["status"] = "ILLEGAL"
                else:
                    try:
                        fi.validate(value)
                    except exceptions.ValidationError as e:
                        config_info["reportable"] = fi.reportable(value)
                        config_info["status"] = "INVALID"
                        config_info["errors"] = e.messages
                    else:
                        config_info["reportable"] = fi.reportable(value)
                        config_info["status"] = "OK"
        return ret

    def remove_stale(self):
        pass
