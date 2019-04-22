import os
import importlib
import inspect

import click

from ..helpers import path_check
from .field import ConfigField
from ..exceptions import ImproperlyConfigured
from .exceptions import (
    DefaultUsedException,
    ConfigMissingError,
    ValidationError,
    PermissionDenied
)
from ..helpers import env


FLAGS = {
    # "OK": ("●", "green"),
    # "DEF": ("○", "green"),
    # "MISS": ("━", "red"),
    # "INV": ("✖", "red"),
    "OK": (" ", "green"),
    "DEF": (".", "green"),
    "MISS": ("?", "red"),
    "INV": ("!", "red"),
}


class Config:
    def __init__(
        self,
        config_module=None,
        env_file_path=None,
        secret_file_path=None,
        secret_dir=None,
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

        self.config_module = env(config_module, "GSTACK_CONFIG_MODULE", "config.gstack_conf")
        self.env_file_path = env(env_file_path, "GSTACK_ENV_FILE", "/host/.env")
        self.secret_file_path = env(secret_file_path, "GSTACK_SECRET_FILE", "/host/.secret.env")
        self.secret_dir = env(secret_dir, "GSTACK_SECRET_DIR", "/run/secrets")

        path_check("f", self.env_file_path, self.pu, self.pg, 0o133, self.root_mode)
        path_check("f", self.secret_file_path, self.pu, self.pg, 0o177, self.root_mode)
        path_check("d", self.secret_dir, self.pu, self.pg, 0o22, self.root_mode)

        # print("***", self.config_module)
        mod = importlib.import_module(self.config_module)

        fields = []
        self.field_names = set()

        sections = [
            c for c in mod.__dict__.values()
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
                field_instance.setup_field(self, field_name)
                fields.append((field_name, field_instance, section_instance))
                self.field_names.add(field_name)

        self.fields = fields
        self.field_map = dict([(fn, (fi, si)) for fn, fi, si in self.fields])
        # instance._check_config()

    def inspect(self):
        if not self.root_mode:
            raise PermissionDenied("This operation is allowed in root mode only.")
        info = {}
        for field_name, field_instance, section_instance in self.fields:
            try:
                value = field_instance.get(root=True, default_exception=True)
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
                value = field_instance.human_readable(value)
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
                symbol, color = FLAGS[f[1]]
                # flag = click.style(symbol, fg=color)
                flag = symbol
                value = f[2]
                click.echo(f"    {name:>{max_name}} {flag} {value}")

    def get(self, name, root=None, as_string=False):
        root = self.root_mode if root is None else root
        if not self.root_mode and root:
            raise PermissionDenied("This operation is allowed in root mode only.")
        try:
            field, _ = self.field_map[name]
        except KeyError:
            raise KeyError(f"No such config: {name}")
        if as_string:
            return field.to_storage(field.get(root=root)).decode()
        return field.get(root=root)

    def set(self, name, value, from_string=False, no_validate=False):
        try:
            field, _ = self.field_map[name]
        except KeyError:
            raise KeyError(f"No such config: {name}")
        if from_string:
            value = field.from_storage(value.encode())
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
