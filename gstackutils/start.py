import importlib

import click

from .conf import Config
from .db import ensure
from .run import run


def start_postgres(conf):
    ensure(conf=conf)
    run(["postgres"], usr="postgres", exit=True)


STARTERS = {
    "postgres": start_postgres,
}


def start(service, conf=None):
    config = conf or Config()
    config_module = config.config_module
    mod = importlib.import_module(config_module)
    if hasattr(mod, "starters"):
        _starters = mod.STARTERS
    else:
        _starters = {}
    starter = _starters.get(service, STARTERS[service])
    starter(config)


@click.command(name="start")
@click.argument("service")
def cli(service):
    try:
        start(service)
    except KeyError:
        raise click.ClickException(f"Service does not exist: {service}")
