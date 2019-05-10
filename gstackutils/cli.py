# import os
# import importlib

import click

from .config import conf
from .run import run_cli
from .db import cli as db_cli
from .cert import cert_cli
from .helpers import cli as helpers_cli
from .start import cli as start_cli
from .backup import backup_cli, restore_cli


@click.group()
def cli():
    pass


cli.add_command(conf)
cli.add_command(db_cli)
cli.add_command(cert_cli)
cli.add_command(run_cli)
cli.add_command(helpers_cli)
cli.add_command(start_cli)
cli.add_command(backup_cli)
cli.add_command(restore_cli)


# config_module = os.environ.get("GSTACK_CONFIG_MODULE", "config.gstack_conf")
# mod = importlib.import_module(config_module)
#
# if hasattr(mod, "backup_cli"):
#     cli.add_command(mod.backup_cli)
# else:
#     cli.add_command(backup_cli)
#
# if hasattr(mod, "restore_cli"):
#     cli.add_command(mod.restore_cli)
# else:
#     cli.add_command(restore_cli)
