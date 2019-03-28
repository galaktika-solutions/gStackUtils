import click

from .conf.cli import conf


@click.group()
def cli():
    pass


cli.add_command(conf)
