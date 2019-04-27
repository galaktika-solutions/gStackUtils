import click

from .conf.cli import conf
from .run import run_cli
from .db import cli as db_cli
from .cert import cert_cli
from .helpers import cli as helpers_cli


@click.group()
def cli():
    pass


cli.add_command(conf)
cli.add_command(db_cli)
cli.add_command(cert_cli)
cli.add_command(run_cli)
cli.add_command(helpers_cli)
