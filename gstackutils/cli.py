import argparse
import sys
import random
import string
import signal

# import click
# import pick

# from . import config, helpers, exceptions, db, validators, cert, run, start
from . import conf
from . import exceptions
from . import run
from . import cert


# def db_ensure(args, parser):
#     try:
#         db.ensure(args.conf, args.verbose)
#     except exceptions.ImproperlyConfigured as e:
#         parser.error(e)
#
#
# def db_wait(args, parser):
#     try:
#         db.wait_for_db(args.timeout, args.conf, args.verbose)
#     except exceptions.DatabaseNotPresent:
#         sys.exit(1)
#
#
# def cert_cmd(args, parser):
#     if args.ip:
#         ip_validator = validators.IPValidator()
#         for ip in args.ip:
#             try:
#                 ip_validator(None, ip)
#             except exceptions.ValidationError as e:
#                 parser.error(e)
#     cert.createcerts(args.name, ips=args.ip, wd=os.getcwd(), silent=args.silent, conf=args.conf)


# def start_cmd(args, parser):
#     try:
#         start.start(args.service, args.conf)
#     except exceptions.ServiceNotFound:
#         parser.error(
#             f"No starter function defined for service {args.service}."
#             f" Available services are: {', '.join(start.get_starters().keys())}"
#         )


def conf_command(parser):
    def inspect_command(parser):
        def cmd(args):
            config = conf.Config(args.config_module)
            config.inspect(develop=args.develop)

        parser.set_defaults(func=cmd)
        parser.add_argument(
            "--develop", "-d",
            help="show extra information (for development)",
            action="store_true"
        )

    def set_command(parser):
        def cmd(args):
            config = conf.Config(args.config_module)
            if not config.root_mode:
                parser.error("must be root to set config")
            try:
                field = config.get_field(args.name)
            except KeyError:
                config.inspect()
                parser.error(f"no such config: {args.name}")

            if args.value is not None:
                if field.binary:
                    parser.error("binary field can not be set from the command line")
                value = args.value
            elif args.random is not None:
                if field.binary:
                    parser.error("binary field can not use the random setter")
                value = ''.join(
                    random.choice(
                        string.ascii_letters + string.digits + string.punctuation
                    ) for _ in range(args.random)
                )
            else:
                if field.binary:
                    value = sys.stdin.buffer.read()
                else:
                    value = sys.stdin.read()

            try:
                config.set(args.name, value, stream=True)
            except exceptions.ValidationError as e:
                parser.error(e)

        parser.set_defaults(func=cmd)
        parser.add_argument("name", help="field name")
        # parser.add_argument("--name", "-n", help="field name")
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--value", "-v", help="the value of the config to set"
        )
        group.add_argument(
            "--random", "-r", type=int,
            help="set a random string of given length", metavar="LEN"
        )

    def get_command(parser):
        def cmd(args):
            config = conf.Config(args.config_module)
            try:
                stream = config.get(args.name, stream=True)
            except KeyError:
                config.inspect()
                parser.error(f"no such config: {args.name}")
            if isinstance(stream, bytes):
                sys.stdout.buffer.write(stream)
            else:
                sys.stdout.write(stream)

        parser.set_defaults(func=cmd)
        parser.add_argument("name", help="field name")

    def del_command(parser):
        def cmd(args):
            config = conf.Config(args.config_module)
            try:
                config.set(args.name, None)
            except KeyError:
                config.inspect()
                parser.error(f"no such config: {args.name}")

        parser.set_defaults(func=cmd)
        parser.add_argument("name", help="field name")

    def delstale_command(parser):
        def cmd(args):
            config = conf.Config(args.config_module)
            config.delete_stale()

        parser.set_defaults(func=cmd)

    subcommands = parser.add_subparsers(title="conf commands")

    inspect_parser = subcommands.add_parser("inspect", help="inspect config")
    inspect_command(inspect_parser)
    set_parser = subcommands.add_parser("set", help="set config field")
    set_command(set_parser)
    get_parser = subcommands.add_parser("get", help="get config field")
    get_command(get_parser)
    del_parser = subcommands.add_parser("delete", help="delete config field")
    del_command(del_parser)
    delstale_parser = subcommands.add_parser("delete-stale", help="delete stale config")
    delstale_command(delstale_parser)


def run_command(parser):
    def cmd(args):
        if not args.cmd:
            parser.error("no command given")
        if args.signal is not None:
            if not hasattr(signal, args.signal) or args.signal[:3] != "SIG":
                parser.error(f"invalid signal: {args.signal}")
        try:
            run.run(
                args.cmd, usr=args.user, grp=args.group,
                silent=args.silent, stopsignal=args.signal,
                exit=True
            )
        except exceptions.ImproperlyConfigured as e:
            parser.error(e)

    parser.set_defaults(func=cmd)
    parser.add_argument("--user", "-u")
    parser.add_argument("--group", "-g")
    parser.add_argument("--silent", "-s", action="store_true")
    parser.add_argument(
        "--signal",
        help="the signal to send to the process when terminating (ex.: `SIGINT`)"
    )
    parser.add_argument("cmd", nargs=argparse.REMAINDER)


def cert_command(parser):
    def cmd(args):
        cert.generate(args.name, args.ip, args.ca_key_file, args.ca_cert_file)

    parser.set_defaults(func=cmd)
    parser.add_argument(
        "--name", "-n",
        help="name the generated certificate is valid for",
        action="append", required=True,
    )
    parser.add_argument(
        "--ip", "-i",
        help="IP address the generated certificate is valid for",
        action="append"
    )
    parser.add_argument(
        "--ca-key-file", "-k",
        help="root CA key file (pem format, relative to project root) if present",
    )
    parser.add_argument(
        "--ca-cert-file", "-c",
        help="root CA certificate file (pem format, relative to project root) if present",
    )


def cli():
    parser = argparse.ArgumentParser(prog="gstack")
    parser.add_argument("--config-module", "-m", help="the config module")
    subcommands = parser.add_subparsers(title="commands")

    conf_parser = subcommands.add_parser("conf", help="configuration system")
    conf_command(conf_parser)
    run_parser = subcommands.add_parser("run", help="run command as different user")
    run_command(run_parser)
    cert_parser = subcommands.add_parser("cert", help="generate certificates for development")
    cert_command(cert_parser)

#     ################
#     # command `db` #
#     ################
#     db_parser = main_command.add_parser("db", help="database related commands")
#     db_command = db_parser.add_subparsers(title="database subcommands", dest="db_command")
#
#     # db ensure
#     ensure_parser = db_command.add_parser(
#         "ensure", help="setup the database, create users, set passwords, etc.",
#         description="setup the database, create users, set passwords, etc."
#     )
#     ensure_parser.add_argument("--verbose", "-v", action="store_true")
#
#     # db wait
#     wait_parser = db_command.add_parser(
#         "wait", help="wait for the database to accept connections",
#         description="wait for the database to accept connections"
#     )
#     wait_parser.add_argument("--timeout", "-t", type=int, default=10)
#     wait_parser.add_argument("--verbose", "-v", action="store_true")
#
#     ##################
#     # command `cert` #
#     ##################
#     cert_parser = main_command.add_parser("cert", help="create certificates for development")
#     cert_parser.add_argument(
#         "--name", "-n",
#         help="name the generated certificate is valid for",
#         action="append", required=True,
#     )
#     cert_parser.add_argument(
#         "--ip", "-i",
#         help="IP address the generated certificate is valid for",
#         action="append"
#     )
#     cert_parser.add_argument("--silent", "-s", action="store_true")
#
#
#     ###################
#     # command `start` #
#     ###################
#     start_parser = main_command.add_parser("start", help="start a service")
#     start_parser.add_argument("service")
#
#     ####################
#     # command `backup` #
#     ####################
#     backup_parser = main_command.add_parser("backup", help="start a service")
#     backup_cmd = conf.backup_cmd(backup_parser)

    args = parser.parse_args()
    args.func(args)
