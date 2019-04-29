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
@click.argument("value", required=False)
@click.option('--no-validate', is_flag=True)
def set(name, value, no_validate):
    if value is None:
        value = click.get_binary_stream("stdin").read()
    else:
        value = value.encode()
    try:
        Config().set(name, value, no_validate=no_validate, from_stdin=True)
    except KeyError:
        raise click.ClickException(f"No such config: {name}")
    except ValidationError as e:
        arg = e.args[0]
        if isinstance(arg, str):
            arg = [arg]
        raise click.ClickException("/n".join([str(v) for v in arg]))


@conf.command()
@click.argument("name")
def get(name):
    try:
        value = Config().get(name, to_stdout=True)
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
