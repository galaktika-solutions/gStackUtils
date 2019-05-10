import os
import importlib
import inspect
import random as rnd
import string
import re

import click

from .helpers import (
    path_check,
    ask,
)
from .fields import ConfigField
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
        use_default_config_module=True,
        root_mode=None,
    ):
        stat = os.stat(".")
        self.pu, self.pg = stat.st_uid, stat.st_gid  # project user & group
        self.is_dev = os.path.isdir(".git")
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
        if use_default_config_module:
            self.default_config_module = importlib.import_module("gstackutils.default_gstack_conf")
        else:
            self.default_config_module = None

        self.env_file_path = self.env("GSTACK_ENV_FILE", "/host/.env")
        self.secret_file_path = self.env("GSTACK_SECRET_FILE", "/host/.secret.env")
        self.secret_dir = self.env("GSTACK_SECRET_DIR", "/run/secrets")
        self.theme = self.env("GSTACK_THEME", "colors")

        path_check("f", self.env_file_path, self.pu, self.pg, 0o133, self.root_mode)
        path_check("f", self.secret_file_path, self.pu, self.pg, 0o177, self.root_mode)
        path_check("d", self.secret_dir, self.pu, self.pg, 0o22, self.root_mode)

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

    def env(self, name, default):
        if hasattr(self.config_module, name):
            return getattr(self.config_module, name)
        if self.default_config_module and hasattr(self.default_config_module, name):
            return getattr(self.default_config_module, name)
        return default

    def validate(self):
        if hasattr(self.config_module, "validate"):
            return getattr(self.config_module, "validate")(self)

    def inspect_config(self, name):
        if name not in self.field_map:
            raise KeyError(f"No such config: {name}")
        fi, si = self.field_map[name]
        if si.__class__.__doc__:
            click.echo(f"In section {si.__class__.__name__}: {si.__class__.__doc__.strip()}")
        else:
            click.echo(f"In section {si.__class__.__name__}")

        if fi.help_text:
            click.echo(f"{name}: {fi.help_text}")

        try:
            value = fi.get(root=True, default_exception=True, validate=True)
        except DefaultUsedException:
            value = fi.default
            click.echo(f"value: {fi.to_human_readable(value)} (uses default)")
        except ConfigMissingError:
            click.secho("Not set.", fg="red", bold=True)
        except ValidationError as e:
            for error in e.args[0]:
                click.secho(error, fg="red", bold=True)
        else:
            click.echo(f"value: {fi.to_human_readable(value)}")

    def inspect(self, delete_stale=False):
        if not self.root_mode:
            raise PermissionDenied("This operation is allowed in root mode only.")
        info = {}
        valid = True
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
            else:
                valid = False
                pass
            section_list = info.setdefault(section_instance, [])
            section_list.append((field_name, flag, value))

        # find the max length of config names
        max_name = max([len(x) for x in self.field_names])

        # output the result
        for k, v in info.items():
            click.secho(k.__class__.__name__, fg="yellow", bold=True, nl=False)
            if k.__class__.__doc__:
                click.echo(f" ({k.__class__.__doc__.strip()})")
            else:
                click.echo()
            click.echo()
            for f in v:
                name = f[0]
                symbol, color = FLAGS[self.theme][f[1]]
                flag = click.style(symbol, fg=color)
                value = f[2]
                click.echo(f"    {name:>{max_name}} {flag} {value}")
            click.echo()

        click.echo("Cross validation")
        click.echo()
        if valid:
            validation_errors = self.validate()
            if validation_errors:
                for ve in validation_errors:
                    click.secho(f"    {ve}", fg="red", bold=True)
            else:
                click.secho(f"    OK", fg="green", bold=True)
        else:
            click.secho(f"    Did not validate due to value errors.", fg="yellow", bold=True)
        click.echo()

        self.stale_list(False, delete_stale)
        self.stale_list(True, delete_stale)

    def stale_list(self, secret, delete_stale):
        regex = r"([^#^\s^=]+)="
        stale = []
        filepath = self.secret_file_path if secret else self.env_file_path
        with open(filepath, "r") as f:
            for l in f.readlines():
                m = re.match(regex, l)
                if m:
                    confname = m.group(1)
                    try:
                        f = self.fieldbyname(confname)
                        if f.secret != secret:
                            stale.append(confname)
                    except KeyError:
                        stale.append(confname)
        if not stale:
            return

        if delete_stale:
            for n in stale:
                f = ConfigField(secret=secret)
                f._setup_field(self, n)
                f.set_root(None)
        else:
            click.echo(f"Stale {'secret' if secret else 'environment'} config:")
            click.echo()
            for n in stale:
                click.secho(f"    {n}", fg="red", bold=True)
            click.echo()

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
            return field.to_bytes(field.get(root=root))
        return field.get(root=root)

    def set(self, name, value, no_validate=False, from_stdin=False):
        try:
            field, _ = self.field_map[name]
        except KeyError:
            raise KeyError(f"No such config: {name}")
        if from_stdin:
            value = field.to_python(value)
        field.set(value, no_validate=no_validate)

    def prepare(self, service):
        for name, [field, _] in self.field_map.items():
            field.prepare(service)


class Section:
    def __init__(self, config):
        self.config = config


@click.group()
def conf():
    pass


@conf.command(name="inspect")
@click.argument("name", required=False)
@click.option("--delete-stale", "-d", is_flag=True)
def inspect_cli(name, delete_stale):
    if name:
        Config().inspect_config(name)
    else:
        Config().inspect(delete_stale)


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
            "Only one input method can be used: random, stdin or file.",
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
                "Value", hide_input=field.secret, confirmation_prompt=field.secret
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


# @conf.command()
# @click.argument("service")
# def prepare(service):
#     Config().prepare(service)
