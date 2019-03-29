import sys

import click

from .config import Config
from .exceptions import ValidationError, ConfigMissingError


@click.group()
def conf():
    pass


@conf.command()
def inspect():
    Config().inspect()


@conf.command()
@click.argument("name")
@click.argument("value")
def set(name, value):
    conf = Config()
    try:
        field, section = conf.field_map[name]
    except KeyError:
        raise click.ClickException(f"No such config: {name}")
    _value = field.from_storage(value.encode())
    try:
        field.set(_value)
    except ValidationError as e:
        raise click.ClickException(e)


@conf.command()
@click.argument("name")
def get(name):
    conf = Config()
    try:
        field, section = conf.field_map[name]
    except KeyError:
        raise click.ClickException(f"No such config: {name}")
    try:
        _value = field.get(root=True)
    except ValidationError as e:
        raise click.ClickException(e)
    except ConfigMissingError:
        raise click.ClickException("The config is not set and no default specified.")
    sys.stdout.write(field.to_storage(_value).decode())
