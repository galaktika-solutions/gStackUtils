import click

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
def set(name):
    c = modconf.Config("tests.fixtures.config_module")
    c.set(name, "hello")
