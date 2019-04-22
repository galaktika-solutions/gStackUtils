import psycopg2

from gstackutils.conf import Section, EnvString, SecretString
from gstackutils.helpers import pg_pass


class PYPI_CREDENTIALS(Section):
    PYPI_USERNAME = EnvString()
    PYPI_PASSWORD = SecretString(min_length=8)


class POSTGRES(Section):
    DB_PASSWORD_POSTGRES = SecretString(min_length=8)
    DB_PASSWORD_DJANGO = SecretString(min_length=8)


def pg_init(conf):
    postgres_pass = pg_pass("postgres", conf.get("DB_PASSWORD_POSTGRES"))
    django_pass = pg_pass("django", conf.get("DB_PASSWORD_DJANGO"))

    return([
        (
            "postgres", "postgres",
            "ALTER ROLE postgres ENCRYPTED PASSWORD %s", (postgres_pass,),
        ),
        (
            "template1", "postgres",
            "CREATE EXTENSION unaccent; CREATE EXTENSION fuzzystrmatch", (),
        ),
        (
            "postgres", "postgres",
            "CREATE ROLE django", (),
        ),
        (
            "postgres", "postgres",
            "ALTER ROLE django ENCRYPTED PASSWORD %s LOGIN CREATEDB", (django_pass,),
        ),
        (
            "postgres", "django",
            "CREATE DATABASE django", (),
        ),
    ])


def healthcheck(conf):
    dbname = "django"
    user = "django"
    password = conf.get("DB_PASSWORD_DJANGO")
    host = "postgres"
    psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
