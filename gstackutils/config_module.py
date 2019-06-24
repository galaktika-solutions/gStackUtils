from . import conf
from . import fields
from . import default_utils as du
from . import run


class COMPOSE_VARIABLES(conf.Section):
    COMPOSE_FILE = fields.StringField(default="docker-compose.yml")


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
    )


class DJANGO(conf.Section):
    DJANGO_SECRET_KEY = fields.StringField(secret=True)

    django = conf.Service(
        DJANGO_SECRET_KEY="django",
    )


class Start_postgres(conf.Command):
    "start the postgresql service"

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

        du.ensure_postgres(verbose=True, actions=actions)
        run.run(["postgres"], usr="postgres", exit=True)


class Start_django(conf.Command):
    "start the django service"

    def cmd(self, args):
        args.config.prepare("django")
        du.wait_for_db()
        run.run(
            ["django-admin", "runserver", "0.0.0.0:8000"],
            usr="django", stopsignal="SIGINT", exit=True
        )
