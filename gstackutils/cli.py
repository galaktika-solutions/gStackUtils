import click
import random as modrandom
import sys
import string

from . import conf as modconf
from . import cert as modcert
from . import exceptions
from . import termout


@click.group()
def cli():
    pass


@cli.group()
@click.option("-c", "--config-module")
@click.pass_context
def conf(ctx, config_module):
    ctx.ensure_object(dict)
    try:
        ctx.obj['config'] = modconf.Config(config_module)
    except ModuleNotFoundError as e:
        raise click.ClickException(e)


@conf.command()
@click.pass_context
@click.option('-v', '--verbosity', count=True)
def info(ctx, verbosity):
    c = ctx.obj["config"]
    termout.print_info(c.info(), verbosity)
    # from rich import print as pp
    # pp(c.info())


@conf.command()
@click.argument("name")
@click.option("-v", "--value", type=str)
@click.option("-r", "--random", type=int)
@click.option("-b", "--binary-file", type=click.File("rb"))
@click.option("-f", "--text-file", type=click.File("r"))
@click.option('--validate/--no-validate', default=True)
@click.pass_context
def set(ctx, name, value, random, binary_file, text_file, validate):
    """Store a config value in the associated storage file."""

    c = ctx.obj["config"]
    try:
        _, _ = c.get_field(name)
    except exceptions.ConfigMissingError as e:
        raise click.ClickException(f"No such config: {e}")

    input_methods = (value, random, binary_file, text_file)
    if not any(input_methods):
        raise click.UsageError("No input method given", ctx=ctx)
    if len([x for x in input_methods if x]) > 1:
        raise click.UsageError("More input methods given", ctx=ctx)

    try:
        if value:
            c.set(name, value, from_stream=True, validate=validate)
        if random:
            value = ''.join(
                modrandom.choice(
                    string.ascii_letters + string.digits + string.punctuation
                ) for _ in range(random)
            )
            c.set(name, value, from_stream=True, validate=validate)
        if binary_file:
            c.set(name, binary_file.read(), from_stream=True, validate=validate)
        if text_file:
            c.set(name, text_file.read(), from_stream=True, validate=validate)
    except exceptions.ValidationError as e:
        raise click.ClickException(e)

@conf.command()
@click.argument("name")
@click.pass_context
def retrieve(ctx, name):
    """Retrieve a configuration value from the storage file."""

    c = ctx.obj["config"]
    try:
        stream = c.retrieve(name, to_stream=True, validate=False)
    except exceptions.DefaultException as e:
        raise click.ClickException("Config value not found")
    except exceptions.ConfigNotSetError as e:
        raise click.ClickException(e)
    except exceptions.ConfigMissingError as e:
        raise click.ClickException(f"No such config: {e}")
    except ValueError as e:
        raise click.ClickException(e)
    if isinstance(stream, str):
        print(stream, end="")
    else:
        sys.stdout.buffer.write(stream)


@cli.command()
@click.option("-n", "--name", multiple=True, required=True)
@click.option("-i", "--ip", multiple=True)
@click.option("--cakey", type=click.File(mode="rb"))
@click.option("--cacert", type=click.File(mode="rb"))
def cert(name, ip, cakey, cacert):
    try:
        modcert.generate(name, ip, cakey, cacert)
    except exceptions.InvalidUsage as e:
        raise click.UsageError(e)
    except ValueError as e:
        raise click.ClickException(e)
