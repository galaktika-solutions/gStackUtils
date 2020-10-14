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
@click.option("-k", "--key")
@click.option("-j", "--json", is_flag=True)
def info(ctx, verbosity, key, json):
    c = ctx.obj["config"]
    try:
        info = c.info(key)
        # termout.print_info(c.info(key), verbosity)
    except exceptions.EncryptionKeyError as e:
        if key is None:
            for cnt in range(3):
                key = click.prompt("Enter the encryption key", hide_input=True, err=True)
                try:
                    info = c.info(key)
                    # termout.print_info(c.info(key), verbosity)
                except exceptions.EncryptionKeyError as e:
                    click.echo(e, err=True)
                else:
                    break
            else:
                return
        else:
            click.echo(e, err=True)
            return

    if json:
        from rich import print as pp
        pp(info)
    else:
        termout.print_info(info, verbosity)


@conf.command()
@click.argument("name")
@click.option("-v", "--value", type=str)
@click.option("-r", "--random", type=int)
@click.option("-b", "--binary-file", type=click.File("rb"))
@click.option("-f", "--text-file", type=click.File("r"))
@click.option("-p", "--prompt", is_flag=True)
@click.option('--validate/--no-validate', default=True)
@click.option("-k", "--key")
@click.pass_context
def set(ctx, name, value, random, binary_file, text_file, prompt, validate, key):
    """Store a config value in the associated storage file."""

    c = ctx.obj["config"]
    try:
        _, field = c.get_field(name)
    except exceptions.ConfigMissingError as e:
        raise click.ClickException(f"No such config: {e}")

    input_methods = (value, random, binary_file, text_file, prompt)
    if not any(input_methods):
        raise click.UsageError("No input method given", ctx=ctx)
    if len([x for x in input_methods if x]) > 1:
        raise click.UsageError("More input methods given", ctx=ctx)

    if field.encrypt:
        if key is not None:
            try:
                c.info(key=key, exclude=name)
            except exceptions.EncryptionKeyError as e:
                click.echo(e, err=True)
                return
        else:
            for cnt in range(3):
                key = click.prompt("Enter the encryption key", hide_input=True, err=True)
                try:
                    c.info(key=key, exclude=name)
                except exceptions.EncryptionKeyError as e:
                    click.echo(e, err=True)
                else:
                    break
            else:
                return

    if value:
        pass
    elif random:
        value = "".join(
            modrandom.choice(
                string.ascii_letters + string.digits + string.punctuation
            ) for _ in range(random)
        )
    elif binary_file:
        value = binary_file.read()
    elif text_file:
        value = text_file.read()
    elif prompt:
        value = click.prompt("Enter the config value", hide_input=field.hide)

    try:
        c.set(name, value, from_stream=True, validate=validate, key=key)
    except exceptions.ValidationError as e:
        raise click.ClickException(e)

@conf.command()
@click.argument("name")
@click.option("-k", "--key")
@click.pass_context
def retrieve(ctx, name, key):
    """Retrieve a configuration value from the storage file."""

    c = ctx.obj["config"]
    stream = None
    try:
        try:
            stream = c.retrieve(name, to_stream=True, validate=False, key=key)
        except exceptions.EncryptionKeyError as e:
            if key is None:
                for cnt in range(3):
                    key = click.prompt("Enter the encryption key", hide_input=True, err=True)
                    try:
                        stream = c.retrieve(name, to_stream=True, validate=False, key=key)
                    except exceptions.EncryptionKeyError as e:
                        click.echo(e, err=True)
                    else:
                        break
            else:
                click.echo(e, err=True)
    except exceptions.DefaultException as e:
        raise click.ClickException("Config value not found")
    except exceptions.ConfigNotSetError as e:
        raise click.ClickException(e)
    except exceptions.ConfigMissingError as e:
        raise click.ClickException(f"No such config: {e}")
    except ValueError as e:
        raise click.ClickException(e)

    if stream is not None:
        if isinstance(stream, str):
            print(stream, end="")
        else:
            sys.stdout.buffer.write(stream)


@conf.command()
@click.argument("name")
@click.option("-f", "--file", type=click.Path(file_okay=True))
@click.pass_context
def delete(ctx, name, file):
    c = ctx.obj["config"]
    c.delete(name, file)


@conf.command()
@click.pass_context
def remove_stale(ctx):
    c = ctx.obj["config"]
    c.remove_stale()


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
