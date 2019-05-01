import random as rnd
import string

import click

from .config import Config
from .exceptions import ValidationError, ConfigMissingError
from ..helpers import ask


@click.group()
def conf():
    pass


@conf.command()
def inspect():
    Config().inspect()


@conf.command()
@click.option("--name", "-n")
@click.option("--value", "-v")
@click.option('--no-validate', is_flag=True)
@click.option('--random', "-r", type=int)
@click.option("--stdin", "-s", is_flag=True)
@click.option("--file", "-f", type=click.File(mode="rb"))
def set(name, value, no_validate, random, stdin, file):
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
