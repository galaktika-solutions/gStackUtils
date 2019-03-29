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
    ValidationError
)


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
        self.root_mode = (os.getuid() == 0) if root_mode is None else root_mode

        if not self.is_dev:
            path_check("d", "/host", 0, 0, 0o22)

        def fb(var, env, default):
            return var if var is not None else os.environ.get(env, default)

        self.config_module = fb(config_module, "GSTACK_CONFIG_MODULE", "gstack_conf")
        self.env_file_path = fb(env_file_path, "GSTACK_ENV_FILE", "/host/.env")
        self.secret_file_path = fb(secret_file_path, "GSTACK_SECRET_FILE", "/host/.secret.env")
        self.secret_dir = fb(secret_dir, "GSTACK_SECRET_DIR", "/run/secrets")

        path_check("f", self.env_file_path, self.pu, self.pg, 0o133, self.root_mode)
        path_check("f", self.secret_file_path, self.pu, self.pg, 0o177, self.root_mode)
        path_check("d", self.secret_dir, self.pu, self.pg, 0o22, self.root_mode)

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


class Section:
    def __init__(self, config):
        self.config = config

    # def get_name(self) -> str:
    #     return self.name if self.name else "Section {}".format(self._section_counter)
    #
    # def __setitem__(self, name: str, value: Any) -> None:
    #     if name not in self.fields:
    #         raise KeyError("No such config: {}".format(name))
    #     self.fields[name].set_root(value)
    #
    # def _validate(self) -> None:
    #     validated_data = dict((f.name, f.get_root()) for f in self.fields.values())
    #     self.validate(validated_data)
    #
    # def validate(self, validated_data: Dict[str, Any]) -> None:
    #     pass
    #
    # def configure(self) -> None:
    #     pass
