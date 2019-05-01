import importlib

import click

from .config import Config
from .db import ensure, wait_for_db
from .run import run
from .exceptions import ServiceNotFound


def start_postgres(conf):
    ensure(conf=conf)
    run(["postgres"], usr="postgres", exit=True)


def start_django(conf):
    conf.prepare("django")
    wait_for_db(conf=conf)
    run(["django-admin", "runserver", "0.0.0.0:8000"], usr="django", stopsignal="SIGINT", exit=True)


STARTERS = {
    "postgres": start_postgres,
    "django": start_django,
}


def start(service, conf=None):
    config = conf or Config()
    config_module = config.config_module
    mod = importlib.import_module(config_module)
    if hasattr(mod, "starters"):
        _starters = mod.STARTERS
    else:
        _starters = {}
    try:
        starter = _starters.get(service, STARTERS[service])
    except KeyError:
        raise ServiceNotFound()
    starter(config)


@click.command(name="start")
@click.argument("service")
def cli(service):
    try:
        start(service)
    except ServiceNotFound:
        raise click.ClickException(f"Service does not exist: {service}")
