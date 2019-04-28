import psycopg2
# import click

from gstackutils.conf import (
    Section, EnvString, SecretString, EnvBool, EnvFile, SecretFile,
    SSLPrivateKey, SSLCertificate
)
from gstackutils.helpers import pg_pass


class PYPI_CREDENTIALS(Section):
    PYPI_USERNAME = EnvString()
    PYPI_PASSWORD = SecretString(min_length=8)


class POSTGRES(Section):
    DB_PASSWORD_POSTGRES = SecretString(min_length=8)
    DB_PASSWORD_DJANGO = SecretString(min_length=8)


class JustForFun(Section):
    BOOL = EnvBool(default=False)
    SECRETSTRING = SecretString(min_length=8)
    ENVFILE = EnvFile(min_size=50)
    SECRETFILE = SecretFile(max_size=100)
    PRIVATEKEY = SSLPrivateKey()
    CACERT = SSLCertificate(default=b"", validate=False)
    CERTIFICATE = SSLCertificate(getCA=lambda conf: conf.get("CACERT"))


def pg_init(conf):
    postgres_pass = pg_pass("postgres", conf.get("DB_PASSWORD_POSTGRES"))
    django_pass = pg_pass("django", conf.get("DB_PASSWORD_DJANGO"))

    return([
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
            "user": "django",
            "sql": "CREATE DATABASE django",
        },
    ])


def healthcheck(conf):
    dbname = "django"
    user = "django"
    password = conf.get("DB_PASSWORD_DJANGO")
    host = "postgres"
    psycopg2.connect(dbname=dbname, user=user, password=password, host=host)


# @click.command(name="backup")
# @click.option("--db", "-d", is_flag=True)
# @click.option("--files", "-f", is_flag=True)
# def backup_cli(db, files):
#     print("doing backup...")
