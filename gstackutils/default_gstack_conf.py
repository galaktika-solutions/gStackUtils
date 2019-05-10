import psycopg2

from .helpers import pg_pass
from .config import Section
from . import fields
from .db import ensure, wait_for_db
from .run import run


class POSTGRES(Section):
    DB_PASSWORD_POSTGRES = fields.StringConfig(secret=True, min_length=8)
    DB_PASSWORD_DJANGO = fields.StringConfig(
        secret=True, min_length=8, services={"django": ["django"]}
    )
    DB_PASSWORD_EXPLORER = fields.StringConfig(
        secret=True, min_length=8, services={"django": ["django"]}
    )


class DJANGO(Section):
    DJANGO_SECRET_KEY = fields.StringConfig(
        secret=True, min_length=64, services={"django": ["django"]}
    )


def validate(conf):
    ret = []
    # ret.append("An error message to show.")
    return ret


def pg_init(conf):
    postgres_pass = pg_pass("postgres", conf.get("DB_PASSWORD_POSTGRES"))
    django_pass = pg_pass("django", conf.get("DB_PASSWORD_DJANGO"))
    explorer_pass = pg_pass("django", conf.get("DB_PASSWORD_EXPLORER"))

    return([
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
    ])


def healthcheck(conf):
    dbname = "django"
    user = "django"
    password = conf.get("DB_PASSWORD_DJANGO")
    host = "postgres"
    psycopg2.connect(dbname=dbname, user=user, password=password, host=host)


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
