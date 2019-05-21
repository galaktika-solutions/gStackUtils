import click

from .config import Config
from .exceptions import ServiceNotFound


def get_starters(conf=None):
    config = conf or Config()
    if hasattr(config.config_module, "STARTERS"):
        return config.config_module.STARTERS
    else:
        return config.default_config_module.STARTERS


def start(service, conf=None):
    config = conf or Config()
    _starters = get_starters(config)
    try:
        starter = _starters[service]
    except KeyError:
        raise ServiceNotFound(f"Service not found: {service}")
    starter(config)


@click.command(name="start")
@click.argument("service")
def cli(service):
    try:
        start(service)
    except ServiceNotFound:
        raise click.ClickException(f"No starter function defined for service {service}")
