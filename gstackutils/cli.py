import click
import random as modrandom
import sys
import string

from . import conf as modconf


@click.group()
def cli():
    pass


@cli.group()
def conf():
    pass


@conf.command()
def info():
    pass


@conf.command()
@click.argument("name")
@click.option("-v", "--value", type=str)
@click.option("-r", "--random", type=int)
@click.option("-b", "--binary-file", type=click.File("rb"))
@click.option("-f", "--text-file", type=click.File("r"))
def set(name, value, random, binary_file, text_file):
    c = modconf.Config("tests.fixtures.config_module")
    if value:
        c.set(name, value, from_stream=True, validate=True)
    if random:
        value = ''.join(
            modrandom.choice(
                string.ascii_letters + string.digits + string.punctuation
            ) for _ in range(random)
        )
        c.set(name, value, from_stream=True, validate=True)
    if binary_file:
        c.set(name, binary_file.read(), from_stream=True, validate=True)
    if text_file:
        c.set(name, text_file.read(), from_stream=True, validate=True)


@conf.command()
@click.argument("name")
def get(name):
    c = modconf.Config("tests.fixtures.config_module")
    stream = c.get_from_file(name, to_stream=True, validate=False)
    if isinstance(stream, str):
        print(stream, end="")
    else:
        sys.stdout.buffer.write(stream)
