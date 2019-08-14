import os
import re
import importlib
import inspect
import click

from . import fields
from . import exceptions
from . import utils


FLAGS = {
    "OK": "",
    "DEF": ".",
    "MISS": "-",
    "INV": "!",
}

VARIABLES = {
    "GSTACK_ENV_FILE": "/host/.env",
    "GSTACK_SECRET_FILE": "/host/.secret.env",
    "GSTACK_SECRET_DIR": "/run/secrets/",
}


class Command:
    def __init__(self, parser):
        self.parser = parser
        if parser is not None:
            self.arguments(parser)

    def arguments(self, parser):
        pass

    def cmd(self, args):
        pass


class Section:
    def __init__(self, config):
        self.config = config


class Service:
    def __init__(self, **kwargs):
        self.fields = {}
        for field_name, _ugm in kwargs.items():
            if isinstance(_ugm, int) or isinstance(_ugm, str):
                ugm = {"usr": _ugm, "grp": _ugm, "mode": 0o400}
            elif isinstance(_ugm, (tuple, list)):
                if len(_ugm) == 0:
                    ugm = {"usr": 0, "grp": 0, "mode": 0o400}
                elif len(_ugm) == 1:
                    ugm = {"usr": _ugm[0], "grp": _ugm[0], "mode": 0o400}
                elif len(_ugm) == 2:
                    ugm = {"usr": _ugm[0], "grp": _ugm[1], "mode": 0o400}
                else:
                    ugm = {"usr": _ugm[0], "grp": _ugm[1], "mode": _ugm[2]}
            elif isinstance(_ugm, dict):
                ugm = {}
                for k in ["usr", "grp", "mode"]:
                    if k in _ugm:
                        ugm[k] = _ugm[k]
                u = ugm.setdefault("usr", 0)
                ugm.setdefault("grp", u)
                ugm.setdefault("mode", 0o400)
            else:
                raise exceptions.ImproperlyConfigured(
                    f"Invalid service definition for field {field_name}. "
                    "Should be int, tuple, list or dict."
                )
            self.fields[field_name] = ugm


class Config:
    ENV_REGEX = re.compile(r"^\s*([^#].*?)=(.*)$")

    def __init__(self, config_module=None, root_mode=None):
        config_module = config_module or os.environ.get("GSTACK_CONFIG_MODULE")
        self.config_module_var = config_module
        self.config_module = importlib.import_module(config_module)

        for var, default in VARIABLES.items():
            setattr(self, var, self._get_meta(var, default))

        stat = os.stat("/host/")
        self.pu, self.pg = stat.st_uid, stat.st_gid  # project user & group
        self.is_dev = os.path.isdir("/host/.git")
        self.root_mode = os.getuid() == 0
        if root_mode and not self.root_mode:
            raise exceptions.PermissionDenied(f"Can not set root mode, uid: {os.getuid()}")
        if root_mode is False:
            self.root_mode = False

        if not self.is_dev:
            utils.path_check("/host/", usr=0, grp=0, mode=0o755, fix=False)
        utils.path_check(
            self.GSTACK_ENV_FILE, usr=self.pu, grp=self.pg, mode=0o644, fix=self.root_mode
        )
        utils.path_check(
            self.GSTACK_SECRET_FILE, usr=self.pu, grp=self.pg, mode=0o600, fix=self.root_mode
        )
        utils.path_check(
            self.GSTACK_SECRET_DIR, usr=self.pu, grp=self.pg, mode=0o755, fix=self.root_mode
        )

        self.fields = []
        self.field_names = set()
        self.services = []

        sections = [
            c for c in self.config_module.__dict__.values()
            if inspect.isclass(c) and issubclass(c, Section) and c != Section
        ]

        for s in sections:
            self._process_section(s)

        self.field_map = dict([(fn, (fi, si)) for fn, fi, si in self.fields])

    def _root_mode_needed(self):
        if not self.root_mode:
            raise exceptions.PermissionDenied("This operation is only allowed in root mode")

    def _get_meta(self, name, default):
        try:
            return getattr(self.config_module, name)
        except AttributeError:
            return default

    def get_field(self, name):
        fi, _ = self.field_map.get(name, (None, None))
        if not fi:
            raise KeyError(f"No such field: {name}")
        return fi

    def get(self, name, default_exception=False, validate=False, stream=False):
        value = self._get(name, default_exception)

        fi = self.get_field(name)
        if validate:
            fi.validate(value)
        return fi.to_stream(value) if stream else value

    def _get(self, name, default_exception=False):
        fi = self.get_field(name)
        if self.root_mode:
            fn = self.GSTACK_SECRET_FILE if fi.secret else self.GSTACK_ENV_FILE
            try:
                with open(fn, "r") as f:
                    for l in f.readlines():
                        m = self.ENV_REGEX.match(l)
                        if m and m.group(1) == name:
                            return fi.from_storage(m.group(2))
            except (FileNotFoundError, PermissionError):
                raise exceptions.ConfigMissingError(f"Field could not be accessed: {name}")
        else:
            if not fi.secret:
                env = os.environ.get(name)
                if env is not None:
                    return fi.from_storage(env)
            else:
                fn = os.path.join(self.GSTACK_SECRET_DIR, name)
                mode = "rb" if fi.binary else "r"
                try:
                    with open(fn, mode) as f:
                        return fi.from_stream(f.read())
                except PermissionError:
                    raise exceptions.ConfigMissingError(f"Field could not be accessed: {name}")
                except FileNotFoundError:
                    pass
        if fi.default is not None:
            if isinstance(fi.default, fields.Field):
                ret = self._get(fi.default.name)
            elif callable(fi.default):
                ret = fi.default(self)
            else:
                ret = fi.default
            if default_exception:
                raise exceptions.DefaultUsedException()
            return ret
        raise exceptions.ConfigMissingError(f"Field not set: {name}")

    def set(self, name, value, stream=False):
        self._root_mode_needed()
        fi = self.get_field(name)
        self._set(name, fi, value, stream)

    def _set(self, name, fi, value, stream=False):
        fn = self.GSTACK_SECRET_FILE if fi.secret else self.GSTACK_ENV_FILE
        if value is not None:
            if stream:
                value = fi.from_stream(value)
            fi.validate(value)
            storagestr = fi.to_storage(value)
            actualline = f"{name}={storagestr}\n"

        newlines = []
        done = False
        with open(fn, "r") as f:
            lines = [l for l in f.readlines() if l]
        for l in lines:
            if done:  # if we are done, just append remaining lines
                newlines.append(l)
                continue
            m = self.ENV_REGEX.match(l)
            if m and m.group(1) == name:
                done = True
                if value is not None:  # if we delete, leave this line alone
                    newlines.append(actualline)
            else:
                newlines.append(l)
        if not done and value is not None:
            newlines.append(actualline)
        with open(fn, "w") as f:
            f.writelines(newlines)

    def _process_section(self, sectionclass):
        section_instance = sectionclass(self)
        section_name = sectionclass.__name__
        section_fields = [
            (field_name, field_instance)
            for field_name, field_instance in sectionclass.__dict__.items()
            if isinstance(field_instance, fields.Field)
        ]
        field_map = dict(section_fields)

        if not section_fields:
            return

        for field_name, field_instance in section_fields:
            if field_name in self.field_names:
                raise exceptions.ImproperlyConfigured(
                    f"Field '{field_name}' was defined multiple times."
                )
            self.fields.append((field_name, field_instance, section_instance))
            self.field_names.add(field_name)
            field_instance.name = field_name

        services = [
            (service_name, service_instance)
            for service_name, service_instance in sectionclass.__dict__.items()
            if isinstance(service_instance, Service)
        ]
        self.services += [(sn, si, section_instance) for sn, si in services]

        service_fields = set([f for n, s in services for f in s.fields])

        # is there a service that refers to a field that is not defined?
        for sn, si in services:
            for fn in si.fields:
                if fn not in self.field_names:
                    raise exceptions.ImproperlyConfigured(
                        f"Field `{fn}` refered by service `{sn}` in "
                        f"section {section_name} does not exist."
                    )
                if not field_map[fn].secret:
                    raise exceptions.ImproperlyConfigured(
                        f"Field `{fn}` refered by service `{sn}` in "
                        f"section {section_name} is not a secret."
                    )

        # is there a secret field that is not defined by any service?
        for secret_field in [n for n, i in section_fields if i.secret]:
            if secret_field not in service_fields:
                raise exceptions.ImproperlyConfigured(
                    f"Secret field `{secret_field}` in section `{section_name}` is "
                    "not used by any service."
                )

    def validate(self):
        self._root_mode_needed()
        errors = {}
        for field_name, field_instance, section_instance in self.fields:
            try:
                self.get(field_name, validate=True)
            except exceptions.ValidationError as e:
                errors.setdefault(field_name, []).append(e)
            except ValueError as e:
                errors.setdefault(field_name, []).append(
                    exceptions.ValidationError(str(e))
                )
        if not errors and hasattr(self.config_module, "validate"):
            try:
                getattr(self.config_module, "validate")(self)
            except exceptions.ValidationError as e:
                errors[exceptions.NON_FIELD_ERRORS] = e.error_list
        if errors:
            raise exceptions.ValidationError(errors)

    def inspect(self, develop=False):
        self._root_mode_needed()
        if develop:
            click.echo(f"GSTACK_CONFIG_MODULE = {self.config_module_var}")
            for var in VARIABLES:
                click.echo(f"{var} = {getattr(self, var)}")
            click.echo()

        info = {}
        valid = True
        for field_name, field_instance, section_instance in self.fields:
            try:
                value = self.get(field_name, default_exception=True, validate=True)
                flag = "OK"
            except exceptions.DefaultUsedException:
                value = self.get(field_name)
                flag = "DEF"
            except exceptions.ConfigMissingError:
                value = ""
                flag = "MISS"
                valid = False
            except exceptions.ValidationError as e:
                value = e.messages
                flag = "INV"
                valid = False
            except ValueError as e:
                value = str(e)
                flag = "INV"
                valid = False
            if flag in ("OK", "DEF"):
                value = field_instance.reportable(value)
            section_list = info.setdefault(section_instance, [])
            section_list.append((field_name, FLAGS[flag], value))

        # find the max length of config names
        max_name = max([len(x) for x in self.field_names])

        # output the result
        for k, v in info.items():
            click.secho(k.__class__.__name__, fg="yellow", bold=True)
            # if k.__class__.__doc__:
            #     click.echo(inspect.getdoc(k))
            for f in v:
                if f[1] != "INV":
                    click.echo(f"    {f[0]:>{max_name}} {f[1]:>1} {f[2]}")
                else:
                    click.echo(f"    {f[0]:>{max_name}} {f[1]:>1} {f[2][0]}")
                    for message in f[2][1:]:
                        click.echo(f"    {'':>{max_name}} {'':>1} {message}")

        if valid and hasattr(self.config_module, "validate"):
            try:
                getattr(self.config_module, "validate")(self)
            except exceptions.ValidationError as e:
                click.secho("Validation errors:", fg="red", bold=True)
                for msg in e.messages:
                    click.echo(f"    {msg}")
            else:
                click.secho("Validation OK", fg="green", bold=True)

        stale = self.stale(False)
        if stale:
            click.echo()
            click.secho("Stale environment config:", fg="yellow", bold=True)
            for n in stale:
                click.secho(f"    {n}", fg="red", bold=True)
        stale = self.stale(True)
        if stale:
            click.echo()
            click.secho("Stale secret config:", fg="yellow", bold=True)
            for n in stale:
                click.secho(f"    {n}", fg="red", bold=True)

    def delete_stale(self):
        self._root_mode_needed()
        for name in self.stale(False):
            fi = fields.Field(secret=False)
            self._set(name, fi, None)
        for name in self.stale(True):
            fi = fields.Field(secret=True)
            self._set(name, fi, None)

    def stale(self, secret):
        regex = r"([^#^\s^=]+)="
        stale = []
        filepath = self.GSTACK_SECRET_FILE if secret else self.GSTACK_ENV_FILE
        with open(filepath, "r") as f:
            for l in f.readlines():
                m = re.match(regex, l)
                if m:
                    confname = m.group(1)
                    try:
                        f = self.get_field(confname)
                        if f.secret != secret:
                            stale.append(confname)
                    except KeyError:
                        stale.append(confname)
        return stale

    def prepare(self, service):
        self._root_mode_needed()
        for si in [x[1] for x in self.services if x[0] == service]:
            for field_name, ugm in si.fields.items():
                fi = self.get_field(field_name)
                fn = os.path.join(self.GSTACK_SECRET_DIR, field_name)
                mode = "wb" if fi.binary else "w"
                with open(fn, mode) as f:
                    f.write(self.get(field_name, stream=True))
                utils.path_check(
                    fn, usr=ugm["usr"], grp=ugm["grp"], mode=ugm["mode"],
                    fix=True, allow_stricter=False
                )
