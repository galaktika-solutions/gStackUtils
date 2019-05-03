import click

from .config import Config
from .exceptions import ServiceNotFound


def start(service, conf=None):
    config = conf or Config()
    if hasattr(config.config_module, "STARTERS"):
        _starters = config.config_module.STARTERS
    else:
        _starters = config.default_config_module.STARTERS
    try:
        starter = _starters[service]
    except KeyError:
        raise ServiceNotFound()
    starter(config)


@click.command(name="start")
@click.argument("service")
def cli(service):
    try:
        start(service)
    except ServiceNotFound:
        raise click.ClickException(f"No starter function defined for service {service}")
