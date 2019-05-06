from gstackutils.config import Section
from gstackutils.helpers import pg_pass
from gstackutils.fields import (
    EnvString, SecretString, EnvBool, EnvFile, SecretFile,
    SSLPrivateKey, SSLCertificate
)


class PYPI_CREDENTIALS(Section):
    """Credentials for https://pypi.org/"""
    PYPI_USERNAME = EnvString()
    PYPI_PASSWORD = SecretString(min_length=8)


from gstackutils.default_gstack_conf import POSTGRES, DJANGO  # noqa


class TESTING(Section):
    """Definitions for testing purposes only."""

    BOOL = EnvBool(default=False)
    SECRETSTRING = SecretString(min_length=8, help_text="Some secret long enough.")
    ENVFILE = EnvFile(min_size=50)
    SECRETFILE = SecretFile(max_size=100)
    PRIVATEKEY = SSLPrivateKey()
    CACERT = SSLCertificate(default=b"", validate=False)
    CERTIFICATE = SSLCertificate(getCA=lambda conf: conf.get("CACERT"))


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
