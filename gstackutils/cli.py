import signal as sigmod

import click

from .conf.cli import conf
from .run import run


@click.group()
def cli():
    pass


cli.add_command(conf)


@cli.command(name="run")
@click.option('--user', '-u')
@click.option('--group', '-g')
@click.option('--silent', is_flag=True)
@click.option('--signal', '-s', default='SIGTERM')
@click.argument("cmd", nargs=-1, required=True)
def run_cmd(user, group, silent, signal, cmd):
    if user is not None:
        try:
            user = int(user)
        except ValueError:
            pass
    if group is not None:
        try:
            group = int(group)
        except ValueError:
            pass
    signal = signal.upper()
    if not signal.startswith('SIG'):
        raise click.ClickException(f"Signal not defined: {signal}")
    try:
        stopsignal = getattr(sigmod, signal)
    except AttributeError:
        raise click.ClickException(f"Signal not defined: {signal}")
    run(cmd, usr=user, grp=group, stopsignal=stopsignal, silent=silent)
