import os
import importlib
import inspect
import random as rnd
import string
import re

import click

from .helpers import path_check, ask
from .fields import ConfigField, SecretConfigField
from .exceptions import (
    DefaultUsedException,
    ConfigMissingError,
    ValidationError,
    PermissionDenied,
    ImproperlyConfigured
)


FLAGS = {
    "colors": {
        "OK": ("●", "green"),
        "DEF": ("○", "green"),
        "MISS": ("━", "red"),
        "INV": ("✖", "red"),
    },
    "simple": {
        "OK": (" ", None),
        "DEF": (".", None),
        "MISS": ("?", None),
        "INV": ("!", None),
    }
}


class Config:
    def __init__(
        self,
        config_module=None,
        root_mode=None,
    ):
        stat = os.stat(".")
        self.pu, self.pg = stat.st_uid, stat.st_gid  # project user & group
        self.is_dev = os.path.isdir(".git")
        # self.root_mode = (os.getuid() == 0) if root_mode is None else root_mode
        self.root_mode = os.getuid() == 0
        if root_mode and not self.root_mode:
            raise PermissionDenied(f"Can not set root mode, uid: {os.getuid()}")
        if root_mode is False:
            self.root_mode = False

        if not self.is_dev:
            path_check("d", "/host", 0, 0, 0o22)

        cm = (
            config_module or
            os.environ.get("GSTACK_CONFIG_MODULE") or
            "gstackutils.default_gstack_conf"
        )
        self.config_module = importlib.import_module(cm)
        self.default_config_module = importlib.import_module("gstackutils.default_gstack_conf")

        self.env_file_path = self.env("GSTACK_ENV_FILE", "/host/.env")
        self.secret_file_path = self.env("GSTACK_SECRET_FILE", "/host/.secret.env")
        self.secret_dir = self.env("GSTACK_SECRET_DIR", "/run/secrets")
        self.theme = self.env("GSTACK_THEME", "colors")

        path_check("f", self.env_file_path, self.pu, self.pg, 0o133, self.root_mode)
        path_check("f", self.secret_file_path, self.pu, self.pg, 0o177, self.root_mode)
        path_check("d", self.secret_dir, self.pu, self.pg, 0o22, self.root_mode)

        # mod = importlib.import_module(self.config_module)

        fields = []
        self.field_names = set()

        sections = [
            c for c in self.config_module.__dict__.values()
            if inspect.isclass(c) and issubclass(c, Section) and c != Section
        ]
        for S in sections:
            section_fields = [
                (field_name, field_instance)
                for field_name, field_instance in S.__dict__.items()
                if isinstance(field_instance, ConfigField)
            ]
            if not section_fields:
                continue

            section_instance = S(self)
            for field_name, field_instance in section_fields:
                if field_name in self.field_names:
                    raise ImproperlyConfigured(
                        f"Config '{field_name}' was defined multiple times."
                    )
                field_instance._setup_field(self, field_name)
                fields.append((field_name, field_instance, section_instance))
                self.field_names.add(field_name)

        self.fields = fields
        self.field_map = dict([(fn, (fi, si)) for fn, fi, si in self.fields])
        # instance._check_config()

    def env(self, name, default):
        if hasattr(self.config_module, name):
            return getattr(self.config_module, name)
        if hasattr(self.default_config_module, name):
            return getattr(self.default_config_module, name)
        return default

    def inspect(self):
        if not self.root_mode:
            raise PermissionDenied("This operation is allowed in root mode only.")
        info = {}
        for field_name, field_instance, section_instance in self.fields:
            try:
                value = field_instance.get(root=True, default_exception=True, validate=True)
                flag = "OK"
            except DefaultUsedException:
                value = field_instance.default
                flag = "DEF"
            except ConfigMissingError:
                value = ""
                flag = "MISS"
            except ValidationError:
                value = ""
                flag = "INV"
            if flag in ("OK", "DEF"):
                value = field_instance.to_human_readable(value)
            section_list = info.setdefault(section_instance.__class__.__name__, [])
            section_list.append((field_name, flag, value))

        # find the max length of config names
        max_name = max([len(x) for x in self.field_names])
        # max_val = max([len(x[2]) for v in info.values() for x in v])

        # output the result
        for k, v in info.items():
            click.secho(k, fg="yellow")
            for f in v:
                name = f[0]
                symbol, color = FLAGS[self.theme][f[1]]
                flag = click.style(symbol, fg=color)
                # flag = symbol
                value = f[2]
                click.echo(f"    {name:>{max_name}} {flag} {value}")

        regex = r"([^#^\s^=]+)="
        obsolete = []
        with open(self.env_file_path, "r") as f:
            for l in f.readlines():
                m = re.match(regex, l)
                if m:
                    confname = m.group(1)
                    try:
                        f = self.fieldbyname(confname)
                        if isinstance(f, SecretConfigField):
                            obsolete.append(confname)
                    except KeyError:
                        obsolete.append(confname)
        if obsolete:
            click.echo()
            click.echo("Obsolete environment config:")
            for n in obsolete:
                click.secho(f"    {n}", fg="red")

        obsolete = []
        with open(self.secret_file_path, "r") as f:
            for l in f.readlines():
                m = re.match(regex, l)
                if m:
                    confname = m.group(1)
                    try:
                        f = self.fieldbyname(confname)
                        if not isinstance(f, SecretConfigField):
                            obsolete.append(confname)
                    except KeyError:
                        obsolete.append(confname)
        if obsolete:
            click.echo()
            click.echo("Obsolete secret config:")
            for n in obsolete:
                click.secho(f"    {n}", fg="red")

    # def _obsolate(self, path):
    def fieldbyname(self, name):
        try:
            field, _ = self.field_map[name]
        except KeyError:
            raise KeyError(f"No such config: {name}")
        return field

    def get(self, name, root=None, to_stdout=False, default=None):
        root = self.root_mode if root is None else root
        if not self.root_mode and root:
            raise PermissionDenied("This operation is allowed in root mode only.")
        try:
            field, _ = self.field_map[name]
        except KeyError:
            if default:
                return default
            raise KeyError(f"No such config: {name}")
        if to_stdout:
            return field.to_stdout(field.get(root=root))
        return field.get(root=root)

    def set(self, name, value, no_validate=False, from_stdin=False):
        try:
            field, _ = self.field_map[name]
        except KeyError:
            raise KeyError(f"No such config: {name}")
        if from_stdin:
            value = field.from_stdin(value)
        field.set(value, no_validate=no_validate)

    def prepare(self, service):
        for name, [field, _] in self.field_map.items():
            try:
                field.prepare(service=service)
            except Exception as e:
                raise e.__class__(f"{name}: {e}")


class Section:
    def __init__(self, config):
        self.config = config


@click.group()
def conf():
    pass


@conf.command(name="inspect")
def inspect_cli():
    Config().inspect()


@conf.command(name="set")
@click.option("--name", "-n")
@click.option("--value", "-v")
@click.option('--no-validate', is_flag=True)
@click.option('--random', "-r", type=int)
@click.option("--stdin", "-s", is_flag=True)
@click.option("--file", "-f", type=click.File(mode="rb"))
def set_cli(name, value, no_validate, random, stdin, file):
    numinputoptions = len([o for o in [random, stdin, file] if o])
    if numinputoptions > 1:
        raise click.UsageError(
            "Only on input method can be used: random, stdin or file.",
        )
    config = Config()
    if not name:
        # we will ask for the variable, so no stdin allowed
        if stdin:
            raise click.BadOptionUsage(
                "stdin",
                "If name is not given, we can not read from STDIN.",
            )
        # ask for the name
        name = ask([f[0] for f in config.fields], prompt="Which config to set?")

    try:
        field = config.fieldbyname(name)
    except KeyError:
        raise click.ClickException(f"No such config: {name}")

    if value is None:
        if random:
            value = ''.join(
                rnd.choice(
                    string.ascii_letters + string.digits + string.punctuation
                ) for _ in range(random)
            )
        elif stdin:
            value = click.get_binary_stream("stdin").read()
        elif file:
            value = file.read()
        else:
            # value = input("Value: ").encode()
            value = click.prompt(
                "Value", hide_input=field.hide_input, confirmation_prompt=field.hide_input
            ).encode()
    else:
        value = value.encode()

    try:
        config.set(name, value, no_validate=no_validate, from_stdin=True)
    except ValidationError as e:
        arg = e.args[0]
        if isinstance(arg, str):
            arg = [arg]
        raise click.ClickException("/n".join([str(v) for v in arg]))


@conf.command()
@click.argument("name", required=False)
def get(name):
    config = Config()
    if name is None:
        name = ask([f[0] for f in config.fields], prompt="Which config to get?")
    try:
        value = config.get(name, to_stdout=True)
    except KeyError:
        raise click.ClickException(f"No such config: {name}")
    except ConfigMissingError:
        raise click.ClickException("The config is not set and no default specified.")
    except (FileNotFoundError, PermissionError):
        raise click.ClickException("Wrong permission or missing file.")
    click.echo(value, nl=False)


@conf.command()
@click.argument("name")
def delete(name):
    try:
        Config().set(name, None)
    except KeyError:
        raise click.ClickException(f"No such config: {name}")


@conf.command()
@click.argument("service")
def prepare(service):
    Config().prepare(service)
