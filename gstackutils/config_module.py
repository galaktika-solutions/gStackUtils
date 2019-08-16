import argparse
import sys
import os

from . import conf
from . import fields
from . import default_utils as du
from . import run
from . import exceptions
from . import utils
from . import validators


class COMPOSE_VARIABLES(conf.Section):
    COMPOSE_FILE = fields.StringField(default="docker-compose.yml")
    HOST_NAMES = fields.StringListField(
        default=["gstack.localhost"],
        validators=(validators.HostNameValidator(),)
    )


class CERTIFICATES(conf.Section):
    CERTIFICATE_KEY = fields.SSLPrivateKeyField()
    CERTIFICATE_CRT = fields.SSLCertificateField(secret=True)

    nginx = conf.Service(
        CERTIFICATE_KEY="nginx",
        CERTIFICATE_CRT="nginx",
    )


class POSTGRES_PASSWORDS(conf.Section):
    DB_PASSWORD_POSTGRES = fields.StringField(secret=True)
    DB_PASSWORD_DJANGO = fields.StringField(secret=True)
    DB_PASSWORD_EXPLORER = fields.StringField(secret=True)

    postgres = conf.Service(
        DB_PASSWORD_POSTGRES="postgres",
        DB_PASSWORD_DJANGO="postgres",
        DB_PASSWORD_EXPLORER="postgres",
    )

    django = conf.Service(
        DB_PASSWORD_DJANGO="django",
        DB_PASSWORD_EXPLORER="django",
    )


class DJANGO(conf.Section):
    DJANGO_SECRET_KEY = fields.StringField(secret=True)
    DJANGO_DEBUG = fields.BooleanField(default=False)
    ADMINS = fields.EmailListField()
    SERVER_EMAIL = fields.EmailField()
    USE_UWSGI = fields.BooleanField(default=False)

    django = conf.Service(
        DJANGO_SECRET_KEY="django",
    )


class TECHNICAL(conf.Section):
    BACKUP_UID = fields.IntegerField(default=0)
    BACKUP_GID = fields.IntegerField(default=BACKUP_UID)


def validate(config):
    if not config.is_dev and config.get("DJANGO_DEBUG"):
        raise exceptions.ValidationError("Django DEBUG must not be True in production")
    if not config.is_dev and not config.get("USE_UWSGI"):
        raise exceptions.ValidationError("In production uwsgi must be used")


class Start_postgres(conf.Command):
    """start the postgresql service"""

    def cmd(self, args):
        args.config.prepare("postgres")
        postgres_pass = du.pg_pass("postgres", args.config.get("DB_PASSWORD_POSTGRES"))
        django_pass = du.pg_pass("django", args.config.get("DB_PASSWORD_DJANGO"))
        explorer_pass = du.pg_pass("django", args.config.get("DB_PASSWORD_EXPLORER"))

        actions = [
            {
                "sql": "ALTER ROLE postgres ENCRYPTED PASSWORD %s",
                "params": (postgres_pass,),
            },
            {
                "dbname": "template1",
                "sql": "CREATE EXTENSION unaccent",
            },
            {
                "dbname": "template1",
                "sql": "CREATE EXTENSION fuzzystrmatch",
            },
            {
                "sql": "CREATE ROLE django",
            },
            {
                "sql": "ALTER ROLE django ENCRYPTED PASSWORD %s LOGIN CREATEDB",
                "params": (django_pass,),
            },
            {
                "sql": "CREATE ROLE explorer",
            },
            {
                "sql": "ALTER ROLE explorer ENCRYPTED PASSWORD %s LOGIN",
                "params": (explorer_pass,),
            },
            {
                "user": "django",
                "sql": "CREATE DATABASE django",
            },
            {
                "dbname": "django",
                "sql": "CREATE EXTENSION unaccent",
            },
            {
                "dbname": "django",
                "sql": "CREATE EXTENSION fuzzystrmatch",
            },
            {
                "user": "django", "dbname": "django",
                "sql": "CREATE SCHEMA django",
            },
            {
                "user": "django", "dbname": "django",
                "sql": "GRANT SELECT ON ALL TABLES IN SCHEMA django TO explorer",
            },
            {
                "user": "django", "dbname": "django",
                "sql": "ALTER DEFAULT PRIVILEGES FOR USER django IN SCHEMA django "
                       "GRANT SELECT ON TABLES TO explorer",
            },
        ]

        utils.path_fix("/host/log/", usr=args.config.pu, grp=args.config.pg)
        utils.path_fix("/host/log/postgres/", usr="postgres", grp="postgres")
        du.ensure_postgres(
            args.config, verbose=True, actions=actions,
            cpenv={"LOG_FILE_MODE": "0644" if args.config.is_dev else "0600"}
        )
        run.run(["postgres"], usr="postgres", exit=True)


class Start_nginx(conf.Command):
    """start the nginx service"""

    def cmd(self, args):
        args.config.prepare("nginx")
        utils.path_fix("/host/log/", usr=args.config.pu, grp=args.config.pg)
        utils.path_check(
            "/host/log/nginx/",
            usr="nginx", grp="nginx", mode=(0o755 if args.config.is_dev else 0o700),
            fix=True
        )

        conf = "/src/config/nginx.conf"
        if args.config.get("USE_UWSGI"):
            conf = "/src/config/nginx_uwsgi.conf"
        utils.cp(
            conf, "/etc/nginx/nginx.conf",
            substitute=True, usr="nginx", grp="nginx", mode=0o600
        )
        run.run(["nginx"], exit=True)


class Start_django(conf.Command):
    """start django; development server or uwsgi"""

    def cmd(self, args):
        utils.path_fix("/host/log/", usr=args.config.pu, grp=args.config.pg)
        utils.path_fix("/host/log/django/", usr="django", grp="django")

        if args.config.get("USE_UWSGI"):
            utils.path_fix("/host/log/uwsgi/", usr="django", grp="django")
            args.config.prepare("django")
            du.wait_for_db(verbose=args.config.is_dev)
            du.set_files_perms()
            run.run(
                ["uwsgi", "--ini", "config/uwsgi.conf"],
                usr="django", stopsignal="SIGINT", exit=True
            )

        args.command = ["runserver", "0.0.0.0:8000"]
        args.chown = False
        Django_admin(None).cmd(args)


class Django_admin(conf.Command):
    "run django-admin with Django's dependencies and permissions"

    def arguments(self, parser):
        parser.add_argument("command", nargs=argparse.REMAINDER)
        parser.add_argument("--chown", action="store_true")

    def cmd(self, args):
        args.config.prepare("django")
        du.wait_for_db(verbose=args.config.is_dev)
        du.set_files_perms()
        # in development mode, we change some source folder's and files ownership
        # (recursively) to django and change it back later.
        os.chdir("/src/django_project")
        if args.config.is_dev and args.chown:
            utils.path_fix("/src/django_project/", usr="django", grp="django")
            utils.path_fix("/src/static/", usr="django", grp="django")
        returncode = run.run(
            ["django-admin"] + args.command,
            usr="django", stopsignal="SIGINT"
        )
        if args.config.is_dev and args.chown:
            utils.path_fix("/src/django_project/", usr=args.config.pu, grp=args.config.pg)
            utils.path_fix("/src/static/", usr=args.config.pu, grp=args.config.pg)
            utils.pycclean()
        sys.exit(returncode)


class Backup(conf.Command):
    """create a backup"""

    def arguments(self, parser):
        parser.add_argument("-d", "--dbformat", choices=['custom', 'plain'])
        parser.add_argument("-f", "--files", action="store_true")

    def cmd(self, args):
        du.backup(config=args.config, dbformat=args.dbformat, files=args.files)


class Restore(conf.Command):
    """restore existing backup"""

    def arguments(self, parser):
        parser.add_argument("-d", "--dumpfile")
        parser.add_argument("-f", "--files", action="store_true")

    def cmd(self, args):
        du.restore(config=args.config, dumpfile=args.dumpfile, files=args.files)
