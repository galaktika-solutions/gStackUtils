import argparse
import sys
import random as rnd
import string
import os
import signal

import click

from . import config, helpers, exceptions, db, validators, cert, run, start


class FileType(argparse.FileType):
    """STDIN or STDOUT habdles bytes when opened in binary mode"""

    def __call__(self, s):
        if s == '-':
            if 'r' in self._mode:
                if 'b' in self._mode:
                    return sys.stdin.buffer
                return sys.stdin
            elif 'w' in self._mode:
                if 'b' in self._mode:
                    return sys.stdout.buffer
                return sys.stdout
            else:
                super().__call__(s)
        super().__call__(s)


def config_inspect(args, parser):
    try:
        args.conf.inspect(args)
    except KeyError:
        parser.error(f"no such config: {args.name}")


def config_set(args, parser):
    if not args.conf.root_mode:
        parser.error("must be root to set config")
    if not args.name:
        # we will ask for the variable, so no stdin allowed
        if args.file == sys.stdin.buffer:
            parser.error("if name is not given, we can not read from STDIN")
        # ask for the name
        name = helpers.ask([f[0] for f in args.conf.fields], prompt="Which config to set?")
    else:
        name = args.name

    try:
        field = args.conf.fieldbyname(name)
    except KeyError:
        parser.error(f"no such config: {name}")

    if args.value is not None:
        value = args.value.encode()
    elif args.file is not None:
        value = args.file.read()
    elif args.random is not None:
        value = ''.join(
            rnd.choice(
                string.ascii_letters + string.digits + string.punctuation
            ) for _ in range(args.random)
        ).encode()
    else:
        value = click.prompt(
            "Value", hide_input=field.secret, confirmation_prompt=field.secret
        ).encode()

    try:
        args.conf.set(name, value, no_validate=args.no_validate, from_stdin=True)
    except exceptions.ValidationError as e:
        arg = e.args[0]
        if isinstance(arg, str):
            arg = [arg]
        parser.error("/n".join([str(v) for v in arg]))
    except exceptions.InvalidValue as e:
        parser.error(e)


def config_get(args, parser):
    name = args.name
    if name is None:
        name = helpers.ask([f[0] for f in args.conf.fields], prompt="Which config to get?")
    try:
        value = args.conf.get(name, to_stdout=True)
    except KeyError:
        parser.error(f"no such config: {name}")
    except exceptions.ConfigMissingError:
        parser.error("the config is not set and no default specified")
    except (FileNotFoundError, PermissionError):
        parser.error("wrong permission or missing file")
    sys.stdout.buffer.write(value)


def config_delete(args, parser):
    name = args.name
    if name is None:
        name = helpers.ask([f[0] for f in args.conf.fields], prompt="Which config to delete?")
    try:
        args.conf.set(name, None)
    except KeyError:
        parser.error(f"no such config: {name}")
    except exceptions.PermissionDenied:
        parser.error("must be root to set config")
    except (FileNotFoundError, PermissionError):
        parser.error("wrong permission or missing file")


def db_ensure(args, parser):
    try:
        db.ensure(args.conf, args.verbose)
    except exceptions.ImproperlyConfigured as e:
        parser.error(e)


def db_wait(args, parser):
    try:
        db.wait_for_db(args.timeout, args.conf, args.verbose)
    except exceptions.DatabaseNotPresent:
        sys.exit(1)


def cert_cmd(args, parser):
    if args.ip:
        ip_validator = validators.IPValidator()
        for ip in args.ip:
            try:
                ip_validator(None, ip)
            except exceptions.ValidationError as e:
                parser.error(e)
    cert.createcerts(args.name, ips=args.ip, wd=os.getcwd(), silent=args.silent, conf=args.conf)


def run_cmd(args, parser):
    if not args.cmd:
        parser.error("no command given")
    if args.user is not None:
        try:
            args.user = int(args.user)
        except ValueError:
            pass
    if args.group is not None:
        try:
            args.group = int(args.group)
        except ValueError:
            pass

    try:
        run.run(
            args.cmd, usr=args.user, grp=args.group,
            silent=args.silent, stopsignal=args.signal,
            exit=True
        )
    except exceptions.ImproperlyConfigured as e:
        parser.error(e)


def start_cmd(args, parser):
    try:
        start.start(args.service, args.conf)
    except exceptions.ServiceNotFound:
        parser.error(
            f"No starter function defined for service {args.service}."
            f" Available services are: {', '.join(start.get_starters().keys())}"
        )


def cli():
    conf = config.Config()

    parser = argparse.ArgumentParser(prog="gstack")
    parser.set_defaults(conf=conf)
    main_command = parser.add_subparsers(title="subcommands", dest="main_command")

    ##################
    # command `conf` #
    ##################
    conf_parser = main_command.add_parser("conf", help="config system")
    conf_command = conf_parser.add_subparsers(title="config subcommands", dest="conf_command")

    # conf inspect
    inspect_parser = conf_command.add_parser(
        "inspect", help="inspect configuration",
        description="inspect description"
    )
    group = inspect_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--name", "-n",
        help="name of the config to inspect",
        # choices=[x[0] for x in conf.fields],
    )
    group.add_argument(
        "--delete-stale", "-d", action="store_true",
        help="delete undefined config from storage files"
    )

    # conf set
    set_parser = conf_command.add_parser(
        "set", help="set configuration",
        description="set configuration"
    )
    set_parser.add_argument("--name", "-n", help="the name of the config")
    set_parser.add_argument(
        "--no-validate", "-V",
        action="store_true", help="do not validate the value"
    )
    group = set_parser.add_mutually_exclusive_group()
    group.add_argument("--value", "-v", help="the value of the config to set")
    group.add_argument("--random", "-r", type=int, help="set a random string", metavar="LEN")
    group.add_argument(
        "--file", "-f",
        type=FileType(mode="rb"),
        help="read the value from this file or STDIN (-)"
    )

    # conf get
    get_parser = conf_command.add_parser(
        "get", help="get configuration",
        description="get configuration"
    )
    get_parser.add_argument("--name", "-n", help="the name of the config to get")

    # conf delete
    delete_parser = conf_command.add_parser(
        "delete", help="delete configuration",
        description="delete configuration"
    )
    delete_parser.add_argument("--name", "-n", help="the name of the config to delete")

    ################
    # command `db` #
    ################
    db_parser = main_command.add_parser("db", help="database related commands")
    db_command = db_parser.add_subparsers(title="database subcommands", dest="db_command")

    # db ensure
    ensure_parser = db_command.add_parser(
        "ensure", help="setup the database, create users, set passwords, etc.",
        description="setup the database, create users, set passwords, etc."
    )
    ensure_parser.add_argument("--verbose", "-v", action="store_true")

    # db wait
    wait_parser = db_command.add_parser(
        "wait", help="wait for the database to accept connections",
        description="wait for the database to accept connections"
    )
    wait_parser.add_argument("--timeout", "-t", type=int, default=10)
    wait_parser.add_argument("--verbose", "-v", action="store_true")

    ##################
    # command `cert` #
    ##################
    cert_parser = main_command.add_parser("cert", help="create certificates for development")
    cert_parser.add_argument(
        "--name", "-n",
        help="name the generated certificate is valid for",
        action="append", required=True,
    )
    cert_parser.add_argument(
        "--ip", "-i",
        help="IP address the generated certificate is valid for",
        action="append"
    )
    cert_parser.add_argument("--silent", "-s", action="store_true")

    #################
    # command `run` #
    #################
    run_parser = main_command.add_parser("run", help="run commands as different user")
    run_parser.add_argument("--user", "-u")
    run_parser.add_argument("--group", "-g")
    run_parser.add_argument("--silent", "-s", action="store_true")
    run_parser.add_argument(
        "--signal",
        choices=[s for s in dir(signal) if s[:3] == "SIG" and s[3] != "_"]
    )
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER)

    ###################
    # command `start` #
    ###################
    start_parser = main_command.add_parser("start", help="start a service")
    start_parser.add_argument("service")

    ####################
    # command `backup` #
    ####################
    backup_parser = main_command.add_parser("backup", help="start a service")
    backup_cmd = conf.backup_cmd(backup_parser)

    ##################
    # do the parsing #
    ##################
    args = parser.parse_args()

    if args.main_command == "conf":
        if args.conf_command == "inspect":
            config_inspect(args, inspect_parser)
        elif args.conf_command == "set":
            config_set(args, set_parser)
        elif args.conf_command == "get":
            config_get(args, get_parser)
        elif args.conf_command == "delete":
            config_delete(args, delete_parser)
        else:
            conf_parser.error("no subcommand given")
    elif args.main_command == "db":
        if args.db_command == "ensure":
            db_ensure(args, ensure_parser)
        elif args.db_command == "wait":
            db_wait(args, wait_parser)
        else:
            db_parser.error("no subcommand given")
    elif args.main_command == "cert":
        cert_cmd(args, cert_parser)
    elif args.main_command == "run":
        run_cmd(args, run_parser)
    elif args.main_command == "start":
        start_cmd(args, start_parser)
    elif args.main_command == "backup":
        backup_cmd(args)
    else:
        parser.error("no subcommand given")
