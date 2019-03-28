import click

from .config import Config


@click.group()
def conf():
    pass


@conf.command()
def inspect():
    Config().inspect()
