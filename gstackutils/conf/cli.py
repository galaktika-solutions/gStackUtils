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
@click.option('--no-validate', is_flag=True)
def set(name, value, no_validate):
    try:
        Config().set(name, value, no_validate=no_validate, from_string=True)
    except KeyError:
        raise click.ClickException(f"No such config: {name}")
    except ValidationError as e:
        raise click.ClickException(e)


@conf.command()
@click.argument("name")
def get(name):
    try:
        value = Config().get(name, root=True, as_string=True)
    except KeyError:
        raise click.ClickException(f"No such config: {name}")
    except ValidationError as e:
        raise click.ClickException(e)
    except ConfigMissingError:
        raise click.ClickException("The config is not set and no default specified.")
    sys.stdout.write(value)


@conf.command()
@click.argument("service")
def prepare(service):
    Config().prepare(service)
